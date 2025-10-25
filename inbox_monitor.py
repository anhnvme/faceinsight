import os
import time
import cv2
import shutil
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
from typing import Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InboxHandler(FileSystemEventHandler):
    def __init__(self, process_callback: Callable, inbox_path: str = './inbox'):
        self.process_callback = process_callback
        self.inbox_path = inbox_path
        self.processing = set()
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            return
        
        if file_path in self.processing:
            return
        
        logger.info(f"New file detected: {file_path}")
        self.processing.add(file_path)
        
        time.sleep(0.5)
        
        if not self._is_file_complete(file_path):
            logger.warning(f"File not complete, waiting: {file_path}")
            time.sleep(1)
        
        try:
            self.process_callback(file_path)
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
        finally:
            self.processing.discard(file_path)
    
    def _is_file_complete(self, file_path: str, wait_time: float = 0.5) -> bool:
        try:
            if not os.path.exists(file_path):
                return False
            
            initial_size = os.path.getsize(file_path)
            time.sleep(wait_time)
            
            if not os.path.exists(file_path):
                return False
            
            final_size = os.path.getsize(file_path)
            
            return initial_size == final_size and final_size > 0
        except Exception as e:
            logger.error(f"Error checking file completion: {e}")
            return False

class InboxMonitor:
    def __init__(self, face_processor, database, mqtt_client, inbox_path: str = './inbox'):
        self.face_processor = face_processor
        self.database = database
        self.mqtt_client = mqtt_client
        self.inbox_path = inbox_path
        self.observer = None
        
        os.makedirs(inbox_path, exist_ok=True)
    
    def save_history_record(self, img, timestamp: str, person_id=None, name="Unknown", 
                          nickname=None, score=0.0, trained_image_id=None, age=0, gender='Unknown', bbox_info=None) -> tuple:
        """Helper to save history log image and thumbnail, returns (history_path, thumbnail_path)"""
        # Save history log image to static/logs/
        history_img_path = f"static/logs/log_{timestamp}.jpg"
        os.makedirs(os.path.dirname(history_img_path), exist_ok=True)
        if not cv2.imwrite(history_img_path, img):
            logger.error(f"Failed to save history image: {history_img_path}")
            return None, None
        
        # Create and save thumbnail (150x150)
        thumbnail = cv2.resize(img, (150, 150))
        thumbnail_path = f"static/logs/thumb_{timestamp}.jpg"
        if not cv2.imwrite(thumbnail_path, thumbnail):
            logger.error(f"Failed to save thumbnail: {thumbnail_path}")
            if os.path.exists(history_img_path):
                os.remove(history_img_path)
            return None, None
        
        # Add to database with bbox_info
        self.database.add_recognition_history(
            person_id, name, nickname, score,
            history_img_path, thumbnail_path, trained_image_id, bbox_info
        )
        
        # Publish to MQTT with age and gender (no image_url parameter)
        self.mqtt_client.publish_detection(name, nickname, score, age, gender)
        
        return history_img_path, thumbnail_path
    
    def process_image(self, image_path: str):
        try:
            logger.info(f"Processing image: {image_path}")
            
            # Read image ONCE at the beginning
            img = cv2.imread(image_path)
            if img is None:
                logger.warning(f"Failed to read image: {image_path}")
                self._delete_file(image_path)
                return
            
            # Validate without re-reading
            file_size = os.path.getsize(image_path)
            if file_size > 8 * 1024 * 1024:
                logger.warning(f"Image too large: {file_size} bytes")
                self._delete_file(image_path)
                return
            
            # Detect face using already-loaded image
            result = self.face_processor.detect_and_align_face(image_path)
            if not result:
                logger.warning(f"No face detected in: {image_path}")
                self._delete_file(image_path)
                return
            
            face_img, embedding, age, gender, bbox_info = result
            
            # Gender text for display
            gender_text = 'Male' if gender == 1 else 'Female' if gender == 0 else 'Unknown'
            
            database_embeddings = self.database.get_all_embeddings()
            threshold = float(self.database.get_setting('recognition_threshold') or 0.4)
            top_k = int(self.database.get_setting('voting_top_k') or 3)
            
            match = self.face_processor.find_match(embedding, database_embeddings, threshold, top_k)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            
            if match:
                img_id, name, nickname, score = match
                person = self.database.get_person_by_name(name)
                person_id = person['id'] if person else None
                
                logger.info(f"Face matched: {name} ({nickname}) with score {round(score * 100)}, age={age}, gender={gender_text}")
                
                # Check if auto-train is enabled
                auto_train_enabled = self.database.get_setting('auto_train_enabled') == 'true'
                
                trained_image_id = None
                if person_id and auto_train_enabled:
                    # Use shared auto-train method
                    trained_image_id = self.database.auto_train_face(
                        person_id, name, face_img, embedding, timestamp, image_path
                    )
                elif person_id and not auto_train_enabled:
                    logger.info(f"Auto-train is disabled, skipping training for {name}")
                
                # Save history using helper function with age and gender
                self.save_history_record(img, timestamp, person_id, name, nickname, score, trained_image_id, age, gender_text, bbox_info)
            else:
                logger.info(f"Unknown face detected (age={age}, gender={gender_text})")
                # Save history using helper function with age and gender
                self.save_history_record(img, timestamp, age=age, gender=gender_text, bbox_info=bbox_info)
            
            self._delete_file(image_path)
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            self._delete_file(image_path)
    
    def _delete_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
    
    def start(self):
        handler = InboxHandler(self.process_image, self.inbox_path)
        self.observer = Observer()
        self.observer.schedule(handler, self.inbox_path, recursive=False)
        self.observer.start()
        logger.info(f"Started monitoring inbox: {self.inbox_path}")
    
    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped monitoring inbox")
