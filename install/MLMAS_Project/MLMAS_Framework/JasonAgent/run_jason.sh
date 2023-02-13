
#!/bin/bash
java -Dfile.encoding=UTF-8 -classpath MLMAS_Framework/JasonAgent/carla_agents/bin/classes:MLMAS_Framework/JasonAgent/JasonLib/jason-3.1.jar:MLMAS_Framework/JasonAgent/JasonLib/javax.json-1.1.4.jar:JasonLib/javax.json-api-1.1.4.jar -XX:+ShowCodeDetailsInExceptionMessages jason.runtime.RunJasonProject MLMAS_Framework/JasonAgent/carla_agents/carla_agents.mas2j &
