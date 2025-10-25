# Data Persistence Architecture

## How FaceInsight Protects Your Data

### The Problem

When a Docker container is updated or rebuilt, everything inside it is lost. This would normally mean:
- ❌ Losing trained face embeddings
- ❌ Losing recognition history
- ❌ Having to re-upload all images
- ❌ Re-downloading models (~1GB)

### The Solution: Symlinks + External Storage

FaceInsight stores **all data outside the container** and uses **symlinks** to connect them.

```
┌─────────────────────────────────────────────────────┐
│  FaceInsight Addon Container (Temporary)            │
│  ┌──────────────────────────────────────────────┐   │
│  │  /app/                                       │   │
│  │  ├── app.py          ← Code (updated)       │   │
│  │  ├── database.py     ← Code (updated)       │   │
│  │  │                                           │   │
│  │  ├── faceinsight.db  ─────────┐ (symlink)   │   │
│  │  ├── inbox/          ─────────┤             │   │
│  │  ├── models/         ─────────┤             │   │
│  │  └── static/         ─────────┤             │   │
│  │      ├── detect/     ─────────┤             │   │
│  │      ├── original/   ─────────┤             │   │
│  │      ├── logs/       ─────────┤             │   │
│  │      └── test/       ─────────┘             │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────┘
                           │ Symlinks point to
                           ▼
┌─────────────────────────────────────────────────────┐
│  Host Filesystem (Persistent - Never Deleted)       │
│  ┌──────────────────────────────────────────────┐   │
│  │  /share/faceinsight/                         │   │
│  │  ├── faceinsight.db      ✓ Persisted        │   │
│  │  ├── inbox/              ✓ Persisted        │   │
│  │  ├── models/             ✓ Persisted        │   │
│  │  │   └── buffalo_s/      (~300 MB)          │   │
│  │  └── static/             ✓ Persisted        │   │
│  │      ├── detect/         (cropped faces)    │   │
│  │      ├── original/       (original images)  │   │
│  │      ├── logs/           (history)          │   │
│  │      └── test/           (test uploads)     │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Update Process

**Before Update:**
```
Container v1.0.0               /share/faceinsight/
├── app.py (old code)          ├── faceinsight.db
├── faceinsight.db ────────►   ├── models/
├── models/ ───────────────►   └── static/
└── static/ ───────────────►       ├── detect/
                                   ├── original/
                                   └── logs/
```

**During Update:**
```
🔄 Container is rebuilt
   - Old code deleted
   - New code downloaded
   - Symlinks recreated
   
✅ /share/faceinsight/ untouched!
```

**After Update:**
```
Container v1.1.0               /share/faceinsight/
├── app.py (NEW code)          ├── faceinsight.db (SAME)
├── faceinsight.db ────────►   ├── models/ (SAME)
├── models/ ───────────────►   └── static/ (SAME)
└── static/ ───────────────►       ├── detect/
                                   ├── original/
                                   └── logs/
```

### What Happens on Update

1. **GitHub** receives new code push
2. **HA Supervisor** detects update available
3. **User** clicks "Update" button
4. **HA Supervisor** downloads new code
5. **Docker** rebuilds container with new code
6. **run.sh** executes:
   ```bash
   # Recreate symlinks
   ln -sf /share/faceinsight/faceinsight.db /app/faceinsight.db
   ln -sf /share/faceinsight/static/detect /app/static/detect
   ln -sf /share/faceinsight/models /app/models
   # ... etc
   ```
7. **Application** starts with new code + old data
8. ✅ **Everything works** - no data lost!

### Custom Paths

If you use custom paths:

```yaml
use_custom_paths: true
data_path: /home/faceinsight/img
inbox_path: /home/homeassistant/www/snapshots_2
models_path: /home/faceinsight/models
```

Symlinks point to your specified locations:

```
Container                      Custom Locations
/app/faceinsight.db ────────► /home/faceinsight/img/faceinsight.db
/app/static/detect/ ────────► /home/faceinsight/img/static/detect/
/app/inbox/ ────────────────► /home/homeassistant/www/snapshots_2/
/app/models/ ───────────────► /home/faceinsight/models/
```

### Benefits

✅ **Safe Updates** - Update anytime without fear  
✅ **Zero Downtime** - Data always available  
✅ **Rollback Safe** - Can downgrade to older version  
✅ **Backup Simple** - Just backup `/share/faceinsight/`  
✅ **Migration Easy** - Copy folder to new HA instance  

### Verification

To verify symlinks after addon starts:

```bash
# SSH into HA, then access addon container
docker exec -it addon_xxxxx_faceinsight ls -la /app/

# You should see:
lrwxrwxrwx  1 root root   inbox -> /share/faceinsight/inbox
lrwxrwxrwx  1 root root   models -> /share/faceinsight/models
lrwxrwxrwx  1 root root   faceinsight.db -> /share/faceinsight/faceinsight.db
```

### Summary

| Item | Stored Where | Updated? | Persists? |
|------|-------------|----------|-----------|
| Python code | Inside container | ✅ Yes | ❌ No |
| Templates/CSS | Inside container | ✅ Yes | ❌ No |
| Database | `/share/faceinsight/` | ❌ No | ✅ Yes |
| Face images | `/share/faceinsight/static/` | ❌ No | ✅ Yes |
| Models | `/share/faceinsight/models/` | ❌ No | ✅ Yes |
| Inbox | `/share/faceinsight/inbox/` | ❌ No | ✅ Yes |

**Result:** Update code freely, data is always safe! 🔒
