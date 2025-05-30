#!/usr/bin/python
# Code adapted starting from https://github.com/seanauff/WOL-proxy 
from wakeonlan import send_magic_packet
from header import *

# private env variables
MQTT_CLIENT_ID     = os.getenv('MQTT_CLIENT_ID',"WOL-proxy")
MQTT_USERNAME      = os.getenv('MQTT_USERNAME',"")
MQTT_PASSWORD      = os.getenv('MQTT_PASSWORD',"")
WOL_BROADCAST_ADDR = os.getenv('WOL_BROADCAST_ADDR',"255.255.255.255")
#print("All env vars read.")

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} with reason code {reason_code}: "+mqtt.connack_string(reason_code))

    client.publish(PROXY_TOPIC_STATUS,payload=f"{MQTT_CLIENT_ID} online",qos=PROXY_QOS_STATUS,retain=True)

    # subscribe to command topic
    client.subscribe(PROXY_TOPIC_WAKEUP, PROXY_QOS_WAKEUP)

def on_subscribe(client, userdata, mid, reason_code, properties):
    print(f"Subscribed to commands on topic \"{PROXY_TOPIC_WAKEUP}\" with QOS {reason_code[0]}.")
    print(f"Wake-On-LAN proxy service started.")  

def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"Unexpected disconnection from broker (RC={reason_code}). Attempting to reconnect...")

# callback for when the client receives a message on the subscribed topic
def on_message(client:mqtt.Client, userdata, message):
    message.payload = message.payload.decode()
    print(f"Message received with payload {message.payload}")
    macList = json.loads(message.payload)[WAKEUP_KEYS[0]]
    for mac in macList:
        if re.match(r"[0-9a-f]{2}([-:\.]?)[0-9a-f]{2}(\1[0-9a-f]{2}){4}$", mac):
            send_magic_packet(mac,ip_address=WOL_BROADCAST_ADDR)
            print(f"Magic packet sent to {mac}.")
        else:
            err_str = f"Message payload has invalid MAC address format!\nReceived message: {message.payload}"
            client.publish(PROXY_TOPIC_ERROR,payload=err_str,qos=PROXY_QOS_ERROR)

if __name__ == "__main__":
    # set up mqtt client
    client = mqtt.Client(callback_api_version=MQTT_CALLBACK_VERS,protocol=MQTT_PROTOCOL_VERS,client_id=MQTT_CLIENT_ID)
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME,MQTT_PASSWORD)
        print("Username and password set.")
    # The will is not used if the client disconnects with a proper disconnect().
    # In this case the proxy should always run so if it disconnects it happens unexpectedly, meaning that the
    # will is always sent.   
    client.will_set(PROXY_TOPIC_STATUS, payload=f"{MQTT_CLIENT_ID} offline", qos=PROXY_QOS_STATUS, retain=True)    
    client.on_connect = on_connect # on connect callback
    client.on_message = on_message # on message callback
    client.on_disconnect = on_disconnect # on disconnect callback
    client.on_subscribe = on_subscribe # on subscribe callback

    # connect to broker
    client.connect(MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)

    # start loop
    client.loop_forever()