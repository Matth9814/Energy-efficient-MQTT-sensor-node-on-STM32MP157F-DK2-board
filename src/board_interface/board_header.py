import os
import json
import paho.mqtt.client as mqtt
from getmac import get_mac_address
import sys
import time
import threading
import traceback


### MQTT CONSTANTS
## MQTT protocol
MQTT_CALLBACK_VERS      = mqtt.CallbackAPIVersion.VERSION2
MQTT_PROTOCOL_VERS      = mqtt.MQTTv5
## MQTT connections
#MQTT_BROKER_HOST        = os.getenv('MQTT_BROKER_HOST',"broker.hivemq.com")
#MQTT_BROKER_HOST        = os.getenv('MQTT_BROKER_HOST',"192.168.1.67")
MQTT_BROKER_HOST        = os.getenv('MQTT_BROKER_HOST',"192.168.1.123")
MQTT_BROKER_PORT        = int(os.getenv('MQTT_BROKER_PORT',1883))
## MQTT connection : WoL_proxy - User client
# Missing since these macros are not necessary to the boards
## MQTT connection : Boards - User client
# General
BOARD_TOPICS_PREFIX     =  os.getenv('BOARD_TOPICS_PREFIX',"Boards")
BOARD_TOPIC_STATUS      = os.getenv('BOARD_TOPIC_STATUS',f"{BOARD_TOPICS_PREFIX}/status")
BOARD_QOS_STATUS        = int(os.getenv('BOARD_QOS_STATUS',1))
BOARD_TOPIC_ERROR      = os.getenv('BOARD_TOPIC_ERROR',f"{BOARD_TOPICS_PREFIX}/error")
BOARD_QOS_ERROR        = int(os.getenv('BOARD_QOS_ERROR',1))
# Threshold update
THR_TOPICS_PREFIX       = os.getenv('THR_TOPICS_PREFIX',"thr")
THR_TOPIC_UPDATE        = os.getenv('THR_TOPIC_UPDATE',f"{BOARD_TOPICS_PREFIX}/{THR_TOPICS_PREFIX}/update")
THR_QOS_UPDATE          = int(os.getenv('THR_QOS_UPDATE',2))
THR_TOPIC_ACK           = os.getenv('THR_TOPIC_ACK',f"{BOARD_TOPICS_PREFIX}/{THR_TOPICS_PREFIX}/ack")
THR_QOS_ACK             = int(os.getenv('THR_QOS_ACK',2))
# Out of window data
DATA_TOPIC              = os.getenv('DATA_TOPIC',f"{BOARD_TOPICS_PREFIX}/data")
DATA_QOS                = int(os.getenv('DATA_QOS',1))
# Topics data format
DATA_KEYS               = ["boardId","sensorId","vals","ts"]    # Used in "{DATA_TOPIC}"
UPDATE_KEYS             = ["toUpdate","thr"]                    # Used in "{THR_TOPICS_PREFIX}/{THR_TOPIC_UPDATE}"

### GENERAL CONSTANTS
ETH_INTERFACE           = "end0"                                
BOARD_ID                = get_mac_address(ETH_INTERFACE).casefold()         # Board id (MAC address)

SENSOR_ID               = "voltage_sensor0"                                 # Id of the voltage sensor 

SUB_TOPICS              = [(THR_TOPIC_UPDATE,THR_QOS_UPDATE)]               # Topics to subscribe to
UNSUB_TOPICS            = []
for topic in SUB_TOPICS:
    UNSUB_TOPICS.append(topic[0])

dataStruct = {                  # Data struct
    DATA_KEYS[0]: BOARD_ID,
    DATA_KEYS[1]: SENSOR_ID,
    DATA_KEYS[2]: [],
    DATA_KEYS[3]: 0
}

TTY_PATTERN     = ".*/ttyRPMSG[0-9]\{1,\}$"             # Name pattern of the tty interface to communicate with the M4

ETHWU_EV_FILE   = "/sys/kernel/debug/wakeup_sources"    # File used to check the last occurrence of an ethernet wake-up event

#SENSDATA_DELIM = b';'  # Bytes object needs a byte-like delimiter
DATA_TYPE       = int   # Data coming from the M4 are uint32_t but Python 3.x has non-limited int so the 
                        # representation is correct even if a 32 bits unsigned integer is sent
DATA_SIZE       = 4     # Size of datum sent by the M4

M4_MSG_INTERVAL = 30    # Maximum interval with no message from M4 before A7 suspends

LOG_ROOT        = "/home/root/log" 
ERR_FILE        = f"{LOG_ROOT}/error.txt"   # File to log all the boards errors 
DBG_FILE        = f"{LOG_ROOT}/dbg.txt"     # File to log all debug/status info
# This file is especially important because it also logs the runtime errors that are not delivered to the user client

THR_MSG_INTERVAL= 20    # Maximum time waited for the update structure message containing the threhsold after a threshold
                        # update procedure is issued
SUSP_M4_RDY_TO  = 5     # Maximum time waited for M4 response before suspension

RPROC_STATE_FILE= "/sys/class/remoteproc/remoteproc0/state"     # File holding the state of the remote processor (CM4)
RPROC_RUN       = "running\n"                                     # CM4 running
RPROC_RDY_TO    = 10                                            # Max waiting time for CM4 running 

INITIAL_THR     = b"0;2900"  # The ADC Vref is 2.9V so, with this threshold, no out of window value can be generated  

### A7-M4 MESSAGES
RDY4TR          = b"tr_Rdy"     # A7 ready for next transmission [to M4]
WAIT4THR        = b"thr_Wait"   # Puts the M4 in a listening state, waiting for new thresholds [to M4]
THR_SET         = b"thr_Set"    # New threshold set [from M4]
WAIT4SUSP       = b"susp_Wait"  # Prevents the M4 from sending new out of window data while A7 is suspending [to M4]
# The following messages are mutually exclusive, only one can be sent by the M4 before an A7 operation 
RDY4OP          = b"op_Rdy"     # Signals the A7 that there are no new data to read so it can proceed [from M4]

### CONFIGURATION CONSTANTS
SUSPEND         = False # If True the A7 suspension procedure is triggered whenever possible to save energy
DISCONN_B4SUS   = SUSPEND and False # If True the board is disconnected from the broker before suspending
                                    # It depends on SUSPEND since it is used during the suspension procedure
COMM_INIT       = "comm_init"       # Executes the M4-A7 RPMsg comm. channel init
