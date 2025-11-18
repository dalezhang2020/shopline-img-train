#!/bin/bash
# Test parallel vs sequential performance

set -e

# Test with small subset first (100 images)
echo "=========================================="
echo "Testing with 100 images (5x augmentation)"
echo "=========================================="

# Test sequential version
echo ""
echo "1. Sequential version (current implementation):"
time python3 scripts/build_robust_vector_db.py \
  --config config/config.yaml \
  --sku-data data/raw/sku_data.json \
  --images-dir data/images \
  --augment-per-image 5 \
  --max-images 100 \
  --output-index data/embeddings/test_sequential.bin \
  --output-metadata data/embeddings/test_sequential.pkl

# Test parallel version
echo ""
echo "2. Parallel version (12 workers):"
export KMP_DUPLICATE_LIB_OK=TRUE
time python3 scripts/build_robust_vector_db_parallel.py \
  --config config/config.yaml \
  --sku-data data/raw/sku_data.json \
  --images-dir data/images \
  --augment-per-image 5 \
  --max-images 100 \
  --num-workers 12 \
  --encoding-batch-size 64 \
  --output-index data/embeddings/test_parallel.bin \
  --output-metadata data/embeddings/test_parallel.pkl

echo ""
echo "=========================================="
echo "Performance test completed!"
echo "=========================================="
