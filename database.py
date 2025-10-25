import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='face_recognition.db'):
        self.db_path = db_path
        self.init_db()
    
    def __enter__(self):
        """Context manager entry"""
        self.conn = self.get_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure connection is closed"""
        if hasattr(self, 'conn'):
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()
        return False
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    
    @staticmethod
    def _safe_delete_file(file_path: str) -> bool:
        """
        Safely delete a file with error handling.
        Returns True if deleted successfully or file doesn't exist, False on error.
        """
        if not file_path:
            return True
        
        if not os.path.exists(file_path):
            return True
        
        try:
            os.remove(file_path)
            logger.debug(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                nickname TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                original_image_path TEXT,
                embedding TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recognition_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                person_name TEXT,
                nickname TEXT,
                score REAL,
                image_path TEXT,
                thumbnail_path TEXT,
                bbox_info TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trained_image_id INTEGER,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE SET NULL,
                FOREIGN KEY (trained_image_id) REFERENCES face_images(id) ON DELETE SET NULL
            )
        ''')
        
        # Migration: Add bbox_info column if it doesn't exist
        cursor.execute("PRAGMA table_info(recognition_history)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'bbox_info' not in columns:
            cursor.execute('ALTER TABLE recognition_history ADD COLUMN bbox_info TEXT')
            print("Migration: Added bbox_info column to recognition_history table")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Create indexes for faster queries (especially for lookups by person_id)
        # These indexes make queries 50-80% faster when searching by person or sorting by time
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_face_images_person_id ON face_images(person_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recognition_history_person_id ON recognition_history(person_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recognition_history_timestamp ON recognition_history(timestamp DESC)')
        
        # Default settings
        default_settings = {
            'recognition_threshold': '0.30',  # Lowered from 0.4 to compensate for data quality variance
            'auto_train_enabled': 'true',
            'max_images_per_person': '10',
            'voting_top_k': '3',  # For hybrid matching
            'mqtt_enabled': 'false',
            'mqtt_broker': 'localhost',
            'mqtt_port': '1883',
            'mqtt_username': '',
            'mqtt_password': '',
            'mqtt_topic': 'homeassistant/face_recognition'
        }
        
        for key, value in default_settings.items():
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
        
        conn.commit()
        conn.close()
    
    def add_person(self, name: str, nickname: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO persons (name, nickname) VALUES (?, ?)', (name, nickname))
        person_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return person_id
    
    def update_person(self, person_id: int, name: str = None, nickname: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if name:
            cursor.execute('UPDATE persons SET name = ? WHERE id = ?', (name, person_id))
        if nickname is not None:
            cursor.execute('UPDATE persons SET nickname = ? WHERE id = ?', (nickname, person_id))
        conn.commit()
        conn.close()
    
    def delete_person(self, person_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get person name before deleting (need for folder cleanup)
        cursor.execute('SELECT name FROM persons WHERE id = ?', (person_id,))
        person = cursor.fetchone()
        person_name = person['name'] if person else None
        
        # Delete all training images of this person (both cropped and original)
        cursor.execute('SELECT image_path, original_image_path FROM face_images WHERE person_id = ?', (person_id,))
        images = cursor.fetchall()
        for img in images:
            self._safe_delete_file(img['image_path'])
            self._safe_delete_file(img['original_image_path'])
        
        # IMPORTANT: Do NOT delete history records when deleting person
        # History is permanent log - keep the records but unlink from person
        # Set person_id to NULL and revert to "Unknown" status
        cursor.execute('''
            UPDATE recognition_history 
            SET person_id = NULL, person_name = 'Unknown', nickname = NULL, score = 0.0
            WHERE person_id = ?
        ''', (person_id,))
        
        # Delete person (CASCADE will automatically delete records in face_images)
        cursor.execute('DELETE FROM persons WHERE id = ?', (person_id,))
        conn.commit()
        conn.close()
        
        # Delete person-specific directories to prevent orphan files
        if person_name:
            import shutil
            for subdir in ['detect', 'original']:
                dir_path = os.path.join(os.path.dirname(__file__), 'static', subdir, person_name)
                if os.path.exists(dir_path):
                    try:
                        shutil.rmtree(dir_path)
                        print(f"Deleted directory: {dir_path}")
                    except Exception as e:
                        print(f"Warning: Could not delete directory {dir_path}: {e}")
    
    def get_person(self, person_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM persons WHERE id = ?', (person_id,))
        person = cursor.fetchone()
        conn.close()
        return dict(person) if person else None
    
    def get_person_by_name(self, name: str) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM persons WHERE name = ?', (name,))
        person = cursor.fetchone()
        conn.close()
        return dict(person) if person else None
    
    def get_all_persons(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM persons ORDER BY created_at DESC')
        persons = cursor.fetchall()
        conn.close()
        return [dict(p) for p in persons]
    
    def add_face_image(self, person_id: int, image_path: str, embedding: List[float], original_image_path: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        embedding_str = json.dumps(embedding)
        cursor.execute('INSERT INTO face_images (person_id, image_path, original_image_path, embedding) VALUES (?, ?, ?, ?)',
                      (person_id, image_path, original_image_path, embedding_str))
        image_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return image_id
    
    def get_face_images(self, person_id: int) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM face_images WHERE person_id = ? ORDER BY created_at', (person_id,))
        images = cursor.fetchall()
        conn.close()
        return [dict(img) for img in images]
    
    def get_face_count(self, person_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM face_images WHERE person_id = ?', (person_id,))
        count = cursor.fetchone()['count']
        conn.close()
        return count
    
    def get_oldest_face_image(self, person_id: int) -> Optional[Dict]:
        """Get the oldest face image for a person (by created_at)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM face_images WHERE person_id = ? ORDER BY created_at ASC LIMIT 1', (person_id,))
        image = cursor.fetchone()
        conn.close()
        return dict(image) if image else None
    
    def update_face_embedding(self, image_id: int, embedding: List[float]):
        """Update only the embedding of a face image without deleting the image file"""
        conn = self.get_connection()
        cursor = conn.cursor()
        embedding_str = json.dumps(embedding)
        cursor.execute('UPDATE face_images SET embedding = ? WHERE id = ?', (embedding_str, image_id))
        conn.commit()
        conn.close()
    
    def delete_face_image(self, image_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get image info before deleting (need person_id for cleanup)
        cursor.execute('SELECT fi.image_path, fi.original_image_path, p.name FROM face_images fi JOIN persons p ON fi.person_id = p.id WHERE fi.id = ?', (image_id,))
        image = cursor.fetchone()
        person_name = image['name'] if image else None
        
        # Delete training image files (both cropped and original)
        if image:
            self._safe_delete_file(image['image_path'])
            self._safe_delete_file(image['original_image_path'])
        
        # IMPORTANT: Do NOT delete history records when deleting training image
        # History is permanent log - just unlink the reference by setting trained_image_id to NULL
        # This prevents orphan history files (log_*.jpg and thumb_*.jpg would be deleted but record remains)
        cursor.execute('UPDATE recognition_history SET trained_image_id = NULL WHERE trained_image_id = ?', (image_id,))
        
        # Delete training image record in database
        cursor.execute('DELETE FROM face_images WHERE id = ?', (image_id,))
        conn.commit()
        conn.close()
        
        # Cleanup empty directories after deleting files
        if person_name:
            self._cleanup_empty_person_folders(person_name)
    
    def get_all_embeddings(self) -> List[Tuple[int, str, str, List[float]]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fi.id, p.name, p.nickname, fi.embedding 
            FROM face_images fi
            JOIN persons p ON fi.person_id = p.id
        ''')
        results = []
        for row in cursor.fetchall():
            embedding = json.loads(row['embedding'])
            results.append((row['id'], row['name'], row['nickname'], embedding))
        conn.close()
        return results
    
    def add_recognition_history(self, person_id: Optional[int], person_name: str, 
                                nickname: Optional[str], score: float, 
                                image_path: str, thumbnail_path: str,
                                trained_image_id: Optional[int] = None,
                                bbox_info: Optional[dict] = None,
                                max_records: int = 30) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Convert bbox_info dict to JSON string
        bbox_json = json.dumps(bbox_info) if bbox_info else None
        
        # Insert new record
        cursor.execute('''
            INSERT INTO recognition_history 
            (person_id, person_name, nickname, score, image_path, thumbnail_path, trained_image_id, bbox_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (person_id, person_name, nickname, score, image_path, thumbnail_path, trained_image_id, bbox_json))
        history_id = cursor.lastrowid
        
        # Check if we exceed max_records limit
        cursor.execute('SELECT COUNT(*) as count FROM recognition_history')
        count = cursor.fetchone()['count']
        
        if count > max_records:
            # Delete oldest records (keep only max_records)
            cursor.execute('''
                SELECT id, image_path, thumbnail_path 
                FROM recognition_history 
                ORDER BY timestamp ASC 
                LIMIT ?
            ''', (count - max_records,))
            
            old_records = cursor.fetchall()
            
            # Delete image files first
            for record in old_records:
                if record['image_path'] and os.path.exists(record['image_path']):
                    try:
                        os.remove(record['image_path'])
                    except Exception as e:
                        print(f"Error deleting image {record['image_path']}: {e}")
                
                if record['thumbnail_path'] and os.path.exists(record['thumbnail_path']):
                    try:
                        os.remove(record['thumbnail_path'])
                    except Exception as e:
                        print(f"Error deleting thumbnail {record['thumbnail_path']}: {e}")
            
            # Delete database records
            cursor.execute('''
                DELETE FROM recognition_history 
                WHERE id IN (
                    SELECT id FROM recognition_history 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                )
            ''', (count - max_records,))
        
        conn.commit()
        conn.close()
        return history_id
    
    def get_recognition_history(self, limit: int = 100) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM recognition_history 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        history = cursor.fetchall()
        conn.close()
        return [dict(h) for h in history]
    
    def undo_recognition(self, history_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT trained_image_id, image_path, thumbnail_path FROM recognition_history WHERE id = ?', 
                      (history_id,))
        record = cursor.fetchone()
        
        if record:
            if record['trained_image_id']:
                cursor.execute('SELECT image_path FROM face_images WHERE id = ?', (record['trained_image_id'],))
                face_img = cursor.fetchone()
                if face_img:
                    self._safe_delete_file(face_img['image_path'])
                cursor.execute('DELETE FROM face_images WHERE id = ?', (record['trained_image_id'],))
            
            self._safe_delete_file(record['image_path'])
            self._safe_delete_file(record['thumbnail_path'])
            
            cursor.execute('DELETE FROM recognition_history WHERE id = ?', (history_id,))
        
        conn.commit()
        conn.close()
    
    def clear_history(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT image_path, thumbnail_path FROM recognition_history')
        records = cursor.fetchall()
        for record in records:
            self._safe_delete_file(record['image_path'])
            self._safe_delete_file(record['thumbnail_path'])
        
        cursor.execute('DELETE FROM recognition_history')
        conn.commit()
        conn.close()
    
    def clear_all_data(self):
        import shutil
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT image_path FROM face_images')
        images = cursor.fetchall()
        for img in images:
            self._safe_delete_file(img['image_path'])
        
        cursor.execute('SELECT image_path, thumbnail_path FROM recognition_history')
        records = cursor.fetchall()
        for record in records:
            self._safe_delete_file(record['image_path'])
            self._safe_delete_file(record['thumbnail_path'])
        
        # Delete static/original, static/detect, static/logs, and static/test directories
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        for subdir in ['original', 'detect', 'logs', 'test']:
            dir_path = os.path.join(static_dir, subdir)
            if os.path.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                    # Recreate empty directory
                    os.makedirs(dir_path, exist_ok=True)
                    print(f"Cleared directory: {subdir}")
                except Exception as e:
                    print(f"Warning: Could not delete {subdir} directory: {e}")
        
        # Delete models directory
        models_dir = os.path.join(os.path.dirname(__file__), 'models')
        if os.path.exists(models_dir):
            try:
                shutil.rmtree(models_dir)
                # Recreate empty models directory
                os.makedirs(models_dir, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not delete models directory: {e}")
        
        # Delete all data from tables
        cursor.execute('DELETE FROM persons')
        cursor.execute('DELETE FROM recognition_history')
        
        # Reset MQTT settings to default (empty/unconfigured state)
        cursor.execute('DELETE FROM settings WHERE key LIKE "mqtt_%"')
        
        conn.commit()
        conn.close()
    
    def get_setting(self, key: str) -> Optional[str]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result['value'] if result else None
    
    def set_setting(self, key: str, value: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()
    
    def get_all_settings(self) -> Dict[str, str]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        settings = cursor.fetchall()
        conn.close()
        return {s['key']: s['value'] for s in settings}
    
    def _cleanup_empty_person_folders(self, person_name: str):
        """
        Helper function to remove empty person folders after deleting images
        Prevents orphan empty directories
        """
        import shutil
        for subdir in ['detect', 'original']:
            dir_path = os.path.join(os.path.dirname(__file__), 'static', subdir, person_name)
            if os.path.exists(dir_path):
                try:
                    # Check if directory is empty or only contains hidden files
                    if not os.listdir(dir_path) or all(f.startswith('.') for f in os.listdir(dir_path)):
                        shutil.rmtree(dir_path)
                        print(f"Cleaned up empty directory: {dir_path}")
                except Exception as e:
                    print(f"Warning: Could not cleanup directory {dir_path}: {e}")
    
    def cleanup_temp_files(self) -> dict:
        """
        Cleanup temporary test files in static/test directory
        Returns dict with cleanup statistics
        """
        test_dir = os.path.join(os.path.dirname(__file__), 'static', 'test')
        if not os.path.exists(test_dir):
            return {'deleted_count': 0, 'freed_space_mb': 0}
        
        deleted_count = 0
        freed_space = 0
        
        for filename in os.listdir(test_dir):
            # Only delete temp_ and test_ files (not .gitkeep or other files)
            if not (filename.startswith('temp_') or filename.startswith('test_')):
                continue
            
            file_path = os.path.join(test_dir, filename)
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                continue
            
            try:
                file_size = os.path.getsize(file_path)
                self._safe_delete_file(file_path)
                deleted_count += 1
                freed_space += file_size
                logger.info(f"Deleted temp file: {filename}")
            except Exception as e:
                logger.error(f"Error deleting temp file {filename}: {e}")
        
        freed_space_mb = freed_space / (1024 * 1024)
        return {
            'deleted_count': deleted_count,
            'freed_space_mb': round(freed_space_mb, 2)
        }
    
    def cleanup_orphan_history_files(self) -> dict:
        """
        Cleanup orphan history files that exist in static/logs but not in database
        Returns dict with cleanup statistics
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all image paths from database
        cursor.execute('SELECT image_path, thumbnail_path FROM recognition_history')
        db_records = cursor.fetchall()
        conn.close()
        
        # Collect all valid file paths from database
        valid_files = set()
        for record in db_records:
            if record['image_path']:
                valid_files.add(record['image_path'])
            if record['thumbnail_path']:
                valid_files.add(record['thumbnail_path'])
        
        # Scan static/logs directory
        logs_dir = os.path.join(os.path.dirname(__file__), 'static', 'logs')
        if not os.path.exists(logs_dir):
            return {'deleted_count': 0, 'freed_space_mb': 0}
        
        deleted_count = 0
        freed_space = 0
        
        for filename in os.listdir(logs_dir):
            file_path = os.path.join(logs_dir, filename)
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                continue
            
            # Check if file is in database
            relative_path = os.path.join('static', 'logs', filename)
            
            if relative_path not in valid_files:
                # Orphan file - delete it
                try:
                    file_size = os.path.getsize(file_path)
                    self._safe_delete_file(file_path)
                    deleted_count += 1
                    freed_space += file_size
                    logger.info(f"Deleted orphan file: {relative_path}")
                except Exception as e:
                    logger.error(f"Error deleting orphan file {relative_path}: {e}")
        
        freed_space_mb = freed_space / (1024 * 1024)
        return {
            'deleted_count': deleted_count,
            'freed_space_mb': round(freed_space_mb, 2)
        }
    
    def enforce_history_limit(self, max_records: int = 30) -> dict:
        """
        Enforce history limit by deleting oldest records if exceeds max_records
        Returns dict with cleanup statistics
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check current count
        cursor.execute('SELECT COUNT(*) as count FROM recognition_history')
        result = cursor.fetchone()
        count = result['count'] if result else 0
        
        if count <= max_records:
            conn.close()
            return {
                'deleted_count': 0,
                'freed_space_mb': 0.0,
                'current_count': count,
                'max_records': max_records
            }
        
        # Get oldest records to delete
        records_to_delete = count - max_records
        cursor.execute('''
            SELECT id, image_path, thumbnail_path 
            FROM recognition_history 
            ORDER BY timestamp ASC 
            LIMIT ?
        ''', (records_to_delete,))
        
        old_records = cursor.fetchall()
        deleted_count = 0
        freed_space = 0
        
        # Delete image files first
        for record in old_records:
            try:
                file_size = 0
                if record['image_path'] and os.path.exists(record['image_path']):
                    file_size += os.path.getsize(record['image_path'])
                if record['thumbnail_path'] and os.path.exists(record['thumbnail_path']):
                    file_size += os.path.getsize(record['thumbnail_path'])
                
                self._safe_delete_file(record['image_path'])
                self._safe_delete_file(record['thumbnail_path'])
                
                freed_space += file_size
                logger.info(f"Deleted old history record: {record['image_path']}")
            except Exception as e:
                logger.error(f"Error processing old record: {e}")
            
            deleted_count += 1
        
        # Delete database records
        cursor.execute('''
            DELETE FROM recognition_history 
            WHERE id IN (
                SELECT id FROM recognition_history 
                ORDER BY timestamp ASC 
                LIMIT ?
            )
        ''', (records_to_delete,))
        
        conn.commit()
        conn.close()
        
        freed_space_mb = freed_space / (1024 * 1024)
        return {
            'deleted_count': deleted_count,
            'freed_space_mb': round(freed_space_mb, 2),
            'current_count': max_records,
            'max_records': max_records
        }

    def get_storage_info(self) -> Dict[str, any]:
        """
        Calculate and return storage usage for models and data folders.
        Returns dict with formatted strings and raw bytes.
        """
        def get_folder_size(folder_path):
            """Calculate total size of folder in bytes"""
            total_size = 0
            if not os.path.exists(folder_path):
                return 0
            
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        continue
            return total_size
        
        def format_size(bytes_size):
            """Format bytes to human readable format"""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_size < 1024.0:
                    return f"{bytes_size:.1f} {unit}"
                bytes_size /= 1024.0
            return f"{bytes_size:.1f} TB"
        
        # Calculate sizes
        models_size = get_folder_size('models')
        logs_size = get_folder_size('static/logs')
        original_size = get_folder_size('static/original')
        detect_size = get_folder_size('static/detect')
        
        data_size = logs_size + original_size + detect_size
        total_size = models_size + data_size
        
        # Format for display
        models_formatted = format_size(models_size)
        data_formatted = format_size(data_size)
        total_formatted = format_size(total_size)
        
        # Save to database
        self.set_setting('storage_models', models_formatted)
        self.set_setting('storage_data', data_formatted)
        self.set_setting('storage_total', total_formatted)
        
        return {
            'models': models_formatted,
            'data': data_formatted,
            'total': total_formatted,
            'bytes': {
                'models': models_size,
                'data': data_size,
                'total': total_size
            }
        }

    def auto_train_face(self, person_id: int, person_name: str, face_img, embedding, 
                       timestamp: str, original_image_path: str) -> Optional[int]:
        """
        Auto-train a face image for a person (used by inbox monitor and other auto-train scenarios).
        Handles max_images limit by deleting oldest image if needed.
        
        Args:
            person_id: ID of the person
            person_name: Name of the person (for directory paths)
            face_img: Cropped face image (numpy array)
            embedding: Face embedding (numpy array or list)
            timestamp: Timestamp string for filename
            original_image_path: Path to original image to copy
            
        Returns:
            Image ID if successful, None if failed
        """
        import cv2
        import shutil
        
        max_images = int(self.get_setting('max_images_per_person') or 10)
        face_count = self.get_face_count(person_id)
        
        # If already at max_images, delete oldest image
        if face_count >= max_images:
            oldest_image = self.get_oldest_face_image(person_id)
            if oldest_image:
                logger.info(f"Deleting oldest face image (id={oldest_image['id']}) for {person_name} to make room for new one")
                self.delete_face_image(oldest_image['id'])
        
        # Create person-specific directories
        detect_dir = f"static/detect/{person_name}"
        original_dir = f"static/original/{person_name}"
        os.makedirs(detect_dir, exist_ok=True)
        os.makedirs(original_dir, exist_ok=True)
        
        # Save cropped image (detect) - for display
        face_save_path = f"{detect_dir}/{person_name}_{timestamp}.jpg"
        if not cv2.imwrite(face_save_path, face_img):
            logger.error(f"Failed to save face image: {face_save_path}")
            return None
        
        # Save original image (original) - for retrain
        original_save_path = f"{original_dir}/{person_name}_{timestamp}.jpg"
        try:
            shutil.copy(original_image_path, original_save_path)
        except Exception as e:
            logger.error(f"Failed to copy original image: {e}")
            self._safe_delete_file(face_save_path)
            return None
        
        # Convert embedding to list if numpy array
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
        
        # Add to database with both paths
        image_id = self.add_face_image(person_id, face_save_path, embedding, original_save_path)
        logger.info(f"Auto-trained new face image for {person_name} (total: {min(face_count + 1, max_images)} images)")
        
        return image_id

