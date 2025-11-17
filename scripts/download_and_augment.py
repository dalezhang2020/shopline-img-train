#!/usr/bin/env python3
"""
Download SKU data from api_scm_skuinfo table and apply image augmentation
"""

import sys
import logging
import os
import asyncio
from pathlib import Path
import argparse
from tqdm import tqdm
import yaml
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.mysql_client import MySQLClient
from src.utils.augmentation import ImageAugmenter, ImageDownloader, save_augmented_images

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SKUImageProcessor:
    """Processor for SKU images with augmentation"""

    def __init__(
        self,
        mysql_client: MySQLClient,
        output_dir: Path,
        augmented_dir: Path,
        enable_augmentation: bool = True,
        num_augmentations: int = 5,
    ):
        """
        Initialize SKU image processor

        Args:
            mysql_client: MySQL client instance
            output_dir: Directory for original images
            augmented_dir: Directory for augmented images
            enable_augmentation: Whether to enable image augmentation
            num_augmentations: Number of augmentations per image
        """
        self.client = mysql_client
        self.output_dir = Path(output_dir)
        self.augmented_dir = Path(augmented_dir)
        self.enable_augmentation = enable_augmentation
        self.num_augmentations = num_augmentations

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.enable_augmentation:
            self.augmented_dir.mkdir(parents=True, exist_ok=True)

        # Initialize augmenter and downloader
        self.augmenter = ImageAugmenter(
            brightness_range=(0.7, 1.3),
            contrast_range=(0.8, 1.2),
            crop_ratio=0.9,
            noise_intensity=0.02,
        )
        self.downloader = ImageDownloader()

    async def process_single_sku(self, sku_data: dict) -> dict:
        """
        Process a single SKU: download image and create augmentations

        Args:
            sku_data: SKU data dictionary

        Returns:
            Processing result dictionary
        """
        sku = sku_data['sku']
        image_url = sku_data['image_url']
        category = sku_data.get('category', 'UNKNOWN')

        logger.info(f"Processing SKU: {sku} ({category})")

        try:
            # Download original image
            original_image = await self.downloader.download_image(image_url)
            if original_image is None:
                logger.warning(f"Failed to download image for SKU: {sku}")
                return {
                    'sku': sku,
                    'status': 'failed',
                    'error': 'Image download failed'
                }

            # Save original image
            safe_sku = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in sku)
            original_path = self.output_dir / f"{safe_sku}.jpg"
            original_image.save(original_path, "JPEG", quality=95)

            result = {
                'sku': sku,
                'category': category,
                'original_path': str(original_path),
                'original_url': image_url,
                'status': 'success',
                'augmented_count': 0,
                'augmented_paths': []
            }

            # Generate augmented images if enabled
            if self.enable_augmentation:
                augmented_images = self.augmenter.generate_augmentations(
                    original_image,
                    num_augmentations=self.num_augmentations
                )

                # Save augmented images
                augmented_paths = save_augmented_images(
                    augmented_images,
                    sku,
                    self.augmented_dir
                )

                result['augmented_count'] = len(augmented_paths)
                result['augmented_paths'] = [str(p) for p in augmented_paths]

                logger.info(
                    f"Successfully processed SKU: {sku} "
                    f"(1 original + {len(augmented_paths)} augmented)"
                )
            else:
                logger.info(f"Successfully downloaded image for SKU: {sku}")

            return result

        except Exception as e:
            logger.error(f"Error processing SKU {sku}: {e}")
            return {
                'sku': sku,
                'status': 'failed',
                'error': str(e)
            }

    async def process_batch(self, sku_batch: list) -> list:
        """
        Process a batch of SKUs concurrently

        Args:
            sku_batch: List of SKU data dictionaries

        Returns:
            List of processing results
        """
        tasks = [self.process_single_sku(sku_data) for sku_data in sku_batch]
        results = await asyncio.gather(*tasks)
        return results

    async def process_all_skus(self, sku_data_list: list, batch_size: int = 10) -> dict:
        """
        Process all SKUs in batches

        Args:
            sku_data_list: List of all SKU data
            batch_size: Number of SKUs to process concurrently

        Returns:
            Summary dictionary with statistics
        """
        total_skus = len(sku_data_list)
        logger.info(f"Processing {total_skus} SKUs in batches of {batch_size}")

        all_results = []
        success_count = 0
        failed_count = 0

        # Process in batches with progress bar
        for i in tqdm(range(0, total_skus, batch_size), desc="Processing batches"):
            batch = sku_data_list[i:i + batch_size]
            batch_results = await self.process_batch(batch)
            all_results.extend(batch_results)

            # Count successes and failures
            for result in batch_results:
                if result['status'] == 'success':
                    success_count += 1
                else:
                    failed_count += 1

        # Calculate total images
        total_original = success_count
        total_augmented = sum(
            r.get('augmented_count', 0)
            for r in all_results
            if r['status'] == 'success'
        )

        summary = {
            'total_skus': total_skus,
            'success_count': success_count,
            'failed_count': failed_count,
            'total_original_images': total_original,
            'total_augmented_images': total_augmented,
            'total_images': total_original + total_augmented,
            'results': all_results
        }

        return summary


async def main_async(args):
    """Async main function"""

    # Load environment variables
    load_dotenv()

    # Load config
    logger.info(f"Loading config from {args.config}")
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Get MySQL credentials
    mysql_config = config.get('mysql', {})
    host = os.getenv('MYSQL_HOST', mysql_config.get('host', 'localhost'))
    database = os.getenv('MYSQL_DATABASE', mysql_config.get('database'))
    user = os.getenv('MYSQL_USER', mysql_config.get('user'))
    password = os.getenv('MYSQL_PASSWORD', mysql_config.get('password'))
    port = int(os.getenv('MYSQL_PORT', mysql_config.get('port', 3306)))

    if not all([database, user, password]):
        logger.error("MySQL credentials not configured. Please set MYSQL_* environment variables.")
        sys.exit(1)

    # Initialize MySQL client
    logger.info(f"Connecting to MySQL database: {host}:{port}/{database}")
    client = MySQLClient(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port,
    )

    try:
        # Connect to database
        client.connect()

        # Fetch SKU data from api_scm_skuinfo table
        logger.info("Fetching SKU data from api_scm_skuinfo table")
        sku_data_list = client.get_sku_from_scm_table()

        if not sku_data_list:
            logger.warning("No SKU data found in database")
            return

        logger.info(f"Retrieved {len(sku_data_list)} SKUs from database")

        # Save SKU metadata
        metadata_path = args.output_dir / 'sku_data.json'
        client.save_sku_data(sku_data_list, metadata_path)

        # Initialize processor
        processor = SKUImageProcessor(
            mysql_client=client,
            output_dir=args.images_dir,
            augmented_dir=args.augmented_dir,
            enable_augmentation=args.enable_augmentation,
            num_augmentations=args.num_augmentations,
        )

        # Process all SKUs
        summary = await processor.process_all_skus(
            sku_data_list,
            batch_size=args.batch_size
        )

        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("PROCESSING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total SKUs: {summary['total_skus']}")
        logger.info(f"Successful: {summary['success_count']}")
        logger.info(f"Failed: {summary['failed_count']}")
        logger.info(f"Original images: {summary['total_original_images']}")
        logger.info(f"Augmented images: {summary['total_augmented_images']}")
        logger.info(f"Total images: {summary['total_images']}")
        logger.info("=" * 80)

        # Save summary
        import json
        summary_path = args.output_dir / 'processing_summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"Summary saved to {summary_path}")

        logger.info("✓ Processing completed successfully")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise

    finally:
        # Disconnect from database
        client.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description='Download SKU images from MySQL and apply augmentation'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config/config.yaml'),
        help='Path to config file'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/raw'),
        help='Output directory for metadata'
    )
    parser.add_argument(
        '--images-dir',
        type=Path,
        default=Path('data/images'),
        help='Output directory for original images'
    )
    parser.add_argument(
        '--augmented-dir',
        type=Path,
        default=Path('data/augmented'),
        help='Output directory for augmented images'
    )
    parser.add_argument(
        '--enable-augmentation',
        action='store_true',
        default=True,
        help='Enable image augmentation (default: True)'
    )
    parser.add_argument(
        '--no-augmentation',
        action='store_false',
        dest='enable_augmentation',
        help='Disable image augmentation'
    )
    parser.add_argument(
        '--num-augmentations',
        type=int,
        default=5,
        help='Number of augmented images per original (default: 5)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for concurrent processing (default: 10)'
    )

    args = parser.parse_args()

    # Run async main
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
