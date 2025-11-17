"""Image augmentation module for SKU product images"""

import logging
from typing import List, Tuple, Optional
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance
import random
import asyncio
import aiohttp
import io

logger = logging.getLogger(__name__)


class ImageAugmenter:
    """Image augmentation processor for SKU product images"""

    def __init__(
        self,
        brightness_range: Tuple[float, float] = (0.7, 1.3),
        contrast_range: Tuple[float, float] = (0.8, 1.2),
        crop_ratio: float = 0.9,
        noise_intensity: float = 0.02,
        rotation_angles: List[int] = [0, 90, 180, 270],
    ):
        """
        Initialize image augmenter

        Args:
            brightness_range: Range for brightness adjustment (min, max)
            contrast_range: Range for contrast adjustment (min, max)
            crop_ratio: Ratio of image to keep when cropping
            noise_intensity: Intensity of noise to add (0.0 to 1.0)
            rotation_angles: List of rotation angles to apply
        """
        self.brightness_range = brightness_range
        self.contrast_range = contrast_range
        self.crop_ratio = crop_ratio
        self.noise_intensity = noise_intensity
        self.rotation_angles = rotation_angles

    def flip_horizontal(self, image: Image.Image) -> Image.Image:
        """Flip image horizontally (mirror)"""
        return image.transpose(Image.FLIP_LEFT_RIGHT)

    def flip_vertical(self, image: Image.Image) -> Image.Image:
        """Flip image vertically"""
        return image.transpose(Image.FLIP_TOP_BOTTOM)

    def random_crop(self, image: Image.Image) -> Image.Image:
        """Randomly crop the image and resize back to original size"""
        width, height = image.size
        new_width = int(width * self.crop_ratio)
        new_height = int(height * self.crop_ratio)

        # Random crop position
        left = random.randint(0, width - new_width)
        top = random.randint(0, height - new_height)
        right = left + new_width
        bottom = top + new_height

        cropped = image.crop((left, top, right, bottom))
        # Resize back to original size
        return cropped.resize((width, height), Image.LANCZOS)

    def adjust_brightness(self, image: Image.Image, factor: Optional[float] = None) -> Image.Image:
        """Adjust image brightness"""
        if factor is None:
            factor = random.uniform(*self.brightness_range)
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)

    def adjust_contrast(self, image: Image.Image, factor: Optional[float] = None) -> Image.Image:
        """Adjust image contrast"""
        if factor is None:
            factor = random.uniform(*self.contrast_range)
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)

    def add_noise(self, image: Image.Image) -> Image.Image:
        """Add random Gaussian noise to image"""
        img_array = np.array(image).astype(np.float32)
        noise = np.random.normal(0, self.noise_intensity * 255, img_array.shape)
        noisy_img = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy_img)

    def rotate(self, image: Image.Image, angle: Optional[int] = None) -> Image.Image:
        """Rotate image by specified angle"""
        if angle is None:
            angle = random.choice(self.rotation_angles)
        return image.rotate(angle, expand=True)

    def augment(self, image: Image.Image, augmentation_type: str) -> Image.Image:
        """
        Apply specific augmentation to image

        Args:
            image: PIL Image object
            augmentation_type: Type of augmentation
                ('flip_h', 'flip_v', 'crop', 'brightness', 'contrast', 'noise', 'rotate')

        Returns:
            Augmented image
        """
        augmentation_map = {
            "flip_h": self.flip_horizontal,
            "flip_v": self.flip_vertical,
            "crop": self.random_crop,
            "brightness": self.adjust_brightness,
            "contrast": self.adjust_contrast,
            "noise": self.add_noise,
            "rotate": self.rotate,
        }

        if augmentation_type in augmentation_map:
            return augmentation_map[augmentation_type](image)
        else:
            logger.warning(f"Unknown augmentation type: {augmentation_type}")
            return image

    def generate_augmentations(
        self,
        image: Image.Image,
        num_augmentations: int = 5,
        augmentation_types: Optional[List[str]] = None,
    ) -> List[Tuple[Image.Image, str]]:
        """
        Generate multiple augmented versions of an image

        Args:
            image: PIL Image object
            num_augmentations: Number of augmented images to generate
            augmentation_types: List of augmentation types to apply
                If None, uses default set

        Returns:
            List of tuples (augmented_image, augmentation_name)
        """
        if augmentation_types is None:
            augmentation_types = [
                "flip_h",
                "crop",
                "brightness",
                "contrast",
                "noise",
            ]

        augmented_images = []

        # Generate augmentations
        for i in range(num_augmentations):
            # Randomly select augmentation type
            aug_type = random.choice(augmentation_types)
            augmented = self.augment(image.copy(), aug_type)
            augmented_images.append((augmented, f"{aug_type}_{i+1}"))

        logger.debug(f"Generated {len(augmented_images)} augmented images")
        return augmented_images

    def generate_all_augmentations(
        self, image: Image.Image
    ) -> List[Tuple[Image.Image, str]]:
        """
        Generate all possible augmentations

        Args:
            image: PIL Image object

        Returns:
            List of tuples (augmented_image, augmentation_name)
        """
        augmentations = []

        # Original
        augmentations.append((image.copy(), "original"))

        # Flip horizontal
        augmentations.append((self.flip_horizontal(image), "flip_h"))

        # Random crop
        augmentations.append((self.random_crop(image), "crop"))

        # Brightness variations
        for i, factor in enumerate([0.7, 0.9, 1.1, 1.3]):
            aug = self.adjust_brightness(image, factor)
            augmentations.append((aug, f"brightness_{factor}"))

        # Add noise
        augmentations.append((self.add_noise(image), "noise"))

        logger.info(f"Generated {len(augmentations)} augmented versions")
        return augmentations


class ImageDownloader:
    """Async image downloader"""

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize image downloader

        Args:
            timeout: Download timeout in seconds
            max_retries: Maximum number of retries
        """
        self.timeout = timeout
        self.max_retries = max_retries

    async def download_image(self, url: str) -> Optional[Image.Image]:
        """
        Download image from URL

        Args:
            url: Image URL

        Returns:
            PIL Image object or None if download failed
        """
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            content = await response.read()
                            image = Image.open(io.BytesIO(content)).convert("RGB")
                            return image
                        else:
                            logger.warning(
                                f"Failed to download image (status {response.status}): {url}"
                            )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout downloading image (attempt {attempt + 1}): {url}")
            except Exception as e:
                logger.error(f"Error downloading image (attempt {attempt + 1}): {url} - {e}")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(1)  # Wait before retry

        return None

    def download_image_sync(self, url: str) -> Optional[Image.Image]:
        """
        Synchronous image download

        Args:
            url: Image URL

        Returns:
            PIL Image object or None if failed
        """
        import requests

        try:
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            return image
        except Exception as e:
            logger.error(f"Error downloading image: {url} - {e}")
            return None


def save_augmented_images(
    augmented_images: List[Tuple[Image.Image, str]],
    sku: str,
    output_dir: Path,
) -> List[Path]:
    """
    Save augmented images to disk

    Args:
        augmented_images: List of (image, augmentation_name) tuples
        sku: SKU identifier
        output_dir: Output directory path

    Returns:
        List of saved file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []

    for image, aug_name in augmented_images:
        # Sanitize SKU for filename
        safe_sku = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in sku)
        filename = f"{safe_sku}_{aug_name}.jpg"
        filepath = output_dir / filename

        try:
            image.save(filepath, "JPEG", quality=95)
            saved_paths.append(filepath)
            logger.debug(f"Saved augmented image: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save image {filepath}: {e}")

    return saved_paths
