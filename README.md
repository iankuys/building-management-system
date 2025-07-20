# Building Management System (Python)

This is a Python-based Building Management System (BMS) designed to integrate environmental sensors and display systems for real-time monitoring and control. The system was developed using Raspberry Pi-compatible hardware components and includes support for LCD displays, temperature and humidity sensors, and serial data collection.

## Features

- Reads and processes data from environmental sensors (e.g. DHT)
- Displays data on I2C-connected LCD (16x2) modules
- Interfaces with CIMIS weather data (California Irrigation Management Information System)
- Modular and extensible Python codebase
- Real-time monitoring loop via `main.py`
- Bug fixes and enhancements to common libraries (LCD, PCF8574)

## File Overview

| File | Description |
|------|-------------|
| `main.py` | Entry point. Initializes and runs the BMS loop. |
| `Adafruit_LCD1602.py` | LCD driver using Adafruit protocol. |
| `PCF8574.py` | Handles I2C communication for LCD via IO expander. |
| `LCD.py` | Custom LCD logic with bug fixes and display handling. |
| `Freenove_DHT.py` | Reads DHT sensor data (temperature, humidity). |
| `CIMIS.py` | Pulls data from the CIMIS system. |
| `requirements.txt` | Python dependencies list. |

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Run app with:
```bash
python main.py
```
