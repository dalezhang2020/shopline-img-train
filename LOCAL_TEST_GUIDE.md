# 本地 Gunicorn 测试指南

## 快速开始

### 选项 1: 快速测试（推荐用于调试）

单个 worker，开启 debug 日志，支持热重载：

```bash
./test_api_quick.sh
```

特点：
- ✅ 1 个 worker（启动快，便于调试）
- ✅ Debug 日志级别（详细错误信息）
- ✅ 热重载（修改代码自动重启）
- ✅ 端口：6007

### 选项 2: 生产配置测试

完全模拟 Docker 生产环境：

```bash
./test_gunicorn_local.sh
```

特点：
- ✅ 2 个 workers（与生产一致）
- ✅ `--preload` 启用（测试模型共享）
- ✅ 所有生产环境变量
- ✅ 端口：6007

## 手动测试命令

### 最简单的测试（单 worker，无 preload）

```bash
export PYTHONPATH=/Users/dizhang/Gitlab/shopline-img-train
export DEVICE=cpu

gunicorn scripts.api_server:app \
    --bind 0.0.0.0:6007 \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --log-level debug
```

### 测试 --preload 参数（2 workers）

```bash
gunicorn scripts.api_server:app \
    --bind 0.0.0.0:6007 \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --preload \
    --log-level info
```

## 测试 API 端点

启动成功后，在新终端测试：

### 1. 健康检查

```bash
curl http://localhost:6007/sku_recognition_fastapi/api/v1/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "database_size": 20545,
  "uptime_seconds": 10.5
}
```

### 2. 查看 API 文档

浏览器访问：
```
http://localhost:6007/sku_recognition_fastapi/docs
```

### 3. 测试图片识别

```bash
# 使用本地图片
curl -X POST "http://localhost:6007/sku_recognition_fastapi/api/v1/recognize?top_k=5&confidence_threshold=0.7" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/image.jpg"
```

## 常见问题排查

### 问题 1: 端口已被占用

```
ERROR: bind(): Address already in use
```

**解决**：
```bash
# 查找占用 6007 端口的进程
lsof -i :6007

# 杀死进程
kill -9 <PID>

# 或使用不同端口
gunicorn ... --bind 0.0.0.0:8000
```

### 问题 2: 向量数据库未找到

```
FileNotFoundError: Vector database not found
```

**检查**：
```bash
ls -lh data/embeddings/faiss_index_robust_5x.bin
ls -lh data/embeddings/sku_metadata_robust_5x.pkl
```

如果文件不存在，需要先构建或下载：
```bash
# 从 S3 下载（如果有访问权限）
curl -o data/embeddings/faiss_index_robust_5x.bin \
  https://s3.us-east-2.amazonaws.com/tools.zgallerie.com/model/faiss_index_robust_5x.bin

curl -o data/embeddings/sku_metadata_robust_5x.pkl \
  https://s3.us-east-2.amazonaws.com/tools.zgallerie.com/model/sku_metadata_robust_5x.pkl
```

### 问题 3: 模块导入错误

```
ModuleNotFoundError: No module named 'xxx'
```

**解决**：
```bash
# 安装生产依赖
pip install -r requirements-prod.txt

# 或安装开发依赖（包含所有工具）
pip install -r requirements.txt
```

### 问题 4: CLIP 模型下载慢

首次启动会下载 CLIP 模型（~1.5GB），可能需要几分钟。

**解决**：
- 等待下载完成
- 或预先下载：
  ```bash
  python -c "import open_clip; open_clip.create_model_and_transforms('ViT-L-14', pretrained='openai')"
  ```

### 问题 5: 内存不足（本地 Mac）

如果本地内存有限，减少 workers：

```bash
# 只用 1 个 worker
gunicorn scripts.api_server:app \
    --bind 0.0.0.0:6007 \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker
```

## 性能监控

### 查看实时日志

Gunicorn 会输出到终端，包括：
- 请求日志（access log）
- 错误日志（error log）
- Worker 状态

### 查看内存使用

```bash
# macOS
ps aux | grep gunicorn

# 详细内存信息
top -pid $(pgrep gunicorn | head -1)
```

### 查看 Python 进程

```bash
# 查看所有 gunicorn 进程
pgrep -fl gunicorn

# 查看进程树
pstree -p $(pgrep gunicorn | head -1)
```

## 停止服务

### 方法 1: Ctrl+C

在运行 Gunicorn 的终端按 `Ctrl+C`

### 方法 2: 杀死进程

```bash
# 查找主进程
pgrep -f "gunicorn scripts.api_server"

# 杀死所有 gunicorn 进程
pkill -f "gunicorn scripts.api_server"
```

## 调试技巧

### 1. 启用 Python 调试模式

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

python -m pdb scripts/api_server.py
```

### 2. 只测试导入（不启动服务）

```bash
python -c "
from scripts.api_server import app
from src.pipeline.inference import SKURecognitionPipeline
print('✅ All imports successful')
"
```

### 3. 测试单个请求（不用 Gunicorn）

```bash
# 使用 Uvicorn 直接运行（更简单）
uvicorn scripts.api_server:app --host 0.0.0.0 --port 6007 --reload
```

### 4. 查看详细启动日志

```bash
gunicorn scripts.api_server:app \
    --bind 0.0.0.0:6007 \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --log-level debug \
    --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
```

## 对比 Docker vs 本地

| 特性 | 本地测试 | Docker 生产 |
|------|----------|-------------|
| 启动速度 | 快 (10-30秒) | 慢 (30-60秒) |
| 热重载 | ✅ 支持 | ❌ 不支持 |
| 调试 | ✅ 容易 | ❌ 困难 |
| 环境一致性 | ⚠️ 可能不同 | ✅ 完全一致 |
| 依赖管理 | 手动 | 自动 |
| 向量数据库 | 本地文件 | S3 自动下载 |

## 建议工作流程

1. **本地快速测试** → `./test_api_quick.sh`
   - 验证代码逻辑
   - 测试 API 端点
   - 调试错误

2. **本地生产配置测试** → `./test_gunicorn_local.sh`
   - 测试 `--preload` 参数
   - 验证多 worker 配置
   - 测试内存使用

3. **Docker 测试** → `docker build && docker run`
   - 验证完整生产环境
   - 测试 S3 下载
   - 最终验证

4. **GitLab CI/CD 部署** → `git push`
   - 自动构建镜像
   - 部署到生产

## 下一步

测试成功后：
1. 确认所有 API 端点正常工作
2. 测试几张真实产品图片
3. 检查内存使用是否合理
4. 推送到 GitLab 触发 CI/CD
