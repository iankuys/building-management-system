# Building Management System (Python)

A Python-based Building Management System (BMS) designed for real-time monitoring and control of environmental conditions. Built for Raspberry Pi, it integrates sensor data, LCD display, and multithreaded execution for smooth, concurrent hardware interaction.


## Features

- Reads and processes data from environmental sensors (e.g. DHT)
- **Multithreaded architecture** for concurrent data collection and display
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
