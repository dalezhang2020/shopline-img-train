#!/usr/bin/env python3
"""
Evaluate SKU recognition performance with ground truth data
"""

import sys
import logging
from pathlib import Path
import argparse
import json
import yaml
from tqdm import tqdm
import pandas as pd
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.inference import SKURecognitionPipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_ground_truth(gt_file: Path) -> dict:
    """
    Load ground truth data

    Expected format (JSON):
    {
        "image1.jpg": "SKU-001",
        "image2.jpg": "SKU-002",
        ...
    }

    Or CSV with columns: image_file, sku
    """
    if gt_file.suffix == '.json':
        with open(gt_file, 'r') as f:
            return json.load(f)
    elif gt_file.suffix == '.csv':
        df = pd.read_csv(gt_file)
        return dict(zip(df['image_file'], df['sku']))
    else:
        raise ValueError(f"Unsupported file format: {gt_file.suffix}")


def calculate_metrics(predictions: dict, ground_truth: dict) -> dict:
    """Calculate recognition metrics"""

    total = len(ground_truth)
    top1_correct = 0
    top3_correct = 0
    top5_correct = 0
    not_detected = 0

    per_category_stats = defaultdict(lambda: {'total': 0, 'correct': 0})

    for image_file, true_sku in ground_truth.items():
        if image_file not in predictions:
            not_detected += 1
            continue

        pred = predictions[image_file]

        if not pred or 'top_matches' not in pred or len(pred['top_matches']) == 0:
            not_detected += 1
            continue

        # Get predicted SKUs
        pred_skus = [m['sku'] for m in pred['top_matches']]

        # Top-1 accuracy
        if pred_skus[0] == true_sku:
            top1_correct += 1

        # Top-3 accuracy
        if true_sku in pred_skus[:3]:
            top3_correct += 1

        # Top-5 accuracy
        if true_sku in pred_skus[:5]:
            top5_correct += 1

        # Per-category accuracy
        category = pred['top_matches'][0].get('category', 'unknown')
        per_category_stats[category]['total'] += 1
        if pred_skus[0] == true_sku:
            per_category_stats[category]['correct'] += 1

    metrics = {
        'total_images': total,
        'not_detected': not_detected,
        'detected': total - not_detected,
        'top1_accuracy': top1_correct / total if total > 0 else 0,
        'top3_accuracy': top3_correct / total if total > 0 else 0,
        'top5_accuracy': top5_correct / total if total > 0 else 0,
        'detection_rate': (total - not_detected) / total if total > 0 else 0,
        'per_category': {
            cat: {
                'total': stats['total'],
                'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0
            }
            for cat, stats in per_category_stats.items()
        }
    }

    return metrics


def main():
    parser = argparse.ArgumentParser(description='Evaluate SKU recognition performance')
    parser.add_argument(
        'ground_truth',
        type=Path,
        help='Ground truth file (JSON or CSV)'
    )
    parser.add_argument(
        'images_dir',
        type=Path,
        help='Directory containing test images'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config/config.yaml'),
        help='Path to config file'
    )
    parser.add_argument(
        '--index',
        type=Path,
        default=Path('data/embeddings/faiss_index.bin'),
        help='Path to FAISS index'
    )
    parser.add_argument(
        '--metadata',
        type=Path,
        default=Path('data/embeddings/sku_metadata.pkl'),
        help='Path to metadata file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('evaluation_results.json'),
        help='Output file for evaluation results'
    )

    args = parser.parse_args()

    # Load ground truth
    logger.info(f"Loading ground truth from {args.ground_truth}")
    ground_truth = load_ground_truth(args.ground_truth)
    logger.info(f"Loaded {len(ground_truth)} ground truth labels")

    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Initialize pipeline
    logger.info("Initializing SKU recognition pipeline")
    pipeline = SKURecognitionPipeline(config_path=args.config)
    pipeline.load_database(args.index, args.metadata)

    # Run predictions
    logger.info("Running predictions...")
    predictions = {}

    for image_file in tqdm(ground_truth.keys(), desc="Processing"):
        image_path = args.images_dir / image_file

        if not image_path.exists():
            logger.warning(f"Image not found: {image_path}")
            continue

        try:
            results = pipeline.process_image(image_path)
            if results:
                predictions[image_file] = results[0]  # Take first detection
        except Exception as e:
            logger.error(f"Error processing {image_file}: {e}")

    # Calculate metrics
    logger.info("Calculating metrics...")
    metrics = calculate_metrics(predictions, ground_truth)

    # Print results
    logger.info("\n" + "=" * 80)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total images: {metrics['total_images']}")
    logger.info(f"Detected: {metrics['detected']} ({metrics['detection_rate']:.2%})")
    logger.info(f"Not detected: {metrics['not_detected']}")
    logger.info(f"")
    logger.info(f"Top-1 Accuracy: {metrics['top1_accuracy']:.2%}")
    logger.info(f"Top-3 Accuracy: {metrics['top3_accuracy']:.2%}")
    logger.info(f"Top-5 Accuracy: {metrics['top5_accuracy']:.2%}")
    logger.info(f"")
    logger.info("Per-Category Accuracy:")
    for category, stats in metrics['per_category'].items():
        logger.info(f"  {category}: {stats['accuracy']:.2%} ({stats['total']} images)")
    logger.info("=" * 80)

    # Save results
    with open(args.output, 'w') as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"\n✓ Evaluation results saved to {args.output}")


if __name__ == '__main__':
    main()
