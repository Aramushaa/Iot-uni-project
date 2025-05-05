import requests
import sched
import time
import json
import math
import copy
from control_unit import Controler  

class CU_instancer():
    def __init__(self, catalogAddress):
        self.catalogAddress = catalogAddress
        self.availableUnitsList = []
        self.PERIODIC_UPDATE_INTERVAL = 60  # seconds
        self.NUM_UNITS_PER_CONTROLLER = 5   # number of units each controller manages

        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler.enter(0, 1, self.periodic_unit_list_update, ())
        self.scheduler.run(blocking=False)

        # Immediately load unit list from catalog before creating controllers
        self.update_unit_list()  # Make sure self.availableUnitsList is filled
        self.controller_creator()
        self.scheduler.enter(0, 2, self.subscribe_to_all, ())
        self.scheduler.run()

    def wrapped_notify(self, name, controller):
        original_notify = controller.notify

        def new_notify(topic, payload):
            original_notify(topic, payload)

        return new_notify

    def subscribe_to_all(self):
        self.check_units_and_controllers()
        temp_units_list = copy.deepcopy(self.availableUnitsList)

        for i in range(self.num_controllers):
            units_slice = temp_units_list[:self.NUM_UNITS_PER_CONTROLLER]
            controller_name = f"controller_{i}"
            self.controllers[controller_name].subscribe_to_topics(units_slice)
            print(f"[SUBSCRIBE] {controller_name} subscribed to: {units_slice}")
            temp_units_list = temp_units_list[self.NUM_UNITS_PER_CONTROLLER:]

        self.scheduler.enter(self.PERIODIC_UPDATE_INTERVAL, 2, self.subscribe_to_all, ())

    def check_units_and_controllers(self):
        required_controllers = math.ceil(len(self.availableUnitsList) / self.NUM_UNITS_PER_CONTROLLER)
        existing_count = len(self.controllers)
        num_new_needed = required_controllers - existing_count

        if num_new_needed > 0:
            print(f"[INFO] Adding {num_new_needed} new controller(s)...")
            for _ in range(num_new_needed):
                new_name = f"controller_{len(self.controllers)}"
                controller = Controler(self.catalogAddress)
                controller.client.notifier = controller
                controller.notify = self.wrapped_notify(new_name, controller)
                self.controllers[new_name] = controller
                print(f"[CREATE] {new_name} created")

    def controller_creator(self):
        self.num_controllers = math.ceil(len(self.availableUnitsList) / self.NUM_UNITS_PER_CONTROLLER)
        self.controllers = {}

        for i in range(self.num_controllers):
            controller_name = f"controller_{i}"
            controller = Controler(self.catalogAddress)
            controller.client.notifier = controller  # ✅ FIX HERE
            controller.notify = self.wrapped_notify(controller_name, controller)
            self.controllers[controller_name] = controller
            print(f"[INIT] {controller_name} initialized and notify hooked")

    def update_unit_list(self):
        self.availableUnitsList = []
        for house in self.houses:
            for floor in house["floors"]:
                for unit in floor["units"]:
                    if 'devicesList' in unit and len(unit['devicesList']) > 0:
                        unitID = f"{house['houseID']}-{floor['floorID']}-{unit['unitID']}"
                        if unitID not in self.availableUnitsList:
                            self.availableUnitsList.append(unitID)
                            print(f"[UNIT] Added {unitID}")
        self.availableUnitsList.sort()

    def periodic_unit_list_update(self):
        try:
            response = requests.get(f"{self.catalogAddress}houses")
            self.houses = response.json()
            self.update_unit_list()
            print(f"[UPDATE] Unit list refreshed. Total: {len(self.availableUnitsList)}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to update unit list: {e}")

        self.scheduler.enter(self.PERIODIC_UPDATE_INTERVAL, 1, self.periodic_unit_list_update, ())


if __name__ == "__main__":
    catalogAddress = "http://127.0.0.1:8080/"
    cu_instancer = CU_instancer(catalogAddress)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[EXIT] Keyboard interrupt detected. Shutting down...")