# 🛡️ ThiefDetector IoT System

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Broker-brightgreen?style=for-the-badge&logo=mqtt)](https://mqtt.org/)

A comprehensive, microservice-based IoT system for home security monitoring. This project simulates a network of sensors and actuators to detect and respond to potential intrusions, providing real-time updates through a web dashboard, a ThingSpeak channel, and a Telegram bot.

![Dashboard Screenshot](docs/dashboard.png)

---

## ✅ Features

-   **Microservice Architecture**: Fully containerized with Docker Compose for a single-command setup and maximum scalability.
-   **Real-time Web Dashboard**: A dynamic, single-page application that provides a live overview of all connected devices and their statuses.
-   **Intelligent Automation**: Automatically turns lights ON for motion detection or low ambient light, and provides on-screen reasons for its actions.
-   **Dynamic Alerts**: Both the global and per-house alerts are time-sensitive and will automatically clear after a period of inactivity.
-   **Cloud Integration**: Pushes sensor and actuator data to ThingSpeak for historical analysis and visualization.
-   **Remote Control & Alerts**: A Telegram bot allows users to claim and monitor devices and receive real-time motion alerts.
-   **Dynamic Service Discovery**: A central Catalog service allows all components to discover each other dynamically within the Docker network.

---

## 🛠️ Technology Stack

-   **Backend**: Python, CherryPy, Flask
-   **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
-   **Messaging**: MQTT (Eclipse Mosquitto Broker)
-   **Containerization**: Docker & Docker Compose

---

## 🏛️ Architecture Overview

The system follows a microservice architecture where each component is a standalone Docker container. Services communicate through REST APIs for configuration and an MQTT message broker for real-time events.

```mermaid
graph TD
    subgraph User Interfaces
        A[Web Dashboard]
        B[Telegram Bot]
    end

    subgraph Backend Services
        C[Operator Control API]
        D[Control Unit]
        E[Catalog]
        F[ThingSpeak Adaptor]
    end

    subgraph Simulated Devices
        G[Sensors]
        H[Actuators]
    end

    subgraph Message Broker
        MQTT
    end

    A --> |HTTP GET| C
    B --> |HTTP GET| C
    C --> |HTTP GET| E
    C --> |HTTP GET| G
    C --> |HTTP GET| H

    G --> |Publish Sensor Data| MQTT
    MQTT --> |Subscribe to Sensors| D
    MQTT --> |Subscribe to Sensors| F
    D --> |Publish Commands| MQTT
    MQTT --> |Subscribe to Commands| H
    F --> |HTTP POST| ThingSpeak([ThingSpeak Cloud])
```

---

## 🧩 Components

| Component              | File(s)                                       | Purpose                                                                                |
| ---------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------- |
| **Catalog Registry** | `Catalog/catalog_registry.py`                 | The single source of truth. Manages service discovery and device registration.         |
| **Sensor Connectors** | `Device_connectors/DC_instancer.py`           | Simulates multiple sensor devices and publishes their data to MQTT.                    |
| **Actuator Connectors**| `Device_connectors/DC_instancer_actuator.py`  | Simulates multiple actuators and subscribes to MQTT command topics.                    |
| **Control Unit** | `Control_units/CU_instancer.py`               | The system's brain. Subscribes to sensor data and publishes commands based on logic.   |
| **ThingSpeak Adaptor** | `ThingSpeak/adaptor.py`                       | Listens to MQTT and pushes data to the ThingSpeak cloud platform for visualization.    |
| **Operator Control** | `Operator_control/operator_control.py`        | An API Gateway that aggregates data from all services for the user interfaces.         |
| **Web Interface** | `User_awareness/frontEnd/`                    | A static web dashboard that polls the Operator Control API for real-time updates.      |
| **Telegram Bot** | `User_awareness/telegram_bot.py`              | Allows users to interact with their devices via the Telegram app.                      |

---

## ⚙️ Configuration

Before running the system, you must configure a few credentials:

1.  **ThingSpeak API Keys**:
    -   Open `ThingSpeak/adaptor.py`.
    -   Update the `self.api_keys` dictionary with your own ThingSpeak Channel Write API Keys.

2.  **Telegram Bot Token**:
    -   Open `User_awareness/telegram_bot.py`.
    -   At the bottom, replace the placeholder `token` with your Telegram Bot token from BotFather.

3.  **Telegram User ID (for device ownership)**:
    -   Talk to the `@userinfobot` on Telegram to get your unique Chat ID.
    -   Open `User_awareness/device_ownership.json`.
    -   Replace `"592396681"` with your own Chat ID to claim ownership of a device.

---

## 🚀 Getting Started with Docker

This project is fully containerized, making setup incredibly simple.

### Prerequisites

-   [Docker](https://www.docker.com/get-started)
-   [Docker Compose](https://docs.docker.com/compose/install/)

### Installation & Launch

1.  **Clone the Repository**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-folder>
    ```

2.  **Perform Configuration**
    -   Follow the steps in the **Configuration** section above to add your API keys and tokens.

3.  **Build and Run the System**
    -   From the root directory of the project, run the following single command:
    ```bash
    docker-compose up --build
    ```
    -   This will build the Docker image for all services and start the entire system.

4.  **Access the Dashboard**
    -   Once the containers are running, open your web browser and navigate to:
    -   **`http://localhost:8000`**

5.  **Interact with the Telegram Bot**
    -   Find your bot on Telegram and use the `/menu` command to start tracking your devices.

