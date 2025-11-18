#!/usr/bin/env python3
"""
Test SKU matching on a single image
"""

import sys
import logging
from pathlib import Path
import yaml
import pickle
import numpy as np
from dotenv import load_dotenv
from PIL import Image

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


def load_metadata(metadata_path):
    """Load FAISS metadata"""
    with open(metadata_path, 'rb') as f:
        data = pickle.load(f)
    return data['metadata']


def test_single_image(image_path, top_k=10):
    """Test SKU matching on a single image"""

    image_path = Path(image_path)
    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return

    # Load config
    config_path = Path('config/config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    logger.info("=" * 100)
    logger.info(f"SKU MATCHING TEST - Single Image: {image_path.name}")
    logger.info("=" * 100)

    # Initialize CLIP encoder
    logger.info("\n1️⃣  Initializing CLIP encoder (ViT-L/14)...")
    clip_config = config['clip']
    encoder = CLIPEncoder(
        model_name=clip_config['model_name'],
        pretrained=clip_config['pretrained'],
        device=clip_config.get('device', 'cpu'),
        batch_size=clip_config.get('batch_size', 32),
    )
    logger.info(f"   ✓ CLIP encoder loaded")

    # Load vector database
    logger.info(f"\n2️⃣  Loading FAISS vector database...")
    index_path = Path('data/embeddings/faiss_index.bin')
    metadata_path = Path('data/embeddings/sku_metadata.pkl')

    faiss_config = config['faiss']
    vector_db = VectorDatabase(
        dimension=faiss_config.get('dimension', 768),
        index_type=faiss_config.get('index_type', 'IndexFlatL2'),
        metric='IP',
    )

    vector_db.load(index_path, metadata_path)
    stats = vector_db.get_stats()
    logger.info(f"   ✓ Database loaded: {stats['total_embeddings']} embeddings")

    # Load and display image info
    logger.info(f"\n3️⃣  Loading test image...")
    try:
        img = Image.open(image_path)
        logger.info(f"   Image: {image_path.name}")
        logger.info(f"   Size: {img.size} ({img.width}x{img.height})")
        logger.info(f"   Mode: {img.mode}")
    except Exception as e:
        logger.error(f"   ❌ Error loading image: {e}")
        return

    # Encode the image
    logger.info(f"\n4️⃣  Encoding image with CLIP...")
    try:
        embeddings = encoder.encode_image_paths([image_path], show_progress=False)
        image_embedding = embeddings[0]

        # Normalize for cosine similarity
        image_embedding = image_embedding / np.linalg.norm(image_embedding)
        image_embedding = image_embedding.reshape(1, -1).astype(np.float32)

        logger.info(f"   ✓ Image encoded (embedding dimension: {image_embedding.shape[1]})")
    except Exception as e:
        logger.error(f"   ❌ Encoding error: {e}")
        return

    # Search in database
    logger.info(f"\n5️⃣  Searching for similar SKUs (Top-{top_k})...")
    try:
        matches, similarities = vector_db.search(
            image_embedding,
            k=top_k,
            return_distances=True
        )

        if not matches or len(matches) == 0:
            logger.warning(f"   ⚠ No matches found in database")
            return

        logger.info(f"   ✓ Found {len(matches)} matches!\n")

        # Display results
        logger.info("=" * 100)
        logger.info(f"🔍 TOP {min(top_k, len(matches))} SKU MATCHES")
        logger.info("=" * 100)

        for i, (match, sim) in enumerate(zip(matches, similarities), 1):
            # Determine confidence level
            if sim >= 0.95:
                confidence = "🟢 VERY HIGH"
            elif sim >= 0.85:
                confidence = "🟡 HIGH"
            elif sim >= 0.75:
                confidence = "🟠 MEDIUM"
            else:
                confidence = "🔴 LOW"

            logger.info(f"\n{i}. SKU: {match['sku']}")
            logger.info(f"   Product Title: {match['product_title']}")
            logger.info(f"   Category: {match['category']}")
            logger.info(f"   Similarity Score: {sim:.4f} {confidence}")

            # Show additional metadata if available
            if 'brand' in match and match['brand']:
                logger.info(f"   Brand: {match['brand']}")
            if 'retail_price' in match and match['retail_price']:
                logger.info(f"   Price: ${match['retail_price']}")

        # Summary statistics
        logger.info("\n" + "=" * 100)
        logger.info("📊 MATCHING STATISTICS")
        logger.info("=" * 100)
        logger.info(f"Total Matches Found: {len(matches)}")
        logger.info(f"Top Match Similarity: {similarities[0]:.4f}")
        logger.info(f"Average Similarity (Top-5): {np.mean(similarities[:5]):.4f}")

        high_conf = sum(1 for s in similarities if s >= 0.85)
        logger.info(f"High Confidence Matches (≥0.85): {high_conf}/{len(matches)}")

        # Recommendation
        logger.info("\n💡 RECOMMENDATION:")
        if similarities[0] >= 0.95:
            logger.info("   ✅ Top match has VERY HIGH confidence - likely correct SKU")
        elif similarities[0] >= 0.85:
            logger.info("   ✓ Top match has HIGH confidence - review recommended")
        elif similarities[0] >= 0.75:
            logger.info("   ⚠️ Top match has MEDIUM confidence - manual verification needed")
        else:
            logger.info("   ❌ LOW confidence - consider checking image quality or database")

        logger.info("\n✓ Test completed!")

    except Exception as e:
        logger.error(f"   ❌ Search error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test SKU matching on a single image')
    parser.add_argument(
        'image_path',
        type=str,
        help='Path to the image file to test'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=10,
        help='Number of top matches to return (default: 10)'
    )

    args = parser.parse_args()

    load_dotenv()
    test_single_image(args.image_path, top_k=args.top_k)
