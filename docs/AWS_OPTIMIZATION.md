# AWS c6id.2xlarge 优化配置

## 实例规格

- **实例类型**: c6id.2xlarge (计算优化型)
- **vCPU**: 8核 (Intel Ice Lake)
- **内存**: 16 GB
- **网络**: 高达10 Gbps
- **本地存储**: 1 x 237 GB NVMe SSD

## 优化配置

### 1. Gunicorn Workers

```bash
--workers 4  # 针对 CLIP ViT-L/14 优化（防止 OOM）
--preload-app  # 在 fork 前加载模型，共享内存
--worker-tmp-dir /dev/shm  # 使用共享内存加速heartbeat
--max-requests 1000  # 防止内存泄漏
--max-requests-jitter 50  # 避免所有worker同时重启
```

**重要**: 使用 `--preload-app` 可以在所有 workers 间共享 CLIP 模型，节省 ~6GB 内存

**公式**:
- 一般情况: `workers = (CPU核心数 - 1)` 或 `(CPU核心数 - 2)`
- 大模型 (ViT-L/14): `workers = 4` (平衡性能和内存)

### 2. PyTorch CPU 线程配置

```bash
OMP_NUM_THREADS=4  # 每个worker使用4线程
MKL_NUM_THREADS=4  # Intel MKL优化
OPENBLAS_NUM_THREADS=4
```

**配置原理**:
- 4个workers × 4线程 = 16个线程
- 由于超线程和I/O等待,实际CPU利用率会保持在60-80%

### 3. CLIP批处理

```yaml
clip:
  batch_size: 32  # 增大批处理以充分利用CPU
```

### 4. 内存使用估算 (使用 --preload-app)

**每个组件内存占用**:
- CLIP ViT-L/14模型: ~1.5 GB (共享)
- FAISS索引: ~350 MB (共享)
- 向量元数据: ~10 MB (共享)
- Gunicorn worker开销: ~500 MB (per worker)

**总内存 (优化后)**:
- 共享模型: 1.5 GB (使用 --preload-app 只加载一次)
- 4个workers × 0.5 GB开销 = 2.0 GB
- 共享数据: 0.36 GB
- 系统开销: 1-2 GB
- **总计**: ~4.9-5.9 GB / 16 GB = **30-37%利用率** ✅

**对比 (不使用 --preload-app)**:
- 4个workers × 1.5 GB模型 = 6.0 GB
- 4个workers × 0.5 GB开销 = 2.0 GB
- 共享数据: 0.36 GB
- 系统开销: 1-2 GB
- **总计**: ~9.4-10.4 GB / 16 GB = **59-65%利用率**

⚠️ **重要**: 6个workers 会导致 OOM (超过 16GB)，因此减少到 4 个

### 5. 系统优化

#### a) 启用BBR拥塞控制 (提升网络性能)

```bash
echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### b) 增加文件描述符限制

```bash
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf
```

#### c) Docker内存限制（可选）

```bash
docker run -d \
  --name sku-recognition-api \
  --restart unless-stopped \
  -p 6007:6007 \
  --memory="14g" \
  --memory-swap="14g" \
  --cpus="7.5" \
  registry.gitlab.com/dalez/fastapi/shopline-img-train:main
```

### 6. 监控和调优

#### 查看CPU使用率

```bash
# 实时监控
docker stats sku-recognition-api

# 详细CPU信息
docker exec sku-recognition-api ps aux
```

#### 查看内存使用

```bash
# 容器内存
docker exec sku-recognition-api free -h

# 进程内存
docker exec sku-recognition-api ps aux --sort=-%mem | head -10
```

#### 性能测试

```bash
# 使用Apache Bench测试
ab -n 1000 -c 10 -p image.jpg -T 'image/jpeg' \
  http://localhost:6007/sku_recognition_fastapi/api/v1/recognize

# 使用wrk测试
wrk -t4 -c50 -d30s --latency \
  http://localhost:6007/sku_recognition_fastapi/api/v1/health
```

## 预期性能指标

### c6id.2xlarge 上的表现

- **吞吐量**: 30-40 req/s (SKU识别)
- **延迟**:
  - P50: 150-200ms
  - P95: 300-400ms
  - P99: 500-700ms
- **并发**: 支持50-100并发连接
- **CPU利用率**: 60-80%
- **内存使用**: 11-12 GB

### 与其他实例类型对比

| 实例类型 | vCPU | 内存 | 推荐Workers | 预期吞吐量 | 月成本(us-east-1) |
|---------|------|------|-------------|-----------|-----------------|
| t3.large | 2 | 8GB | 2 | 10-15 req/s | ~$60 |
| c6i.xlarge | 4 | 8GB | 3 | 20-25 req/s | ~$140 |
| **c6id.2xlarge** | **8** | **16GB** | **6** | **30-40 req/s** | **~$280** |
| c6i.4xlarge | 16 | 32GB | 12 | 60-80 req/s | ~$560 |

## 成本优化建议

### 1. 使用Spot实例（节省70%）

```bash
# 创建Spot实例请求
aws ec2 request-spot-instances \
  --spot-price "0.20" \
  --instance-count 1 \
  --type "persistent" \
  --launch-specification file://spot-spec.json
```

### 2. 自动伸缩（按需）

- 低流量时段: 使用c6i.xlarge (4核)
- 高流量时段: 使用c6id.2xlarge (8核)
- 节省: ~40%成本

### 3. Reserved Instances（1-3年）

- 1年预留: 节省30-40%
- 3年预留: 节省50-60%

## 故障排除

### CPU使用率低于预期

```bash
# 检查线程配置
docker exec sku-recognition-api env | grep THREADS

# 增加workers
docker exec sku-recognition-api ps aux | grep gunicorn
```

### 内存不足

```bash
# 查看内存详情
docker exec sku-recognition-api cat /proc/meminfo

# 减少workers或batch_size
```

### 延迟过高

```bash
# 查看worker状态
docker exec sku-recognition-api curl http://localhost:6007/sku_recognition_fastapi/api/v1/stats

# 检查日志
docker logs sku-recognition-api --tail 100
```

## 更新配置

如果需要调整workers数量，可以通过环境变量覆盖：

```bash
docker run -d \
  --name sku-recognition-api \
  --restart unless-stopped \
  -p 6007:6007 \
  -e GUNICORN_WORKERS=8 \
  -e OMP_NUM_THREADS=3 \
  registry.gitlab.com/dalez/fastapi/shopline-img-train:main
```

## 参考资源

- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)
- [PyTorch Performance Tuning](https://pytorch.org/tutorials/recipes/recipes/tuning_guide.html)
- [AWS c6id Instances](https://aws.amazon.com/ec2/instance-types/c6i/)
