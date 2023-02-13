
from jason_carla_bridge import JasonCarlaBridge
from agents.navigation.basic_agent import BasicAgent
from leaderboard.autoagents.autonomous_agent import AutonomousAgent
from agents.tools.misc import is_within_distance_ahead
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
import math
import os
import pandas as pd
import time


ml_agent = os.getenv('ML_MODEL')
result_file_path = (os.getenv('CHECKPOINT_ENDPOINT').replace(".json","") + "_jason_metrics.csv")

exec(open(ml_agent).read())
class_name = get_entry_point()
def get_entry_point():
    return 'MLMASAgent'

is_print_log_enabled = False  ## enable for # DEBUG
class MLMASAgent(AutonomousAgent):

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

    def run_step(self, input_data, timestamp):
        if self.ml_model._global_plan is None:
            self.ml_model._global_plan = self._global_plan
        if self._vehicle == None:
            self._vehicle = CarlaDataProvider.get_hero_actor()
            self.basic_agent = BasicAgent(self._vehicle)
            print(self._vehicle)
        #==== prepare sensors data to be sent to JASON
        self.num_frames += 1

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


        self.main_info = (self.num_frames, round(ego_vehicle_speed,3))
        self.lidar_df = self.preprocess(lidar)

        self.front_objects_detection = self.minimum_obstacle_distance()

        self.back_objects_detection = self.minimum_obstacle_distance(direction="B")

        self.SFront_objects_detection = self.minimum_obstacle_distance(direction="SF")

        self.sBack_objects_detection = self.minimum_obstacle_distance(direction="SB")

        self.Left_objects_detection = self.minimum_obstacle_distance(direction="L")

        self.right_objects_detection = self.minimum_obstacle_distance(direction="R")

        self.traffic_light_detection = self.check_traffic_lights()
        if self.traffic_light_detection != -1 and self.traffic_light_detection[0] == "A":
            self.ahead_traffic_light_distance = self.traffic_light_detection[4]


        self.ml_control = (self.ml_model.run_step(input_data, timestamp) if self.should_get_ml_control()
                            else carla.VehicleControl(steer=float(0.0),
                                                      throttle=float(0.0),
                                                       brake= float(1.0)) )
        if self.should_send_to_jason():
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
                or self.right_objects_detection != -1)

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

    def preprocess(self, lidar_xyzr, min_z = 0.7, max_z = 2,
     min_x = -5, max_x = 8,  min_y = -4, max_y = 4
                                , min_intensity = 0.8):
        intensity = lidar_xyzr[:,-1]
        x_offset = self.ego_car_diminsions.x/2
        x = lidar_xyzr[:,0] + self.lidar_dim[0]
        y = lidar_xyzr[:,1] + self.lidar_dim[1]
        z = lidar_xyzr[:,2] + self.lidar_dim[2]
        direction = np.array([self.points_direction(x1,y1) for x1,y1 in  lidar_xyzr[:,0:2]])

        final_df = pd.DataFrame({'x':x, 'y': y, 'z': z, #'distance': d,
                        'direction': direction, 'intensity': intensity})
        final_df = final_df[final_df.z > min_z]
        final_df = final_df[final_df.z < max_z]

        final_df = final_df[final_df.x > min_x - x_offset]
        final_df = final_df[final_df.x < max_x + x_offset]

        final_df = final_df[final_df.y > min_y]
        final_df = final_df[final_df.y < max_y]
        final_df = final_df[final_df.intensity > min_intensity]
        return final_df

    def points_direction(self, x,y):
        ## in front of the car with (~ -175 to 5 degree)
        if x > 0 and (abs(y)/x) <= 9.5: # > 6 degree
            return "F"

        ## in back of the car with (-45 to 45 degree)
        if x < 0 and (y/x) >= -1 and (y/x) <= 1:
            return "B"

        ## in left  of the car with (-45 to 45 degree)
        if y < 0 and (x/y) >= -1 and (x/y) <= 1:
            return "L"

        ## in right of the car with (-45 to 45 degree)
        if y > 0 and (x/y) >= -1 and (x/y) <= 1:
            return "R"
        return ""

    def minimum_obstacle_distance(self , direction = "F"):
        ## Filter lidar points by direction:
        ## F: front (45 degree) | SF: front (straight)
        ## B: Back (45 degree)  | SB: Back (straight)
        ## L: Left (45 degree)  | R: Right (45 degree)

        x_offset = self.ego_car_diminsions.x
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
            x = (x - x_offset) if x >= x_offset else (x + x_offset)
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
