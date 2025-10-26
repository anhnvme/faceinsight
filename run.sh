#!/usr/bin/env bashio
set -e

# Read options from Home Assistant with defaults
PORT=$(bashio::config 'web_port' 6080)
DATA_PATH=$(bashio::config 'data_path' '/share/faceinsight')
MODELS_PATH=$(bashio::config 'models_path' '')

# Set environment variables
export PORT="${PORT}"
export HOST="0.0.0.0"
export DATA_PATH="${DATA_PATH}"

bashio::log.info "Web port: ${PORT}"
bashio::log.info "Data path: ${DATA_PATH}"

# Handle models path
if [ -n "$MODELS_PATH" ] && [ "$MODELS_PATH" != "null" ] && [ "$MODELS_PATH" != "" ]; then
    bashio::log.info "Using custom models path: ${MODELS_PATH}"
    mkdir -p "${MODELS_PATH}"
    ln -sf "${MODELS_PATH}" /app/models || true
else
    # Use default models path inside data_path
    bashio::log.info "Using default models path: ${DATA_PATH}/models"
    mkdir -p "${DATA_PATH}/models"
    ln -sf "${DATA_PATH}/models" /app/models || true
fi

# Create data directories
bashio::log.info "Setting up data directories"
mkdir -p "${DATA_PATH}"/{database,static/detect,static/original,static/logs,inbox}

# Create symlinks for data persistence
ln -sf "${DATA_PATH}/database" /app/database || true
ln -sf "${DATA_PATH}/static/detect" /app/static/detect || true
ln -sf "${DATA_PATH}/static/original" /app/static/original || true
ln -sf "${DATA_PATH}/inbox" /app/inbox || true

bashio::log.info "Starting FaceInsight on ${HOST}:${PORT}"
bashio::log.info "Configure MQTT and other settings in the web UI"
cd /app
exec python3 app.py
