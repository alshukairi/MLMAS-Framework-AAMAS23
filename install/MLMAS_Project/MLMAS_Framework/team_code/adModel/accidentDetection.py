import os
import pandas as pd
import numpy as np
import math
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider

from adModel.models.dataProcessor import dataProcessor
from adModel.models.TGANTrainer import TGANTrainer
import itertools
from vehicle_types import vehicle_type_mapping


class accidentDetection:
    def __init__(self, ego, world,senaria_name, collect_t = 30, neighbors=2, target_t=60, output_dir = "/home/jamie/MLMAS-Framework-AAMAS23/install/MLMAS_Project/output"):
        self.scenario_id = 0
        self.neighbor_count = neighbors
        self.fps = 1
        self.s_t = collect_t
        self.e_t = target_t
        self.target_frames = collect_t * self.fps
        self.target_frames_end = target_t * self.fps
        self.ego = ego
        self.world = world
        self.ego_new_id = None
        self.output_dir = output_dir
        self.collected_data = []
        self.fixed_neighbors = None
        self.time_map = {}
        self.senaria_name = senaria_name

        # world = CarlaDataProvider.get_world()

    def reset_collected_data(self):
        self.collected_data = []
        self.fixed_neighbors = None

    def get_actor_info(self, actor, ego_location):
        transform = actor.get_transform()
        location = transform.location
        yaw = transform.rotation.yaw
        velocity = actor.get_velocity()
        bbox = actor.bounding_box
        extent = bbox.extent
        dimensions = (extent.x * 2, extent.y * 2, extent.z * 2)

        # 判断类型
        a_type = actor.type_id
        if a_type.startswith("walker.pedestrian"):
            vehicle_type = vehicle_type_mapping.get("walker.pedestrian", None)
        else:
            vehicle_type = vehicle_type_mapping.get(a_type, None)

        type_order = [
            "car", "truck", "van", "bus", "motorcycle", "pedestrian", "cyclist", "none"
        ]
        type_to_idx = {label: idx + 1 for idx, label in enumerate(type_order)}
        type_encoded = type_to_idx[vehicle_type]

        frame_id = self.world.get_snapshot().frame

        # 相对位置和角度
        dst_x = round(location.x, 6)
        dst_y = round(location.y, 6)
        src_x = ego_location.x
        src_y = ego_location.y
        dx = dst_x - src_x
        dy = dst_y - src_y
        distance = math.sqrt(dx ** 2 + dy ** 2)  # 只算平面距离
        theta = math.atan2(dy, dx)

        s_yaw = self.ego.get_transform().rotation.yaw
        src_yaw = math.radians(s_yaw)
        dst_yaw = math.radians(yaw)
        phi_src = ((theta - src_yaw) + np.pi) % (2 * np.pi) - np.pi
        phi_dst = ((theta - dst_yaw) + np.pi) % (2 * np.pi) - np.pi

        # ego 尺寸
        e_extent = self.ego.bounding_box.extent
        src_shape = (e_extent.x * 2, e_extent.y * 2, e_extent.z * 2)
        l_src = src_shape[0]
        w_src = src_shape[1]
        l_dst = round(dimensions[0], 6)
        w_dst = round(dimensions[1], 6)

        # 投影半径
        a_src = l_src / 2.0
        b_src = w_src / 2.0
        a_dst = l_dst / 2.0
        b_dst = w_dst / 2.0
        r_src = a_src * abs(np.cos(phi_src)) + b_src * abs(np.sin(phi_src))
        r_dst = a_dst * abs(np.cos(phi_dst)) + b_dst * abs(np.sin(phi_dst))

        m_proj = distance - (r_src + r_dst)

        return {
            "scenario_id": self.scenario_id,
            "agent_id": actor.id,
            "frame_id": round(frame_id, 3),
            "type_encoded": type_encoded,
            "l": l_dst,
            "w": w_dst,
            "h": round(dimensions[2], 6),
            "x": dst_x,
            "y": dst_y,
            "z": round(location.z, 6),
            "vx": round(velocity.x, 6),
            "vy": round(velocity.y, 6),
            "yaw": round(dst_yaw, 6),
            "rel_dis": round(distance, 6),
            "m_proj": m_proj,
        }

    def collect_one_frame(self):
        ego_location = self.ego.get_location()
        ego_info = self.get_actor_info(self.ego, ego_location)

        # all_vehicles = self.world.get_actors().filter("vehicle.*")
        vehicles = self.world.get_actors().filter("vehicle.*")
        walkers = self.world.get_actors().filter("walker.pedestrian.*")
        all_actors = list(vehicles) + list(walkers)
        # 第一次采集时锁定固定邻居
        if self.fixed_neighbors is None:
            vehicle_infos = []
            for v in all_actors:
                if v.id != self.ego.id:
                    info = self.get_actor_info(v, ego_location)
                    vehicle_infos.append(info)

            # 按距离排序
            vehicle_infos.sort(key=lambda x: x["rel_dis"])

            # 获取前 N 个邻居的 vehicle_id，初始化 global_id 为 -1（后续填充）
            self.fixed_neighbors = {
                info["agent_id"]: -1 for info in vehicle_infos[:self.neighbor_count]
            }

        # 收集固定邻居的数据
        neighbor_infos = []

        for v in all_actors:
            if v.id in self.fixed_neighbors:
                info = self.get_actor_info(v, ego_location)
                neighbor_infos.append(info)

        # 保存当前帧数据
        frame_data = [ego_info] + neighbor_infos
        self.collected_data.append(frame_data)

    def prepare_dataset(self, collected_data):

        flat_data = [agent for frame in collected_data for agent in frame]
        df = pd.DataFrame(flat_data)
        df = df[df["scenario_id"] == self.scenario_id]

        clear_cols = ["x", "y", "z", "vx", "vy", "yaw"]
        base_cols = ["agent_id", "type_encoded", "l", "w", "h", "scenario_id"]

        padded_rows = []
        duration = self.target_frames_end - self.target_frames

        for vid in df["agent_id"].unique():
            vehicle_data = df[df["agent_id"] == vid].sort_values("frame_id")

            if vehicle_data["frame_id"].nunique() > self.target_frames:
                last_row = vehicle_data.iloc[-1]
                last_frame = last_row["frame_id"]

                for i in range(1, duration + 1 ):
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

        unique_agents = data_df.drop_duplicates(subset=["agent_id"])

        unique_agents = unique_agents.copy()
        unique_agents["global_id"] = range(len(unique_agents))

        node_features = unique_agents[[
            "global_id", "scenario_id", "agent_id",
            "w", "h", "l", "type_encoded",
        ]]


        ego_row = node_features[node_features["agent_id"] == self.ego.id]
        if not ego_row.empty:
            self.ego_new_id = int(ego_row.iloc[0]["global_id"])
        else:
            raise ValueError("ego row is empty")


        return node_features


    def create_edge_features(self, or_data_df,node_features_df, scenario_dir):
        edge_rows = []
        data_df = or_data_df.merge(
            node_features_df[["agent_id", "global_id"]],
            on="agent_id", how="left"
        )
        for frame_id in sorted(data_df["frame_id"].unique()):
            frame_nodes = data_df[data_df["frame_id"] == frame_id]

            node_ids = frame_nodes["global_id"].tolist()

            rel_dists = dict(zip(frame_nodes["global_id"], frame_nodes["rel_dis"]))
            m_proj_dists = dict(zip(frame_nodes["global_id"], frame_nodes["m_proj"]))
            node_info = frame_nodes.set_index("global_id")[["vx", "vy", "yaw"]].to_dict("index")

            # 有序配对（不含自环）
            for src, dst in itertools.permutations(node_ids, 2):
                src_info = node_info[src]
                dst_info = node_info[dst]

                edge_rows.append({
                    "src": src,
                    "dst": dst,
                    "frame_id": frame_id,
                    "rel_dis":  rel_dists[dst],
                    "m_proj": m_proj_dists[dst],
                    "vx": src_info["vx"] - dst_info["vx"],
                    "vy": src_info["vy"]  - dst_info["vy"],
                    "yaw": src_info["yaw"] - dst_info["yaw"],
                    "ego":  1 if src == self.ego_new_id else 0

                })

        edge_df = pd.DataFrame(edge_rows).sort_values("frame_id").reset_index(drop=True)

        # 初始化 time 列
        edge_df["time"] = -1  # 初始化

        for (src, dst), group in edge_df.groupby(["src", "dst"]):
            first_frame = group["frame_id"].min()
            local_time = ((group["frame_id"] - first_frame) // self.fps)
            edge_df.loc[group.index, "time"] = local_time

            # 更新后的 group 包含 time 列
            updated_group = edge_df.loc[group.index]

            # 构建 per-time 的 frame info
            time_group = (
                updated_group.groupby("time")["frame_id"]
                .agg(["min", "max"])
                .rename(columns={"min": "frame_start", "max": "frame_end"})
                .to_dict(orient="index")
            )

            self.time_map[(src, dst)] = time_group

        # 平均每条边每段时间的特征
        mean_cols = ["rel_dis", "vx", "vy", "yaw","m_proj"]
        avg_df = (
            edge_df.groupby(["time", "src", "dst", "ego"], as_index=False)[mean_cols].mean()
        )

        time_max_by_pair = avg_df.groupby(["src", "dst"])["time"].max()


        if (time_max_by_pair < self.e_t).any():
            print(f"Error : {scenario_dir}")
            self.reset_collected_data()
        return avg_df

    def create_all_edges(self,edge_df):
        return edge_df[["src", "dst"]].drop_duplicates().reset_index(drop=True)

    def run(self):

        self.collect_one_frame()

        # 检查 frame_id 的跨度是否达到目标帧数
        if len(self.collected_data) < 2:
            return 0

        ego_frame_ids = [frame[0]["frame_id"] for frame in self.collected_data]
        frame_span = ego_frame_ids[-1] - ego_frame_ids[0]


        if frame_span == self.target_frames_end:
            s_dir = os.path.join(self.output_dir, f"{self.senaria_name}/{self.scenario_id}")
            flat_data = [agent for frame in self.collected_data for agent in frame]
            all_df = pd.DataFrame(flat_data)
            all_df.to_csv(os.path.join(f"{s_dir}/results", "original_data.csv"), index=False)
            self.scenario_id += 1
            self.reset_collected_data()
            return frame_span

        if frame_span != self.target_frames:
            return frame_span

        data_df = self.prepare_dataset(self.collected_data)

        scenario_dir = os.path.join(self.output_dir, f"{self.senaria_name}/{self.scenario_id}")
        os.makedirs(scenario_dir, exist_ok=True)
        os.makedirs(f"{scenario_dir}/results", exist_ok=True)
        data_df.to_csv(f"{scenario_dir}/data_df.csv", index=False)
        node_features_df = self.create_node_features(data_df)
        edge_features_df = self.create_edge_features(data_df, node_features_df, scenario_dir)
        all_edges_df = self.create_all_edges(edge_features_df)

        node_features_df.to_csv(f"{scenario_dir}/node_features.csv", index=False)
        edge_features_df.to_csv(f"{scenario_dir}/edge_features.csv", index=False)
        all_edges_df.to_csv(f"{scenario_dir}/all_edges.csv", index=False)

        splitDataset = dataProcessor(root_dir=scenario_dir, output_dir=scenario_dir, mask_node_num=self.neighbor_count)
        splitDataset.run()
        src_edg_df = edge_features_df[edge_features_df['src'] == 0]
        for dst, df_group in src_edg_df.groupby('dst'):
            theo = int(len (df_group) / 6)
            first_three = df_group[["vx", "vy"]].head(theo)
            if np.all(abs(first_three.values) < 1e-5):
                return frame_span

        trainer = TGANTrainer(data_dir=scenario_dir, output_dir=f"{scenario_dir}/results",batch_size = 64)

        df = trainer.eval()

        id_map = node_features_df.set_index("global_id")["agent_id"].to_dict()

        # 添加 src_agent_id 和 dst_agent_id 列
        df["src_agent_id"] = df["src"].map(id_map)
        df["dst_agent_id"] = df["dst"].map(id_map)

        df["frame_start"] = df.apply(
            lambda row: self.time_map.get((row["src"], row["dst"]), {}).get(row["ts"], {}).get("frame_start", -1),
            axis=1
        )

        df["frame_end"] = df.apply(
            lambda row: self.time_map.get((row["src"], row["dst"]), {}).get(row["ts"], {}).get("frame_end", -1),
            axis=1
        )

        # 打印最大得分行的信息
        max_score_row = df.loc[df["score"].idxmax()]

        if max_score_row["score"] > 0.8:
            print(
                f"{scenario_dir},"
                f"Collision Max score: {max_score_row['score']}, "
                f"Src: {max_score_row['src_agent_id']}, "
                f"Dst: {max_score_row['dst_agent_id']}, "
                f"ts: {max_score_row['ts']}, "
                f"Frame ID range: [{max_score_row['frame_start']}, {max_score_row['frame_end']}]"
            )

        df.to_csv(os.path.join(f"{scenario_dir}/results", "topk_dst_predictions.csv"), index=False)
        accident = 0
        # if max_score_row["score"] > 0.7:
        #     mx_ts = int(max_score_row["ts"])
        #     min_ts = int(df["ts"].min())
        #     if  mx_ts == min_ts:
        #         accident = 1
        return accident
