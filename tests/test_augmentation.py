"""Tests for image augmentation"""

import pytest
import numpy as np
from PIL import Image
from src.utils.augmentation import ImageAugmenter


@pytest.fixture
def test_image():
    """Create a test image"""
    # Create a 224x224 RGB image
    img_array = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    return Image.fromarray(img_array)


def test_augmenter_initialization():
    """Test augmenter initialization"""
    augmenter = ImageAugmenter(
        brightness_range=(0.7, 1.3),
        crop_ratio=0.9
    )

    assert augmenter.brightness_range == (0.7, 1.3)
    assert augmenter.crop_ratio == 0.9


def test_flip_horizontal(test_image):
    """Test horizontal flip"""
    augmenter = ImageAugmenter()
    flipped = augmenter.flip_horizontal(test_image)

    assert flipped.size == test_image.size
    assert isinstance(flipped, Image.Image)


def test_random_crop(test_image):
    """Test random crop"""
    augmenter = ImageAugmenter(crop_ratio=0.9)
    cropped = augmenter.random_crop(test_image)

    # Should be resized back to original size
    assert cropped.size == test_image.size


def test_brightness_adjustment(test_image):
    """Test brightness adjustment"""
    augmenter = ImageAugmenter(brightness_range=(0.8, 1.2))
    adjusted = augmenter.adjust_brightness(test_image, factor=1.1)

    assert adjusted.size == test_image.size
    assert isinstance(adjusted, Image.Image)


def test_add_noise(test_image):
    """Test noise addition"""
    augmenter = ImageAugmenter(noise_intensity=0.02)
    noisy = augmenter.add_noise(test_image)

    assert noisy.size == test_image.size
    assert isinstance(noisy, Image.Image)


def test_generate_augmentations(test_image):
    """Test generating multiple augmentations"""
    augmenter = ImageAugmenter()
    augmented = augmenter.generate_augmentations(test_image, num_augmentations=5)

    assert len(augmented) == 5

    for aug_img, aug_name in augmented:
        assert isinstance(aug_img, Image.Image)
        assert isinstance(aug_name, str)
        assert aug_img.size == test_image.size
