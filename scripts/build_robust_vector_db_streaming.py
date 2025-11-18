#!/usr/bin/env python3
"""
Build a robust FAISS vector database with data augmentation
Streaming version to avoid memory issues
"""

import sys
import logging
from pathlib import Path
import argparse
import json
import yaml
from tqdm import tqdm
from dotenv import load_dotenv
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import random

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


def apply_light_augmentation(img, aug_type=None):
    """
    Apply light augmentation to simulate real-world conditions
    """
    if aug_type is None:
        brightness = random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)

        contrast = random.uniform(0.85, 1.15)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)

        angle = random.uniform(-10, 10)
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))

    elif aug_type == 0:
        brightness = random.uniform(0.7, 1.3)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)

    elif aug_type == 1:
        contrast = random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)

        color = random.uniform(0.9, 1.1)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(color)

    elif aug_type == 2:
        angle = random.uniform(-15, 15)
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))

    elif aug_type == 3:
        if random.random() > 0.5:
            img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

    elif aug_type == 4:
        width, height = img.size
        crop_factor = random.uniform(0.85, 0.95)
        new_width = int(width * crop_factor)
        new_height = int(height * crop_factor)
        left = random.randint(0, width - new_width)
        top = random.randint(0, height - new_height)
        img = img.crop((left, top, left + new_width, top + new_height))
        img = img.resize((width, height), Image.LANCZOS)

    return img


def main():
    parser = argparse.ArgumentParser(
        description='Build robust vector database with streaming processing'
    )
    parser.add_argument('--config', type=Path, default=Path('config/config.yaml'))
    parser.add_argument('--sku-data', type=Path, default=Path('data/raw/sku_data.json'))
    parser.add_argument('--images-dir', type=Path, default=Path('data/images'))
    parser.add_argument('--output-index', type=Path, default=Path('data/embeddings/faiss_index_robust.bin'))
    parser.add_argument('--output-metadata', type=Path, default=Path('data/embeddings/sku_metadata_robust.pkl'))
    parser.add_argument('--augment-per-image', type=int, default=2)
    parser.add_argument('--max-images', type=int, default=None)
    parser.add_argument('--chunk-size', type=int, default=100, help='Process images in chunks to save memory')

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

    if args.max_images:
        valid_skus = valid_skus[:args.max_images]
        image_paths = image_paths[:args.max_images]

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

    # Initialize vector database
    logger.info("Initializing vector database")
    faiss_config = config['faiss']
    vector_db = VectorDatabase(
        dimension=faiss_config.get('dimension', 768),
        index_type=faiss_config.get('index_type', 'IndexFlatL2'),
        metric='IP',
        nlist=faiss_config.get('nlist', 100),
    )

    # Process in chunks to avoid memory issues
    logger.info(f"Processing images in chunks of {args.chunk_size} (streaming mode)")

    total_embeddings = 0
    all_metadata = []

    for chunk_start in tqdm(range(0, len(valid_skus), args.chunk_size), desc="Processing chunks"):
        chunk_end = min(chunk_start + args.chunk_size, len(valid_skus))
        chunk_skus = valid_skus[chunk_start:chunk_end]
        chunk_paths = image_paths[chunk_start:chunk_end]

        # Process current chunk
        chunk_images = []
        chunk_metadata = []

        for img_path, sku_info in zip(chunk_paths, chunk_skus):
            try:
                # Load original image
                img = Image.open(img_path).convert('RGB')

                # Add original
                chunk_images.append(img.copy())
                chunk_metadata.append(sku_info)

                # Generate augmented versions
                if args.augment_per_image > 0:
                    for aug_idx in range(args.augment_per_image):
                        aug_type = aug_idx % 5
                        aug_img = apply_light_augmentation(img.copy(), aug_type=aug_type)

                        chunk_images.append(aug_img)

                        aug_metadata = sku_info.copy()
                        aug_metadata['augmented'] = True
                        aug_metadata['aug_index'] = aug_idx + 1
                        aug_metadata['aug_type'] = aug_type
                        chunk_metadata.append(aug_metadata)

            except Exception as e:
                logger.error(f"Error processing {img_path}: {e}")
                continue

        # Encode chunk
        if chunk_images:
            logger.info(f"Encoding chunk {chunk_start//args.chunk_size + 1}: {len(chunk_images)} images")
            embeddings_array = encoder.encode_images_batch(chunk_images, show_progress=False)

            # Add to database
            vector_db.add_embeddings(embeddings_array, chunk_metadata)
            all_metadata.extend(chunk_metadata)

            total_embeddings += len(embeddings_array)

            # Clear memory
            del chunk_images
            del embeddings_array

    logger.info(f"Generated {total_embeddings} embeddings total")
    logger.info(f"  - Original: {len(valid_skus)}")
    logger.info(f"  - Augmented: {total_embeddings - len(valid_skus)}")

    # Save database
    logger.info("Saving vector database")
    vector_db.save(args.output_index, args.output_metadata)

    # Print statistics
    stats = vector_db.get_stats()
    logger.info("Database statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    augmentation_ratio = (total_embeddings - len(valid_skus)) / len(valid_skus) * 100
    logger.info(f"Augmentation ratio: {augmentation_ratio:.1f}%")
    logger.info("✓ Robust vector database built successfully (streaming version)")


if __name__ == '__main__':
    main()
