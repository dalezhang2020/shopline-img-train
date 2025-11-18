#!/bin/bash
# Test API response format with a sample image

echo "Testing API response format..."
echo ""

# Test with the screenshot you mentioned
IMAGE_PATH="ScreenShot_2025-11-17_004216_196.png"

if [ ! -f "$IMAGE_PATH" ]; then
    echo "❌ Image not found: $IMAGE_PATH"
    echo "Please provide the path to an image file"
    exit 1
fi

echo "📤 Sending request to production API..."
echo "URL: https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize"
echo "Image: $IMAGE_PATH"
echo ""

# Send request and save response
RESPONSE=$(curl -s -X POST \
  "https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize?top_k=5&confidence_threshold=0.7" \
  -F "file=@$IMAGE_PATH")

echo "📥 Response:"
echo "$RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Check if response has expected fields
echo "Checking response structure..."
if echo "$RESPONSE" | grep -q "success"; then
    echo "✅ Has 'success' field"
else
    echo "❌ Missing 'success' field"
fi

if echo "$RESPONSE" | grep -q "matches"; then
    echo "✅ Has 'matches' field"
else
    echo "❌ Missing 'matches' field"
fi

if echo "$RESPONSE" | grep -q "processing_time_ms"; then
    echo "✅ Has 'processing_time_ms' field"
else
    echo "❌ Missing 'processing_time_ms' field"
fi
