# Face Recognition System

## Overview

This is a Python-based face recognition application that monitors an inbox folder for images, detects and recognizes faces using the InsightFace library, and integrates with Home Assistant via MQTT. The system provides a Flask web interface for managing known faces, viewing recognition history, and configuring settings. It runs entirely on CPU and is optimized for Intel N100 processors.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Structure

**Monolithic Flask Application**: The system uses a single Flask application (`app.py`) as the main entry point, coordinating between multiple specialized components. This architecture provides simplicity for a focused use case while maintaining clear separation of concerns through modular components.

**Component-Based Design**: The application is divided into five core modules:
- `face_processor.py` - Handles face detection, alignment, and embedding extraction using InsightFace
- `database.py` - Manages SQLite operations for persons, face images, embeddings, and recognition history
- `mqtt_client.py` - Handles MQTT communication with Home Assistant
- `inbox_monitor.py` - Watches the inbox folder for new images using the watchdog library
- `app.py` - Orchestrates all components and provides the web interface

**Rationale**: This modular approach allows each component to be independently tested and maintained while keeping the overall system architecture simple enough to understand and deploy quickly.

### Data Storage

**SQLite Database**: All application data is stored in a single SQLite database (`face_recognition.db`) with three main tables:
- `persons` - Stores person metadata (name, nickname)
- `face_images` - Stores face image paths and their corresponding embeddings (serialized as JSON text)
- `recognition_history` - Logs all recognition events with timestamps, scores, and image references
- `settings` - Stores application configuration (MQTT settings, model selection, recognition threshold)

**Rationale**: SQLite was chosen for its zero-configuration nature, file-based storage, and sufficient performance for this single-user application. Face embeddings are stored as JSON-serialized arrays in TEXT columns, which is simple and adequate for the expected scale (max 10 images per person).

**File Storage**: Original face images and thumbnails are stored in the `static/uploads/` and `static/thumbnails/` directories. The database maintains paths to these files rather than storing binary data directly.

### Face Recognition Pipeline

**InsightFace Library**: The system uses InsightFace's pre-trained models running on CPU with the following pipeline:
1. Face detection and alignment using RetinaFace
2. Feature extraction to generate 512-dimensional embeddings
3. Cosine similarity comparison against stored embeddings

**Model Options**: Three models are supported with different speed/accuracy tradeoffs:
- `buffalo_s` (MobileFaceNet) - Default, optimized for speed on N100 CPU
- `buffalo_m` (ResNet34) - Balanced
- `buffalo_l` (ResNet100) - Highest accuracy, slower

**CPU Optimization**: Environment variables (`OMP_NUM_THREADS=4`, `MKL_NUM_THREADS=4`) are set to optimize performance on the Intel N100 processor. Detection size is set to 640x640 for good balance between speed and accuracy.

**Image Processing**: Detected faces are cropped to minimum 320x320 pixels before being resized to the model's input size (112x112) to preserve quality during alignment.

### Inbox Monitoring System

**Watchdog-Based Monitoring**: The `InboxMonitor` class uses the watchdog library to monitor the `./inbox/` directory for new image files (JPEG/PNG). This provides real-time detection without polling.

**Processing Workflow**:
1. New image detected → validate format and size
2. Wait briefly to ensure file copy is complete
3. Detect and align face → extract embedding
4. Compare against database (top-k matching with threshold)
5. Publish result to MQTT
6. Store in recognition history with thumbnail
7. Auto-train: If matched with high confidence, add to person's training set
8. Delete original inbox image

**Rationale**: Watchdog provides efficient file system monitoring without constant polling. The auto-training feature improves recognition accuracy over time by adding successfully recognized images back to the training set.

### MQTT Integration

**Home Assistant Integration**: The application publishes recognition events to MQTT topics configured for Home Assistant consumption. The payload includes:
- Event type (`face_detected`)
- Person name (or "unknown")
- Confidence score
- Nickname
- Timestamp

**Paho MQTT Client**: Uses the `paho-mqtt` library with persistent connections and automatic reconnection handling. The MQTT client is configured through the web interface settings page.

**Rationale**: MQTT is the standard protocol for Home Assistant integrations, providing reliable, lightweight messaging. The JSON payload structure is designed to be easily consumed by Home Assistant automations.

### Web Interface

**Flask + Jinja2 Templates**: Traditional server-side rendered templates using Flask's templating engine. The interface provides four main pages:
- Index - Person management (add/edit/delete persons, manage face images)
- Test - Manual recognition testing with instant feedback
- History - Recognition log with undo functionality
- Settings - MQTT configuration and model selection

**Rationale**: Server-side rendering keeps the application simple without requiring a separate frontend build process. JavaScript is used minimally for interactive features like file uploads and AJAX form submissions.

### Multi-Threading

**Background Threads**: The inbox monitor runs in a separate thread to avoid blocking the Flask application. MQTT operations also run in background threads managed by the paho-mqtt client.

**Thread Safety**: SQLite connections are created per-thread using `sqlite3.connect()` in each operation, avoiding connection sharing issues. The `PRAGMA foreign_keys = ON` ensures referential integrity.

## External Dependencies

### Core Libraries

**InsightFace**: Deep learning library for face detection and recognition. Provides pre-trained models (buffalo series) that work on CPU. The application uses `buffalo_s` by default but supports switching between models.

**OpenCV (cv2)**: Used for image loading, preprocessing, and thumbnail generation. Handles image format conversions and resizing operations.

**Flask**: Web framework providing the HTTP server, routing, templating, and request handling. Version 2.x+ required for modern security features.

**SQLite3**: Built-in Python database engine, no external service required.

**Watchdog**: File system monitoring library that triggers callbacks when files are created in the inbox directory.

**Paho MQTT**: Python MQTT client library for publishing recognition events to Home Assistant.

### Optional Dependencies

**NumPy**: Required by InsightFace and OpenCV for array operations and mathematical computations on embeddings.

**Werkzeug**: Flask's dependency, provides secure filename handling and file upload utilities.

### External Services

**Home Assistant**: MQTT broker integration for smart home automation. The application publishes to configurable topics (default: `homeassistant/face_detection`).

**MQTT Broker**: Can be Home Assistant's built-in Mosquitto broker or an external MQTT broker. Configuration includes host, port, optional authentication, and topic prefix.

### System Requirements

**CPU-Only Operation**: Designed to run on CPU without GPU acceleration, optimized for Intel N100 processors with thread limits set appropriately.

**File System**: Requires read/write access to:
- `./inbox/` - Monitored directory for incoming images
- `./static/uploads/` - Stored face images
- `./static/thumbnails/` - Recognition history thumbnails
- `face_recognition.db` - SQLite database file