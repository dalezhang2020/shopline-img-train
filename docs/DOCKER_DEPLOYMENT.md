# Docker 部署指南

## 快速开始

### 1. 构建镜像

```bash
docker-compose build
```

### 2. 配置环境变量

确保 `.env` 文件已配置：

```bash
MYSQL_HOST=your_mysql_host
MYSQL_PORT=3306
MYSQL_DATABASE=hyt_bi
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
```

### 3. 启动容器

```bash
docker-compose up -d
```

### 4. 运行推理

```bash
# 单张图片推理
docker-compose exec sku-recognition python3 scripts/run_inference.py /app/test_images/test.jpg --visualize

# 批量推理
docker-compose exec sku-recognition python3 scripts/batch_inference.py /app/test_images --visualize
```

## 完整工作流

### 步骤 1: 下载数据并增强

```bash
docker-compose exec sku-recognition python3 scripts/download_and_augment.py \
  --enable-augmentation \
  --num-augmentations 5
```

### 步骤 2: 构建向量数据库

```bash
docker-compose exec sku-recognition python3 scripts/build_vector_db_augmented.py \
  --use-augmented
```

### 步骤 3: 运行推理

```bash
docker-compose exec sku-recognition python3 scripts/run_inference.py \
  /app/test_images/product.jpg \
  --visualize
```

## 仅使用 Docker（不用 docker-compose）

### 构建

```bash
docker build -t sku-recognition:latest .
```

### 运行

```bash
docker run --gpus all \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/test_images:/app/test_images \
  --env-file .env \
  sku-recognition:latest \
  python3 scripts/run_inference.py /app/test_images/test.jpg --visualize
```

## GPU 支持

### 安装 NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 验证 GPU

```bash
docker-compose exec sku-recognition nvidia-smi
```

## CPU 模式

如果没有 GPU，修改 `docker-compose.yml`:

```yaml
# 注释掉 GPU 配置
# deploy:
#   resources:
#     reservations:
#       devices:
#         - driver: nvidia
#           count: 1
#           capabilities: [gpu]

# 设置 CPU 模式
environment:
  - DEVICE=cpu
```

然后使用 CPU 版本的依赖：

```dockerfile
# Dockerfile 中使用
FROM python:3.10-slim
# 而不是 nvidia/cuda
```

## 数据持久化

重要的数据通过 volume 挂载：

```yaml
volumes:
  - ./data:/app/data              # SKU 数据和图片
  - ./output:/app/output          # 推理结果
  - ./logs:/app/logs              # 日志
  - ./models:/app/models          # 模型权重
  - ./config:/app/config          # 配置文件
```

## 常用命令

```bash
# 查看日志
docker-compose logs -f

# 进入容器
docker-compose exec sku-recognition bash

# 停止容器
docker-compose down

# 重启容器
docker-compose restart

# 查看容器状态
docker-compose ps

# 清理
docker-compose down -v  # 删除 volumes
```

## 生产部署建议

### 1. 使用固定版本

```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
# 而不是 latest
```

### 2. 健康检查

在 `docker-compose.yml` 添加：

```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import torch; torch.cuda.is_available()"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 3. 资源限制

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 16G
    reservations:
      memory: 8G
```

### 4. 日志管理

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 故障排除

### GPU 不可用

```bash
# 检查 nvidia-docker
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 检查容器内
docker-compose exec sku-recognition nvidia-smi
```

### 权限问题

```bash
# 给予执行权限
chmod +x scripts/*.sh scripts/*.py
```

### 内存不足

减少批处理大小或使用更小的模型：

```bash
# 设置环境变量
CLIP_MODEL=ViT-B/32  # 使用较小模型
```

## 性能优化

### 1. 使用 Docker BuildKit

```bash
DOCKER_BUILDKIT=1 docker-compose build
```

### 2. 多阶段构建

```dockerfile
# 构建阶段
FROM python:3.10 as builder
# ... 安装依赖

# 运行阶段
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
COPY --from=builder /usr/local/lib/python3.10 /usr/local/lib/python3.10
```

### 3. 缓存优化

把不常变化的层放在前面：

```dockerfile
# 先复制 requirements.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

# 后复制代码
COPY . .
```
