# 重启 SKU Recognition API 服务

## 问题说明

前端从 Vercel (`https://zg-wms-store.vercel.app`) 访问API时遇到CORS错误。

已修复：
1. ✅ 添加了Vercel域名到CORS白名单
2. ✅ 修复了FormData上传问题
3. ⏳ 需要重启服务以应用更改

## 重启步骤

### 如果是在AWS EC2上通过Docker运行：

```bash
# SSH到AWS服务器
ssh your-user@tools.zgallerie.com

# 找到运行中的容器
docker ps | grep sku-recognition

# 重启容器（保留数据）
docker restart <container-id>

# 或者，如果需要重新构建并部署：
cd /path/to/shopline-img-train
docker build -t sku-recognition-api .
docker stop <old-container-id>
docker rm <old-container-id>
docker run -d -p 6007:6007 --name sku-recognition-api sku-recognition-api
```

### 如果是通过systemd服务运行：

```bash
sudo systemctl restart sku-recognition-api
```

### 验证服务是否正常：

```bash
curl https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/health
```

应该返回：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "database_size": 117738
}
```

## 修改内容

### 1. `/scripts/api_server.py` (Line 105)
添加了Vercel域名到CORS白名单：
```python
ALLOWED_ORIGINS = [
    # ...
    "https://zg-wms-store.vercel.app",  # ← 新增
]
```

### 2. `/Users/dizhang/Gitlab/wms-store/lib/sku-recognition-api.ts`
- 移除了默认的 `Content-Type: application/json` header
- 修复了Blob文件上传问题

## 测试

重启后，在前端测试：
1. 访问 https://zg-wms-store.vercel.app/admin/sku-recognition
2. 上传产品图片
3. 应该能正常识别并显示产品信息
