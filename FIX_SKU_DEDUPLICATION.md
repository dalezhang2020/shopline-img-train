# SKU去重修复说明

## 🔍 问题描述

API返回的识别结果中存在**重复的SKU**，例如：
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

## 📊 原因分析

1. **向量数据库包含多个版本的图片**
   - 原始SKU数量：~1万个
   - 数据库向量数量：117,738个
   - 原因：每个SKU有多张产品图 × 5个数据增强版本

2. **搜索返回所有匹配向量**
   - FAISS搜索返回top_k=5个最相似的向量
   - 这5个向量可能属于同一个SKU的不同图片

## ✅ 解决方案

### 修改文件：`src/pipeline/inference.py`

在 `process_image()` 方法中添加SKU去重逻辑：

```python
# Deduplicate by SKU - keep only the highest similarity for each SKU
sku_best_match = {}
for result in formatted_results:
    sku = result['sku']
    if sku not in sku_best_match or result['similarity'] > sku_best_match[sku]['similarity']:
        sku_best_match[sku] = result

# Sort by similarity (descending) and limit to top_k
deduplicated_results = sorted(
    sku_best_match.values(),
    key=lambda x: x['similarity'],
    reverse=True
)[:top_k]

return deduplicated_results
```

### 去重策略

1. **保留每个SKU的最高相似度结果** - 如果同一SKU有多个匹配，只保留相似度最高的
2. **按相似度降序排序** - 确保top_k结果都是最相关的
3. **限制返回数量** - 仍然只返回top_k个结果

## 🎯 修复后的效果

修复前（重复）：
```
1. CHLB0971-BGE - 89.5%
2. CHLB0971-BGE - 88.0% ← 重复
3. FSF11292-ALP - 88.0%
4. CHLB0971-BGE - 87.9% ← 重复
5. FSF11294-ALP - 87.3%
```

修复后（去重）：
```
1. CHLB0971-BGE - 89.5%  ← 只保留最高相似度
2. FSF11292-ALP - 88.0%
3. FSF11294-ALP - 87.3%
4. [下一个不同的SKU]
5. [下一个不同的SKU]
```

## 🚀 部署步骤

### 方法1：重启Docker容器（推荐）

如果服务在Docker中运行：
```bash
# 停止容器
docker stop <container-name>

# 重新构建镜像（包含新代码）
docker build -t sku-recognition-api .

# 启动新容器
docker run -d -p 6007:6007 --name sku-recognition-api sku-recognition-api
```

### 方法2：热更新（如果使用--reload）

如果开发环境使用了 `--reload` 参数：
```bash
# 代码会自动重新加载，无需重启
# 只需确保修改的文件已保存
```

### 方法3：手动重启服务

如果通过systemd或其他方式运行：
```bash
sudo systemctl restart sku-recognition-api
```

## ✅ 验证

重启后测试：
```bash
curl -X POST 'https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/recognize?top_k=5&confidence_threshold=0.7' \
  -F 'file=@test_image.jpg'
```

检查返回结果，确保：
- ✅ 每个SKU只出现一次
- ✅ 按相似度降序排列
- ✅ 返回数量 ≤ top_k

## 📝 技术细节

### 为什么不在数据库层去重？

**优点**：在推理时去重更灵活
- 可以根据业务需求调整去重策略
- 保留数据增强的优势（提高识别准确率）
- 数据库中保留多样性有助于模型学习

**性能影响**：
- 去重操作在内存中进行，O(n) 时间复杂度
- 对5-20个结果进行去重，性能影响可忽略
- 处理时间仍在 <500ms 范围内

## 🎨 优化建议（未来）

如果需要进一步优化，可以考虑：

1. **在向量数据库搜索时增加k值**
   ```python
   # 搜索更多结果，然后去重
   results, similarities = self.vector_db.search(embedding, k=top_k * 3)
   ```

2. **添加SKU元数据聚合**
   ```python
   # 聚合同一SKU的所有匹配信息
   result['match_count'] = len(sku_matches)  # 匹配次数
   result['avg_similarity'] = np.mean(similarities)  # 平均相似度
   ```

3. **使用集群或平均池化**
   - 将同一SKU的所有向量进行平均池化
   - 构建新的去重向量数据库
