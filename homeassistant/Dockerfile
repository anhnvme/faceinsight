ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.19
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/ash", "-o", "pipefail", "-c"]

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    g++ \
    make \
    cmake \
    musl-dev \
    python3-dev \
    openblas-dev \
    lapack-dev \
    linux-headers \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev \
    harfbuzz-dev \
    fribidi-dev \
    libpng-dev \
    libwebp-dev \
    libgomp \
    ffmpeg-libs \
    libstdc++

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY database.py .
COPY face_processor.py .
COPY inbox_monitor.py .
COPY mqtt_client.py .
COPY templates templates/
COPY static static/

# Create necessary directories
RUN mkdir -p \
    /app/inbox \
    /app/models \
    /data/faceinsight \
    /share/faceinsight

# Copy run script
COPY homeassistant/run.sh /
RUN chmod a+x /run.sh

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:6080/ || exit 1

# Labels
LABEL \
    io.hass.name="FaceInsight" \
    io.hass.description="Face Recognition System with InsightFace" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    maintainer="Your Name <your.email@example.com>"

CMD ["/run.sh"]
