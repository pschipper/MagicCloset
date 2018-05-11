'''
/*
 * Copyright 2010-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *
 *  http://aws.amazon.com/apache2.0
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */
 '''

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from sens_SI7021 import *
from sens_ADC import *
import datetime
import logging
import time
import argparse
import json
import pigpio

# Define constants (later define in config file?)
host = "a18zc4nl7slca7.iot.us-east-2.amazonaws.com"
rootCAPath = "/home/pi/mc/root.pem"
certificatePath = "/home/pi/mc/cert.pem"
privateKeyPath = "/home/pi/mc/private.pem"
clientId = "MC-1126-1-1"
topic = "telem"

# Custom MQTT message callback
def customCallback(client, userdata, message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")

# Build telem message function
def telemMessage(client, ts, temp, rh, light, moisture, pump):
    message = {
        'id': clientId
    }
    message['ts'] = ts
    message['temp'] = round(temp,2)
    message['rh'] = round(rh,2)
    message['light'] = round(light,2)
    message['moisture'] = round(moisture,2)
    message['pump'] = pump
    messageJson = json.dumps(message)

    # Send message
    try:
        mqttClient.publish(topic, messageJson, 1)
        print('--Published a message to topic %s: %s' % (topic, messageJson))
    except:
        print('** exception')

# Configure logging
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Init AWSIoTMQTTClient
mqttClient = None
mqttClient = AWSIoTMQTTClient(clientId)
mqttClient.configureEndpoint(host, 8883)
mqttClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
mqttClient.configureAutoReconnectBackoffTime(1, 128, 20)
mqttClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
mqttClient.configureDrainingFrequency(2)  # Draining: 2 Hz
mqttClient.configureConnectDisconnectTimeout(60)  # sec
mqttClient.configureMQTTOperationTimeout(30)  # sec

# Connect and subscribe to AWS IoT
time.sleep(60) # lazy way to wait for network interfaces to come up
mqttClient.connect()

# Subscribe to topic
#mqttClient.subscribe(topic, 1, customCallback)

# Sensor interfaces
sens_i2c = SI7021()
sens_adc = ADC()

# Pump IO
piio = pigpio.pi()

# Time since pump constant
tsPump = (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()

try:
    while True:
        # Pump off
        piio.write(13,0)

        # Get posix time stamp
        ts = (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()

        # Read sensors
        moisture = sens_adc.readMoisture()
        temp = sens_i2c.readTemp()
        rh = sens_i2c.readRH()
        light = sens_adc.readLight()

        # If Pump
        if((moisture < 10) and ((ts - tsPump) > 2*60*60)): # 2 hours to seconds
            # Send telem message with pump off and then on for nice edges
            telemMessage(mqttClient, ts, temp, rh, light, moisture, 0)
            time.sleep(0.5)
            ts = (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()
            telemMessage(mqttClient, ts, temp, rh, light, moisture, 10)

            # Update time since pump
            tsPump = ts

            # Run pump
            piio.write(13,1)
            time.sleep(5)
            piio.write(13,0)

        #Update time stamp
        ts = (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()

        # Send telem message with pump off
        telemMessage(mqttClient, ts, temp, rh, light, moisture, 0)

        # Sleep until next time
        time.sleep(60*10)
except KeyboardInterrupt:
    pass

