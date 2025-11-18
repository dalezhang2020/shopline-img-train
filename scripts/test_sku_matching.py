#!/usr/bin/env python3
"""
Test SKU matching using CLIP embeddings and FAISS database
Direct test of the vector database without Grounding DINO detection
"""

import sys
import logging
from pathlib import Path
import json
import yaml
import random
import pickle
import numpy as np
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


def load_metadata(metadata_path):
    """Load FAISS metadata"""
    with open(metadata_path, 'rb') as f:
        data = pickle.load(f)
    return data['metadata']


def test_sku_matching(num_samples=10, top_k=5):
    """Test SKU matching on random samples"""

    # Load config
    config_path = Path('config/config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    logger.info("=" * 100)
    logger.info("SKU MATCHING TEST - CLIP + FAISS Vector Database")
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
    logger.info(f"   ✓ CLIP encoder loaded. Output dimension: 768")

    # Load vector database
    logger.info(f"\n2️⃣  Loading FAISS vector database...")
    index_path = Path('data/embeddings/faiss_index.bin')
    metadata_path = Path('data/embeddings/sku_metadata.pkl')

    faiss_config = config['faiss']
    vector_db = VectorDatabase(
        dimension=faiss_config.get('dimension', 768),
        index_type=faiss_config.get('index_type', 'IndexFlatL2'),
        metric='IP',  # Inner product for cosine similarity
    )

    vector_db.load(index_path, metadata_path)
    logger.info(f"   ✓ FAISS database loaded successfully")

    # Get database stats
    stats = vector_db.get_stats()
    logger.info(f"\n📊 Database Statistics:")
    logger.info(f"   Total embeddings: {stats['total_embeddings']}")
    logger.info(f"   Embedding dimension: {stats['dimension']}")
    logger.info(f"   Index type: {stats['index_type']}")
    logger.info(f"   Metric: {stats['metric']}")

    # Load metadata to get list of SKUs with images
    logger.info(f"\n3️⃣  Preparing test data...")
    metadata_list = load_metadata(metadata_path)

    # Find available image files
    images_dir = Path('data/images')
    available_images = list(images_dir.glob('*.jpg'))
    logger.info(f"   Available image files: {len(available_images)}")

    if len(available_images) == 0:
        logger.error("   ❌ No image files found in data/images/")
        return

    # Randomly select test samples
    num_test = min(num_samples, len(available_images))
    test_images = random.sample(available_images, num_test)

    logger.info(f"\n4️⃣  Running CLIP + FAISS matching on {num_test} random samples...")

    results_summary = {
        'total_tested': num_test,
        'successful': 0,
        'failed': 0,
        'top_k': top_k,
        'database_size': stats['total_embeddings'],
        'results': []
    }

    for idx, img_path in enumerate(test_images, 1):
        try:
            logger.info(f"\n{'=' * 100}")
            logger.info(f"Test {idx}/{num_test}: {img_path.name}")
            logger.info(f"{'=' * 100}")

            # Encode the image using encode_image_paths
            embeddings = encoder.encode_image_paths([img_path], show_progress=False)
            image_embedding = embeddings[0]

            # Normalize for cosine similarity
            image_embedding = image_embedding / np.linalg.norm(image_embedding)
            image_embedding = image_embedding.reshape(1, -1).astype(np.float32)

            # Search in database
            matches, similarities = vector_db.search(
                image_embedding,
                k=top_k,
                return_distances=True
            )

            if matches and len(matches) > 0:
                results_summary['successful'] += 1

                logger.info(f"\n✓ Found {len(matches)} matches from database!")
                logger.info(f"\n  Top {min(3, len(matches))} SKU Matches:")

                for i, (match, sim) in enumerate(zip(matches[:3], similarities[:3]), 1):
                    logger.info(f"\n    {i}. SKU: {match['sku']}")
                    logger.info(f"       Title: {match['product_title']}")
                    logger.info(f"       Category: {match['category']}")
                    logger.info(f"       Similarity Score: {sim:.4f}")

                # Store result
                result_entry = {
                    'image_name': img_path.name,
                    'status': 'success',
                    'match_count': len(matches),
                    'top_match': {
                        'sku': matches[0]['sku'],
                        'title': matches[0]['product_title'],
                        'category': matches[0]['category'],
                        'similarity': float(similarities[0])
                    },
                    'all_matches': [
                        {
                            'sku': m['sku'],
                            'title': m['product_title'],
                            'category': m['category'],
                            'similarity': float(s)
                        }
                        for m, s in zip(matches, similarities)
                    ]
                }
            else:
                results_summary['failed'] += 1
                logger.warning(f"\n⚠ No matches found in database")
                result_entry = {
                    'image_name': img_path.name,
                    'status': 'no_matches',
                    'match_count': 0
                }

            results_summary['results'].append(result_entry)

        except Exception as e:
            results_summary['failed'] += 1
            logger.error(f"\n❌ Error processing image: {str(e)}")
            result_entry = {
                'image_name': img_path.name,
                'status': 'error',
                'error': str(e)
            }
            results_summary['results'].append(result_entry)

    # Print summary
    logger.info(f"\n\n{'=' * 100}")
    logger.info("📈 TEST SUMMARY")
    logger.info(f"{'=' * 100}")
    logger.info(f"Total Tested:      {results_summary['total_tested']}")
    logger.info(f"Successful:        {results_summary['successful']} ✓")
    logger.info(f"Failed:            {results_summary['failed']} ❌")
    success_rate = (results_summary['successful'] / results_summary['total_tested'] * 100) if results_summary['total_tested'] > 0 else 0
    logger.info(f"Success Rate:      {success_rate:.1f}%")
    logger.info(f"Database Size:     {results_summary['database_size']} SKUs")
    logger.info(f"Top-K Results:     {results_summary['top_k']}")

    # Save detailed results
    output_dir = Path('output')
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / 'sku_matching_test_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)

    logger.info(f"\n📁 Detailed results saved to: {results_file}")
    logger.info(f"\n✓ Test completed successfully!")

    return results_summary


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test CLIP + FAISS SKU matching')
    parser.add_argument(
        '--samples',
        type=int,
        default=10,
        help='Number of random samples to test (default: 10)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='Number of top matches to return (default: 5)'
    )

    args = parser.parse_args()

    load_dotenv()
    test_sku_matching(num_samples=args.samples, top_k=args.top_k)
