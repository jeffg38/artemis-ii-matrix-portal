# Artemis II Matrix Portal Display 🚀
![Artemis II Matrix Portal Display](IMG_6961.jpg)

A CircuitPython project for the **Adafruit Matrix Portal M4** + **64×32 RGB LED matrix** that displays real-time Artemis II mission status.

## Code Options

- `code.py` → Standard display version  
- `code_with_io.py` → Adds Adafruit IO telemetry logging

The display automatically transitions through mission phases:

* **Pre-launch countdown**
* **Live in-flight telemetry (AROW data)**
* **Post-mission splashdown message**

---

## ✨ Features

* ⏳ **Live countdown to launch**
* 🛰️ **Real-time telemetry display (AROW)**

  * Altitude (miles)
  * Velocity (mph)
  * Mission Elapsed Time (MET)
* 🔁 **Automatic state machine**

  * `PRE_LAUNCH`
  * `IN_FLIGHT`
  * `POST_MISSION`
* 📡 **Memory-efficient partial JSON fetching** (optimized for M4 RAM limits)
* 🎨 Color-coded display for mission phases
* 📜 Smooth scrolling telemetry text

---

## 🧰 Hardware Required

* Adafruit Matrix Portal M4
* 64×32 RGB LED Matrix (HUB75)
* Wi-Fi connection

---

## 📂 Files

* `code.py` — main application 

---

## ⚙️ Setup Instructions

### 1. Install CircuitPython

Install CircuitPython on the Matrix Portal M4:
https://circuitpython.org/board/matrixportal_m4/

---

### 2. Install Required Libraries

Download the matching **Adafruit CircuitPython Library Bundle**:
https://circuitpython.org/libraries

Required libraries in /CIRCUITPY/lib/ (use .mpy versions from CP 10.x bundle):
#   adafruit_matrixportal/
#   adafruit_portalbase/
#   adafruit_esp32spi/
#   adafruit_io/
#   adafruit_minimqtt/
#   adafruit_bus_device/
#   adafruit_requests.mpy
#   adafruit_connection_manager.mpy
#   adafruit_fakerequests.mpy
#   adafruit_ticks.mpy
#   adafruit_imageload/
#   adafruit_display_text/
#   adafruit_bitmap_font/
#   neopixel.mpy
#   adafruit_lis3dh.mpy
#
# IMPORTANT: Use .mpy compiled versions, not .py source versions.
#            The .py versions cause memory errors on the M4.

# AROW telemetry fetched in two small chunks to stay within M4 RAM limits:
#   Chunk 1 (bytes 0-2047):      position 2003/2004/2005, velocity 2009/2010/2011
#   Chunk 2 (bytes 15000-17000): timestamps 5010/5011/5012
#
# Watchdog: script reloads automatically every RELOAD_CYCLES fetch cycles
#           to prevent heap fragmentation during long runs.

### 3. Add Wi-Fi Credentials

Create a file on your device:

```text
/CIRCUITPY/settings.toml
```

Add:

```toml
CIRCUITPY_WIFI_SSID = "your_ssid"
CIRCUITPY_WIFI_PASSWORD = "your_password"
```

---

### 4. Copy Code

Copy `code.py` to the root of the CIRCUITPY drive.

---

## 🚀 How It Works

### Mission Timeline

The script uses fixed mission timing:

* Launch: **April 1, 2026 22:24:00 UTC**
* Mission duration: **~10 days**

---

### State Machine

The display automatically transitions between:

#### PRE_LAUNCH

* Shows:

  * `ARTEMIS II`
  * `COUNTDOWN`
  * Live T-minus clock

#### IN_FLIGHT

* Shows:

  * `ARTEMIS II`
  * `** LIVE **`
  * Scrolling telemetry:

    ```
    ALT:xxxmi SPD:xxxxmph T+xhxxm
    ```

#### POST_MISSION

* Shows:

  * `SPLASHDOWN!`
  * Scrolling crew welcome message

---

### 📡 Telemetry Source (AROW)

Data is fetched from NASA AROW telemetry:

```
https://storage.googleapis.com/.../October_105_1.txt
```

To stay within Matrix Portal memory limits, the script:

* Fetches **two partial byte ranges**
* Extracts:

  * Position (Parameters 2003–2005)
  * Velocity (2009–2011)
  * Timestamp (5010–5012)

---

### 🧮 Calculations

* **Altitude**

  * Derived from position vector
  * Converted from ft → km → miles
  * Earth radius subtracted

* **Velocity**

  * Vector magnitude → mph

* **MET (Mission Elapsed Time)**

  * Computed from telemetry timestamps

---

## 🔧 Configuration

You can adjust:

```python
FETCH_INTERVAL = 120   # seconds between telemetry updates
SCROLL_DELAY   = 0.03  # scroll speed
```

---

## ⚠️ Notes

* Designed specifically for **Matrix Portal M4 RAM constraints**
* Uses aggressive `gc.collect()` calls for stability
* Telemetry may not be available early in mission
* Network failures will show:

  ```
  AWAITING AROW DATA...
  ```

---

## 🛠️ Future Ideas

* Add local RTC fallback
* Add brightness control based on ambient light
* Support different matrix sizes
* Add altitude graphing or icons

---

## 📜 License

Add your preferred license here (MIT is common for this type of project).

---

## 🙌 Credits

* NASA Artemis II mission data
* Adafruit CircuitPython ecosystem
* AROW telemetry feed

---

## 🚀 Demo Idea

Mount the Matrix Portal in a frame and run it as a live mission tracker during Artemis II.

---

## Optional: Adafruit IO Logging

## code_with_io.py (v9.1)

This version adds Adafruit IO cloud logging to the base display code, 
allowing you to record the full Artemis II trajectory data to the cloud 
for later analysis and visualization.

### Additional Setup Required

**settings.toml** — add your Adafruit IO credentials:
```toml
ADAFRUIT_AIO_USERNAME = "your_username"
ADAFRUIT_AIO_KEY = "your_key"
```

**Adafruit IO feeds** — create these three feeds at io.adafruit.com:
- `artemis-altitude` — distance from Earth in miles
- `artemis-speed` — velocity in mph  
- `artemis-met` — mission elapsed time in seconds

### Features vs base version
- Logs altitude, speed, and MET to Adafruit IO after each successful fetch
- Watchdog auto-reload every ~90 minutes to prevent heap fragmentation
- If IO logging fails it continues displaying telemetry silently

### Notes
- Adafruit IO free tier allows 30 data points/minute — well within limits
- Each fetch cycle pushes 3 data points every 2 minutes
- Gaps in IO data indicate either WiFi dropout or NASA telemetry outage
- Rename to code.py before copying to CIRCUITPY drive