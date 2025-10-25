# FaceInsight - Installation Guide

## Installation (Recommended)

### Step 1: Add Repository to Home Assistant

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** menu (top right) → **Repositories**
3. Add this repository URL:
   ```
   https://github.com/yourusername/faceinsight-addon
   ```
4. Click **Add** → **Close**

### Step 2: Install FaceInsight Add-on

1. Refresh the Add-on Store page
2. Find **FaceInsight** in the list
3. Click on it → Click **Install**
4. Wait for installation to complete (2-3 minutes)

### Step 3: Configure

1. Go to the **Configuration** tab
2. Set your settings:
   ```yaml
   web_port: 6080             # Change if port conflicts
   mqtt_host: core-mosquitto
   mqtt_port: 1883
   mqtt_topic: faceinsight
   max_images_per_person: 10
   recognition_threshold: 0.4
   use_custom_paths: false
   ```
3. Click **Save**

### Step 4: Start

1. Go to the **Info** tab
2. Click **Start**
3. Enable **"Start on boot"** (optional but recommended)
4. Enable **"Watchdog"** (optional)
5. Click **Logs** to verify it's running

### Step 5: Access Web Interface

Open your browser to:
```
http://homeassistant.local:6080
```

---

## Configuration Examples

### Minimal Configuration (Recommended)

```yaml
web_port: 6080
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_topic: faceinsight
```

### Port Conflict Resolution

If port 6080 is already in use by another addon:

```yaml
web_port: 8080  # or 8081, 9090, 3000, etc.
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_topic: faceinsight
```

Access UI at: `http://homeassistant.local:8080`

### With Authentication

```yaml
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_username: your_mqtt_user
mqtt_password: your_mqtt_password
mqtt_topic: faceinsight
```

### Custom Data Paths (Migration from Docker)

```yaml
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_topic: faceinsight
use_custom_paths: true
data_path: /home/faceinsight/img
inbox_path: /home/homeassistant/www/snapshots_2
models_path: /home/faceinsight/models
```

---

## First Time Setup

### 1. Add Your First Person

1. Open Web UI at `http://homeassistant.local:6080`
2. Click **"Add Person"**
3. Enter:
   - **Nickname**: Display name (e.g., "John Doe")
   - **Name**: System name (auto-generated, can edit)
4. Upload 5-10 clear photos of the person's face
5. Click **Save**

### 2. Test Recognition

1. Go to **Test** page
2. Upload a test photo
3. Verify the person is recognized correctly
4. Adjust **recognition_threshold** if needed

### 3. Set Up Automations

Listen to MQTT topic: `faceinsight/recognition`

Example automation:
```yaml
automation:
  - alias: "Face Detected Notification"
    trigger:
      platform: mqtt
      topic: faceinsight/recognition
    action:
      - service: notify.mobile_app
        data:
          title: "Face Recognized"
          message: "{{ trigger.payload_json.nickname }} detected!"
```

---

## Troubleshooting

### Add-on won't start
- Check **Logs** tab for errors
- Verify MQTT broker is running
- Ensure port 6080 is not already in use

### Can't access Web UI
- Try `http://YOUR_HA_IP:6080` instead
- Check firewall settings
- Verify add-on is running (Info tab shows "Started")

### MQTT not working
- Test MQTT: **Developer Tools** → **MQTT** → Subscribe to `faceinsight/#`
- Verify Mosquitto broker add-on is installed and running
- Check credentials if authentication is enabled

### Models won't download
- Check internet connection
- Ensure at least 1GB free space
- Wait 2-3 minutes on first run
- Check logs for download progress

### Recognition accuracy is poor
- Add more photos per person (10-15 recommended)
- Use clear, front-facing photos
- Lower **recognition_threshold** (try 0.35-0.3)
- Try different model: Web UI → Settings → Model

---

## Updating the Add-on

1. Go to **Settings** → **Add-ons** → **FaceInsight**
2. Click **Update** (if available)
3. Wait for update to complete
4. Restart the add-on

**Your data is safe!** All data is stored outside the addon container:

### Data Persistence

When you update the addon, **only the code is updated**. Your data is preserved because it's stored in:

**Default mode:**
- `/share/faceinsight/faceinsight.db` - Database
- `/share/faceinsight/static/detect/` - Cropped faces
- `/share/faceinsight/static/original/` - Original images  
- `/share/faceinsight/static/logs/` - History
- `/share/faceinsight/inbox/` - Auto-training inbox
- `/share/faceinsight/models/` - Downloaded models

**Custom paths mode:**
- Your specified `data_path`, `inbox_path`, `models_path`

The addon uses **symlinks** to connect these persistent folders to the container:
```
/app/static/detect   → /share/faceinsight/static/detect
/app/static/original → /share/faceinsight/static/original
/app/static/logs     → /share/faceinsight/static/logs
/app/inbox          → /share/faceinsight/inbox
/app/models         → /share/faceinsight/models
/app/faceinsight.db → /share/faceinsight/faceinsight.db
```

✅ **Safe to update anytime** - Your trained faces, database, and settings are never lost!

---

## Uninstalling

1. Stop the add-on
2. Click **Uninstall**
3. Optionally delete data:
   ```bash
   rm -rf /share/faceinsight
   ```

---

## Support

- 📖 [Documentation](https://github.com/yourusername/faceinsight-addon/blob/main/DOCS.md)
- 🐛 [Report Issues](https://github.com/yourusername/faceinsight-addon/issues)
- 💬 [Discussions](https://github.com/yourusername/faceinsight-addon/discussions)

---

**That's it! 🎉 You're ready to use FaceInsight!**
