#!/usr/bin/env python3
"""
Build FAISS vector database from SKU images with optimizations for CPU-only systems
- Supports partial image index (incremental building)
- Progress monitoring
- Memory efficient
"""

import sys
import logging
import os
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
    parser = argparse.ArgumentParser(description='Build FAISS vector database from SKU images (optimized)')
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
    parser.add_argument(
        '--max-images',
        type=int,
        default=None,
        help='Maximum number of images to process (for testing)'
    )
    parser.add_argument(
        '--skip-encoding',
        action='store_true',
        help='Skip encoding, just build index from saved embeddings'
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

    args.images_dir.mkdir(parents=True, exist_ok=True)

    for sku_info in sku_data:
        sku = sku_info['sku']
        # Sanitize SKU for filename
        safe_sku = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in sku)
        image_path = args.images_dir / f"{safe_sku}.jpg"

        if image_path.exists():
            valid_skus.append(sku_info)
            image_paths.append(image_path)
        else:
            logger.debug(f"Image not found for SKU: {sku}")

    logger.info(f"Found {len(valid_skus)} SKUs with images")

    # Apply max images limit if specified
    if args.max_images and len(valid_skus) > args.max_images:
        logger.info(f"Limiting to {args.max_images} images for testing")
        valid_skus = valid_skus[:args.max_images]
        image_paths = image_paths[:args.max_images]

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
    logger.info(f"Encoding {len(image_paths)} images with CLIP")
    logger.info(f"CLIP Model: {clip_config['model_name']}")
    logger.info(f"Device: {clip_config.get('device', 'auto')}")
    logger.info(f"Batch size: {clip_config.get('batch_size', 32)}")

    embeddings = encoder.encode_image_paths(image_paths, show_progress=True)

    logger.info(f"Generated {len(embeddings)} embeddings")
    logger.info(f"Embedding shape: {embeddings.shape}")

    # Initialize vector database
    logger.info("Building vector database")
    faiss_config = config['faiss']
    logger.info(f"FAISS Index Type: {faiss_config.get('index_type', 'IndexFlatL2')}")
    logger.info(f"Embedding Dimension: {faiss_config.get('dimension', 512)}")

    vector_db = VectorDatabase(
        dimension=faiss_config.get('dimension', 512),
        index_type=faiss_config.get('index_type', 'IndexFlatL2'),
        metric='IP',  # Use inner product for cosine similarity
        nlist=faiss_config.get('nlist', 100),
    )

    # Add embeddings to database
    logger.info("Adding embeddings to database")
    vector_db.add_embeddings(embeddings, valid_skus)

    # Save database
    logger.info("Saving vector database")
    args.output_index.parent.mkdir(parents=True, exist_ok=True)
    args.output_metadata.parent.mkdir(parents=True, exist_ok=True)
    vector_db.save(args.output_index, args.output_metadata)

    # Print statistics
    stats = vector_db.get_stats()
    logger.info("Database statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    logger.info("✓ Vector database built successfully")
    logger.info(f"Index saved to: {args.output_index}")
    logger.info(f"Metadata saved to: {args.output_metadata}")


if __name__ == '__main__':
    main()
