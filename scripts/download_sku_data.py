#!/usr/bin/env python3
"""
Download SKU data and images from Shopline API
"""

import sys
import logging
from pathlib import Path
import argparse
from tqdm import tqdm
import yaml
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.shopline_client import ShoplineClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Download SKU data from Shopline')
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
        default=100,
        help='Batch size for API requests'
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Load config
    logger.info(f"Loading config from {args.config}")
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Initialize Shopline client
    logger.info("Initializing Shopline client")
    client = ShoplineClient(
        api_url=config['shopline']['api_url'],
        api_version=config['shopline']['api_version'],
    )

    # Fetch all products
    logger.info("Fetching products from Shopline")
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
        for sku_info in tqdm(all_sku_data, desc="Downloading images"):
            image_url = sku_info.get('image_url')
            if not image_url:
                continue

            sku = sku_info['sku']
            image_path = args.images_dir / f"{sku}.jpg"

            if image_path.exists():
                logger.debug(f"Image already exists: {image_path}")
                success_count += 1
                continue

            if client.download_image(image_url, image_path):
                success_count += 1

        logger.info(f"Downloaded {success_count}/{len(all_sku_data)} images")

    logger.info("✓ Data download completed successfully")


if __name__ == '__main__':
    main()
