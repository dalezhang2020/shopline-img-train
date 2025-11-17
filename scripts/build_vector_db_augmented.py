#!/usr/bin/env python3
"""
Build FAISS vector database from SKU images (including augmented images)
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
    parser = argparse.ArgumentParser(
        description='Build vector database from SKU images (with augmentation support)'
    )
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
        help='Directory containing original SKU images'
    )
    parser.add_argument(
        '--augmented-dir',
        type=Path,
        default=Path('data/augmented'),
        help='Directory containing augmented images'
    )
    parser.add_argument(
        '--use-augmented',
        action='store_true',
        default=True,
        help='Include augmented images in database (default: True)'
    )
    parser.add_argument(
        '--original-only',
        action='store_false',
        dest='use_augmented',
        help='Use only original images, skip augmented'
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

    # Prepare image paths and metadata
    all_image_paths = []
    all_metadata = []

    for sku_info in tqdm(sku_data, desc="Preparing image list"):
        sku = sku_info['sku']
        safe_sku = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in sku)

        # Check for original image
        original_path = args.images_dir / f"{safe_sku}.jpg"

        if original_path.exists():
            all_image_paths.append(original_path)
            metadata = sku_info.copy()
            metadata['image_type'] = 'original'
            metadata['image_path'] = str(original_path)
            all_metadata.append(metadata)

            # Check for augmented images if enabled
            if args.use_augmented and args.augmented_dir.exists():
                # Find all augmented images for this SKU
                augmented_pattern = f"{safe_sku}_*.jpg"
                augmented_images = list(args.augmented_dir.glob(augmented_pattern))

                for aug_path in augmented_images:
                    all_image_paths.append(aug_path)
                    aug_metadata = sku_info.copy()
                    aug_metadata['image_type'] = 'augmented'
                    aug_metadata['image_path'] = str(aug_path)
                    aug_metadata['augmentation'] = aug_path.stem.replace(f"{safe_sku}_", "")
                    all_metadata.append(aug_metadata)

        else:
            logger.debug(f"Image not found for SKU: {sku}")

    logger.info(f"Found {len(all_image_paths)} total images:")
    original_count = sum(1 for m in all_metadata if m['image_type'] == 'original')
    augmented_count = sum(1 for m in all_metadata if m['image_type'] == 'augmented')
    logger.info(f"  - Original: {original_count}")
    logger.info(f"  - Augmented: {augmented_count}")

    if len(all_image_paths) == 0:
        logger.error("No images found. Exiting.")
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
    embeddings = encoder.encode_image_paths(all_image_paths, show_progress=True)

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
    vector_db.add_embeddings(embeddings, all_metadata)

    # Save database
    logger.info("Saving vector database")
    vector_db.save(args.output_index, args.output_metadata)

    # Print statistics
    stats = vector_db.get_stats()
    logger.info("\n" + "=" * 80)
    logger.info("DATABASE STATISTICS")
    logger.info("=" * 80)
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    logger.info(f"  Original images: {original_count}")
    logger.info(f"  Augmented images: {augmented_count}")
    logger.info(f"  Augmentation ratio: {augmented_count/original_count:.1f}x" if original_count > 0 else "  Augmentation ratio: N/A")
    logger.info("=" * 80)

    logger.info("✓ Vector database built successfully")


if __name__ == '__main__':
    main()
