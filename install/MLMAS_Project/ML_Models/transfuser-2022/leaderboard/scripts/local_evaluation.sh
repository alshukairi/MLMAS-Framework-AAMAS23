export CARLA_ROOT=${1:-/home/hilalss/Desktop/MLMAS_Project/CARLA_0.9.10.1}
export WORK_DIR=${2:-ML_Models/transfuser-2022}

export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
export SCENARIO_RUNNER_ROOT=${WORK_DIR}/scenario_runner
export LEADERBOARD_ROOT=${WORK_DIR}/leaderboard
export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/":"${SCENARIO_RUNNER_ROOT}":"${LEADERBOARD_ROOT}":${PYTHONPATH}

export ROUTES=leaderboard/data/longest6/longest6.xml
export SCENARIOS=leaderboard/data/longest6/eval_scenarios.json
export REPETITIONS=1
export CHALLENGE_TRACK_CODENAME=SENSORS
export CHECKPOINT_ENDPOINT=${WORK_DIR}/results/transfuser_longest6.json
export TEAM_AGENT=${WORK_DIR}/team_code_transfuser/submission_agent.py
export TEAM_CONFIG=${WORK_DIR}/model_ckpt/transfuser
export DEBUG_CHALLENGE=0
export RESUME=1
export DATAGEN=0
export RECORD_PATH=/home/hilalss/Desktop/MLMAS_Project/results/records/tfus

python3 ${LEADERBOARD_ROOT}/leaderboard/leaderboard_evaluator.py \
--scenarios=${SCENARIOS}  \
--routes=${ROUTES} \
--repetitions=${REPETITIONS} \
--track=${CHALLENGE_TRACK_CODENAME} \
--checkpoint=${CHECKPOINT_ENDPOINT} \
--agent=${TEAM_AGENT} \
--agent-config=${TEAM_CONFIG} \
--debug=${DEBUG_CHALLENGE} \
--resume=${RESUME}\
--record=${RECORD_PATH}
