
#!/bin/bash
ps -ef | grep carla_agent | grep -v grep | awk '{print $2}' | xargs kill
