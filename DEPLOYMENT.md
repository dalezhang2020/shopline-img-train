# 🚀 SKU 识别 API - 超简单部署指南

## ✅ 完成！向量数据库已上传到公开 S3

向量数据库已上传到公开 URL，容器启动时会**自动下载**，无需任何配置！

- ✅ FAISS 索引: https://s3.us-east-2.amazonaws.com/tools.zgallerie.com/model/faiss_index_robust_5x.bin (345 MB)
- ✅ SKU 元数据: https://s3.us-east-2.amazonaws.com/tools.zgallerie.com/model/sku_metadata_robust_5x.pkl (9.7 MB)

---

## 📦 三步部署（超简单）

### 1️⃣ 推送代码到 GitLab

```bash
# 添加所有文件
git add .

# 提交
git commit -m "feat: auto-download vector database from public S3"

# 推送（自动触发 CI/CD）
git push origin main
```

### 2️⃣ 等待 CI/CD 构建完成

1. 访问 GitLab 项目页面
2. 点击 **CI/CD > Pipelines**
3. 等待构建完成（约 5-10 分钟）

### 3️⃣ 在 AWS 服务器运行（一行命令）

```bash
# SSH 登录
ssh your-user@your-aws-server

# 登录 GitLab Registry
docker login registry.gitlab.com

# 拉取并运行（向量数据库自动下载）
docker pull registry.gitlab.com/your-group/shopline-img-train:latest && \
docker run -d \
  --name sku-recognition-api \
  --restart unless-stopped \
  -p 6007:6007 \
  registry.gitlab.com/your-group/shopline-img-train:latest

# 查看日志（会显示下载进度）
docker logs -f sku-recognition-api
```

**就是这样！** 容器启动时会自动从 S3 下载向量数据库（345MB），无需任何 AWS credentials！

---

## 📊 启动日志示例

```
===========================================
SKU Recognition API - Starting...
===========================================
📥 Downloading vector database from S3...
   FAISS: https://s3.us-east-2.amazonaws.com/.../faiss_index_robust_5x.bin
   Metadata: https://s3.us-east-2.amazonaws.com/.../sku_metadata_robust_5x.pkl

Downloading FAISS index (345 MB)...
######################################################################## 100.0%
✓ FAISS index downloaded

Downloading SKU metadata (9.7 MB)...
######################################################################## 100.0%
✓ SKU metadata downloaded

✓ Vector database downloaded successfully
total 354M
-rw-r--r-- 1 apiuser apiuser 345M Nov 17 23:00 faiss_index_robust_5x.bin
-rw-r--r-- 1 apiuser apiuser 9.7M Nov 17 23:00 sku_metadata_robust_5x.pkl

Starting Gunicorn + Uvicorn workers...
Port: 6007
Workers: 4
===========================================

[INFO] Uvicorn running on http://0.0.0.0:6007
```

---

## ✅ 验证部署

### 1. 检查容器状态

```bash
docker ps | grep sku-recognition
```

应该看到容器正在运行。

### 2. 健康检查

```bash
# 本地测试
curl http://localhost:6007/sku_recognition_fastapi/api/v1/health

# 应该返回
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "database_size": 4109
}
```

### 3. 配置 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name tools.zgallerie.com;

    location /sku_recognition_fastapi/ {
        proxy_pass http://127.0.0.1:6007/sku_recognition_fastapi/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        client_max_body_size 10M;
    }
}
```

重启 Nginx：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 4. 测试生产环境

```bash
curl https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/health
```

---

## 🔄 更新部署

### 更新代码

```bash
# 1. 推送新代码
git push origin main

# 2. 等待 CI/CD 构建

# 3. 在服务器上更新
docker pull registry.gitlab.com/your-group/shopline-img-train:latest
docker stop sku-recognition-api
docker rm sku-recognition-api
# 重新运行容器（使用上面的命令）
```

### 更新向量数据库

```bash
# 1. 上传新文件到 S3（覆盖旧文件）
aws s3 cp data/embeddings/faiss_index_robust_5x.bin \
  s3://tools.zgallerie.com/model/faiss_index_robust_5x.bin --acl public-read

aws s3 cp data/embeddings/sku_metadata_robust_5x.pkl \
  s3://tools.zgallerie.com/model/sku_metadata_robust_5x.pkl --acl public-read

# 2. 重启容器（会重新下载）
docker restart sku-recognition-api
```

---

## 🎯 核心优势

### ✅ 无需 AWS Credentials

向量数据库托管在公开 S3 URL，容器启动时使用 `curl` 直接下载，无需任何 AWS 访问密钥！

### ✅ 零配置

不需要设置任何环境变量，默认配置即可工作：

```bash
# 最简单的运行方式
docker run -d -p 6007:6007 your-image:latest
```

### ✅ 自动下载

第一次启动时自动下载向量数据库，后续启动会跳过下载（文件已存在）。

### ✅ 可自定义

如果需要使用不同的 URL：

```bash
docker run -d -p 6007:6007 \
  -e FAISS_URL="https://your-url/faiss.bin" \
  -e METADATA_URL="https://your-url/metadata.pkl" \
  your-image:latest
```

---

## 📁 部署架构

```
GitLab Repository
  ├── 代码
  └── Dockerfile (包含公开 S3 URL)
       ↓
GitLab CI/CD
  └── 自动构建 Docker 镜像
       ↓
Container Registry
  └── 存储镜像
       ↓
AWS 服务器
  └── docker run (一行命令)
       ↓
  启动时从公开 S3 自动下载向量数据库
       ↓
  API 就绪！
```

---

## 🛠️ 环境变量（可选）

所有环境变量都有默认值，通常不需要修改：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FAISS_URL` | `https://s3.us-east-2.amazonaws.com/...` | FAISS 索引下载 URL |
| `METADATA_URL` | `https://s3.us-east-2.amazonaws.com/...` | 元数据下载 URL |
| `SKIP_DOWNLOAD` | `false` | 跳过下载（用于本地开发） |
| `CORS_ORIGINS` | - | CORS 允许的域名 |

---

## 🐛 故障排除

### 问题 1: 下载失败

```bash
# 手动测试下载 URL
curl -I https://s3.us-east-2.amazonaws.com/tools.zgallerie.com/model/faiss_index_robust_5x.bin

# 应该返回 200 OK
```

### 问题 2: 容器启动慢

第一次启动需要下载 345MB，根据网络速度可能需要几分钟：

```bash
# 查看下载进度
docker logs -f sku-recognition-api
```

### 问题 3: API 无响应

```bash
# 检查容器日志
docker logs sku-recognition-api

# 检查端口
netstat -tlnp | grep 6007

# 进入容器调试
docker exec -it sku-recognition-api bash
```

---

## 📊 性能指标

- **Docker 镜像大小**: ~2.5 GB
- **向量数据库下载**: 355 MB（首次启动）
- **启动时间**:
  - 首次（含下载）: 2-5 分钟（取决于网络）
  - 后续启动: 30-60 秒
- **内存占用**: 4-8 GB
- **吞吐量**: 18-20 req/s（4 workers）

---

## 🎉 完成！

现在你只需要：

1. ✅ 推送代码到 GitLab
2. ✅ 等待 CI/CD 构建
3. ✅ 在服务器上运行一行 `docker run` 命令

**就是这么简单！** 🚀

详细信息请参考：
- [README_DEPLOYMENT.md](README_DEPLOYMENT.md) - 快速部署指南
- [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) - API 接口文档
