#!/usr/bin/env python3
"""
Augment product images to simulate real-world mobile photography conditions
This helps improve recognition accuracy for mobile-captured photos
"""

import sys
import logging
from pathlib import Path
import random
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from tqdm import tqdm
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImageAugmentor:
    """
    Augment product images to simulate real-world conditions:
    - Different lighting conditions
    - Various angles and rotations
    - Background variations
    - Blur and noise
    - Occlusions
    """

    def __init__(self, output_dir='data/augmented'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def apply_lighting_variation(self, img):
        """Simulate different lighting conditions"""
        # Random brightness adjustment
        brightness_factor = random.uniform(0.6, 1.4)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness_factor)

        # Random contrast adjustment
        contrast_factor = random.uniform(0.7, 1.3)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_factor)

        # Random color temperature shift
        if random.random() > 0.5:
            color_factor = random.uniform(0.8, 1.2)
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(color_factor)

        return img

    def apply_rotation(self, img):
        """Simulate different viewing angles"""
        # Small random rotation (-15 to 15 degrees)
        angle = random.uniform(-15, 15)
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))
        return img

    def apply_perspective_transform(self, img):
        """Simulate viewing from different angles (perspective distortion)"""
        width, height = img.size

        # Random perspective coefficients
        coeffs = [
            1 + random.uniform(-0.1, 0.1),  # a
            random.uniform(-0.05, 0.05),     # b
            random.uniform(-20, 20),          # c
            random.uniform(-0.05, 0.05),     # d
            1 + random.uniform(-0.1, 0.1),  # e
            random.uniform(-20, 20),          # f
            random.uniform(-0.0002, 0.0002), # g
            random.uniform(-0.0002, 0.0002)  # h
        ]

        img = img.transform(
            img.size,
            Image.PERSPECTIVE,
            coeffs,
            Image.BICUBIC
        )
        return img

    def apply_blur(self, img):
        """Simulate motion blur or focus issues"""
        blur_type = random.choice(['gaussian', 'motion', 'none'])

        if blur_type == 'gaussian':
            radius = random.uniform(0.5, 2.0)
            img = img.filter(ImageFilter.GaussianBlur(radius))
        elif blur_type == 'motion':
            # Approximate motion blur
            img = img.filter(ImageFilter.BLUR)

        return img

    def apply_noise(self, img):
        """Add sensor noise"""
        if random.random() > 0.7:  # 30% chance
            img_array = np.array(img)
            noise = np.random.normal(0, 5, img_array.shape).astype(np.uint8)
            img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
            img = Image.fromarray(img_array)
        return img

    def apply_crop_and_zoom(self, img):
        """Simulate different distances/crops"""
        width, height = img.size

        # Random crop factor (80% to 100% of original)
        crop_factor = random.uniform(0.8, 1.0)

        new_width = int(width * crop_factor)
        new_height = int(height * crop_factor)

        # Random crop position
        left = random.randint(0, width - new_width)
        top = random.randint(0, height - new_height)

        img = img.crop((left, top, left + new_width, top + new_height))
        img = img.resize((width, height), Image.LANCZOS)

        return img

    def add_background_clutter(self, img):
        """Add simple background variations"""
        # Create a random colored background
        if random.random() > 0.7:  # 30% chance
            bg_color = tuple(random.randint(200, 255) for _ in range(3))
            background = Image.new('RGB', img.size, bg_color)

            # Paste product on background
            # Assume product is centered
            background.paste(img, (0, 0))
            img = background

        return img

    def augment_image(self, img, augmentation_level='medium'):
        """
        Apply multiple augmentations to simulate real-world conditions

        Args:
            img: PIL Image
            augmentation_level: 'light', 'medium', 'heavy'
        """
        augmentations = {
            'light': ['lighting', 'rotation'],
            'medium': ['lighting', 'rotation', 'blur', 'crop'],
            'heavy': ['lighting', 'rotation', 'perspective', 'blur', 'noise', 'crop', 'background']
        }

        aug_list = augmentations.get(augmentation_level, augmentations['medium'])

        # Apply augmentations
        if 'lighting' in aug_list:
            img = self.apply_lighting_variation(img)

        if 'rotation' in aug_list:
            img = self.apply_rotation(img)

        if 'perspective' in aug_list and random.random() > 0.7:
            img = self.apply_perspective_transform(img)

        if 'blur' in aug_list:
            img = self.apply_blur(img)

        if 'noise' in aug_list:
            img = self.apply_noise(img)

        if 'crop' in aug_list:
            img = self.apply_crop_and_zoom(img)

        if 'background' in aug_list:
            img = self.add_background_clutter(img)

        return img

    def augment_dataset(self, images_dir, num_augmentations=3, level='medium'):
        """
        Augment all images in a directory

        Args:
            images_dir: Directory containing original images
            num_augmentations: Number of augmented versions per image
            level: Augmentation intensity level
        """
        images_dir = Path(images_dir)
        image_files = list(images_dir.glob('*.jpg'))

        logger.info(f"Found {len(image_files)} images to augment")
        logger.info(f"Generating {num_augmentations} augmented versions per image")
        logger.info(f"Augmentation level: {level}")

        total_generated = 0

        for img_path in tqdm(image_files, desc="Augmenting images"):
            try:
                img = Image.open(img_path).convert('RGB')

                # Generate augmented versions
                for i in range(num_augmentations):
                    aug_img = self.augment_image(img, level)

                    # Save augmented image
                    output_name = f"{img_path.stem}_aug{i+1}.jpg"
                    output_path = self.output_dir / output_name
                    aug_img.save(output_path, quality=85)
                    total_generated += 1

            except Exception as e:
                logger.error(f"Error augmenting {img_path.name}: {e}")

        logger.info(f"✓ Generated {total_generated} augmented images")
        logger.info(f"✓ Saved to {self.output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Augment product images to improve mobile recognition accuracy'
    )
    parser.add_argument(
        '--images-dir',
        type=Path,
        default=Path('data/images'),
        help='Directory containing original images'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/augmented'),
        help='Output directory for augmented images'
    )
    parser.add_argument(
        '--num-aug',
        type=int,
        default=3,
        help='Number of augmented versions per image (default: 3)'
    )
    parser.add_argument(
        '--level',
        choices=['light', 'medium', 'heavy'],
        default='medium',
        help='Augmentation intensity level (default: medium)'
    )
    parser.add_argument(
        '--max-images',
        type=int,
        default=None,
        help='Maximum number of original images to process (for testing)'
    )

    args = parser.parse_args()

    # Get image files
    image_files = list(args.images_dir.glob('*.jpg'))
    if args.max_images:
        image_files = image_files[:args.max_images]
        logger.info(f"Processing first {args.max_images} images (test mode)")

    # Create temporary directory with selected images
    if args.max_images:
        temp_dir = Path('data/temp_images')
        temp_dir.mkdir(parents=True, exist_ok=True)
        for img_file in image_files:
            import shutil
            shutil.copy(img_file, temp_dir / img_file.name)
        process_dir = temp_dir
    else:
        process_dir = args.images_dir

    # Augment images
    augmentor = ImageAugmentor(output_dir=args.output_dir)
    augmentor.augment_dataset(
        process_dir,
        num_augmentations=args.num_aug,
        level=args.level
    )

    # Cleanup temp directory
    if args.max_images:
        import shutil
        shutil.rmtree(temp_dir)

    logger.info("✓ Augmentation complete!")


if __name__ == '__main__':
    main()
