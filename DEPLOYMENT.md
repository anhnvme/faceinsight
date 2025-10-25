# FaceInsight - Deployment Options

This project supports two deployment methods:

## 1. 🐳 Standalone Docker (Development/Testing)

**Use case**: Local development, non-HA environments

**Files used**:
- `Dockerfile` (root)
- `docker-compose.yml` (root)
- All `.py` files, `templates/`, `static/`

**Quick start**:
```bash
docker-compose up
# Access: http://localhost:6080
```

**Data location**: 
- `./static/`, `./inbox/`, `./faceinsight.db`

---

## 2. 🏠 Home Assistant Add-on (Production)

**Use case**: Home Assistant OS integration

**Files used**:
- `homeassistant/Dockerfile`
- `homeassistant/config.json`
- `homeassistant/run.sh`
- All `.py` files, `templates/`, `static/` (shared with standalone)

**Quick start**:
```bash
# Copy to HA
scp -r . root@homeassistant:/addons/faceinsight/

# Install via HA UI
# Supervisor → Add-on Store → Local Addons → FaceInsight
```

**Data location**: 
- `/share/faceinsight/`

---

## 📂 Directory Structure

```
FaceInsight/
│
├── Core Application (Shared by both)
│   ├── app.py                    - Flask web server
│   ├── database.py               - SQLite database
│   ├── face_processor.py         - InsightFace wrapper
│   ├── inbox_monitor.py          - Auto-training service
│   ├── mqtt_client.py            - MQTT integration
│   ├── requirements.txt          - Python dependencies
│   ├── templates/                - Jinja2 templates
│   └── static/                   - CSS, JS, images
│
├── Standalone Docker
│   ├── Dockerfile                - Standalone container
│   ├── docker-compose.yml        - Compose config
│   └── .dockerignore             - Build exclusions
│
└── Home Assistant Addon
    └── homeassistant/
        ├── config.json           - HA addon manifest
        ├── Dockerfile            - HA-specific container
        ├── run.sh                - HA entrypoint script
        ├── build.json            - Multi-arch build config
        ├── build.sh              - Build helper script
        ├── README.md             - Addon store description
        ├── DOCS.md               - User documentation
        ├── CHANGELOG.md          - Version history
        ├── INSTALL.md            - Installation guide
        ├── QUICKSTART.md         - Quick reference
        └── .dockerignore         - Addon build exclusions
```

---

## 🔄 Shared vs Specific

### Shared Code (Both deployments)
- ✅ `app.py`, `database.py`, `face_processor.py`
- ✅ `inbox_monitor.py`, `mqtt_client.py`
- ✅ `templates/`, `static/`
- ✅ `requirements.txt`

### Standalone Specific
- 🐳 `Dockerfile` (uses `python:3.11-slim`)
- 🐳 `docker-compose.yml`
- 🐳 Environment variables for config

### HA Addon Specific
- 🏠 `homeassistant/Dockerfile` (uses HA base image)
- 🏠 `homeassistant/config.json` (addon manifest)
- 🏠 `homeassistant/run.sh` (reads HA config)
- 🏠 `homeassistant/*.md` (documentation)

---

## 🛠️ Development Workflow

1. **Make changes** to core files (`app.py`, etc.)
2. **Test standalone**: `docker-compose up`
3. **Test addon**: Build with `homeassistant/build.sh`
4. **Deploy to HA**: Copy to `/addons/faceinsight/`

---

## 📝 Configuration

### Standalone (Environment Variables)
```env
MQTT_HOST=localhost
MQTT_PORT=1883
SESSION_SECRET=your-secret
```

### HA Addon (config.json options)
```yaml
mqtt_host: core-mosquitto
mqtt_port: 1883
max_images_per_person: 10
recognition_threshold: 0.4
```

---

## 📚 Documentation

- **README.md** (this file): Overview
- **homeassistant/QUICKSTART.md**: Quick reference
- **homeassistant/INSTALL.md**: Detailed installation
- **homeassistant/DOCS.md**: Configuration guide
- **homeassistant/README.md**: Addon store description

---

## 🚀 Quick Commands

### Standalone
```bash
docker-compose up              # Start
docker-compose down            # Stop
docker-compose logs -f         # Logs
```

### HA Addon
```bash
# Build locally
cd homeassistant && ./build.sh

# Test build
docker run -p 6080:6080 local/faceinsight:1.0.0-amd64

# Deploy to HA
scp -r . root@homeassistant:/addons/faceinsight/
```

---

**Choose your deployment method and get started! 🎉**
