#!/bin/bash
# Download Grounding DINO model weights

set -e

echo "==========================================="
echo "Downloading Grounding DINO Model Weights"
echo "==========================================="

# Create models directory
mkdir -p models/weights

# Download Grounding DINO weights
WEIGHT_FILE="models/weights/groundingdino_swint_ogc.pth"

if [ -f "$WEIGHT_FILE" ]; then
    echo "✓ Model weights already exist: $WEIGHT_FILE"
else
    echo "Downloading Grounding DINO SwinT-OGC weights..."
    wget -O "$WEIGHT_FILE" \
        "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth" \
        || curl -L -o "$WEIGHT_FILE" \
        "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth"

    echo "✓ Model weights downloaded successfully"
fi

# Alternative: Download from HuggingFace
if [ ! -f "$WEIGHT_FILE" ]; then
    echo "Trying alternative download from HuggingFace..."
    wget -O "$WEIGHT_FILE" \
        "https://huggingface.co/ShilongLiu/GroundingDINO/resolve/main/groundingdino_swint_ogc.pth" \
        || curl -L -o "$WEIGHT_FILE" \
        "https://huggingface.co/ShilongLiu/GroundingDINO/resolve/main/groundingdino_swint_ogc.pth"
fi

# Verify file size (should be around 600MB)
if [ -f "$WEIGHT_FILE" ]; then
    FILE_SIZE=$(stat -f%z "$WEIGHT_FILE" 2>/dev/null || stat -c%s "$WEIGHT_FILE" 2>/dev/null)
    if [ "$FILE_SIZE" -gt 500000000 ]; then
        echo "✓ Model weights verified (size: $FILE_SIZE bytes)"
    else
        echo "⚠ Warning: Model file seems too small, download may have failed"
    fi
fi

echo ""
echo "==========================================="
echo "✓ Model setup complete"
echo "==========================================="
