import requests
import cherrypy
import sched
import time

class OperatorControl:
    exposed = True

    def __init__(self, catalogAddress, adaptor_url, thingspeak_channels_url="https://api.thingspeak.com/channels/"):
        self.catalogAddress = catalogAddress
        self.adaptor_url = adaptor_url
        self.thingspeak_channels_url = thingspeak_channels_url
        self.PERIODIC_UPDATE_INTERVAL = 600
        self.houses = None
        self.real_time_houses = {}
        self.base_url_actuators = None
        self.channels_detail = None
        self.motion_alerts = {}  # store unitID → timestamp



        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler.enter(0, 1, self.periodic_house_list_update, ())
        self.scheduler.run(blocking=False)

    @cherrypy.tools.json_out()
    def GET(self, *uri, **params):
        if len(uri) != 0:
            if uri[0] == "houses":
                self.get_realtime_house()
                if len(uri) > 1:
                    return self.real_time_houses.get(uri[1])
                return self.real_time_houses

            elif uri[0] == "channels_detail":
                if len(uri) > 1:
                    return self.get_channel_detail(uri[1])
                return "Enter the name of the Thingspeak channel."

            elif uri[0] == "sensing_data":
                if len(uri) > 1:
                    return self.get_latest_sensing_data(uri[1])
                return "Enter the name of the Thingspeak channel."

            elif uri[0] == "health":
                return {"status": "Operator Control is running."}
            
            elif uri[0] == "motion_alerts":
                alerts = []
                now = time.time()
                for unit_key, ts in self.motion_alerts.items():
                    if now - ts < 60:  # 🕐 alert valid for 60 seconds
                        alerts.append(unit_key)
                return {"activeAlerts": alerts}

            return "Invalid URL. Visit '/houses' or '/channels_detail' for information."
        return "Visit '/houses' or '/channels_detail' or /motion_alerts for information."

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *uri, **params):
        if len(uri) != 0 and uri[0] == "device_status":
            body = cherrypy.request.json
            device_id = body["deviceID"]
            houseID = body["houseID"]
            floorID = body["floorID"]
            status = body["status"]
            device_message = {"deviceID": device_id, "status": status}

            try:
                response = requests.put(
                    f"{self.base_url_actuators}/actuator_{houseID}_{floorID}/device_status", json=device_message
                )
                print(f"Response from actuator connector: {response.text}")
                return {"success": [device_id, houseID, floorID, status]}
            except requests.exceptions.RequestException as e:
                print(f"Error updating device status: {e}")
                return {"error": str(e)}

        return {"error": "Invalid POST request"}

    def get_channel_detail(self, channel_name):
        try:
            response = requests.get(f"{self.adaptor_url}/channels_detail")
            channels = response.json()
            return channels.get(channel_name)
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving Thingspeak channel details: {e}")
            return None

    def get_latest_sensing_data(self, channel_name):
        channel_detail = self.get_channel_detail(channel_name)
        if channel_detail:
            try:
                fields = channel_detail["fields"]
                channel_id = channel_detail["channelId"]
                response = requests.get(f"{self.thingspeak_channels_url}{channel_id}/feeds.json?results=5")
                data_list = response.json()["feeds"]

                current_data = {}
                for record in data_list:
                    for field, value in record.items():
                        if field.startswith("field") and value:
                            current_data[fields[field]] = value
                return current_data
            except requests.exceptions.RequestException as e:
                print(f"Error retrieving Thingspeak data: {e}")
                return {"error": str(e)}
        return {"error": "Channel not found"}

    def get_realtime_house(self):
        if not self.houses:
            try:
                self.houses = requests.get(f"{self.catalogAddress}/houses").json()
            except:
                self.houses = []

        self.real_time_houses = {}
        for house in self.houses:
            houseID = house["houseID"]
            self.real_time_houses[houseID] = {
                "houseID": houseID,
                "houseName": house.get("houseName", f"House {houseID}"),
                "floors": []
            }

            for floor in house.get("floors", []):
                floor_data = {"floorID": floor["floorID"], "units": []}
                for unit in floor.get("units", []):
                    unitID = unit["unitID"]
                    url_sensors = unit.get("urlSensors")
                    url_actuators = unit.get("urlActuators")
                    if not url_sensors or not url_actuators:
                        continue
                    device_list = self.fetch_device_data(url_sensors, url_actuators)
                    # ✅ Detect motion and update alert timestamp
                    for dev in device_list.get("devicesList", []):
                        if dev.get("deviceName") == "motion_sensor" and dev.get("deviceStatus") == "Detected":
                            unit_key = f"{houseID}-{floor['floorID']}-{unitID}"
                            self.motion_alerts[unit_key] = time.time()
                    unit_data = {
                        "unitID": unitID,
                        "devicesList": device_list.get("devicesList", [])
                    }
                    floor_data["units"].append(unit_data)
                self.real_time_houses[houseID]["floors"].append(floor_data)

    def fetch_device_data(self, url_sensors, url_actuators):
        devices = []
        try:
            sensors_response = requests.get(url_sensors)
            actuators_response = requests.get(url_actuators)

            if sensors_response.status_code == 200:
                sensors_data = sensors_response.json()
                print(f"[SENSORS] {url_sensors} -> {sensors_data}")  # 👈
                devices.extend(sensors_data.get("devicesList", sensors_data))

            if actuators_response.status_code == 200:
                actuators_data = actuators_response.json()
                print(f"[ACTUATORS] {url_actuators} -> {actuators_data}")  # 👈
                devices.extend(actuators_data if isinstance(actuators_data, list) else actuators_data.get("devicesList", []))

        except requests.exceptions.RequestException as e:
            print(f"Error fetching device data: {e}")
        return {"devicesList": devices}


    def periodic_house_list_update(self):
        try:
            response = requests.get(f"{self.catalogAddress}/houses")
            self.houses = []
            for house in response.json():
                has_devices = False
                for floor in house.get("floors", []):
                    for unit in floor.get("units", []):
                        if unit.get("devicesList"):
                            has_devices = True
                            break
                    if has_devices:
                        break
                if has_devices:
                    house["urlSensors"] = floor["units"][0]["urlSensors"]
                    house["urlActuators"] = floor["units"][0]["urlActuators"]
                    self.houses.append(house)

            self.update_base_actuator_url()
        except requests.exceptions.RequestException as e:
            print(f"Error updating house list: {e}")

        self.scheduler.enter(self.PERIODIC_UPDATE_INTERVAL, 1, self.periodic_house_list_update, ())

    def update_base_actuator_url(self):
        if self.houses:
            self.base_url_actuators = "/".join(self.houses[0]["urlActuators"].strip().split("/")[:3])


if __name__ == "__main__":
    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.sessions.on": True,
        }
    }
    catalogAddress = "http://127.0.0.1:8080/"
    adaptor_url = "http://127.0.0.1:8099/"
    operator_control = OperatorControl(catalogAddress, adaptor_url)

    cherrypy.config.update({"server.socket_port": 8095})
    cherrypy.tree.mount(operator_control, "/", conf)
    cherrypy.engine.start()

    try:
        for _ in range(600):
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Shutting down...")
        cherrypy.engine.stop()
    finally:
        cherrypy.engine.block()
