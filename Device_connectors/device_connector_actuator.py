# changelog:
# - 2025-07-17: Added robust error handling for JSON parsing in notify and PUT methods.
# - 2025-07-17: Improved error messages for REST API.
# - 2025-07-17: Standardized on string comparison for IDs.

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
        self.clientID = f"{baseClientID}_{DCID}_DCA"
        self.devices = self.DCConfiguration.get("devicesList", [])

        try:
            self.houseID, self.floorID, self.unitID = DCID.split("-")
        except ValueError as e:
            print(f"Error parsing DCID '{DCID}'. Expected format 'houseID-floorID-unitID'. Error: {e}")
            return

        try:
            broker, port = self.get_broker()
        except (TypeError, ValueError, requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"Failed to get the broker's information. Possibly server is down. Error: {e}")
            return

        self.client = MyMQTT(self.clientID, broker, port, self)
        self.client.start()
        print(f"MQTT client '{self.clientID}' started.")

        self.topic = f"ThiefDetector/commands/{self.houseID}/{self.floorID}/{self.unitID}/#"
        self.client.mySubscribe(self.topic)
        print(f"Subscribed to topic: {self.topic}")

    @cherrypy.tools.json_out()
    def GET(self, *uri, **params):
        if len(uri) != 0:
            if uri[0] == "devices":
                return self.devices
            else:
                cherrypy.response.status = 404
                return {"error": "Invalid endpoint. Use '/devices' to see the devices list."}
        cherrypy.response.status = 404
        return {"error": "Use '/devices' to see the devices list."}

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self, *uri, **params):
        if len(uri) == 0 or uri[0] != "device_status":
            cherrypy.response.status = 400
            return {"error": "Invalid request. Use PUT on /device_status to update device status."}
        
        # --- CHANGE: Added robust error handling for the PUT request body ---
        try:
            body = cherrypy.request.json
            deviceID = body.get("deviceID")
            newStatus = body.get("status")

            if deviceID is None or newStatus is None:
                cherrypy.response.status = 400
                return {"error": "Missing 'deviceID' or 'status' in request body."}

            for device in self.devices:
                if str(device["deviceID"]) == str(deviceID):
                    print(f"Device {deviceID} -> {newStatus}")
                    device["deviceStatus"] = newStatus
                    device["lastUpdate"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    return {"message": f"Device {deviceID} updated to {newStatus}"}

            cherrypy.response.status = 404
            return {"error": f"Device with ID '{deviceID}' not found."}

        except Exception as e:
            cherrypy.response.status = 500
            return {"error": f"An internal server error occurred: {str(e)}"}


    def notify(self, topic, payload):
        # --- CHANGE: Added robust error handling for the MQTT payload ---
        try:
            # The payload from MyMQTT is already a dict, no need for json.loads
            msg = payload 
            event = msg.get("e", [{}])[0]
            deviceStatusValue = event.get("v")

            if deviceStatusValue is None:
                print(f"[WARN] MQTT message on topic '{topic}' is missing a value ('v').")
                return

            deviceName = topic.split("/")[-1]

            device_found = False
            for device in self.devices:
                if device["deviceName"].lower() == deviceName.lower():
                    print(f"Updating '{deviceName}' status to '{deviceStatusValue}' via MQTT")
                    device["deviceStatus"] = deviceStatusValue
                    device["lastUpdate"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    device_found = True
                    # No need to break; update all matching devices if there are duplicates
            
            if not device_found:
                print(f"[WARN] No device named '{deviceName}' found for this connector.")

        except (IndexError, KeyError) as e:
            print(f"Failed to parse MQTT message payload on topic '{topic}'. Invalid format: {e}")
        except Exception as e:
            print(f"An unexpected error occurred in notify(): {e}")

    def stop(self):
        """Stops the MQTT client."""
        if hasattr(self, 'client'):
            self.client.stop()
            print(f"MQTT client '{self.clientID}' stopped.")

    def get_broker(self):
        req_b = requests.get(self.catalog_url + "broker")
        req_b.raise_for_status()
        broker_json = req_b.json()
        broker, port = broker_json["IP"], int(broker_json["port"])
        print("Broker info received.")
        return broker, port

    def registerer(self):
        """Registers each device from self.devices with the catalog."""
        for device in self.devices:
            device["lastUpdate"] = time.strftime("%Y-%m-%d %H:%M:%S")
            try:
                # Use PUT for an "upsert" operation (update or create)
                # This is simpler than POST-then-PUT
                response = requests.put(self.catalog_url + "devices", json=device)
                response.raise_for_status()
                print(f"Device '{device['deviceName']}' registered/updated successfully.")
            except requests.exceptions.RequestException as e:
                print(f"Error registering device '{device['deviceName']}': {e}")