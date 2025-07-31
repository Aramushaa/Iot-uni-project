graph TD
    subgraph User Awareness
        WebInterface[Web Dashboard]
        TelegramBot[Telegram Bot]
    end

    subgraph Core Services
        OperatorControl[Operator Control API]
        ControlUnit[Control Unit]
        HomeCatalog[Home Catalog]
    end
    
    subgraph External
        ThingSpeakAdaptor[ThingSpeak Adaptor]
        ThingSpeakCloud([ThingSpeak Cloud])
    end

    subgraph Devices
        Sensors[Device Connector for Sensors]
        Actuators[Device Connector for Actuators]
    end

    subgraph Broker
        MessageBroker[Message Broker]
    end

    %% Connections
    WebInterface -->|REST: Get House Data| OperatorControl
    TelegramBot -->|REST: Track Devices| OperatorControl
    
    OperatorControl -->|REST: Get Config| HomeCatalog
    OperatorControl -->|REST: Get Device Status| Sensors
    OperatorControl -->|REST: Get Device Status| Actuators

    Sensors -->|MQTT: Publish Data| MessageBroker
    
    MessageBroker -->|MQTT: Sensor Data| ControlUnit
    MessageBroker -->|MQTT: Sensor Data| ThingSpeakAdaptor
    MessageBroker -->|MQTT: Sensor & Command Alerts| TelegramBot
    
    ControlUnit -->|MQTT: Publish Commands| MessageBroker
    ControlUnit -->|REST: Update Device Status & Reason| HomeCatalog
    
    MessageBroker -->|MQTT: Commands| Actuators

    ThingSpeakAdaptor -->|REST: Post Data| ThingSpeakCloud
