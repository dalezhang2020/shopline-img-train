#!/usr/bin/env python3
"""
Run SKU recognition inference on images
"""

import sys
import logging
from pathlib import Path
import argparse
import json
import yaml
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.inference import SKURecognitionPipeline
from src.utils.image_utils import load_image

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Run SKU recognition inference')
    parser.add_argument(
        'image',
        type=Path,
        help='Input image path or directory'
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
        default=Path('output'),
        help='Output directory for results'
    )
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Save visualization images'
    )
    parser.add_argument(
        '--text-prompt',
        type=str,
        default=None,
        help='Text prompt for detection (optional)'
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

    # Print pipeline stats
    stats = pipeline.get_stats()
    logger.info("Pipeline statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # Process image(s)
    image_path = args.image

    if image_path.is_file():
        # Single image
        logger.info(f"Processing image: {image_path}")
        results = pipeline.process_image(
            image_path,
            text_prompt=args.text_prompt,
            visualize=args.visualize,
            output_dir=args.output_dir,
        )

        # Save results
        output_json = args.output_dir / f"{image_path.stem}_results.json"
        output_json.parent.mkdir(parents=True, exist_ok=True)

        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {output_json}")

        # Print results
        print("\n" + "=" * 80)
        print(f"RESULTS for {image_path.name}")
        print("=" * 80)

        for i, result in enumerate(results, 1):
            print(f"\nDetection {i}:")
            print(f"  Box: {result['box']}")
            print(f"  Detection Score: {result['detection_score']:.3f}")
            print(f"  Label: {result['detection_label']}")
            print(f"\n  Top Matches:")

            for j, match in enumerate(result['top_matches'][:3], 1):
                print(f"    {j}. SKU: {match['sku']}")
                print(f"       Title: {match['title']}")
                print(f"       Category: {match['category']}")
                print(f"       Similarity: {match['similarity']:.3f}")

        print("\n" + "=" * 80)

    elif image_path.is_dir():
        # Directory of images
        logger.info(f"Processing images in directory: {image_path}")

        # Find all image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
            image_files.extend(image_path.glob(ext))
            image_files.extend(image_path.glob(ext.upper()))

        logger.info(f"Found {len(image_files)} images")

        all_results = {}

        for img_file in image_files:
            logger.info(f"Processing: {img_file.name}")

            results = pipeline.process_image(
                img_file,
                text_prompt=args.text_prompt,
                visualize=args.visualize,
                output_dir=args.output_dir,
            )

            all_results[img_file.name] = results

        # Save all results
        output_json = args.output_dir / "batch_results.json"
        output_json.parent.mkdir(parents=True, exist_ok=True)

        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        logger.info(f"Batch results saved to {output_json}")

    else:
        logger.error(f"Invalid path: {image_path}")
        sys.exit(1)

    logger.info("✓ Inference completed successfully")


if __name__ == '__main__':
    main()
