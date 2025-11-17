# API Documentation

## Python API 使用文档

### 1. Shopline Client API

#### 初始化客户端

```python
from src.api.shopline_client import ShoplineClient

client = ShoplineClient(
    access_token="your_token",
    shop_name="your_shop",
    api_url="https://api.shoplineapp.com",
    api_version="v1"
)
```

#### 获取产品

```python
# 获取单页产品
products = client.get_products(limit=100, page=1)

# 获取所有产品
all_products = client.get_all_products(
    categories=["FURNITURE", "DECOR"],
    batch_size=100
)
```

#### 提取 SKU 数据

```python
sku_data = []
for product in products:
    skus = client.extract_sku_data(product)
    sku_data.extend(skus)
```

#### 下载图片

```python
from pathlib import Path

client.download_image(
    image_url="https://example.com/image.jpg",
    save_path=Path("data/images/sku_001.jpg")
)
```

### 2. CLIP Encoder API

#### 初始化编码器

```python
from src.models.clip_encoder import CLIPEncoder

encoder = CLIPEncoder(
    model_name="ViT-B-32",
    pretrained="openai",
    device="cuda",
    batch_size=32
)
```

#### 编码单张图片

```python
from PIL import Image

image = Image.open("product.jpg")
embedding = encoder.encode_image(image)
# embedding.shape: (512,)
```

#### 批量编码图片

```python
from pathlib import Path

image_paths = list(Path("data/images").glob("*.jpg"))
embeddings = encoder.encode_image_paths(
    image_paths,
    show_progress=True
)
# embeddings.shape: (N, 512)
```

#### 编码文本

```python
text_embedding = encoder.encode_text("furniture product")
# text_embedding.shape: (1, 512)
```

### 3. Vector Database API

#### 初始化数据库

```python
from src.database.vector_db import VectorDatabase

db = VectorDatabase(
    dimension=512,
    index_type="IndexFlatL2",
    metric="IP",
    nlist=100
)
```

#### 添加向量

```python
import numpy as np

embeddings = np.random.rand(1000, 512).astype(np.float32)
metadata = [{"sku": f"SKU_{i}", "title": f"Product {i}"} for i in range(1000)]

db.add_embeddings(embeddings, metadata)
```

#### 搜索

```python
query = np.random.rand(512).astype(np.float32)

results, similarities = db.search(
    query_embedding=query,
    k=5,
    return_distances=True
)

for result, sim in zip(results, similarities):
    print(f"SKU: {result['sku']}, Similarity: {sim:.3f}")
```

#### 保存和加载

```python
from pathlib import Path

# 保存
db.save(
    index_path=Path("data/embeddings/index.bin"),
    metadata_path=Path("data/embeddings/metadata.pkl")
)

# 加载
db.load(
    index_path=Path("data/embeddings/index.bin"),
    metadata_path=Path("data/embeddings/metadata.pkl")
)
```

### 4. Grounding DINO Detector API

#### 初始化检测器

```python
from src.models.grounding_dino import GroundingDINODetector

detector = GroundingDINODetector(
    config_file="path/to/config.py",
    checkpoint_path="path/to/weights.pth",
    device="cuda",
    box_threshold=0.35,
    text_threshold=0.25
)
```

#### 检测物体

```python
from PIL import Image

image = Image.open("scene.jpg")
boxes, scores, labels = detector.detect(
    image,
    text_prompt="retail product. furniture item. decor item"
)

print(f"Detected {len(boxes)} objects")
for box, score, label in zip(boxes, scores, labels):
    print(f"Box: {box}, Score: {score:.3f}, Label: {label}")
```

#### 裁剪检测区域

```python
crops = detector.crop_detections(image, boxes)

for i, crop in enumerate(crops):
    print(f"Crop {i} shape: {crop.shape}")
```

#### 可视化结果

```python
from pathlib import Path

vis_image = detector.visualize_detection(
    image,
    boxes,
    scores,
    labels,
    output_path=Path("output/detection.jpg")
)
```

### 5. SKU Recognition Pipeline API

#### 初始化 Pipeline

```python
from src.pipeline.inference import SKURecognitionPipeline
from pathlib import Path

pipeline = SKURecognitionPipeline(
    config_path=Path("config/config.yaml")
)

# 加载向量数据库
pipeline.load_database(
    index_path=Path("data/embeddings/faiss_index.bin"),
    metadata_path=Path("data/embeddings/sku_metadata.pkl")
)
```

#### 处理单张图片

```python
results = pipeline.process_image(
    image="test.jpg",
    text_prompt="retail product",
    visualize=True,
    output_dir=Path("output")
)

for result in results:
    print(f"Detection {result['detection_id']}:")
    top_match = result['top_matches'][0]
    print(f"  SKU: {top_match['sku']}")
    print(f"  Title: {top_match['title']}")
    print(f"  Similarity: {top_match['similarity']:.3f}")
```

#### 只检测产品

```python
boxes, scores, labels = pipeline.detect_products(
    image="test.jpg",
    text_prompt="furniture product"
)
```

#### 只识别 SKU（从裁剪图）

```python
from PIL import Image

crop = Image.open("cropped_product.jpg")
results, similarities = pipeline.recognize_sku(
    crop,
    top_k=5
)

for result, sim in zip(results, similarities):
    print(f"{result['sku']}: {sim:.3f}")
```

#### 获取统计信息

```python
stats = pipeline.get_stats()
print(stats)
# {
#   'clip_model': 'ViT-B-32',
#   'embedding_dim': 512,
#   'database': {
#     'total_embeddings': 20000,
#     'dimension': 512,
#     'index_type': 'IndexFlatL2'
#   }
# }
```

## 高级用法

### 1. 自定义 CLIP 模型

```python
encoder = CLIPEncoder(
    model_name="ViT-L-14",  # 更大的模型
    pretrained="openai",
    device="cuda",
    batch_size=16  # 较小批次因为模型更大
)
```

### 2. 使用 GPU 加速的 FAISS

```python
import faiss

# 创建 GPU 资源
res = faiss.StandardGpuResources()

# 创建 GPU 索引
cpu_index = faiss.IndexFlatL2(512)
gpu_index = faiss.index_cpu_to_gpu(res, 0, cpu_index)

# 在 VectorDatabase 中使用
db = VectorDatabase(dimension=512)
db.index = gpu_index
```

### 3. 多 GPU 推理

```python
import torch

# 设置主 GPU
torch.cuda.set_device(0)

# 初始化模型在不同 GPU 上
encoder_gpu0 = CLIPEncoder(device="cuda:0")
detector_gpu1 = GroundingDINODetector(device="cuda:1")
```

### 4. 批量处理优化

```python
from pathlib import Path
from tqdm import tqdm

image_dir = Path("test_images")
image_files = list(image_dir.glob("*.jpg"))

results_all = []

for img_file in tqdm(image_files):
    results = pipeline.process_image(img_file)
    results_all.append({
        'filename': img_file.name,
        'results': results
    })
```

## 错误处理

### 1. API 请求失败

```python
from requests.exceptions import RequestException

try:
    products = client.get_products()
except RequestException as e:
    print(f"API request failed: {e}")
    # 实现重试逻辑
```

### 2. 模型加载失败

```python
try:
    encoder = CLIPEncoder(model_name="ViT-B-32")
except Exception as e:
    print(f"Failed to load model: {e}")
    # 降级到 CPU 或使用备用模型
    encoder = CLIPEncoder(model_name="ViT-B-32", device="cpu")
```

### 3. 检测失败处理

```python
boxes, scores, labels = pipeline.detect_products(image)

if len(boxes) == 0:
    print("No products detected. Using full image.")
    # 使用整张图片进行识别
    results, similarities = pipeline.recognize_sku(image)
```

## 性能测试

```python
import time

# 测试编码速度
start = time.time()
embeddings = encoder.encode_image_paths(image_paths)
encode_time = time.time() - start
print(f"Encoding speed: {len(image_paths)/encode_time:.2f} images/sec")

# 测试搜索速度
start = time.time()
results, _ = db.search(query, k=5)
search_time = time.time() - start
print(f"Search time: {search_time*1000:.2f} ms")

# 测试端到端延迟
start = time.time()
results = pipeline.process_image(image)
total_time = time.time() - start
print(f"Total inference time: {total_time:.2f} s")
```
