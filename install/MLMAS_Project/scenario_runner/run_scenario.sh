#!/bin/bash

export CARLA_ROOT=/home/hilalss/work/CARLA_0.9.10.1
export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
export PYTHONPATH=$PYTHONPATH:leaderboard
export PYTHONPATH=$PYTHONPATH:leaderboard/team_code
export PYTHONPATH=$PYTHONPATH:scenario_runner

export LEADERBOARD_ROOT=leaderboard
export SCENARIO_RUNNER_ROOT=/home/hilalss/work/LAV/scenario_runner

export CHALLENGE_TRACK_CODENAME=SENSORS
export PORT=2000 # same as the carla server port
export TM_PORT=8000 # port for traffic manager, required when spawning multiple servers/clients
export DEBUG_CHALLENGE=0
export REPETITIONS=1 # multiple evaluation runs
export ROUTES=leaderboard/data/validation_routes/routs_failure.xml
# export TEAM_AGENT=leaderboard/team_code/auto_pilot.py # agent
export TEAM_AGENT=/home/hilalss/work/LAV/team_code/lav_agent.py
# export TEAM_CONFIG=aim/log/aim_ckpt # model checkpoint, not required for expert
export TEAM_CONFIG=/home/hilalss/work/LAV/team_code/config.yaml
export CHECKPOINT_ENDPOINT=results/sample_result.json # results file
export SCENARIOS=leaderboard/data/scenarios/no_scenarios.json
export SAVE_PATH=data/expert # path for saving episodes while evaluating
export RESUME=True

python3 ${SCENARIO_RUNNER_ROOT}/scenario_runner.py \
--scenarios=${SCENARIOS}  \
--routes=${ROUTES} \
--repetitions=${REPETITIONS} \
--track=${CHALLENGE_TRACK_CODENAME} \
--checkpoint=${CHECKPOINT_ENDPOINT} \
--agent=${TEAM_AGENT} \
--agent-config=${TEAM_CONFIG} \
--port=${PORT} \
--trafficManagerPort=${TM_PORT}
