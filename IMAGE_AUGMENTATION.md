# 图片数据增强工具

## 功能说明

本工具从 MySQL 数据库读取 SKU 图片数据，并对每张图片进行数据增强处理，包括：

1. **镜像翻转** (Horizontal Flip) - 水平翻转图片
2. **随机裁剪** (Random Crop) - 随机裁剪图片并调整回原尺寸
3. **亮度调整** (Brightness Adjustment) - 随机调整图片亮度
4. **添加噪点** (Noise Addition) - 添加随机噪点

## 项目结构

```
shopline-img-train/
├── image_config.py           # 配置文件
├── image_augmentation.py     # 图片增强模块
├── augment_images.py         # 主执行脚本
├── requirements.txt          # 依赖包
└── augmented_images/         # 输出目录（自动创建）
    └── {SKU}/                # 每个 SKU 一个文件夹
        ├── {SKU}_original.jpg
        ├── {SKU}_flip_1.jpg
        ├── {SKU}_crop_2.jpg
        ├── {SKU}_brightness_3.jpg
        └── {SKU}_noise_4.jpg
```

## 数据库配置

默认配置（在 `image_config.py` 中）：

- **Host**: am-bp1ch634s7l1264ft167320o.ads.aliyuncs.com
- **User**: dale_admin
- **Password**: DaleAdmin2024#
- **Database**: hyt_bi
- **Port**: 3306

**查询语句**:
```sql
SELECT SKU, ProductGroup, image_url
FROM api_scm_skuinfo
WHERE `ProductGroup` <> '**' AND `image_url` <> '**'
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 基本使用（处理所有 SKU）

```bash
python augment_images.py
```

### 2. 测试模式（只处理前 10 个 SKU）

修改 `augment_images.py` 的最后部分：

```python
if __name__ == "__main__":
    asyncio.run(main())
```

改为：

```python
async def main():
    pipeline = ImageAugmentationPipeline()
    await pipeline.run(limit=10)  # 只处理 10 个 SKU

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. 自定义配置

在 `image_config.py` 中修改配置参数：

```python
class ImageAugmentationSettings(BaseSettings):
    # 输出目录
    output_dir: str = "augmented_images"

    # 增强参数
    brightness_range: tuple = (0.7, 1.3)  # 亮度范围
    crop_ratio: float = 0.9               # 裁剪比例
    noise_intensity: float = 0.02         # 噪点强度

    # 每张原图生成的增强图片数量
    augmentations_per_image: int = 5

    # 批处理大小
    batch_size: int = 10
```

## 输出结果

### 目录结构

```
augmented_images/
├── SKU001/
│   ├── SKU001_original.jpg      # 原图
│   ├── SKU001_flip_1.jpg        # 镜像翻转
│   ├── SKU001_crop_2.jpg        # 随机裁剪
│   ├── SKU001_brightness_3.jpg  # 亮度调整
│   ├── SKU001_noise_4.jpg       # 添加噪点
│   └── SKU001_flip_5.jpg        # 随机选择的增强
├── SKU002/
│   └── ...
└── ...
```

### 日志输出

运行时会显示详细的处理进度：

```
2025-01-17 10:00:00 - __main__ - INFO - Starting image augmentation pipeline...
2025-01-17 10:00:01 - __main__ - INFO - Fetched 100 SKU records from database
2025-01-17 10:00:01 - __main__ - INFO - Total SKUs to process: 100
2025-01-17 10:00:01 - __main__ - INFO - Processing batch 1/10 (10 SKUs)
2025-01-17 10:00:05 - __main__ - INFO - Successfully processed SKU: SKU001 (6 images)
...
2025-01-17 10:05:00 - __main__ - INFO - ============================================================
2025-01-17 10:05:00 - __main__ - INFO - Image Augmentation Pipeline Completed
2025-01-17 10:05:00 - __main__ - INFO - Total SKUs processed: 100
2025-01-17 10:05:00 - __main__ - INFO - Successful: 95
2025-01-17 10:05:00 - __main__ - INFO - Failed: 5
2025-01-17 10:05:00 - __main__ - INFO - Total augmented images: 570
2025-01-17 10:05:00 - __main__ - INFO - Output directory: augmented_images
2025-01-17 10:05:00 - __main__ - INFO - Execution time: 300.00 seconds
2025-01-17 10:05:00 - __main__ - INFO - ============================================================
```

## 增强效果说明

1. **镜像翻转 (Flip)**: 水平镜像，适用于对称的产品
2. **随机裁剪 (Crop)**: 保留 90% 的图片内容，模拟不同的拍摄距离
3. **亮度调整 (Brightness)**: 亮度范围 0.7-1.3，模拟不同的光照条件
4. **添加噪点 (Noise)**: 强度 0.02，模拟图片噪声

## 性能优化

- 使用异步 I/O 处理网络请求
- 批量处理 SKU（默认 batch_size=10）
- 并发下载和处理图片
- 连接池管理数据库连接

## 故障排除

### 1. 数据库连接失败

检查网络连接和数据库凭证是否正确。

### 2. 图片下载失败

某些图片 URL 可能无效或无法访问，这些会被记录在日志中并跳过。

### 3. 内存不足

如果处理大量图片，可以减小 `batch_size` 或 `augmentations_per_image`。

## 技术栈

- **Python 3.8+**
- **SQLAlchemy**: 数据库 ORM
- **aiomysql**: 异步 MySQL 驱动
- **Pillow**: 图片处理
- **aiohttp**: 异步 HTTP 客户端
- **NumPy**: 数值计算
