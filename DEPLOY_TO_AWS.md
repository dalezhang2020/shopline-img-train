# 🚀 Deploy SKU Recognition API to AWS

## 📝 Changes Summary

This deployment includes two critical fixes:

### 1. ✅ CORS Fix for Vercel Frontend
**File**: `scripts/api_server.py` (Line 104)
```python
ALLOWED_ORIGINS = [
    # ... existing origins ...
    "https://zg-wms-store.vercel.app",  # ← Added
]
```

### 2. ✅ SKU Deduplication Fix
**File**: `src/pipeline/inference.py` (Lines 237-279)

**Problem**: API returned duplicate SKUs because vector database contains multiple augmented images per SKU (117,738 vectors for ~10,000 SKUs)

**Solution**:
- Added `top_k` and `confidence_threshold` parameters to `process_image()`
- Implemented API mode for direct SKU recognition without detection
- Search with `top_k * 3` to get enough candidates for deduplication
- Keep only highest similarity match per unique SKU
- Return sorted, deduplicated list of top_k results

**Example**:
```
Before (duplicates):
1. CHLB0971-BGE - 89.5%
2. CHLB0971-BGE - 88.0% ← duplicate
3. FSF11292-ALP - 88.0%
4. CHLB0971-BGE - 87.9% ← duplicate
5. FSF11294-ALP - 87.3%

After (deduplicated):
1. CHLB0971-BGE - 89.5%
2. FSF11292-ALP - 88.0%
3. FSF11294-ALP - 87.3%
4. [next unique SKU]
5. [next unique SKU]
```

---

## 🔄 Deployment Steps

### Option 1: SSH to AWS and Deploy (Recommended)

```bash
# 1. SSH to AWS server
ssh your-user@tools.zgallerie.com

# 2. Navigate to project directory
cd /path/to/shopline-img-train

# 3. Pull latest changes from GitLab
git pull origin sku-dedup-cors-fix

# Or merge the branch into main first:
git checkout main
git merge sku-dedup-cors-fix
git push origin main

# 4. Find running Docker container
docker ps | grep sku-recognition

# 5. Rebuild Docker image with latest code
docker build -t sku-recognition-api .

# 6. Stop and remove old container
docker stop <container-id-or-name>
docker rm <container-id-or-name>

# 7. Start new container
docker run -d \
  --name sku-recognition-api \
  -p 6007:6007 \
  --restart unless-stopped \
  sku-recognition-api

# 8. Verify container is running
docker ps | grep sku-recognition
docker logs sku-recognition-api --tail 50
```

### Option 2: Quick Restart (If Code Already on Server)

```bash
# If you already manually copied the files to the server:

# 1. SSH to AWS
ssh your-user@tools.zgallerie.com

# 2. Restart Docker container
docker restart <container-id-or-name>

# 3. Check logs
docker logs sku-recognition-api --tail 50 -f
```

### Option 3: Using Docker Compose (If Available)

```bash
# 1. SSH to AWS
ssh your-user@tools.zgallerie.com

# 2. Navigate to project directory
cd /path/to/shopline-img-train

# 3. Pull latest changes
git pull origin sku-dedup-cors-fix

# 4. Rebuild and restart
docker-compose up -d --build

# 5. Check status
docker-compose logs -f api
```

---

## ✅ Verification Steps

### 1. Health Check
```bash
curl https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "database_size": 117738,
  "uptime_seconds": 123.45
}
```

### 2. Test CORS Headers
```bash
curl -I -X OPTIONS \
  -H "Origin: https://zg-wms-store.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize
```

**Expected Headers**:
```
access-control-allow-origin: https://zg-wms-store.vercel.app
access-control-allow-credentials: true
access-control-allow-methods: *
access-control-allow-headers: *
```

### 3. Test SKU Recognition (No Duplicates)
```bash
curl -X POST \
  'https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize?top_k=5&confidence_threshold=0.7' \
  -F 'file=@test_image.jpg' \
  | jq '.matches[] | .sku' | sort | uniq -d
```

**Expected**: No duplicate SKUs printed (empty output means success)

### 4. Test from Frontend
1. Visit: https://zg-wms-store.vercel.app/admin/sku-recognition
2. Upload a product image
3. Verify:
   - ✅ No CORS errors in browser console
   - ✅ Recognition results appear
   - ✅ No duplicate SKUs in results
   - ✅ Product images load from MySQL API
   - ✅ Similarity scores are sorted descending

---

## 🐛 Troubleshooting

### Issue: CORS Error Still Appears

**Check 1**: Verify Vercel domain is in CORS whitelist
```bash
ssh your-user@tools.zgallerie.com
cd /path/to/shopline-img-train
grep "zg-wms-store.vercel.app" scripts/api_server.py
```

**Check 2**: Restart service if code exists but not applied
```bash
docker restart sku-recognition-api
```

### Issue: Still Seeing Duplicate SKUs

**Check 1**: Verify inference.py has deduplication code
```bash
ssh your-user@tools.zgallerie.com
cd /path/to/shopline-img-train
grep -A 5 "Deduplicate by SKU" src/pipeline/inference.py
```

**Expected Output**:
```python
# Deduplicate by SKU - keep only the highest similarity for each SKU
sku_best_match = {}
for result in formatted_results:
    sku = result['sku']
    if sku not in sku_best_match or result['similarity'] > sku_best_match[sku]['similarity']:
        sku_best_match[sku] = result
```

**Check 2**: Verify Docker image was rebuilt
```bash
docker inspect sku-recognition-api | grep Created
# Should show recent timestamp
```

### Issue: Container Won't Start

**Check logs**:
```bash
docker logs sku-recognition-api --tail 100
```

**Common issues**:
- Port 6007 already in use → Kill old process or use different port
- Vector database files missing → Check S3 download in entrypoint.sh
- CUDA/GPU errors → Ensure running on CPU-only instance

### Issue: High Memory Usage / OOM Errors

**Check current workers**:
```bash
docker logs sku-recognition-api | grep "workers"
```

**Should show**: `workers=2` (reduced from 4 to prevent OOM on 16GB RAM)

If using more workers, update `entrypoint.sh`:
```bash
exec gunicorn api_server:app \
  --bind 0.0.0.0:6007 \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 300 \
  --preload
```

---

## 📊 Production Configuration

### Current AWS Setup
- **Instance**: c6id.2xlarge (8 vCPU, 16GB RAM)
- **Workers**: 2 (reduced to prevent OOM)
- **Port**: 6007
- **Reverse Proxy**: Nginx at `/sku_recognition_fastapi`
- **Vector DB**: 117,738 embeddings (~2GB in memory)

### Environment Variables
```bash
# Optional: Override in docker run command
-e WORKERS=2 \
-e PORT=6007 \
-e LOG_LEVEL=info
```

### Nginx Configuration
Ensure Nginx forwards requests correctly:
```nginx
location /sku_recognition_fastapi/ {
    proxy_pass http://localhost:6007/sku_recognition_fastapi/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Increase timeout for large image uploads
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;

    # Allow large file uploads (10MB max)
    client_max_body_size 10M;
}
```

---

## 🔗 Git Repository

### Main Repositories
- **GitLab**: https://gitlab.com/dalez/fastapi/shopline-img-train.git
- **GitHub**: https://github.com/dalezhang2020/shopline-img-train.git

### Deployed Branch
The fixes are on branch: `sku-dedup-cors-fix`

To merge into main:
```bash
git checkout main
git merge sku-dedup-cors-fix
git push origin main
```

### Commits Included
1. `feat: add SKU deduplication and API mode to process_image`
2. `fix: add Vercel frontend to CORS whitelist`

---

## 📞 Support

If deployment fails:
1. Check Docker logs: `docker logs sku-recognition-api --tail 100`
2. Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Verify network: `curl localhost:6007/sku_recognition_fastapi/api/v1/health`
4. Test CORS: Use browser DevTools Network tab

**Rollback** (if needed):
```bash
docker ps -a  # Find previous container ID
docker start <old-container-id>
docker stop sku-recognition-api
```
