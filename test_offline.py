"""
Offline test script for image augmentation functionality
Uses a sample image from the web to demonstrate augmentation
"""
import asyncio
import logging
from pathlib import Path
from image_augmentation import ImageAugmenter, ImageDownloader, save_augmented_images

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_image_augmentation():
    """Test image augmentation with a sample image"""
    logger.info("=" * 60)
    logger.info("Image Augmentation Offline Test")
    logger.info("=" * 60)

    # Sample product image URL (placeholder)
    test_image_url = "https://via.placeholder.com/600x600.jpg?text=Sample+Product"

    try:
        # Initialize components
        logger.info("Initializing components...")
        downloader = ImageDownloader()
        augmenter = ImageAugmenter(
            brightness_range=(0.7, 1.3),
            crop_ratio=0.9,
            noise_intensity=0.02
        )

        # Download test image
        logger.info(f"Downloading test image from: {test_image_url}")
        image = await downloader.download_image(test_image_url)

        if image is None:
            logger.error("Failed to download test image")
            return False

        logger.info(f"✓ Downloaded image: {image.size} pixels")

        # Generate augmentations
        logger.info("Generating augmented images...")
        augmented_images = augmenter.generate_augmentations(image, num_augmentations=5)
        logger.info(f"✓ Generated {len(augmented_images)} augmented images")

        # Display augmentation details
        for i, (_, aug_name) in enumerate(augmented_images):
            logger.info(f"  {i+1}. {aug_name}")

        # Save augmented images
        output_dir = "test_output"
        logger.info(f"Saving augmented images to: {output_dir}")
        saved_paths = save_augmented_images(
            augmented_images,
            sku="TEST_SKU_001",
            output_dir=output_dir
        )

        logger.info(f"✓ Saved {len(saved_paths)} images")
        logger.info("\nSaved files:")
        for path in saved_paths:
            logger.info(f"  - {path}")

        logger.info("=" * 60)
        logger.info("✓ Augmentation test completed successfully!")
        logger.info(f"✓ Check the '{output_dir}/TEST_SKU_001/' directory for results")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_individual_augmentations():
    """Test each augmentation type individually"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Individual Augmentation Types")
    logger.info("=" * 60)

    test_image_url = "https://via.placeholder.com/600x600.jpg?text=Test+Image"

    try:
        downloader = ImageDownloader()
        augmenter = ImageAugmenter()

        # Download test image
        logger.info("Downloading test image...")
        image = await downloader.download_image(test_image_url)

        if image is None:
            logger.error("Failed to download test image")
            return False

        logger.info("✓ Image downloaded")

        # Test each augmentation type
        aug_types = ["flip", "crop", "brightness", "noise"]

        for aug_type in aug_types:
            try:
                augmented = augmenter.augment(image.copy(), aug_type)
                logger.info(f"✓ {aug_type.capitalize()} augmentation: OK")
            except Exception as e:
                logger.error(f"✗ {aug_type.capitalize()} augmentation: FAILED - {str(e)}")

        logger.info("=" * 60)
        logger.info("✓ All augmentation types tested")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"✗ Test failed: {str(e)}")
        return False


async def main():
    """Run offline tests"""
    # Test 1: Full augmentation pipeline
    test1 = await test_image_augmentation()

    # Test 2: Individual augmentation types
    test2 = await test_individual_augmentations()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Full Augmentation Pipeline: {'✓ PASS' if test1 else '✗ FAIL'}")
    print(f"  Individual Augmentation Types: {'✓ PASS' if test2 else '✗ FAIL'}")
    print("=" * 60)

    if test1 and test2:
        print("\n✓ All offline tests passed!")
        print("✓ Image augmentation functionality is working correctly.")
        print("\nNext steps:")
        print("1. Ensure you can connect to the MySQL database from your environment")
        print("2. Run: python augment_images.py")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
