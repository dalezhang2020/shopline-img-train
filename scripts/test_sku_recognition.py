#!/usr/bin/env python3
"""
Test SKU recognition on sample images from the database
Tests the complete pipeline with the built FAISS database
"""

import sys
import logging
from pathlib import Path
import json
import yaml
import random
import pickle
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.inference import SKURecognitionPipeline
from src.database.vector_db import VectorDatabase
from src.models.clip_encoder import CLIPEncoder

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


def test_recognition(num_samples=5):
    """Test SKU recognition on random samples"""

    # Load config
    config_path = Path('config/config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    logger.info("=" * 80)
    logger.info("SKU Recognition System Test")
    logger.info("=" * 80)

    # Initialize pipeline
    logger.info("\n1️⃣  Initializing SKU recognition pipeline...")
    pipeline = SKURecognitionPipeline(config_path=str(config_path))

    # Load vector database
    index_path = Path('data/embeddings/faiss_index.bin')
    metadata_path = Path('data/embeddings/sku_metadata.pkl')

    logger.info(f"\n2️⃣  Loading vector database from {index_path}...")
    pipeline.load_database(index_path, metadata_path)

    # Get database stats
    stats = pipeline.get_stats()
    logger.info("\n📊 Database Statistics:")
    for key, value in stats.items():
        logger.info(f"   {key}: {value}")

    # Load metadata to get list of SKUs with images
    logger.info(f"\n3️⃣  Loading SKU metadata...")
    metadata_list = load_metadata(metadata_path)
    logger.info(f"   Total SKUs in database: {len(metadata_list)}")

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

    logger.info(f"\n4️⃣  Running inference on {num_test} random samples...\n")

    results_summary = {
        'total_tested': num_test,
        'successful': 0,
        'failed': 0,
        'results': []
    }

    for idx, img_path in enumerate(test_images, 1):
        try:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Test {idx}/{num_test}: {img_path.name}")
            logger.info(f"{'=' * 80}")

            # Process image
            results = pipeline.process_image(
                img_path,
                text_prompt="retail product",
                visualize=False
            )

            if results and len(results) > 0:
                results_summary['successful'] += 1

                # Display results for first detection
                detection = results[0]
                logger.info(f"\n✓ Detection found!")
                logger.info(f"  Detection label: {detection['detection_label']}")
                logger.info(f"  Detection score: {detection['detection_score']:.3f}")

                # Show top 3 matches
                logger.info(f"\n  Top 3 SKU Matches:")
                for i, match in enumerate(detection['top_matches'][:3], 1):
                    logger.info(f"    {i}. SKU: {match['sku']}")
                    logger.info(f"       Title: {match['title']}")
                    logger.info(f"       Category: {match['category']}")
                    logger.info(f"       Similarity Score: {match['similarity']:.4f}")

                # Store result
                result_entry = {
                    'image_name': img_path.name,
                    'status': 'success',
                    'detected': True,
                    'detection_count': len(results),
                    'top_match': detection['top_matches'][0] if detection['top_matches'] else None
                }
            else:
                results_summary['failed'] += 1
                logger.warning(f"\n⚠ No detections found in image")
                result_entry = {
                    'image_name': img_path.name,
                    'status': 'no_detection',
                    'detected': False
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
    logger.info(f"\n\n{'=' * 80}")
    logger.info("📈 TEST SUMMARY")
    logger.info(f"{'=' * 80}")
    logger.info(f"Total Tested: {results_summary['total_tested']}")
    logger.info(f"Successful:  {results_summary['successful']} ✓")
    logger.info(f"Failed:      {results_summary['failed']} ❌")
    success_rate = (results_summary['successful'] / results_summary['total_tested'] * 100) if results_summary['total_tested'] > 0 else 0
    logger.info(f"Success Rate: {success_rate:.1f}%")

    # Save detailed results
    output_dir = Path('output')
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / 'sku_recognition_test_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)

    logger.info(f"\n📁 Detailed results saved to: {results_file}")
    logger.info(f"\n✓ Test completed!")

    return results_summary


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test SKU recognition system')
    parser.add_argument(
        '--samples',
        type=int,
        default=5,
        help='Number of random samples to test (default: 5)'
    )

    args = parser.parse_args()

    load_dotenv()
    test_recognition(num_samples=args.samples)
