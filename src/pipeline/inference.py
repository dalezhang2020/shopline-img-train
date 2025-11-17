"""SKU Recognition Inference Pipeline"""

import logging
from typing import List, Dict, Any, Union, Optional, Tuple
from pathlib import Path
import numpy as np
from PIL import Image
import yaml

from ..models.clip_encoder import CLIPEncoder
from ..models.grounding_dino import GroundingDINODetector
from ..database.vector_db import VectorDatabase
from ..utils.image_utils import load_image

logger = logging.getLogger(__name__)


class SKURecognitionPipeline:
    """
    Complete SKU recognition pipeline combining:
    1. Grounding DINO for object detection
    2. CLIP for feature extraction
    3. FAISS for similarity search
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        clip_model: Optional[CLIPEncoder] = None,
        detector: Optional[GroundingDINODetector] = None,
        vector_db: Optional[VectorDatabase] = None,
    ):
        """
        Initialize SKU recognition pipeline

        Args:
            config_path: Path to configuration file
            clip_model: Pre-initialized CLIP encoder
            detector: Pre-initialized Grounding DINO detector
            vector_db: Pre-initialized vector database
        """
        # Load config
        if config_path:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._default_config()

        # Initialize components
        self.clip_model = clip_model or self._init_clip()
        self.detector = detector or self._init_detector()
        self.vector_db = vector_db or self._init_vector_db()

        # Inference settings
        self.confidence_threshold = self.config['inference']['confidence_threshold']
        self.top_k = self.config['inference']['top_k']

        logger.info("SKU Recognition Pipeline initialized")

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'clip': {
                'model_name': 'ViT-B-32',
                'pretrained': 'openai',
                'device': 'cuda',
                'batch_size': 32,
            },
            'grounding_dino': {
                'device': 'cuda',
                'box_threshold': 0.35,
                'text_threshold': 0.25,
                'prompts': [
                    'retail product',
                    'furniture item',
                    'decor item',
                ],
            },
            'inference': {
                'confidence_threshold': 0.7,
                'top_k': 5,
            },
        }

    def _init_clip(self) -> CLIPEncoder:
        """Initialize CLIP encoder"""
        clip_config = self.config.get('clip', {})
        return CLIPEncoder(
            model_name=clip_config.get('model_name', 'ViT-B-32'),
            pretrained=clip_config.get('pretrained', 'openai'),
            device=clip_config.get('device'),
            batch_size=clip_config.get('batch_size', 32),
        )

    def _init_detector(self) -> GroundingDINODetector:
        """Initialize Grounding DINO detector"""
        dino_config = self.config.get('grounding_dino', {})
        return GroundingDINODetector(
            config_file=dino_config.get('config_file'),
            checkpoint_path=dino_config.get('checkpoint_path'),
            device=dino_config.get('device'),
            box_threshold=dino_config.get('box_threshold', 0.35),
            text_threshold=dino_config.get('text_threshold', 0.25),
        )

    def _init_vector_db(self) -> VectorDatabase:
        """Initialize vector database"""
        faiss_config = self.config.get('faiss', {})
        return VectorDatabase(
            dimension=faiss_config.get('dimension', 512),
            index_type=faiss_config.get('index_type', 'IndexFlatL2'),
        )

    def load_database(self, index_path: Path, metadata_path: Path):
        """
        Load pre-built vector database

        Args:
            index_path: Path to FAISS index
            metadata_path: Path to metadata
        """
        logger.info(f"Loading vector database from {index_path}")
        self.vector_db.load(index_path, metadata_path)
        logger.info(f"Database loaded: {self.vector_db.get_stats()}")

    def detect_products(
        self,
        image: Union[Image.Image, np.ndarray, Path],
        text_prompt: Optional[str] = None,
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Detect products in image using Grounding DINO

        Args:
            image: Input image
            text_prompt: Text prompt for detection

        Returns:
            Tuple of (boxes, scores, labels)
        """
        # Load image if path
        if isinstance(image, (str, Path)):
            image = load_image(image)

        # Use default prompt if not provided
        if text_prompt is None:
            prompts = self.config.get('grounding_dino', {}).get('prompts', ['retail product'])
            text_prompt = '. '.join(prompts)

        # Detect
        boxes, scores, labels = self.detector.detect(image, text_prompt)

        logger.info(f"Detected {len(boxes)} products")
        return boxes, scores, labels

    def recognize_sku(
        self,
        crop: Union[Image.Image, np.ndarray],
        top_k: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """
        Recognize SKU from cropped product image

        Args:
            crop: Cropped product image
            top_k: Number of top results to return

        Returns:
            Tuple of (results, similarities)
        """
        if top_k is None:
            top_k = self.top_k

        # Extract CLIP embedding
        embedding = self.clip_model.encode_image(crop)

        # Search in database
        results, similarities = self.vector_db.search(
            embedding,
            k=top_k,
            return_distances=True,
        )

        return results, similarities

    def process_image(
        self,
        image: Union[Image.Image, np.ndarray, Path],
        text_prompt: Optional[str] = None,
        visualize: bool = False,
        output_dir: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """
        Complete pipeline: detect products and recognize SKUs

        Args:
            image: Input image
            text_prompt: Text prompt for detection
            visualize: Whether to save visualizations
            output_dir: Directory to save outputs

        Returns:
            List of detection results with SKU information
        """
        # Load image if path
        if isinstance(image, (str, Path)):
            image_path = Path(image)
            image = load_image(image)
        else:
            image_path = None

        # Step 1: Detect products
        boxes, scores, labels = self.detect_products(image, text_prompt)

        if len(boxes) == 0:
            logger.warning("No products detected")
            return []

        # Step 2: Crop detected regions
        crops = self.detector.crop_detections(image, boxes)

        # Step 3: Recognize SKUs for each crop
        results = []
        for i, (box, score, label, crop) in enumerate(zip(boxes, scores, labels, crops)):
            # Skip if crop is too small
            if crop.shape[0] < 10 or crop.shape[1] < 10:
                logger.warning(f"Skipping small crop {i}")
                continue

            # Recognize SKU
            sku_results, similarities = self.recognize_sku(crop)

            # Filter by confidence threshold
            if len(sku_results) > 0 and similarities[0] >= self.confidence_threshold:
                result = {
                    'detection_id': i,
                    'box': box.tolist(),
                    'detection_score': float(score),
                    'detection_label': label,
                    'top_matches': [
                        {
                            'sku': sku_result.get('sku'),
                            'title': sku_result.get('title'),
                            'category': sku_result.get('category'),
                            'similarity': float(sim),
                            'metadata': sku_result,
                        }
                        for sku_result, sim in zip(sku_results, similarities)
                    ]
                }
                results.append(result)

        logger.info(f"Recognized {len(results)} products")

        # Visualize if requested
        if visualize and output_dir:
            self._visualize_results(image, results, output_dir, image_path)

        return results

    def _visualize_results(
        self,
        image: Image.Image,
        results: List[Dict[str, Any]],
        output_dir: Path,
        image_path: Optional[Path] = None,
    ):
        """Visualize detection and recognition results"""
        import cv2

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert to numpy array
        img_array = np.array(image)

        # Draw results
        for result in results:
            box = result['box']
            x1, y1, x2, y2 = [int(v) for v in box]

            # Get top match
            if result['top_matches']:
                top_match = result['top_matches'][0]
                sku = top_match['sku']
                similarity = top_match['similarity']
                label_text = f"SKU: {sku} ({similarity:.2f})"
            else:
                label_text = "Unknown"

            # Draw box
            cv2.rectangle(img_array, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Draw label background
            text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(
                img_array,
                (x1, y1 - text_size[1] - 10),
                (x1 + text_size[0], y1),
                (0, 255, 0),
                -1
            )

            # Draw label text
            cv2.putText(
                img_array,
                label_text,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2
            )

        # Save visualization
        if image_path:
            output_path = output_dir / f"{image_path.stem}_result.jpg"
        else:
            output_path = output_dir / "result.jpg"

        cv2.imwrite(str(output_path), cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))
        logger.info(f"Saved visualization to {output_path}")

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            'clip_model': self.clip_model.model_name,
            'embedding_dim': self.clip_model.embedding_dim,
            'database': self.vector_db.get_stats(),
        }
