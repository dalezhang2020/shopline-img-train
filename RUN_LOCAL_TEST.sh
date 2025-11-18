#!/bin/bash
# 一键启动本地测试

cd "$(dirname "$0")"

echo "============================================"
echo "本地 Gunicorn 快速测试"
echo "============================================"
echo ""
echo "测试配置："
echo "  - 1 个 worker（快速启动）"
echo "  - Debug 日志"
echo "  - 端口 6007"
echo "  - API 文档: http://localhost:6007/sku_recognition_fastapi/docs"
echo ""
echo "按 Ctrl+C 停止"
echo "============================================"
echo ""

# 设置环境变量
export PYTHONPATH="$(pwd)"
export PYTHONUNBUFFERED=1
export DEVICE=cpu
export CLIP_MODEL="ViT-L/14"

# 启动（最简配置）
gunicorn scripts.api_server:app \
    --bind 0.0.0.0:6007 \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --log-level debug \
    --reload
