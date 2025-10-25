#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: FaceInsight
# Runs the FaceInsight Face Recognition System
# ==============================================================================

bashio::log.info "Starting FaceInsight..."

# Read configuration from Home Assistant
WEB_PORT=$(bashio::config 'web_port')
MQTT_HOST=$(bashio::config 'mqtt_host')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_USERNAME=$(bashio::config 'mqtt_username')
MQTT_PASSWORD=$(bashio::config 'mqtt_password')
MQTT_TOPIC=$(bashio::config 'mqtt_topic')
SESSION_SECRET=$(bashio::config 'session_secret')
MAX_IMAGES=$(bashio::config 'max_images_per_person')
THRESHOLD=$(bashio::config 'recognition_threshold')

# Path configuration
USE_CUSTOM_PATHS=$(bashio::config 'use_custom_paths')
DATA_PATH=$(bashio::config 'data_path')
INBOX_PATH=$(bashio::config 'inbox_path')
MODELS_PATH=$(bashio::config 'models_path')

# Set environment variables
export WEB_PORT="${WEB_PORT}"
export MQTT_HOST="${MQTT_HOST}"
export MQTT_PORT="${MQTT_PORT}"
export MQTT_USERNAME="${MQTT_USERNAME}"
export MQTT_PASSWORD="${MQTT_PASSWORD}"
export MQTT_TOPIC="${MQTT_TOPIC}"
export SESSION_SECRET="${SESSION_SECRET:-$(openssl rand -hex 32)}"
export MAX_IMAGES_PER_PERSON="${MAX_IMAGES}"
export RECOGNITION_THRESHOLD="${THRESHOLD}"

# Use custom paths if enabled, otherwise use default /share location
if bashio::config.true 'use_custom_paths'; then
    bashio::log.info "Using custom data paths..."
    
    # Use user-specified paths or defaults
    DATA_DIR="${DATA_PATH}"
    INBOX_DIR="${INBOX_PATH:-${DATA_PATH}/inbox}"
    MODELS_DIR="${MODELS_PATH:-${DATA_PATH}/models}"
else
    bashio::log.info "Using default /share/faceinsight paths..."
    DATA_DIR="/share/faceinsight"
    INBOX_DIR="${DATA_DIR}/inbox"
    MODELS_DIR="${DATA_DIR}/models"
fi

export DB_PATH="${DATA_DIR}/faceinsight.db"

# Create directory structure
bashio::log.info "Setting up directories..."
mkdir -p "${DATA_DIR}"
mkdir -p "${DATA_DIR}/static/detect"
mkdir -p "${DATA_DIR}/static/original"
mkdir -p "${DATA_DIR}/static/logs"
mkdir -p "${DATA_DIR}/static/test"
mkdir -p "${INBOX_DIR}"
mkdir -p "${MODELS_DIR}"

# Create symlinks from app directories to data locations
bashio::log.info "Creating symlinks..."
ln -sf "${DATA_DIR}/static/detect" /app/static/detect
ln -sf "${DATA_DIR}/static/original" /app/static/original
ln -sf "${DATA_DIR}/static/logs" /app/static/logs
ln -sf "${DATA_DIR}/static/test" /app/static/test
ln -sf "${INBOX_DIR}" /app/inbox
ln -sf "${MODELS_DIR}" /app/models

# Symlink database file (with backward compatibility check)
if [ -f "${DATA_DIR}/faceinsight.db" ]; then
    ln -sf "${DATA_DIR}/faceinsight.db" /app/faceinsight.db
    bashio::log.info "Database found and linked"
elif [ -f "${DATA_DIR}/face_recognition.db" ]; then
    # Backward compatibility: rename old database
    mv "${DATA_DIR}/face_recognition.db" "${DATA_DIR}/faceinsight.db"
    ln -sf "${DATA_DIR}/faceinsight.db" /app/faceinsight.db
    bashio::log.info "Migrated old database (face_recognition.db → faceinsight.db)"
else
    # First run: link will be created when app creates the database
    ln -sf "${DATA_DIR}/faceinsight.db" /app/faceinsight.db
    bashio::log.info "New database will be created"
fi

bashio::log.info "Configuration loaded:"
bashio::log.info "  Web Port: ${WEB_PORT}"
bashio::log.info "  MQTT Host: ${MQTT_HOST}:${MQTT_PORT}"
bashio::log.info "  MQTT Topic: ${MQTT_TOPIC}"
bashio::log.info "  Max Images: ${MAX_IMAGES}"
bashio::log.info "  Threshold: ${THRESHOLD}"
bashio::log.info "  Data Path: ${DATA_DIR}"
bashio::log.info "  Inbox Path: ${INBOX_DIR}"
bashio::log.info "  Models Path: ${MODELS_DIR}"
bashio::log.info "  Database: ${DB_PATH}"

# Change to app directory
cd /app || bashio::exit.nok "Cannot change to /app directory"

# Set PORT environment variable for Flask app
export PORT="${WEB_PORT}"
export HOST="0.0.0.0"

# Start the application on configured port
bashio::log.info "Starting FaceInsight application on port ${WEB_PORT}..."
exec python3 app.py
