# 🛡️ ThiefDetector IoT System

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Broker-brightgreen?style=for-the-badge&logo=mqtt)](https://mqtt.org/)

A comprehensive, microservice-based IoT system for home security monitoring. This project simulates a network of sensors and actuators to detect and respond to potential intrusions, providing real-time updates through a web dashboard, a ThingSpeak channel, and a Telegram bot.


---

## ✅ Features

-   **Microservice Architecture**: Fully containerized with Docker Compose for a single-command setup and maximum scalability.
-   **Real-time Web Dashboard**: A dynamic, single-page application that provides a live overview of all connected devices and their statuses.
-   **Intelligent Automation**: Automatically turns lights on for motion detection or low ambient light, and provides on-screen reasons for its actions.
-   **Dynamic Alerts**: Both the global and per-house alerts are time-sensitive and will automatically clear after a period of inactivity.
-   **Cloud Integration**: Pushes sensor and actuator data to ThingSpeak for historical analysis and visualization.
-   **Remote Control & Alerts**: A Telegram bot allows users to claim and monitor devices from anywhere.
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