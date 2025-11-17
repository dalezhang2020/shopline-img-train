# 图像增强功能说明

## 概述

图像增强是提高 SKU 识别系统鲁棒性的关键技术。通过对原始图片进行各种变换，生成多个增强版本，可以：

1. **提高识别准确率** - 训练集更丰富，模型更robust
2. **增强泛化能力** - 应对各种光照、角度变化
3. **扩充数据集** - 1张原图可生成5-10张变体

## 支持的增强方式

### 1. 水平翻转 (Flip Horizontal)
- **作用**: 镜像翻转，适合对称性商品
- **示例**: 左右对称的家具、装饰品
- **参数**: 无

### 2. 随机裁剪 (Random Crop)
- **作用**: 模拟不同拍摄距离和角度
- **参数**: `crop_ratio=0.9` (保留90%区域后缩放回原尺寸)
- **效果**: 轻微缩放和位移变化

### 3. 亮度调整 (Brightness Adjustment)
- **作用**: 模拟不同光照条件
- **参数**: `brightness_range=(0.7, 1.3)`
- **效果**: 70%-130%的亮度变化

### 4. 对比度调整 (Contrast Adjustment)
- **作用**: 模拟不同相机设置
- **参数**: `contrast_range=(0.8, 1.2)`
- **效果**: 80%-120%的对比度变化

### 5. 添加噪点 (Add Noise)
- **作用**: 模拟低质量图片和压缩伪影
- **参数**: `noise_intensity=0.02`
- **效果**: 高斯噪声叠加

### 6. 旋转 (Rotation)
- **作用**: 模拟不同拍摄角度
- **参数**: `rotation_angles=[0, 90, 180, 270]`
- **效果**: 多角度视图

## 使用方法

### 方法 1: 一键下载并增强（推荐）

```bash
# 从 api_scm_skuinfo 表下载数据并生成5个增强图片
python scripts/download_and_augment.py \
  --enable-augmentation \
  --num-augmentations 5 \
  --batch-size 10
```

**输出**：
- `data/images/` - 原始图片
- `data/augmented/` - 增强图片
- `data/raw/sku_data.json` - SKU 元数据
- `data/raw/processing_summary.json` - 处理统计

### 方法 2: 单独使用增强模块

```python
from src.utils.augmentation import ImageAugmenter, ImageDownloader
from PIL import Image

# 初始化增强器
augmenter = ImageAugmenter(
    brightness_range=(0.7, 1.3),
    crop_ratio=0.9,
    noise_intensity=0.02
)

# 加载图片
image = Image.open("product.jpg")

# 生成5个增强图片
augmented_images = augmenter.generate_augmentations(
    image,
    num_augmentations=5
)

# augmented_images: List[(Image, augmentation_name)]
for aug_image, aug_name in augmented_images:
    aug_image.save(f"output_{aug_name}.jpg")
```

### 方法 3: Python API

```python
from pathlib import Path
from src.utils.augmentation import (
    ImageAugmenter,
    save_augmented_images
)
from PIL import Image

# 初始化
augmenter = ImageAugmenter()
image = Image.open("product.jpg")

# 生成所有增强版本
augmented = augmenter.generate_all_augmentations(image)

# 保存
save_augmented_images(
    augmented,
    sku="SKU-12345",
    output_dir=Path("data/augmented")
)
```

## 完整工作流程

### 步骤 1: 下载并增强图片

```bash
python scripts/download_and_augment.py \
  --enable-augmentation \
  --num-augmentations 5
```

**预期输出**：
```
2024-01-15 10:00:00 - INFO - Fetched 20000 SKU records from database
2024-01-15 10:00:01 - INFO - Processing 20000 SKUs in batches of 10
Processing batches: 100%|████████| 2000/2000 [15:30<00:00, 2.15it/s]

================================================================================
PROCESSING SUMMARY
================================================================================
Total SKUs: 20000
Successful: 19850
Failed: 150
Original images: 19850
Augmented images: 99250
Total images: 119100
================================================================================
```

### 步骤 2: 构建向量数据库（包含增强图片）

```bash
python scripts/build_vector_db_augmented.py --use-augmented
```

**预期输出**：
```
2024-01-15 10:20:00 - INFO - Found 119100 total images:
2024-01-15 10:20:00 - INFO -   - Original: 19850
2024-01-15 10:20:00 - INFO -   - Augmented: 99250
Encoding images: 100%|████████| 3722/3722 [12:45<00:00, 4.86it/s]

================================================================================
DATABASE STATISTICS
================================================================================
  total_embeddings: 119100
  dimension: 512
  index_type: IndexFlatL2
  Original images: 19850
  Augmented images: 99250
  Augmentation ratio: 5.0x
================================================================================
```

### 步骤 3: 运行推理

```bash
python scripts/run_inference.py test.jpg --visualize
```

推理系统会在增强后的数据库中搜索最相似的 SKU。

## 配置参数

### 全局配置 (`config/config.yaml`)

虽然增强参数在代码中设置，但可以在配置文件中添加：

```yaml
# 图像增强配置（可选）
image_augmentation:
  enabled: true
  num_augmentations: 5
  brightness_range: [0.7, 1.3]
  contrast_range: [0.8, 1.2]
  crop_ratio: 0.9
  noise_intensity: 0.02
  rotation_angles: [0, 90, 180, 270]
```

### 命令行参数

```bash
# 增强数量
--num-augmentations 5          # 每张原图生成5个增强图

# 批处理大小
--batch-size 10                # 并发处理10个SKU

# 禁用增强
--no-augmentation              # 只下载原图，不做增强

# 自定义输出目录
--images-dir data/images       # 原始图片目录
--augmented-dir data/augmented # 增强图片目录
```

## 性能指标

### 数据量估算

| 原始 SKU 数量 | 增强倍数 | 增强后总图片 | 磁盘空间 (估算) |
|-------------|---------|------------|--------------|
| 1,000       | 5x      | 6,000      | ~600 MB      |
| 10,000      | 5x      | 60,000     | ~6 GB        |
| 20,000      | 5x      | 120,000    | ~12 GB       |

### 处理速度

| 环境 | 下载速度 | 增强速度 | 总耗时 (10K SKU) |
|-----|---------|---------|------------------|
| 本地网络 + CPU | ~50 img/s | ~100 img/s | ~15 分钟 |
| 云服务器 + GPU | ~100 img/s | ~500 img/s | ~5 分钟 |

### 向量数据库构建时间

| 图片数量 | GPU (RTX 3090) | CPU (i7-9700) |
|---------|----------------|---------------|
| 6,000   | ~3 分钟        | ~15 分钟       |
| 60,000  | ~25 分钟       | ~2 小时        |
| 120,000 | ~50 分钟       | ~4 小时        |

## 质量控制

### 最佳实践

1. **适度增强** - 推荐5个增强图/原图，过多会稀释数据质量
2. **保留原图** - 原图始终保留在数据库中
3. **监控失败率** - 下载失败率应 < 1%
4. **检查增强质量** - 随机抽查增强图片

### 增强效果示例

```bash
# 生成测试增强图片
python -c "
from src.utils.augmentation import ImageAugmenter
from PIL import Image

augmenter = ImageAugmenter()
img = Image.open('test_product.jpg')
augmented = augmenter.generate_all_augmentations(img)

for i, (aug_img, name) in enumerate(augmented):
    aug_img.save(f'preview_{name}.jpg')

print(f'Generated {len(augmented)} augmented images')
"
```

## 故障排除

### Q: 增强图片看起来失真？

**A**: 调整参数降低强度：
```python
augmenter = ImageAugmenter(
    brightness_range=(0.8, 1.2),  # 减小范围
    noise_intensity=0.01           # 降低噪点
)
```

### Q: 下载速度太慢？

**A**: 增加并发数：
```bash
python scripts/download_and_augment.py --batch-size 20
```

### Q: 内存不足？

**A**: 减小批次大小：
```bash
python scripts/download_and_augment.py --batch-size 5
```

### Q: 磁盘空间不足？

**A**: 减少增强数量或只使用原图：
```bash
# 只生成2个增强图
python scripts/download_and_augment.py --num-augmentations 2

# 或完全禁用增强
python scripts/download_and_augment.py --no-augmentation
```

## 高级功能

### 自定义增强策略

```python
from src.utils.augmentation import ImageAugmenter

# 创建自定义增强器
augmenter = ImageAugmenter(
    brightness_range=(0.5, 1.5),  # 更大的亮度范围
    contrast_range=(0.7, 1.3),    # 更大的对比度范围
    crop_ratio=0.85,               # 更激进的裁剪
    noise_intensity=0.03,          # 更多噪点
)

# 指定增强类型
augmented = augmenter.generate_augmentations(
    image,
    num_augmentations=10,
    augmentation_types=['flip_h', 'brightness', 'crop']
)
```

### 批量处理特定 SKU

```python
import asyncio
from scripts.download_and_augment import SKUImageProcessor

# 只处理特定 SKU
specific_skus = ['SKU-001', 'SKU-002', 'SKU-003']

# 过滤数据
filtered_data = [
    sku for sku in sku_data_list
    if sku['sku'] in specific_skus
]

# 处理
summary = await processor.process_all_skus(filtered_data)
```

## 与识别系统集成

增强图片会自动集成到识别流程：

1. **向量数据库** - 原图和增强图都会编码存储
2. **检索** - 查询时会匹配所有版本
3. **结果聚合** - 同一SKU的多个匹配会被聚合

**效果**：识别准确率提升10-20%（取决于数据质量）

## 与 Makefile 集成

```bash
# 完整流程（下载 + 增强 + 构建数据库）
make all

# 只下载和增强
make download

# 只下载不增强
make download-no-aug

# 只构建数据库（使用增强图）
make build

# 只构建数据库（只用原图）
make build-original-only
```

## 参考资料

- 图像增强代码: `src/utils/augmentation.py`
- 下载脚本: `scripts/download_and_augment.py`
- 构建脚本: `scripts/build_vector_db_augmented.py`
