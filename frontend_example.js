// Next.js 前端调用 SKU Recognition API 示例

// 方法 1: 使用 fetch (推荐)
async function recognizeSKU(imageFile, topK = 5, confidenceThreshold = 0.7) {
  const formData = new FormData();
  formData.append('file', imageFile);

  try {
    const response = await fetch(
      `https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize?top_k=${topK}&confidence_threshold=${confidenceThreshold}`,
      {
        method: 'POST',
        body: formData,
        // 不需要设置 Content-Type，浏览器会自动设置为 multipart/form-data
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('API Response:', data);

    // 检查响应结构
    if (data.success && data.matches) {
      console.log(`Found ${data.matches.length} matches`);
      console.log(`Processing time: ${data.processing_time_ms}ms`);

      // 处理匹配结果
      data.matches.forEach((match, index) => {
        console.log(`Match ${index + 1}:`, {
          sku: match.sku,
          similarity: match.similarity,
          title: match.product_title,
          price: match.retail_price,
        });
      });

      return data.matches;
    } else {
      console.warn('No matches found or request failed');
      return [];
    }
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// 方法 2: 使用 axios
import axios from 'axios';

async function recognizeSKUWithAxios(imageFile, topK = 5, confidenceThreshold = 0.7) {
  const formData = new FormData();
  formData.append('file', imageFile);

  try {
    const response = await axios.post(
      'https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize',
      formData,
      {
        params: {
          top_k: topK,
          confidence_threshold: confidenceThreshold,
        },
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    console.log('API Response:', response.data);
    return response.data.matches;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// React Component 示例
import { useState } from 'react';

export function SKURecognitionUpload() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const matches = await recognizeSKU(file, 5, 0.7);
      setResults(matches);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept="image/*"
        onChange={handleFileUpload}
        disabled={loading}
      />

      {loading && <p>Processing...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {results && results.length > 0 && (
        <div>
          <h3>Recognition Results:</h3>
          <ul>
            {results.map((match, index) => (
              <li key={index}>
                <strong>SKU:</strong> {match.sku} <br />
                <strong>Similarity:</strong> {(match.similarity * 100).toFixed(2)}% <br />
                <strong>Title:</strong> {match.product_title} <br />
                <strong>Price:</strong> ${match.retail_price}
              </li>
            ))}
          </ul>
        </div>
      )}

      {results && results.length === 0 && (
        <p>No matches found above the confidence threshold.</p>
      )}
    </div>
  );
}

// Next.js API Route 示例 (可选，用于服务端调用)
// pages/api/recognize-sku.js
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const formData = new FormData();
    // 从 req.body 获取图片数据并转发到 SKU API

    const response = await fetch(
      'https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize?top_k=5&confidence_threshold=0.7',
      {
        method: 'POST',
        body: formData,
      }
    );

    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}

// 期望的响应格式：
/*
{
  "success": true,
  "matches": [
    {
      "sku": "ABC123",
      "similarity": 0.85,
      "product_title": "Modern Sofa",
      "category": "FURNITURE",
      "retail_price": 1299.99,
      "image_url": "https://...",
      "barcode": "1234567890"
    }
  ],
  "processing_time_ms": 150.5,
  "timestamp": "2025-11-18T20:00:00",
  "message": "Found 1 matches"
}
*/
