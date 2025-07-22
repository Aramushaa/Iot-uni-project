# changelog:
# - 2025-07-21: Converted from a polling to an event-driven model by adding an MQTT client.
# - 2025-07-21: Motion alerts are now received instantly and reliably.

import requests
import cherrypy
import time
import datetime
import json
import threading
from MyMQTT2 import MyMQTT # Import the MQTT client

class OperatorControl:
    exposed = True

    def __init__(self, catalog_address):
        self.catalog_address = catalog_address.rstrip('/')
        self.houses = {}
        self.motion_alerts = {}  # unit_key -> timestamp

        # --- NEW: MQTT Client for Real-Time Alerts ---
        self.mqtt_client = None
        try:
            broker, port, main_topic = self.get_mqtt_config()
            client_id = f"OperatorControl_{int(time.time())}"
            self.mqtt_client = MyMQTT(client_id, broker, port, self)
            self.mqtt_client.start()
            self.mqtt_client.mySubscribe(f"{main_topic}/sensors/#")
            print(f"[MQTT] Operator Control subscribed to {main_topic}/sensors/#")
        except Exception as e:
            print(f"[FATAL ERROR] Could not start MQTT client for Operator Control: {e}")

        # Start a background thread to periodically update the house list
        self.update_house_list()

    def notify(self, topic, payload):
        """This method is called by MyMQTT when a message is received."""
        try:
            print(f"[MQTT NOTIFY] Received message on topic: {topic}")
            parts = topic.split("/")
            if len(parts) < 6 or parts[5] != "motion_sensor":
                return # We only care about motion sensor messages here

            value = payload.get("e", [{}])[0].get("v")
            if value == "Detected":
                unit_key = f"{parts[2]}-{parts[3]}-{parts[4]}"
                self.motion_alerts[unit_key] = time.time()
                print(f"[ALERT] Real-time motion alert received for unit: {unit_key}")
        except Exception as e:
            print(f"[ERROR] Could not process MQTT message in Operator Control: {e}")

    def get_mqtt_config(self):
        """Fetches broker details and the main topic from the catalog."""
        print("[INFO] Fetching MQTT configuration from catalog...")
        r_broker = requests.get(f"{self.catalog_address}/broker", timeout=5)
        r_broker.raise_for_status()
        broker_info = r_broker.json()

        r_topic = requests.get(f"{self.catalog_address}/topic", timeout=5)
        r_topic.raise_for_status()
        # Assuming the topic endpoint returns a simple string
        main_topic = r_topic.text.strip('"')

        return broker_info["IP"], int(broker_info["port"]), main_topic

    @cherrypy.tools.json_out()
    def GET(self, *uri, **params):
        if not uri:
            cherrypy.response.status = 404
            return {"error": "Invalid endpoint."}

        path = uri[0].lower()
        if path == "houses":
            real_time_data = self.get_realtime_data()
            return real_time_data

        elif path == "motion_alerts":
            active_alerts = [
                key for key, ts in self.motion_alerts.items() 
                if time.time() - ts < 300 # 5 minutes
            ]
            return {"activeAlerts": active_alerts}

        cherrypy.response.status = 404
        return {"error": f"Endpoint '/{path}' not found."}

    def update_house_list(self):
        """Periodically fetches the master list of houses from the catalog."""
        try:
            response = requests.get(f"{self.catalog_address}/houses", timeout=5)
            response.raise_for_status()
            houses_list = response.json()
            self.houses = {str(h.get("houseID")): h for h in houses_list if h.get("houseID")}
            print(f"[INFO] House list updated. Found {len(self.houses)} houses.")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Could not update house list from catalog: {e}")
        finally:
            # Reschedule the next update
            threading.Timer(60, self.update_house_list).daemon = True
            threading.Timer(60, self.update_house_list).start()


    def get_realtime_data(self):
        """Fetches data from all connectors and merges it into a complete view."""
        if not self.houses:
            return {}
        real_time_houses = json.loads(json.dumps(self.houses))
        
        for house_id, house in real_time_houses.items():
            for floor in house.get("floors", []):
                for unit in floor.get("units", []):
                    unit["devicesList"] = self.fetch_unit_devices(unit)
        return real_time_houses

    def fetch_unit_devices(self, unit):
        """Fetches sensor and actuator data for a single unit and merges them."""
        devices = []
        urls_to_fetch = [unit.get("urlSensors"), unit.get("urlActuators")]
        
        for url in urls_to_fetch:
            if not url: continue
            try:
                response = requests.get(url, timeout=3)
                response.raise_for_status()
                data = response.json()
                device_list = data if isinstance(data, list) else data.get("devicesList", [])
                devices.extend(device_list)
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Failed to fetch from {url}: {e}")
        return devices

def cors():
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
    cherrypy.response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    cherrypy.response.headers["Access-Control-Allow-Headers"] = "Content-Type"

def OPTIONS(*args, **kwargs):
    return ""

if __name__ == "__main__":
    cherrypy.tools.cors = cherrypy.Tool('before_handler', cors)
    conf = {
        "/": { "request.dispatch": cherrypy.dispatch.MethodDispatcher(), "tools.cors.on": True }
    }
    catalog_address = "http://127.0.0.1:8080/"
    operator_control = OperatorControl(catalog_address)
    operator_control.OPTIONS = OPTIONS 
    
    cherrypy.config.update({"server.socket_port": 8095})
    cherrypy.tree.mount(operator_control, "/", conf)
    cherrypy.engine.start()

    try:
        print("Operator Control server started on port 8095.")
        cherrypy.engine.block()
    except KeyboardInterrupt:
        print("\nShutting down Operator Control server...")
        if operator_control.mqtt_client:
            operator_control.mqtt_client.stop()
    finally:
        cherrypy.engine.stop()
        print("Server shut down.")