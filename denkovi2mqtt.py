#!/usr/bin/env python
# (c) 2021 Andreas Böhler
# License: Apache 2.0

from pysnmp.hlapi import *
import paho.mqtt.client as mqtt
import socket
import json
import yaml
import os
import sys
import requests
import time
import base64

if os.path.exists('/config/denkovi2mqtt.yaml'):
    fp = open('/config/denkovi2mqtt.yaml', 'r')
    config = yaml.safe_load(fp)
elif os.path.exists('denkovi2mqtt.yaml'):
    fp = open('denkovi2mqtt.yaml', 'r')
    config = yaml.safe_load(fp)
else:
    print('Configuration file not found, exiting.')
    sys.exit(1)

def get_relay_state(host, port, community):
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community),
        UdpTransportTarget((host, port)),
        ContextData(),
        ObjectType(ObjectIdentity('1.3.6.1.4.1.42505.8.3.5.0'))
    )

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication:
        return False

    elif errorStatus:
        return False

    else:
        for varBind in varBinds:
            return int(varBind[1])

    return False

def set_relay_state(host, port, community, state):
    iterator = setCmd(
        SnmpEngine(),
        CommunityData(community),
        UdpTransportTarget((host, port)),
        ContextData(),
        ObjectType(ObjectIdentity('1.3.6.1.4.1.42505.8.3.5.0'), Integer(state))
    )

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication:
        return False

    elif errorStatus:
        return False

    else:
        return True


# Define MQTT event callbacks
def on_connect(client, userdata, flags, rc):
    connect_statuses = {
        0: "Connected",
        1: "incorrect protocol version",
        2: "invalid client ID",
        3: "server unavailable",
        4: "bad username or password",
        5: "not authorised"
    }
    print("MQTT: " + connect_statuses.get(rc, "Unknown error"))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection")
    else:
        print("Disconnected")

def on_message(client, obj, msg):
    print("Msg: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    topic = msg.topic.replace(config['mqtt']['topic'] + '/light/', '')
    name, command = topic.split('/')
    devid, relay, number = name.split('_')
    number = int(number)
    # Here we should send a HTTP request to Mediola to open the blind
    for dev in config['denkovi']:
        if dev['id'] == devid:
            if msg.payload == b"ON":
                state = dev['state'] | (1 << (number - 1))
            else:
                state = dev['state'] & ~(1 << (number - 1))

            if set_relay_state(dev['host'], dev['port'], dev['communitywrite'], state):
                dev['state'] = state
                payload = msg.payload
                mqttc.publish(config['mqtt']['topic'] + '/light/' + name + '/state', payload=payload, retain=True)

def on_publish(client, obj, mid):
    print("Pub: " + str(mid))

def on_subscribe(client, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(client, obj, level, string):
    print(string)

# Setup MQTT connection
mqttc = mqtt.Client()

mqttc.on_connect = on_connect
mqttc.on_subscribe = on_subscribe
mqttc.on_disconnect = on_disconnect
mqttc.on_message = on_message

if config['mqtt']['debug']:
    print("Debugging messages enabled")
    mqttc.on_log = on_log    
    mqttc.on_publish = on_publish

if config['mqtt']['username'] and config['mqtt']['password']:
    mqttc.username_pw_set(config['mqtt']['username'], config['mqtt']['password'])
mqttc.connect(config['mqtt']['host'], config['mqtt']['port'], 60)
mqttc.loop_start()

# Set up discovery structure

for dev in config['denkovi']:
    dev['state'] = 0
    for relay in dev['relays']:
        identifier = dev['id'] + '_relay_' + str(relay['number'])
        dtopic = config['mqtt']['discovery_prefix'] + '/light/' + \
                 identifier + '/config'
        topic = config['mqtt']['topic'] + '/light/' + identifier
        name = relay['name']
        
        payload = {
          "state_topic" : topic + '/state',
          "command_topic" : topic + '/set',
          "name" : name,
          "unique_id" : identifier,
          "device" : {
            "identifiers" : base64.b64encode(dev['host'].encode('ascii')).decode('ascii'),
            "manufacturer" : 'Denkovi',
            "name" : dev['name'],
            "model" : "SmartDEN",
          },
        }
        
        payload = json.dumps(payload)
        mqttc.publish(dtopic, payload=payload, retain=True)
        mqttc.publish(topic + '/state', payload="OFF", retain=True)
        mqttc.subscribe(topic + "/set")

while True:
    for dev in config['denkovi']:
        state = get_relay_state(dev['host'], dev['port'], dev['communityread'])
        if state is False:
            continue

        for relay in dev['relays']:
            identifier = dev['id'] + '_relay_' + str(relay['number'])
            topic = config['mqtt']['topic'] + '/light/' + identifier
            number = relay['number'] - 1
            current_state = (state & (1 << number)) == (1 << number)
            old_state = (dev['state'] & (1 << number)) == (1 << number)
            if current_state != old_state:
                if current_state:
                    payload = "ON"
                else:
                    payload = "OFF"
                
                mqttc.publish(topic + '/state', payload=payload, retain=True)

        dev['state'] = state
    time.sleep(config['general']['interval'])
