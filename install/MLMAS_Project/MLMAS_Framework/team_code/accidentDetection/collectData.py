import math
import pandas as pd
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider

class AccidentDetection:
    def __init__(self, ego, world, collect_t=7, neighbors=5, target_t = 10):
        self.scenario_id = 0
        self.neighbor_count = neighbors
        self.fps = 20
        self.target_frames = collect_t * self.fps
        self.target_frames_end = target_t * self.fps
        self.ego = ego
        self.ego_location = ego.get_location()
        self.world = world
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
            "id": vehicle.id,
            "frame_id": round(frame_id, 3),
            "type": vehicle_type,
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

        ego_info = self.get_vehicle_info(self.ego, self.ego_location, self.world)

        all_vehicles = self.world.get_actors().filter("vehicle.*")
        neighbors = []
        for v in all_vehicles:
            if v.id != self.ego.id:
                neighbor = self.get_vehicle_info(v, self.ego_location, self.world)
                neighbors.append(neighbor)

        neighbors.sort(key=lambda x: x["rel_dist"])
        neighbors = neighbors[:self.neighbor_count]

        # 将 ego 和邻居都扁平化添加
        self.collected_data.append(ego_info)
        self.collected_data.extend(neighbors)

    def prepare_dataset(self):
        df = pd.DataFrame(self.collected_data)
        df = df[df["scenario_id"] == self.scenario_id]

        clear_cols = ["x", "y", "z", "vx", "vy", "yaw"]
        base_cols = ["id", "type", "l", "w", "h", "scenario_id"]
        padded_rows = []
        duration = self.target_frames_end - self.target_frames

        for vid in df["id"].unique():
            vehicle_data = df[df["id"] == vid].sort_values("frame_id")

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
        padded_df = padded_df.sort_values(by=["id", "frame_id"]).reset_index(drop=True)

        self.scenario_id += 1
        return padded_df
    def run(self):
        self.collect_one_frame()
        if len(self.collected_data) != self.target_frames:
            return
        data_df = self.prepare_dataset()
        train_df, self.split_dataset()

