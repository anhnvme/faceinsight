#!/usr/bin/env bashio
set -e

# Read options from Home Assistant
export PORT=$(bashio::config 'web_port')
export HOST="0.0.0.0"
export MQTT_HOST=$(bashio::config 'mqtt_host')
export MQTT_PORT=$(bashio::config 'mqtt_port')
export MQTT_USERNAME=$(bashio::config 'mqtt_username')
export MQTT_PASSWORD=$(bashio::config 'mqtt_password')
export MQTT_TOPIC=$(bashio::config 'mqtt_topic')
export RECOGNITION_THRESHOLD=$(bashio::config 'recognition_threshold')
export MAX_IMAGES_PER_PERSON=$(bashio::config 'max_images_per_person')
export SESSION_SECRET=$(bashio::config 'session_secret')

# Handle custom paths
if bashio::config.true 'use_custom_paths'; then
    export DATA_PATH=$(bashio::config 'data_path')
    export INBOX_PATH=$(bashio::config 'inbox_path')
    export MODELS_PATH=$(bashio::config 'models_path')
else
    export DATA_PATH="/share/faceinsight"
fi

# Create symlinks for data persistence
bashio::log.info "Setting up data directories at ${DATA_PATH}"
mkdir -p "${DATA_PATH}"/{database,models,static/detect,static/original,static/logs,inbox}

# Link directories
ln -sf "${DATA_PATH}/database" /app/database || true
ln -sf "${DATA_PATH}/models" /app/models || true
ln -sf "${DATA_PATH}/static/detect" /app/static/detect || true
ln -sf "${DATA_PATH}/static/original" /app/static/original || true
ln -sf "${DATA_PATH}/inbox" /app/inbox || true

bashio::log.info "Starting FaceInsight on port ${PORT}"
cd /app
exec python3 app.py
