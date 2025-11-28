import os
import time
import carla


def main():
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    # world = client.get_world()
    # print("连接成功，当前地图为:", world.get_map().name)

    recording_file = os.path.abspath("results/records/MLMAS_LAV/RouteScenario_12_rep0.log")
    print("recording_file", recording_file)
    if not os.path.exists(recording_file):
        print(f"录制文件不存在: {recording_file}")
        return

    try:
        print("录制文件信息：")
        info = client.show_recorder_file_info(recording_file, show_all=False)

        client.set_replayer_time_factor(1.0)

        # 必须用位置参数
        client.replay_file(recording_file, 0.0, 0, 3298)
        # client.replay_file(recording_file, 0.0, 0.0, 0)
        time.sleep(10)  # 或根据文件时长调整

    except Exception as e:
        print("异常:", e)


if __name__ == '__main__':
    main()
