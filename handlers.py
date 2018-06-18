import sys
import logging
import json
import paho.mqtt.client as mqtt
import datetime


LOG = logging.getLogger("kattvhask")
LOG.addHandler(logging.StreamHandler(sys.stdout))
LOG.setLevel(logging.DEBUG)

def event_msg_converter(o):
    if isinstance(o, datetime.datetime):
        return str(o)

class Mqtt:
    """mqtt handler that connects and allows us to publish messages to our mqtt server.

    This allows easily integration between various systems.
    """
    def __init__(self, topic, server, username=None, password=None):
        self._topic = topic
        self._server = server
        self.mqttc = mqtt.Client()

        # Setup correct callbacks
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_publish = self.on_publish
        self.mqttc.on_disconnect = self.on_disconnect
        LOG.info("MQTT handler initialized")

    def on_disconnect(self, mqttc, obj, rc):
        LOG.debug(f"on_disconnect: rc: {rc}, obj: {obj}")

    def on_connect(self, mqttc, obj, flags, rc):
        LOG.debug(f"on_connect: rc: {rc}, flags: {flags}, obj: {obj}")

    def on_publish(self, mqttc, obj, mid):
        LOG.info("on_publish called")

    def publish(self, payload: dict):
        msg_info = self.mqttc.publish(self._topic, payload)
        return msg_info

    def __call__(self, event:  dict):
        payload_s = json.dumps(event, default=event_msg_converter)
        self.publish(payload_s)

        LOG.info(f"Sent MQTT msg: {event}")
        print(f"Sent MQTT msg: {event}")
        return True
