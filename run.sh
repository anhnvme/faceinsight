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

# Create data directories first
bashio::log.info "Setting up data directories"
mkdir -p "${DATA_PATH}"/{database,static/detect,static/original,static/logs,inbox}

# Handle models path - MUST remove existing /app/models first
if [ -n "$MODELS_PATH" ] && [ "$MODELS_PATH" != "null" ] && [ "$MODELS_PATH" != "" ]; then
    bashio::log.info "Using custom models path: ${MODELS_PATH}"
    mkdir -p "${MODELS_PATH}"
    rm -rf /app/models
    ln -sf "${MODELS_PATH}" /app/models
else
    # Use default models path inside data_path
    bashio::log.info "Using default models path: ${DATA_PATH}/models"
    mkdir -p "${DATA_PATH}/models"
    rm -rf /app/models
    ln -sf "${DATA_PATH}/models" /app/models
fi

# Create symlinks for other data persistence
rm -rf /app/database /app/inbox
ln -sf "${DATA_PATH}/database" /app/database
ln -sf "${DATA_PATH}/inbox" /app/inbox

# For static subdirectories, need to remove and recreate
rm -rf /app/static/detect /app/static/original /app/static/logs
ln -sf "${DATA_PATH}/static/detect" /app/static/detect
ln -sf "${DATA_PATH}/static/original" /app/static/original
ln -sf "${DATA_PATH}/static/logs" /app/static/logs

bashio::log.info "Starting FaceInsight on ${HOST}:${PORT}"
bashio::log.info "Configure MQTT and other settings in the web UI"
bashio::log.info "Data path: ${DATA_PATH}"
bashio::log.info "Models will be stored at: /app/models"

# List directory contents for debugging
bashio::log.info "Checking /app directory..."
ls -la /app/ || bashio::log.warning "Cannot list /app/"

cd /app
bashio::log.info "Executing: python3 app.py"
exec python3 app.py
