#!/usr/bin/env python
# (c) 2021 Andreas Böhler
# License: Apache 2.0

from easysnmp import Session
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

            if 'sessionwrite' in dev:
                if dev['sessionwrite'].set('1.3.6.1.4.1.42505.8.3.5.0', state, snmp_type='INTEGER'):
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

try:
    mqttc.connect(config['mqtt']['host'], config['mqtt']['port'], 60)
except:
    print('Could not connect to MQTT, will now quit')
    sys.exit(1)
mqttc.loop_start()

# Set up discovery structure

def connect_and_setup():
    for dev in config['denkovi']:
        dev['state'] = 0
        if 'sessionread' in dev and 'sessionwrite' in dev:
            print('Already connected to ' + dev['id'] + ', continuing')
            continue
        try:
            dev['sessionread'] = Session(hostname=dev['host'], remote_port=dev['port'], community=dev['communityread'], version=2)
            dev['sessionwrite'] = Session(hostname=dev['host'], remote_port=dev['port'], community=dev['communitywrite'], version=2)
        except:
            print('Error creating session, device not available?')
            continue
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
            
            #payload = ""
            payload = json.dumps(payload)
            mqttc.publish(dtopic, payload=payload, retain=True)
            mqttc.publish(topic + '/state', payload="OFF", retain=True)
            mqttc.subscribe(topic + "/set")

while True:
    for dev in config['denkovi']:
        if 'sessionread' in dev:
            try:
                state = dev['sessionread'].get('1.3.6.1.4.1.42505.8.3.5.0')
                state = int(state.value)
            except:
                print('Could not get value, connection lost?')
                del dev['sessionread']
                del dev['sessionwrite']
                connect_and_setup()
                continue
        else:
            connect_and_setup()
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
