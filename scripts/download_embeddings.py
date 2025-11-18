#!/usr/bin/env python3
"""
下载向量数据库文件
支持从云存储（S3/阿里云 OSS）或 HTTP URL 下载
"""

import os
import sys
from pathlib import Path
import requests
from tqdm import tqdm
import argparse

PROJECT_ROOT = Path(__file__).parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"


def download_file(url: str, dest_path: Path, desc: str = "Downloading"):
    """
    从 URL 下载文件，显示进度条

    Args:
        url: 文件 URL
        dest_path: 保存路径
        desc: 进度条描述
    """
    print(f"📥 {desc}: {url}")

    # 确保目录存在
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # 下载文件
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # 获取文件大小
    total_size = int(response.headers.get('content-length', 0))

    # 写入文件并显示进度
    with open(dest_path, 'wb') as f, tqdm(
        desc=desc,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))

    print(f"✅ 已保存到: {dest_path}")


def download_from_s3(bucket: str, prefix: str, region: str = "us-east-1"):
    """
    从 AWS S3 下载向量数据库文件

    Args:
        bucket: S3 bucket 名称
        prefix: S3 对象前缀
        region: AWS 区域
    """
    try:
        import boto3

        s3 = boto3.client('s3', region_name=region)

        # 下载 FAISS 索引
        faiss_key = f"{prefix}/faiss_index_robust_5x.bin"
        faiss_path = EMBEDDINGS_DIR / "faiss_index_robust_5x.bin"

        print(f"📥 从 S3 下载 FAISS 索引: s3://{bucket}/{faiss_key}")
        s3.download_file(bucket, faiss_key, str(faiss_path))
        print(f"✅ 已保存到: {faiss_path}")

        # 下载元数据
        metadata_key = f"{prefix}/sku_metadata_robust_5x.pkl"
        metadata_path = EMBEDDINGS_DIR / "sku_metadata_robust_5x.pkl"

        print(f"📥 从 S3 下载元数据: s3://{bucket}/{metadata_key}")
        s3.download_file(bucket, metadata_key, str(metadata_path))
        print(f"✅ 已保存到: {metadata_path}")

        print("\n✅ 向量数据库下载完成！")

    except ImportError:
        print("❌ 错误: boto3 未安装，请运行: pip install boto3")
        sys.exit(1)
    except Exception as e:
        print(f"❌ S3 下载失败: {e}")
        sys.exit(1)


def download_from_http(base_url: str):
    """
    从 HTTP URL 下载向量数据库文件

    Args:
        base_url: 基础 URL（不包含文件名）
    """
    try:
        # 下载 FAISS 索引
        faiss_url = f"{base_url}/faiss_index_robust_5x.bin"
        faiss_path = EMBEDDINGS_DIR / "faiss_index_robust_5x.bin"
        download_file(faiss_url, faiss_path, "下载 FAISS 索引")

        # 下载元数据
        metadata_url = f"{base_url}/sku_metadata_robust_5x.pkl"
        metadata_path = EMBEDDINGS_DIR / "sku_metadata_robust_5x.pkl"
        download_file(metadata_url, metadata_path, "下载 SKU 元数据")

        print("\n✅ 向量数据库下载完成！")

    except Exception as e:
        print(f"❌ HTTP 下载失败: {e}")
        sys.exit(1)


def check_embeddings_exist() -> bool:
    """检查向量数据库文件是否存在"""
    faiss_path = EMBEDDINGS_DIR / "faiss_index_robust_5x.bin"
    metadata_path = EMBEDDINGS_DIR / "sku_metadata_robust_5x.pkl"

    return faiss_path.exists() and metadata_path.exists()


def main():
    parser = argparse.ArgumentParser(description="下载向量数据库文件")
    parser.add_argument(
        "--source",
        choices=["s3", "http"],
        required=True,
        help="下载源类型"
    )
    parser.add_argument(
        "--s3-bucket",
        help="S3 bucket 名称（当 source=s3 时必需）"
    )
    parser.add_argument(
        "--s3-prefix",
        default="embeddings",
        help="S3 对象前缀（默认: embeddings）"
    )
    parser.add_argument(
        "--s3-region",
        default="us-east-1",
        help="AWS 区域（默认: us-east-1）"
    )
    parser.add_argument(
        "--http-url",
        help="HTTP 基础 URL（当 source=http 时必需）"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新下载（即使文件已存在）"
    )

    args = parser.parse_args()

    # 检查文件是否已存在
    if check_embeddings_exist() and not args.force:
        print("ℹ️  向量数据库文件已存在")
        print(f"   FAISS 索引: {EMBEDDINGS_DIR / 'faiss_index_robust_5x.bin'}")
        print(f"   SKU 元数据: {EMBEDDINGS_DIR / 'sku_metadata_robust_5x.pkl'}")
        print("\n如需重新下载，请使用 --force 参数")
        return

    # 根据源类型下载
    if args.source == "s3":
        if not args.s3_bucket:
            print("❌ 错误: --s3-bucket 参数必需")
            sys.exit(1)
        download_from_s3(args.s3_bucket, args.s3_prefix, args.s3_region)

    elif args.source == "http":
        if not args.http_url:
            print("❌ 错误: --http-url 参数必需")
            sys.exit(1)
        download_from_http(args.http_url)


if __name__ == "__main__":
    main()
