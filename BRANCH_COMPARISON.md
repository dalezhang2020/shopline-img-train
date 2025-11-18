# Main 分支 vs Claude 分支对比

## 📊 总结

### ✅ Main 分支已包含的核心功能（可以部署）

| 功能 | Main 分支 | Claude 分支 | 状态 |
|------|----------|------------|------|
| **CORS 修复** | ✅ `269d81d` | ✅ `9e2cf34` | 相同 |
| **Vector DB 路径** | ✅ `dd03e58` | ✅ `8a0965c` | 相同 |
| **SKU 去重** | ✅ `59d4849` (更完整) | ✅ `d4a1ba4` | Main 更好 |
| **部署文档** | ✅ DEPLOY_TO_AWS.md | ✅ PRODUCTION_DEPENDENCIES.md | 都有 |

### ⚠️ Main 分支缺少的重要优化

| 优化项 | Main 分支 | Claude 分支 | 影响 |
|--------|----------|------------|------|
| **Workers 数量** | ❌ 6 workers | ✅ 2 workers | 可能 OOM |
| **模型预加载** | ❌ 无 `--preload` | ✅ 有 `--preload` | 内存浪费 |
| **可选导入** | ❌ 无 | ✅ `71e2f4c` | 生产健壮性 |

---

## 🔍 详细对比

### 1. Workers 配置（内存优化）⚠️

#### Main 分支 (Dockerfile 第 186 行)
```dockerfile
exec gunicorn scripts.api_server:app \
    --bind 0.0.0.0:6007 \
    --workers 6 \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-tmp-dir /dev/shm \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

**内存估算**：
- CLIP ViT-L/14 模型：~1.5GB × 6 workers = **9GB**
- FAISS 索引：~0.36GB
- Worker 开销：~0.5GB × 6 = 3GB
- **总计：~12.4GB**

**风险**：在 16GB RAM 的实例上可能 OOM！

---

#### Claude 分支 (`8551c02`)
```dockerfile
exec gunicorn scripts.api_server:app \
    --bind 0.0.0.0:6007 \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --preload \                           # ← 关键！共享模型
    --worker-tmp-dir /dev/shm \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

**内存估算**（使用 `--preload`）：
- CLIP ViT-L/14 模型：~1.5GB (共享，只加载一次)
- FAISS 索引：~0.36GB
- Worker 开销：~0.5GB × 2 = 1GB
- **总计：~2.9GB**

**优势**：
- ✅ 节省 **9.5GB** 内存
- ✅ 更快的启动时间（模型只加载一次）
- ✅ 适合 16GB RAM 实例

---

### 2. 可选导入（生产环境健壮性）

#### Claude 分支包含的修复：

##### `71e2f4c` - Make augmentation imports optional
**src/utils/__init__.py**
```python
# 修复前：强制导入数据增强（生产不需要）
from .augmentation import *  # ← 可能失败

# 修复后：可选导入
try:
    from .augmentation import *
except ImportError:
    pass  # 生产环境不需要数据增强
```

##### `0ca83b0` - Make tqdm optional
**src/pipeline/inference.py**
```python
# 修复前：
from tqdm import tqdm  # ← API 不需要进度条

# 修复后：
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    tqdm = lambda x, **kwargs: x  # 无操作包装器
```

**影响**：Main 分支如果缺少这些包可能会启动失败。

---

### 3. SKU 去重实现对比

#### Main 分支 (`59d4849`) - 更完整 ✅
```python
def process_image(
    self,
    image,
    top_k: Optional[int] = None,
    confidence_threshold: Optional[float] = None,
):
    # API 模式：直接识别
    if top_k is not None and confidence_threshold is not None:
        search_k = top_k * 3  # 搜索更多结果
        results, similarities = self.vector_db.search(embedding, k=search_k)

        # 去重逻辑
        sku_best_match = {}
        for result in formatted_results:
            sku = result['sku']
            if sku not in sku_best_match or result['similarity'] > sku_best_match[sku]['similarity']:
                sku_best_match[sku] = result

        return sorted(sku_best_match.values(), key=lambda x: x['similarity'], reverse=True)[:top_k]
```

**优势**：
- ✅ 支持 API 模式和检测模式
- ✅ 搜索 `top_k * 3` 确保有足够的唯一 SKU
- ✅ 完整的去重和排序

#### Claude 分支 (`d4a1ba4`) - 简化版
```python
# 简单的去重，但搜索数量固定为 top_k
results, similarities = self.vector_db.search(embedding, k=top_k)
# ... 去重逻辑类似但没有 top_k * 3 扩展
```

**结论**：Main 分支的实现更好！

---

## 🚀 推荐的部署策略

### 选项 1：使用当前 Main 分支（快速部署）✅

**适用场景**：
- ✅ AWS 实例有足够内存（> 14GB 可用）
- ✅ 需要立即修复 CORS 和去重问题
- ✅ 可以监控内存使用情况

**部署命令**：
```bash
git checkout sku-dedup-cors-fix
docker build -t sku-recognition-api .
docker run -d --name sku-recognition-api -p 6007:6007 --restart unless-stopped sku-recognition-api
```

**监控内存**：
```bash
docker stats sku-recognition-api
```

如果内存使用 > 14GB，停止并使用选项 2。

---

### 选项 2：合并 Workers 优化（推荐）✅✅

**修改 Dockerfile（手动或从 claude 分支合并）**：

```dockerfile
# 修改第 186 行
--workers 2 \           # 改为 2
--preload \             # 添加这行
```

**优势**：
- ✅ 内存安全（~2.9GB vs ~12.4GB）
- ✅ 包含所有核心功能（CORS + 去重 + 路径修复）
- ✅ 生产环境更稳定

**部署命令**：
```bash
# 修改 Dockerfile 后
docker build -t sku-recognition-api .
docker run -d --name sku-recognition-api -p 6007:6007 --restart unless-stopped sku-recognition-api
```

---

### 选项 3：完全合并 Claude 分支（最稳定）

**包含所有优化**：
- Workers = 2 + --preload
- 可选导入（augmentation, tqdm）
- 额外的生产文档

**命令**：
```bash
git checkout main
git merge claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR
# 解决冲突...
git push
```

---

## 📝 当前状态总结

### ✅ 可以立即部署 Main 分支

**Main 分支包含的核心修复**：
1. ✅ CORS 修复 - 前端可以调用 API
2. ✅ SKU 去重 - 不再返回重复结果
3. ✅ Vector DB 路径 - 使用正确的文件名
4. ✅ 完整的部署文档

**功能完整性**：**95%** ✅

---

### ⚠️ 建议添加的优化

**从 Claude 分支缺少的优化**：
1. ⚠️ Workers = 2 + --preload（内存优化）
2. ⚠️ 可选导入（健壮性）

**影响**：
- 在高负载或有限内存环境下可能 OOM
- 如果缺少某些包（tqdm, augmentation）可能启动失败

**建议**：
- 先部署 main 分支测试功能
- 监控内存使用情况
- 如果内存 > 12GB，应用 workers=2 优化

---

## 🎯 最终建议

### 立即行动：

1. **部署 Main 分支到 AWS** ✅
   - 修复了所有核心问题（CORS + 去重 + 路径）
   - 可以立即使用

2. **监控内存使用** ⏳
   ```bash
   docker stats sku-recognition-api
   ```

3. **如果内存 > 12GB**：
   - 应用 workers=2 优化
   - 添加 --preload 参数
   - 重新部署

### 长期优化：

合并 Claude 分支的内存优化（workers=2 + preload）作为生产环境的标准配置。

---

## 📊 提交清单

### Main 分支最新提交：
```
0df0c95 - docs: add comprehensive summary of latest changes
dd03e58 - fix: correct vector database paths to robust 5x version
735c669 - docs: add comprehensive AWS deployment guide
269d81d - fix: add Vercel frontend to CORS whitelist
59d4849 - feat: add SKU deduplication and API mode to process_image
```

### Claude 分支独有的提交：
```
8551c02 - fix: reduce workers to 2 and correct --preload parameter ⭐
71e2f4c - fix: make augmentation imports optional
0ca83b0 - fix: make tqdm optional
... (其他优化)
```

⭐ = 推荐合并到 main
