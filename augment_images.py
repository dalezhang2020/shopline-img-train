"""
Main script for image augmentation from MySQL database
"""
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from image_config import image_settings
from image_augmentation import ImageAugmenter, ImageDownloader, save_augmented_images

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImageAugmentationPipeline:
    """Pipeline for processing SKU images from database"""

    def __init__(self):
        """Initialize the pipeline"""
        self.settings = image_settings
        self.augmenter = ImageAugmenter(
            brightness_range=self.settings.brightness_range,
            crop_ratio=self.settings.crop_ratio,
            noise_intensity=self.settings.noise_intensity
        )
        self.downloader = ImageDownloader()

        # Create async engine for MySQL
        self.engine = create_async_engine(
            self.settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )

        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Create output directory
        Path(self.settings.output_dir).mkdir(parents=True, exist_ok=True)

    async def get_sku_data(self) -> List[Dict]:
        """
        Fetch SKU data from MySQL database

        Returns:
            List of SKU records with image URLs
        """
        query = """
            SELECT SKU, ProductGroup, image_url
            FROM api_scm_skuinfo
            WHERE `ProductGroup` <> '**' AND `image_url` <> '**'
        """

        try:
            async with self.SessionLocal() as session:
                result = await session.execute(text(query))
                rows = result.fetchall()
                data = [
                    {
                        "SKU": row[0],
                        "ProductGroup": row[1],
                        "image_url": row[2]
                    }
                    for row in rows
                ]
                logger.info(f"Fetched {len(data)} SKU records from database")
                return data
        except Exception as e:
            logger.error(f"Error fetching SKU data: {str(e)}")
            raise

    async def process_single_sku(self, sku_data: Dict) -> Optional[Dict]:
        """
        Process a single SKU: download image and create augmentations

        Args:
            sku_data: Dictionary containing SKU, ProductGroup, and image_url

        Returns:
            Processing result dictionary or None if failed
        """
        sku = sku_data["SKU"]
        product_group = sku_data["ProductGroup"]
        image_url = sku_data["image_url"]

        logger.info(f"Processing SKU: {sku}")

        try:
            # Download original image
            original_image = await self.downloader.download_image(image_url)
            if original_image is None:
                logger.warning(f"Failed to download image for SKU: {sku}")
                return None

            # Generate augmented images
            augmented_images = self.augmenter.generate_augmentations(
                original_image,
                num_augmentations=self.settings.augmentations_per_image
            )

            # Save augmented images
            saved_paths = save_augmented_images(
                augmented_images,
                sku,
                self.settings.output_dir
            )

            result = {
                "SKU": sku,
                "ProductGroup": product_group,
                "original_url": image_url,
                "augmented_count": len(saved_paths),
                "saved_paths": saved_paths,
                "status": "success"
            }

            logger.info(f"Successfully processed SKU: {sku} ({len(saved_paths)} images)")
            return result

        except Exception as e:
            logger.error(f"Error processing SKU {sku}: {str(e)}")
            return {
                "SKU": sku,
                "ProductGroup": product_group,
                "status": "failed",
                "error": str(e)
            }

    async def process_batch(self, sku_batch: List[Dict]) -> List[Dict]:
        """
        Process a batch of SKUs concurrently

        Args:
            sku_batch: List of SKU data dictionaries

        Returns:
            List of processing results
        """
        tasks = [self.process_single_sku(sku_data) for sku_data in sku_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception during processing: {str(result)}")
            elif result is not None:
                valid_results.append(result)

        return valid_results

    async def run(self, limit: Optional[int] = None):
        """
        Run the image augmentation pipeline

        Args:
            limit: Optional limit on number of SKUs to process
        """
        start_time = datetime.now()
        logger.info("Starting image augmentation pipeline...")

        try:
            # Fetch SKU data
            sku_data = await self.get_sku_data()

            if limit:
                sku_data = sku_data[:limit]
                logger.info(f"Processing limited to {limit} SKUs")

            total_skus = len(sku_data)
            logger.info(f"Total SKUs to process: {total_skus}")

            # Process in batches
            all_results = []
            batch_size = self.settings.batch_size

            for i in range(0, total_skus, batch_size):
                batch = sku_data[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (total_skus + batch_size - 1) // batch_size

                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} SKUs)")

                batch_results = await self.process_batch(batch)
                all_results.extend(batch_results)

                # Log batch statistics
                success_count = sum(1 for r in batch_results if r.get("status") == "success")
                logger.info(f"Batch {batch_num} completed: {success_count}/{len(batch)} successful")

            # Final statistics
            end_time = datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()

            success_count = sum(1 for r in all_results if r.get("status") == "success")
            failed_count = len(all_results) - success_count
            total_images = sum(r.get("augmented_count", 0) for r in all_results)

            logger.info("=" * 60)
            logger.info("Image Augmentation Pipeline Completed")
            logger.info(f"Total SKUs processed: {len(all_results)}")
            logger.info(f"Successful: {success_count}")
            logger.info(f"Failed: {failed_count}")
            logger.info(f"Total augmented images: {total_images}")
            logger.info(f"Output directory: {self.settings.output_dir}")
            logger.info(f"Execution time: {elapsed_time:.2f} seconds")
            logger.info("=" * 60)

            return all_results

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            raise
        finally:
            await self.engine.dispose()


async def main():
    """Main entry point"""
    pipeline = ImageAugmentationPipeline()

    # You can set a limit for testing, e.g., limit=10
    # Remove limit parameter to process all SKUs
    await pipeline.run(limit=None)


if __name__ == "__main__":
    asyncio.run(main())
