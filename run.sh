#!/usr/bin/env bashio
set -e

# Read options from Home Assistant with defaults
PORT=$(bashio::config 'web_port' 6080)
DATA_PATH=$(bashio::config 'data_path' '/share/faceinsight')
MODELS_PATH=$(bashio::config 'models_path' '')
INBOX_PATH=$(bashio::config 'inbox_path' '')

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

# Handle inbox path
if [ -n "$INBOX_PATH" ] && [ "$INBOX_PATH" != "null" ] && [ "$INBOX_PATH" != "" ]; then
    bashio::log.info "Using custom inbox path: ${INBOX_PATH}"
    mkdir -p "${INBOX_PATH}"
    rm -rf /app/inbox
    ln -sf "${INBOX_PATH}" /app/inbox
else
    # Use default inbox path inside data_path
    bashio::log.info "Using default inbox path: ${DATA_PATH}/inbox"
    rm -rf /app/inbox
    ln -sf "${DATA_PATH}/inbox" /app/inbox
fi

# Create symlinks for other data persistence
# Database file is face_recognition.db in /app root, not in a folder
# So we symlink the file itself or make the whole /app persistent (too much)
# Better approach: symlink to data path and update database.py to use DATABASE_PATH env
rm -rf /app/database
ln -sf "${DATA_PATH}/database" /app/database

# Also create a direct symlink for the database file if it exists in data path
if [ -f "${DATA_PATH}/face_recognition.db" ]; then
    bashio::log.info "Found existing database at ${DATA_PATH}/face_recognition.db"
    rm -f /app/face_recognition.db
    ln -sf "${DATA_PATH}/face_recognition.db" /app/face_recognition.db
elif [ -f "${DATA_PATH}/database/face_recognition.db" ]; then
    bashio::log.info "Found existing database at ${DATA_PATH}/database/face_recognition.db"
    rm -f /app/face_recognition.db
    ln -sf "${DATA_PATH}/database/face_recognition.db" /app/face_recognition.db
fi

# For static subdirectories, need to remove and recreate
rm -rf /app/static/detect /app/static/original /app/static/logs
ln -sf "${DATA_PATH}/static/detect" /app/static/detect
ln -sf "${DATA_PATH}/static/original" /app/static/original
ln -sf "${DATA_PATH}/static/logs" /app/static/logs
ln -sf "${DATA_PATH}/static/test" /app/static/test

bashio::log.info "Starting FaceInsight on ${HOST}:${PORT}"
bashio::log.info "Configure MQTT and other settings in the web UI"
bashio::log.info "Data path: ${DATA_PATH}"
bashio::log.info "Models will be stored at: /app/models"

# Verify symlinks
bashio::log.info "Verifying symlinks..."
ls -la /app/models && bashio::log.info "/app/models -> $(readlink -f /app/models 2>/dev/null || echo 'NOT A SYMLINK')"
ls -la /app/database && bashio::log.info "/app/database -> $(readlink -f /app/database 2>/dev/null || echo 'NOT A SYMLINK')"
ls -la /app/inbox && bashio::log.info "/app/inbox -> $(readlink -f /app/inbox 2>/dev/null || echo 'NOT A SYMLINK')"

# List directory contents for debugging
bashio::log.info "Checking /app directory..."
ls -la /app/ || bashio::log.warning "Cannot list /app/"

cd /app
bashio::log.info "Executing: python3 app.py"
exec python3 app.py
