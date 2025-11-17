#!/usr/bin/env python3
"""
Batch inference on multiple images
"""

import sys
import logging
from pathlib import Path
import argparse
import json
import yaml
from tqdm import tqdm
from dotenv import load_dotenv
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.inference import SKURecognitionPipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Run batch SKU recognition inference')
    parser.add_argument(
        'input_dir',
        type=Path,
        help='Input directory containing images'
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
        '--output-dir',
        type=Path,
        default=Path('output/batch'),
        help='Output directory for results'
    )
    parser.add_argument(
        '--output-csv',
        type=Path,
        default=None,
        help='Output CSV file for results summary'
    )
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Save visualization images'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='Number of top matches to return'
    )
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.7,
        help='Confidence threshold for recognition'
    )
    parser.add_argument(
        '--extensions',
        nargs='+',
        default=['jpg', 'jpeg', 'png', 'bmp'],
        help='Image file extensions to process'
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Load config
    logger.info(f"Loading config from {args.config}")
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Override config with command line arguments
    config['inference']['top_k'] = args.top_k
    config['inference']['confidence_threshold'] = args.confidence

    # Initialize pipeline
    logger.info("Initializing SKU recognition pipeline")
    pipeline = SKURecognitionPipeline(config_path=args.config)

    # Load vector database
    logger.info("Loading vector database")
    pipeline.load_database(args.index, args.metadata)

    # Find all image files
    logger.info(f"Scanning directory: {args.input_dir}")
    image_files = []
    for ext in args.extensions:
        image_files.extend(args.input_dir.glob(f"*.{ext}"))
        image_files.extend(args.input_dir.glob(f"*.{ext.upper()}"))

    logger.info(f"Found {len(image_files)} images to process")

    if len(image_files) == 0:
        logger.error(f"No images found in {args.input_dir}")
        sys.exit(1)

    # Process images
    all_results = []
    successful = 0
    failed = 0

    for img_file in tqdm(image_files, desc="Processing images"):
        try:
            logger.info(f"Processing: {img_file.name}")

            results = pipeline.process_image(
                img_file,
                visualize=args.visualize,
                output_dir=args.output_dir,
            )

            # Store results
            for result in results:
                result['image_file'] = img_file.name
                result['image_path'] = str(img_file)
                all_results.append(result)

            successful += 1

        except Exception as e:
            logger.error(f"Failed to process {img_file.name}: {e}")
            failed += 1
            all_results.append({
                'image_file': img_file.name,
                'image_path': str(img_file),
                'error': str(e),
                'status': 'failed'
            })

    # Save JSON results
    output_json = args.output_dir / "batch_results.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_json}")

    # Save CSV summary if requested
    if args.output_csv or len(all_results) > 0:
        # Flatten results for CSV
        csv_data = []
        for result in all_results:
            if result.get('status') == 'failed':
                csv_data.append({
                    'image_file': result['image_file'],
                    'status': 'failed',
                    'error': result.get('error', ''),
                })
            elif 'top_matches' in result and len(result['top_matches']) > 0:
                top_match = result['top_matches'][0]
                csv_data.append({
                    'image_file': result['image_file'],
                    'sku': top_match.get('sku', ''),
                    'title': top_match.get('title', ''),
                    'category': top_match.get('category', ''),
                    'similarity': top_match.get('similarity', 0),
                    'detection_score': result.get('detection_score', 0),
                    'box': str(result.get('box', [])),
                    'status': 'success'
                })

        df = pd.DataFrame(csv_data)

        csv_path = args.output_csv or args.output_dir / "batch_results.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"CSV summary saved to {csv_path}")

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total images: {len(image_files)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total detections: {len(all_results)}")
    logger.info(f"Results saved to: {args.output_dir}")
    logger.info("=" * 80)

    logger.info("✓ Batch inference completed")


if __name__ == '__main__':
    main()
