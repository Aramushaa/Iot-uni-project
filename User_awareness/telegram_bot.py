import requests
import sched
import time
import json
from datetime import datetime
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton


class TeleBotDataManager:
    def __init__(self, operator_control_url):
        self.operator_control_url = operator_control_url
        self.devicesDict = {}
        self.PERIODIC_UPDATE_INTERVAL = 600

        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler.enter(0, 1, self.periodic_deviceDict_update, ())
        self.scheduler.run(blocking=False)

    def get_available_devices(self):
        if isinstance(self.devicesDict, dict):
            return list(self.devicesDict.keys())
        else:
            return []

    def get_device_data(self, deviceID):
        try:
            response = requests.get(f"{self.operator_control_url}sensing_data/{deviceID}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to get device data. Error: {e}")
            return {}

    def get_actuator_status(self, deviceID):
        try:
            device = self.devicesDict.get(deviceID)
            return {dev["deviceName"]: dev["deviceStatus"] for dev in device["devicesList"]}
        except (KeyError, TypeError):
            return {}

    def periodic_deviceDict_update(self):
        try:
            response = requests.get(f"{self.operator_control_url}houses")
            data = response.json()
            if isinstance(data, dict):
                self.devicesDict = data
                print("Devices dictionary updated (dict).")
            else:
                print(f"Expected a JSON object (dict), got {type(data)} => {data}")
                self.devicesDict = {}
        except requests.exceptions.RequestException as e:
            print(f"Failed to update devices dictionary. Error: {e}")
            self.devicesDict = {}
        self.scheduler.enter(self.PERIODIC_UPDATE_INTERVAL, 1, self.periodic_deviceDict_update, ())


class TeleBot:
    def __init__(self, token, operator_control_url, ownership_file):
        self.token = token
        self.operator_control_url = operator_control_url
        self.ownership_file = ownership_file
        self.botManager = TeleBotDataManager(operator_control_url)
        self.bot = telepot.Bot(self.token)
        MessageLoop(self.bot, {'chat': self.on_chat_message, 'callback_query': self.on_callback_query}).run_as_thread()

        with open(self.ownership_file, 'r') as fp:
            self.ownership_dict = json.load(fp)

        self.available_devices = []
        self.update_available_devices()

    def update_available_devices(self):
        deviceIDs = self.botManager.get_available_devices()
        self.available_devices = [
            dev for dev in deviceIDs
            if dev not in self.ownership_dict.values()
        ]

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        command = msg['text']

        if command == "/start":
            self.bot.sendMessage(chat_id, "Welcome to ThiefDetector Bot!")
        elif command == "/menu":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Track a device', callback_data='track_device')],
                [InlineKeyboardButton(text='Claim a device', callback_data='claim_device')]
            ])
            self.bot.sendMessage(chat_id, "What would you like to do?", reply_markup=keyboard)
        else:
            self.bot.sendMessage(chat_id, "Sorry, I couldn't understand that command.")

    def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')

        if query_data == "claim_device":
            if not self.available_devices:
                self.bot.sendMessage(from_id, "No devices are currently available.")
                return
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=device, callback_data=f"claim_{device}")]
                for device in self.available_devices
            ])
            self.bot.sendMessage(from_id, "Available devices:", reply_markup=keyboard)
        elif query_data.startswith("claim_"):
            deviceID = query_data.split("_", 1)[1]
            if str(from_id) in self.ownership_dict:
                self.bot.sendMessage(from_id, "You already own a device.")
            else:
                self.ownership_dict[str(from_id)] = deviceID
                self.update_available_devices()
                self.bot.sendMessage(from_id, f"You've successfully claimed device {deviceID}!")
        elif query_data == "track_device":
            if str(from_id) not in self.ownership_dict:
                self.bot.sendMessage(from_id, "You don't own a device yet.")
                return
            deviceID = self.ownership_dict[str(from_id)]
            self.bot.sendMessage(from_id, f"Fetching data for your device {deviceID}...")
            sensing_data = self.botManager.get_device_data(deviceID)
            actuator_status = self.botManager.get_actuator_status(deviceID)
            sensing_str = "\n".join([f"{sensor}: {value}" for sensor, value in sensing_data.items()])
            self.bot.sendMessage(from_id, f"Sensing Data:\n{sensing_str}")
            if isinstance(actuator_status, dict):
                actuator_str = "\n".join([f"{actuator}: {status}" for actuator, status in actuator_status.items()])
            else:
                actuator_str = "No actuators found."
            self.bot.sendMessage(from_id, f"Actuator Status:\n{actuator_str}")

    def save_ownership_data(self):
        with open(self.ownership_file, 'w') as fp:
            json.dump(self.ownership_dict, fp, indent=4)


if __name__ == "__main__":
    # In Docker, the operator-control service is available at this address
    operator_control_url = "http://operator-control:8095/" 
    # FIX: The path is relative to the working directory /app/User_awareness
    ownership_file = "device_ownership.json" 
    token = "7841720164:AAG8L5p4OI7-OKyg1kASAmwO1MVijHEU5XA" 

    bot = TeleBot(token, operator_control_url, ownership_file)

    try:
        while True:
            time.sleep(10)
            bot.save_ownership_data()
    except KeyboardInterrupt:
        print("Shutting down bot...")
        bot.save_ownership_data()