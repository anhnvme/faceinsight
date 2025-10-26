# FaceInsight Home Assistant Add-on - Quick Start

## 🚀 Quick Installation

### Add Repository & Install

1. **Settings** → **Add-ons** → **Add-on Store**
2. Click **⋮** → **Repositories**
3. Add: `https://github.com/anhnvme/faceinsight`
4. Find **FaceInsight** → Click **Install**
5. **Configuration**:
   ```yaml
   web_port: 6080
   mqtt_host: core-mosquitto
   mqtt_port: 1883
   mqtt_topic: faceinsight
   ```
6. **Start** add-on
7. Enable "Start on boot"

### Access

Web UI: `http://homeassistant.local:6080`

**Note:** If port 6080 conflicts with another addon, change `web_port` to `8080`, `8081`, etc.

---

## 📋 Standalone Docker vs HA Addon

### Standalone (Development)

```bash
# Use root Dockerfile
docker-compose up
```

Access: `http://localhost:6080`

### Home Assistant Addon (Production)

```bash
# Use homeassistant/Dockerfile
# Installed via HA Supervisor
```

Access: `http://homeassistant.local:6080`

---

## 🔧 Key Differences

| Feature | Standalone | HA Addon |
|---------|-----------|----------|
| Dockerfile | `/Dockerfile` | `/homeassistant/Dockerfile` |
| Base Image | `python:3.11-slim` | `ghcr.io/home-assistant/base-python` |
| Data Path | `./static/`, `./inbox/` | `/share/faceinsight/` |
| Config | Environment vars | HA config options |
| MQTT | Manual setup | Auto from HA |
| Updates | Manual rebuild | HA Supervisor |

---

## 📁 File Structure

```
FaceInsight/
├── app.py, *.py           ← Core application (shared)
├── templates/, static/    ← Web UI (shared)
├── requirements.txt       ← Dependencies (shared)
├── Dockerfile             ← Standalone Docker
├── docker-compose.yml     ← Standalone compose
│
└── homeassistant/         ← HA Addon specific
    ├── config.json        ← Addon manifest
    ├── Dockerfile         ← Addon Dockerfile
    ├── run.sh             ← Addon entrypoint
    ├── build.json         ← Multi-arch config
    ├── README.md          ← Addon description
    ├── DOCS.md            ← User documentation
    ├── CHANGELOG.md       ← Version history
    ├── INSTALL.md         ← Installation guide
    └── build.sh           ← Build script
```

---

## 🎯 Development Workflow

### 1. Develop Standalone

```bash
cd /root/FaceInsight
docker-compose up
# Make changes, test at localhost:6080
```

### 2. Test Addon Locally

```bash
# Build addon
docker build -f homeassistant/Dockerfile -t faceinsight:test .

# Run
docker run --rm -p 6080:6080 \
  -e MQTT_HOST=localhost \
  faceinsight:test
```

### 3. Deploy to HA

```bash
# Copy to HA
scp -r /root/FaceInsight/* root@homeassistant:/addons/faceinsight/

# Rebuild via HA UI
# Supervisor → FaceInsight → Rebuild
```

---

## 🔔 MQTT Integration

### Topics Published

```
faceinsight/recognition
faceinsight/status
```

### Example Automation

```yaml
automation:
  - alias: "Face Detected"
    trigger:
      platform: mqtt
      topic: faceinsight/recognition
    action:
      - service: notify.mobile_app
        data:
          message: "Detected: {{ trigger.payload_json.nickname }}"
```

---

## 📊 Storage Locations

### Standalone

```
./static/detect/        # Cropped faces
./static/original/      # Original images
./static/logs/          # History images
./inbox/                # Auto-training
./faceinsight.db        # Database
```

### HA Addon

```
/share/faceinsight/static/detect/
/share/faceinsight/static/original/
/share/faceinsight/static/logs/
/share/faceinsight/inbox/
/share/faceinsight/faceinsight.db
```

---

## 🐛 Common Issues

### Addon won't start
- Check logs: Supervisor → FaceInsight → Logs
- Verify MQTT config
- Check `/share/faceinsight/` permissions

### Can't access Web UI
- Ensure port 6080 is not blocked
- Try `http://homeassistant.local:6080`
- Check firewall settings

### MQTT not working
- Test Mosquitto: Developer Tools → MQTT
- Listen to `faceinsight/#`
- Check broker is running

### Models not downloading
- Check internet connection
- Ensure 1GB free space
- Wait 2-3 minutes on first run

---

## 📚 Documentation

- **README.md**: Addon overview
- **DOCS.md**: Configuration guide
- **INSTALL.md**: Detailed installation
- **CHANGELOG.md**: Version history

---

## ✅ Quick Test

1. Add person: Dashboard → Add Person
2. Upload 5 photos
3. Test: Test page → Upload test image
4. Check: History page → View results
5. MQTT: Developer Tools → Listen `faceinsight/recognition`

---

**Need help?** Check INSTALL.md for detailed instructions!
