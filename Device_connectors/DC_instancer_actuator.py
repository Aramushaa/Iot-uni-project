# changelog:
# - 2025-07-17: Implemented a graceful shutdown procedure for CherryPy and MQTT clients.
# - 2025-07-17: Simplified registration loop.

from device_connector_actuator import Device_connector_act
import json
import time
import cherrypy

if __name__ == "__main__":
    settingActFile = "Device_connectors/setting_act.json"

    try:
        with open(settingActFile) as fp:
            settingAct = json.load(fp)
    except FileNotFoundError:
        print(f"Configuration file '{settingActFile}' not found.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in '{settingActFile}': {e}")
        exit(1)

    catalog_url = settingAct.get("catalogURL", "http://127.0.0.1:8080/")
    baseClientID = settingAct["clientID"]
    DCID_act_dict = settingAct["DCID_dict"]

    deviceConnectorsAct = {}
    for DCID, plantConfig in DCID_act_dict.items():
        DC_name = f"arduino_{DCID}"
        connector = Device_connector_act(
            catalog_url,
            plantConfig,
            baseClientID,
            DCID
        )
        deviceConnectorsAct[DC_name] = connector
        cherrypy.tree.mount(connector, f'/{DC_name}', {
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.sessions.on': True
            }
        })
        print(f"Mounted {DC_name} to CherryPy")
    
    # Register all devices once at the start
    print("Registering all actuator devices...")
    for DC in deviceConnectorsAct.values():
        DC.registerer()
        time.sleep(0.1) # small delay

    cherrypy.config.update({'server.socket_port': 8086})
    cherrypy.engine.start()
    
    # --- CHANGE: The main loop is now simpler and more robust ---
    try:
        print("Server started. Press Ctrl+C to shut down.")
        cherrypy.engine.block()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Shutting down...")
    finally:
        # --- CHANGE: Graceful shutdown logic ---
        print("Stopping all actuator MQTT clients...")
        for DC in deviceConnectorsAct.values():
            DC.stop()
        
        print("Stopping CherryPy server...")
        cherrypy.engine.stop()
        print("Server shut down gracefully.")