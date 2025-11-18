"""Image processing utilities"""

import logging
from typing import Union, Tuple, Optional
from pathlib import Path
import numpy as np
from PIL import Image

# cv2 is optional - only needed for advanced numpy array operations
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

logger = logging.getLogger(__name__)


def load_image(image_path: Union[str, Path]) -> Image.Image:
    """
    Load image from file

    Args:
        image_path: Path to image file

    Returns:
        PIL Image
    """
    try:
        image = Image.open(image_path).convert("RGB")
        return image
    except Exception as e:
        logger.error(f"Failed to load image {image_path}: {e}")
        raise


def save_image(image: Union[Image.Image, np.ndarray], output_path: Union[str, Path]):
    """
    Save image to file

    Args:
        image: PIL Image or numpy array
        output_path: Output file path
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(image, np.ndarray):
            # Convert BGR to RGB if needed (requires cv2)
            if CV2_AVAILABLE and len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                # Fallback: assume RGB if cv2 not available
                pass
            image = Image.fromarray(image)

        image.save(output_path)
        logger.debug(f"Saved image to {output_path}")

    except Exception as e:
        logger.error(f"Failed to save image to {output_path}: {e}")
        raise


def resize_image(
    image: Union[Image.Image, np.ndarray],
    size: Tuple[int, int],
    keep_aspect_ratio: bool = True,
) -> Union[Image.Image, np.ndarray]:
    """
    Resize image

    Args:
        image: Input image
        size: Target size (width, height)
        keep_aspect_ratio: Whether to maintain aspect ratio

    Returns:
        Resized image (same type as input)
    """
    is_pil = isinstance(image, Image.Image)

    if is_pil:
        if keep_aspect_ratio:
            image.thumbnail(size, Image.Resampling.LANCZOS)
        else:
            image = image.resize(size, Image.Resampling.LANCZOS)
        return image
    else:
        # For numpy arrays, convert to PIL and back (cv2 not required)
        if not CV2_AVAILABLE:
            # Fallback to PIL for numpy arrays
            pil_img = Image.fromarray(image)
            if keep_aspect_ratio:
                pil_img.thumbnail(size, Image.Resampling.LANCZOS)
            else:
                pil_img = pil_img.resize(size, Image.Resampling.LANCZOS)
            return np.array(pil_img)

        # Use cv2 if available (faster for numpy arrays)
        if keep_aspect_ratio:
            h, w = image.shape[:2]
            target_w, target_h = size
            scale = min(target_w / w, target_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            resized = cv2.resize(image, size, interpolation=cv2.INTER_LANCZOS4)
        return resized
