Thief Detector IoT System
A comprehensive, microservice-based IoT system for home security monitoring. This project simulates a network of sensors and actuators to detect and respond to potential intrusions, providing real-time updates through a web interface, a ThingSpeak dashboard, and a Telegram bot.

🌟 Features
Microservice Architecture: The system is broken down into independent services for scalability and maintainability.

Real-time Monitoring: A web interface provides a live overview of all connected devices and their statuses.

Intelligent Automation: The system automatically turns lights on when motion is detected and off when the area is clear and well-lit.

Cloud Integration: Sensor data is pushed to ThingSpeak for historical analysis and visualization.

Remote Control: A Telegram bot allows users to claim and monitor devices from anywhere.

Dynamic Service Discovery: A central catalog service allows components to discover each other dynamically.

Simulated Devices: Includes simulated light and motion sensors for easy testing and development without physical hardware.

🏛️ Architecture Overview
The Thief Detector system follows a microservice architecture. Each component is a standalone service that communicates with others through REST APIs and an MQTT message broker. This decoupled design makes the system robust, scalable, and easy to modify.

Here’s a high-level overview of the data flow:

Device Connectors (Sensors) (device_connector.py) simulate sensor readings (light, motion) and publish them to an MQTT broker.

The Control Unit (control_unit.py) subscribes to sensor topics on the MQTT broker. Based on the incoming data, it implements the core security logic.

When a response is needed, the Control Unit publishes a command to a different MQTT topic.

Device Connectors (Actuators) (device_connector_actuator.py) subscribe to command topics and simulate an actuator's response (e.g., turning on a light switch).

The ThingSpeak Adaptor (adaptor.py) also subscribes to sensor topics and periodically pushes the data to the ThingSpeak cloud platform.

All services register with and query the Catalog Registry (catalog_registry.py) to get configuration details like broker IP, device lists, and API endpoints.

The Operator Control service (operator_control.py) acts as a gateway, aggregating data from the catalog and device connectors to provide a unified API for front-end clients.

The Web Interface (interface.py & *.html) and Telegram Bot (telegram_bot.py) are the user-facing clients that communicate with the Operator Control service to display data and send commands.

🧩 Components

1. Catalog Registry (catalog_registry.py)
Purpose: The single source of truth for the entire system. It's a RESTful service that manages a catalog.json file containing information about all houses, devices, and service endpoints.

Functionality:

Provides broker connection details to all MQTT clients.

Allows services to register new devices and update their status.

Implements schema validation to ensure data integrity.

Periodically cleans up inactive devices from the registry.

2. Device Connectors (device_connector.py & device_connector_actuator.py)
Purpose: These services simulate the behavior of physical IoT devices.

Functionality:

Sensor Connector (device_connector.py): Generates simulated light and motion data and publishes it to MQTT topics.

Actuator Connector (device_connector_actuator.py): Subscribes to MQTT command topics and updates the state of simulated actuators (e.g., light switches).

Both connectors are instantiated by their respective "instancer" scripts (DC_instancer.py and DC_instancer_actuator.py) based on configuration files.

3. Control Unit (control_unit.py)
Purpose: This is the brain of the system. It contains the core automation logic.

Functionality:

Subscribes to all sensor data topics via MQTT.

Implements the main security logic: turns lights on when motion is detected and turns them off after a period of inactivity if the ambient light is high.

Publishes commands to actuators via MQTT.

Instantiated and managed by CU_instancer.py for scalability.

4. ThingSpeak Adaptor (adaptor.py)
Purpose: Acts as a bridge between the local MQTT broker and the ThingSpeak cloud platform.

Functionality:

Subscribes to sensor topics on the MQTT broker.

Buffers data and periodically sends it to specific ThingSpeak channels using the ThingSpeak REST API.

5. Operator Control (operator_control.py)
Purpose: An API gateway that simplifies interactions for front-end clients.

Functionality:

Aggregates data from the Catalog and various Device Connectors.

Provides a clean, unified REST API for clients to get real-time information about all houses and devices.

Tracks and reports active motion alerts.

6. Web Interface (interface.py, index.html, house_detail.html)
Purpose: Provides a user-friendly web dashboard for monitoring the system.

Functionality:

A Flask-based web server that renders HTML templates.

Communicates with the Operator Control service to get the latest device data.

Displays all houses, devices, and their statuses in real-time, with an auto-refresh feature.

7. Telegram Bot (telegram_bot.py)
Purpose: Allows users to interact with the system via the Telegram messaging app.

Functionality:

Provides an interface for users to claim ownership of a device.

Allows users to request the current status of their claimed device.

Communicates with the Operator Control service to fetch data.

🚀 Getting Started
To run the Thief Detector system, you'll need to start each microservice. It's recommended to run each command in a separate terminal.

Prerequisites
Python 3.8+

The following Python libraries: requests, paho-mqtt, cherrypy, flask, telepot

You can install all dependencies with pip:

Bash

pip install requests paho-mqtt cherrypy flask telepot
Running the Services
Start the services in the following order:

Catalog Registry:

Bash

python catalog_registry.py
Device Connectors (Sensors):

Bash

python DC_instancer.py
Device Connectors (Actuators):

Bash

python DC_instancer_actuator.py
Control Unit:

Bash

python CU_instancer.py
ThingSpeak Adaptor:

Bash

python adaptor.py
Operator Control:

Bash

python operator_control.py
Web Interface:

Bash

python interface.py
Telegram Bot: (Make sure to add your bot token)

Bash

python telegram_bot.py
Once all services are running, you can access the web interface at http://127.0.0.1:5000/.