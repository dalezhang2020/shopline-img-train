"""Grounding DINO for zero-shot object detection"""

import logging
from typing import List, Tuple, Optional, Union
from pathlib import Path
import numpy as np
import torch
from PIL import Image
import cv2

logger = logging.getLogger(__name__)


class GroundingDINODetector:
    """Grounding DINO detector for text-prompted object detection"""

    def __init__(
        self,
        config_file: Optional[str] = None,
        checkpoint_path: Optional[str] = None,
        device: Optional[str] = None,
        box_threshold: float = 0.35,
        text_threshold: float = 0.25,
    ):
        """
        Initialize Grounding DINO detector

        Args:
            config_file: Path to config file
            checkpoint_path: Path to model checkpoint
            device: Device to use (cuda/cpu)
            box_threshold: Box confidence threshold
            text_threshold: Text confidence threshold
        """
        self.box_threshold = box_threshold
        self.text_threshold = text_threshold

        # Set device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Initializing Grounding DINO on {self.device}")

        try:
            # Import groundingdino (lazy import)
            from groundingdino.util.inference import load_model, predict

            self.predict_fn = predict

            # Load model
            if config_file and checkpoint_path:
                logger.info(f"Loading model from {checkpoint_path}")
                self.model = load_model(config_file, checkpoint_path, device=self.device)
            else:
                # Try to load default pretrained model
                logger.info("Loading default Grounding DINO model")
                self.model = self._load_default_model()

            logger.info("Grounding DINO loaded successfully")

        except ImportError as e:
            logger.error(f"Failed to import groundingdino: {e}")
            logger.info("Installing groundingdino-py package is recommended")
            self.model = None
            self.predict_fn = None

    def _load_default_model(self):
        """Load default Grounding DINO model"""
        try:
            from groundingdino.util.inference import load_model

            # Try to download and load default model
            # This is a placeholder - actual implementation depends on groundingdino-py
            config_url = "https://huggingface.co/ShilongLiu/GroundingDINO/resolve/main/GroundingDINO_SwinT_OGC.py"
            checkpoint_url = "https://huggingface.co/ShilongLiu/GroundingDINO/resolve/main/groundingdino_swint_ogc.pth"

            logger.warning("Default model loading not implemented. Please provide config_file and checkpoint_path.")
            return None

        except Exception as e:
            logger.error(f"Failed to load default model: {e}")
            return None

    def detect(
        self,
        image: Union[Image.Image, np.ndarray],
        text_prompt: str,
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Detect objects in image using text prompt

        Args:
            image: PIL Image or numpy array
            text_prompt: Text description of objects to detect

        Returns:
            Tuple of (boxes, scores, labels)
            - boxes: Array of bounding boxes in format [x1, y1, x2, y2] (N, 4)
            - scores: Confidence scores (N,)
            - labels: Text labels (N,)
        """
        if self.model is None:
            logger.error("Model not loaded. Using fallback detection.")
            return self._fallback_detect(image)

        # Convert to PIL Image if needed
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        try:
            # Run prediction
            boxes, logits, phrases = self.predict_fn(
                model=self.model,
                image=image,
                caption=text_prompt,
                box_threshold=self.box_threshold,
                text_threshold=self.text_threshold,
                device=self.device,
            )

            # Convert boxes to numpy and denormalize
            if len(boxes) > 0:
                h, w = image.size[1], image.size[0]
                boxes_np = boxes.cpu().numpy()

                # Boxes are in format [cx, cy, w, h] normalized, convert to [x1, y1, x2, y2]
                boxes_xyxy = np.zeros_like(boxes_np)
                boxes_xyxy[:, 0] = (boxes_np[:, 0] - boxes_np[:, 2] / 2) * w  # x1
                boxes_xyxy[:, 1] = (boxes_np[:, 1] - boxes_np[:, 3] / 2) * h  # y1
                boxes_xyxy[:, 2] = (boxes_np[:, 0] + boxes_np[:, 2] / 2) * w  # x2
                boxes_xyxy[:, 3] = (boxes_np[:, 1] + boxes_np[:, 3] / 2) * h  # y2

                scores = logits.cpu().numpy()
            else:
                boxes_xyxy = np.array([])
                scores = np.array([])
                phrases = []

            return boxes_xyxy, scores, phrases

        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return self._fallback_detect(image)

    def _fallback_detect(self, image: Union[Image.Image, np.ndarray]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Fallback detection method when Grounding DINO is not available
        Returns the entire image as a single detection box

        Args:
            image: Input image

        Returns:
            Tuple of (boxes, scores, labels)
        """
        if isinstance(image, Image.Image):
            w, h = image.size
        else:
            h, w = image.shape[:2]

        # Return full image as detection
        boxes = np.array([[0, 0, w, h]], dtype=np.float32)
        scores = np.array([1.0], dtype=np.float32)
        labels = ["product"]

        logger.warning("Using fallback detection - returning full image")
        return boxes, scores, labels

    def detect_batch(
        self,
        images: List[Union[Image.Image, np.ndarray]],
        text_prompt: str,
    ) -> List[Tuple[np.ndarray, np.ndarray, List[str]]]:
        """
        Batch detection on multiple images

        Args:
            images: List of images
            text_prompt: Text description

        Returns:
            List of (boxes, scores, labels) tuples
        """
        results = []
        for image in images:
            result = self.detect(image, text_prompt)
            results.append(result)
        return results

    def visualize_detection(
        self,
        image: Union[Image.Image, np.ndarray],
        boxes: np.ndarray,
        scores: np.ndarray,
        labels: List[str],
        output_path: Optional[Path] = None,
    ) -> np.ndarray:
        """
        Visualize detection results

        Args:
            image: Input image
            boxes: Bounding boxes
            scores: Confidence scores
            labels: Labels
            output_path: Optional path to save visualization

        Returns:
            Visualized image as numpy array
        """
        # Convert to numpy array
        if isinstance(image, Image.Image):
            img_array = np.array(image)
        else:
            img_array = image.copy()

        # Draw boxes
        for box, score, label in zip(boxes, scores, labels):
            x1, y1, x2, y2 = box.astype(int)

            # Draw rectangle
            cv2.rectangle(img_array, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Draw label
            label_text = f"{label}: {score:.2f}"
            cv2.putText(
                img_array,
                label_text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

        # Save if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_path), cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))

        return img_array

    def crop_detections(
        self,
        image: Union[Image.Image, np.ndarray],
        boxes: np.ndarray,
    ) -> List[np.ndarray]:
        """
        Crop detected regions from image

        Args:
            image: Input image
            boxes: Bounding boxes in format [x1, y1, x2, y2]

        Returns:
            List of cropped image arrays
        """
        if isinstance(image, Image.Image):
            img_array = np.array(image)
        else:
            img_array = image

        crops = []
        for box in boxes:
            x1, y1, x2, y2 = box.astype(int)

            # Ensure coordinates are within image bounds
            h, w = img_array.shape[:2]
            x1 = max(0, min(x1, w))
            x2 = max(0, min(x2, w))
            y1 = max(0, min(y1, h))
            y2 = max(0, min(y2, h))

            # Crop
            crop = img_array[y1:y2, x1:x2]
            crops.append(crop)

        return crops
