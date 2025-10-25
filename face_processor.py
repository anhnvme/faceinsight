import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from typing import List, Tuple, Optional
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaceProcessor:
    def __init__(self, model_name='buffalo_s'):
        os.environ['OMP_NUM_THREADS'] = '4'
        os.environ['MKL_NUM_THREADS'] = '4'
        
        # Set model directory to project folder instead of ~/.insightface
        # InsightFace will automatically append /models to the end, so root should be the parent directory
        self.models_root = os.path.dirname(__file__)  # /root/FaceInsight
        os.environ['INSIGHTFACE_HOME'] = self.models_root
        
        self.model_name = model_name
        self.app = None
        self.load_model(model_name)
    
    @contextmanager
    def temporary_threshold(self, threshold: float):
        """Context manager for temporary detection threshold changes"""
        old_thresh = self.app.det_model.det_thresh if hasattr(self.app, 'det_model') else 0.5
        try:
            if hasattr(self.app, 'det_model'):
                self.app.det_model.det_thresh = threshold
            yield
        finally:
            if hasattr(self.app, 'det_model'):
                self.app.det_model.det_thresh = old_thresh
    
    def load_model(self, model_name: str):
        try:
            logger.info(f"Loading model: {model_name}")
            self.model_name = model_name
            
            # Delete old app if exists to avoid conflicts
            if self.app is not None:
                del self.app
                self.app = None
            
            # Check and fix nested directory structure if present
            model_path = os.path.join(self.models_root, 'models', model_name)
            nested_path = os.path.join(model_path, model_name)
            if os.path.isdir(nested_path):
                logger.warning(f"Fixing nested directory structure for {model_name}")
                import shutil
                # Move files from nested folder up
                for item in os.listdir(nested_path):
                    src = os.path.join(nested_path, item)
                    dst = os.path.join(model_path, item)
                    if not os.path.exists(dst):
                        shutil.move(src, dst)
                # Delete empty folder
                try:
                    os.rmdir(nested_path)
                except:
                    pass
            
            # Delete zip file after extraction to save disk space
            zip_path = os.path.join(self.models_root, 'models', f'{model_name}.zip')
            if os.path.exists(zip_path) and os.path.isdir(model_path):
                logger.info(f"Deleting zip file: {zip_path}")
                try:
                    os.remove(zip_path)
                    logger.info(f"Zip file deleted successfully")
                except Exception as e:
                    logger.warning(f"Could not delete zip file: {e}")
            
            # Load new model from project directory
            # FaceAnalysis will automatically look in {root}/models/{model_name}
            self.app = FaceAnalysis(name=model_name, root=self.models_root, providers=['CPUExecutionProvider'])
            
            # Det_size: Use 640 for ALL models because:
            # - 640 is a safe value, well supported by all detection models
            # - Higher det_size (960, 1280) MAY make detection model too strict → miss faces
            # - Accuracy mainly depends on RECOGNITION model, not det_size
            # Valid values: 320, 480, 512, 640, 960, 1280
            det_size = (640, 640)
            self.app.prepare(ctx_id=-1, det_size=det_size)
            
            logger.info(f"Model {model_name} loaded successfully with det_size={det_size}")
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            raise
    
    def detect_and_align_face(self, image_path: str, min_size: int = 360) -> Optional[Tuple[np.ndarray, np.ndarray, int, int, dict]]:
        """
        Detect and align face in image.
        
        Args:
            image_path: Path to image file
            min_size: Minimum face size after resize
            
        Returns:
            Tuple of (face_img, embedding, age, gender, bbox_info) or None
            Gender: 0 = Female, 1 = Male
            bbox_info: {'x': x1, 'y': y1, 'width': w, 'height': h, 'img_width': img_w, 'img_height': img_h}
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Failed to read image: {image_path}")
                return None
            
            faces = self.app.get(img)
            
            if len(faces) == 0:
                logger.warning(f"No face detected in {image_path}")
                return None
            
            if len(faces) > 1:
                logger.warning(f"Multiple faces detected in {image_path}, using the first one")
            
            face = faces[0]
            
            # Store original bbox for frontend display
            bbox = face.bbox.astype(int)
            h, w = img.shape[:2]
            bbox_info = {
                'x': int(bbox[0]),
                'y': int(bbox[1]),
                'width': int(bbox[2] - bbox[0]),
                'height': int(bbox[3] - bbox[1]),
                'img_width': w,
                'img_height': h
            }
            
            # Get age and gender
            age = int(face.age) if hasattr(face, 'age') else 0
            gender = int(face.gender) if hasattr(face, 'gender') else -1
            
            # Crop face with padding
            padding = 60
            x1 = max(0, bbox[0] - padding)
            y1 = max(0, bbox[1] - padding)
            x2 = min(w, bbox[2] + padding)
            y2 = min(h, bbox[3] + padding)
            
            face_img = img[y1:y2, x1:x2]
            
            # Ensure minimum size
            if face_img.shape[0] < min_size or face_img.shape[1] < min_size:
                max_dim = max(face_img.shape[0], face_img.shape[1])
                if max_dim > 0:
                    scale = min_size / max_dim
                    face_img = cv2.resize(face_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
            
            # Get embedding from detected face
            embedding = face.normed_embedding
            
            # Validate embedding
            if embedding is None or len(embedding) == 0:
                logger.error(f"Invalid embedding extracted from {image_path}")
                return None
                
            logger.debug(f"Extracted: embedding={len(embedding)}, age={age}, gender={gender} from {image_path}")
            
            return face_img, embedding, age, gender, bbox_info
            
        except Exception as e:
            logger.error(f"Error processing face in {image_path}: {e}")
            return None
    
    def extract_embedding(self, image_path: str, is_aligned: bool = False) -> Optional[np.ndarray]:
        """
        Extract face embedding from image file.
        
        Args:
            image_path: Path to image file
            is_aligned: If True, assumes image is already cropped face (skip detection padding/resize).
                       If False, performs full face detection and alignment.
        
        Returns:
            Face embedding as numpy array, or None if failed
        """
        try:
            if is_aligned:
                # For already-cropped face images (from database)
                img = cv2.imread(image_path)
                if img is None:
                    logger.error(f"Failed to read image: {image_path}")
                    return None
                
                faces = self.app.get(img)
                
                if len(faces) == 0:
                    logger.warning(f"No face detected in cropped image: {image_path}")
                    return None
                
                face = faces[0]
                embedding = face.normed_embedding
                
                if embedding is None or len(embedding) == 0:
                    logger.error(f"Invalid embedding from {image_path}")
                    return None
                
                logger.debug(f"Extracted embedding from aligned image: {image_path}")
                return embedding
            else:
                # For original images (full detection)
                result = self.detect_and_align_face(image_path)
                if result:
                    return result[1]  # Return embedding only
                return None
                
        except Exception as e:
            logger.error(f"Error extracting embedding from {'aligned' if is_aligned else 'original'} image {image_path}: {e}")
            return None
    
    def compare_faces(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compare two embeddings. Assumes embeddings are already flattened."""
        # Check if embedding sizes match
        if embedding1.shape[0] != embedding2.shape[0]:
            logger.warning(f"Embedding size mismatch: {embedding1.shape[0]} vs {embedding2.shape[0]}")
            return 0.0
        
        similarity = np.dot(embedding1, embedding2)
        return float(similarity)
    
    def find_match(self, test_embedding: np.ndarray, database_embeddings: List[Tuple[int, str, str, List[float]]], 
                   threshold: float = 0.4, top_k: int = 3) -> Optional[Tuple[int, str, str, float]]:
        """
        Hybrid matching approach:
        - If person has >= top_k images: Use Top-K average (voting mechanism)
        - If person has < top_k images: Use best single match
        
        Args:
            test_embedding: Embedding to match
            database_embeddings: List of (img_id, name, nickname, embedding)
            threshold: Minimum similarity threshold
            top_k: Number of top scores to average (default 3)
            
        Returns:
            Tuple of (img_id, name, nickname, score) or None
        """
        test_embedding = np.array(test_embedding).flatten()
        
        # Group scores by person
        person_data = {}  # {person_name: {'scores': [(score, img_id)], 'nickname': str}}
        
        for img_id, name, nickname, db_embedding in database_embeddings:
            db_embedding = np.array(db_embedding).flatten()
            
            # Skip embedding with mismatched size
            if db_embedding.shape[0] != test_embedding.shape[0]:
                logger.warning(f"Skipping embedding {img_id} due to size mismatch: {db_embedding.shape[0]} vs {test_embedding.shape[0]}")
                continue
            
            score = self.compare_faces(test_embedding, db_embedding)
            
            if name not in person_data:
                person_data[name] = {'scores': [], 'nickname': nickname}
            person_data[name]['scores'].append((score, img_id))
        
        # Find best match using hybrid approach
        best_match = None
        best_score = threshold
        best_person_name = None
        
        for person_name, data in person_data.items():
            scores_with_ids = data['scores']
            nickname = data['nickname']
            
            if len(scores_with_ids) >= top_k:
                # Voting: Use average of top-K scores
                sorted_scores = sorted(scores_with_ids, key=lambda x: x[0], reverse=True)
                top_scores = sorted_scores[:top_k]
                
                # Calculate average score
                avg_score = sum(s[0] for s in top_scores) / len(top_scores)
                
                # Use the image ID from the best single match among top-K
                best_img_id = top_scores[0][1]
                
                logger.debug(f"Person '{person_name}': {len(scores_with_ids)} images, "
                           f"top-{top_k} average = {avg_score:.3f}, best single = {top_scores[0][0]:.3f}")
                
                final_score = avg_score
            else:
                # Best single: Use highest score
                sorted_scores = sorted(scores_with_ids, key=lambda x: x[0], reverse=True)
                final_score = sorted_scores[0][0]
                best_img_id = sorted_scores[0][1]
                
                logger.debug(f"Person '{person_name}': {len(scores_with_ids)} images, "
                           f"best single = {final_score:.3f}")
            
            # Update best match if this person has higher score
            if final_score > best_score:
                best_score = final_score
                best_person_name = person_name
                best_match = (best_img_id, person_name, nickname, final_score)
        
        if best_match:
            logger.info(f"Best match: {best_match[1]} (score: {best_match[3]:.3f})")
        
        return best_match
    
    def validate_image(self, image_path: str) -> bool:
        if not os.path.exists(image_path):
            return False
        
        file_size = os.path.getsize(image_path)
        if file_size > 8 * 1024 * 1024:
            logger.warning(f"Image too large: {file_size} bytes")
            return False
        
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            logger.warning(f"Invalid image format: {ext}")
            return False
        
        img = cv2.imread(image_path)
        if img is None:
            logger.warning(f"Failed to read image: {image_path}")
            return False
        
        return True
    
    def get_available_models(self) -> List[dict]:
        """Get list of available models"""
        return [
            {
                'name': 'buffalo_s',
                'display_name': 'Buffalo S (Small)',
                'description': 'Balanced speed/accuracy - Recommended for CPU N100 ⭐',
                'speed': '⚡⚡',
                'accuracy': '⭐⭐⭐'
            },
            {
                'name': 'buffalo_l',
                'display_name': 'Buffalo L (Large)',
                'description': 'Higher accuracy, ~3x slower - ResNet50',
                'speed': '⚡',
                'accuracy': '⭐⭐⭐⭐'
            },
            {
                'name': 'antelopev2',
                'display_name': 'Antelope v2 (SOTA)',
                'description': 'Most accurate, very slow ~6x - ResNet100 (Requires powerful CPU)',
                'speed': '🐌',
                'accuracy': '⭐⭐⭐⭐⭐'
            }
        ]
