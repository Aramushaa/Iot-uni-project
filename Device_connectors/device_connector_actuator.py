# changelog:
# - 2025-07-22: Made clientID unique to prevent connection drops by the MQTT broker.
# - 2025-07-22: Added detailed logging to the notify() method to confirm command reception.

from MyMQTT import MyMQTT
import requests
import time
import json
import cherrypy

class Device_connector_act():
    exposed = True

    def __init__(self, catalog_url, DCConfiguration, baseClientID, DCID):
        self.catalog_url = catalog_url
        self.DCConfiguration = DCConfiguration
        # --- FIX: Make the Client ID unique for every instance ---
        self.clientID = f"{baseClientID}_{DCID}_DCA_{int(time.time())}"
        self.devices = self.DCConfiguration.get("devicesList", [])

        try:
            self.houseID, self.floorID, self.unitID = DCID.split("-")
        except ValueError as e:
            print(f"Error parsing DCID '{DCID}'. Expected format 'houseID-floorID-unitID'. Error: {e}")
            return

        try:
            broker, port, main_topic = self.get_mqtt_config(catalog_url)
            self.main_topic = main_topic
        except Exception as e:
            print(f"Failed to get the broker's information for {self.clientID}. Error: {e}")
            return

        self.client = MyMQTT(self.clientID, broker, port, self)
        self.client.start()
        
        self.topic = f"{self.main_topic}/commands/{self.houseID}/{self.floorID}/{self.unitID}/#"
        self.client.mySubscribe(self.topic)
        print(f"[{self.clientID}] Subscribed to topic: {self.topic}")

    def get_mqtt_config(self, catalog_url):
        r_broker = requests.get(f"{catalog_url}/broker", timeout=5)
        r_broker.raise_for_status()
        broker_info = r_broker.json()
        r_topic = requests.get(f"{catalog_url}/topic", timeout=5)
        r_topic.raise_for_status()
        main_topic = r_topic.text.strip('"')
        return broker_info["IP"], int(broker_info["port"]), main_topic

    @cherrypy.tools.json_out()
    def GET(self, *uri, **params):
        if len(uri) != 0 and uri[0] == "devices":
            return self.devices
        cherrypy.response.status = 404
        return {"error": "Invalid endpoint. Use '/devices'."}

    def notify(self, topic, payload):
        # --- FIX: Added detailed logging to see incoming commands ---
        print(f"[{self.clientID} NOTIFY] Command received on topic: {topic}")
        try:
            msg = payload 
            event = msg.get("e", [{}])[0]
            deviceStatusValue = event.get("v")
            deviceName = topic.split("/")[-1]

            for device in self.devices:
                if device["deviceName"].lower() == deviceName.lower():
                    print(f"[{self.clientID}] Updating '{deviceName}' status to '{deviceStatusValue}'")
                    device["deviceStatus"] = deviceStatusValue
                    device["lastUpdate"] = time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"[{self.clientID} ERROR] Failed to process command: {e}")

    def stop(self):
        if hasattr(self, 'client'):
            self.client.stop()
            print(f"MQTT client '{self.clientID}' stopped.")