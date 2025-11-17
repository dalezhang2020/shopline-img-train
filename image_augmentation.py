"""
Image augmentation module for product images
"""
import os
import io
import random
import logging
from typing import List, Tuple, Optional
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance
import aiohttp

logger = logging.getLogger(__name__)


class ImageAugmenter:
    """Image augmentation processor"""

    def __init__(
        self,
        brightness_range: Tuple[float, float] = (0.7, 1.3),
        crop_ratio: float = 0.9,
        noise_intensity: float = 0.02
    ):
        """
        Initialize image augmenter

        Args:
            brightness_range: Range for brightness adjustment (min, max)
            crop_ratio: Ratio of image to keep when cropping
            noise_intensity: Intensity of noise to add (0.0 to 1.0)
        """
        self.brightness_range = brightness_range
        self.crop_ratio = crop_ratio
        self.noise_intensity = noise_intensity

    def flip_horizontal(self, image: Image.Image) -> Image.Image:
        """
        Flip image horizontally (mirror)

        Args:
            image: PIL Image object

        Returns:
            Flipped image
        """
        return image.transpose(Image.FLIP_LEFT_RIGHT)

    def random_crop(self, image: Image.Image) -> Image.Image:
        """
        Randomly crop the image

        Args:
            image: PIL Image object

        Returns:
            Cropped image
        """
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

    def adjust_brightness(self, image: Image.Image) -> Image.Image:
        """
        Randomly adjust image brightness

        Args:
            image: PIL Image object

        Returns:
            Brightness-adjusted image
        """
        factor = random.uniform(*self.brightness_range)
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)

    def add_noise(self, image: Image.Image) -> Image.Image:
        """
        Add random noise to image

        Args:
            image: PIL Image object

        Returns:
            Image with added noise
        """
        # Convert to numpy array
        img_array = np.array(image).astype(np.float32)

        # Generate random noise
        noise = np.random.normal(0, self.noise_intensity * 255, img_array.shape)

        # Add noise and clip values
        noisy_img = np.clip(img_array + noise, 0, 255).astype(np.uint8)

        return Image.fromarray(noisy_img)

    def augment(
        self,
        image: Image.Image,
        augmentation_type: str
    ) -> Image.Image:
        """
        Apply specific augmentation to image

        Args:
            image: PIL Image object
            augmentation_type: Type of augmentation ('flip', 'crop', 'brightness', 'noise')

        Returns:
            Augmented image
        """
        if augmentation_type == "flip":
            return self.flip_horizontal(image)
        elif augmentation_type == "crop":
            return self.random_crop(image)
        elif augmentation_type == "brightness":
            return self.adjust_brightness(image)
        elif augmentation_type == "noise":
            return self.add_noise(image)
        else:
            logger.warning(f"Unknown augmentation type: {augmentation_type}")
            return image

    def generate_augmentations(
        self,
        image: Image.Image,
        num_augmentations: int = 5
    ) -> List[Tuple[Image.Image, str]]:
        """
        Generate multiple augmented versions of an image

        Args:
            image: PIL Image object
            num_augmentations: Number of augmented images to generate

        Returns:
            List of tuples (augmented_image, augmentation_name)
        """
        augmentations = []
        aug_types = ["flip", "crop", "brightness", "noise"]

        # Original image
        augmentations.append((image.copy(), "original"))

        # Generate augmented versions
        for i in range(num_augmentations):
            aug_type = random.choice(aug_types)
            augmented = self.augment(image.copy(), aug_type)
            augmentations.append((augmented, f"{aug_type}_{i+1}"))

        return augmentations


class ImageDownloader:
    """Async image downloader"""

    def __init__(self, timeout: int = 30):
        """
        Initialize image downloader

        Args:
            timeout: Download timeout in seconds
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def download_image(self, url: str) -> Optional[Image.Image]:
        """
        Download image from URL

        Args:
            url: Image URL

        Returns:
            PIL Image object or None if download fails
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        image = Image.open(io.BytesIO(image_data))
                        # Convert to RGB if necessary
                        if image.mode != 'RGB':
                            image = image.convert('RGB')
                        return image
                    else:
                        logger.warning(f"Failed to download image: {url} (status: {response.status})")
                        return None
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {str(e)}")
            return None


def save_augmented_images(
    images: List[Tuple[Image.Image, str]],
    sku: str,
    output_dir: str
) -> List[str]:
    """
    Save augmented images to disk

    Args:
        images: List of tuples (image, augmentation_name)
        sku: Product SKU
        output_dir: Output directory

    Returns:
        List of saved file paths
    """
    saved_paths = []

    # Create output directory if it doesn't exist
    sku_dir = Path(output_dir) / sku
    sku_dir.mkdir(parents=True, exist_ok=True)

    for image, aug_name in images:
        try:
            filename = f"{sku}_{aug_name}.jpg"
            filepath = sku_dir / filename
            image.save(filepath, "JPEG", quality=95)
            saved_paths.append(str(filepath))
            logger.debug(f"Saved: {filepath}")
        except Exception as e:
            logger.error(f"Error saving image {filename}: {str(e)}")

    return saved_paths
