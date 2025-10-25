import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self):
        self.client = None
        self.connected = False
        self.config = {}
    
    def configure(self, host: str, port: int, username: str = None, password: str = None, topic: str = 'homeassistant/face_detection'):
        self.config = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'topic': topic
        }
    
    def connect(self):
        try:
            if not self.config.get('host'):
                logger.warning("MQTT not configured")
                return False
            
            # Try paho-mqtt 2.x first, fallback to 1.x
            try:
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            except AttributeError:
                # paho-mqtt 1.x
                self.client = mqtt.Client()
            
            if self.config.get('username') and self.config.get('password'):
                self.client.username_pw_set(self.config['username'], self.config['password'])
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            self.client.connect(self.config['host'], int(self.config['port']), 60)
            self.client.loop_start()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when MQTT connects (compatible with paho-mqtt 1.x and 2.x)"""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker")
            # Publish Home Assistant auto-discovery config on connect
            self._publish_ha_discovery()
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_disconnect(self, client, userdata, flags=None, rc=None, properties=None):
        """Callback when MQTT disconnects (compatible with paho-mqtt 1.x and 2.x)"""
        self.connected = False
        # Handle both v1 and v2: in v2, 'flags' is actually 'disconnect_flags', 'rc' is 'reason_code'
        reason = rc if rc is not None else flags
        logger.warning(f"Disconnected from MQTT broker: {reason}")
    
    def _publish_ha_discovery(self):
        """Publish Home Assistant MQTT Discovery config for sensors"""
        try:
            # Create sensor for last detected person
            discovery_config = {
                "name": "FaceInsight Last Person",
                "unique_id": "faceinsight_last_person",
                "state_topic": "homeassistant/sensor/faceinsight/state",
                "json_attributes_topic": "homeassistant/sensor/faceinsight/attributes",
                "icon": "mdi:face-recognition",
                "device": {
                    "identifiers": ["faceinsight"],
                    "name": "FaceInsight",
                    "model": "Face Recognition System",
                    "manufacturer": "FaceInsight"
                }
            }
            
            # Publish discovery config
            discovery_topic = "homeassistant/sensor/faceinsight/config"
            self.client.publish(discovery_topic, json.dumps(discovery_config), qos=1, retain=True)
            logger.info("Published Home Assistant auto-discovery config")
        except Exception as e:
            logger.error(f"Error publishing HA discovery: {e}")
    
    def publish_detection(self, name: str, nickname: Optional[str], score: float, age: int = 0, gender: str = 'Unknown'):
        """
        Publish face detection to MQTT with Home Assistant format
        gender: 'Male', 'Female', or 'Unknown'
        """
        if not self.connected or not self.client:
            logger.warning("MQTT not connected, attempting to reconnect...")
            self.connect()
        
        try:
            # Publish state (person name)
            state_topic = "homeassistant/sensor/faceinsight/state"
            self.client.publish(state_topic, name, qos=1, retain=True)
            
            # Publish attributes (detailed info)
            attributes = {
                "name": name,
                "nickname": nickname if nickname else name,
                "score": round(score * 100),
                "age": age,
                "gender": gender,
                "timestamp": datetime.now().isoformat(),
                "event": "face_detected"
            }
            
            attributes_topic = "homeassistant/sensor/faceinsight/attributes"
            self.client.publish(attributes_topic, json.dumps(attributes), qos=1, retain=True)
            
            # Also publish to custom topic for compatibility (with retain)
            custom_topic = self.config.get('topic', 'homeassistant/face_detection')
            payload = {
                "event": "face_detected",
                "name": name,
                "score": round(score * 100),
                "nickname": nickname if nickname else name,
                "age": age,
                "gender": gender,
                "timestamp": datetime.now().isoformat()
            }
            self.client.publish(custom_topic, json.dumps(payload), qos=1, retain=True)
            
            logger.info(f"Published detection to MQTT (HA Discovery): {name} (score={round(score * 100)}, age={age}, gender={gender})")
            return True
        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")
            return False
    
    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("Disconnected from MQTT")
