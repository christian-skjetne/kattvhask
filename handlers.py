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
        self._topic_cmds = topic + "/cmds"
        self._server = server
        self.mqttc = mqtt.Client()
        if username or password:
            self.mqttc.username_pw_set(username, password)

        # Setup correct callbacks
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_publish = self.on_publish
        self.mqttc.on_disconnect = self.on_disconnect
        self.mqttc.on_message = self.on_message
        self.mqttc.on_subscribe = self.on_subscribe
        LOG.info("MQTT handler initialized")
        LOG.info("Publish topic: {}".format(self._topic))
        LOG.info("Subscribe topic: {}".format(self._topic_cmds))

        self.mqttc.connect(self._server, 1883)
        self.mqttc.loop_start()
        self.subscribe()

    def on_disconnect(self, mqttc, obj, rc):
        LOG.debug(f"on_disconnect: rc: {rc}, obj: {obj}")
        self.stop()

    def on_connect(self, mqttc, obj, flags, rc):
        LOG.debug(f"on_connect: rc: {rc}, flags: {flags}, obj: {obj}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        LOG.debug(f"on_subscribe: userdata: {userdata}, mid: {mid}, granted_qos: {granted_qos}")

    def on_publish(self, mqttc, obj, mid):
        LOG.info("on_publish called")

    def publish(self, payload: str):
        msg_info = self.mqttc.publish(self._topic, payload)
        return msg_info

    def on_message(self, mqttc, userdata, msg: mqtt.MQTTMessage):
        LOG.info(f"on_message(userdata={userdata}, message topic={msg.topic}, payload={msg.payload})")

        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError:
            LOG.error(f"Unable to parse payload ('{msg.payload}') on topic '{msg.topic}'")
            return

        LOG.debug("Incoming message: {}".format(payload))

    def subscribe(self):
        LOG.info(f"cmds topic: {self._topic_cmds}")
        self.mqttc.subscribe(self._topic_cmds, 2)

    def stop(self):
        self.mqttc.disconnect()
        self.mqttc.loop_stop()

    def __call__(self, event:  dict):
        payload_s = json.dumps(event, default=event_msg_converter)
        msg_info = self.publish(payload_s)

        LOG.debug(f"Sent MQTT msg: {event}")

        if not msg_info.is_published():
            LOG.error("Unable to publish event to MQTT!")
            return False
        return True

    def __repr__(self):
        return f"{self.__class__.__name__}(host={self._server}, topic={self._topic})"
