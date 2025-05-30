from board_header import *
import subprocess as sp
from shlex import split as shSplit

# GLOBAL VARIABLES
pubLock         = threading.Lock()  # Lock for lastPublish
thrFlagLock     = threading.Lock()  # Lock for thrToSet and thrToReceive

lastPublish     = None              # Mid of the last published message
                                    # The A7 waits for this message to be published before going to sleep
# Threhsold update variables
thrToSet = False            # Threshold update procedure required when True
thrReceived = False         # New threshold received when True
newThr = None               # New threshold

# CM4-CA7 comm. interface
# NOTE: this is the name of the first interface initialized after flashing the CM4.
# In case there is a communication failure and another interface is initialized its name will be "/dev/ttyRPMSG1".
# However, in this case, the CM4, if not the entire system, will probably need a reboot/reflash so the interface will
# be created again as /dev/ttyRPMSG0
ttyRPMSGx = "/dev/ttyRPMSG0"

# Fileno and file object
m4ch = None

# File descriptors of error and debug files
errfp = None
dbgfp = None

# MQTT client
client = None

def on_connect(client:mqtt.Client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"Connection to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} failed with reason code {reason_code}: "+mqtt.connack_string(reason_code))
        print("Trying to reconnect...")
    else:
        print(f"Successfully connected to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        # Subscribe from on_connect callback to be sure subscriptions are persisted across reconnections.
        result,mid = client.subscribe(SUB_TOPICS)
        if result != mqtt.MQTT_ERR_SUCCESS:
            log_err("Subscription failed")

def on_subscribe(client:mqtt.Client, userdata, mid, reason_code_list, properties):
    global lastPublish
    failedSub = False
    for rc in reason_code_list:
        if rc.is_failure:
            failedSub = True
            log_err(f"Subscription to topics {SUB_TOPICS} failed")
    if not failedSub:
        pubLock.acquire()
        # The client can be informed the board is online only after it has correctly subscribed to BOARD_TOPIC_STATUS 
        lastPublish = client.publish(BOARD_TOPIC_STATUS,payload=f"{BOARD_ID} online",qos=BOARD_QOS_STATUS).mid
        pubLock.release()
        

#def on_unsubscribe(client, userdata, mid, reason_code_list, properties):
#    for rc in reason_code_list:
#        print(f"Unsubscription {rc}")

def on_publish(client, userdata, mid, reason_code, properties):
    global lastPublish
    if reason_code.is_failure:
        log_err(f"Publish call failed: mid={mid} | rc={reason_code}")
    # Needs to be checked even if the publish failed, otherwise the A7 may be stopped from sleeping
    # because the current last publish failed.
    pubLock.acquire()
    # Lock acquired before reading because lastPublish should not be changed while reading
    if mid == lastPublish:
        print("Nothing else to publish")
        # NOTE: If you user the client.loop_start() method then this starts a new thread in the background to run
        # the network loop and all the callbacks on.
        # All callbacks block the execution of the network thread, this is why you should not run long 
        # running or blocking tasks directly in the callback.
        lastPublish = None    # No message unpublished
    pubLock.release()

#callback function for incoming threshold
def on_message(client, userdata, message):
    global thrReceived
    global thrToSet
    global newThr
    #if message.topic == THR_TOPIC_UPDATE:
    message.payload = message.payload.decode('utf-8')
    thrFlagLock.acquire()
    if not thrReceived:
        print("Threshold received")
        # NOTE: If the threhsold was already received there is an ongoing threshold update process.
        # This case is handled discarding the latest threshold. The client that issued the discarded update
        # will need to retry the update.
        
        newThr = json.loads(message.payload)
        if BOARD_ID in newThr[UPDATE_KEYS[0]]:
            print("Threshold update required")
            # NOTE: The threshold structure is coming from the client is trusted to be correct.
            # Moreover there is no mechanism to check that the threshold values are within the correct operational bounds.
            # This check depends on some application design choices (i.e. sensors, voltage, etc) and, in order to be
            # automatic, proper data structures and communication protocols should be adopted between boards and clients.
            # For example, when the client is first started, it could publish a message informing all clients about its
            # operational values. However, this means that all clients should be online when the board is started. In fact,
            # only the last retained message of a topic is sent to a subscribing client so retaining these info for multiple
            # boards is not a solution for clients that subscribe after the boards are already online.
            # A possible solution could be to retrieve these informations from a database that is updated each time a 
            # new board is added or to fetch them asking to the boards themselves. In the latter scenario a client/server
            # approach should be preferred instead of a publish/subscribe protocol.
            # Another problem is the need to track the online/offline boards. At the moment the list of online boards is
            # statically defined in the client.
            newThr = newThr[UPDATE_KEYS[1]]
            thrToSet = True
            thrReceived = True
    else:
        print("Message received while already updating the threshold")
    thrFlagLock.release()
    #print(f"[{message.topic}] {message.payload}")
    
def on_disconnect(client:mqtt.Client, userdata, flags, reason_code, properties):
    if reason_code.is_failure: # Disconnection problem  
        log_err(f"Unexpected disconnection from broker (RC={reason_code}). Attempting to reconnect...")
    else:
        print(f"Correctly disconnected from {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")

def monitor_ethWakeUp() -> bytes:
    """Monitor ethernet wake-up events
    
    Return:
    @lastWu: last time the ethernet woke-up the processor"""

    try:
        lastWu = sp.run(shSplit(f"awk 'NR == 2 {{print $3}}' {ETHWU_EV_FILE}"),capture_output=True,check=True)
        lastWu = lastWu.stdout[:-1] # Retrieve stdout (bytes object) and remove \n
    except sp.CalledProcessError:
        lastWu = None

    return lastWu

def send_mqttData(data:list[DATA_TYPE]):
    """Send data through MQTT"""
    global lastPublish
    dataStruct[DATA_KEYS[2]] = data
    dataStruct[DATA_KEYS[3]] = time.time()
    # NOTE: the mqtt client hangs while publishing when it is flooded with messages to publish with QoS 1 or 2
    # In our system this happens because the ADC is fed with a constant value by the DAC so, when the DAC
    # value is out of the window, the CM4 floods the CA7 of data to send to the user client 
    # The adopted solution blocks the publish of new out of window data untile the previous message has been
    # fully acknowledged by the broker. Despite this measure there shouldn't be significant performance issues since,
    # in real applications, a board should not flood the user client of messages
    while DATA_QOS != 0 and lastPublish != None:
        pass
    pubLock.acquire()
    lastPublish = client.publish(DATA_TOPIC,payload=json.dumps(dataStruct),qos=DATA_QOS).mid
    pubLock.release()
    
def process_rawData(sensorData:bytes=b'') -> list[DATA_TYPE]:
    """Elaborates data coming from the M4.

        Returns:
        @mqttData: List of out of window data"""

    mqttData = []
    for i in range(0,len(sensorData),DATA_SIZE):
        #print(f"Data #{i/DATA_SIZE}: {sensorData[i:i+DATA_SIZE-1]}")
        #print(f"Data #{i/DATA_SIZE}: {int.from_bytes(sensorData[i:i+DATA_SIZE-1],byteorder='little',signed=False)}")
        mqttData.append(DATA_TYPE.from_bytes(sensorData[i:i+DATA_SIZE-1],byteorder='little',signed=False))

    print(mqttData)
    return mqttData

def exit_procedure():
    global lastPublish
    # MQTT exit procedure
    try:
        pubLock.acquire()
        lastPublish = client.publish(BOARD_TOPIC_STATUS,payload=f"{BOARD_ID} offline",qos=BOARD_QOS_STATUS).mid
        pubLock.release()
        result, mid = client.unsubscribe(UNSUB_TOPICS)
        if result != mqtt.MQTT_ERR_SUCCESS:
            log_err(f"Unsubscription to topics {UNSUB_TOPICS} failed")
        # No message is published anymore after the offline message
        while lastPublish != None: # There are messages that need to be published
            pass
        client.disconnect()
        client.loop_stop()
    except:
        pass
    # Log files exit procedure
    try:
        errfp.close()
    except:
        pass
    # ttyRPMSGx exit procedure
    try:
        m4ch.close()
    except NameError:
        pass # m4ch does not exist when the CM4-CA7 interface is still not opened
    exit()

def fatal_err(err_msg:str):
    global lastPublish
    log_err(err_msg)
    pubLock.acquire()
    lastPublish = client.publish(BOARD_TOPIC_ERROR,payload=err_msg+f" on {BOARD_ID}",qos=BOARD_QOS_ERROR).mid
    pubLock.release()
    exit_procedure()

if __name__ == "__main__":
    
    # Error log file setup
    if not os.path.isdir(LOG_ROOT):
        os.makedirs(LOG_ROOT)

    errfp = open(ERR_FILE,"a")

    def log_err(msg:str):
        print(f"[ERROR] {msg}")
        errfp.write(f"[{time.time()}] {msg}\n")
        errfp.flush()

    # MQTT client setup
    client = mqtt.Client(callback_api_version=MQTT_CALLBACK_VERS,protocol=MQTT_PROTOCOL_VERS,client_id=BOARD_ID)
    # NOTE: The will is sent each time the board disconnects unexpectedly, so it is sent each time it is suspended.
    # However, since it is sent after the disconnection, so when the board is suspending, it may be received by the
    # user client only when the message is actually published, so when the board wakes-up again.
    #client.will_set(BOARD_TOPIC_STATUS, payload=f"{BOARD_ID} connection lost", qos=BOARD_QOS_STATUS, retain=True)    
    client.on_message = on_message
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    client.on_publish = on_publish
    #client.on_unsubscribe = on_unsubscribe
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    # Connecting after calling loop_start() can result in strange behaviours
    client.loop_start()
    while not client.is_connected():
        pass

    # Retrieve the M4 state
    #with open(RPROC_STATE_FILE,"r") as rproc_fp:
    #    start_time = time.time()
    #    while rproc_fp.read() != RPROC_RUN:
    #        if time.time() - start_time > RPROC_RDY_TO:
    #            fatal_err("CM4-CA7 comm. init error")
    
    # Find CM4-CA7 RPMsg interface
    #try:
    #    ttyRPMSGx = sp.run(shSplit(f"find /dev -regex \"{TTY_PATTERN}\""),capture_output=True,check=True)
    #    ttyRPMSGx = str(ttyRPMSGx.stdout[:-1],'utf-8') # Retrieve stdout (bytes object) and remove \n
    #    #print(ttyRPMSGx)
    #except sp.CalledProcessError:
    #    fatal_err("Failed to retrieve CM4-CA7 comm. interface")

    # Open a stream to the M4-A7 rpmsg interface
    # The interface is not seekable so the buffer size needs to be set to zero (only possible in binary mode)
    # NOTE: the stream should be opened before initializing the connection with the M4 because it is only possible to see
    # the data sent by the M4 after the stream is opened on this side
    m4ch = open(ttyRPMSGx,'w+b',buffering=0)
    os.set_blocking(m4ch.fileno(),False)             # The actions on the stream are non-blocking
        
    #print(f"TTY: {m4ch.isatty()}")

    # This step is normally done by the setup service
    if len(sys.argv) == 2 and sys.argv[1] == COMM_INIT:
        print("Initializing RPMsg communication")
        # RPMsg initialization
        # Send a message to the M4 to let it know the address of the A7
        # Communication over Virtual UART (over RPMsg) won't work without this step

        # Let the M4 know the A7 address and initialize the Analog watchdog
        # Threshold transmission format: <low_thr>(mV);<high_thr>(mV)
        m4ch.write(INITIAL_THR)
    
    # Register last ethernet wake-up event
    if((lastEthWuTime := monitor_ethWakeUp()) == None):
        # Not being able to distinguish the wake-up source is a major problem
        log_err("Cannot monitor the last ethernet wake-up event")
        exit_procedure()
    # Start M4 message reception interval
    lastMsgTime = time.time()
    
    # NOTE: up to this point no error is reported because the first start of the program
    # should be SUPERVISED

    while True: # Main loop

        ### NEW THRESHOLD ###
        # If a new threshold needs to be set, put the M4 in a wait state so that it does not send
        # out of window data before this operations is complete (A7 receives the "threshold set" ack)
        # In particular, telling the M4 to wait avoids that it sends new data while the A7 is sending the threshold
        if thrToSet:
            print("Waiting for threshold...")
            thrUpdStart = time.time()
            while not thrReceived:
                if time.time() - thrUpdStart > THR_MSG_INTERVAL:
                    break
            if not thrReceived:
                err_msg = f"Threshold wait time ({THR_MSG_INTERVAL}s) exceeded"
                log_err(err_msg)
                pubLock.acquire()
                lastPublish = client.publish(BOARD_TOPIC_ERROR,payload=err_msg+f" on {BOARD_ID}",qos=BOARD_QOS_ERROR).mid
                pubLock.release()
                thrFlagLock.acquire()
                thrToSet = False
                thrReceived = False
                thrFlagLock.release()
                # The A7 interface and the M4 firmware do not need to be restarted in this case because there is no
                # communication issue between CM4 and CA7
                # The user may want to try the update again so let the A7 stay awake for a while 
                lastMsgTime = time.time()
                continue

            if m4ch.write(WAIT4THR) == None:
                fatal_err("Cannot start the threshold change procedure")

            print("Starting threshold update")
            thrUpdStart = time.time()
            msgRec = None
            while (msgRec := m4ch.read()) == None: # Wait for M4 response
                if time.time() - thrUpdStart > THR_MSG_INTERVAL:
                    break
            if msgRec == None:
                fatal_err("CM4 did not respond to threhsold update request")
            elif msgRec != RDY4OP:
                # There were out of window data on the channel
                mqttData =  process_rawData(msgRec)
                send_mqttData(mqttData)
                # If there is a threshold to send do not allow the M4 to send new out of window data
                # The channel M4->A7 has to be free in order for the M4 to send the "threshold setting success" ack 
                lastMsgTime = time.time()
                
            print("Sending new threshold to M4")           
            if m4ch.write(bytes(newThr,"utf-8")) == None:
                fatal_err("Cannot send the new threshold to the M4")

            thrUpdStart = time.time()
            thrAck = None
            while (thrAck := m4ch.read()) == None:
                if time.time() - thrUpdStart > THR_MSG_INTERVAL:
                    break
            if thrAck != THR_SET: # Something went wrong
                fatal_err(f"CM4 error while setting the threshold")
            
            print(f"New threshold [{newThr}] has been set")
            #print(f"Acknowledge: {thrAck}")
            pubLock.acquire()
            lastPublish = client.publish(THR_TOPIC_ACK,payload=BOARD_ID,qos=THR_QOS_ACK).mid
            pubLock.release()

            # Send the previously skipped (so that the A7 could recieve the "threshold set" ack) "data elaborated acknowledge"
            # The same ack used to tell the M4 it can send other out of window data is also used to signal 
            # the M4 that it can now send again data.
            # In fact, the out of window data have already been read and the M4 is still not authorized
            # to send new data so there is no risk for not yet processed out of window data to be in the channel
            if m4ch.write(RDY4TR) == None:
                fatal_err(f"Cannot acknowledge the CM4")

            # Flags the end of the threshold update procedure 
            thrFlagLock.acquire()
            thrToSet = False
            thrReceived = False
            thrFlagLock.release()

        ### OUT OF WINDOW DATA ###
        # Start listening to M4
        #while (sensorData := m4ch.read()) != None:
        sensorData = m4ch.read()     
        if(sensorData != None):
            mqttData = process_rawData(sensorData)
            send_mqttData(mqttData)
            if m4ch.write(RDY4TR) == None:
                fatal_err(f"Cannot acknowledge the CM4")
            lastMsgTime = time.time()

        ### SUSPENSION ###

        # NOTE: SUSPENSION PROCESS
        # The A7 should suspend only when it does not have to communicate with the M4 anymore and there are no new messages 
        # from M4 for a certain time. The former statement identifies the case where the A7 has to communicate the threshold
        # to the M4. In this scenario the A7 cannot suspend. The latter statement identifies the case where the A7 does not
        # receive out of window data for a certain period of time, during which the A7 checks for messages from the M4.
        # This should be done after every event that wakes the A7 from suspension. The events that can do so are:
        # 1. New Threshold received
        #   In this case the A7, waken up through ethernet, communicates the threshold to the M4 and, after finishing this operation,
        #   enables it to send new data. In fact, it would not make sense to prevent the M4 from sending new messages 
        #   for a certain time and put the A7 to sleep if the M4 has new out of window data to communicate. Those data
        #   would just be sent after the A7 goes to sleep, waking it up again. It is better to just read the M4 and suspend the
        #   A7 only when the M4 does not send data for a while.
        # 2. New data received from M4
        #   The A7 is waken up when the IPCC channel is flagged as occupied by the M4. At this point the A7 just needs to read
        #   the data the M4 sends to it. The A7 is suspended again only when there a no data for a while.
        #
        # The suspension process follows these steps:
        # 1. Send a message (i.e. WAIT4SUSP) to the M4 to signal the A7 wants to go to sleep
        # 2.a Wait for M4 response. It can be:
        #     - RDY4OP: the A7 can proceed with the suspension operation --> go to step 3 
        #     - Out of window data already on the channel: read the out of window data on the channel
        #           before proceeding --> go to step 2.b
        #     These are the same responses used for the threshold update procedure. 
        # 2.b Read the channel but do not grant the permission to send new data to the M4 and
        #     reset the activity interval --> wait for the interval to expire and restart from step 1
        # 3. Suspend the A7

        # The only messages sent by the board to the user client are errors, out of window data and threshold
        # update ack. All these messages need to be sent before the processor suspends.
        if SUSPEND:
            if lastPublish == None and (time.time()-lastMsgTime > M4_MSG_INTERVAL):
                #print(time.time())
                msgSent = m4ch.write(WAIT4SUSP)
                if msgSent == None:
                    err_msg = "Cannot start the suspension procedure"
                    log_err(err_msg)
                    pubLock.acquire()
                    lastPublish = client.publish(BOARD_TOPIC_ERROR,payload=err_msg+f" on {BOARD_ID}",qos=BOARD_QOS_ERROR).mid
                    pubLock.release()
                    SUSPEND = 0         # Blocks suspension
                    continue            # Skip to next iteration

                suspStart = time.time()
                m4Resp = True
                while (msgRec := m4ch.read()) == None: # Wait for M4 response
                    if time.time() - suspStart > SUSP_M4_RDY_TO:
                        m4Resp = False
                        break                        
            
                if m4Resp == False:                        
                    err_msg = f"CM4 response time before suspension ({SUSP_M4_RDY_TO}s) exceeded"
                    log_err(err_msg)
                    pubLock.acquire()
                    lastPublish = client.publish(BOARD_TOPIC_ERROR,payload=err_msg+f" on {BOARD_ID}",qos=BOARD_QOS_ERROR).mid
                    pubLock.release()
                    SUSPEND = 0
                    continue

                if msgRec == RDY4OP:
                    print(f"Starting processor stop... [{time.time()}]")
                    
                    if DISCONN_B4SUS:
                        client.disconnect()
                        while client.is_connected():
                            pass
                        client.loop_stop()

                    # Stop the A7 processor when the threshold has been set
                    try:
                        sp.run(['systemctl', 'suspend'],check=True)
                    except sp.CalledProcessError: # Commands return a non zero code
                        #tb.format_exc() --> stack trace as a string
                        err_msg = "MPU suspension failed"
                        log_err(err_msg)
                        pubLock.acquire()
                        lastPublish = client.publish(BOARD_TOPIC_ERROR,payload=err_msg+f" on {BOARD_ID}",qos=BOARD_QOS_ERROR).mid
                        pubLock.release()
                    else:
                        time.sleep(5) # The system needs some time to go to sleep
                        print(f"Resuming processor activities... [{time.time()}]")

                        # Reconnect if the board was disconnected from the broker while sleeping
                        # NOTE: if the connection is not explicitly closed, even if the client is disconnected by the broker
                        # because the session expired, client.is_disconnected() will still return True
                        #if not client.is_connected():
                        #    print("Client not connected")
                        #    while lastPublish != None:
                        #        pass
                        #    client.loop_stop()
                        #    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
                        #    # Connecting after calling loop_start() can result in strange behaviours
                        #    client.loop_start()
                        #    while not client.is_connected():
                        #        pass
                        
                        if DISCONN_B4SUS:
                            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
                            # Connecting after calling loop_start() can result in strange behaviours
                            client.loop_start()
                            while not client.is_connected():
                                pass

                        #print(threading.enumerate())

                        tmpEthWuTime = monitor_ethWakeUp()
                        #print(f"New eth event time: {tmpEthWuTime}")
                        #print(f"Old eth event time: {lastEthWuTime}")
                        if(tmpEthWuTime == None):
                            err_msg = "Could not monitor ethernet wake-up event"
                            log_err(err_msg)
                            pubLock.acquire()
                            lastPublish = client.publish(BOARD_TOPIC_ERROR,payload=err_msg+f" on {BOARD_ID}",qos=BOARD_QOS_ERROR).mid
                            pubLock.release()
                            exit_procedure()
                        elif(tmpEthWuTime != lastEthWuTime):
                            print("[INFO] Woke-up through ethernet")
                            # The wake-up source is Ethernet (i.e. there is a new threshold to set)
                            lastEthWuTime = tmpEthWuTime # Update the last eth wake-up event time
                            # NOTE: the threshold update process is flagged here but proceeds only when the message with
                            # the threshold is received.
                            # Flagging it here avoids to wait too much for the wake-up in the user client and make the board
                            # suspend again. (thrToSet == True could be used as condition not to start the suspension process)
                            thrFlagLock.acquire()
                            thrToSet = True
                            thrFlagLock.release()
                        else: 
                            # The wake-up source is the IPCC (i.e. there are new data from M4)
                            print("[INFO] Woke-up through IPCC")
                    lastMsgTime = time.time() # Reset the "no messages" interval
                else:
                    # There were out of window data on the channel
                    print(f"[INFO] Suspension process interrupted")
                    mqttData =  process_rawData(msgRec)
                    send_mqttData(mqttData)
                    m4ch.write(RDY4TR)
                    lastMsgTime = time.time()
                # print(lastMsgTime)
    
# NOTE: IPCC
# According to the STM IPCC documentation (https://wiki.st.com/stm32mpu/wiki/IPCC_internal_peripheral)
# "Once the 'sender' processor has posted the communication data in the memory, 
# it sets the channel status flag to occupied." so the A7 should not be able to retrieve data before the
# M4 has finished sending them.
# However, the M4 might still flood the channel and start another communication before the A7 has even retrieved the 
# previous one. This may cause the A7 to retrieve incomplete data since the M4 may still be sending data. In fact,
# in this case, the A7 does not need to wait for the M4 to send the interrupt for the second transmission since it has not
# serviced the one from the first transmission yet. Moreover, if the channel is being flooded the listening subprocess
# cannot end so the timeout will expire and the subprocess will end even though the M4 may still be sending data.
# Technically there would be no need for an explicit acknowledge since 
# "The 'receiver' processor clears the flag when the message is treated". However, since we are working at a higher level
# and the M4 may put data on the channel faster than the subprocess can read them, the channel appears as always occupied.
# Using an HAL_Delay() on the M4 side is not reliable. In fact, even if waiting for some milliseconds may be enough in one
# case, it may still create problems when the A7 workload is higher.
# P.S. The web page linked before also explains how to setup the IPCC on CubeMX 

# NOTE: Wake-up with remote packet (unicast activity) or magic packet (wake-on-lan)
# Both solutions have pros and cons, but neither of them works best in all scenarios.
# The unicast one may be better when the user client communicates directly with the boards through MQTT (i.e. "ARCH 2")
# because it does not need another node in the boards local network (i.e. the proxy client) to wake them up.
# However, this solution causes to wake-up the boards on EVERY unicast packet they receive. This may be accepted or not,
# useful even, depending on the specific application of the system. Moreover, each time the "session expired" interval
# for a session expires, the broker sends a DISCONNECT packet to the board that has been disconnected. This causes the board
# to wake-up to establish a new connection, even though it may not be necessary at that time. It means that the board is
# consuming energy even though it could have remained suspended. The power wasted is higher the longer the maximum inactivity
# time of a board. Obviously the proxy client is an additional node, so it consumes power too. To choose the best solution
# an accurate power analysis should be performed considering each scenario the system may face while deployed.
# When "ARCH 1" is considered the two solutions are not so different since the proxy client is needed anyway.
# Remote packet wake-up should be slightly more performant since there is no need for the additional magic packet.

# The project implements the solution with magic packets because it is more complex to implement when "ARCH 2" is used.
# Using the unicast activity simply requires to change the flag "g" with "u" inside the wol@end0.service and cut the
# communication between the proxy client and the user client, making the latter directly send the update data structure
# to the boards.  