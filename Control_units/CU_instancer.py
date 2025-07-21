# changelog:
# - 2025-07-21: Refactored to manage a SINGLE MQTT client to prevent client ID collisions.
# - 2025-07-21: The instancer now acts as a dispatcher, forwarding messages to the correct controller.

import requests
import time
import json
import math
import threading
from control_unit import Controler
from MyMQTT2 import MyMQTT # Import MyMQTT here

class CU_instancer():
    def __init__(self, catalogAddress):
        self.catalogAddress = catalogAddress.rstrip('/')
        self.PERIODIC_UPDATE_INTERVAL = 60
        self.NUM_UNITS_PER_CONTROLLER = 5

        self.controllers = {}
        self.unit_assignment = {}
        
        # --- CHANGE: The instancer now owns the single MQTT client ---
        self.main_topic = self.get_main_topic()
        self.clientID = "ThiefDetector_Controller_Instancer" # A unique ID for the instancer
        try:
            broker, port = self.get_broker()
            # The 'notifier' is now the instancer itself
            self.client = MyMQTT(self.clientID, broker, port, self) 
            self.client.start()
            print("[MQTT] Instancer's MQTT client started.")
        except Exception as e:
            print(f"[FATAL] Could not start MQTT client for instancer: {e}")
            return
        
        # Start by updating the unit list and creating controllers
        self.update_and_rebalance_controllers()
        
        # Start a periodic check to rebalance if new units are added
        self.scheduler = threading.Timer(self.PERIODIC_UPDATE_INTERVAL, self.update_and_rebalance_controllers)
        self.scheduler.daemon = True
        self.scheduler.start()

    def get_main_topic(self):
        try:
            r = requests.get(f"{self.catalogAddress}/topic")
            return r.json()
        except: return "ThiefDetector"

    def get_broker(self):
        r = requests.get(f"{self.catalogAddress}/broker")
        b = r.json()
        return b.get("IP"), int(b.get("port"))
        
    def notify(self, topic, payload):
        """This is the single entry point for all MQTT messages."""
        print(f"[DISPATCH] Received on topic: {topic}")
        try:
            parts = topic.split("/")
            if len(parts) < 5: return

            # Find which controller is responsible for this unit
            unit_key_str = f"{parts[2]}-{parts[3]}-{parts[4]}"
            assigned_controller_name = self.unit_assignment.get(unit_key_str)
            
            if assigned_controller_name:
                controller = self.controllers.get(assigned_controller_name)
                if controller:
                    # Forward the message to the correct controller
                    controller.process_message(topic, payload)
                else:
                    print(f"[WARN] No controller instance found for '{assigned_controller_name}'")
            else:
                print(f"[WARN] No controller assigned for unit '{unit_key_str}'")

        except Exception as e:
            print(f"[ERROR] Error in dispatcher notify(): {e}")

    def update_and_rebalance_controllers(self):
        print("[INFO] Checking for unit updates and rebalancing controllers...")
        try:
            resp = requests.get(f"{self.catalogAddress}/houses")
            houses = resp.json()
            
            current_units = set()
            for house in houses:
                for floor in house.get("floors", []):
                    for unit in floor.get("units", []):
                        uid = f"{house['houseID']}-{floor['floorID']}-{unit['unitID']}"
                        current_units.add(uid)

            if set(self.unit_assignment.keys()) == current_units:
                print("[INFO] No change in units. No rebalance needed.")
                return

            print("[INFO] Unit list has changed. Rebalancing controllers.")
            self.availableUnitsList = sorted(list(current_units))

            # Create controllers
            needed_controllers = math.ceil(len(self.availableUnitsList) / self.NUM_UNITS_PER_CONTROLLER)
            for i in range(needed_controllers):
                name = f"controller_{i}"
                if name not in self.controllers:
                    # Pass the shared MQTT client to the controller
                    self.controllers[name] = Controler(self.catalogAddress, self.client, self.main_topic)
                    print(f"[INIT] Created {name}")

            # Assign units to controllers
            self.unit_assignment.clear()
            for idx, unit in enumerate(self.availableUnitsList):
                controller_idx = idx // self.NUM_UNITS_PER_CONTROLLER
                assigned_controller = f"controller_{controller_idx}"
                self.unit_assignment[unit] = assigned_controller
            
            print(f"[REBALANCE] Unit assignment updated: {self.unit_assignment}")
            
            # Subscribe to all sensor topics with the single client
            topic = f"{self.main_topic}/sensors/#"
            self.client.mySubscribe(topic)
            print(f"[SUBSCRIBE] Instancer subscribed to master topic: {topic}")

        except Exception as e:
            print(f"[ERROR] Failed during rebalance: {e}")


if __name__ == "__main__":
    catalogAddress = "http://127.0.0.1:8080/"
    cu_instancer = CU_instancer(catalogAddress)
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n[EXIT] Shutting down...")
        # The MQTT client will stop automatically since it's in a daemon thread.