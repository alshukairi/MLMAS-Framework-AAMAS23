#!/bin/bash
# ./CARLA_0.9.10.1/CarlaUE4.sh --vulkan -windowed -ResX=1280 -ResY=720
# ./reply.sh               

ulimit -s unlimited
source MLMAS_Framework/config_LAV.sh

export CARLA_ROOT=CARLA_0.9.10.1
export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
export PYTHONPATH=$PYTHONPATH:leaderboard
export PYTHONPATH=$PYTHONPATH:MLMAS_Framework/team_code
export PYTHONPATH=$PYTHONPATH:MLMAS_Framework/team_code/adModel
export PYTHONPATH=$PYTHONPATH:MLMAS_Framework/team_code/adModel/models
export PYTHONPATH=$PYTHONPATH:scenario_runner

export LEADERBOARD_ROOT=leaderboard
export CHALLENGE_TRACK_CODENAME=SENSORS
export PORT=2000 # same as the carla server port
export TM_PORT=8000 # port for traffic manager, required when spawning multiple servers/clients
export DEBUG_CHALLENGE=0
export REPETITIONS=1 # multiple evaluation runs

export TEAM_AGENT=MLMAS_Framework/team_code/Orchestrator.py



export RESUME=True

#python scenario_runner/scenario_runner.py --replay ./results/records/MLMAS_LAV/RouteScenario_11_rep0.log
#${CARLA_ROOT}/CarlaUE4.sh -carla-port=2000 -recorder-replay=./results/records/MLMAS_LAV/RouteScenario_11_rep0.log
#python trasform_reply.py
python replay_record.py
