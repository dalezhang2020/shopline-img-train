# SKU Recognition API - Quick Start Guide

快速入门指南，5分钟部署SKU识别API服务。

---

## ⚡ 30秒快速测试

如果你已经有向量数据库文件，可以立即启动：

```bash
cd /Users/dizhang/Gitlab/shopline-img-train

# 1. 检查向量数据库是否存在
ls -lh data/embeddings/

# 2. 启动 API 服务器
./scripts/start_api.sh

# 3. 打开浏览器测试
open http://localhost:8000/docs
```

---

## 🚀 完整5分钟部署

### 前置条件

✅ Python 3.9+ 已安装
✅ 已完成 `pip install -r requirements.txt`
✅ 有 MySQL 数据库连接（如果需要重新下载数据）

### 步骤 1: 配置环境变量 (1分钟)

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
vim .env  # 或使用你喜欢的编辑器
```

**必须配置的变量**：
```bash
# MySQL 数据库（如果需要下载数据）
MYSQL_HOST=your_mysql_host
MYSQL_PORT=3306
MYSQL_DATABASE=hyt_bi
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password

# 设备配置（Mac M4 Pro 使用 CPU）
DEVICE=cpu
CLIP_MODEL=ViT-L/14
```

### 步骤 2: 构建向量数据库 (2-3分钟)

#### 选项 A: 使用增强数据库（推荐）

```bash
python scripts/build_robust_vector_db.py --augment-per-image 2
```

⏱️ **预计时间**:
- 2,000 SKUs: ~5分钟
- 4,000 SKUs: ~10分钟
- 19,000 SKUs: ~30分钟

#### 选项 B: 使用基础数据库（更快）

```bash
python scripts/build_vector_db.py \
  --config config/config.yaml \
  --sku-data data/raw/sku_data.json \
  --images-dir data/images \
  --output-index data/embeddings/faiss_index.bin \
  --output-metadata data/embeddings/sku_metadata.pkl
```

⏱️ **预计时间**:
- 4,000 SKUs: ~3分钟
- 19,000 SKUs: ~15分钟

### 步骤 3: 启动 API 服务器 (30秒)

```bash
# 生产模式
./scripts/start_api.sh

# 或开发模式（热重载）
./scripts/start_api.sh --dev
```

**成功标志**：

```
🚀 Starting SKU Recognition API Server...
✅ Loaded environment variables from .env
✅ Python: Python 3.10.x
✅ Virtual environment activated
✅ All required packages installed
✅ Vector database found
   📊 Database size: 4109 SKUs
✅ Configuration file found

🚀 Server Configuration:
   Host:    0.0.0.0
   Port:    8000
   Workers: 1
   Mode:    Production

📝 Access the API documentation at:
   http://localhost:8000/docs (Swagger UI)
   http://localhost:8000/redoc (ReDoc)

INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 步骤 4: 测试 API (1分钟)

#### 测试 1: 健康检查

```bash
curl http://localhost:8000/api/v1/health
```

**预期输出**：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "database_size": 4109,
  "uptime_seconds": 10.5
}
```

#### 测试 2: SKU 识别

```bash
# 使用你的测试图片
curl -X POST http://localhost:8000/api/v1/recognize \
  -F "file=@data/images/DPH00685-BLK.jpg" \
  -F "top_k=5"
```

**预期输出**：
```json
{
  "success": true,
  "matches": [
    {
      "sku": "DPH00685-BLK",
      "similarity": 0.9876,
      "product_title": "Contemporary Sofa - Black",
      "category": "FURNITURE",
      "retail_price": 1299.99
    }
  ],
  "processing_time_ms": 175.4,
  "timestamp": "2025-11-17T12:34:56.789Z"
}
```

#### 测试 3: 使用 Swagger UI

1. 打开浏览器访问: http://localhost:8000/docs
2. 找到 `POST /api/v1/recognize` 端点
3. 点击 "Try it out"
4. 上传图片文件
5. 点击 "Execute"
6. 查看响应结果

---

## 🖥️ 前端集成 (可选)

### 前端项目路径

```bash
cd /Users/dizhang/Gitlab/wms-store
```

### 启动前端

```bash
# 安装依赖（如果还没安装）
npm install

# 启动开发服务器
npm run dev
```

### 访问 SKU 识别页面

1. 打开浏览器: http://localhost:3000
2. 登录系统
3. 导航到 **SKU识别** 菜单
4. 上传图片或使用相机拍照
5. 查看识别结果

---

## 📊 性能基准

### 识别速度（CPU - Apple M4 Pro）

| 操作 | 时间 | 备注 |
|------|------|------|
| 单张图片识别 | 170ms | 包含编码和搜索 |
| 批量5张 | 600ms | 并行处理 |
| 批量20张 | 2.5s | 最大批量 |

### 准确率（基于测试集）

| 数据库版本 | Top-1 | Top-5 |
|-----------|-------|-------|
| 基础版 | 50% | 94% |
| 2x增强版 | 65% | 97% ✅ |
| 5x增强版 | 70% | 98% |

---

## 🔧 常见问题

### 问题 1: 向量数据库文件不存在

**错误**：
```
FileNotFoundError: Vector database not found
```

**解决**：
```bash
# 构建向量数据库
python scripts/build_robust_vector_db.py --augment-per-image 2
```

### 问题 2: 端口 8000 被占用

**错误**：
```
[ERROR] error: Address already in use
```

**解决**：
```bash
# 方案 1: 更换端口
./scripts/start_api.sh --port 8001

# 方案 2: 停止占用进程
lsof -ti:8000 | xargs kill -9
```

### 问题 3: CUDA/GPU 错误（Mac）

**错误**：
```
RuntimeError: CUDA not available
```

**解决**：
```bash
# 在 .env 中设置
DEVICE=cpu
```

### 问题 4: FastAPI 未安装

**错误**：
```
ModuleNotFoundError: No module named 'fastapi'
```

**解决**：
```bash
pip install -r requirements.txt
```

### 问题 5: 识别速度慢

**原因**：图片过大或向量数据库过大

**优化**：
```bash
# 1. 调整图片大小
# 前端会自动压缩，但CLI可以手动处理：
convert input.jpg -resize 800x800 output.jpg

# 2. 使用 GPU（如果有）
DEVICE=cuda  # 在 .env 中

# 3. 减少 top_k 参数
curl -F "file=@image.jpg" -F "top_k=1" http://localhost:8000/api/v1/recognize
```

---

## 📈 下一步

### 提升准确率

1. **重建增强数据库**：
   ```bash
   python scripts/build_robust_vector_db.py --augment-per-image 5
   ```

2. **评估当前准确率**：
   ```bash
   python scripts/evaluate_accuracy.py
   ```

### 生产部署

1. **Docker 部署**：
   ```bash
   docker-compose up -d sku-recognition-api
   ```

2. **添加认证**：
   在 `.env` 中设置 `API_KEY`

3. **启用速率限制**：
   编辑 `config/config.yaml`，设置 `api.rate_limit.enabled: true`

4. **配置监控**：
   集成 Prometheus/Grafana

### API 高级用法

- [完整 API 文档](docs/API_DOCUMENTATION.md)
- [移动端拍照优化指南](docs/MOBILE_RECOGNITION_GUIDE.md)
- [性能优化指南](docs/PERFORMANCE_OPTIMIZATION.md)

---

## 💡 实用命令

```bash
# 查看 API 日志
tail -f logs/app.log

# 查看服务状态
curl http://localhost:8000/api/v1/stats

# 停止服务
# Ctrl+C 或 kill $(lsof -t -i:8000)

# 重启服务
./scripts/start_api.sh

# 测试单张图片（命令行）
python scripts/test_single_image.py data/images/test.jpg --top-k 10

# 批量测试
python scripts/test_sku_matching.py
```

---

## 🎯 总结

**你已成功完成**：
- ✅ 环境配置
- ✅ 向量数据库构建
- ✅ API 服务启动
- ✅ 功能测试

**现在可以**：
- 🚀 通过 API 识别 SKU
- 🖥️ 在前端页面使用拍照识别
- 📊 查看识别统计数据
- 🔧 进一步优化和部署

**需要帮助？**
- 查看 [完整文档](README.md)
- 查看 [API 文档](docs/API_DOCUMENTATION.md)
- 提交 [GitHub Issue](https://github.com/your-repo/issues)

祝使用愉快！🎉
