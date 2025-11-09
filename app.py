import os
import cv2
import logging
import shutil
import re
import unicodedata
import time
from contextlib import contextmanager
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import threading

from database import Database
from face_processor import FaceProcessor
from mqtt_client import MQTTClient
from inbox_monitor import InboxMonitor

# Configure logging to console only (no file output)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==================== Utility Functions ====================

@contextmanager
def temp_file_cleanup(*file_paths):
    """
    Context manager for automatic temp file cleanup.
    Ensures temp files are deleted even if exception occurs.
    
    Usage:
        with temp_file_cleanup(temp_path):
            # Your code here
            # temp_path will be auto-deleted on exit
    """
    try:
        yield
    finally:
        for temp_path in file_paths:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"Deleted temp file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Could not delete temp file {temp_path}: {e}")

# Global state for retrain progress
retrain_progress = {
    'is_running': False,
    'current': 0,
    'total': 0,
    'current_person': '',
    'status': 'idle'
}

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

db = Database()

# Read model from settings instead of hard-coding buffalo_s
saved_model = db.get_setting('current_model') or 'buffalo_s'
logger.info(f"Initializing FaceProcessor with model: {saved_model}")
face_processor = FaceProcessor(model_name=saved_model)

mqtt_client = MQTTClient()
inbox_monitor = None

def slugify_name(text: str) -> str:
    """
    Convert Vietnamese/Unicode text to ASCII slug (a-z and numbers allowed)
    Examples: 
        'Việt Anh' -> 'vietanh'
        'Nguyễn Văn A' -> 'nguyenvana'
        'Việt Anh 2' -> 'vietanh2'
    """
    # Normalize unicode to decomposed form (NFD)
    text = unicodedata.normalize('NFD', text)
    # Remove diacritics/accents
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    # Convert to lowercase
    text = text.lower()
    # Remove all non a-z0-9 characters
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def init_mqtt():
    settings = db.get_all_settings()
    mqtt_host = settings.get('mqtt_host', 'localhost')
    
    if mqtt_host and mqtt_host != 'localhost':
        mqtt_client.configure(
            host=mqtt_host,
            port=int(settings.get('mqtt_port', 1883)),
            username=settings.get('mqtt_username'),
            password=settings.get('mqtt_password'),
            topic=settings.get('mqtt_topic', 'homeassistant/face_detection')
        )
        mqtt_client.connect()

def clear_inbox_folder():
    """Clear all files in inbox folder on startup"""
    inbox_path = './inbox'
    try:
        if os.path.exists(inbox_path):
            file_count = 0
            for filename in os.listdir(inbox_path):
                file_path = os.path.join(inbox_path, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        file_count += 1
                        logger.info(f"Deleted inbox file: {filename}")
                except Exception as e:
                    logger.error(f"Error deleting {filename}: {e}")
            
            if file_count > 0:
                logger.info(f"Cleared {file_count} file(s) from inbox folder on startup")
            else:
                logger.info("Inbox folder is already empty")
        else:
            os.makedirs(inbox_path, exist_ok=True)
            logger.info("Created inbox folder")
    except Exception as e:
        logger.error(f"Error clearing inbox folder: {e}")

def init_inbox_monitor():
    global inbox_monitor
    # Clear inbox folder before starting monitor
    clear_inbox_folder()
    
    # Cleanup temp files in static/test on startup
    logger.info("Cleaning up temp files in static/test...")
    temp_result = db.cleanup_temp_files()
    if temp_result['deleted_count'] > 0:
        logger.info(f"Deleted {temp_result['deleted_count']} temp files, "
                   f"freed {temp_result['freed_space_mb']} MB")
    else:
        logger.info("No temp files to clean")
    
    # Enforce history limit (keep only latest 30 records)
    logger.info("Enforcing history limit (max 30 records)...")
    limit_result = db.enforce_history_limit(max_records=30)
    if limit_result['deleted_count'] > 0:
        logger.info(f"Deleted {limit_result['deleted_count']} old history records, "
                   f"freed {limit_result['freed_space_mb']} MB")
    else:
        logger.info(f"History within limit ({limit_result['current_count']}/{limit_result['max_records']} records)")
    
    # Cleanup orphan history files (files in static/logs not in database)
    logger.info("Cleaning up orphan history files...")
    cleanup_result = db.cleanup_orphan_history_files()
    if cleanup_result['deleted_count'] > 0:
        logger.info(f"Deleted {cleanup_result['deleted_count']} orphan files, "
                   f"freed {cleanup_result['freed_space_mb']} MB")
    else:
        logger.info("No orphan files found")
    
    # Get inbox path from environment or use default
    inbox_path = os.environ.get('INBOX_PATH', './inbox')
    if not inbox_path or inbox_path == 'null' or inbox_path == '':
        inbox_path = './inbox'
    
    logger.info(f"Initializing inbox monitor with path: {inbox_path}")
    inbox_monitor = InboxMonitor(face_processor, db, mqtt_client, inbox_path)
    inbox_monitor.start()

def save_face_image(person_id: int, person_name: str, temp_path: str, face_img, embedding) -> int:
    """Helper function to save both cropped and original images, returns image_id"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filename = secure_filename(f"{person_name}_{timestamp}.jpg")
    
    # Create person-specific directories
    detect_dir = f"static/detect/{person_name}"
    original_dir = f"static/original/{person_name}"
    os.makedirs(detect_dir, exist_ok=True)
    os.makedirs(original_dir, exist_ok=True)
    
    # Save cropped image (detect) - for display
    face_path = f"{detect_dir}/{filename}"
    if not cv2.imwrite(face_path, face_img):
        logger.error(f"Failed to save cropped image: {face_path}")
        return None
    
    # Save original image - using shutil.copy (faster than cv2.imwrite(cv2.imread()))
    original_path = f"{original_dir}/{filename}"
    try:
        shutil.copy(temp_path, original_path)
    except Exception as e:
        logger.error(f"Failed to save original image: {e}")
        if os.path.exists(face_path):
            os.remove(face_path)
        return None
    
    # Save to database with both paths
    image_id = db.add_face_image(person_id, face_path, embedding.tolist(), original_path)
    return image_id

@app.route('/')
def index():
    persons = db.get_all_persons()
    for person in persons:
        person['images'] = db.get_face_images(person['id'])
        person['image_count'] = len(person['images'])
        person['embed_count'] = db.get_face_count(person['id'])
    
    # Get current model info
    current_model = db.get_setting('current_model') or 'buffalo_s'
    
    # Check MQTT configuration
    settings = db.get_all_settings()
    mqtt_host = settings.get('mqtt_host', 'localhost')
    mqtt_configured = mqtt_host and mqtt_host != 'localhost'
    
    # Get storage info from database
    storage_models = db.get_setting('storage_models') or '0 MB'
    storage_data = db.get_setting('storage_data') or '0 MB'
    storage_total = db.get_setting('storage_total') or '0 MB'
    
    # Get max images per person setting
    max_images = int(db.get_setting('max_images_per_person') or 10)
    
    return render_template('index.html', persons=persons, current_model=current_model, 
                         mqtt_configured=mqtt_configured, mqtt_host=mqtt_host,
                         storage_models=storage_models, storage_data=storage_data,
                         storage_total=storage_total, max_images=max_images)

@app.route('/person/add', methods=['POST'])
def add_person():
    temp_files = []  # Track temp files for cleanup
    try:
        name = request.form.get('name')  # User can edit this
        nickname = request.form.get('nickname')
        
        if not name:
            return jsonify({'error': 'Tên là bắt buộc'}), 400
        
        if not nickname:
            return jsonify({'error': 'Nickname là bắt buộc'}), 400
        
        # Ensure name is slugified (a-z only)
        name_slug = slugify_name(name).strip().lower()
        
        if not name_slug:
            return jsonify({'error': 'Tên phải chứa ít nhất 1 ký tự chữ cái'}), 400
        
        # Check for duplicates and auto-increment if exists
        original_name = name_slug
        counter = 2
        while db.get_person_by_name(name_slug):
            name_slug = f"{original_name}{counter}"
            counter += 1
            if counter > 100:  # Safety limit
                return jsonify({'error': 'Không thể tạo tên unique (quá nhiều trùng lặp)'}), 400
        
        # Use unique slugified name for storage, nickname for display
        person_id = db.add_person(name_slug, nickname)
        
        files = request.files.getlist('images')
        for file in files[:10]:
            if file and file.filename:
                # Save temp in test folder (directory created by run.sh or Dockerfile)
                temp_path = f"static/test/temp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                temp_files.append(temp_path)
                file.save(temp_path)
                
                with temp_file_cleanup(temp_path):
                    # Extract face (baseline - no optimizations needed)
                    result = face_processor.detect_and_align_face(temp_path)
                    if result:
                        face_img, embedding, age, gender, bbox_info = result
                        save_face_image(person_id, name_slug, temp_path, face_img, embedding)
        
        return jsonify({'success': True, 'person_id': person_id, 'name_slug': name_slug})
    except Exception as e:
        logger.error(f"Error adding person: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/person/<int:person_id>/edit', methods=['POST'])
def edit_person(person_id):
    try:
        name = request.form.get('name')
        nickname = request.form.get('nickname')
        
        # Only update nickname, name cannot be changed after creation
        # (changing name would require renaming folders and updating all paths)
        db.update_person(person_id, None, nickname)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error editing person: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/person/<int:person_id>/delete', methods=['POST'])
def delete_person(person_id):
    try:
        db.delete_person(person_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting person: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/person/<int:person_id>/add_image', methods=['POST'])
def add_person_image(person_id):
    temp_path = None
    try:
        person = db.get_person(person_id)
        if not person:
            return jsonify({'error': 'Người không tồn tại'}), 404
        
        # Get max_images from settings instead of hardcoded 10
        max_images = int(db.get_setting('max_images_per_person') or 10)
        current_count = db.get_face_count(person_id)
        
        if current_count >= max_images:
            return jsonify({'error': f'Đã đạt tối đa {max_images} ảnh'}), 400
        
        file = request.files.get('image')
        if not file:
            return jsonify({'error': 'Không có file'}), 400
        
        # Save temp in test folder (directory created by run.sh or Dockerfile)
        temp_path = f"static/test/temp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        file.save(temp_path)
        
        with temp_file_cleanup(temp_path):
            result = face_processor.detect_and_align_face(temp_path)
            if result:
                face_img, embedding, age, gender, bbox_info = result
                image_id = save_face_image(person_id, person['name'], temp_path, face_img, embedding)
                if image_id:
                    return jsonify({'success': True, 'image_id': image_id})
                else:
                    return jsonify({'error': 'Lỗi lưu ảnh'}), 500
            else:
                return jsonify({'error': 'Không phát hiện khuôn mặt'}), 400
    except Exception as e:
        logger.error(f"Error adding image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/person/<int:person_id>/delete_image/<int:image_id>', methods=['POST'])
def delete_person_image(person_id, image_id):
    try:
        db.delete_face_image(image_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test_page():
    return render_template('test.html')

@app.route('/test/recognize', methods=['POST'])
def test_recognize():
    start_time = time.time()
    temp_path = None
    
    try:
        file = request.files.get('image')
        if not file:
            return jsonify({'error': 'Không có file'}), 400
        
        # Save to test folder (directory created by run.sh or Dockerfile)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        temp_path = f"static/test/test_{timestamp}.jpg"
        file.save(temp_path)
        
        with temp_file_cleanup(temp_path):
            if not face_processor.validate_image(temp_path):
                return jsonify({'error': 'File ảnh không hợp lệ'}), 400
            
            detect_start = time.time()
            result = face_processor.detect_and_align_face(temp_path)
            detect_time = (time.time() - detect_start) * 1000  # Convert to ms
            
            if not result:
                return jsonify({'error': 'Không phát hiện khuôn mặt'}), 400
            
            _, embedding, age, gender, bbox_info = result
            
            database_embeddings = db.get_all_embeddings()
            threshold = float(db.get_setting('recognition_threshold') or 0.4)
            top_k = int(db.get_setting('voting_top_k') or 3)
            
            match_start = time.time()
            match = face_processor.find_match(embedding, database_embeddings, threshold, top_k)
            match_time = (time.time() - match_start) * 1000  # Convert to ms
            
            # Gender text
            gender_text = 'Nam' if gender == 1 else 'Nữ' if gender == 0 else 'Không xác định'
            
            # Convert image to base64 for inline display (avoid keeping file on server)
            with open(temp_path, 'rb') as f:
                import base64
                image_data = base64.b64encode(f.read()).decode('utf-8')
                image_url = f"data:image/jpeg;base64,{image_data}"
            
            total_time = (time.time() - start_time) * 1000  # Convert to ms
            
            response_data = {
                'success': True,
                'age': age,
                'gender': gender_text,
                'bbox': bbox_info,
                'image_url': image_url,
                'processing_time': {
                    'detect': round(detect_time, 1),
                    'match': round(match_time, 1),
                    'total': round(total_time, 1)
                }
            }
            
            if match:
                _, name, nickname, score = match
                response_data.update({
                    'matched': True,
                    'name': name,
                    'nickname': nickname,
                    'score': round(score * 100)  # Convert to 1-100 scale
                })
            else:
                response_data.update({
                    'matched': False,
                    'message': ''
                })
            
            return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error testing recognition: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def history():
    history_records = db.get_recognition_history(30)
    persons = db.get_all_persons()
    return render_template('history.html', history=history_records, persons=persons)

@app.route('/history/<int:history_id>/undo', methods=['POST'])
def undo_history(history_id):
    try:
        db.undo_recognition(history_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/history/<int:history_id>/add_to_person', methods=['POST'])
def add_history_to_person(history_id):
    try:
        data = request.json
        person_id = data.get('person_id')
        new_person_name = data.get('new_person_name')
        new_person_nickname = data.get('new_person_nickname')
        
        # Get history record
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT image_path FROM recognition_history WHERE id = ?', (history_id,))
        record = cursor.fetchone()
        conn.close()
        
        if not record or not record['image_path']:
            return jsonify({'success': False, 'error': 'Không tìm thấy ảnh'}), 404
        
        image_path = record['image_path']
        
        # Resolve absolute path
        if not os.path.isabs(image_path):
            history_image_path = os.path.join(app.root_path, 'static', image_path.replace('static/', ''))
        else:
            history_image_path = image_path
        
        # IMPORTANT: Check if file exists before processing
        if not os.path.exists(history_image_path):
            return jsonify({'success': False, 'error': 'File ảnh không tồn tại (đã bị xóa)'}), 404
        
        # Check image size first
        img = cv2.imread(history_image_path)
        if img is None:
            return jsonify({'success': False, 'error': 'Không thể đọc được ảnh'}), 400
        
        height, width = img.shape[:2]
        if width < 200 or height < 200:
            return jsonify({
                'success': False, 
                'error': f'Ảnh quá nhỏ ({width}x{height}px). Cần ít nhất 200x200px để đảm bảo chất lượng nhận diện.'
            }), 400
        
        # Create new person if needed
        if not person_id and new_person_name:
            person_id = db.add_person(new_person_name, new_person_nickname)
            logger.info(f"Created new person: {new_person_name} (ID: {person_id})")
        
        if not person_id:
            return jsonify({'success': False, 'error': 'Thiếu thông tin người'}), 400
        
        # Extract face and embedding from history image
        result = face_processor.detect_and_align_face(history_image_path)
        if not result:
            return jsonify({'success': False, 'error': 'Không phát hiện khuôn mặt trong ảnh'}), 400
        
        face_img, embedding, _, _, _ = result
        
        # Get person info
        person = db.get_person(person_id)
        if not person:
            return jsonify({'success': False, 'error': 'Không tìm thấy người'}), 404
        
        name = person['name']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        
        # Create directories
        detect_dir = f"static/detect/{name}"
        original_dir = f"static/original/{name}"
        os.makedirs(detect_dir, exist_ok=True)
        os.makedirs(original_dir, exist_ok=True)
        
        # Save cropped face
        face_save_path = f"{detect_dir}/{name}_{timestamp}.jpg"
        cv2.imwrite(face_save_path, face_img)
        
        # Copy original image
        original_save_path = f"{original_dir}/{name}_{timestamp}.jpg"
        import shutil
        shutil.copy(image_path, original_save_path)
        
        # Add to database
        image_id = db.add_face_image(person_id, face_save_path, embedding.tolist(), original_save_path)
        
        # Calculate similarity score between this image and the person's existing embeddings
        # This gives a more accurate score than the original 0% from Unknown detection
        database_embeddings = db.get_all_embeddings()
        person_embeddings = [(img_id, name, nick, emb) for img_id, name, nick, emb in database_embeddings if name == person['name']]
        
        # Calculate average similarity score with this person's embeddings
        if person_embeddings:
            import numpy as np
            from face_processor import FaceProcessor
            
            similarities = []
            for img_id, _, _, person_emb in person_embeddings:
                # Calculate cosine similarity
                emb1 = np.array(embedding)
                emb2 = np.array(person_emb)
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                similarities.append(similarity)
            
            # Use average similarity as score
            avg_score = float(np.mean(similarities))
            logger.info(f"Calculated similarity score: {avg_score:.3f} (avg of {len(similarities)} embeddings)")
        else:
            # No existing embeddings, use 1.0 (perfect match since we're adding it)
            avg_score = 1.0
            logger.info("No existing embeddings, using score 1.0")
        
        # Update history record to link to person AND update score
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE recognition_history 
            SET person_id = ?, person_name = ?, nickname = ?, score = ?
            WHERE id = ?
        ''', (person_id, person['name'], person['nickname'], avg_score, history_id))
        conn.commit()
        conn.close()
        
        logger.info(f"Added history image to person {name} (ID: {person_id}), updated score to {avg_score:.3f}")
        return jsonify({'success': True, 'person_id': person_id, 'person_name': name})
        
    except Exception as e:
        logger.error(f"Error adding history to person: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/storage', methods=['GET'])
def get_storage():
    """Calculate and return storage usage for models and data folders"""
    try:
        storage_info = db.get_storage_info()
        return jsonify({
            'success': True,
            **storage_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/settings')
def settings():
    settings_data = db.get_all_settings()
    models = face_processor.get_available_models()
    return render_template('settings.html', settings=settings_data, models=models)

@app.route('/settings/save', methods=['POST'])
def save_settings():
    try:
        data = request.json
        
        for key, value in data.items():
            db.set_setting(key, str(value))
        
        init_mqtt()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings/change_model', methods=['POST'])
def change_model():
    try:
        model_name = request.json.get('model_name')
        if not model_name:
            return jsonify({'error': 'Model name required'}), 400
        
        face_processor.load_model(model_name)
        db.set_setting('current_model', model_name)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error changing model: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/retrain-progress', methods=['GET'])
def get_retrain_progress():
    """Get current retrain progress"""
    return jsonify(retrain_progress)

@app.route('/settings/retrain', methods=['POST'])
def retrain_all():
    global retrain_progress
    
    # Prevent multiple concurrent retrains
    if retrain_progress['is_running']:
        return jsonify({'success': False, 'error': 'Retrain already in progress'})
    
    try:
        # Initialize progress
        retrain_progress['is_running'] = True
        retrain_progress['current'] = 0
        retrain_progress['status'] = 'counting'
        
        persons = db.get_all_persons()
        retrained_count = 0
        skipped_count = 0
        
        # Count total images first
        total_images = 0
        for person in persons:
            images = db.get_face_images(person['id'])
            total_images += len(images)
        
        retrain_progress['total'] = total_images
        retrain_progress['status'] = 'training'
        
        for person in persons:
            retrain_progress['current_person'] = person.get('nickname') or person['name']
            images = db.get_face_images(person['id'])
            
            for img in images:
                # Update progress
                retrain_progress['current'] = retrained_count + skipped_count + 1
                
                # Prioritize original image if available, fallback to cropped image
                original_path = img.get('original_image_path')
                use_original = original_path and os.path.exists(original_path)
                image_path = original_path if use_original else img['image_path']
                
                if not os.path.exists(image_path):
                    skipped_count += 1
                    continue
                
                # Extract embedding: original needs detection, cropped is already aligned
                embedding = face_processor.extract_embedding(image_path, is_aligned=not use_original)
                
                if embedding is not None:
                    db.update_face_embedding(img['id'], embedding.tolist())
                    retrained_count += 1
                else:
                    logger.warning(f"Could not extract embedding from {image_path}")
                    skipped_count += 1
        
        # Reset progress
        retrain_progress['is_running'] = False
        retrain_progress['status'] = 'completed'
        
        return jsonify({'success': True, 'retrained_count': retrained_count, 'skipped_count': skipped_count})
    except Exception as e:
        logger.error(f"Error retraining: {e}")
        retrain_progress['is_running'] = False
        retrain_progress['status'] = 'error'
        return jsonify({'success': False, 'error': str(e)})

@app.route('/settings/test_mqtt', methods=['POST'])
def test_mqtt():
    try:
        data = request.json
        test_client = MQTTClient()
        test_client.configure(
            host=data.get('mqtt_host'),
            port=int(data.get('mqtt_port', 1883)),
            username=data.get('mqtt_username'),
            password=data.get('mqtt_password'),
            topic=data.get('mqtt_topic', 'homeassistant/face_detection')
        )
        
        if test_client.connect():
            test_client.publish_detection('test', 'Test Connection', 100, 25, 'Nam')
            test_client.disconnect()
            return jsonify({'success': True, 'message': 'Kết nối MQTT thành công!'})
        else:
            return jsonify({'success': False, 'error': 'Không thể kết nối MQTT'}), 400
    except Exception as e:
        logger.error(f"Error testing MQTT: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/settings/clear_history', methods=['POST'])
def clear_history():
    try:
        db.clear_history()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings/clear_all', methods=['POST'])
def clear_all_data():
    try:
        db.clear_all_data()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error clearing all data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings/toggle_auto_train', methods=['POST'])
def toggle_auto_train():
    try:
        data = request.json
        enabled = data.get('enabled', True)
        db.set_setting('auto_train_enabled', 'true' if enabled else 'false')
        return jsonify({'success': True, 'enabled': enabled})
    except Exception as e:
        logger.error(f"Error toggling auto-train: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings/max_images', methods=['POST'])
def set_max_images():
    try:
        data = request.json
        new_max = int(data.get('max_images', 10))
        
        # Validate: allow 1-100 images
        if new_max < 1 or new_max > 100:
            return jsonify({'error': 'Số ảnh phải từ 1 đến 100'}), 400
        
        # Get current max_images setting
        old_max = int(db.get_setting('max_images_per_person') or 10)
        
        # Update setting first
        db.set_setting('max_images_per_person', str(new_max))
        
        # If reducing limit, delete oldest images for all persons
        total_deleted = 0
        if new_max < old_max:
            persons = db.get_all_persons()
            for person in persons:
                face_count = db.get_face_count(person['id'])
                
                # If person has more images than new limit
                if face_count > new_max:
                    # Get all images sorted by created_at (oldest first)
                    images = db.get_face_images(person['id'])
                    images_to_delete = face_count - new_max
                    
                    # Delete oldest images
                    for i in range(images_to_delete):
                        if i < len(images):
                            db.delete_face_image(images[i]['id'])
                            total_deleted += 1
                            logger.info(f"Deleted oldest image for {person['name']} (id={images[i]['id']})")
        
        return jsonify({
            'success': True, 
            'max_images': new_max,
            'deleted_count': total_deleted,
            'old_max': old_max
        })
    except Exception as e:
        logger.error(f"Error setting max images: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings/voting_top_k', methods=['POST'])
def set_voting_top_k():
    try:
        data = request.json
        top_k = int(data.get('voting_top_k', 3))
        
        # Validate: only allow 2, 3, or 5
        if top_k not in [2, 3, 5]:
            return jsonify({'error': 'Chỉ cho phép 2, 3, hoặc 5 ảnh'}), 400
        
        # Update setting
        db.set_setting('voting_top_k', str(top_k))
        
        return jsonify({'success': True, 'voting_top_k': top_k})
    except Exception as e:
        logger.error(f"Error setting voting_top_k: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings/cleanup_orphan_files', methods=['POST'])
def cleanup_orphan_files():
    try:
        # First enforce history limit
        limit_result = db.enforce_history_limit(max_records=30)
        
        # Then cleanup orphan history files
        orphan_result = db.cleanup_orphan_history_files()
        
        # Cleanup temp files in static/test
        temp_result = db.cleanup_temp_files()
        
        total_deleted = limit_result['deleted_count'] + orphan_result['deleted_count'] + temp_result['deleted_count']
        total_freed = limit_result['freed_space_mb'] + orphan_result['freed_space_mb'] + temp_result['freed_space_mb']
        
        return jsonify({
            'success': True,
            'data': {
                'deleted_count': total_deleted,
                'freed_space_mb': round(total_freed, 2),
                'history_cleaned': limit_result['deleted_count'],
                'orphans_cleaned': orphan_result['deleted_count'],
                'temp_cleaned': temp_result['deleted_count'],
                'current_records': limit_result.get('current_count', 0)
            }
        })
    except Exception as e:
        logger.error(f"Error cleaning up files: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_mqtt()
    init_inbox_monitor()
    
    # Read port from environment variable (for Docker/HA addon) or use default
    port = int(os.environ.get('PORT', 6080))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting FaceInsight web server on {host}:{port}")
    app.run(host=host, port=port, debug=False)
