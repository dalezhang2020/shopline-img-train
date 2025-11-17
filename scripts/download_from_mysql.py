#!/usr/bin/env python3
"""
Download SKU data and images from MySQL database
"""

import sys
import logging
import os
from pathlib import Path
import argparse
from tqdm import tqdm
import yaml
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.mysql_client import MySQLClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Download SKU data from MySQL database')
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
        help='Output directory for data'
    )
    parser.add_argument(
        '--images-dir',
        type=Path,
        default=Path('data/images'),
        help='Output directory for images'
    )
    parser.add_argument(
        '--download-images',
        action='store_true',
        help='Download product images'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for database queries'
    )
    parser.add_argument(
        '--use-optimized-query',
        action='store_true',
        help='Use optimized single query to fetch all SKUs (faster)'
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Load config
    logger.info(f"Loading config from {args.config}")
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Get MySQL credentials from environment
    mysql_config = config.get('mysql', {})
    host = os.getenv('MYSQL_HOST', mysql_config.get('host', 'localhost'))
    database = os.getenv('MYSQL_DATABASE', mysql_config.get('database'))
    user = os.getenv('MYSQL_USER', mysql_config.get('user'))
    password = os.getenv('MYSQL_PASSWORD', mysql_config.get('password'))
    port = int(os.getenv('MYSQL_PORT', mysql_config.get('port', 3306)))

    if not all([database, user, password]):
        logger.error("MySQL credentials not configured. Please set MYSQL_* environment variables or config file.")
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

        # Print database statistics
        stats = client.get_stats()
        logger.info("Database statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")

        # Fetch SKU data
        if args.use_optimized_query:
            # Use optimized single query (faster)
            logger.info("Fetching all SKUs with optimized query")
            all_sku_data = client.get_sku_with_images()

        else:
            # Fetch products then variants (more flexible but slower)
            logger.info("Fetching products from database")
            categories = config.get('categories')

            products = client.get_all_products(
                categories=categories,
                batch_size=args.batch_size,
            )

            logger.info(f"Fetched {len(products)} products")

            # Extract SKU data
            logger.info("Extracting SKU data")
            all_sku_data = []

            for product in tqdm(products, desc="Processing products"):
                sku_data = client.extract_sku_data(product)
                all_sku_data.extend(sku_data)

        logger.info(f"Extracted {len(all_sku_data)} SKU records")

        # Save SKU data
        output_path = args.output_dir / 'sku_data.json'
        client.save_sku_data(all_sku_data, output_path)

        # Download images if requested
        if args.download_images:
            logger.info("Downloading product images")
            args.images_dir.mkdir(parents=True, exist_ok=True)

            success_count = 0
            failed_urls = []

            for sku_info in tqdm(all_sku_data, desc="Downloading images"):
                image_url = sku_info.get('image_url')
                if not image_url:
                    logger.debug(f"No image URL for SKU: {sku_info['sku']}")
                    continue

                sku = sku_info['sku']
                # Sanitize SKU for filename
                safe_sku = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in sku)
                image_path = args.images_dir / f"{safe_sku}.jpg"

                if image_path.exists():
                    logger.debug(f"Image already exists: {image_path}")
                    success_count += 1
                    continue

                if client.download_image(image_url, image_path):
                    success_count += 1
                else:
                    failed_urls.append(image_url)

            logger.info(f"Downloaded {success_count}/{len(all_sku_data)} images")

            if failed_urls:
                logger.warning(f"Failed to download {len(failed_urls)} images")
                # Save failed URLs for retry
                failed_path = args.output_dir / 'failed_downloads.txt'
                with open(failed_path, 'w') as f:
                    f.write('\n'.join(failed_urls))
                logger.info(f"Failed URLs saved to {failed_path}")

        logger.info("✓ Data download completed successfully")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise

    finally:
        # Disconnect from database
        client.disconnect()


if __name__ == '__main__':
    main()
