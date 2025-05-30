import os
import re
import json
import paho.mqtt.client as mqtt

## Shared constants
# MQTT protocol
MQTT_CALLBACK_VERS      = mqtt.CallbackAPIVersion.VERSION2
MQTT_PROTOCOL_VERS      = mqtt.MQTTv5
# MQTT connections
#MQTT_BROKER_HOST        = os.getenv('MQTT_BROKER_HOST',"broker.hivemq.com")
#MQTT_BROKER_HOST        = os.getenv('MQTT_BROKER_HOST',"192.168.1.67")
MQTT_BROKER_HOST        = os.getenv('MQTT_BROKER_HOST',"192.168.1.123")
MQTT_BROKER_PORT        = int(os.getenv('MQTT_BROKER_PORT',1883))
# MQTT connection : WoL_proxy - User client
PROXY_TOPICS_PREFIX     = os.getenv('PROXY_TOPICS_PREFIX',"WOL-proxy")
PROXY_TOPIC_WAKEUP      = os.getenv('PROXY_TOPIC_WAKEUP',f"{PROXY_TOPICS_PREFIX}/wakeup")
PROXY_QOS_WAKEUP        = int(os.getenv('PROXY_QOS_WAKEUP',2))
PROXY_TOPIC_STATUS      = os.getenv('PROXY_TOPIC_STATUS',f"{PROXY_TOPICS_PREFIX}/status")
PROXY_QOS_STATUS        = int(os.getenv('PROXY_QOS_STATUS',1))
PROXY_TOPIC_ERROR       = os.getenv('PROXY_TOPIC_ERROR',f"{PROXY_TOPICS_PREFIX}/error")
PROXY_QOS_ERROR         = int(os.getenv('PROXY_QOS_ERROR',1))
# MQTT connection : Boards - User client
# GENERAL
BOARD_TOPICS_PREFIX     =  os.getenv('BOARD_TOPICS_PREFIX',"Boards")
BOARD_TOPIC_STATUS      = os.getenv('BOARD_TOPIC_STATUS',f"{BOARD_TOPICS_PREFIX}/status")
BOARD_QOS_STATUS        = int(os.getenv('BOARD_QOS_STATUS',1))
BOARD_TOPIC_ERROR       = os.getenv('BOARD_TOPIC_ERROR',f"{BOARD_TOPICS_PREFIX}/error")
BOARD_QOS_ERROR         = int(os.getenv('BOARD_QOS_ERROR',1))
# THRESHOLD UPDATE
THR_TOPICS_PREFIX       = os.getenv('THR_TOPICS_PREFIX',"thr")
THR_TOPIC_UPDATE        = os.getenv('THR_TOPIC_UPDATE',f"{BOARD_TOPICS_PREFIX}/{THR_TOPICS_PREFIX}/update")
THR_QOS_UPDATE          = int(os.getenv('THR_QOS_UPDATE',2))
THR_TOPIC_ACK           = os.getenv('THR_TOPIC_ACK',f"{BOARD_TOPICS_PREFIX}/{THR_TOPICS_PREFIX}/ack")
THR_QOS_ACK             = int(os.getenv('THR_QOS_ACK',2))
# OUT OF WINDOW DATA
DATA_TOPIC              = os.getenv('DATA_TOPIC',f"{BOARD_TOPICS_PREFIX}/data")
DATA_QOS                = int(os.getenv('DATA_QOS',1))
# TOPICS DATA FORMAT
WAKEUP_KEYS             = ["toWakeup"]                          # Used in "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_WAKEUP}"
UPDATE_KEYS             = ["toUpdate","thr"]                    # Used in "{THR_TOPICS_PREFIX}/{THR_TOPIC_UPDATE}"
DATA_KEYS               = ["boardId","sensorId","vals","ts"]    # Used in "{DATA_TOPIC}"