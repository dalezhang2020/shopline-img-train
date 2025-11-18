#!/usr/bin/env python3
"""
Build a robust FAISS vector database with data augmentation
for improved mobile photography recognition
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
from PIL import Image, ImageEnhance
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
    This is applied ON-THE-FLY during encoding, not saved to disk

    Args:
        img: PIL Image
        aug_type: Type of augmentation (0-4), if None will apply random mix
    """
    from PIL import ImageFilter

    if aug_type is None:
        # Random mix of augmentations
        brightness = random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)

        contrast = random.uniform(0.85, 1.15)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)

        angle = random.uniform(-10, 10)
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))

    elif aug_type == 0:
        # Type 0: Brightness adjustment
        brightness = random.uniform(0.7, 1.3)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)

    elif aug_type == 1:
        # Type 1: Contrast + Color adjustment
        contrast = random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)

        color = random.uniform(0.9, 1.1)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(color)

    elif aug_type == 2:
        # Type 2: Rotation
        angle = random.uniform(-15, 15)
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))

    elif aug_type == 3:
        # Type 3: Slight blur (simulate motion or focus issues)
        if random.random() > 0.5:
            img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

    elif aug_type == 4:
        # Type 4: Crop and zoom (simulate different distances)
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
        description='Build robust vector database with augmentation'
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
        help='Directory containing SKU images'
    )
    parser.add_argument(
        '--output-index',
        type=Path,
        default=Path('data/embeddings/faiss_index_robust.bin'),
        help='Output path for FAISS index'
    )
    parser.add_argument(
        '--output-metadata',
        type=Path,
        default=Path('data/embeddings/sku_metadata_robust.pkl'),
        help='Output path for metadata'
    )
    parser.add_argument(
        '--augment-per-image',
        type=int,
        default=2,
        help='Number of augmented versions per image (0 = no augmentation)'
    )
    parser.add_argument(
        '--max-images',
        type=int,
        default=None,
        help='Maximum number of images to process (for testing)'
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

    if args.max_images:
        valid_skus = valid_skus[:args.max_images]
        image_paths = image_paths[:args.max_images]
        logger.info(f"Limited to {args.max_images} images (test mode)")

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

    # Encode images with augmentation
    logger.info(f"Encoding images with CLIP (with {args.augment_per_image} augmentations per image)")

    all_embeddings = []
    all_metadata = []

    for idx, (img_path, sku_info) in enumerate(tqdm(
        zip(image_paths, valid_skus),
        total=len(image_paths),
        desc="Encoding images"
    )):
        try:
            # Original image
            embeddings = encoder.encode_image_paths([img_path], show_progress=False)
            all_embeddings.append(embeddings[0])
            all_metadata.append(sku_info)

            # Augmented versions
            if args.augment_per_image > 0:
                img = Image.open(img_path).convert('RGB')

                for aug_idx in range(args.augment_per_image):
                    # Apply specific augmentation type (cycling through 0-4 for 5 types)
                    # If augment_per_image <= 5, each gets a unique type
                    # If augment_per_image > 5, types repeat
                    aug_type = aug_idx % 5
                    aug_img = apply_light_augmentation(img.copy(), aug_type=aug_type)

                    # Encode augmented image
                    # Note: encode_image expects PIL Image or numpy array
                    aug_embedding = encoder.encode_image(aug_img)
                    all_embeddings.append(aug_embedding)

                    # Add metadata with augmentation flag
                    aug_metadata = sku_info.copy()
                    aug_metadata['augmented'] = True
                    aug_metadata['aug_index'] = aug_idx + 1
                    aug_metadata['aug_type'] = aug_type
                    all_metadata.append(aug_metadata)

        except Exception as e:
            logger.error(f"Error encoding {img_path}: {e}")
            continue

    # Convert to numpy array
    embeddings_array = np.vstack(all_embeddings)

    logger.info(f"Generated {len(all_embeddings)} embeddings total")
    logger.info(f"  - Original: {len(valid_skus)}")
    logger.info(f"  - Augmented: {len(all_embeddings) - len(valid_skus)}")

    # Initialize vector database
    logger.info("Building vector database")
    faiss_config = config['faiss']
    vector_db = VectorDatabase(
        dimension=faiss_config.get('dimension', 768),
        index_type=faiss_config.get('index_type', 'IndexFlatL2'),
        metric='IP',  # Use inner product for cosine similarity
        nlist=faiss_config.get('nlist', 100),
    )

    # Add embeddings to database
    vector_db.add_embeddings(embeddings_array, all_metadata)

    # Save database
    logger.info("Saving vector database")
    vector_db.save(args.output_index, args.output_metadata)

    # Print statistics
    stats = vector_db.get_stats()
    logger.info("Database statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    augmentation_ratio = (len(all_embeddings) - len(valid_skus)) / len(valid_skus) * 100
    logger.info(f"Augmentation ratio: {augmentation_ratio:.1f}%")
    logger.info("✓ Robust vector database built successfully")


if __name__ == '__main__':
    main()
