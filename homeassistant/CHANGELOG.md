# Changelog

All notable changes to this add-on will be documented in this file.

## [1.0.0] - 2025-10-25

### Added
- Initial release of FaceInsight Home Assistant Add-on
- Face recognition using InsightFace (buffalo_s, buffalo_l, antelopev2 models)
- Web interface for person management
- MQTT integration for Home Assistant automations
- Automatic training from inbox folder
- Recognition history with bounding boxes
- Storage management and cleanup
- Settings page for configuration
- Test page for verification
- Support for nicknames and display names
- Auto-slug name generation from Vietnamese text
- Shared JavaScript utilities
- Image preview modal with ESC key support
- Click-to-view original images

### Features
- Real-time face detection and recognition
- Multi-person support with configurable limits
- Automatic cleanup of old history (30 days retention)
- Model switching (buffalo_s/buffalo_l/antelopev2)
- MQTT notifications with person details
- Docker-based deployment
- Persistent storage in `/share/faceinsight/`
- Health check endpoint
- Responsive web UI

### Configuration Options
- MQTT host, port, credentials, topic
- Session secret for Flask
- Max images per person (1-25)
- Recognition threshold (0.1-0.9)

### Known Limitations
- First run takes 2-3 minutes to download models
- Requires at least 5 images per person for good accuracy
- MQTT broker required for notifications
- ARM support limited to ARMv7 and ARM64

### Dependencies
- Python 3.11
- InsightFace
- OpenCV
- Flask
- SQLite
- Paho MQTT
- Watchdog

---

## Future Releases

### [1.1.0] - Planned
- [ ] Video stream support (RTSP/HTTP)
- [ ] Real-time camera monitoring
- [ ] Advanced filtering and search in history
- [ ] Face grouping and clustering
- [ ] Export/import person database
- [ ] Multi-face detection in single image
- [ ] Face quality scoring
- [ ] Age and gender detection

### [1.2.0] - Planned
- [ ] Integration with Home Assistant camera entities
- [ ] Snapshot automation on recognition
- [ ] Zone-based recognition (different cameras)
- [ ] Advanced MQTT topics (per person)
- [ ] Webhooks support
- [ ] REST API for external integrations
- [ ] Mobile app notifications

### [2.0.0] - Planned
- [ ] GPU acceleration support
- [ ] Multiple model backends (ONNX, TensorRT)
- [ ] Face anti-spoofing
- [ ] Live face recognition dashboard
- [ ] Advanced analytics and reporting
- [ ] Multi-user support with permissions
- [ ] Cloud backup integration
