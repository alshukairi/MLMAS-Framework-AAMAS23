
from jason_carla_bridge import JasonCarlaBridge
from agents.navigation.basic_agent import BasicAgent
from leaderboard.autoagents.autonomous_agent import AutonomousAgent

from agents.tools.misc import is_within_distance_ahead
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
import math
import os
import pandas as pd
import time
from  adModel.accidentDetection import accidentDetection
import numpy as np

ml_agent = os.getenv('ML_MODEL')
result_file_path = (os.getenv('CHECKPOINT_ENDPOINT').replace(".json","") + "_jason_metrics.csv")

exec(open(ml_agent).read())
class_name = get_entry_point()
def get_entry_point():
    return 'Orchestrator'

is_print_log_enabled = False  ## enable for # DEBUG
class Orchestrator(AutonomousAgent):

    def __init__(self, path_to_conf_file):
        ml_class = eval(class_name)
        self.ml_model = ml_class(path_to_conf_file)
        #  current global plans to reach a destination
        self.num_frames = 0
        self._global_plan_world_coord = self.ml_model._global_plan_world_coord

        # this data structure will contain all sensor data
        self.sensor_interface = self.ml_model.sensor_interface

        self.jason_carla_bridge = JasonCarlaBridge(self)
        # agent's initialization
        self.setup(path_to_conf_file)

        self.wallclock_t0 = self.ml_model.wallclock_t0
        self._vehicle = None
        self.ego_car_diminsions = None

        self._proximity_tlight_threshold = 10.0  # meters
        self._last_traffic_light = None
        self.is_tfl_x_dif_positive = None
        self.is_tfl_y_dif_positive = None
        self.is_box_x_dif_positive = None
        self.is_box_y_dif_positive = None

        self.is_control_responce_recieved = False
        self.prev_traffic_light_detection = -1
        self.control_repeat = 1
        self.ahead_traffic_light_distance = 0
        self.lidar_df = None
        self.accidentDetector = None
        self.slow = 0
        self.senaria_name_log = "UnknownScenario"
    def sensors(self):

        ## 1. get the required sinsors by the ML models
        ## 2. check if the framework required sensors (LiDAR and speedometer)
        ##    are exist and add them if not exists.

        sensors =  self.ml_model.sensors()

        sensors_pd = pd.DataFrame(sensors)
        lidar_dict =  sensors_pd[sensors_pd.type == 'sensor.lidar.ray_cast']

        if len(lidar_dict) > 0:
            self.lidar_dim = (float(lidar_dict.x.values[0]),
                              float(lidar_dict.y.values[0]),
                             float(lidar_dict.z.values[0]))
            self.lidar_id = lidar_dict.id.values[0]
            # print_log("(",self.lidar_id,") LiDAR is exist with dim:", self.lidar_dim)
        else:
            self.lidar_dim = (0.0, 0.0 , 2.4)
            self.lidar_id = "LIDAR"
            # Add LiDAR
            sensors.append({
                'type': 'sensor.lidar.ray_cast', 'x': self.lidar_dim[0], 'y': self.lidar_dim[1]
                , 'z': self.lidar_dim[2], 'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0,
                'id': self.lidar_id
            })
            # print_log("(",self.lidar_id,") LiDAR is added with dim:", self.lidar_dim)


        speedometer_dict =  sensors_pd[sensors_pd.type == 'sensor.speedometer']

        if len(speedometer_dict) > 0:
            self.speedometer_id = speedometer_dict.id.values[0]
            # print_log("(",self.speedometer_id,") speedometer is exist")
        else:
            self.speedometer_id = "EGO"
            # Add speedometer
            sensors.append({'type': 'sensor.speedometer', 'id': self.speedometer_id})
            # print_log("(",self.speedometer_id,") speedometer is added")


        return sensors

    def setup(self, path_to_conf_file):
        self.jason_carla_bridge.start()
        self.ml_model.setup(path_to_conf_file)
        self.track = self.ml_model.track

    def destroy(self):
        self.jason_carla_bridge.send_socket_restart()
        self.jason_carla_bridge.stop()

        self.jason_carla_bridge.json_processing.save_mas_metrics(total_frames = self.num_frames,
                                                                  file_path=result_file_path
                                                                 )
        self.ego_car_diminsions = None
        self._last_traffic_light = None
        self.num_frames = 1
        self.ml_model.destroy()
        self._vehicle = None
        self.accidentDetector = None

    def run_step(self, input_data, timestamp):
        if self.ml_model._global_plan is None:
            self.ml_model._global_plan = self._global_plan
        if self._vehicle == None:
            self._vehicle = CarlaDataProvider.get_hero_actor()
            self.basic_agent = BasicAgent(self._vehicle)
            print(self._vehicle)
        #==== prepare sensors data to be sent to JASON
        self.num_frames += 1

        if self.accidentDetector is None:
            self.accidentDetector = accidentDetection(
                ego=self._vehicle,
                world=CarlaDataProvider.get_world(),
                senaria_name=self.senaria_name_log,
            )
        accidentMark = 0
        accidentMark, probability, dangerous, debuge = self.accidentDetector.run()


        # print(len)

        # if self.num_frames < 2100:
        #     return self.ml_model.run_step(input_data, timestamp)
        self.control_repeat -= 1
        if (self.control_repeat > 0):
            return self.last_control

        # if self.num_frames < 250: # or self.num_frames == 1450:
        #     return self.ml_model.run_step(input_data, timestamp)
        _, lidar = input_data.get(self.lidar_id)
        _, ego   = input_data.get(self.speedometer_id)
        ego_vehicle_speed      = ego.get('speed')


        #========= Ego Vehicle info ===================
        if self.ego_car_diminsions == None:
            self.ego_car_diminsions = self._vehicle.bounding_box.extent
            # print_log(self.ego_car_diminsions)
        #==============================================
        # frames = (v / a) × FPS
        # distance = v² / (2a)
        sframes  = (ego_vehicle_speed / 8 ) * 20
        sdistance = (ego_vehicle_speed **2) / 16
        self.main_info = (self.num_frames, round(ego_vehicle_speed,3), int(sframes), round(sdistance,3))
        self.lidar_df = self.preprocess(lidar)
        # self.front_objects_detection = self.minimum_obstacle_distance()
        #
        # self.back_objects_detection = self.minimum_obstacle_distance(direction="B")
        #
        # self.SFront_objects_detection = self.minimum_obstacle_distance(direction="SF")
        #
        # self.sBack_objects_detection = self.minimum_obstacle_distance(direction="SB")
        #
        # self.Left_objects_detection = self.minimum_obstacle_distance(direction="L")
        #
        # self.right_objects_detection = self.minimum_obstacle_distance(direction="R")
        self.front_objects_detection = self.mlAlert_axis()
        self.back_objects_detection = self.mlAlert_axis(direction="B")
        self.SFront_objects_detection = self.mlAlert_axis(direction="SF")
        self.sBack_objects_detection = self.mlAlert_axis(direction="SB")
        self.Left_objects_detection = self.mlAlert_axis(direction="L")
        self.right_objects_detection = self.mlAlert_axis(direction="R")

        self.traffic_light_detection = self.check_traffic_lights()

        # print(f"dis_l : {self.Left_objects_detection}")
        # print(f"dis_b: {self.back_objects_detection}")
        # print(f"dis_sb: {self.sBack_objects_detection}")

        # print(f"l: {self.Left_objects_detection}, r: {self.right_objects_detection}")
        # print("-------")
        if accidentMark == 1:

            self.mlAlert = (accidentMark, probability, dangerous)
            if debuge == 1 :
                print(f"mlAlert: {probability}, {dangerous}")
                print(f"f: {self.front_objects_detection},r : {self.right_objects_detection},l : {self.Left_objects_detection}")

        else :
            self.mlAlert = -1

        ## X_offset : 2.5 Y_ofset : 1.1


        if self.traffic_light_detection != -1 and self.traffic_light_detection[0] == "A":
            self.ahead_traffic_light_distance = self.traffic_light_detection[4]


        self.ml_control = (self.ml_model.run_step(input_data, timestamp) if self.should_get_ml_control()
                            else carla.VehicleControl(steer=float(0.0),
                                                      throttle=float(0.0),
                                                       brake= float(1.0)) )

        jason_cond = self.should_send_to_jason()
        if jason_cond:
            cnt = self.send_sensor_data()
            if cnt != -1:
                return cnt

        return  self.ml_control #carla.VehicleControl(steer=control.steer, throttle=float(1.0), brake=control.brake)

    def should_get_ml_control(self):
        return self.should_send_to_jason() or (not (
                self.main_info[1] == 0
                and self.traffic_light_detection != -1
                and self.traffic_light_detection[0] == "A"
                and self.traffic_light_detection[1] == "R"
                ))

    def should_send_to_jason(self):
        cond = (self.front_objects_detection != -1
                or self.back_objects_detection != -1
                or self.sBack_objects_detection != -1
                or self.SFront_objects_detection != -1
                or self.Left_objects_detection != -1
                or self.right_objects_detection != -1
                or self.mlAlert != -1)

        # if ahead traffic light just send it once except if something change
        cond = cond or (
                        self.traffic_light_detection != -1
                        and (
                        (self.traffic_light_detection[0] == "L" and
                        (self.ahead_traffic_light_distance - self.traffic_light_detection[4]) > 8) # on the traffic light box
                        or self.traffic_light_detection[1] == "G" or
                        (self.prev_traffic_light_detection == -1
                        or self.prev_traffic_light_detection != self.traffic_light_detection)
                        )
                        )
        self.prev_traffic_light_detection = self.traffic_light_detection

        return cond

    def preprocess(self, lidar_xyzr,
                   min_z=0.7, max_z=2,
                   min_x=-8, max_x=8,
                   min_y=-5, max_y=5,
                   min_intensity=0.8):
        # if self.num_frames % 20 == 0:
        #     yaw = self._vehicle.get_transform().rotation.yaw
            # print("=== DEBUG START ===")
            # print("Vehicle yaw:", yaw)
            #
            # # 随便打印一点激光点 (原始 + 旋转后)
            # for i in range(5):
            #     xr, yr = lidar_xyzr[i, 0], lidar_xyzr[i, 1]
            #
            #     vehicle_yaw = math.radians(yaw)
            #     cos_y = math.cos(vehicle_yaw)
            #     sin_y = math.sin(vehicle_yaw)
            #
            #     xl = cos_y * xr + sin_y * yr
            #     yl = -sin_y * xr + cos_y * yr
            #
            #     print(f"[{i}] raw=({xr:.2f},{yr:.2f})  local=({xl:.2f},{yl:.2f})  dir={self.points_direction(xl, yl)}")
            #
            # print("=== DEBUG END ===")

        intensity = lidar_xyzr[:, -1]

        # 1. 获取车辆 yaw
        yaw = self._vehicle.get_transform().rotation.yaw
        vehicle_yaw = math.radians(yaw)
        cos_y = math.cos(vehicle_yaw)
        sin_y = math.sin(vehicle_yaw)

        # 2. LiDAR → Vehicle coordinate transformation
        # LiDAR

        z_raw = lidar_xyzr[:, 2]

        xr, yr = lidar_xyzr[:, 0], lidar_xyzr[:, 1]
        x_rot = cos_y * xr + sin_y * yr
        y_rot = -sin_y * xr + cos_y * yr
        # Z 不需要旋转，因为 yaw 不影响高度
        z_l = z_raw
        x_l = x_rot + self.lidar_dim[0]
        y_l = y_rot + self.lidar_dim[1]


        # 3. 使用车辆坐标来进行方向判断
        direction = np.array([self.points_direction(x, y) for x, y in zip(x_l, y_l)])

        # 4. 生成 dataframe（使用车辆坐标）
        final_df = pd.DataFrame({
            'x': x_l,
            'y': y_l,
            'z': z_l,
            'direction': direction,
            'intensity': intensity
        })

        # 5. 过滤高度
        final_df = final_df[(final_df.z > min_z) & (final_df.z < max_z)]

        # 6. 过滤 x,y 范围（车辆坐标）
        final_df = final_df[(final_df.x > min_x) & (final_df.x < max_x)]
        final_df = final_df[(final_df.y > min_y) & (final_df.y < max_y)]

        # 7. 过滤强度
        final_df = final_df[final_df.intensity > min_intensity]

        return final_df

    # def preprocess(self, lidar_xyzr, min_z = 0.7, max_z = 2,
    #  min_x = -8, max_x = 8,  min_y = -5, max_y = 5
    #                             , min_intensity = 0.8):
    #     intensity = lidar_xyzr[:,-1]
    #     x_offset = self.ego_car_diminsions.x
    #     x = lidar_xyzr[:,0] + self.lidar_dim[0]
    #     y = lidar_xyzr[:,1] + self.lidar_dim[1]
    #     z = lidar_xyzr[:,2] + self.lidar_dim[2]
    #
    #     direction = np.array([self.points_direction(x1,y1) for x1,y1 in  lidar_xyzr[:,0:2]])
    #
    #     final_df = pd.DataFrame({'x':x, 'y': y, 'z': z, #'distance': d,
    #                     'direction': direction, 'intensity': intensity})
    #     final_df = final_df[final_df.z > min_z]
    #     final_df = final_df[final_df.z < max_z]
    #
    #     final_df = final_df[final_df.x > min_x ]
    #     final_df = final_df[final_df.x < max_x ]
    #
    #     final_df = final_df[final_df.y > min_y]
    #     final_df = final_df[final_df.y < max_y]
    #     final_df = final_df[final_df.intensity > min_intensity]
    #     return final_df

    # def points_direction(self, x,y):
    #     ## in front of the car with (~ -175 to 5 degree)
    #     if x > 0 and (abs(y)/x) <= 9.5: # > 6 degree
    #         return "F"
    #
    #     ## in back of the car with (-45 to 45 degree)
    #     if x < 0 and (y/x) >= -1 and (y/x) <= 1:
    #         return "B"
    #
    #     ## in left  of the car with (-45 to 45 degree)
    #     if y < 0 and (x/y) >= -1 and (x/y) <= 1:
    #         return "L"
    #
    #     ## in right of the car with (-45 to 45 degree)
    #     if y > 0 and (x/y) >= -1 and (x/y) <= 1:
    #         return "R"
    #     return ""


    def points_direction(self, x, y):
        # self._vehicle.bounding_box.extent.x = 2.4508416652679443
        # self._vehicle.bounding_box.extent.y = 1.0641621351242065
        # diag_angle = math.degrees(math.atan2(1.0641621351242065,2.4508416652679443)) = 23.3
        # side_angle = 180 - diag_angle = 156.7
        angle = math.degrees(math.atan2(y, x))  # -180 to +180

        if -45 <= angle <= 45:
            return "F"
        if 45 < angle <= 135:
            return "L"
        if angle > 135 or angle < -135:
            return "B"
        if -135 <= angle < -45:
            return "R"

        return ""

    # def points_direction(self, x, y):
    #     angle = math.degrees(math.atan2(y, x))  # -180 to 180
    #
    #     # CARLA vehicle coordinate:
    #     # x > 0 front
    #     # x < 0 back
    #     # y > 0 right
    #     # y < 0 left
    #
    #     # 车辆前方 ±23°
    #     if -23.3 <= angle <= 23.3:
    #         return "F"
    #
    #     # 车辆右侧 (+23° → +156°)
    #     if 23.3 < angle <= 156.7:
    #         return "R"
    #
    #     # 车辆后方 (>|156°|)
    #     if angle > 156.7 or angle < -156.7:
    #         return "B"
    #
    #     # 车辆左侧 (-156.7° → -23.3°)
    #     if -156.7 <= angle < -23.3:
    #         return "L"
    #
    #     return ""

    def mlAlert_axis(self, direction="F"):

        df = self.lidar_df

        if direction == "F":  # 前方：x > 0
            sub = df[df.x > 0]
            if len(sub) == 0:
                return -1

            p = sub.loc[sub.x.idxmin()]  # 最靠前
            # f =  sub.loc[sub.x.idxmax()]
            # p_distance = math.sqrt(p.x * p.x + p.y * p.y)
            # f_distance = math.sqrt(f.x * f.x + f.y * f.y)
            #
            # print(f"p.x {p.x}, p.y {p.y}, pd {p_distance}, f.x {f.x}, f.y {f.y}, fd{f_distance}")

            return (p.x, p.y, abs(p.x), abs(p.y))

        if direction == "B":  # 后方：x < 0
            sub = df[df.x < 0]
            sub = df[df.x < 0]
            if len(sub) == 0:
                return -1
            p = sub.loc[sub.x.idxmax()]  # 最靠后（x 最大负值）
            return (p.x, p.y, abs(p.x), abs(p.y))

        if direction == "L":  # 左侧：y > 0
            sub = df[df.y > 0]
            if len(sub) == 0:
                return -1
            p = sub.loc[sub.y.idxmin()]  # y 最小的正值（最靠近车辆左侧）
            return (p.x, p.y, abs(p.x), abs(p.y))

        if direction == "R":  # 右侧：y < 0
            sub = df[df.y < 0]
            if len(sub) == 0:
                return -1
            p = sub.loc[sub.y.idxmax()]  # y 最大的负值（最靠近车辆右侧）
            return (p.x, p.y, abs(p.x), abs(p.y))

        # SF: straight front 又是前方且 |y|<lane_width
        if direction == "SF":
            sub = df[(df.x > 0) & (abs(df.y) < 2.12)]
            if len(sub) == 0:
                return -1
            p = sub.loc[sub.x.idxmin()]
            return (p.x, p.y, abs(p.x), abs(p.y))

        # SB: straight back 又是后方且 |y|<lane_width
        if direction == "SB":
            sub = df[(df.x < 0) & (abs(df.y) < 2.12)]
            if len(sub) == 0:
                return -1
            p = sub.loc[sub.x.idxmax()]
            return (p.x, p.y, abs(p.x), abs(p.y))

        return -1

    def minimum_obstacle_distance(self , direction = "F"):
        ## Filter lidar points by direction:
        ## F: front (45 degree) | SF: front (straight)
        ## B: Back (45 degree)  | SB: Back (straight)
        ## L: Left (45 degree)  | R: Right (45 degree)
        ## X_offset : 2.5 Y_ofset : 1.1
        x_offset = self.ego_car_diminsions.x
        # y_offset = self.ego_car_diminsions.y
        # print(x_offset,y_offset)
        ## filter the lidars data
        if direction == "SF":
            final_df = self.lidar_df[self.lidar_df.x > x_offset]
            final_df = final_df[abs(final_df.y) < 1.5]
        elif direction == "SB":
            x_offset = self.ego_car_diminsions.x
            final_df = self.lidar_df[self.lidar_df.x < (0-x_offset)]
            final_df = final_df[abs(final_df.y) < 1.5] ## lane standard width is 3.65m

        else:
            final_df = self.lidar_df[self.lidar_df.direction == direction]

        # if(direction == "R" or direction == "L"):
        #     final_df = final_df[final_df.y.abs() < (max_distance)]
        if  direction == "F":
            # final_df = final_df[final_df.x.abs() < (max_distance + x_offset)]
            final_df = final_df[final_df.x > (x_offset)]
        if  direction == "B":
            # final_df = final_df[final_df.x.abs() < (max_distance + x_offset)]
            final_df = final_df[final_df.x < (0-x_offset)]
        # else:
        #      final_df[final_df.x.abs() < (max_distance + 2)]
        # if  direction == "F":
        #     # final_df = final_df[final_df.x.abs() < (max_distance + x_offset)]
        #     final_df = final_df[final_df.x > (x_offset)]

        if len(final_df) > 0:
            # ds = [distance(x,y) for x,y in final_df[["x","y"]].values]
            min_x = min(final_df.x.abs())
            y = final_df[final_df.x.abs() == min_x].y.values[0]
            min_y = min(final_df.y.abs())
            x = final_df[final_df.y.abs() == min_y].x.values[0]
            # x = (x - x_offset) if x >= x_offset else (x + x_offset)
            return (x, y ,min_x - x_offset , min_y) # min(final_df.y.abs()), min(ds))
        return -1

    def check_traffic_lights(self):
        traffic_light_list = self.basic_agent._world.get_actors().filter("*traffic_light*")
        light_state, traffic_light = self._is_at_traffic_light(traffic_light_list)
        if light_state:
            self._last_traffic_light = traffic_light
            trfc_loc = self._last_traffic_light.get_transform().location
            ego_loc = self._vehicle.get_transform().location
            trfc_distance = distance((ego_loc.x - trfc_loc.x),(ego_loc.y - trfc_loc.y))
            traffic_light_detection = ("A", trafic_light_states(self._last_traffic_light.state),
                           (abs(ego_loc.x) - abs(trfc_loc.x)), (abs(ego_loc.y) - abs(trfc_loc.y)),
                           trfc_distance, False)
            self.is_tfl_x_dif_positive = traffic_light_detection[2] >= 0
            self.is_tfl_y_dif_positive = traffic_light_detection[3] >= 0

            return traffic_light_detection
        elif self._last_traffic_light != None:
            trfc_loc = self._last_traffic_light.get_transform().location
            ego_loc = self._vehicle.get_transform().location

            trfc_distance = distance((ego_loc.x - trfc_loc.x),(ego_loc.y - trfc_loc.y))
            traffic_light_detection = ("L", trafic_light_states(self._last_traffic_light.state),
                                       (abs(ego_loc.x) - abs(trfc_loc.x)),
                                       (abs(ego_loc.y) - abs(trfc_loc.y)),
                                       trfc_distance, self.is_in_traffic_light_box())
            cancel_threshold = 40 ## meter
            if (trfc_distance > cancel_threshold or
            max(abs(traffic_light_detection[2]),abs(traffic_light_detection[3])) > cancel_threshold
            or (traffic_light_detection[2] >= 0) != self.is_tfl_x_dif_positive
            or (traffic_light_detection[3] >= 0) != self.is_tfl_y_dif_positive): ## we are not close to the traffic area
                self._last_traffic_light = None
                # traffic_light_detection[5] = False


            return traffic_light_detection
        return -1

    def is_in_traffic_light_box(self):
        traffic_light_group = self._last_traffic_light.get_group_traffic_lights()
        x = []
        y = []
        for tf in traffic_light_group:
            x.append(tf.get_transform().location.x)
            y.append(tf.get_transform().location.y)
        ego_loc = self._vehicle.get_transform().location
        return (ego_loc.x > min(x) and ego_loc.x < max(x)
                and ego_loc.y > min(y) and ego_loc.y < max(y))

    def _is_at_traffic_light(self, lights_list):
        """
        Method to check if there is a red light affecting us. This version of
        the method is compatible with both European and US style traffic lights.

        :param lights_list: list containing TrafficLight objects
        :return: a tuple given by (bool_flag, traffic_light), where
                 - bool_flag is True if there is a traffic light in RED
                   affecting us and False otherwise
                 - traffic_light is the object itself or None if there is no
                   red traffic light affecting us
        """
        ego_vehicle_location = self._vehicle.get_location()
        ego_vehicle_waypoint = self.basic_agent._map.get_waypoint(ego_vehicle_location)

        for traffic_light in lights_list:
            object_location = self.basic_agent._get_trafficlight_trigger_location(traffic_light)
            object_waypoint = self.basic_agent._map.get_waypoint(object_location)

            if object_waypoint.road_id != ego_vehicle_waypoint.road_id:
                continue

            ve_dir = ego_vehicle_waypoint.transform.get_forward_vector()
            wp_dir = object_waypoint.transform.get_forward_vector()
            dot_ve_wp = ve_dir.x * wp_dir.x + ve_dir.y * wp_dir.y + ve_dir.z * wp_dir.z

            if dot_ve_wp < 0:
                continue

            if is_within_distance_ahead(object_waypoint.transform,
                                        self._vehicle.get_transform(),
                                        self._proximity_tlight_threshold):

                                        return (True, traffic_light)

        return (False, None)

    def send_sensor_data(self):

        self.is_control_responce_recieved = False
        self.jason_carla_bridge.send_sensor_data()
        # print("Send msg")
        sleep_time = 0.1
        time_out = 5 ## sec
        i = 0
        max_count = int(time_out/sleep_time)
        while self.is_control_responce_recieved == False:
            time.sleep(sleep_time)
            i += 1
            if i >= max_count:
                print("Jason Agent is disconnected!!")
                return -1
        # print(self.last_control)
        return self.last_control

    def jason_control_response(self, control, repeat):
        # print("Control Recieved")
        if (self.control_repeat < 1):
            self.last_control = control
            self.control_repeat = repeat
        self.is_control_responce_recieved = True

## calculate the 2d geomatric distance
def distance(x,y):
    total = x**2 + y**2
    return round(math.sqrt(total),1)

def trafic_light_states(state):
    if state == carla.TrafficLightState.Red:
        return "R"
    elif state == carla.TrafficLightState.Yellow:
        return "Y"
    elif state == carla.TrafficLightState.Green:
        return "G"
    return ""



def print_log(*arguments):
    if is_print_log_enabled:
        print(arguments)
