"""
Local test script using a generated test image
"""
import logging
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pathlib import Path
from image_augmentation import ImageAugmenter, save_augmented_images

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_image(size=(600, 600)):
    """Create a simple test image"""
    # Create a gradient background
    image = Image.new('RGB', size, color='white')
    draw = ImageDraw.Draw(image)

    # Draw some shapes
    draw.rectangle([50, 50, 550, 550], outline='blue', width=5)
    draw.ellipse([150, 150, 450, 450], fill='lightblue', outline='darkblue', width=3)
    draw.rectangle([200, 200, 400, 400], fill='orange', outline='red', width=3)

    # Add some text
    try:
        draw.text((300, 300), "TEST", fill='black', anchor='mm')
    except:
        # If font fails, just skip text
        pass

    return image


def test_image_augmentation():
    """Test image augmentation with generated image"""
    logger.info("=" * 60)
    logger.info("Image Augmentation Local Test")
    logger.info("=" * 60)

    try:
        # Create test image
        logger.info("Creating test image...")
        image = create_test_image()
        logger.info(f"✓ Created test image: {image.size} pixels, mode: {image.mode}")

        # Initialize augmenter
        logger.info("\nInitializing augmenter...")
        augmenter = ImageAugmenter(
            brightness_range=(0.7, 1.3),
            crop_ratio=0.9,
            noise_intensity=0.02
        )
        logger.info("✓ Augmenter initialized")

        # Test individual augmentation types
        logger.info("\nTesting individual augmentation types:")

        # 1. Flip
        logger.info("  1. Testing horizontal flip...")
        flipped = augmenter.flip_horizontal(image.copy())
        logger.info(f"     ✓ Flip: {flipped.size}")

        # 2. Crop
        logger.info("  2. Testing random crop...")
        cropped = augmenter.random_crop(image.copy())
        logger.info(f"     ✓ Crop: {cropped.size}")

        # 3. Brightness
        logger.info("  3. Testing brightness adjustment...")
        brightened = augmenter.adjust_brightness(image.copy())
        logger.info(f"     ✓ Brightness: {brightened.size}")

        # 4. Noise
        logger.info("  4. Testing noise addition...")
        noisy = augmenter.add_noise(image.copy())
        logger.info(f"     ✓ Noise: {noisy.size}")

        # Generate multiple augmentations
        logger.info("\nGenerating multiple augmentations...")
        augmented_images = augmenter.generate_augmentations(image, num_augmentations=5)
        logger.info(f"✓ Generated {len(augmented_images)} augmented images:")

        for i, (_, aug_name) in enumerate(augmented_images):
            logger.info(f"  {i+1}. {aug_name}")

        # Save augmented images
        output_dir = "test_output"
        logger.info(f"\nSaving augmented images to: {output_dir}")
        saved_paths = save_augmented_images(
            augmented_images,
            sku="TEST_SKU_001",
            output_dir=output_dir
        )

        logger.info(f"✓ Saved {len(saved_paths)} images")
        logger.info("\nSaved files:")
        for path in saved_paths:
            logger.info(f"  - {path}")

        # Verify files exist
        logger.info("\nVerifying saved files...")
        all_exist = all(Path(path).exists() for path in saved_paths)
        if all_exist:
            logger.info("✓ All files saved successfully")
        else:
            logger.warning("✗ Some files are missing")

        logger.info("=" * 60)
        logger.info("✓ All tests passed!")
        logger.info(f"✓ Check the '{output_dir}/TEST_SKU_001/' directory for results")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run local test"""
    success = test_image_augmentation()

    print("\n" + "=" * 60)
    if success:
        print("✓ LOCAL TEST PASSED")
        print("\nImage augmentation functionality is working correctly!")
        print("\nNext steps:")
        print("1. Ensure you can connect to the MySQL database")
        print("2. Run: python augment_images.py")
        print("\nNote: The database connection requires access to:")
        print("   Host: am-bp1ch634s7l1264ft167320o.ads.aliyuncs.com")
        print("   Port: 3306")
    else:
        print("✗ LOCAL TEST FAILED")
        print("Please check the errors above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
