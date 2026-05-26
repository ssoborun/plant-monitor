from m5stack import *
from m5ui import *
from uiflow import *

import unit
import time
import urequests
import json
import wifiCfg

from machine import ADC, Pin

setScreenColor(0x111111)

# ── Configuration ─────────────────────────────────────────────────────────────

# URL de l'API Cloud Run
url = "https://plant-monitoring-api-735616131730.europe-west1.run.app/sensor-data"

headers = {"Content-Type": "application/json"}

# Calibration capteur sol (capacitif)
# Valeur basse = sol mouillé, valeur haute = sol sec
WET_VALUE = 1100   # valeur mesurée dans l'eau
DRY_VALUE = 2500   # valeur mesurée à sec

# Intervalle d'envoi : 4 minutes
INTERVAL_SECONDS = 4 * 60

# ── Connexion WiFi ────────────────────────────────────────────────────────────
lcd.print("Connecting WiFi...", 20, 20, 0xffffff)
wifiCfg.autoConnect(lcdShow=True)
while not wifiCfg.wlan_sta.isconnected():
    lcd.print(".", 20, 50, 0xffffff)
    time.sleep(1)
lcd.clear()
lcd.print("WiFi connected", 20, 20, 0x00ff00)

# ── Initialisation capteurs ───────────────────────────────────────────────────
env3 = unit.get(unit.ENV3, unit.PORTA)  # température, humidité, pression
soil = ADC(Pin(36))                      # capteur sol (ADC broche 36)
soil.atten(ADC.ATTN_11DB)               # plage 0-3.6V
soil.width(ADC.WIDTH_12BIT)             # résolution 12 bits (0-4095)
time.sleep(2)

# ── Boucle principale ─────────────────────────────────────────────────────────
while True:
    lcd.clear()

    # Lecture capteurs ENV III
    temp = env3.temperature
    hum  = env3.humidity
    pres = env3.pressure

    # Lecture ADC brut du capteur sol
    soil_raw = soil.read()

    # Conversion ADC → pourcentage humidité sol
    # 2500 (sec) = 0%, 1100 (mouillé) = 100%
    soil_percent = (DRY_VALUE - soil_raw) * 100 / (DRY_VALUE - WET_VALUE)
    soil_percent = max(0, min(100, round(soil_percent, 1)))

    # Affichage sur l'écran du M5Stack
    lcd.print("Temperature:",  20, 30,  0xffffff)
    lcd.print(str(temp) + " C", 180, 30, 0xffffff)
    lcd.print("Air humidity:", 20, 60,  0xffffff)
    lcd.print(str(hum) + " %",  180, 60, 0xffffff)
    lcd.print("Pressure:",     20, 90,  0xffffff)
    lcd.print(str(pres) + " hPa", 180, 90, 0xffffff)
    lcd.print("Soil raw:",     20, 120, 0xffffff)
    lcd.print(str(soil_raw),   180, 120, 0x00ff00)
    lcd.print("Soil moisture:", 20, 150, 0xffffff)
    lcd.print(str(soil_percent) + " %", 180, 150, 0x00ff00)

    # Vérification WiFi avant envoi
    if not wifiCfg.wlan_sta.isconnected():
        lcd.print("Reconnecting WiFi", 20, 190, 0xff9900)
        speaker.playWAV('/flash/res/todo-mal.wav', volume=6)
        wifiCfg.autoConnect(lcdShow=True)
        retry = 0
        while not wifiCfg.wlan_sta.isconnected() and retry < 10:
            lcd.print(".", 20 + retry * 10, 220, 0xffffff)
            time.sleep(1)
            retry += 1
        if not wifiCfg.wlan_sta.isconnected():
            lcd.print("NO WIFI", 20, 190, 0xff0000)
            speaker.playWAV('/flash/res/no-wifi.wav', volume=6)
            speaker.playWAV('/flash/res/todo-mal.wav', volume=6)
            time.sleep(INTERVAL_SECONDS)
            continue

    # Construction du payload JSON
    data = {
        "device_id":    "core2_plant_01",
        "temperature":  temp,
        "humidity":     hum,
        "pressure":     pres,
        "soil_raw":     soil_raw,
        "soil_moisture": soil_percent
    }

    # Envoi à l'API Cloud Run
    try:
        response = urequests.post(url, data=json.dumps(data), headers=headers)
        lcd.print("HTTP OK", 20, 190, 0x00ff00)
        lcd.print(str(response.status_code), 140, 190, 0x00ff00)
        speaker.playWAV('/flash/res/todo-ok.wav', volume=6)
        response.close()
    except Exception as e:
        lcd.print("HTTP ERROR", 20, 190, 0xff0000)
        lcd.print(str(e), 20, 220, 0xff0000)
        speaker.playWAV('/flash/res/todo-mal.wav', volume=6)

    time.sleep(INTERVAL_SECONDS)
