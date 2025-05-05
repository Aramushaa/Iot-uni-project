from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)

class UserAwareness:
    def __init__(self, operator_control_url, adaptor_url=None):
        self.operator_control_url = operator_control_url
        self.adaptor_url = adaptor_url
        self.houses = []

    def update_house_list(self):
        try:
            response = requests.get("http://127.0.0.1:8095/houses")
            print("House list updated (interface)")
            raw = response.json()

            # Accept either dict or list
            if isinstance(raw, dict):
                candidates = raw.values()
            elif isinstance(raw, list):
                candidates = raw
            else:
                candidates = []

            # ✅ Check devices nested inside units → floors → house
            self.houses = [
                h for h in candidates
                if any(
                    device
                    for floor in h.get("floors", [])
                    for unit in floor.get("units", [])
                    for device in unit.get("devicesList", [])
                )
            ]
        except requests.exceptions.RequestException as e:
            print(f"Error during GET request to fetch houses: {e}")
            self.houses = []

    def get_channel_detail(self, channel_name):
        try:
            response = requests.get(f"{self.operator_control_url}/channels_detail/{channel_name}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error during GET request for Thingspeak channel details: {e}")
            return None

    def post_device_status(self, device_detail):
        try:
            response = requests.post(self.operator_control_url + "device_status", json=device_detail)
            print(f"Response from operator control on device status update: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error posting device status: {e}")

    def get_houses(self):
        return self.houses

def get_button_class(status):
    return {
        "ON": "green",
        "OFF": "blue",
        "DISABLE": "red",
    }.get(status, "orange")

@app.route('/send_status_message', methods=['POST'])
def send_status_message():
    device_info = request.json
    status = device_info["status"]

    try:
        operator_control_url = "http://127.0.0.1:8095/"
        user_awareness = UserAwareness(operator_control_url)
        user_awareness.post_device_status(device_info)
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)})

    if status == "DISABLE":
        return jsonify({'message': f'{status} status is not available at the moment.'})
    return jsonify({'message': 'Device status updated successfully.'})

@app.route('/')
def index():
    operator_control_url = "http://127.0.0.1:8095/"
    user_awareness = UserAwareness(operator_control_url)
    user_awareness.update_house_list()
    houses = user_awareness.get_houses()

    # Fix for: devices missing houseID, floorID, unitID
    devices = []
    for h in houses:
        for floor in h.get("floors", []):
            for unit in floor.get("units", []):
                for d in unit.get("devicesList", []):
                    d["houseID"] = h.get("houseID")  # ← this was missing
                    d["floorID"] = floor.get("floorID")
                    d["unitID"] = unit.get("unitID")
                    devices.append(d)

    motion_alerts = []
    try:
        r = requests.get(operator_control_url + "motion_alerts")
        motion_alerts = r.json().get("activeAlerts", [])
    except:
        print("Motion alerts fetch failed.")

    return render_template(
        'index.html',
        houses=houses,
        devices=devices,
        motion_alerts=motion_alerts
    )

@app.route('/house/<houseID>')
def house_detail(houseID):
    res = requests.get(f"http://127.0.0.1:8080/house/{houseID}")
    house = res.json()
    if house:
        return render_template('house_detail.html', house=house, get_button_class=get_button_class)
    else:
        return "House not found."

if __name__ == '__main__':
    app.run(debug=True)
