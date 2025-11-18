#!/usr/bin/env python3
"""
Evaluate SKU matching accuracy
Tests if the model correctly identifies the exact SKU from the image filename
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
from collections import defaultdict

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


def extract_sku_from_filename(filename):
    """Extract SKU from image filename (e.g., 'FBD90573-CHA.jpg' -> 'FBD90573-CHA')"""
    return filename.replace('.jpg', '').replace('.JPG', '')


def evaluate_accuracy(num_samples=50, top_k=5):
    """
    Evaluate SKU matching accuracy

    Metrics:
    - Top-1 Accuracy: Image's SKU matches top-1 result
    - Top-K Accuracy: Image's SKU in top-K results
    - Mean Reciprocal Rank (MRR): Average of 1/rank for correct matches
    """

    # Load config
    config_path = Path('config/config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    logger.info("=" * 100)
    logger.info("SKU MATCHING ACCURACY EVALUATION")
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

    # Load metadata to create SKU lookup
    logger.info(f"\n3️⃣  Preparing test data...")
    metadata_list = load_metadata(metadata_path)

    # Create a set of SKUs in database
    database_skus = set(meta['sku'] for meta in metadata_list)
    logger.info(f"   Total SKUs in database: {len(database_skus)}")

    # Find available image files that are in the database
    images_dir = Path('data/images')
    available_images = list(images_dir.glob('*.jpg'))

    # Filter to only test images whose SKU is in the database
    valid_test_images = []
    for img_path in available_images:
        sku = extract_sku_from_filename(img_path.name)
        if sku in database_skus:
            valid_test_images.append(img_path)

    logger.info(f"   Total images: {len(available_images)}")
    logger.info(f"   Valid test images (SKU in database): {len(valid_test_images)}")

    if len(valid_test_images) == 0:
        logger.error("   ❌ No valid test images found")
        return

    # Randomly select test samples
    num_test = min(num_samples, len(valid_test_images))
    test_images = random.sample(valid_test_images, num_test)

    logger.info(f"\n4️⃣  Running accuracy evaluation on {num_test} samples...")
    logger.info(f"   Metrics: Top-1, Top-{top_k}, Mean Reciprocal Rank (MRR)\n")

    # Metrics tracking
    top1_correct = 0
    topk_correct = 0
    reciprocal_ranks = []

    # Detailed results
    results = {
        'total_tested': num_test,
        'top_k': top_k,
        'database_size': stats['total_embeddings'],
        'test_results': [],
        'similarity_scores': defaultdict(list)
    }

    for idx, img_path in enumerate(test_images, 1):
        try:
            ground_truth_sku = extract_sku_from_filename(img_path.name)

            logger.info(f"\n{'=' * 100}")
            logger.info(f"Test {idx}/{num_test}: {img_path.name}")
            logger.info(f"Ground Truth SKU: {ground_truth_sku}")
            logger.info(f"{'=' * 100}")

            # Encode the image
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

            if not matches or len(matches) == 0:
                logger.warning(f"   ⚠ No matches found")
                results['test_results'].append({
                    'image_name': img_path.name,
                    'ground_truth': ground_truth_sku,
                    'status': 'no_matches',
                    'top1_correct': False,
                    'topk_correct': False,
                    'rank': None
                })
                continue

            # Find rank of ground truth SKU
            predicted_skus = [m['sku'] for m in matches]

            # Check if ground truth is in top-K
            if ground_truth_sku in predicted_skus:
                rank = predicted_skus.index(ground_truth_sku) + 1  # 1-indexed
                topk_correct += 1
                reciprocal_ranks.append(1.0 / rank)

                if rank == 1:
                    top1_correct += 1
                    logger.info(f"   ✅ TOP-1 CORRECT! (Similarity: {similarities[0]:.4f})")
                else:
                    logger.info(f"   ✓ Found at rank {rank} (Similarity: {similarities[rank-1]:.4f})")

                # Store similarity score for correct match
                results['similarity_scores']['correct'].append(float(similarities[rank-1]))
            else:
                rank = None
                reciprocal_ranks.append(0.0)
                logger.info(f"   ❌ Ground truth NOT in top-{top_k}")
                logger.info(f"      Top prediction: {predicted_skus[0]} (Similarity: {similarities[0]:.4f})")

                # Store similarity score for incorrect top-1
                results['similarity_scores']['incorrect_top1'].append(float(similarities[0]))

            # Log top-3 predictions
            logger.info(f"\n   Top-3 Predictions:")
            for i, (match, sim) in enumerate(zip(matches[:3], similarities[:3]), 1):
                is_correct = "✓✓✓" if match['sku'] == ground_truth_sku else ""
                logger.info(f"      {i}. {match['sku']} - Similarity: {sim:.4f} {is_correct}")

            # Store result
            results['test_results'].append({
                'image_name': img_path.name,
                'ground_truth': ground_truth_sku,
                'predicted_top1': predicted_skus[0],
                'predicted_topk': predicted_skus,
                'similarities': [float(s) for s in similarities],
                'rank': rank,
                'top1_correct': rank == 1 if rank else False,
                'topk_correct': rank is not None,
                'status': 'success'
            })

        except Exception as e:
            logger.error(f"   ❌ Error: {str(e)}")
            results['test_results'].append({
                'image_name': img_path.name,
                'ground_truth': extract_sku_from_filename(img_path.name),
                'status': 'error',
                'error': str(e),
                'top1_correct': False,
                'topk_correct': False
            })

    # Calculate metrics
    top1_accuracy = (top1_correct / num_test) * 100
    topk_accuracy = (topk_correct / num_test) * 100
    mrr = (sum(reciprocal_ranks) / num_test) if reciprocal_ranks else 0

    # Print summary
    logger.info(f"\n\n{'=' * 100}")
    logger.info("📊 ACCURACY EVALUATION RESULTS")
    logger.info(f"{'=' * 100}")
    logger.info(f"\n📈 Accuracy Metrics:")
    logger.info(f"   Total Tested:           {num_test}")
    logger.info(f"   Database Size:          {stats['total_embeddings']} SKUs")
    logger.info(f"")
    logger.info(f"   Top-1 Accuracy:         {top1_correct}/{num_test} = {top1_accuracy:.2f}% {'✅' if top1_accuracy >= 80 else '⚠️'}")
    logger.info(f"   Top-{top_k} Accuracy:        {topk_correct}/{num_test} = {topk_accuracy:.2f}% {'✅' if topk_accuracy >= 90 else '⚠️'}")
    logger.info(f"   Mean Reciprocal Rank:   {mrr:.4f}")
    logger.info(f"")

    # Similarity score analysis
    if results['similarity_scores']['correct']:
        avg_correct_sim = np.mean(results['similarity_scores']['correct'])
        logger.info(f"📊 Similarity Score Analysis:")
        logger.info(f"   Avg similarity (correct matches): {avg_correct_sim:.4f}")

        if results['similarity_scores']['incorrect_top1']:
            avg_incorrect_sim = np.mean(results['similarity_scores']['incorrect_top1'])
            logger.info(f"   Avg similarity (incorrect top-1): {avg_incorrect_sim:.4f}")
            logger.info(f"   Separation margin:                {avg_correct_sim - avg_incorrect_sim:.4f}")

    # Performance breakdown
    logger.info(f"\n📊 Performance Breakdown:")
    perfect_matches = sum(1 for r in results['test_results']
                         if r.get('status') == 'success' and r.get('similarities', [0])[0] >= 0.99)
    high_conf = sum(1 for r in results['test_results']
                   if r.get('status') == 'success' and 0.90 <= r.get('similarities', [0])[0] < 0.99)
    med_conf = sum(1 for r in results['test_results']
                  if r.get('status') == 'success' and 0.80 <= r.get('similarities', [0])[0] < 0.90)
    low_conf = sum(1 for r in results['test_results']
                  if r.get('status') == 'success' and r.get('similarities', [0])[0] < 0.80)

    logger.info(f"   Near-perfect (≥0.99):   {perfect_matches}/{num_test} = {perfect_matches/num_test*100:.1f}%")
    logger.info(f"   High confidence (≥0.90): {high_conf}/{num_test} = {high_conf/num_test*100:.1f}%")
    logger.info(f"   Medium conf (≥0.80):     {med_conf}/{num_test} = {med_conf/num_test*100:.1f}%")
    logger.info(f"   Low confidence (<0.80):  {low_conf}/{num_test} = {low_conf/num_test*100:.1f}%")

    # Save results
    results['metrics'] = {
        'top1_accuracy': top1_accuracy,
        'topk_accuracy': topk_accuracy,
        'mean_reciprocal_rank': mrr,
        'top1_correct_count': top1_correct,
        'topk_correct_count': topk_correct
    }

    output_dir = Path('output')
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / 'accuracy_evaluation.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n📁 Detailed results saved to: {results_file}")
    logger.info(f"\n{'✅ EXCELLENT' if top1_accuracy >= 90 else '✓ GOOD' if top1_accuracy >= 75 else '⚠️ NEEDS IMPROVEMENT'} - Evaluation completed!")

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Evaluate SKU matching accuracy')
    parser.add_argument(
        '--samples',
        type=int,
        default=50,
        help='Number of random samples to test (default: 50)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='K for top-K accuracy (default: 5)'
    )

    args = parser.parse_args()

    load_dotenv()
    evaluate_accuracy(num_samples=args.samples, top_k=args.top_k)
