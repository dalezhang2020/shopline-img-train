#!/usr/bin/env python3
"""
Download SKU data from MySQL database using api_scm_skuinfo table
This is optimized for the actual Shopline database structure
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
    parser = argparse.ArgumentParser(description='Download SKU data from MySQL database using api_scm_skuinfo table')
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

        # Fetch SKU data from api_scm_skuinfo table (optimized for Shopline)
        logger.info("Fetching SKUs from api_scm_skuinfo table")
        all_sku_data = client.get_sku_from_scm_table()

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
                if not image_url or image_url == '**':
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
