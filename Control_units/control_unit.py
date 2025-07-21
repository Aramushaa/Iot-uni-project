# changelog:
# - 2025-07-21: Removed MQTT client management from this class. It is now handled by CU_instancer.
# - 2025-07-21: The class now processes messages handed to it, rather than subscribing itself.

import json
import time
import sched
import requests
import copy
from datetime import datetime
import threading # Added threading for the scheduler

# Mapping from (houseID, floorID, unitID) to deviceID for light_switch
DEVICE_ID_MAPPING = {
    (1, 1, 1): 10101, (1, 1, 2): 10102, (1, 2, 1): 10103,
    (2, 1, 1): 20101, (2, 1, 2): 20102, (2, 2, 1): 20103,
}

class Controler():
    def __init__(self, catalogAddress, mqtt_client, main_topic):
        self.catalogAddress = catalogAddress.rstrip('/')
        self.client = mqtt_client  # Use the client provided by the instancer
        self.main_topic = main_topic
        
        self.device_status_cache = {}
        self.last_motion_time = {}
        self.latest_light_level = {}

        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler.enter(10, 1, self.check_lights_off, ())
        
        # Each controller runs its own check in a separate thread
        self.thread = threading.Thread(target=self.scheduler.run)
        self.thread.daemon = True
        self.thread.start()

        self.msg_template = {
            "bn": None,
            "e": [{"n": "actuator", "u": "command", "t": None, "v": None}]
        }

    def process_message(self, topic, payload):
        """This method is called by CU_instancer to process a message."""
        try:
            parts = topic.split("/")
            if len(parts) < 6:
                print(f"[WARN] Controller received unexpected topic format: {topic}")
                return

            _, _, houseID, floorID, unitID, sensorType = parts[:6]
            key = (int(houseID), int(floorID), int(unitID))
            
            event = payload.get("e", [{}])[0]
            value = event.get("v")

            if sensorType == "motion_sensor":
                if value == "Detected":
                    self.last_motion_time[key] = time.time()
                    print(f"[ALERT] Motion in {key[0]}/{key[1]}/{key[2]}")
                    self.send_command(key, "light_switch", "ON")
            elif sensorType == "light_sensor":
                self.latest_light_level[key] = float(value)

        except (ValueError, IndexError, KeyError) as e:
            print(f"[ERROR] Controller failed to process message on topic '{topic}': {e}")

    def check_lights_off(self):
        now = time.time()
        # Use list() to create a copy, allowing safe deletion during iteration
        for key in list(self.last_motion_time.keys()):
            if now - self.last_motion_time.get(key, now) > 30:
                light_level = self.latest_light_level.get(key, 0)
                if light_level > 400:
                    h, f, u = key
                    print(f"[ACTION] No motion & bright -> Turn OFF light in {h}/{f}/{u}")
                    self.send_command(key, "light_switch", "OFF")
                    # Remove the timestamp to prevent repeatedly sending OFF command
                    del self.last_motion_time[key]
        
        # Reschedule the check
        self.scheduler.enter(10, 1, self.check_lights_off, ())

    def send_command(self, key, device_name, command):
        houseID, floorID, unitID = key
        topic = f"{self.main_topic}/commands/{houseID}/{floorID}/{unitID}/{device_name}"
        msg = copy.deepcopy(self.msg_template)
        msg["bn"] = topic
        msg["e"][0]["t"] = str(time.time())
        msg["e"][0]["v"] = command
        self.client.myPublish(topic, msg)
        print(f"[CMD] {command} -> {topic}")
        self.update_catalog(key, command)
        
    def update_catalog(self, key, new_status):
        did = DEVICE_ID_MAPPING.get(key)
        if not did: return

        if self.device_status_cache.get(key) == new_status:
            return # Status unchanged, no update needed

        self.device_status_cache[key] = new_status
        payload = {
            "deviceID": did,
            "deviceLocation": {"houseID": str(key[0]), "floorID": str(key[1]), "unitID": str(key[2])},
            "deviceStatus": new_status, "lastUpdate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            requests.put(f"{self.catalogAddress}/devices", json=payload)
        except Exception as e:
            print(f"[ERROR] Failed to update catalog: {e}")