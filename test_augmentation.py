"""
Simple test script to validate the image augmentation setup
"""
import asyncio
import logging
from image_config import image_settings
from image_augmentation import ImageAugmenter, ImageDownloader
from augment_images import ImageAugmentationPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test database connection"""
    logger.info("Testing database connection...")
    pipeline = ImageAugmentationPipeline()

    try:
        # Try to fetch a small amount of data
        async with pipeline.SessionLocal() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        return False
    finally:
        await pipeline.engine.dispose()


async def test_query():
    """Test the SKU query"""
    logger.info("Testing SKU query...")
    pipeline = ImageAugmentationPipeline()

    try:
        data = await pipeline.get_sku_data()
        logger.info(f"✓ Successfully fetched {len(data)} SKU records")

        if data:
            logger.info(f"Sample record: {data[0]}")

        return True
    except Exception as e:
        logger.error(f"✗ Query failed: {str(e)}")
        return False
    finally:
        await pipeline.engine.dispose()


async def test_augmentation():
    """Test image augmentation functions"""
    logger.info("Testing image augmentation...")

    try:
        augmenter = ImageAugmenter()
        logger.info("✓ ImageAugmenter initialized")

        # Test with a sample image download
        downloader = ImageDownloader()
        logger.info("✓ ImageDownloader initialized")

        logger.info("All augmentation components initialized successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Augmentation test failed: {str(e)}")
        return False


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Running Image Augmentation Tests")
    logger.info("=" * 60)

    # Test 1: Database connection
    test1 = await test_database_connection()

    # Test 2: Query
    test2 = await test_query()

    # Test 3: Augmentation setup
    test3 = await test_augmentation()

    # Summary
    logger.info("=" * 60)
    logger.info("Test Summary:")
    logger.info(f"  Database Connection: {'✓ PASS' if test1 else '✗ FAIL'}")
    logger.info(f"  SKU Query: {'✓ PASS' if test2 else '✗ FAIL'}")
    logger.info(f"  Augmentation Setup: {'✓ PASS' if test3 else '✗ FAIL'}")
    logger.info("=" * 60)

    if all([test1, test2, test3]):
        logger.info("✓ All tests passed! Ready to run augmentation.")
    else:
        logger.warning("✗ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
