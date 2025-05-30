from board_header import *

# GLOBAL VARIABLES
pubLock         = threading.Lock()  # Lock for lastPublish
thrFlagLock     = threading.Lock()  # Lock for thrToSet

lastPublish     = None              # Mid of the last published message
                                    # The A7 waits for this message to be published before going to sleep
# Threhsold update variables
thrToSet = False            # Threshold update procedure required when True
newThr = None               # New threshold

# CM4-CA7 comm. interface
# NOTE: this is the name of the first interface initialized after flashing the CM4.
# In case there is a communication failure and another interface is initialized its name will be "/dev/ttyRPMSG1".
# However, in this case, the CM4, if not the entire system, will probably need a reboot/reflash so the interface will
# be created again as /dev/ttyRPMSG0
ttyRPMSGx = "/dev/ttyRPMSG0"

# Fileno and file object
m4ch = None
ttyRPMSGx_fd = None 

# File descriptors of error and debug files
errfp = None
dbgfp = None

# MQTT client
client = None

# User defined class for application protocol errors
class AppException(Exception):
    def __init__(self, message):
        # Initialize the parent class object to behave like a standard exception
        super().__init__(message)
        self.message = message

    def __str__(self): # to print the value
        return self.message

def on_connect(client:mqtt.Client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        log_err(f"Connection to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} failed with reason code {reason_code}: "+mqtt.connack_string(reason_code))
        log_err("Trying to reconnect...")
    else:
        log_dbg(f"Successfully connected to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
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
#        log_dbg(f"Unsubscription {rc}")

def on_publish(client, userdata, mid, reason_code, properties):
    global lastPublish
    if reason_code.is_failure:
        log_err(f"Publish call failed: mid={mid} | rc={reason_code}")
    # Needs to be checked even if the publish failed, otherwise the A7 may hang
    pubLock.acquire()
    # Lock acquired before reading because lastPublish should not be changed while reading
    #log_dbg(f"MID: {mid}")
    #log_dbg(f"LP: {lastPublish}")
    if mid == lastPublish:
        #log_dbg("Nothing else to publish")
        # NOTE: If you user the client.loop_start() method then this starts a new thread in the background to run
        # the network loop and all the callbacks on.
        # All callbacks block the execution of the network thread, this is why you should not run long 
        # running or blocking tasks directly in the callback.
        lastPublish = None    # No message unpublished
    pubLock.release()

#callback function for incoming threshold
def on_message(client, userdata, message):
    global thrToSet
    global newThr
    #if message.topic == THR_TOPIC_UPDATE:
    message.payload = message.payload.decode('utf-8')
    thrFlagLock.acquire()
    if not thrToSet:
        log_dbg("Threshold received")
        # NOTE: If the threhsold was already received there is an ongoing threshold update process.
        # This case is handled discarding the latest threshold. The client that issued the discarded update
        # will need to retry the update.
        
        newThr = json.loads(message.payload)
        if BOARD_ID in newThr[UPDATE_KEYS[0]]:
            log_dbg("Threshold update required")
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
    else:
        log_dbg("Message received while already updating the threshold")
    thrFlagLock.release()
    log_dbg(f"[{message.topic}] {message.payload}")
    
def on_disconnect(client:mqtt.Client, userdata, flags, reason_code, properties):
    if reason_code.is_failure: # Disconnection problem  
        log_err(f"Unexpected disconnection from broker (RC={reason_code}). Attempting to reconnect...")
    else:
        log_dbg(f"Correctly disconnected from {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")

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
        #log_dbg(f"Data #{i/DATA_SIZE}: {sensorData[i:i+DATA_SIZE-1]}")
        #log_dbg(f"Data #{i/DATA_SIZE}: {int.from_bytes(sensorData[i:i+DATA_SIZE-1],byteorder='little',signed=False)}")
        mqttData.append(DATA_TYPE.from_bytes(sensorData[i:i+DATA_SIZE-1],byteorder='little',signed=False))

    #log_dbg(mqttData)
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
        dbgfp.close()
    except:
        pass
    # ttyRPMSGx exit procedure
    try:
        m4ch.close()
        os.close(ttyRPMSGx_fd)
    except:
        pass # m4ch does not exist when the CM4-CA7 interface is still not opened
    exit(1) # Exit with failure code to 
    
def log_err(msg:str):
    errfp.write(f"[{time.time()}] {msg}\n")
    errfp.flush()

def log_dbg(msg:str):
    dbgfp.write(f"[{time.time()}] {msg}\n")
    dbgfp.flush()

if __name__ == "__main__":
    try:
        # NOTE: Even though the main thread errors are properly handled, the deployment of the program
        # should be carefully supervised since not all errors (i.e. runtime errors) are delivered to the user client
 
        # Error log file setup
        if not os.path.isdir(LOG_ROOT):
            os.makedirs(LOG_ROOT)
        
        errfp = open(ERR_FILE,"a")
        dbgfp = open(DBG_FILE,"a")

        #log_dbg(f"PID: {os.getpid()}")
        
        # MQTT client setup
        client = mqtt.Client(callback_api_version=MQTT_CALLBACK_VERS,protocol=MQTT_PROTOCOL_VERS,client_id=BOARD_ID)
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
        #    #log_dbg(ttyRPMSGx)
        #except sp.CalledProcessError:
        #    fatal_err("Failed to retrieve CM4-CA7 comm. interface")

        # Open a stream to the M4-A7 rpmsg interface
        # The interface is not seekable so the buffer size needs to be set to zero (only possible in binary mode)
        # NOTE: the stream should be opened before initializing the connection with the M4 because it is only possible to see
        # the data sent by the M4 after the stream is opened on this side
        
        # O_NOCTTY avoids that the terminal device becomes the controlling terminal for the process
        # O_NONBLOCK allows to read in non-blocking mode
        ttyRPMSGx_fd = os.open(ttyRPMSGx,os.O_RDWR | os.O_APPEND | os.O_NOCTTY | os.O_NONBLOCK)
        
        m4ch = os.fdopen(ttyRPMSGx_fd,"r+b",buffering=0)

        # This step is normally done by the setup service
        if len(sys.argv) == 2 and sys.argv[1] == COMM_INIT:
            log_dbg("Initializing RPMsg communication")
            # RPMsg initialization
            # Send a message to the M4 to let it know the address of the A7
            # Communication over Virtual UART (over RPMsg) won't work without this step

            # Let the M4 know the A7 address and initialize the Analog watchdog
            # Threshold transmission format: <low_thr>(mV);<high_thr>(mV)
            if m4ch.write(INITIAL_THR) == None:
                raise AppException("Cannot initialize the CM4-CA7 communication")
            # NOTE: Since the file is opened in non-blocking mode a None return value does not necessarily
            # mean that nothing will be written, just that nothing is readily written before the function returns.
            # It is up to the user to decide whether to be cautious about this or not. In fact, not to ack a data 
            # transmission from the CM4 (i.e. writing the ack) may lead to block forever the MCU transmissions.
            
        while True: # Main loop

            ### NEW THRESHOLD ###
            # If a new threshold needs to be set, put the M4 in a wait state so that it does not send
            # out of window data before this operations is complete (A7 receives the "threshold set" ack)
            # In particular, telling the M4 to wait avoids that it sends new data while the A7 is sending the threshold
            if thrToSet:
                if m4ch.write(WAIT4THR) == None:
                    raise AppException("Cannot start the threshold change procedure")

                #log_dbg("Starting threshold update")
                thrUpdStart = time.time()
                msgRec = None
                while (msgRec := m4ch.read()) == None: # Wait for M4 response
                    if time.time() - thrUpdStart > THR_MSG_INTERVAL:
                        break
                if msgRec == None:
                    raise AppException("CM4 did not respond to threhsold update request")
                elif msgRec != RDY4OP:
                    # There were out of window data on the channel
                    mqttData =  process_rawData(msgRec)
                    send_mqttData(mqttData)
                    # If there is a threshold to send do not allow the M4 to send new out of window data
                    # The channel M4->A7 has to be free in order for the M4 to send the "threshold setting success" ack 

                #log_dbg("Sending new threshold to M4")
                if m4ch.write(bytes(newThr,"utf-8")) == None:
                    raise AppException("Cannot send the new threshold to the M4")

                thrUpdStart = time.time()
                thrAck = None
                while (thrAck := m4ch.read()) == None:
                    if time.time() - thrUpdStart > THR_MSG_INTERVAL:
                        break
                if thrAck != THR_SET: # Something went wrong
                    raise AppException(f"CM4 error while setting the threshold")
                
                log_dbg(f"New threshold [{newThr}] has been set")
                #log_dbg(f"Acknowledge: {thrAck}")
                pubLock.acquire()
                lastPublish = client.publish(THR_TOPIC_ACK,payload=BOARD_ID,qos=THR_QOS_ACK).mid
                pubLock.release()

                # Send the previously skipped (so that the A7 could recieve the "threshold set" ack) "data elaborated acknowledge"
                # The same ack used to tell the M4 it can send other out of window data is also used to signal 
                # the M4 that it can now send again data.
                # In fact, the out of window data have already been read and the M4 is still not authorized
                # to send new data so there is no risk for not yet processed out of window data to be in the channel
                if m4ch.write(RDY4TR) == None:
                    raise AppException(f"Cannot acknowledge the CM4")

                # Flags the end of the threshold update procedure 
                thrFlagLock.acquire()
                thrToSet = False
                thrFlagLock.release()

            ### OUT OF WINDOW DATA ###
            # Listen to M4
            sensorData = m4ch.read()     
            if(sensorData != None):
                mqttData = process_rawData(sensorData)
                send_mqttData(mqttData)
                if m4ch.write(RDY4TR) == None:
                    raise AppException(f"Cannot acknowledge the CM4")
    except AppException as err_msg:
        log_err(err_msg)
        pubLock.acquire()
        lastPublish = client.publish(BOARD_TOPIC_ERROR,payload=err_msg+f" on {BOARD_ID}",qos=BOARD_QOS_ERROR).mid
        pubLock.release()
    except:
        # Print exception trace to stderr (it is linked to journal)
        traceback.print_exc() 
    finally:
        exit_procedure()