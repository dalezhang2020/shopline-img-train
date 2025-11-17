# System Architecture

## 系统架构概述

SKU 识别系统采用两段式架构：**检测 + 识别**

```
┌─────────────────────────────────────────────────────────────┐
│                        Input Image                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage 1: Object Detection                      │
│                  (Grounding DINO)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - Text-prompted detection                            │  │
│  │ - Zero-shot capability                               │  │
│  │ - Outputs: Bounding boxes + Confidence scores        │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Crop Detections                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage 2: Feature Extraction                    │
│                    (CLIP Encoder)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - Vision Transformer (ViT)                           │  │
│  │ - 512-dimensional embeddings                         │  │
│  │ - Normalized vectors                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage 3: Similarity Search                     │
│                   (FAISS Database)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - Vector similarity search                           │  │
│  │ - Cosine similarity / L2 distance                    │  │
│  │ - Top-K retrieval                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Final Results                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ SKU ID + Title + Category + Similarity Score         │  │
│  │ Bounding Box Coordinates                             │  │
│  │ Metadata (Price, Inventory, etc.)                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Grounding DINO Detector

**功能**: 零样本目标检测

**原理**:
- 结合 DINO (自监督学习) 和文本引导
- 使用 Transformer 架构
- 支持任意类别的文本提示

**输入**:
```python
{
    "image": PIL.Image,
    "text_prompt": "retail product. furniture item. decor item"
}
```

**输出**:
```python
{
    "boxes": [[x1, y1, x2, y2], ...],  # N个边界框
    "scores": [0.95, 0.87, ...],        # 置信度分数
    "labels": ["retail product", ...]   # 检测类别
}
```

**优势**:
- ✅ 零样本：无需训练即可检测新类别
- ✅ 灵活：通过文本提示控制检测目标
- ✅ 准确：SOTA 级别的检测性能

**配置参数**:
```yaml
box_threshold: 0.35   # 边界框置信度阈值
text_threshold: 0.25  # 文本匹配阈值
```

### 2. CLIP Encoder

**功能**: 图像特征提取

**架构**: Vision Transformer (ViT)

**模型选项**:
| 模型 | 参数量 | 速度 | 精度 | 向量维度 |
|------|--------|------|------|----------|
| ViT-B/32 | 151M | 快 | 中 | 512 |
| ViT-B/16 | 149M | 中 | 高 | 512 |
| ViT-L/14 | 427M | 慢 | 最高 | 768 |

**特征提取流程**:
```
Image (224x224x3)
    ↓ Patch Embedding
Patches (196x768)
    ↓ Transformer Encoder
Encoded Features (768)
    ↓ Projection Head
Embedding (512)
    ↓ L2 Normalization
Normalized Embedding (512)
```

**代码示例**:
```python
encoder = CLIPEncoder(model_name="ViT-B-32")
embedding = encoder.encode_image(image)
# embedding: (512,) float32, L2-normalized
```

### 3. FAISS Vector Database

**功能**: 高效向量相似度搜索

**索引类型**:

1. **IndexFlatL2** (精确搜索)
   - 暴力搜索所有向量
   - 100% 准确
   - 适用: < 100K 向量
   - 搜索时间: O(N)

2. **IndexIVFFlat** (近似搜索)
   - 倒排索引 + 聚类
   - 95-99% 准确
   - 适用: 100K - 10M 向量
   - 搜索时间: O(nlist + K)

3. **IndexHNSWFlat** (图索引)
   - 分层可导航小世界图
   - 98-99% 准确
   - 适用: 任意规模
   - 搜索时间: O(log N)

**相似度度量**:

- **L2 距离**: `distance = ||a - b||²`
  - 转换为相似度: `similarity = 1 / (1 + distance)`

- **内积 (IP)**: `similarity = a · b`
  - 当向量归一化时等价于余弦相似度
  - `cosine_similarity = (a · b) / (||a|| × ||b||)`

**性能对比**:

| 向量数量 | IndexFlat | IndexIVF | IndexHNSW |
|---------|-----------|----------|-----------|
| 10K     | 1ms       | 0.5ms    | 0.3ms     |
| 100K    | 10ms      | 2ms      | 1ms       |
| 1M      | 100ms     | 5ms      | 3ms       |
| 10M     | 1000ms    | 15ms     | 10ms      |

## 数据流

### 离线阶段: 构建向量数据库

```
┌─────────────────┐
│ Shopline API    │
│ - Products      │
│ - SKU Data      │
│ - Images        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Download        │
│ - 20K SKUs      │
│ - 20K Images    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ CLIP Encoder            │
│ - Batch process images  │
│ - Extract embeddings    │
│ - Normalize vectors     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ FAISS Index             │
│ - Add 20K embeddings    │
│ - Build index structure │
│ - Save to disk          │
└─────────────────────────┘
```

**时间估算** (20K SKUs):
- 下载图片: 10-30 分钟
- CLIP 编码: 15-30 分钟 (GPU)
- 构建索引: 1-2 分钟
- **总计**: ~30-60 分钟

### 在线阶段: 实时识别

```
┌─────────────────┐
│ Input Image     │
│ (任意分辨率)     │
└────────┬────────┘
         │ ~100ms
         ▼
┌─────────────────────────┐
│ Grounding DINO          │
│ - Detect products       │
│ - Return N bounding box │
└────────┬────────────────┘
         │ N crops
         ▼
┌─────────────────────────┐
│ Crop & Resize           │
│ - Extract N regions     │
│ - Resize to 224x224     │
└────────┬────────────────┘
         │ N images
         ▼
┌─────────────────────────┐
│ CLIP Encoder            │
│ - Batch encode N crops  │
│ - Get N embeddings      │
└────────┬────────────────┘
         │ ~50ms
         ▼
┌─────────────────────────┐
│ FAISS Search            │
│ - Search N queries      │
│ - Return top-K per query│
└────────┬────────────────┘
         │ ~10ms
         ▼
┌─────────────────────────┐
│ Results                 │
│ - N × K SKU matches     │
│ - With similarity scores│
└─────────────────────────┘
```

**延迟分析** (单张图片, GPU):
- Grounding DINO: 100-200ms
- 裁剪处理: 5-10ms
- CLIP 编码: 20-50ms
- FAISS 搜索: 1-10ms
- **总延迟**: ~150-300ms

## 扩展性分析

### 水平扩展

**场景 1: 增加 SKU 数量**

| SKU 数量 | 内存使用 | 搜索延迟 | 建议索引 |
|---------|---------|---------|---------|
| 1K      | ~2MB    | <1ms    | IndexFlat |
| 10K     | ~20MB   | ~1ms    | IndexFlat |
| 100K    | ~200MB  | ~10ms   | IndexIVF |
| 1M      | ~2GB    | ~15ms   | IndexIVF |
| 10M     | ~20GB   | ~20ms   | IndexHNSW |

**场景 2: 增加 QPS (每秒查询数)**

```
┌──────────────────┐
│ Load Balancer    │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ GPU 0 │ │ GPU 1 │
└───┬───┘ └──┬────┘
    │        │
    └────┬───┘
         │
┌────────▼────────┐
│ Shared FAISS DB │
└─────────────────┘
```

**吞吐量估算**:
- 单 GPU: ~10-20 QPS
- 2 GPUs: ~20-40 QPS
- 4 GPUs: ~40-80 QPS

### 垂直扩展

**优化策略**:

1. **模型量化**
   - FP32 → FP16: 2x 速度提升
   - INT8: 4x 速度提升

2. **批处理优化**
   - Batch size 1 → 32: 10x 吞吐量

3. **模型蒸馏**
   - ViT-L/14 → ViT-B/32: 3x 速度提升
   - 精度下降: ~2-3%

## 错误处理

### 检测失败

```python
if len(boxes) == 0:
    # 策略 1: 降低阈值重试
    detector.box_threshold = 0.25
    boxes, scores, labels = detector.detect(image, prompt)

if len(boxes) == 0:
    # 策略 2: 使用全图
    boxes = [[0, 0, width, height]]
    scores = [1.0]
    labels = ["unknown"]
```

### 识别低置信度

```python
if top_similarity < confidence_threshold:
    # 策略 1: 返回 top-K 供人工选择
    return {
        "status": "low_confidence",
        "candidates": top_k_results
    }

    # 策略 2: 触发人工审核
    send_to_manual_review(image, top_k_results)
```

## 监控指标

### 性能指标

1. **检测成功率**: 检测到至少 1 个物体的比例
2. **识别准确率**: Top-1 匹配正确的比例
3. **Top-5 召回率**: 正确 SKU 在 Top-5 中的比例
4. **平均置信度**: 所有识别结果的平均相似度
5. **平均延迟**: 端到端推理时间

### 系统指标

1. **GPU 利用率**: 目标 > 80%
2. **内存使用**: 监控 OOM 风险
3. **QPS**: 每秒处理请求数
4. **错误率**: 系统错误比例

## 安全性

### API 安全

- ✅ HTTPS 加密
- ✅ Token 认证
- ✅ Rate limiting
- ✅ Input validation

### 数据隐私

- ✅ 图片不持久化存储
- ✅ 日志脱敏
- ✅ 访问控制

### 模型安全

- ✅ 模型版本控制
- ✅ 输入异常检测
- ✅ 输出置信度检查
