# 最新修改总结 (Latest Changes)

## ✅ 已推送到 GitLab 和 GitHub

### 📦 仓库信息
- **GitLab**: https://gitlab.com/dalez/fastapi/shopline-img-train.git
  - 分支: `sku-dedup-cors-fix` (准备部署的分支)
  - 合并请求: https://gitlab.com/dalez/fastapi/shopline-img-train/-/merge_requests/new?merge_request%5Bsource_branch%5D=sku-dedup-cors-fix

- **GitHub**: https://github.com/dalezhang2020/shopline-img-train.git
  - 分支: `main`

---

## 🔧 核心修改 (共4个提交)

### 1️⃣ SKU 去重功能 - `59d4849`
**文件**: [`src/pipeline/inference.py`](src/pipeline/inference.py#L199-L329)

**问题**: API 返回重复的 SKU（同一个 SKU 出现 3-5 次）
```json
{
  "matches": [
    {"sku": "CHLB0971-BGE", "similarity": 0.895},
    {"sku": "CHLB0971-BGE", "similarity": 0.880},  // 重复
    {"sku": "FSF11292-ALP", "similarity": 0.880},
    {"sku": "CHLB0971-BGE", "similarity": 0.879},  // 重复
    {"sku": "FSF11294-ALP", "similarity": 0.873}
  ]
}
```

**原因**:
- Vector database 包含 117,738 个向量
- 每个 SKU (~1万个) × 多张图片 × 5 倍数据增强 = 大量重复
- FAISS 搜索返回所有相似向量，不管是否属于同一 SKU

**解决方案**:
```python
# 1. 添加 top_k 和 confidence_threshold 参数到 process_image()
def process_image(
    self,
    image: Union[Image.Image, np.ndarray, Path],
    top_k: Optional[int] = None,
    confidence_threshold: Optional[float] = None,
    # ... 其他参数
):

# 2. API 模式：直接识别整张图，跳过物体检测
if top_k is not None and confidence_threshold is not None:
    # 搜索更多结果以确保去重后有足够的唯一 SKU
    search_k = top_k * 3  # 例如 top_k=5 则搜索 15 个结果
    results, similarities = self.vector_db.search(embedding, k=search_k)

    # 3. 去重：每个 SKU 只保留最高相似度的匹配
    sku_best_match = {}
    for result in formatted_results:
        sku = result['sku']
        if sku not in sku_best_match or result['similarity'] > sku_best_match[sku]['similarity']:
            sku_best_match[sku] = result

    # 4. 按相似度降序排序并限制到 top_k
    deduplicated_results = sorted(
        sku_best_match.values(),
        key=lambda x: x['similarity'],
        reverse=True
    )[:top_k]
```

**效果**:
```diff
修复前（重复）:
1. CHLB0971-BGE - 89.5%
2. CHLB0971-BGE - 88.0% ← 重复
3. FSF11292-ALP - 88.0%
4. CHLB0971-BGE - 87.9% ← 重复
5. FSF11294-ALP - 87.3%

修复后（去重）:
1. CHLB0971-BGE - 89.5% ← 只保留最高分
2. FSF11292-ALP - 88.0%
3. FSF11294-ALP - 87.3%
4. [其他不同的 SKU]
5. [其他不同的 SKU]
```

---

### 2️⃣ CORS 跨域修复 - `269d81d`
**文件**: [`scripts/api_server.py`](scripts/api_server.py#L104)

**问题**: Vercel 前端 (`https://zg-wms-store.vercel.app`) 无法调用 API
```
Access to fetch at 'https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize'
from origin 'https://zg-wms-store.vercel.app' has been blocked by CORS policy
```

**解决方案**:
```python
ALLOWED_ORIGINS = [
    # 本地开发环境
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # AWS 生产环境
    "https://tools.zgallerie.com",
    "https://zgallerie.com",
    # Vercel 前端 ← 新增
    "https://zg-wms-store.vercel.app",
]
```

**验证方法**:
```bash
curl -I -X OPTIONS \
  -H "Origin: https://zg-wms-store.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize
```

**期望响应头**:
```
access-control-allow-origin: https://zg-wms-store.vercel.app
access-control-allow-credentials: true
access-control-allow-methods: *
access-control-allow-headers: *
```

---

### 3️⃣ Vector Database 路径修正 - `dd03e58`
**文件**: [`scripts/api_server.py`](scripts/api_server.py#L153-L154)

**问题**: 代码中使用的文件名与实际下载的不一致
```python
# ❌ 错误的路径（文件不存在）
index_path = 'data/embeddings/faiss_index.bin'
metadata_path = 'data/embeddings/sku_metadata.pkl'
```

**解决方案**:
```python
# ✅ 正确的路径（与 S3 下载的文件名一致）
index_path = 'data/embeddings/faiss_index_robust_5x.bin'
metadata_path = 'data/embeddings/sku_metadata_robust_5x.pkl'
```

**为什么重要**:
- `entrypoint.sh` 从 S3 下载这两个文件
- 如果路径不对，服务启动会失败并报 `FileNotFoundError`

---

### 4️⃣ 部署文档 - `735c669`
**文件**: [`DEPLOY_TO_AWS.md`](DEPLOY_TO_AWS.md)

创建了完整的 AWS 部署指南，包括：
- 部署步骤（SSH、Docker、Docker Compose）
- 验证方法（Health Check、CORS、去重测试）
- 故障排查（CORS 错误、重复 SKU、容器启动失败、OOM）
- 生产配置（Workers、内存、Nginx）
- 回滚程序

---

## 🚀 部署到 AWS 生产环境

### 快速部署命令
```bash
# 1. SSH 到 AWS 服务器
ssh your-user@tools.zgallerie.com

# 2. 进入项目目录
cd /path/to/shopline-img-train

# 3. 拉取最新代码（从 GitLab）
git fetch origin
git checkout sku-dedup-cors-fix  # 或者先合并到 main
# 或者: git checkout main && git merge sku-dedup-cors-fix

# 4. 检查 Docker 当前状态
docker ps | grep sku-recognition

# 5. 重新构建 Docker 镜像
docker build -t sku-recognition-api .

# 6. 停止并删除旧容器
docker stop <container-id>
docker rm <container-id>

# 7. 启动新容器
docker run -d \
  --name sku-recognition-api \
  -p 6007:6007 \
  --restart unless-stopped \
  sku-recognition-api

# 8. 查看日志确认启动成功
docker logs sku-recognition-api --tail 50 -f
```

### 验证部署成功

#### 1. Health Check
```bash
curl https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/health
```
期望返回:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "database_size": 117738
}
```

#### 2. CORS 测试
```bash
curl -I -X OPTIONS \
  -H "Origin: https://zg-wms-store.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize \
  | grep access-control-allow-origin
```
期望输出:
```
access-control-allow-origin: https://zg-wms-store.vercel.app
```

#### 3. 去重测试
上传一张测试图片，检查返回的 SKU 是否有重复：
```bash
curl -X POST \
  'https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize?top_k=5&confidence_threshold=0.7' \
  -F 'file=@test_image.jpg' \
  | jq '.matches[] | .sku' | sort | uniq -d
```
期望输出：**空**（没有重复）

#### 4. 前端测试
1. 访问: https://zg-wms-store.vercel.app/admin/sku-recognition
2. 上传产品图片
3. 确认:
   - ✅ 没有 CORS 错误
   - ✅ 显示识别结果
   - ✅ 没有重复的 SKU
   - ✅ 产品图片正常加载
   - ✅ 相似度降序排列

---

## 📊 技术细节

### Vector Database 信息
```
文件名: faiss_index_robust_5x.bin, sku_metadata_robust_5x.pkl
大小: ~2GB (内存中)
向量数量: 117,738
SKU 数量: ~10,000
数据增强: 5x per image
下载源: AWS S3
```

### Docker 配置
```dockerfile
# Workers 配置 (Dockerfile entrypoint.sh)
--workers 6  # 优化为 c6id.2xlarge (8 vCPU, 16GB RAM)
--worker-class uvicorn.workers.UvicornWorker
--timeout 120
--worker-tmp-dir /dev/shm  # 使用共享内存加速
```

### API 端点
```
Base URL: https://tools.zgallerie.com/sku_recognition_fastapi

- GET  /api/v1/health           - 健康检查
- POST /api/v1/recognize        - 单图识别 (FormData)
- POST /api/v1/recognize/base64 - Base64 识别 (JSON)
- POST /api/v1/recognize/batch  - 批量识别
- GET  /api/v1/stats            - 统计信息
- GET  /docs                    - Swagger 文档
```

---

## 🐛 已知问题和注意事项

### 1. Claude 分支尚未完全合并
`claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR` 分支包含一些额外的优化:
- Workers 从 6 降到 2（防止 OOM）
- 更多的生产环境文档
- 可选的 tqdm 和 cv2 导入

**建议**: 生产环境如果遇到内存问题，可以参考 claude 分支的配置。

### 2. Dockerfile 中的 Workers 配置
当前 Dockerfile 设置为 `--workers 6`，适合 8 vCPU 的实例。
如果遇到内存不足（OOM），可以修改为:
```bash
--workers 2  # 减少内存使用
```

### 3. 前端 FormData 修复
前端代码 ([`wms-store/lib/sku-recognition-api.ts`](../wms-store/lib/sku-recognition-api.ts)) 也已修复:
- 移除了默认的 `Content-Type: application/json` header
- 让 axios 自动设置 `multipart/form-data` boundary

---

## 📝 提交历史

```
dd03e58 fix: correct vector database paths to robust 5x version
735c669 docs: add comprehensive AWS deployment guide
269d81d fix: add Vercel frontend to CORS whitelist
59d4849 feat: add SKU deduplication and API mode to process_image
```

---

## ✅ 检查清单

部署前确认:
- [ ] GitLab 代码已拉取到 AWS 服务器
- [ ] Docker 镜像已重新构建
- [ ] 旧容器已停止并删除
- [ ] 新容器已启动
- [ ] Health check 返回 healthy
- [ ] CORS 响应头包含 Vercel 域名
- [ ] 测试图片识别返回去重结果
- [ ] 前端可以正常上传和显示结果

部署后验证:
- [ ] 日志中没有错误
- [ ] 内存使用在合理范围（< 14GB）
- [ ] 响应时间 < 500ms
- [ ] 没有 OOM 错误

---

## 📞 问题反馈

如果部署后遇到问题:
1. 查看 Docker 日志: `docker logs sku-recognition-api --tail 100`
2. 检查 Nginx 日志: `sudo tail -f /var/log/nginx/error.log`
3. 测试本地端口: `curl localhost:6007/sku_recognition_fastapi/api/v1/health`
4. 参考 [DEPLOY_TO_AWS.md](DEPLOY_TO_AWS.md) 故障排查章节
