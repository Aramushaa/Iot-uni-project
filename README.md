# 🛡️ ThiefDetector IoT System

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Broker-brightgreen?style=for-the-badge&logo=mqtt)](https://mqtt.org/)

[cite_start]A comprehensive, microservice-based IoT system for home security monitoring[cite: 1]. [cite_start]This project simulates a network of sensors and actuators to detect and respond to potential intrusions, providing real-time updates through a web dashboard, a ThingSpeak channel, and a Telegram bot[cite: 1].

![Dashboard Screenshot](docs/dashboard.png)

---

## ✅ Features

-   [cite_start]**Microservice Architecture**: Fully containerized with Docker Compose for a single-command setup and maximum scalability[cite: 1].
-   [cite_start]**Real-time Web Dashboard**: A dynamic, single-page application that provides a live overview of all connected devices and their statuses[cite: 1].
-   **Admin Management Panel**: A dedicated web interface to add new houses, floors, units, and devices to the system.
-   [cite_start]**Intelligent Automation**: Automatically turns lights ON for motion detection or low ambient light, and provides on-screen reasons for its actions[cite: 1].
-   [cite_start]**Dynamic Alerts**: Both the global and per-house alerts are time-sensitive and will automatically clear after a period of inactivity[cite: 1].
-   [cite_start]**Cloud Integration**: Pushes sensor and actuator data to ThingSpeak for historical analysis and visualization[cite: 1].
-   [cite_start]**Remote Control & Alerts**: A Telegram bot allows users to claim and monitor devices and receive real-time motion alerts[cite: 1].
-   [cite_start]**Dynamic Service Discovery**: A central Catalog service allows all components to discover each other dynamically within the Docker network[cite: 1].

---

## 🛠️ Technology Stack

-   [cite_start]**Backend**: Python, CherryPy, Flask [cite: 1]
-   [cite_start]**Frontend**: HTML, CSS, JavaScript, Bootstrap 5 [cite: 1]
-   [cite_start]**Messaging**: MQTT (Eclipse Mosquitto Broker) [cite: 1]
-   [cite_start]**Containerization**: Docker & Docker Compose [cite: 1]

---

## 🏛️ Architecture Overview

[cite_start]The system follows a microservice architecture where each component is a standalone Docker container[cite: 1]. [cite_start]Services communicate through REST APIs for configuration and an MQTT message broker for real-time events[cite: 1].

![Architecture Diagram](docs/Thief_Detector_diagram.jpg)

### Microservice Connections

The following table details the communication paths between each service:

| From Service             | To Service                 | Connection Type | Publisher/Provider or Subscriber/Consumer | Purpose                                                                 |
| ------------------------ | -------------------------- | --------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| **Sensors** | **Message Broker** | MQTT            | Publisher                                 | Publishes sensor data (light, motion).                                  |
| **Control Unit** | **Message Broker** | MQTT            | Subscriber & Publisher                    | Subscribes to sensor data, publishes commands.                          |
| **Actuators** | **Message Broker** | MQTT            | Subscriber                                | Subscribes to commands to change its status.                            |
| **ThingSpeak Adaptor** | **Message Broker** | MQTT            | Subscriber                                | Subscribes to sensor data.                                              |
| **Telegram Bot** | **Message Broker** | MQTT            | Subscriber                                | Subscribes to alerts.                                                   |
| **Operator Control** | **Sensors & Actuators**| REST            | Consumer                                  | Gets the current list/status of devices.                                |
| **Operator Control** | **Home Catalog** | REST            | Consumer                                  | Gets the overall structure of houses/units.                             |
| **Web Interface** | **Operator Control** | REST            | Consumer                                  | Gets all data needed for the dashboard.                                 |
| **Telegram Bot** | **Operator Control** | REST            | Consumer                                  | Gets detailed status reports on demand.                                 |
| **Admin Panel** | **Home Catalog** | REST            | Consumer & Provider                       | To read the current system configuration and to add/remove/update items. |
| **Control Unit** | **Home Catalog** | REST            | Provider                                  | Updates the catalog with the latest device status and command reason.   |
| *All Services* | **Home Catalog** | REST            | Consumer                                  | Get initial configuration (broker IP, etc.).                            |

---

## ⚙️ Configuration

Before running the system, you must configure a few credentials:

1.  **ThingSpeak API Keys**:
    -   [cite_start]Open `ThingSpeak/adaptor.py`[cite: 1].
    -   [cite_start]Update the `self.api_keys` dictionary with your own ThingSpeak Channel Write API Keys[cite: 1].

2.  **Telegram Bot Token**:
    -   [cite_start]Open `User_awareness/telegram_bot.py`[cite: 1].
    -   [cite_start]At the bottom, replace the placeholder `token` with your Telegram Bot token from BotFather[cite: 1].

3.  **Telegram User ID (for device ownership)**:
    -   [cite_start]Talk to the `@userinfobot` on Telegram to get your unique Chat ID[cite: 1].
    -   [cite_start]Open `User_awareness/device_ownership.json`[cite: 1].
    -   [cite_start]Replace `"592396681"` with your own Chat ID to claim ownership of a device[cite: 1].

---

## 🚀 Getting Started with Docker

[cite_start]This project is fully containerized, making setup incredibly simple[cite: 1].

### Prerequisites

-   [cite_start][Docker](https://www.docker.com/get-started)[cite: 1]
-   [cite_start][Docker Compose](https://docs.docker.com/compose/install/)[cite: 1]

### Installation & Launch

1.  **Clone the Repository**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-folder>
    ```

2.  **Perform Configuration**
    -   [cite_start]Follow the steps in the **Configuration** section above to add your API keys and tokens[cite: 1].

3.  **Build and Run the System**
    -   From the root directory of the project, run the following single command:
    ```bash
    docker-compose up --build
    ```
    -   [cite_start]This will build the Docker image for all services and start the entire system[cite: 1].

4.  **Access the Dashboard**
    -   Once the containers are running, open your web browser and navigate to:
    -   [cite_start]**`http://localhost:8000`**[cite: 1]

5.  **Interact with the Telegram Bot**
    -   [cite_start]Find your bot on Telegram and use the `/menu` command to start tracking your devices[cite: 1].

---

## 🔧 Managing the System

This project includes a dedicated **Admin Panel** to manage the system's structure.

-   **Access the Admin Panel**: Once the system is running, navigate to **`http://localhost:8081`**

### Adding Houses and Devices

With the admin panel, you can easily:
-   Add new houses, floors, and units.
-   Add new motion sensors to any unit.
-   Remove individual devices from a unit.

When you add a device, it is automatically registered in `catalog.json`. However, to make the new device fully **active** (i.e., start simulating and publishing data), you must perform one manual step:
-   After adding a device, you must manually update `Device_connectors/setting_sen.json` and `Device_connectors/setting_act.json` with the new device's information. This is required because the device connector services read from these static files at startup.

### Removing a House

The admin panel does not currently support removing an entire house. To do this, you must:
-   Manually edit the `catalog.json` file and remove the entire house object from the `housesList` array.