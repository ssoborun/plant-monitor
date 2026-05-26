import os
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from google.cloud import bigquery

app = Flask(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID")
DATASET_ID = os.environ.get("DATASET_ID", "plant_monitoring")
TABLE_ID   = os.environ.get("TABLE_ID", "sensor_readings")

client = bigquery.Client()

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "api running"}), 200

@app.route("/sensor-data", methods=["POST"])
def receive_sensor_data():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    row = {
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "device_id":    data.get("device_id", "unknown"),
        "temperature":  float(data.get("temperature")),
        "humidity":     float(data.get("humidity")),
        "pressure":     float(data.get("pressure")),
        "soil_raw":     int(data.get("soil_raw")),
        "soil_moisture": str(data.get("soil_moisture")),  # STRING comme dans le schema
    }

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    errors = client.insert_rows_json(table_ref, [row])

    if errors:
        return jsonify({"status": "error", "errors": errors}), 500
    return jsonify({"status": "ok", "inserted": row}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
