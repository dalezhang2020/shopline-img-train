# SKU Recognition API Documentation

## Overview

The SKU Recognition API provides real-time product identification using CLIP (Contrastive Language-Image Pre-training) and FAISS vector similarity search. Upload an image, and the API returns the top matching SKUs with confidence scores.

**Base URL**: `http://localhost:8000`

**API Version**: `v1.0.0`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
   - [Health Check](#health-check)
   - [Get Statistics](#get-statistics)
   - [Recognize SKU (File Upload)](#recognize-sku-file-upload)
   - [Recognize SKU (Base64)](#recognize-sku-base64)
   - [Batch Recognition](#batch-recognition)
3. [Response Models](#response-models)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Examples](#examples)

---

## Authentication

**Current Version**: No authentication required (development mode)

For production deployment, add API key authentication:

```bash
# Set in .env file
API_KEY=your_secret_api_key_here
```

Then include in request headers:
```
X-API-Key: your_secret_api_key_here
```

---

## Endpoints

### Health Check

Check if the API service is running and the model is loaded.

**Endpoint**: `GET /api/v1/health`

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "database_size": 4109,
  "uptime_seconds": 3600.5
}
```

**cURL Example**:
```bash
curl http://localhost:8000/api/v1/health
```

---

### Get Statistics

Retrieve API usage statistics.

**Endpoint**: `GET /api/v1/stats`

**Response**:
```json
{
  "total_requests": 1523,
  "successful_requests": 1489,
  "failed_requests": 34,
  "average_processing_time_ms": 175.3,
  "uptime_seconds": 7200.8
}
```

**cURL Example**:
```bash
curl http://localhost:8000/api/v1/stats
```

---

### Recognize SKU (File Upload)

Upload an image file for SKU recognition.

**Endpoint**: `POST /api/v1/recognize`

**Content-Type**: `multipart/form-data`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | Image file (JPEG, PNG, WebP) |
| `top_k` | Integer | No | 5 | Number of top results (1-20) |
| `confidence_threshold` | Float | No | 0.7 | Minimum confidence score (0.0-1.0) |

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/v1/recognize \
  -F "file=@product_image.jpg" \
  -F "top_k=5" \
  -F "confidence_threshold=0.7"
```

**Response**:
```json
{
  "success": true,
  "matches": [
    {
      "sku": "FBD90554-BSP",
      "similarity": 0.9876,
      "product_title": "Contemporary Sofa - Beige",
      "category": "FURNITURE",
      "retail_price": 1299.99,
      "image_url": "https://example.com/images/FBD90554-BSP.jpg",
      "barcode": "1234567890123"
    },
    {
      "sku": "FBD90555-GRY",
      "similarity": 0.9234,
      "product_title": "Modern Couch - Gray",
      "category": "FURNITURE",
      "retail_price": 1399.99,
      "image_url": "https://example.com/images/FBD90555-GRY.jpg",
      "barcode": "1234567890124"
    }
  ],
  "processing_time_ms": 175.4,
  "timestamp": "2025-11-17T12:34:56.789Z",
  "message": "Found 2 matches"
}
```

**JavaScript Example** (Frontend):
```javascript
import { skuRecognitionAPI } from '@/lib/sku-recognition-api';

const file = /* File object from input */;
const result = await skuRecognitionAPI.recognizeFromFile(file, {
  topK: 5,
  confidenceThreshold: 0.7
});

console.log(result.matches);
```

---

### Recognize SKU (Base64)

Send a base64-encoded image for recognition.

**Endpoint**: `POST /api/v1/recognize/base64`

**Content-Type**: `application/json`

**Request Body**:
```json
{
  "image_base64": "/9j/4AAQSkZJRgABAQAA...",
  "top_k": 5,
  "confidence_threshold": 0.7
}
```

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image_base64` | String | Yes | - | Base64 encoded image |
| `top_k` | Integer | No | 5 | Number of top results (1-20) |
| `confidence_threshold` | Float | No | 0.7 | Minimum confidence score (0.0-1.0) |

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/recognize/base64 \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'$(base64 -i product_image.jpg)'",
    "top_k": 5,
    "confidence_threshold": 0.7
  }'
```

**Response**: Same as [Recognize SKU (File Upload)](#recognize-sku-file-upload)

**JavaScript Example**:
```javascript
const base64Image = await skuRecognitionAPI.fileToBase64(file);
const result = await skuRecognitionAPI.recognizeFromBase64(base64Image, {
  topK: 10,
  confidenceThreshold: 0.6
});
```

---

### Batch Recognition

Process multiple images in a single request.

**Endpoint**: `POST /api/v1/recognize/batch`

**Content-Type**: `multipart/form-data`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `files` | File[] | Yes | - | Array of image files (max 20) |
| `top_k` | Integer | No | 5 | Number of top results per image |
| `confidence_threshold` | Float | No | 0.7 | Minimum confidence score |

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/v1/recognize/batch \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "files=@image3.jpg" \
  -F "top_k=5"
```

**Response**:
```json
{
  "success": true,
  "total_images": 3,
  "results": [
    {
      "filename": "image1.jpg",
      "success": true,
      "matches": [...]
    },
    {
      "filename": "image2.jpg",
      "success": true,
      "matches": [...]
    },
    {
      "filename": "image3.jpg",
      "success": false,
      "error": "Image too small"
    }
  ],
  "processing_time_ms": 456.7,
  "timestamp": "2025-11-17T12:35:00.123Z"
}
```

---

## Response Models

### SKUMatch

Single SKU match result.

```typescript
{
  sku: string;                 // SKU code
  similarity: number;          // Similarity score (0.0-1.0)
  product_title?: string;      // Product name
  category?: string;           // Product category
  retail_price?: number;       // Retail price (USD)
  image_url?: string;          // Product image URL
  barcode?: string;            // Product barcode
}
```

### RecognitionResponse

Recognition result response.

```typescript
{
  success: boolean;            // Whether recognition succeeded
  matches: SKUMatch[];         // Array of matched SKUs
  processing_time_ms: number;  // Processing time in milliseconds
  timestamp: string;           // ISO 8601 timestamp
  message?: string;            // Optional message
}
```

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "matches": [],
  "processing_time_ms": 0,
  "timestamp": "2025-11-17T12:35:00.123Z",
  "message": "Error description"
}
```

### Common Error Codes

| Status Code | Error | Description |
|------------|-------|-------------|
| `400` | Bad Request | Invalid parameters or file format |
| `413` | Payload Too Large | File size exceeds 10MB |
| `422` | Unprocessable Entity | Invalid image format or corrupted file |
| `503` | Service Unavailable | Model not loaded or service down |
| `500` | Internal Server Error | Unexpected server error |

### Error Examples

**Invalid File Type**:
```json
{
  "detail": "Invalid file type: application/pdf. Must be an image."
}
```

**Image Too Small**:
```json
{
  "success": false,
  "message": "Image too small: 30x30. Minimum: 50x50"
}
```

**Model Not Loaded**:
```json
{
  "detail": "Model not loaded"
}
```

---

## Rate Limiting

**Current**: Not enabled (development mode)

**Production** (when enabled):
- Rate Limit: 60 requests per minute per IP
- Headers:
  - `X-RateLimit-Limit`: Maximum requests per minute
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Timestamp when limit resets

**Rate Limit Exceeded Response**:
```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

---

## Examples

### Python Example

```python
import requests

# Health check
response = requests.get('http://localhost:8000/api/v1/health')
print(response.json())

# Recognize SKU from file
with open('product.jpg', 'rb') as f:
    files = {'file': f}
    params = {'top_k': 5, 'confidence_threshold': 0.7}
    response = requests.post(
        'http://localhost:8000/api/v1/recognize',
        files=files,
        params=params
    )
    result = response.json()

    for match in result['matches']:
        print(f"SKU: {match['sku']}, Confidence: {match['similarity']:.2%}")
```

### JavaScript/TypeScript Example

```typescript
import { SKURecognitionAPI } from './sku-recognition-api';

const api = new SKURecognitionAPI({
  baseURL: 'http://localhost:8000',
  timeout: 30000
});

// Health check
const health = await api.healthCheck();
console.log('Service status:', health.status);

// Recognize from file input
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];

const result = await api.recognizeFromFile(file, {
  topK: 10,
  confidenceThreshold: 0.6
});

console.log('Top match:', result.matches[0]);
console.log('Processing time:', result.processing_time_ms, 'ms');
```

### cURL Example (Complete Workflow)

```bash
# 1. Check service health
curl http://localhost:8000/api/v1/health

# 2. Recognize SKU from image
curl -X POST http://localhost:8000/api/v1/recognize \
  -F "file=@product_image.jpg" \
  -F "top_k=10" \
  -F "confidence_threshold=0.6"

# 3. Check stats
curl http://localhost:8000/api/v1/stats

# 4. Batch recognition
curl -X POST http://localhost:8000/api/v1/recognize/batch \
  -F "files=@img1.jpg" \
  -F "files=@img2.jpg" \
  -F "files=@img3.jpg"
```

---

## Interactive Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

These interfaces allow you to:
- View all endpoints
- Test API calls directly
- See request/response schemas
- Download OpenAPI specification

---

## Performance Optimization

### Tips for Better Performance

1. **Image Size**: Resize images to 800x800px before upload for faster processing
2. **Batch Processing**: Use `/recognize/batch` for multiple images (up to 20)
3. **Confidence Threshold**: Lower threshold (0.6) returns more results but may be less accurate
4. **Caching**: Identical images are cached (if Redis is enabled)

### Typical Performance Metrics

| Operation | Time (CPU) | Time (GPU) |
|-----------|------------|------------|
| Single Image Recognition | 170ms | 50ms |
| Batch (5 images) | 600ms | 150ms |
| Batch (20 images) | 2500ms | 500ms |

**Note**: Times may vary based on image size and hardware.

---

## Contact & Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/shopline-img-train/issues)
- **Documentation**: [Full Project Docs](../docs/)
- **API Source**: [api_server.py](../scripts/api_server.py)

---

## Changelog

### Version 1.0.0 (2025-11-17)
- Initial release
- CLIP ViT-L/14 model support
- FAISS vector search
- Multi-format image support (JPEG, PNG, WebP)
- Batch processing
- Interactive documentation
