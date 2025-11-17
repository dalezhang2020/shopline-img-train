# MySQL 数据源配置指南

## 快速开始

本系统支持直接从 MySQL 数据库读取 SKU 数据，无需 Shopline API。

### 第一步：配置数据库连接

#### 1. 复制环境变量模板

```bash
cp .env.example .env
```

#### 2. 编辑 `.env` 文件

```bash
# MySQL 数据库配置
MYSQL_HOST=localhost          # 你的 MySQL 主机地址
MYSQL_PORT=3306               # MySQL 端口
MYSQL_DATABASE=shopline_db    # 数据库名称
MYSQL_USER=root               # 数据库用户名
MYSQL_PASSWORD=your_password  # 数据库密码

# 其他配置
DEVICE=cuda                   # 使用 GPU
CLIP_MODEL=ViT-B/32
```

### 第二步：测试数据库连接

创建测试脚本 `test_db_connection.py`:

```python
from src.api.mysql_client import MySQLClient
import os
from dotenv import load_dotenv

load_dotenv()

# 连接数据库
client = MySQLClient(
    host=os.getenv('MYSQL_HOST'),
    database=os.getenv('MYSQL_DATABASE'),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    port=int(os.getenv('MYSQL_PORT', 3306))
)

try:
    # 测试连接
    client.connect()
    print("✓ 数据库连接成功")

    # 获取统计信息
    stats = client.get_stats()
    print("\n数据库统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 测试获取 SKU
    skus = client.get_sku_with_images()
    print(f"\n找到 {len(skus)} 个 SKU")

    # 显示前 3 个 SKU
    print("\n前 3 个 SKU 示例:")
    for sku in skus[:3]:
        print(f"  - SKU: {sku['sku']}")
        print(f"    标题: {sku.get('product_title', 'N/A')}")
        print(f"    图片: {sku.get('image_url', 'N/A')[:50]}...")
        print()

except Exception as e:
    print(f"✗ 错误: {e}")
finally:
    client.disconnect()
```

运行测试：

```bash
python test_db_connection.py
```

预期输出：

```
✓ 数据库连接成功

数据库统计:
  total_products: 5432
  total_skus: 20158
  products_by_category: {'FURNITURE': 1234, 'DECOR': 2345, ...}

找到 20158 个 SKU

前 3 个 SKU 示例:
  - SKU: SOFA-GRY-001
    标题: Modern Sofa - Gray
    图片: https://example.com/images/sofa-gray.jpg...
  ...
```

### 第三步：下载数据

#### 使用优化查询（推荐）

```bash
python scripts/download_from_mysql.py \
  --download-images \
  --use-optimized-query
```

这会使用单个 SQL 查询获取所有数据，速度更快。

#### 使用标准查询

```bash
python scripts/download_from_mysql.py \
  --download-images \
  --batch-size 1000
```

这会分批查询产品和变体，适合复杂的表结构。

#### 不下载图片（仅获取数据）

```bash
python scripts/download_from_mysql.py \
  --use-optimized-query
```

### 第四步：验证数据

检查下载的数据：

```bash
# 查看 SKU 数据
cat data/raw/sku_data.json | head -50

# 查看下载的图片数量
ls data/images/ | wc -l

# 查看下载的图片
ls data/images/ | head -10
```

## 数据库表结构要求

### 最简化结构

系统至少需要以下信息：

1. **SKU 编码** - 唯一标识
2. **图片 URL** - 产品图片链接
3. **标题** - 产品名称

示例最简表结构：

```sql
CREATE TABLE sku_products (
    sku VARCHAR(100) PRIMARY KEY,
    title VARCHAR(255),
    image_url TEXT,
    category VARCHAR(100)
);
```

### 标准结构（推荐）

参考 [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) 了解完整的数据库结构。

## 自定义表结构映射

如果你的表结构与系统预期不同，需要修改 SQL 查询。

### 示例：单表结构

假设你的所有数据在 `inventory` 表中：

```sql
-- 你的表结构
CREATE TABLE inventory (
    item_code VARCHAR(100),    -- SKU
    item_name VARCHAR(255),    -- 产品名
    img_path TEXT,             -- 图片
    cat VARCHAR(50)            -- 分类
);
```

修改 `src/api/mysql_client.py` 中的 `get_sku_with_images()` 方法：

```python
def get_sku_with_images(self) -> List[Dict[str, Any]]:
    """从 inventory 表获取 SKU 数据"""
    query = """
        SELECT
            item_code as sku,
            item_name as product_title,
            '' as variant_title,
            cat as category,
            img_path as image_url,
            NULL as price,
            0 as inventory_quantity,
            NULL as weight,
            NULL as barcode,
            NULL as variant_id,
            NULL as product_id
        FROM inventory
        WHERE item_code IS NOT NULL
        ORDER BY item_code
    """

    logger.info("Fetching SKUs from inventory table")
    results = self.execute_query(query)
    logger.info(f"Retrieved {len(results)} SKUs")

    return results
```

### 示例：图片存储在文件系统

如果图片是本地文件路径而非 URL：

```python
def get_sku_with_images(self) -> List[Dict[str, Any]]:
    query = """
        SELECT
            v.sku,
            p.name as product_title,
            v.title as variant_title,
            p.category,
            -- 将文件路径转换为可访问的路径
            CONCAT('/var/www/images/', v.image_filename) as image_url,
            v.price,
            v.inventory_quantity
        FROM product_variants v
        JOIN products p ON v.product_id = p.id
        WHERE v.sku IS NOT NULL
    """
    return self.execute_query(query)
```

然后在下载时使用文件系统复制而非 HTTP 下载：

```python
# 在 mysql_client.py 中添加
def copy_local_image(self, image_path: str, save_path: Path) -> bool:
    """从本地文件系统复制图片"""
    import shutil
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, save_path)
        return True
    except Exception as e:
        logger.error(f"Failed to copy image {image_path}: {e}")
        return False
```

## 常见问题

### Q1: 数据库连接失败

```
Error connecting to MySQL: 2003 (HY000): Can't connect to MySQL server
```

**解决方法**：
1. 检查 MySQL 服务是否运行：`sudo systemctl status mysql`
2. 检查主机地址和端口是否正确
3. 检查防火墙设置
4. 验证用户权限：`GRANT ALL ON database.* TO 'user'@'localhost';`

### Q2: 找不到表或字段

```
Error: Table 'products' doesn't exist
```

**解决方法**：
1. 检查 `.env` 中的数据库名称是否正确
2. 查看你的实际表名：`SHOW TABLES;`
3. 修改 `mysql_client.py` 中的表名和字段名

### Q3: SKU 数量为 0

```
Found 0 SKUs
```

**解决方法**：
1. 检查 SKU 字段是否为 NULL：`SELECT COUNT(*) FROM variants WHERE sku IS NOT NULL;`
2. 检查查询条件是否过于严格
3. 临时移除 WHERE 条件测试

### Q4: 图片下载失败

```
Failed to download image https://...
```

**解决方法**：
1. 检查图片 URL 是否可访问
2. 检查网络连接
3. 如果是内网地址，确保可以访问
4. 考虑使用本地文件路径而非 URL

### Q5: 内存不足

```
MemoryError: Unable to allocate...
```

**解决方法**：
1. 减小批次大小：`--batch-size 500`
2. 分批处理 SKU
3. 不要一次性下载所有图片

## 性能优化

### 1. 使用索引

```sql
-- 为常用查询添加索引
CREATE INDEX idx_sku ON product_variants(sku);
CREATE INDEX idx_category ON products(category);
CREATE INDEX idx_image ON product_variants(image_url(100));
```

### 2. 优化查询

```sql
-- 使用 EXPLAIN 分析查询
EXPLAIN SELECT ... FROM products;

-- 添加必要的索引
```

### 3. 分批处理

对于大量 SKU（>50K），分批下载图片：

```bash
# 第一批：只下载数据
python scripts/download_from_mysql.py --use-optimized-query

# 第二批：下载图片（可以后台运行）
python scripts/download_from_mysql.py --download-images --use-optimized-query &
```

## 使用 Makefile 简化操作

```bash
# 下载数据（使用 MySQL）
make download

# 构建向量数据库
make build

# 完整流程
make all
```

## 下一步

配置完成后：

1. ✅ 测试数据库连接
2. ✅ 下载 SKU 数据和图片
3. ➡️ 构建向量数据库：参考 [README.md](../README.md)
4. ➡️ 运行推理测试

## 技术支持

如需帮助，请提供：
1. 数据库表结构：`DESCRIBE your_table;`
2. 示例数据：`SELECT * FROM your_table LIMIT 3;`
3. 错误日志
