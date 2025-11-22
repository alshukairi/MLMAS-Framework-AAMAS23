import os
import pandas as pd
import numpy as np
import math
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider

from adModel.models.dataProcessor import dataProcessor
from adModel.models.TGANTrainer import TGANTrainer
import itertools
from vehicle_types import vehicle_type_mapping
import copy

class accidentDetection:
    def __init__(self, ego, world,senaria_name, collect_t = 6, neighbors=2, target_t=8, bias_power = 1.0, output_dir = "/home/jamie/MLMAS-Framework-AAMAS23/install/MLMAS_Project/output"):
        self.scenario_id = 0
        self.neighbor_count = neighbors
        self.fps = 2
        self.s_t = collect_t
        self.pre_t = collect_t + 1
        self.e_t = target_t
        self.target_frames_start = collect_t * self.fps -1
        self.target_frames_end = target_t * self.fps -1
        self.size_completeness = (self.target_frames_end + 1) * self.neighbor_count
        self.ego = ego
        self.world = world
        self.ego_new_id = None
        self.output_dir = output_dir
        self.collected_data = []
        self.fixed_neighbors = None
        self.fixed_fake_neighbors = None
        self.record_collected_data = []
        self.record_fixed_neighbors = None
        self.record_fixed_fake_neighbors = None
        self.record_scenario_id = 0
        self.time_map = {}
        self.senaria_name = senaria_name
        self.bias_power = bias_power
        self.predict_id = 0
        # world = CarlaDataProvider.get_world()

    def reset_collected_data(self):
        self.collected_data = []
        self.fixed_neighbors = None
        self.fixed_fake_neighbors = None

    def get_actor_info(self, actor, ego_location, sign):
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
        dst_x = location.x
        dst_y = location.y
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
        l_dst = dimensions[0]
        w_dst = dimensions[1]
        h_dst = dimensions[2]
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
            "frame_id": int(frame_id),
            "type_encoded": type_encoded,
            "sign": int(sign), # sign == 1 : ego, sign == 2 : positive target, sign == 3 : fake target.
            "l": l_dst,
            "w": w_dst,
            "h": h_dst,
            "x": dst_x,
            "y": dst_y,
            "z": location.z,
            "vx": velocity.x,
            "vy": velocity.y,
            "yaw": dst_yaw,
            "rel_dis": distance,
            "m_proj": m_proj,
        }


    def collect_one_frame(self, collected_data, fixed_neighbors, fixed_fake_neighbors):
        ego_location = self.ego.get_location()
        ego_info = self.get_actor_info(self.ego, ego_location, 1)

        vehicles = self.world.get_actors().filter("vehicle.*")
        walkers = self.world.get_actors().filter("walker.pedestrian.*")
        all_actors = list(vehicles) + list(walkers)

        if fixed_neighbors is None:
            vehicle_infos = []
            for v in all_actors:
                if v.id != self.ego.id:
                    vehicle_infos.append(self.get_actor_info(v, ego_location, 0))

            # sort by distance
            vehicle_infos.sort(key=lambda x: x["m_proj"])

            # Step 1: take nearest N first
            nearest_N = vehicle_infos[:self.neighbor_count]

            # Step 2: now filter out those >= 17
            selected = [info for info in nearest_N if info["m_proj"] < 17]
            if not selected:
                return 0
            # Build neighbor dictionary
            fixed_neighbors = {info["agent_id"]: -1 for info in selected}

            # farthest one
            farthest = vehicle_infos[-1]
            fixed_fake_neighbors = {farthest["agent_id"]: -1}
            self.fixed_neighbors = fixed_neighbors
            self.fixed_fake_neighbors = fixed_fake_neighbors

        neighbor_infos = []

        # track whether fake neighbor is found
        fake_id = list(fixed_fake_neighbors.keys())[0]
        fake_found = False

        for v in all_actors:
            if v.id in fixed_neighbors:
                neighbor_infos.append(self.get_actor_info(v, ego_location, 2))
            # elif v.id == fake_id:
            #     neighbor_infos.append(self.get_actor_info(v, ego_location, 3))


        frame_data = [ego_info] + neighbor_infos
        collected_data.append(frame_data)
        return 1

    def prepare_dataset(self, collected_data):

        flat_data = [agent for frame in collected_data for agent in frame]
        df = pd.DataFrame(flat_data)
        df = df[df["scenario_id"] == self.scenario_id]
        last_frame = 0
        first_frame = 0
        clear_cols = ["x", "y", "z", "vx", "vy", "yaw"]
        base_cols = ["agent_id", "type_encoded", "l", "w", "h", "scenario_id" , "sign"]

        padded_rows = []
        duration = self.target_frames_end - self.target_frames_start
        for vid in df["agent_id"].unique():
            vehicle_data = df[df["agent_id"] == vid].sort_values("frame_id")

            if vehicle_data["frame_id"].nunique() > self.target_frames_start:
                last_row = vehicle_data.iloc[-1]
                last_frame = last_row["frame_id"]
                first_row = vehicle_data.iloc[0]
                first_frame = first_row["frame_id"]
                for i in range(1, duration + 1 ):
                    new_row = {col: last_row[col] for col in base_cols}
                    new_row["frame_id"] = last_frame + i

                    for col in clear_cols:
                        new_row[col] = 0

                    padded_rows.append(new_row)

        # 拼接补齐数据并排序
        padded_df = pd.concat([df, pd.DataFrame(padded_rows)], ignore_index=True)
        padded_df = padded_df.sort_values(by=["agent_id", "frame_id"]).reset_index(drop=True)

        return padded_df, first_frame, last_frame

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


    def create_edge_features(self, or_data_df,node_features_df, scenario_dir,last_row):
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
            node_info = frame_nodes.set_index("global_id")[["vx", "vy", "yaw","sign"]].to_dict("index")

            # 有序配对（不含自环）
            for src, dst in itertools.permutations(node_ids, 2):
                src_info = node_info[src]
                dst_info = node_info[dst]
                # print(f"src sign = {src_info['sign']}, dst sign = {dst_info['sign']} , src = {src}, ego_new_id = {self.ego_new_id}")
                edge_rows.append({
                    "src": src,
                    "dst": dst,
                    "frame_id": frame_id,
                    "sign" : dst_info["sign"] if src == self.ego_new_id else 0,
                    "rel_dis":  rel_dists[dst],
                    "m_proj": m_proj_dists[dst],
                    "vx": src_info["vx"] - dst_info["vx"],
                    "vy": src_info["vy"]  - dst_info["vy"],
                    "yaw": src_info["yaw"] - dst_info["yaw"],
                    "ego":  1 if src == self.ego_new_id else 0

                })
        # print("edge_rows length:", len(edge_rows))
        # if edge_rows:
        #     print("sample row:", edge_rows[0].keys())

        edge_df = pd.DataFrame(edge_rows).sort_values("frame_id").reset_index(drop=True)

        result_list = []

        # 针对每个 (src, dst) 单独采样
        for (src, dst), group in edge_df.groupby(["src", "dst"]):
            group = group.sort_values("frame_id").reset_index(drop=True)

            # ---- Step 1: 提取关键帧区间 ----
            first_frame = edge_df["frame_id"].min()

            max_frame = edge_df["frame_id"].max()

            # ---- Step 2: 分区间 ----
            edge_df = edge_df.sort_values("frame_id").reset_index(drop=True)
            mask_first = (edge_df["frame_id"] >= first_frame) & (edge_df["frame_id"] <= last_row)
            mask_second = (edge_df["frame_id"] > last_row) & (edge_df["frame_id"] <= max_frame)

            first_section = edge_df.loc[mask_first].copy()
            second_section = edge_df.loc[mask_second].copy()

            # ---- Step 3: 第一段（偏重采样）----
            num_segments = self.s_t
            bias_power = float(self.bias_power)

            if len(first_section) > 0:
                weights = 1 - (1 - np.linspace(0, 1, num_segments)) ** bias_power
                sample_frames_first = first_section["frame_id"].min() + \
                                      (first_section["frame_id"].max() - first_section["frame_id"].min()) * weights
                sample_frames_first = np.unique(sample_frames_first.astype(int))
            else:
                sample_frames_first = np.array([])

            # ---- Step 4: 第二段（均匀采样）----
            if len(second_section) > 0:
                sample_frames_second = np.linspace(
                    second_section["frame_id"].min(),
                    second_section["frame_id"].max(),
                    num_segments,
                    dtype=int
                )
            else:
                sample_frames_second = np.array([])

            # ---- Step 5: 合并采样帧并赋予 time ----
            sample_frames = np.concatenate([sample_frames_first, sample_frames_second])
            sample_frames = np.unique(np.clip(sample_frames, first_frame, max_frame))

            # 取出对应行
            sample_df = group[group["frame_id"].isin(sample_frames)].copy()
            sample_df = sample_df.sort_values("frame_id").reset_index(drop=True)
            sample_df["time"] = np.arange(1, len(sample_df) + 1)
            sample_df["src"] = src
            sample_df["dst"] = dst

            result_list.append(sample_df)

        # 合并所有边的采样结果
        first_df = pd.concat(result_list, ignore_index=True)

        # 检查每条边的时间长度
        time_max_by_pair = first_df.groupby(["src", "dst"])["time"].max()
        if (time_max_by_pair < self.e_t).any():
            print(f"Error : {scenario_dir}")

        return first_df

    def create_all_edges(self,edge_df):
        return edge_df[["src", "dst"]].drop_duplicates().reset_index(drop=True)

    def run(self):

        colle = self.collect_one_frame(self.collected_data, self.fixed_neighbors, self.fixed_fake_neighbors)
        if colle == 0 :
            return 0, 0, 0
        record_frame_span = 0
        if self.record_collected_data:
            self.collect_one_frame(self.record_collected_data, self.record_fixed_neighbors, self.record_fixed_fake_neighbors)
            record_frame_ids = [frame[0]["frame_id"] for frame in self.record_collected_data]
            record_frame_span = record_frame_ids[-1] - record_frame_ids[0]

        # 检查 frame_id 的跨度是否达到目标帧数
        if len(self.collected_data) < 2:
            return 0, 0, 0

        ego_frame_ids = [frame[0]["frame_id"] for frame in self.collected_data]
        frame_span = ego_frame_ids[-1] - ego_frame_ids[0]


        if record_frame_span == self.target_frames_end:
            s_dir = os.path.join(self.output_dir, f"{self.senaria_name}/{self.record_scenario_id}")
            flat_data = [agent for frame in self.record_collected_data for agent in frame]
            all_df = pd.DataFrame(flat_data)
            all_df = all_df.sort_values(by=["agent_id", "frame_id"]).reset_index(drop=True)
            all_df.to_csv(os.path.join(f"{s_dir}/results", "original_data.csv"), index=False)

            self.record_collected_data = []
            self.record_fixed_neighbors = None
            self.record_fixed_fake_neighbors = None
            self.record_scenario_id = None


        if frame_span != self.target_frames_start:
            return 0, 0, 0

        ego_id = self.ego.id

        data_df, first_frame,last_frame = self.prepare_dataset(self.collected_data)
        
        if len(data_df) < self.size_completeness:
            # print(len(data_df))
            # print(self.size_completeness)
            self.reset_collected_data()
            return 0, 0, 0

        src_edg_df = data_df[data_df['agent_id'] == ego_id]

        theo = int(len(src_edg_df) / 2)
        first_three = src_edg_df[["vx", "vy"]].head(theo)
        if np.all(abs(first_three.values) < 1e-5):
            self.reset_collected_data()
            return 0, 0, 0

        # fake_id = list(self.fixed_fake_neighbors.keys())[0]
        # constraint_df = data_df[
        #     (data_df['frame_id'] == first_frame) &
        #     (data_df['agent_id'] != ego_id) &
        #     (data_df['agent_id'] != fake_id)
        # ][['agent_id', 'm_proj']]
        #
        # mask = (constraint_df['m_proj'] <= 17.0) # & (last_dis_df['m_proj'] >= 1.0)
        # keep_ids = set(constraint_df.loc[mask, 'agent_id'])
        #
        # if len(keep_ids) == 0:
        #     self.reset_collected_data()
        #     return 0
        # keep_ids.add(ego_id)
        # keep_ids.add(fake_id)
        # new_df = data_df[data_df['agent_id'].isin(keep_ids)]
        # if new_df.empty:
        #     self.reset_collected_data()
        #     return 0

        self.record_collected_data = copy.deepcopy(self.collected_data)
        self.record_fixed_neighbors = copy.deepcopy(self.fixed_neighbors)
        self.record_fixed_fake_neighbors = copy.deepcopy(self.fixed_fake_neighbors)
        self.record_scenario_id = self.scenario_id

        scenario_dir = os.path.join(self.output_dir, f"{self.senaria_name}/{self.scenario_id}")
        os.makedirs(scenario_dir, exist_ok=True)
        os.makedirs(f"{scenario_dir}/results", exist_ok=True)
        # new_df.to_csv(f"{scenario_dir}/data_df.csv", index=False)
        # node_features_df = self.create_node_features(new_df)
        data_df.to_csv(f"{scenario_dir}/data_df.csv", index=False)
        node_features_df = self.create_node_features(data_df)

        # edge_features_df = self.create_edge_features(new_df, node_features_df, scenario_dir, last_frame)
        edge_features_df = self.create_edge_features(data_df, node_features_df, scenario_dir, last_frame)
        all_edges_df = self.create_all_edges(edge_features_df)

        node_features_df.to_csv(f"{scenario_dir}/node_features.csv", index=False)
        edge_features_df.to_csv(f"{scenario_dir}/edge_features.csv", index=False)
        all_edges_df.to_csv(f"{scenario_dir}/all_edges.csv", index=False)

        splitDataset = dataProcessor(root_dir=scenario_dir, output_dir=scenario_dir, mask_node_num=self.neighbor_count, pre_t=self.pre_t, tar_t = self.e_t)
        splitDataset.run()


        self.reset_collected_data()
        self.scenario_id += 1
        trainer = TGANTrainer(data_dir=scenario_dir, output_dir=f"{scenario_dir}/results",batch_size = 64)

        df = trainer.eval()

        id_map = node_features_df.set_index("global_id")["agent_id"].to_dict()

        # 添加 src_agent_id 和 dst_agent_id 列

        df["src_agent_id"] = df["src"].map(id_map)
        df["dst_agent_id"] = df["dst"].map(id_map)

        # df["frame_start"] = df.apply(
        #     lambda row: self.time_map.get((row["src"], row["dst"]), {}).get(row["ts"], {}).get("frame_start", -1),
        #     axis=1
        # )
        #
        # df["frame_end"] = df.apply(
        #     lambda row: self.time_map.get((row["src"], row["dst"]), {}).get(row["ts"], {}).get("frame_end", -1),
        #     axis=1
        # )

        # 打印最大得分行的信息
        # subset = df[df["ts"] == self.pre_t]
        # max_score_row = subset.loc[subset["score"].idxmax()]
        max_score_row = df.loc[df["score"].idxmax()]
        # if max_score_row["score"] > 0.6:
        #     print(
        #         f"{scenario_dir},"
        #         f"Collision Max score: {max_score_row['score']}, "
        #         f"Src: {max_score_row['src_agent_id']}, "
        #         f"Dst: {max_score_row['dst_agent_id']}, "
        #         f"ts: {max_score_row['ts']}, "
        #         f"Frame ID range: [{max_score_row['frame_start']}, {max_score_row['frame_end']}]"
        #     )

        df.to_csv(os.path.join(f"{scenario_dir}/results", "topk_dst_predictions.csv"), index=False)
        accident = 0
        probability = 0
        dangerous = 0
        # print("slow Down : ")
        # print(
        #     f"Scenario: {self.scenario_id},"
        #     f"ts: {max_score_row['ts']}, "
        #     f"Collision Max score: {max_score_row['score']}, "
        #     f"Dst: {max_score_row['dst_agent_id']}, "
        #     f"Src: {max_score_row['src_agent_id']}, "
        # )
        if max_score_row["score"] >=  0.6:
            print("slow Down : ")
            print(
                f"{scenario_dir},"
                f"Collision Max score: {max_score_row['score']}, "
                f"Src: {max_score_row['src_agent_id']}, "
                f"Dst: {max_score_row['dst_agent_id']}, "
                f"ts: {max_score_row['ts']}, "
                # f"Frame ID range: [{max_score_row['frame_start']}, {max_score_row['frame_end']}]"
            )
            accident = 1
            probability = max_score_row["score"]
            if self.predict_id == max_score_row['dst_agent_id']:
                dangerous = 1
            self.predict_id = max_score_row['dst_agent_id']
        return accident, probability, dangerous
