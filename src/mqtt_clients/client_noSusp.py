from header import *
import time
import threading

# User Client CONSTANTS
MQTT_CLIENT_ID  = "User client"
# Subscribe/unsubscribe to/from these topics
SUB_TOPICS      = [(PROXY_TOPIC_STATUS, PROXY_QOS_STATUS),(PROXY_TOPIC_ERROR, PROXY_QOS_ERROR),
                   (BOARD_TOPIC_STATUS, BOARD_QOS_STATUS),(BOARD_TOPIC_ERROR, BOARD_QOS_ERROR),
                   (THR_TOPIC_ACK, THR_QOS_ACK),(DATA_TOPIC,DATA_QOS),]
UNSUB_TOPICS    = []
for sub in SUB_TOPICS:
    UNSUB_TOPICS.append(sub[0])
# Log directory
LOG_ROOT        = "log"
STATUS_FILE     = f"{LOG_ROOT}/status.txt"
DATA_FILE       = f"{LOG_ROOT}/data.txt"
ERROR_FILE      = f"{LOG_ROOT}/error.txt"

# Boards MAC list
BOARD_MAC       = ["10:E7:7A:E1:7D:BF"]
BOARD_MAC       = [mac.casefold() for mac in BOARD_MAC]

# Boards input separator
# Same separator used by the boards to format the thresholds 
SEP             = ";"

# User Client GLOBAL VARIABLES
# Data structure used in the user client to manage the thrshold update
boardsToUpdate  =   {UPDATE_KEYS[0]:{
                        "boardsId":[],      # Boards to wake-up, i.e. whose threshold has to be updated
                        "isUpdated": []},   # Updated boards list 
                    UPDATE_KEYS[1]:""}      # New threhsold
# The "isUpdated" entry corresponding to the board is True if the client received the board ack
# NOTE: This acknowledge is sent by the board after a successful threshold update. 
# If the ack is not received within a given time the update of that board is considered as failed.
# In this case ERROR_FILE should be checked for errors from that board.

# Lock to manage race-conditions on thrUpdate and boardsToUpdate
lock            = threading.Lock()
# State variable used to manage the threshold update procedure
thrUpdate = False

def on_connect(client:mqtt.Client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        err_write(f"Connection to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} failed with reason code {reason_code}: "+mqtt.connack_string(reason_code))
        err_write("Trying to reconnect...")
    else:
        status_write(f"Successfully connected to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        # Subscribe from on_connect callback to be sure subscriptions are persisted across reconnections.
        result,mid = client.subscribe(SUB_TOPICS)
        if result != mqtt.MQTT_ERR_SUCCESS:
            err_write(f"Subscription failed")

#def on_subscribe(client, userdata, mid, reason_code_list, properties):
#    for rc in reason_code_list:
#        print(f"Subscription {rc}.")

#def on_unsubscribe(client, userdata, mid, reason_code_list, properties):
#    for rc in reason_code_list:
#        print(f"Unsubscription {rc}")

#callback function for incoming threshold
def on_message(client, userdata, message):
    global thrUpdate
    # NOTE: If you user the client.loop_start() method then this starts a new thread in the background to run
    # the network loop and all the callbacks on.
    # All callbacks block the execution of the network thread, this is why you should not run long 
    # running or blocking tasks directly in the callback.
    # The code line below can be used to check if the running thread is the main one or not from Python 3.4 
    #assert threading.current_thread() is threading.main_thread(), f"{threading.current_thread()}"
    
    message.payload = message.payload.decode('utf-8')
    if message.topic == THR_TOPIC_ACK:
        lock.acquire()
        # Prevents the following condition on being checked while thrUpdate is modified in the main thread
        # In case thrUpdate == True the entire block of code is locked because the state of boardsToUpdate
        # should not be modified by the main thread while the operations is running.
        if thrUpdate:
            # The check on thrUpdate avoids to proceed with this step of the update procedure if the update struct
            # was not sent, i.e. the actual threshold update hasn't started.
            if re.match(r"[0-9a-f]{2}([-:\.]?)[0-9a-f]{2}(\1[0-9a-f]{2}){4}$", message.payload):
                status_write(f"{message.payload} updated")
                try:
                    updIndex = boardsToUpdate[UPDATE_KEYS[0]]["boardsId"].index(message.payload)
                    # index() raises ValueError if the board is not among the ones whose threshold needs to be updated
                    # so the "isUpdated" entry is not assigned to True
                    boardsToUpdate[UPDATE_KEYS[0]]["isUpdated"][updIndex] = True
                    if(all(boardsToUpdate[UPDATE_KEYS[0]]["isUpdated"])): 
                        # All boards have been updated
                        thrUpdate = False # Flag the end of the threshold update  
                except:
                    err_write(f"Board {message.payload} threshold was unexpectedly updated")
            else:
                err_write(f"Message payload has invalid MAC address format!\nReceived message: {message.payload}")
        lock.release()
    elif message.topic == DATA_TOPIC:
        data_write(message.payload)
    elif message.topic == BOARD_TOPIC_ERROR or message.topic == PROXY_TOPIC_ERROR:
        err_write(message.payload)
    else: # message.topic == PROXY_TOPIC_STATUS or message.topic == BOARD_TOPIC_STATUS:
        status_write(message.payload)
    #print(f"[{message.topic}] {message.payload}")
    
def on_publish(client, userdata, mid, reason_code, properties):
    if reason_code.is_failure:
        print(f"Message {mid} publish failed with reason code {reason_code}")


def on_disconnect(client:mqtt.Client, userdata, flags, reason_code, properties):
    if reason_code.is_failure: # Disconnection problem  
        err_write(f"Unexpected disconnection from broker (RC={reason_code}). Attempting to reconnect...")
    else:
        status_write(f"Correctly disconnected from {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        
if __name__ == '__main__':
    # Log files setup
    if not os.path.isdir(LOG_ROOT):
        os.makedirs(LOG_ROOT)

    errfp = open(ERROR_FILE,"a")
    datafp = open(DATA_FILE,"a")
    statusfp = open(STATUS_FILE,"a")
    
    def err_write(msg:str): 
        errfp.write(f"[{time.time()}] {msg}\n")
        errfp.flush()

    def status_write(msg:str):
        statusfp.write(f"[{time.time()}] {msg}\n")
        statusfp.flush()

    def data_write(msg:str):
        datafp.write(f"[{time.time()}] {msg}\n")
        datafp.flush()

    # MQTT client setup
    client = mqtt.Client(callback_api_version=MQTT_CALLBACK_VERS,protocol=MQTT_PROTOCOL_VERS,client_id=MQTT_CLIENT_ID)
    client.on_message = on_message
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    #client.on_subscribe = on_subscribe
    #client.on_unsubscribe = on_unsubscribe
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    # Connecting after calling loop_start() can result in strange behaviours
    client.loop_start()
    while not client.is_connected():
        pass

    # Main loop
    #print(threading.enumerate())
    print("#### WELCOME TO THE MANAGEMENT SYSTEM ####")
    print(f"\n>> Out of window data in {DATA_FILE}")
    print(f">> Status messages in {STATUS_FILE}")
    print(f">> Error messages in {ERROR_FILE}")
    # Exit flag
    exitClient = False
    while not exitClient:
        print("\n>> Would you like to update a threshold? [y/n]\n> ",end="")
        inp = input().lower()
        if inp in ("y","yes"):
            # Boards selection
            print("\n## Threshold update ##")
            print("\nStep 1. Select the boards to update")
            print(">> Available boards:")
            for i in range(len(BOARD_MAC)):
                print(f"{i}. {BOARD_MAC[i]}")
            print(f"\n>> Input format: <board0Num>{SEP}<board1Num>{SEP}...{SEP}<boardnNum>")
            print(">> Insert an invalid input to exit")
            print("---> Boards to update: ",end="")
            try:
                inp = input()
                # set() removes repeated values
                # NOTE: if not handled this can cause SEVERE problems 
                inp = set(inp.strip().split(SEP))
                #print(inp)
                boardsToUpdate[UPDATE_KEYS[0]]["boardsId"] = []
                for val in inp:
                    boardsToUpdate[UPDATE_KEYS[0]]["boardsId"].append(BOARD_MAC[int(val)])
                boardsToUpdate[UPDATE_KEYS[0]]["isUpdated"] = [False] * len(boardsToUpdate[UPDATE_KEYS[0]]["boardsId"])

                # New threshold
                print("\nStep 2. Choose the new threshold")
                print(f">> Input format: <lowThr>{SEP}<highThr>")
                print(">> Insert an invalid input to exit")
                print("----> New threshold: ",end="")
                thr = input().strip()
                if re.match(r"\d+"+SEP+r"\d+$",thr) == None:
                    raise Exception
                boardsToUpdate[UPDATE_KEYS[1]] = thr

                # Update process timeout
                print("\nStep 3. Set the maximum update time")
                print(f">> Input format: <maxUpdateTime>")
                print(">> 'maxUpdateTime' is the maximum time waited after sending the threshold to the boards")
                print(">> Insert an invalid input to exit")
                print("----> Update timeout: ",end="")
                maxUpdTime = int(input().strip())
            except:
                print(">> Aborting threshold update...")
                boardsToUpdate = {UPDATE_KEYS[0]:{"boardsId":[],"isUpdated": []},UPDATE_KEYS[1]:""}
                continue
            # Update data sent to the boards
            updateStruct = {UPDATE_KEYS[0]:boardsToUpdate[UPDATE_KEYS[0]]["boardsId"],UPDATE_KEYS[1]:boardsToUpdate[UPDATE_KEYS[1]]}
            #print(boardsToUpdate)
            
            # Send the update data structure
            # The lock is not be necessary since thrUpdate is False, hence the thrUpdate variable
            # cannot be modified in on_message yet 
            thrUpdate = True
            # thrUpdate set before sending the threshold to the boards so that the response can be surely processed
            # when a response come. This is done to avoid that thrUpdate remains False (e.g. processor overloaded 
            # on the client) even after the update data have been sent to the boards.
            info = client.publish(THR_TOPIC_UPDATE, payload=json.dumps(updateStruct),qos=THR_QOS_UPDATE,retain=False)
            print("\r>> Threshold update: STARTED",end="")
            try:
                startUpdTime = time.time()
                info.wait_for_publish(maxUpdTime)
            except:
                lock.acquire()
                # Prevents race-conditions in on_message
                thrUpdate = False
                lock.release()
                # At this point the critical section in on_message cannot be executed anymore so the write operation
                # on boardsToUpdate does not need to be guarded
                print("\n>> Threshold update process failed")
                boardsToUpdate = {UPDATE_KEYS[0]:{"boardsId":[],"isUpdated": []},UPDATE_KEYS[1]:""}
                continue
            print("\r>> Threshold update: IN PROGRESS",end="")
            updAborted = False
            while thrUpdate:
                if time.time()-startUpdTime > maxUpdTime:
                    lock.acquire()
                    thrUpdate = False # Update forced to end
                    lock.release()
                    # thrUpdate == False, cannot process any more update ack in on_message so
                    # there is no race-condition on boardsToUpdate write access
                    updAborted = True
                    print("\r>> Threshold update:     ABORTED")
                    print(">> Not updated boards:")
                    for i in range(len(boardsToUpdate[UPDATE_KEYS[0]]["isUpdated"])):
                        boardUpdated = boardsToUpdate[UPDATE_KEYS[0]]["isUpdated"][i]
                        if boardUpdated == False:
                            print(f"{i}. {boardsToUpdate[UPDATE_KEYS[0]]['boardsId'][i]}")
            if not updAborted:
                print("\r>> Threshold update:    FINISHED")
                print(f">> Check {STATUS_FILE} to monitor the updated boards!")
        elif inp in ("n","no"):
            exitClient = True
            print("\n>> Disconnecting client...")
        else:
            print("\n>> Invalid input")


    result, mid = client.unsubscribe(UNSUB_TOPICS)
    if result != mqtt.MQTT_ERR_SUCCESS:
        err_write("Unsubscription failed")
    # The disconnection is recorded in statusfp/errfp so they need to be closed after disconnecting the client        
    client.disconnect()
    # Stopping the thread inside on_disconnect when calling disconnect() causes some weird problems
    # For example not all write to file are executed
    client.loop_stop()
    errfp.close()
    statusfp.close()
    datafp.close()
    
# NOTE: Network architecture idea
# #### ARCH 1 ####
# Use a PROXY CLIENT in the boards local network to wake them up through magic packets (i.e. WoL packets) before sending them
# the received threshold.
# This proxy is a subscriber of the channel "{PROXY_TOPICS_PREFIX}/{MQTT_TOPIC_NEWTHR}", where it receives messages with the
# threshold and the MAC addresses of the devices to wake-up as payload. The QoS for this channel should be 2 since it is
# better to avoid duplicate messages. In fact, each time the proxy client receives a correct message:
# 1. Sends a magic packet to the target board
# 2. Waits for an ack signaling that the target board woke-up correctly
# 3. Sends the threshold
# 4. Waits for an ack signaling that the threshold has been set correctly
# This is done for each board whose threshold is updated. When all targeted boards are updated the proxy client
# sends an acknowledge to the user client, always on the "{PROXY_TOPICS_PREFIX}/{MQTT_TOPIC_NEWTHR}" topic.
# The QoS of the user client (i.e. the one sending the threshold) has to be 2 too;
# The proxy client acts as publisher of the topics "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_STATUS}" and 
# "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_ERROR}", where it informs the client of resepctively the process errors and
# the process state (IDEA: maybe it can return a data structure to tell if the threshold setting was successful or not).
# The user client is a subscriber of the process status and error topics. "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_STATUS}" is
# mainly used for debug purposes.
# The QoS can be 1 for both publisher and subscriber since there is no problem linked to duplicate messages.
# Using a lower QoS for the publisher would overule the QoS of the subscriber.
# The boards send the out of window data to the proxy client in the local network and the proxy client forwards these data
# to the user client through the topic "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_DATA}".
# The QoS can be 0/1/2 for both publisher and subscriber depending on the severity of the application field the
# system is used for.  
# The communication between the user client and the proxy client relies on MQTT while the communication between the
# proxy client and the boards is done through ethernet.

#### ARCH 2 ####
# Use a PROXY CLIENT in the boards local network to wake them up through magic packets (i.e. WoL packets).
# This proxy is a subscriber of the channel "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_WAKEUP}", where it receives messages with the
# MAC addresses of the devices to wake-up as payload. The QoS for this channel should be 2. In fact, it is better to avoid 
# duplicate messages since this could lead to wake-up a board multiple times.
# The QoS of the user client (i.e. the one sending the threshold) has to be 2 too;
# using a lower QoS for the publisher would overule the QoS of the subscriber.
# In case the message on "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_WAKEUP}" is not published the threshold update 
# process is suspended. The proxy client acts as publisher of the topics "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_STATUS}" and 
# "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_ERROR}", where it informs the client of resepctively the process errors and
# the process state. The user client is a subscriber of the process status and error topics. 
# "{PROXY_TOPICS_PREFIX}/{PROXY_TOPIC_STATUS}" is mainly used for debug purposes.
# The QoS can be 1 for both publisher and subscriber since there is no problem linked to duplicate messages.
# Since it is not possible to accurately keep track of the boards status (i.e. awake or suspended),  after 'maxWuTime' 
# is waited the threshold is sent by the user client on the topic "{THR_TOPICS_PREFIX}/{THR_TOPIC_UPDATE}",
# together with the list of MAC addresses of the targeted boards. The list is useful to check if the board that is receiving
# the message is among the ones that have to be updated. The publication of this message starts the actual threshold update
# process. Once the boards have received the threshold, they try to set it. In case of success they report it with an
# acknowledge on "{THR_TOPICS_PREFIX}/{THR_TOPIC_ACK}". In case of failure, the ack is not sent. An error message
# is published on "{BOARD_TOPICS_PREFIX}/{BOARD_TOPIC_ERROR}" if the board status allows it (e.g. if the board was suddenly
# disconnected from the broker the error message cannot be sent). If 'maxUpdTime' passes the user client considers 
# as concluded threshold update process. The threshold update on the boards who have not acked yet is not
# considered successful. 
# The topic "{BOARD_TOPICS_PREFIX}/{BOARD_TOPIC_ERROR}" is also used to report generic boards errors.
# The topic "{BOARD_TOPICS_PREFIX}/{BOARD_TOPIC_STATUS}" is mainly used for debug.
# With only a few boards, it could be better to use a separate topic for each board to communicate the threshold.
# This would allow not to have to wait for all boards to wake-up and it would also avoid to check the MACs list on each
# board to know if its threshold needs to be updated.
# The boards send the out of window data to the user client through the topic "{DATA_TOPIC}".
# "{THR_TOPICS_PREFIX}/{THR_TOPIC_ACK}" requires a QoS of 2 for both pub and sub since duplicate messages could cause
# the user client (sub) to acknowledge the current threshold update, even though it already started a new update procedure
# sensible to multiple "ack" messages from the same board.
# "{THR_TOPICS_PREFIX}/{THR_TOPIC_UPDATE}" requires a QoS of 2 for both pub and sub since the boards (subs) may waste time
# on multiple unneeded threshold updates if multiple thresholds are received. TODO: check if boards remain connected to
# broker while suspended  
# "{BOARD_TOPICS_PREFIX}/{BOARD_TOPIC_ERROR}" requires a QoS of 1 for both pub and sub since multiple error messages
# do not impact negatively the user client activity.
# "{BOARD_TOPICS_PREFIX}/{BOARD_TOPIC_STATUS}" requires a QoS of 0/1 for both pub and sub since multiple status messages
# do not impact negatively the user client activity.
# "{DATA_TOPIC}" can use a QoS of 0/1/2 for both publisher and subscriber depending
# on the severity of the application field the system is used for.  

# ARCH_1 is better in terms of network organization since there is a node with a high but not excessive traffic in 
# each local network (i.e. the proxy clinet) but it requires more time to be implemented.
# In fact, using socket to implement a client/server mechanism between the proxy and the boards in a same subnet
# requires a lot of time. 
# Actually, if there was only a subnet, the broker could be placed on the same machine of the
# proxy client in order to use MQTT within the subnet. In this case, the architecture would be the same but proxy client
# and boards would communicate with MQTT. However, if there were more subnet, a broker per subnet would be needed,
# so it would be better to resort to a client/server approach.
# ARCH_2 requires less time to be implemented but it has multiple long-range transmission and a broker that needs to
# handle a lot of traffic.

# In the current versione the client session is NOT PERSISTENT, in fact the client should always be active to receive data
# and status messages. During connection (i.e. when connect() is called) the "clean_start" flag is set by default
# to MQTT_CLEAN_START_FIRST_ONLY. This means that, when connecting, previous sessions are not retrieved if still 
# present in the broker but reconnections due to unexpected disconnections are treated as part of the same session.