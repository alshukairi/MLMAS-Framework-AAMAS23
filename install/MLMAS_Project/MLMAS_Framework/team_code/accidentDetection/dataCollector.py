import os
import pandas as pd
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from models.negative_sampling_train.eval_one_epoch import eval_one_epoch
from models.datasetPreprocessor import dataProcessor
class dataCollector:
    def __init__(self, ego, world, collect_t, neighbors, target_t, output_dir):
        self.scenario_id = 0
        self.neighbor_count = neighbors
        self.fps = 20
        self.target_frames = collect_t * self.fps
        self.target_frames_end = target_t * self.fps
        self.ego = ego
        self.ego_location = ego.get_location()
        self.world = world
        self.ego_new_id = None
        self.output_dir = output_dir
        # world = CarlaDataProvider.get_world()

    def reset_collected_data(self):
        self.collected_data = []

    def get_vehicle_info(self, vehicle, ego_location, world):
        transform = vehicle.get_transform()
        location = transform.location
        yaw = transform.rotation.yaw
        velocity = vehicle.get_velocity()
        bbox = vehicle.bounding_box
        extent = bbox.extent
        dimensions = (extent.x * 2, extent.y * 2, extent.z * 2)
        vehicle_type = vehicle.type_id

        distance = ego_location.distance(location)
        frame_id = world.get_snapshot().frame


        return {
            "scenario_id": self.scenario_id,
            "agent_id": vehicle.id,
            "frame_id": round(frame_id, 3),
            "type_encoded": vehicle_type,
            'l': round(dimensions[0], 2),
            'w': round(dimensions[1], 2),
            'h': round(dimensions[2], 2),
            'x' : round(location.x, 2),
            'y' : round(location.y, 2),
            'z' : round(location.z, 2),
            'vx': round(velocity.x, 2),
            'vy': round(velocity.y, 2),
            "yaw": round(yaw, 2),
            'rel_dist': round(distance, 2),

        }

    def collect_one_frame(self):
        num_neighbors = 0
        ego_info = self.get_vehicle_info(self.ego, self.ego_location, self.world)
        ego_info["label"] = 1  # 主车是正样本

        all_vehicles = self.world.get_actors().filter("vehicle.*")
        if len(all_vehicles) < self.neighbor_count:
            num_neighbors = all_vehicles / 2
        elif len(all_vehicles) >= self.neighbor_count:
            num_neighbors = self.neighbor_count
        else :
            raise ValueError("Number of vehicles exceeds number of neighbors")
        vehicle_infos = []

        for v in all_vehicles:
            if v.id != self.ego.id:
                info = self.get_vehicle_info(v, self.ego_location, self.world)
                vehicle_infos.append(info)

        # 按与ego的距离排序（近 → 远）
        vehicle_infos.sort(key=lambda x: x["rel_dist"])

        # 正样本：最近的 N 个邻居
        pos_neighbors = vehicle_infos[:num_neighbors]
        for v in pos_neighbors:
            v["pos_neg"] = 1

        # 负样本：最远的 num_negatives 个邻居
        neg_neighbors = vehicle_infos[-num_neighbors:]
        for v in neg_neighbors:
            v["pos_neg"] = 0

        # 追加到 collected_data
        self.collected_data.append(ego_info)  # ego
        self.collected_data.extend(pos_neighbors)  # 正邻居
        self.collected_data.extend(neg_neighbors)  # 负邻居

    def prepare_dataset(self, data):
        df = pd.DataFrame(data)
        df = df[df["scenario_id"] == self.scenario_id]

        clear_cols = ["x", "y", "z", "vx", "vy", "yaw"]
        base_cols = ["agent_id", "type", "l", "w", "h", "scenario_id"]
        padded_rows = []
        duration = self.target_frames_end - self.target_frames

        for vid in df["agent_id"].unique():
            vehicle_data = df[df["agent_id"] == vid].sort_values("frame_id")

            if vehicle_data["frame_id"].nunique() >= self.target_frames:
                last_row = vehicle_data.iloc[-1]
                last_frame = last_row["frame_id"]


                for i in range(1, duration + 1 ):  # 60 frames for 3 seconds
                    new_row = {col: last_row[col] for col in base_cols}
                    new_row["frame_id"] = last_frame + i

                    for col in clear_cols:
                        new_row[col] = 0

                    padded_rows.append(new_row)

        # 拼接补齐数据并排序
        padded_df = pd.concat([df, pd.DataFrame(padded_rows)], ignore_index=True)
        padded_df = padded_df.sort_values(by=["agent_id", "frame_id"]).reset_index(drop=True)

        return padded_df

    def create_node_features(self, data_df):
        # 保留唯一 agent 的静态属性（按 agent 分组取第一行）
        unique_agents = data_df.drop_duplicates(subset=["agent_id"])

        unique_agents = unique_agents.copy()
        unique_agents["global_id"] = range(len(unique_agents))

        node_features = unique_agents[[
            "global_id", "scenario_id", "agent_id",
            "w", "h", "l", "type_encoded"
        ]]

        # 设置主车 global_id（可用于 edge 构建）
        ego_row = node_features[node_features["agent_id"] == self.ego.id]
        if not ego_row.empty:
            self.ego_new_id = int(ego_row.iloc[0]["global_id"])
        else:
            raise ValueError("ego row is empty")

        return node_features

    def create_edge_features(self,data_df):
        edge_rows = []

        for frame_id in sorted(data_df["frame_id"].unique()):
            frame_nodes = data_df[data_df["frame_id"] == frame_id]
            for j, row_j in frame_nodes.iterrows():
                edge_rows.append({
                    "src": self.ego_new_id,
                    "dst": j,
                    "frame_id": frame_id,
                    "rel_dist": row_j["rel_dist"]
                })
        return pd.DataFrame(edge_rows)

    def create_all_edges(self,edge_df):
        return edge_df[["src", "dst"]].drop_duplicates().reset_index(drop=True)

    def run(self):
        self.collect_one_frame()
        if len(self.collected_data) < self.target_frames:
            return False

        data_df = self.prepare_dataset(self.pos_data)

        node_feature_df = self.create_node_features(data_df)
        edge_features_df = self.create_edge_features(data_df)
        all_edges_df = self.create_all_edges(edge_features_df)

        # 保存
        self.reset_collected_data()

        scenario_dir = os.path.join(self.output_dir, f"/{self.scenario_id}")
        os.makedirs(scenario_dir, exist_ok=True)

        node_feature_df.to_csv(f"{scenario_dir}/pos_node_feature.csv", index=False)
        edge_features_df.to_csv(f"{scenario_dir}/edge_features.csv", index=False)
        all_edges_df.to_csv(f"{scenario_dir}/all_edges.csv", index=False)

        self.scenario_id += 1


        splitDataset = dataProcessor(root_dir=scenario_dir, output_dir=scenario_dir, mask_node_num=self.neighbor_count)
        splitDataset.run()




