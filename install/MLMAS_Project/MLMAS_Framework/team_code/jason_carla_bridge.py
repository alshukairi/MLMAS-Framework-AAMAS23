import socket
import collections
import time
import threading
import json
import carla
import os
import enum
from os.path import exists
import pandas as pd

SERVER_HOST = os.getenv('BRIDGE_SERVER_IP')
SERVER_PORT = int(os.getenv('BRIDGE_SERVER_PORT'))

# Using enum class create enumerations
class AvailableIDs(enum.Enum):
    noAction = 0
    control = 1
    sensors = 2
    socketRestart = 3
    terminate = 4


class JasonCarlaBridge:
    def __init__(self, ml_mas_agent):
        self.q_server_to_jason = collections.deque(maxlen=100)
        self.q_jason_to_server =  collections.deque(maxlen=100)
        self.q_carla_to_server =  collections.deque(maxlen=100)

        self.SERVER_HOST = SERVER_HOST  # Standard loopback interface address (localhost)
        self.SERVER_PORT = SERVER_PORT  # Port to listen on (non-privileged ports are > 1023)

        self.json_processing = JsonProcessing(ml_mas_agent)
        # self.ml_model = MLModel()
        self.ml_mas_agent = ml_mas_agent
        self.s = None

        ##  availableThreads
        self.action_thread = None
        self.public_thread = None

    def start(self):

        try:
            self.action_thread = threading.Thread(target=self.action_executor, name="ActionExecutor")
            self.action_thread.do_run = True
            self.action_thread.start()

            self.public_thread = threading.Thread(target=self.public, name="Public")
            self.public_thread.do_run = True
            self.public_thread.start()

        except:
            self.action_thread.do_run = False
            self.public_thread.do_run = False
            self.s.close()

    def stop(self):
        try:

            if self.action_thread != None:
                self.action_thread.do_run = False
            if self.public_thread != None:
                self.public_thread.do_run = False

            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()
            self.s.close()


        except:
            if(self.action_thread != None):
                self.action_thread.do_run = False
            if(self.public_thread != None):
                self.public_thread.do_run = False
            if self.s != None:
                self.s.shutdown(socket.SHUT_RDWR)
                self.s.close()

    def public(self):
        t = threading.currentThread()
        print("[Public interface] is running")
        # self.s = None
        public_out_thread = None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.s:
            # self.s = s
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.bind((self.SERVER_HOST, self.SERVER_PORT))
            self.s.listen()
            while getattr(t, "do_run", True):
                try:
                    conn, addr = self.s.accept()
                    ##------ run public out thread
                    public_out_thread = threading.Thread(target=self.public_out, name="PublicOut",args=(conn,))
                    public_out_thread.do_run = True
                    public_out_thread.start()

                    with conn:
                        while getattr(t, "do_run", True):

                            data = conn.recv(1024)
                            if data:
                                self.q_jason_to_server.append(data.decode("utf-8"))
                            else:
                                self.CLIENT_HOST = ""
                                public_out_thread.do_run = False
                                break
                except:
                    pass
        if(public_out_thread != None):
            public_out_thread.do_run = False
        print("[Public interface] is stopped!!")

    def public_out(self, s):
        t = threading.currentThread()
        while getattr(t, "do_run", True):
            try:
                if self.q_server_to_jason:
                    jsn = self.q_server_to_jason.popleft()
                    ss = bytes(str(jsn)+"\n",encoding='UTF8')
                    s.sendall(ss)

                else:
                    time.sleep(0.01)
            except:
                    time.sleep(0.1)


    def action_executor(self):
        t = threading.currentThread()
        print("[Action Executor] is running")
        while getattr(t, "do_run", True):
            try:
                if self.q_jason_to_server:
                    jsn = self.q_jason_to_server.popleft()

                    final_json = json.loads(jsn)

                    if self.json_processing.apply_control(final_json):
                        pass
                    # elif self.ml_model.enable_model(final_json, carlaController):
                    #     pass


                if self.q_carla_to_server:
                    jsn = self.q_carla_to_server.popleft()
                    self.q_server_to_jason.append(jsn)

                if not self.q_carla_to_server and not self.q_jason_to_server:
                    time.sleep(0.01)

            except:
                time.sleep(0.1)

        print("[Action Executor] is stopped!!")

    def send_sensor_data(self):
        # print(self.json_processing.JSON_pack_sensors())
        self.q_server_to_jason.append(self.json_processing.JSON_pack_sensors())

    def send_socket_restart(self):
        # print(self.json_processing.JSON_pack_sensors())
        self.q_server_to_jason.append(self.json_processing.JSON_pack(name="socketRestart"))

    def JSON_pack(self):
        print("Pack JSON Data")

    def JSON_unpack(self):
            print("UnPack JSON Data")


class JsonProcessing:

    def __init__(self, ml_mas_agent):
        self.ml_mas_agent = ml_mas_agent
        self.metrics_stats = [0,0,0,0,0,0,0]
    def apply_control(self, jsn):
        cnt, repeat = self.JSON_unpack_control(jsn)
        if cnt == -1 or cnt != None:
            self.ml_mas_agent.jason_control_response(cnt, repeat)
            return True

        return False



# The following methods are used to store a csv file that
# will be used to report the statistical metrics
    def save_mas_metrics(self, total_frames, file_path):
        if exists(file_path) == False:
            metrics_f = open(file_path, 'w')
            metrics_f.write("total_frames;col_front;col_cross_far;col_cross_close;col_back;trf_go;trf_move;trf_slow_down\n")
            metrics_f.close()

        metrics_f = open(file_path, 'a')
        if total_frames > 0:
            metrics_f.write("%i;%.3f;%.3f;%.3f;%.3f;%.3f;%.3f;%.3f\n"%(total_frames,
                                                    self.metrics_stats[0]/total_frames,
                                                    self.metrics_stats[1]/total_frames,
                                                    self.metrics_stats[2]/total_frames,
                                                    self.metrics_stats[3]/total_frames,
                                                    self.metrics_stats[4]/total_frames,
                                                    self.metrics_stats[5]/total_frames,
                                                    self.metrics_stats[6]/total_frames
                                                                ))
        metrics_f.close()
        self.metrics_stats = [0,0,0,0,0,0,0]



    def JSON_unpack_control(self, final_json):
        if final_json['type']['id'] == AvailableIDs.noAction.value:
            return -1,0
        if(final_json['type']['id'] == AvailableIDs.control.value):
            #unpack the json data
            mT = int(final_json['data']['mT'])
            throttle = final_json['data']['throttle']
            steer = final_json['data']['steer']
            brake = final_json['data']['brake']
            hand_brake = final_json['data']['hand_brake']
            reverse = final_json['data']['reverse']
            repeat = final_json['data']['repeat']

            if mT >=0 and mT <= 6: self.metrics_stats[mT] += repeat

            return carla.VehicleControl(steer=float(steer),
                                        throttle=float(throttle),
                                        brake=float(brake),
                                        hand_brake = hand_brake,
                                        reverse = reverse
                                        ), repeat



        return None

    def JSON_pack_sensors(self):
        final_json = json.loads("{}")
        final_json["info"] = { "frame": self.ml_mas_agent.main_info[0],
                                "speed": self.ml_mas_agent.main_info[1]
                             }
        final_json["ml_control"] = {   "throttle": str(round(self.ml_mas_agent.ml_control.throttle,3)),
                                        "steer": str(round(self.ml_mas_agent.ml_control.steer,3)),
                                        "brake": str(round(self.ml_mas_agent.ml_control.brake,3)),
                                        "hand_brake": self.ml_mas_agent.ml_control.hand_brake,
                                        "reverse": self.ml_mas_agent.ml_control.reverse
                             }
        if self.ml_mas_agent.front_objects_detection != -1:
            final_json["f"] = { "x": str(round(self.ml_mas_agent.front_objects_detection[0],3)),
                                "y": str(round(self.ml_mas_agent.front_objects_detection[1],3)),
                                "min_x": str(round(self.ml_mas_agent.front_objects_detection[2],3)),
                                "min_y": str(round(self.ml_mas_agent.front_objects_detection[3],3))
                                 }
        if self.ml_mas_agent.SFront_objects_detection != -1:
            final_json["sF"] = { "x": str(round(self.ml_mas_agent.SFront_objects_detection[0],3)),
                                "y": str(round(self.ml_mas_agent.SFront_objects_detection[1],3)),
                                "min_x": str(round(self.ml_mas_agent.SFront_objects_detection[2],3)),
                                "min_y": str(round(self.ml_mas_agent.SFront_objects_detection[3],3))
                                 }
        if self.ml_mas_agent.back_objects_detection != -1:
            final_json["b"] = { "x": str(round(self.ml_mas_agent.back_objects_detection[0],3)),
                                "y": str(round(self.ml_mas_agent.back_objects_detection[1],3)),
                                "min_x": str(round(self.ml_mas_agent.back_objects_detection[2],3)),
                                "min_y": str(round(self.ml_mas_agent.back_objects_detection[3],3))
                                 }
        if self.ml_mas_agent.sBack_objects_detection != -1:
            final_json["sB"] = { "x": str(round(self.ml_mas_agent.sBack_objects_detection[0],3)),
                                "y": str(round(self.ml_mas_agent.sBack_objects_detection[1],3)),
                                "min_x": str(round(self.ml_mas_agent.sBack_objects_detection[2],3)),
                                "min_y": str(round(self.ml_mas_agent.sBack_objects_detection[3],3))
                                 }
        if self.ml_mas_agent.Left_objects_detection != -1:
            final_json["l"] = { "x": str(round(self.ml_mas_agent.Left_objects_detection[0],3)),
                                "y": str(round(self.ml_mas_agent.Left_objects_detection[1],3)),
                                "min_x": str(round(self.ml_mas_agent.Left_objects_detection[2],3)),
                                "min_y": str(round(self.ml_mas_agent.Left_objects_detection[3],3))
                                 }
        if self.ml_mas_agent.right_objects_detection != -1:
            final_json["r"] = { "x": str(round(self.ml_mas_agent.right_objects_detection[0],3)),
                                "y": str(round(self.ml_mas_agent.right_objects_detection[1],3)),
                                "min_x": str(round(self.ml_mas_agent.right_objects_detection[2],3)),
                                "min_y": str(round(self.ml_mas_agent.right_objects_detection[3],3))
                                 }

        if self.ml_mas_agent.traffic_light_detection != -1:
            final_json["traffic_light"] = {
                                "type": self.ml_mas_agent.traffic_light_detection[0],
                                "state": self.ml_mas_agent.traffic_light_detection[1],
                                "x": str(round(self.ml_mas_agent.traffic_light_detection[2],3)),
                                "y": str(round(self.ml_mas_agent.traffic_light_detection[3],3)),
                                "d": str(round(self.ml_mas_agent.traffic_light_detection[4],3)),
                                "inBox": (1 if self.ml_mas_agent.traffic_light_detection[5] else 0)
                                 }

        return self.JSON_pack(name="sensors", jsn= final_json)

    def JSON_pack(self, name, jsn = None):
        final_json = json.loads("{}")
        final_json["type"] =  {"id": AvailableIDs[name].value, "name": name}
        if(jsn != None):
            final_json["data"] = jsn
        return  json.dumps(final_json)
