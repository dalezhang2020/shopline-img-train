# 向量数据库部署指南

## 📊 文件大小

5x 增强后的向量数据库文件：

```bash
data/embeddings/
├── faiss_index_robust_5x.bin      # 345 MB (FAISS 向量索引)
└── sku_metadata_robust_5x.pkl     # 9.7 MB (SKU 元数据)
```

**总大小**: ~355 MB

---

## ❌ 为什么不能推送到 Git？

1. **文件太大** - Git 不适合管理 300MB+ 的二进制文件
2. **频繁变化** - 每次更新 SKU 或重新训练都会改变
3. **CI/CD 性能** - 会严重拖慢 Git 克隆和 CI/CD 流程
4. **存储成本** - Git 会保存所有历史版本，浪费存储空间

---

## ✅ 推荐部署方案

### 方案 1：手动上传（推荐，最简单）

#### 1.1 首次部署

```bash
# 在本地执行 - 上传向量数据库到 AWS 服务器
rsync -avz --progress \
  /Users/dizhang/Gitlab/shopline-img-train/data/embeddings/ \
  your-user@your-aws-server:/opt/sku_recognition/data/embeddings/

# 或使用 scp
scp data/embeddings/faiss_index_robust_5x.bin \
    data/embeddings/sku_metadata_robust_5x.pkl \
    your-user@your-aws-server:/opt/sku_recognition/data/embeddings/
```

#### 1.2 更新向量数据库

每次重新训练后，重复上传步骤：

```bash
# 重新上传更新的文件
rsync -avz --progress \
  /Users/dizhang/Gitlab/shopline-img-train/data/embeddings/ \
  your-user@your-aws-server:/opt/sku_recognition/data/embeddings/

# SSH 到服务器重启 API
ssh your-user@your-aws-server
cd /opt/sku_recognition
docker-compose -f docker-compose.api.yml restart
```

#### 1.3 Docker Compose 自动挂载

`docker-compose.api.yml` 已配置自动挂载：

```yaml
volumes:
  # 向量数据库 (只读)
  - ./data/embeddings:/app/data/embeddings:ro
```

容器启动时会自动使用服务器上的向量数据库文件。

---

### 方案 2：使用 Git LFS（可选，适合团队协作）

如果你的团队需要版本控制向量数据库：

#### 2.1 安装 Git LFS

```bash
# macOS
brew install git-lfs

# Ubuntu
sudo apt install git-lfs

# 初始化
git lfs install
```

#### 2.2 配置 Git LFS

项目已创建 `.gitattributes` 文件：

```bash
# Git LFS 配置
data/embeddings/*.bin filter=lfs diff=lfs merge=lfs -text
data/embeddings/*.pkl filter=lfs diff=lfs merge=lfs -text
```

#### 2.3 提交大文件

```bash
# 添加向量数据库文件
git add data/embeddings/faiss_index_robust_5x.bin
git add data/embeddings/sku_metadata_robust_5x.pkl

# Git LFS 会自动处理大文件
git commit -m "feat: add 5x augmented vector database"
git push origin main
```

#### 2.4 在服务器上拉取

```bash
# 在 AWS 服务器上
cd /opt/sku_recognition
git lfs pull  # 下载 LFS 文件
```

**注意**: GitLab 免费版 LFS 配额有限（10GB），超出需要付费。

---

### 方案 3：使用云存储（生产环境最佳实践）

#### 3.1 上传到 S3/阿里云 OSS

```bash
# 上传到 AWS S3
aws s3 cp data/embeddings/faiss_index_robust_5x.bin \
  s3://your-bucket/embeddings/faiss_index_robust_5x.bin

aws s3 cp data/embeddings/sku_metadata_robust_5x.pkl \
  s3://your-bucket/embeddings/sku_metadata_robust_5x.pkl

# 或上传到阿里云 OSS
ossutil cp data/embeddings/faiss_index_robust_5x.bin \
  oss://your-bucket/embeddings/
```

#### 3.2 在服务器上下载

使用提供的下载脚本：

```bash
# 从 S3 下载
python scripts/download_embeddings.py \
  --source s3 \
  --s3-bucket your-bucket \
  --s3-prefix embeddings \
  --s3-region us-east-1

# 从 HTTP URL 下载
python scripts/download_embeddings.py \
  --source http \
  --http-url https://your-cdn.com/embeddings
```

#### 3.3 Docker 启动时自动下载

修改 `docker-compose.api.yml` 添加启动脚本：

```yaml
services:
  sku-recognition-api:
    # ... 其他配置
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        # 检查向量数据库是否存在，不存在则下载
        if [ ! -f /app/data/embeddings/faiss_index_robust_5x.bin ]; then
          echo "📥 向量数据库不存在，正在下载..."
          python scripts/download_embeddings.py --source s3 --s3-bucket your-bucket
        fi

        # 启动 API 服务器
        exec gunicorn scripts.api_server:app \
          --bind 0.0.0.0:6007 \
          --workers 4 \
          --worker-class uvicorn.workers.UvicornWorker \
          --threads 2 \
          --timeout 120 \
          --keepalive 5
```

---

## 🔄 更新工作流

### 本地训练 → AWS 部署

```bash
# 1. 本地重新训练模型
cd /Users/dizhang/Gitlab/shopline-img-train
python scripts/build_robust_vector_db.py --augment-per-image 5

# 2. 测试新的向量数据库
python scripts/test_sku_recognition.py

# 3. 上传到 AWS 服务器
rsync -avz --progress \
  data/embeddings/ \
  your-user@your-aws-server:/opt/sku_recognition/data/embeddings/

# 4. 重启 API 服务
ssh your-user@your-aws-server << EOF
  cd /opt/sku_recognition
  docker-compose -f docker-compose.api.yml restart
  docker-compose -f docker-compose.api.yml logs --tail=50
EOF

# 5. 测试生产环境
curl https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/health
```

---

## 📋 部署检查清单

### ✅ 首次部署

- [ ] 向量数据库文件已上传到服务器 (`rsync` 或 `scp`)
- [ ] 文件权限正确 (`chmod 644 data/embeddings/*`)
- [ ] 文件大小正确 (~345MB + ~10MB)
- [ ] Docker Compose 配置了 volume 挂载
- [ ] 容器能读取向量数据库文件

### ✅ 更新向量数据库

- [ ] 本地训练完成并验证准确率
- [ ] 上传新的向量数据库文件
- [ ] 重启 API 容器
- [ ] 验证 API 健康检查通过
- [ ] 测试识别功能正常

---

## 🛠️ 故障排除

### 问题 1: API 启动失败 "Vector database not found"

**原因**: 向量数据库文件未上传或路径错误

**解决**:

```bash
# 检查文件是否存在
ssh your-user@your-aws-server
ls -lh /opt/sku_recognition/data/embeddings/

# 如果不存在，上传文件
rsync -avz data/embeddings/ your-user@your-aws-server:/opt/sku_recognition/data/embeddings/
```

### 问题 2: Docker 容器无法读取文件

**原因**: 文件权限或 volume 挂载问题

**解决**:

```bash
# 检查文件权限
chmod 644 /opt/sku_recognition/data/embeddings/*

# 检查 Docker volume
docker inspect sku-recognition-api | grep -A 10 Mounts

# 进入容器检查
docker exec -it sku-recognition-api ls -lh /app/data/embeddings/
```

### 问题 3: rsync 上传速度慢

**原因**: 文件太大（345MB）

**解决**:

```bash
# 使用压缩传输
rsync -avz --compress --progress \
  data/embeddings/ \
  your-user@your-aws-server:/opt/sku_recognition/data/embeddings/

# 或先压缩再上传
cd data
tar -czf embeddings.tar.gz embeddings/
scp embeddings.tar.gz your-user@your-aws-server:/opt/sku_recognition/
ssh your-user@your-aws-server "cd /opt/sku_recognition && tar -xzf embeddings.tar.gz"
```

---

## 🎯 推荐方案总结

| 场景 | 推荐方案 | 优点 | 缺点 |
|------|---------|------|------|
| **个人项目** | 手动上传 (rsync) | 简单、直接 | 手动操作 |
| **团队协作** | Git LFS | 版本控制 | 配额限制 |
| **生产环境** | 云存储 (S3/OSS) | 自动化、CDN加速 | 需要配置 |

**建议**:

1. **现在**: 使用 rsync 手动上传（最快部署）
2. **短期**: 如果团队需要，配置 Git LFS
3. **长期**: 迁移到 S3/OSS，实现自动化部署

---

## 📞 快速命令参考

```bash
# 上传向量数据库
rsync -avz data/embeddings/ user@aws:/opt/sku_recognition/data/embeddings/

# 重启 API
ssh user@aws "cd /opt/sku_recognition && docker-compose -f docker-compose.api.yml restart"

# 检查健康状态
curl https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/health

# 查看 API 日志
ssh user@aws "cd /opt/sku_recognition && docker-compose -f docker-compose.api.yml logs -f"
```

---

**总结**: 向量数据库文件太大，不要推送到 Git。使用 rsync 手动上传到服务器，Docker Compose 会自动挂载。🚀
