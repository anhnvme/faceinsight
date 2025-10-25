# Configuration

## Web Interface

### Web Port

Configure the port for accessing the web interface:

```yaml
web_port: 6080  # Default, change if port conflict
```

Common alternatives: `8080`, `8081`, `9090`, `3000`

Access UI at: `http://homeassistant.local:{web_port}`

## MQTT Setup

FaceInsight requires MQTT to send notifications to Home Assistant.

### Using Home Assistant's Mosquitto Broker

If you have the Mosquitto broker addon installed:

```yaml
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_username: your_username  # If authentication is enabled
mqtt_password: your_password  # If authentication is enabled
mqtt_topic: faceinsight
```

### Using External MQTT Broker

```yaml
mqtt_host: 192.168.1.100
mqtt_port: 1883
mqtt_username: mqtt_user
mqtt_password: mqtt_password
mqtt_topic: faceinsight
```

## Application Settings

### Session Secret

Leave empty to auto-generate, or provide your own:

```yaml
session_secret: "your-secret-key-here"
```

### Max Images Per Person

Control how many face images to store per person:

```yaml
max_images_per_person: 10  # Range: 1-25
```

Higher values improve recognition accuracy but use more storage.

### Recognition Threshold

Adjust the similarity threshold for face matching:

```yaml
recognition_threshold: 0.4  # Range: 0.1-0.9
```

- **Lower values** (0.1-0.3): More sensitive, may have false positives
- **Medium values** (0.4-0.6): Balanced (recommended)
- **Higher values** (0.7-0.9): Stricter matching, may miss matches

### Custom Data Paths

**Default behavior** (use_custom_paths: false):
All data stored in `/share/faceinsight/`

**Custom paths** (use_custom_paths: true):
Map to your preferred locations:

```yaml
use_custom_paths: true
data_path: /home/faceinsight
inbox_path: /home/homeassistant/www/snapshots_2
models_path: /home/faceinsight/models
```

**Path mapping:**
- `data_path`: Base directory for database and static files
  - Database: `{data_path}/faceinsight.db`
  - Detected faces: `{data_path}/static/detect/`
  - Original images: `{data_path}/static/original/`
  - History logs: `{data_path}/static/logs/`
  - Test images: `{data_path}/static/test/`
- `inbox_path`: Auto-training inbox folder (default: `{data_path}/inbox`)
- `models_path`: InsightFace models folder (default: `{data_path}/models`)

**Example for existing docker-compose setup:**
```yaml
use_custom_paths: true
data_path: /home/faceinsight/img
inbox_path: /home/homeassistant/www/snapshots_2
models_path: /home/faceinsight/models
```

This maps to:
- `/home/faceinsight/img/static/detect` → Cropped faces
- `/home/faceinsight/img/static/original` → Original images
- `/home/faceinsight/img/static/logs` → History
- `/home/homeassistant/www/snapshots_2` → Inbox (auto-training)
- `/home/faceinsight/models` → InsightFace models
- `/home/faceinsight/img/faceinsight.db` → Database


## First Time Setup

1. **Start the addon** and wait for it to download models (first run takes 2-3 minutes)
2. **Open Web UI** at `http://homeassistant.local:6080`
3. **Add people**:
   - Click "Add Person"
   - Enter nickname (display name) and name (identifier)
   - Upload 5-10 face images per person
4. **Test recognition**:
   - Go to Test page
   - Upload a test image
   - Verify recognition accuracy

## Data Persistence

All data is stored in `/share/faceinsight/` which persists across:
- Addon updates
- Addon restarts
- Home Assistant restarts
- Home Assistant updates

**What is preserved:**
- ✅ Database (`faceinsight.db`) - All people, embeddings, history
- ✅ Cropped face images (`static/detect/`)
- ✅ Original images (`static/original/`)
- ✅ Recognition history images (`static/logs/`)
- ✅ Downloaded models (`models/`)
- ✅ Inbox training data (`inbox/`)

**How it works:**
The addon creates **symlinks** from container paths to persistent storage:

```
Container Path          →  Persistent Storage
/app/faceinsight.db    →  /share/faceinsight/faceinsight.db
/app/static/detect/    →  /share/faceinsight/static/detect/
/app/static/original/  →  /share/faceinsight/static/original/
/app/static/logs/      →  /share/faceinsight/static/logs/
/app/inbox/            →  /share/faceinsight/inbox/
/app/models/           →  /share/faceinsight/models/
```

When you update the addon:
1. New code is pulled from GitHub
2. Container is rebuilt with new code
3. Symlinks reconnect to your existing data
4. All your trained faces and history remain intact

**Backup recommendation**: Include `/share/faceinsight/` in your Home Assistant backups.

## Inbox Auto-Training

To automatically add face images:

1. Access `/share/faceinsight/inbox/` via:
   - Samba share
   - SSH
   - File editor addon

2. Create folder structure:
   ```
   inbox/
   └── personname/
       ├── image1.jpg
       └── image2.jpg
   ```

3. Images are processed automatically every 60 seconds

## Performance Tuning

### For Raspberry Pi 4

```yaml
max_images_per_person: 5  # Lower to reduce processing time
recognition_threshold: 0.5  # Slightly higher for better accuracy
```

### For x86/AMD64 Systems

```yaml
max_images_per_person: 15  # Can handle more images
recognition_threshold: 0.4  # Standard setting
```

## Troubleshooting

### Addon won't start

Check logs for:
- MQTT connection errors → Verify broker settings
- Database errors → Delete `/share/faceinsight/faceinsight.db` to reset
- Model download errors → Check internet connection

### Recognition not working

1. Ensure at least 5 images per person
2. Use clear, front-facing photos
3. Check recognition threshold (try lowering to 0.3)
4. Review logs for detection errors

### MQTT messages not received

1. Verify broker is running: `Supervisor → Mosquitto broker → Logs`
2. Test MQTT: Go to `Developer Tools → MQTT` and listen to `faceinsight/#`
3. Check addon logs for connection errors

## Advanced Configuration

### Custom Models

The addon supports InsightFace models:
- `buffalo_s` (default) - Smaller, faster
- `buffalo_l` - Larger, more accurate
- `antelopev2` - Best accuracy, slower

Change via Web UI → Settings → Model Selection

### Storage Management

Monitor storage via Web UI → Dashboard:
- **Models**: ~300MB per model
- **Data**: ~2MB per person (with 10 images)
- **History**: ~500KB per day (with 50 recognitions)

Auto-cleanup runs daily to maintain 30 days of history.
