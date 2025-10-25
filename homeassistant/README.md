# FaceInsight - Home Assistant Add-on

![FaceInsight Logo](logo.png)

Face Recognition System powered by InsightFace for Home Assistant.

## About

FaceInsight is a powerful face recognition system that integrates seamlessly with Home Assistant. It provides:

- 🎭 Real-time face recognition using InsightFace
- 📸 Face detection and embedding extraction
- 🔄 Automatic training from inbox folder
- 📊 Recognition history with statistics
- 🔔 MQTT notifications for Home Assistant automations
- 🎨 Beautiful web interface for management

## Installation

1. **Add Repository**:
   - Navigate to Home Assistant Add-on Store
   - Click on the menu (⋮) → Repositories
   - Add this repository URL: `https://github.com/yourusername/faceinsight-addon`

2. **Install Add-on**:
   - Find "FaceInsight" in the add-on store
   - Click "Install"
   - Wait for installation to complete

3. **Configure**:
   - Go to Configuration tab
   - Set your MQTT settings
   - Adjust other options as needed

4. **Start**:
   - Click "Start"
   - Enable "Start on boot" if desired
   - Check logs for any errors

5. **Access Web UI**:
   - Open `http://homeassistant.local:6080`

For detailed instructions, see [INSTALL.md](INSTALL.md)

## Configuration

### MQTT Settings

```yaml
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_username: ""  # Optional
mqtt_password: ""  # Optional
mqtt_topic: faceinsight
```

### Web Interface

```yaml
web_port: 6080  # Change if port conflicts with other addons
```

### Application Settings

```yaml
session_secret: ""  # Auto-generated if empty
max_images_per_person: 10
recognition_threshold: 0.4
```

### Custom Data Paths (Optional)

**Use default paths** (recommended for new installations):
```yaml
use_custom_paths: false
data_path: /share/faceinsight
```

**Use custom paths** (for migration from docker-compose):
```yaml
use_custom_paths: true
data_path: /home/faceinsight/img
inbox_path: /home/homeassistant/www/snapshots_2
models_path: /home/faceinsight/models
```

This allows you to:
- Reuse existing data from standalone Docker setup
- Share inbox folder with other services
- Store models in a shared location

## Options

### `web_port` (required)
Port for the web interface. Default: `6080`

Change if you have port conflicts with other addons.

### `mqtt_host` (required)
MQTT broker hostname. Use `core-mosquitto` for Home Assistant's built-in broker.

### `mqtt_port` (required)
MQTT broker port. Default: `1883`

### `mqtt_username` (optional)
MQTT username for authentication.

### `mqtt_password` (optional)
MQTT password for authentication.

### `mqtt_topic` (required)
Base topic for MQTT messages. Default: `faceinsight`

### `session_secret` (optional)
Secret key for Flask sessions. Auto-generated if not provided.

### `max_images_per_person` (required)
Maximum number of images to store per person. Range: 1-25, Default: 10

### `recognition_threshold` (required)
Similarity threshold for face recognition. Range: 0.1-0.9, Default: 0.4

### `data_path` (required)
Base directory for storing data. Default: `/share/faceinsight`

### `inbox_path` (optional)
Custom path for auto-training inbox. Default: `{data_path}/inbox`

### `models_path` (optional)
Custom path for InsightFace models. Default: `{data_path}/models`

### `use_custom_paths` (required)
Enable custom path mapping. Default: `false`

When enabled:
- Use your specified `data_path`, `inbox_path`, `models_path`
- Useful for migrating from docker-compose setup
- Allows sharing folders with other services

## Usage

### Web Interface

Access the web interface at: `http://homeassistant.local:6080`

- **Dashboard**: Manage people and their face images
- **History**: View recognition history
- **Test**: Test face recognition with uploaded images
- **Settings**: Configure MQTT, models, and storage

### MQTT Topics

The addon publishes to these topics:

- `faceinsight/recognition`: Face recognition events
  ```json
  {
    "person_name": "John Doe",
    "nickname": "John",
    "score": 0.85,
    "timestamp": "2025-10-25T10:30:00"
  }
  ```

- `faceinsight/status`: System status updates

### Inbox Folder

Place images in `/share/faceinsight/inbox/PersonName/` for automatic training:

```
/share/faceinsight/inbox/
├── johndoe/
│   ├── photo1.jpg
│   └── photo2.jpg
└── janedoe/
    └── photo1.jpg
```

Images will be automatically processed and added to the system.

## Data Storage

All data is stored in `/share/faceinsight/`:

```
/share/faceinsight/
├── faceinsight.db          # Database (people, embeddings, history)
├── static/
│   ├── detect/             # Cropped face images
│   ├── original/           # Original images
│   ├── logs/               # Recognition history images
│   └── test/               # Test uploads
├── inbox/                  # Auto-training inbox
└── models/                 # InsightFace models (auto-downloaded)
```

**Data persistence:** When you update the addon, your data is **never lost**. The addon uses symlinks to connect the container to persistent storage outside the container. Only code is updated, data remains intact.

**Backup:** Include `/share/faceinsight/` in Home Assistant backups to preserve all your trained faces and recognition history.

## Automation Examples

### Notify on Recognition

```yaml
automation:
  - alias: "Face Recognized Notification"
    trigger:
      platform: mqtt
      topic: faceinsight/recognition
    action:
      - service: notify.mobile_app
        data:
          title: "Face Recognized"
          message: "{{ trigger.payload_json.nickname }} detected ({{ (trigger.payload_json.score * 100) | round }}% confidence)"
```

### Turn on Lights When Home

```yaml
automation:
  - alias: "Welcome Home Lights"
    trigger:
      platform: mqtt
      topic: faceinsight/recognition
    condition:
      - condition: template
        value_template: "{{ trigger.payload_json.person_name == 'johndoe' }}"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
```

## Support

- 📖 [Documentation](https://github.com/yourusername/faceinsight)
- 🐛 [Issue Tracker](https://github.com/yourusername/faceinsight/issues)
- 💬 [Discussions](https://github.com/yourusername/faceinsight/discussions)

## Credits

- [InsightFace](https://github.com/deepinsight/insightface) - Face recognition library
- [Home Assistant](https://www.home-assistant.io/) - Home automation platform

## License

MIT License - See LICENSE file for details
