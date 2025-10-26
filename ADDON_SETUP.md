# FaceInsight Addon Repository Setup

This guide shows how to create a separate addon repository that uses prebuilt images from the main faceinsight repo.

## Structure

- **Main repo**: `https://github.com/anhnvme/faceinsight` - Source code + auto-build images
- **Addon repo**: `https://github.com/anhnvme/faceinsight-addon` - Home Assistant addon metadata

## Create Addon Repository

### 1. Create new repo `faceinsight-addon`

```bash
mkdir faceinsight-addon
cd faceinsight-addon
git init
```

### 2. Create repository.json

```json
{
  "name": "FaceInsight Add-ons",
  "url": "https://github.com/anhnvme/faceinsight-addon",
  "maintainer": "Anh Nguyen"
}
```

### 3. Create addon structure

```
faceinsight-addon/
├── repository.json
└── faceinsight/
    ├── config.json
    ├── icon.png
    ├── logo.png
    ├── README.md
    ├── DOCS.md
    └── CHANGELOG.md
```

### 4. Create config.json (uses prebuilt images)

```json
{
  "name": "FaceInsight",
  "version": "1.0.0",
  "slug": "faceinsight",
  "description": "Face Recognition System with InsightFace",
  "url": "https://github.com/anhnvme/faceinsight",
  "arch": ["amd64", "aarch64"],
  "image": "ghcr.io/anhnvme/faceinsight-{arch}",
  "startup": "application",
  "boot": "auto",
  "init": false,
  "ports": {
    "6080/tcp": null
  },
  "options": {
    "web_port": 6080,
    "mqtt_host": "core-mosquitto",
    "mqtt_port": 1883,
    "mqtt_username": "",
    "mqtt_password": "",
    "mqtt_topic": "faceinsight",
    "recognition_threshold": 0.4,
    "data_path": "/share/faceinsight"
  },
  "schema": {
    "web_port": "port",
    "mqtt_host": "str",
    "mqtt_port": "port",
    "mqtt_username": "str?",
    "mqtt_password": "password?",
    "mqtt_topic": "str",
    "recognition_threshold": "float(0.1,0.9)",
    "data_path": "str"
  },
  "map": ["share:rw"]
}
```

### 5. Copy documentation files

Copy from `homeassistant/` folder:
- README.md
- DOCS.md
- CHANGELOG.md
- icon.png (if you have)
- logo.png (if you have)

## Workflow

1. **Update source code** → Push to `faceinsight` repo
2. **GitHub Actions** → Auto builds images → Push to ghcr.io
3. **Update addon** → Update `version` in `faceinsight-addon/faceinsight/config.json`
4. **Users update** → Home Assistant pulls new image version

## Image versioning

GitHub Action creates tags:
- `ghcr.io/anhnvme/faceinsight-amd64:latest` - Always latest build from master
- `ghcr.io/anhnvme/faceinsight-amd64:v1.0.0` - Tagged releases
- `ghcr.io/anhnvme/faceinsight-amd64:dev` - Development builds

To release version 1.0.0:
```bash
# In faceinsight repo
git tag v1.0.0
git push origin v1.0.0

# GitHub Action builds and pushes images with v1.0.0 tag

# Then update addon repo
cd faceinsight-addon/faceinsight
# Update version in config.json to 1.0.0
git commit -am "Release v1.0.0"
git push
```

## Benefits

✅ Source code repo stays clean (no addon-specific files at root)
✅ Auto-build on every commit (no manual Docker builds)
✅ Addon repo is lightweight (just config + docs)
✅ Users get prebuilt images (fast installation)
✅ Can version independently (source vs addon version)
