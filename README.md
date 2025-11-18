# SKU Recognition System - AI-Powered Product Identification

无需人工标注的智能 SKU 识别系统，基于 CLIP（图像向量匹配）+ FAISS（向量检索）技术，提供REST API服务供前端调用。

🎯 **现在支持 REST API！** 可直接集成到 Next.js 前端，实现拍照识别功能。

## 项目背景

构建一个**零标注、实时识别 SKU** 的仓储/展示场景产品识别系统。系统通过摄像头或拍照识别画面中的商品，并匹配对应的 SKU。

### 核心优势

- ✅ **零标注需求** - 无需人工标注数据集
- ✅ **快速部署** - 只需 SKU 官方图片即可上线
- ✅ **高扩展性** - 轻松支持新 SKU 的添加
- ✅ **准确识别** - 基于先进的深度学习模型
- 🆕 **REST API** - 提供 FastAPI 服务，支持前端调用
- 🆕 **前端集成** - 配套 Next.js 前端页面，拍照即识别

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
# 编辑 .env 文件
```

## 快速开始 (API 服务模式)

### 🚀 启动 API 服务器

如果你已经有向量数据库，可以直接启动 API 服务器：

```bash
# 方式一：使用启动脚本（推荐）
chmod +x scripts/start_api.sh
./scripts/start_api.sh

# 方式二：直接运行
python -m uvicorn scripts.api_server:app --host 0.0.0.0 --port 8000

# 方式三：开发模式（热重载）
./scripts/start_api.sh --dev
```

API 服务将在 `http://localhost:8000` 启动。

### 📖 API 文档

启动后访问交互式 API 文档：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **详细文档**: [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)

### 🧪 测试 API

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 识别 SKU
curl -X POST http://localhost:8000/api/v1/recognize \
  -F "file=@test_image.jpg" \
  -F "top_k=5"
```

### 🖥️ 前端集成

前端代码位于 `/Users/dizhang/Gitlab/wms-store`：

1. 访问前端系统登录页面
2. 导航到 **SKU识别** 菜单
3. 上传图片或使用相机拍照
4. 查看识别结果

**前端页面路径**: `/admin/sku-recognition`

---

## 完整部署指南

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

### 第二步: 构建增强向量数据库（推荐）

使用数据增强技术提升识别准确率：

```bash
# 推荐：2x 数据增强（Top-1: 65%, Top-5: 97%）
python scripts/build_robust_vector_db.py --augment-per-image 2

# 可选：5x 数据增强（Top-1: 70%+, Top-5: 98%）
python scripts/build_robust_vector_db.py --augment-per-image 5
```

**增强效果对比**：
- 无增强：Top-1: 50%, Top-5: 94%
- 2x增强：Top-1: 65%, Top-5: 97% ✅ 推荐
- 5x增强：Top-1: 70%, Top-5: 98%

**或使用基础版本（不推荐）**：

```bash
python scripts/build_vector_db.py \
  --config config/config.yaml \
  --sku-data data/raw/sku_data.json \
  --images-dir data/images \
  --output-index data/embeddings/faiss_index.bin \
  --output-metadata data/embeddings/sku_metadata.pkl
```

### 第三步: 启动 API 服务器

```bash
# 启动服务
./scripts/start_api.sh

# 访问 API 文档
open http://localhost:8000/docs
```

### 第四步: 运行推理（命令行模式）

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
│   ├── api_server.py           # FastAPI 服务器 🆕
│   ├── start_api.sh            # 启动脚本 🆕
│   ├── download_sku_data.py    # 下载 SKU 数据
│   ├── build_robust_vector_db.py # 构建增强向量数据库 🆕
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
