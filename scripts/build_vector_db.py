#!/usr/bin/env python3
"""
Build FAISS vector database from SKU images
"""

import sys
import logging
from pathlib import Path
import argparse
import json
import yaml
from tqdm import tqdm
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.clip_encoder import CLIPEncoder
from src.database.vector_db import VectorDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Build vector database from SKU images')
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config/config.yaml'),
        help='Path to config file'
    )
    parser.add_argument(
        '--sku-data',
        type=Path,
        default=Path('data/raw/sku_data.json'),
        help='Path to SKU data JSON'
    )
    parser.add_argument(
        '--images-dir',
        type=Path,
        default=Path('data/images'),
        help='Directory containing SKU images'
    )
    parser.add_argument(
        '--output-index',
        type=Path,
        default=Path('data/embeddings/faiss_index.bin'),
        help='Output path for FAISS index'
    )
    parser.add_argument(
        '--output-metadata',
        type=Path,
        default=Path('data/embeddings/sku_metadata.pkl'),
        help='Output path for metadata'
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Load config
    logger.info(f"Loading config from {args.config}")
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Load SKU data
    logger.info(f"Loading SKU data from {args.sku_data}")
    with open(args.sku_data, 'r') as f:
        sku_data = json.load(f)

    logger.info(f"Loaded {len(sku_data)} SKU records")

    # Filter SKUs with images
    valid_skus = []
    image_paths = []

    for sku_info in sku_data:
        sku = sku_info['sku']
        image_path = args.images_dir / f"{sku}.jpg"

        if image_path.exists():
            valid_skus.append(sku_info)
            image_paths.append(image_path)
        else:
            logger.debug(f"Image not found for SKU: {sku}")

    logger.info(f"Found {len(valid_skus)} SKUs with images")

    if len(valid_skus) == 0:
        logger.error("No valid SKUs with images found. Exiting.")
        sys.exit(1)

    # Initialize CLIP encoder
    logger.info("Initializing CLIP encoder")
    clip_config = config['clip']
    encoder = CLIPEncoder(
        model_name=clip_config['model_name'],
        pretrained=clip_config['pretrained'],
        device=clip_config.get('device'),
        batch_size=clip_config.get('batch_size', 32),
    )

    # Encode images
    logger.info("Encoding images with CLIP")
    embeddings = encoder.encode_image_paths(image_paths, show_progress=True)

    logger.info(f"Generated {len(embeddings)} embeddings")

    # Initialize vector database
    logger.info("Building vector database")
    faiss_config = config['faiss']
    vector_db = VectorDatabase(
        dimension=faiss_config.get('dimension', 512),
        index_type=faiss_config.get('index_type', 'IndexFlatL2'),
        metric='IP',  # Use inner product for cosine similarity
        nlist=faiss_config.get('nlist', 100),
    )

    # Add embeddings to database
    vector_db.add_embeddings(embeddings, valid_skus)

    # Save database
    logger.info("Saving vector database")
    vector_db.save(args.output_index, args.output_metadata)

    # Print statistics
    stats = vector_db.get_stats()
    logger.info("Database statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    logger.info("✓ Vector database built successfully")


if __name__ == '__main__':
    main()
