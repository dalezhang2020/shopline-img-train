# SKU Recognition System using Grounding DINO + CLIP

无需人工标注的智能 SKU 识别系统，基于 Grounding DINO（零样本目标检测）+ CLIP（图像向量匹配）技术。

## 项目背景

构建一个**零标注、实时识别 SKU** 的仓储/展示场景产品识别系统。系统通过摄像头或拍照识别画面中的商品，并匹配对应的 SKU。

### 核心优势

- ✅ **零标注需求** - 无需人工标注数据集
- ✅ **快速部署** - 只需 SKU 官方图片即可上线
- ✅ **高扩展性** - 轻松支持新 SKU 的添加
- ✅ **准确识别** - 基于先进的深度学习模型

### 技术架构

```
Camera/Image Input
      ↓
Grounding DINO (Zero-shot Object Detection)
      ↓ [Bounding Boxes]
Crop Detected Regions
      ↓
CLIP Encoder (Feature Extraction)
      ↓
FAISS Vector Search
      ↓
Top-K SKU Matches + Similarity Scores
      ↓
Result Display (SKU + Bounding Box)
```

## 系统要求

### 硬件要求

- **GPU**: NVIDIA GPU with CUDA support (推荐)
- **内存**: 16GB+ RAM
- **存储**: 取决于 SKU 数量和图片大小

### 软件要求

- Python 3.8+
- CUDA 11.0+ (如使用 GPU)
- PyTorch 2.0+

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd shopline-img-train
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装 Grounding DINO

```bash
# 安装 groundingdino
pip install groundingdino-py

# 或者从源码安装
git clone https://github.com/IDEA-Research/GroundingDINO.git
cd GroundingDINO
pip install -e .
```

### 5. 下载模型权重

```bash
# 创建权重目录
mkdir -p models/weights

# 下载 Grounding DINO 权重
wget -P models/weights https://huggingface.co/ShilongLiu/GroundingDINO/resolve/main/groundingdino_swint_ogc.pth
```

### 6. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入 Shopline API 凭证
```

## 使用指南

### 第一步: 下载 SKU 数据

从 Shopline API 获取 SKU 和图片数据：

```bash
python scripts/download_sku_data.py \
  --config config/config.yaml \
  --download-images \
  --output-dir data/raw \
  --images-dir data/images
```

参数说明：
- `--config`: 配置文件路径
- `--download-images`: 是否下载产品图片
- `--output-dir`: SKU 数据保存目录
- `--images-dir`: 图片保存目录

### 第二步: 构建向量数据库

使用 CLIP 提取图片特征并构建 FAISS 索引：

```bash
python scripts/build_vector_db.py \
  --config config/config.yaml \
  --sku-data data/raw/sku_data.json \
  --images-dir data/images \
  --output-index data/embeddings/faiss_index.bin \
  --output-metadata data/embeddings/sku_metadata.pkl
```

参数说明：
- `--sku-data`: SKU 数据 JSON 文件
- `--images-dir`: SKU 图片目录
- `--output-index`: 输出 FAISS 索引路径
- `--output-metadata`: 输出元数据路径

### 第三步: 运行推理

对新图片进行 SKU 识别：

```bash
# 单张图片
python scripts/run_inference.py \
  test_image.jpg \
  --config config/config.yaml \
  --index data/embeddings/faiss_index.bin \
  --metadata data/embeddings/sku_metadata.pkl \
  --visualize \
  --output-dir output

# 批量处理
python scripts/run_inference.py \
  test_images/ \
  --config config/config.yaml \
  --index data/embeddings/faiss_index.bin \
  --metadata data/embeddings/sku_metadata.pkl \
  --visualize \
  --output-dir output
```

参数说明：
- `--index`: FAISS 索引文件
- `--metadata`: 元数据文件
- `--visualize`: 保存可视化结果
- `--output-dir`: 输出目录
- `--top-k`: 返回 top-k 个匹配结果（默认: 5）
- `--confidence`: 置信度阈值（默认: 0.7）
- `--text-prompt`: 自定义检测提示词（可选）

## 项目结构

```
shopline-img-train/
├── src/                        # 源代码
│   ├── api/                    # Shopline API 集成
│   │   └── shopline_client.py  # API 客户端
│   ├── models/                 # 模型模块
│   │   ├── clip_encoder.py     # CLIP 编码器
│   │   └── grounding_dino.py   # Grounding DINO 检测器
│   ├── database/               # 向量数据库
│   │   └── vector_db.py        # FAISS 数据库
│   ├── pipeline/               # 推理流程
│   │   └── inference.py        # SKU 识别 Pipeline
│   └── utils/                  # 工具函数
│       └── image_utils.py      # 图像处理
├── scripts/                    # 可执行脚本
│   ├── download_sku_data.py    # 下载 SKU 数据
│   ├── build_vector_db.py      # 构建向量数据库
│   └── run_inference.py        # 运行推理
├── config/                     # 配置文件
│   └── config.yaml             # 主配置
├── data/                       # 数据目录
│   ├── raw/                    # 原始 SKU 数据
│   ├── images/                 # SKU 图片
│   └── embeddings/             # 向量数据库
├── models/                     # 模型权重
│   └── weights/
├── output/                     # 输出结果
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
└── README.md                   # 项目文档
```

## 配置说明

### config/config.yaml

主要配置项：

```yaml
# Shopline API
shopline:
  api_url: "https://api.shoplineapp.com"
  access_token: ""  # 从环境变量读取

# CLIP 模型
clip:
  model_name: "ViT-B/32"  # 可选: ViT-B/16, ViT-L/14
  device: "cuda"
  batch_size: 32

# Grounding DINO
grounding_dino:
  box_threshold: 0.35      # 检测框置信度阈值
  text_threshold: 0.25     # 文本匹配阈值
  prompts:                 # 检测提示词
    - "retail product"
    - "furniture item"
    - "decor item"

# FAISS 向量数据库
faiss:
  index_type: "IndexFlatL2"  # 索引类型
  dimension: 512             # 向量维度

# 推理配置
inference:
  confidence_threshold: 0.7  # 识别置信度阈值
  top_k: 5                   # 返回 top-k 结果
```

## API 使用示例

### Python API

```python
from pathlib import Path
from src.pipeline.inference import SKURecognitionPipeline

# 初始化 Pipeline
pipeline = SKURecognitionPipeline(config_path='config/config.yaml')

# 加载向量数据库
pipeline.load_database(
    index_path=Path('data/embeddings/faiss_index.bin'),
    metadata_path=Path('data/embeddings/sku_metadata.pkl')
)

# 处理图片
results = pipeline.process_image(
    image='test.jpg',
    visualize=True,
    output_dir=Path('output')
)

# 查看结果
for result in results:
    print(f"SKU: {result['top_matches'][0]['sku']}")
    print(f"Similarity: {result['top_matches'][0]['similarity']:.3f}")
```

## 性能优化

### GPU 加速

确保在配置中启用 GPU：

```yaml
clip:
  device: "cuda"

grounding_dino:
  device: "cuda"
```

### FAISS 索引优化

对于大规模 SKU（>10,000），建议使用 IVF 索引：

```yaml
faiss:
  index_type: "IndexIVFFlat"
  nlist: 100  # 聚类数量
```

### 批处理

使用批处理提高吞吐量：

```yaml
clip:
  batch_size: 64  # 根据 GPU 内存调整
```

## 故障排除

### 1. CUDA Out of Memory

- 减小 `batch_size`
- 使用更小的 CLIP 模型（如 ViT-B/32）
- 使用 CPU 模式（较慢）

### 2. Grounding DINO 安装失败

```bash
# 手动安装依赖
pip install torch torchvision
pip install transformers
pip install groundingdino-py
```

### 3. API 连接失败

检查环境变量配置：
```bash
echo $SHOPLINE_ACCESS_TOKEN
echo $SHOPLINE_SHOP_NAME
```

## 技术细节

### Grounding DINO

- **功能**: 零样本目标检测
- **输入**: 图片 + 文本提示
- **输出**: 检测框 + 置信度
- **优势**: 无需训练即可检测新类别

### CLIP

- **功能**: 图像/文本特征提取
- **架构**: Vision Transformer
- **维度**: 512 (ViT-B/32)
- **优势**: 强大的跨模态表示能力

### FAISS

- **功能**: 高效向量相似度搜索
- **索引类型**:
  - IndexFlatL2: 精确搜索（小规模）
  - IndexIVFFlat: 近似搜索（大规模）
  - IndexHNSWFlat: 快速近似搜索
- **优势**: 亿级向量毫秒级检索

## 数据流程

1. **数据采集**: Shopline API → SKU 数据 + 图片
2. **特征提取**: CLIP Encoder → 512维向量
3. **索引构建**: FAISS → 向量数据库
4. **实时检测**: Grounding DINO → 商品定位
5. **特征匹配**: CLIP + FAISS → SKU 识别
6. **结果输出**: SKU + 置信度 + 边界框

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

---

**Built with ❤️ using Grounding DINO + CLIP**
