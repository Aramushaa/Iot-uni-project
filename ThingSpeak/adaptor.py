# changelog:
# - 2025-07-21: Made Client ID unique to prevent MQTT connection issues.
# - 2025-07-21: Refactored to listen to command topics, making the Control Unit the single source of truth.

import requests
import time
import threading
from flask import Flask
from MyMQTT2 import MyMQTT

class Adaptor:
    def __init__(self):
        # Make the Client ID unique on each run to prevent collisions
        self.clientID = f"ThingSpeak_Adaptor_V2_{int(time.time())}"
        self.broker = "test.mosquitto.org"
        self.port = 1883
        self.channel_API = "https://api.thingspeak.com/update"

        # Map unit IDs to ThingSpeak channel fields
        self.unit_to_field_map = {
            "1-1-1": {"channel": "house1", "field": "field1"},
            "1-1-2": {"channel": "house1", "field": "field2"},
            "1-2-1": {"channel": "house1", "field": "field3"},
            "2-1-1": {"channel": "house2", "field": "field1"},
            "2-1-2": {"channel": "house2", "field": "field2"},
            "2-2-1": {"channel": "house2", "field": "field3"},
        }
        
        # ThingSpeak API Write Keys per channel
        self.api_keys = {"house1": "TYJBKZK6C3VMU6X0", "house2": "639Q1WGL7VNX405K"}

        # Buffers to hold the latest value (0 for OFF, 1 for ON) for each field
        self.buffers = {
            "house1": {"field1": 0, "field2": 0, "field3": 0},
            "house2": {"field1": 0, "field2": 0, "field3": 0}
        }
        self.lock = threading.Lock()

        # Start the MQTT client
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)
        self.client.start()

        # Subscribe to the master command topic, where the Control Unit sends ON/OFF
        # Use the correct case "ThiefDetector" as seen in your logs
        command_topic = "ThiefDetector/commands/#"
        self.client.mySubscribe(command_topic)
        print(f"[SUBSCRIBE] Listening for all commands on: {command_topic}")

        # Start the periodic updates to ThingSpeak
        for channel in self.api_keys.keys():
            self.schedule_update(channel)

    def schedule_update(self, channel):
        threading.Timer(15.0, self.flush_channel, args=[channel]).start()

    def flush_channel(self, channel):
        with self.lock:
            url = f"{self.channel_API}?api_key={self.api_keys[channel]}"
            for field, value in self.buffers[channel].items():
                url += f"&{field}={value}"
            try:
                r = requests.get(url, timeout=5)
                r.raise_for_status()
                print(f"[THING] Sent to {channel}: {self.buffers[channel]} -> Status {r.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Failed to update ThingSpeak for {channel}: {e}")
        self.schedule_update(channel)

    def notify(self, topic, payload):
        """Processes final ON/OFF commands from the Control Unit."""
        print(f"[MQTT] Received command on: {topic}")
        try:
            parts = topic.split("/")
            if len(parts) < 6 or parts[-1] != "light_switch":
                return  # We only care about light switch commands

            unit_key = f"{parts[2]}-{parts[3]}-{parts[4]}"
            command = payload.get("e", [{}])[0].get("v")

            if unit_key in self.unit_to_field_map:
                config = self.unit_to_field_map[unit_key]
                channel = config["channel"]
                field = config["field"]
                
                # Convert "ON"/"OFF" to 1/0 for ThingSpeak
                new_value = 1 if command == "ON" else 0
                
                with self.lock:
                    self.buffers[channel][field] = new_value
                print(f"[ADAPT] Updated {channel}/{field} to {new_value} for unit {unit_key}")

        except Exception as e:
            print(f"[ERROR] Failed to process message on topic '{topic}': {e}")


# --- Flask App ---
app = Flask(__name__)
adaptor = Adaptor()

@app.route("/", methods=["GET"])
def index():
    return "<h1>ThingSpeak Adaptor is Running</h1>"

if __name__ == "__main__":
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8099, debug=False, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Adaptor service started. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[EXIT] Shutting down...")