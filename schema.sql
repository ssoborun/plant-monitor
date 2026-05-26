-- Schema BigQuery pour le projet Plant Monitor
-- Dataset : plant_monitoring (aligné avec le dashboard et l'API)

CREATE SCHEMA `cryptic-spanner-311208.plant_monitoring`;

CREATE TABLE `cryptic-spanner-311208.plant_monitoring.sensor_readings`
(
  timestamp     TIMESTAMP,   -- Heure de la mesure (UTC)
  device_id     STRING,      -- Identifiant du M5Stack
  temperature   FLOAT64,     -- Température en °C
  humidity      FLOAT64,     -- Humidité relative en %
  pressure      FLOAT64,     -- Pression atmosphérique en hPa
  soil_raw      INT64,       -- Valeur ADC brute du capteur sol
  soil_moisture STRING       -- Humidité sol en % (calculée)
)
PARTITION BY DATE(timestamp); -- Partitionnement pour optimiser les requêtes
