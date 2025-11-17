# Quick Start Guide

快速开始使用 SKU 识别系统

## 5分钟快速开始

### 1. 安装依赖 (1-2分钟)

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install groundingdino-py
```

### 2. 配置 API (1分钟)

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

填入你的 Shopline API 凭证：
```
SHOPLINE_ACCESS_TOKEN=your_token_here
SHOPLINE_SHOP_NAME=your_shop_name
```

### 3. 下载 SKU 数据 (1-5分钟，取决于数据量)

```bash
python scripts/download_sku_data.py --download-images
```

这将：
- 从 Shopline API 获取所有产品
- 提取 SKU 信息
- 下载产品图片到 `data/images/`

### 4. 构建向量数据库 (2-10分钟，取决于 SKU 数量)

```bash
python scripts/build_vector_db.py
```

这将：
- 使用 CLIP 编码所有 SKU 图片
- 构建 FAISS 向量索引
- 保存到 `data/embeddings/`

### 5. 运行推理 (几秒钟)

```bash
# 准备一张测试图片
python scripts/run_inference.py your_test_image.jpg --visualize
```

查看结果：
- JSON 结果: `output/your_test_image_results.json`
- 可视化图片: `output/your_test_image_result.jpg`

## 详细步骤

### 选项1: 使用 CPU（无需 GPU）

修改 `config/config.yaml`:

```yaml
clip:
  device: "cpu"
  batch_size: 8  # CPU 模式使用较小批次

grounding_dino:
  device: "cpu"
```

**注意**: CPU 模式会慢很多，但不需要 GPU。

### 选项2: 使用 GPU（推荐）

确保已安装 CUDA 和 PyTorch GPU 版本：

```bash
# 检查 CUDA
nvidia-smi

# 安装 PyTorch GPU 版本
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

配置使用 GPU（默认设置）：

```yaml
clip:
  device: "cuda"
  batch_size: 32

grounding_dino:
  device: "cuda"
```

### 下载 Grounding DINO 权重（可选）

如果自动下载失败：

```bash
# 创建目录
mkdir -p models/weights

# 手动下载
wget https://huggingface.co/ShilongLiu/GroundingDINO/resolve/main/groundingdino_swint_ogc.pth \
  -O models/weights/groundingdino_swint_ogc.pth
```

更新配置：

```yaml
grounding_dino:
  checkpoint_path: "models/weights/groundingdino_swint_ogc.pth"
```

## 常见问题

### Q: 如何测试系统是否正常工作？

使用内置的 fallback 模式测试：

```python
from src.pipeline.inference import SKURecognitionPipeline
from pathlib import Path

pipeline = SKURecognitionPipeline()
pipeline.load_database(
    Path('data/embeddings/faiss_index.bin'),
    Path('data/embeddings/sku_metadata.pkl')
)

results = pipeline.process_image('test.jpg')
print(results)
```

### Q: 数据库构建需要多长时间？

| SKU 数量 | GPU 时间 | CPU 时间 |
|---------|---------|---------|
| 1,000   | ~2 分钟  | ~10 分钟 |
| 10,000  | ~15 分钟 | ~2 小时  |
| 20,000  | ~30 分钟 | ~4 小时  |

### Q: 推理速度如何？

| 设备 | 检测时间 | 识别时间 | 总时间 |
|-----|---------|---------|-------|
| GPU (RTX 3090) | ~0.2s | ~0.05s | ~0.25s |
| GPU (RTX 2060) | ~0.5s | ~0.1s  | ~0.6s  |
| CPU (i7-9700)  | ~5s   | ~0.5s  | ~5.5s  |

### Q: 如何提高识别准确率？

1. **使用高质量的 SKU 图片**
   - 清晰、高分辨率
   - 白色或纯色背景
   - 正面拍摄

2. **调整检测阈值**
   ```yaml
   grounding_dino:
     box_threshold: 0.25  # 降低以检测更多物体
     text_threshold: 0.20
   ```

3. **调整识别阈值**
   ```yaml
   inference:
     confidence_threshold: 0.6  # 降低以接受更多匹配
   ```

4. **优化检测提示词**
   ```yaml
   grounding_dino:
     prompts:
       - "furniture product"  # 更具体的描述
       - "home decor item"
   ```

### Q: 如何更新 SKU 数据库？

重新运行数据下载和构建步骤：

```bash
# 1. 下载新数据
python scripts/download_sku_data.py --download-images

# 2. 重新构建数据库
python scripts/build_vector_db.py
```

数据库会自动替换旧版本。

## 下一步

- 📖 阅读完整文档: [README.md](README.md)
- 🔧 自定义配置: `config/config.yaml`
- 🧪 运行测试: `pytest tests/`
- 📊 查看性能优化建议

---

如有问题，请查看 [README.md](README.md) 的故障排除部分。
