# ===========================
# Jason - Carla Bridge configuration
# ===========================
export BRIDGE_SERVER_IP=127.0.0.1
export BRIDGE_SERVER_PORT=60111

# ===========================
# The ML Model configuration
# ===========================
# The ML model (AutonomousAgent) agent location.
export ML_MODEL=ML_Models/LAV/team_code/lav_agent.py
# The ML model configuration file location.
export TEAM_CONFIG=ML_Models/LAV/team_code/config.yaml
# add any required python path required by the model
export PYTHONPATH=$PYTHONPATH:ML_Models/LAV/team_code


# ===========================
# The Scenario Routes configuration
# ===========================
export ROUTES=leaderboard/data/longest6/longest6.xml
export SCENARIOS=leaderboard/data/longest6/eval_scenarios.json

# ===========================
# The storing location of the results and the records
# ===========================
# [The results json] work as checkpoint that you can resume to the route when stoped.
# and also the final leader board results will be stored there.
export CHECKPOINT_ENDPOINT=results/MLMAS_LAV_results.json # results file

# The [record path] will store the record log of the running scenarios
# which can be used to rerun the scenario and check the collisions and blocks
# using the provided utility code in this project.
# **Note: required direct path
export RECORD_PATH=$(pwd)/results/records/MLMAS_LAV/

# ===========================
# Jason Agent
# ===========================
# # set it to true, if you want to run the jason agent localy.
# # and automatically, but if it is in remote pc, set it to false.
run_jason_agent=true
