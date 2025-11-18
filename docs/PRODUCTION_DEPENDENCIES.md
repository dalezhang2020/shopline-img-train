# 生产环境依赖管理指南

## 问题背景

在将训练项目部署到生产环境时，我们遇到了多次依赖缺失的问题。这个文档记录了所有的修复和最佳实践。

## 依赖分类

### 生产必需依赖 (requirements-prod.txt)

这些是 FastAPI 后端运行时**必须**的依赖：

```txt
# 核心 ML/AI
torch>=2.0.0
torchvision>=0.15.0
open-clip-torch>=2.20.0
faiss-cpu>=1.7.4

# 图像处理（最小化）
Pillow>=10.0.0
numpy>=1.24.0

# FastAPI 服务器
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
gunicorn>=21.2.0
python-multipart>=0.0.6

# 配置文件
pyyaml>=6.0
python-dotenv>=1.0.0
```

### 训练专用依赖（仅开发环境）

这些依赖**不应该**包含在生产镜像中：

```txt
# 对象检测（生产不需要）
opencv-python  # 导致: cv2 import errors
groundingdino

# 数据增强（仅训练时使用）
albumentations  # 需要 cv2
imgaug

# 数据库和 API 客户端（生产使用预构建向量数据库）
aiomysql  # 导致: aiomysql import errors
pymysql
aiohttp  # 导致: aiohttp import errors in augmentation.py
httpx

# 数据处理和进度条（训练脚本专用）
pandas
tqdm  # 已改为可选

# 开发工具
pytest
black
flake8
jupyter
```

## 代码中的可选依赖处理

### 1. cv2 (OpenCV)

**位置**: `src/utils/image_utils.py`, `src/models/grounding_dino.py`

**解决方案**: 条件导入 + PIL 降级

```python
# cv2 is optional - only needed for advanced numpy array operations
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# 使用时检查
if CV2_AVAILABLE:
    # Use cv2 for faster processing
    image = cv2.resize(...)
else:
    # Fallback to PIL
    pil_img = Image.fromarray(image)
    pil_img = pil_img.resize(size)
```

### 2. GroundingDINO (对象检测)

**位置**: `src/models/__init__.py`, `src/pipeline/inference.py`

**解决方案**: 条件导入 + 配置开关

```python
# src/models/__init__.py
try:
    from .grounding_dino import GroundingDINODetector
    __all__ = ["CLIPEncoder", "GroundingDINODetector"]
except ImportError:
    # 生产模式：cv2 未安装
    __all__ = ["CLIPEncoder"]

# config.yaml
grounding_dino:
  enabled: false  # 生产环境禁用
```

### 3. tqdm (进度条)

**位置**: `src/models/clip_encoder.py`

**解决方案**: 条件导入 + 优雅降级

```python
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# 使用时
if show_progress and TQDM_AVAILABLE:
    iterator = tqdm(iterator, desc="Processing...")
```

### 4. augmentation.py, mysql_client.py (训练工具)

**位置**: `src/utils/augmentation.py`, `src/api/mysql_client.py`

**解决方案**: Dockerfile 中排除这些文件

```dockerfile
# ❌ 错误: 复制整个 src 目录
COPY --chown=apiuser:apiuser src/ src/

# ✅ 正确: 只复制生产需要的文件
COPY --chown=apiuser:apiuser src/__init__.py src/
COPY --chown=apiuser:apiuser src/models/ src/models/
COPY --chown=apiuser:apiuser src/database/ src/database/
COPY --chown=apiuser:apiuser src/pipeline/ src/pipeline/
COPY --chown=apiuser:apiuser src/utils/__init__.py src/utils/
COPY --chown=apiuser:apiuser src/utils/image_utils.py src/utils/
```

## 生产环境运行模式

### process_image() 两种模式

```python
# 生产模式（无检测器）
if self.detector is None:
    # 直接对整张图片进行 SKU 识别
    embedding = self.clip_model.encode_image(image)
    results = self.vector_db.search(embedding, k=top_k)
    return formatted_results

# 训练模式（有检测器）
else:
    # 1. 检测产品
    boxes, scores = self.detector.detect(image)
    # 2. 裁剪每个检测区域
    crops = self.detector.crop_detections(image, boxes)
    # 3. 识别每个裁剪区域的 SKU
    for crop in crops:
        results = self.recognize_sku(crop)
```

## 依赖检查清单

在添加新功能之前，问自己：

### ✅ 新依赖检查

1. **这个依赖是生产运行时必需的吗？**
   - 是 → 添加到 `requirements-prod.txt`
   - 否 → 只添加到 `requirements.txt` (开发环境)

2. **如果这个依赖缺失，功能能否降级？**
   - 能 → 使用条件导入 (try/except)
   - 不能 → 添加到 `requirements-prod.txt`

3. **这个文件会被复制到生产镜像吗？**
   - 检查 Dockerfile 的 COPY 指令
   - 如果是训练脚本，确保它被排除

### ✅ 代码检查

在每个 Python 文件开头检查导入：

```bash
# 检查所有生产文件的导入
find src/models src/database src/pipeline src/utils/image_utils.py scripts/api_server.py \
  -name "*.py" -exec grep -h "^import\|^from" {} \; | sort -u
```

对比 `requirements-prod.txt`，确保：
- 所有导入的包都在 requirements-prod.txt 中
- 或者使用条件导入处理可选依赖

### ✅ Dockerfile 检查

```dockerfile
# Stage 1: Builder
COPY requirements-prod.txt .  # ← 确保使用 -prod 版本
RUN pip install -r requirements-prod.txt

# Stage 2: Runtime
# ← 只复制生产需要的文件
COPY --chown=apiuser:apiuser src/models/ src/models/
COPY --chown=apiuser:apiuser src/database/ src/database/
COPY --chown=apiuser:apiuser src/pipeline/ src/pipeline/
# ← 不要复制 src/utils/augmentation.py
COPY --chown=apiuser:apiuser src/utils/image_utils.py src/utils/
```

## 测试生产镜像

### 本地测试

```bash
# 1. 构建生产镜像
docker build -t sku-api-test .

# 2. 运行并检查启动日志
docker run --rm sku-api-test

# 3. 检查导入错误
docker run --rm sku-api-test python -c "
from src.pipeline.inference import SKURecognitionPipeline
from src.models.clip_encoder import CLIPEncoder
print('✅ All imports successful')
"
```

### 常见错误检查

```bash
# 检查是否有缺失的依赖
docker run --rm sku-api-test python -c "
import sys
import importlib

packages = ['torch', 'PIL', 'faiss', 'fastapi', 'open_clip']
for pkg in packages:
    try:
        importlib.import_module(pkg)
        print(f'✅ {pkg}')
    except ImportError as e:
        print(f'❌ {pkg}: {e}')
        sys.exit(1)
"
```

## 常见问题排查

### 问题 1: ModuleNotFoundError: No module named 'cv2'

**原因**: opencv-python 未安装（生产环境已移除）

**解决**:
1. 检查代码是否使用了条件导入
2. 确保有 PIL 降级方案
3. 如果必需，添加 opencv-python-headless 到 requirements-prod.txt

### 问题 2: ModuleNotFoundError: No module named 'aiohttp'

**原因**: 复制了不应该在生产环境的文件（如 augmentation.py）

**解决**:
1. 检查 Dockerfile COPY 指令
2. 排除训练专用文件
3. 或者在文件中使用条件导入

### 问题 3: ModuleNotFoundError: No module named 'tqdm'

**原因**: API 调用了批量处理方法

**解决**:
1. 确认 API 是否真的需要批量处理
2. 如果需要，添加 tqdm 到 requirements-prod.txt
3. 如果不需要，使用条件导入

## 最佳实践总结

1. **最小化原则**: 生产环境只安装真正需要的依赖
2. **条件导入**: 所有可选功能使用 try/except 导入
3. **配置开关**: 使用 config.yaml 控制可选功能
4. **选择性复制**: Dockerfile 只复制生产需要的文件
5. **定期检查**: 每次添加新功能后运行导入检查

## 当前生产环境状态

### ✅ 已优化

- ✅ cv2 (opencv-python) - 可选，有 PIL 降级
- ✅ GroundingDINO - 可选，配置控制
- ✅ tqdm - 可选，优雅降级
- ✅ augmentation.py - 已从镜像中排除
- ✅ mysql_client.py - 已从镜像中排除
- ✅ shopline_client.py - 已从镜像中排除

### 📊 镜像大小对比

- **完整依赖** (包含 cv2, albumentations): ~3.2 GB
- **生产优化** (当前): ~2.5 GB
- **节省**: ~700 MB (22%)

### 🚀 性能

- **启动时间**: ~30-45秒（包含下载向量数据库）
- **首次请求延迟**: ~200-300ms
- **后续请求**: ~100-200ms
- **内存使用**: ~2.5-3 GB per worker

## 更新记录

- 2025-11-18: 初始文档，记录所有依赖问题和解决方案
