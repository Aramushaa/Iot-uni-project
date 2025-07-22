@echo off
ECHO Starting ThiefDetector IoT System...

start "Catalog" cmd /c python catalog_registry.py
timeout /t 2 >nul

start "Sensor Connectors" cmd /c python Device_connectors/DC_instancer.py
timeout /t 1 >nul

start "Actuator Connectors" cmd /c python Device_connectors/DC_instancer_actuator.py
timeout /t 1 >nul

start "Control Unit" cmd /c python Control_units/CU_instancer.py
timeout /t 1 >nul

start "ThingSpeak Adaptor" cmd /c python ThingSpeak/adaptor.py
timeout /t 1 >nul

start "Operator Control" cmd /c python User_awareness/operator_control.py
timeout /t 1 >nul

start "Web Frontend" cmd /c cd frontend && python -m http.server 8000

ECHO All services have been started.