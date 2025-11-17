# 数据库表结构说明

## 概述

本文档说明系统所需的 MySQL 数据库表结构。你可以根据实际数据库调整表名和字段名。

## 核心表结构

### 1. products 表（产品主表）

存储产品的基本信息。

```sql
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL COMMENT '产品名称',
    category VARCHAR(100) COMMENT '产品分类',
    description TEXT COMMENT '产品描述',
    product_type VARCHAR(100) COMMENT '产品类型',
    vendor VARCHAR(100) COMMENT '供应商',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品主表';
```

### 2. product_variants 表（产品变体/SKU 表）

存储每个产品的 SKU 信息和库存。

```sql
CREATE TABLE product_variants (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL COMMENT '关联的产品ID',
    sku VARCHAR(100) NOT NULL COMMENT 'SKU编码',
    title VARCHAR(255) COMMENT '变体标题',
    price DECIMAL(10, 2) COMMENT '价格',
    inventory_quantity INT DEFAULT 0 COMMENT '库存数量',
    weight DECIMAL(10, 2) COMMENT '重量',
    barcode VARCHAR(100) COMMENT '条形码',
    image_url TEXT COMMENT '变体图片URL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY uk_sku (sku),
    INDEX idx_product_id (product_id),
    INDEX idx_sku (sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品变体SKU表';
```

### 3. product_images 表（产品图片表，可选）

如果图片不存储在 variants 表中，可以使用独立的图片表。

```sql
CREATE TABLE product_images (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL COMMENT '关联的产品ID',
    url TEXT NOT NULL COMMENT '图片URL',
    position INT DEFAULT 0 COMMENT '图片位置（用于排序）',
    alt_text VARCHAR(255) COMMENT '图片描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product_id (product_id),
    INDEX idx_position (position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品图片表';
```

## 示例数据

### products 表示例

```sql
INSERT INTO products (id, name, category, description) VALUES
(1, 'Modern Sofa', 'FURNITURE', '现代简约三人沙发'),
(2, 'Table Lamp', 'LIGHTING', '北欧风格台灯'),
(3, 'Wall Art', 'DECOR', '抽象艺术挂画');
```

### product_variants 表示例

```sql
INSERT INTO product_variants (product_id, sku, title, price, inventory_quantity, image_url) VALUES
(1, 'SOFA-GRY-001', 'Gray', 1999.00, 5, 'https://example.com/images/sofa-gray.jpg'),
(1, 'SOFA-BLU-001', 'Blue', 2099.00, 3, 'https://example.com/images/sofa-blue.jpg'),
(2, 'LAMP-WHT-001', 'White', 299.00, 10, 'https://example.com/images/lamp-white.jpg'),
(3, 'ART-ABS-001', 'Abstract', 599.00, 8, 'https://example.com/images/art-abstract.jpg');
```

## 查询示例

### 获取所有 SKU 及其图片（优化版）

这是系统使用的主要查询：

```sql
SELECT
    v.sku,
    v.id as variant_id,
    v.product_id,
    p.name as product_title,
    v.title as variant_title,
    p.category,
    v.price,
    v.inventory_quantity,
    v.weight,
    v.barcode,
    COALESCE(v.image_url, pi.url) as image_url
FROM product_variants v
JOIN products p ON v.product_id = p.id
LEFT JOIN product_images pi ON pi.product_id = p.id AND pi.position = 1
WHERE v.sku IS NOT NULL AND v.sku != ''
ORDER BY v.id;
```

### 按分类查询产品

```sql
SELECT
    p.id,
    p.name,
    p.category,
    COUNT(v.id) as variant_count
FROM products p
LEFT JOIN product_variants v ON v.product_id = p.id
WHERE p.category = 'FURNITURE'
GROUP BY p.id, p.name, p.category;
```

### 获取特定产品的所有 SKU

```sql
SELECT
    v.sku,
    v.title,
    v.price,
    v.inventory_quantity,
    v.image_url
FROM product_variants v
WHERE v.product_id = 1;
```

## 自定义表结构

如果你的数据库表结构不同，需要修改以下文件：

### 1. 修改 `src/api/mysql_client.py`

找到以下方法并根据你的表结构调整 SQL 查询：

#### `get_products()` 方法

```python
# 修改这部分 SQL
query = """
    SELECT
        p.id as product_id,
        p.name as title,           # 调整字段名
        p.category,
        p.description,
        p.created_at,
        p.updated_at
    FROM products p                # 调整表名
"""
```

#### `get_product_variants()` 方法

```python
# 修改这部分 SQL
query = """
    SELECT
        v.id as variant_id,
        v.product_id,
        v.sku,
        v.title as variant_title,  # 调整字段名
        v.price,
        v.inventory_quantity,
        v.weight,
        v.barcode,
        v.image_url
    FROM product_variants v        # 调整表名
    WHERE v.product_id = %s
"""
```

#### `get_sku_with_images()` 方法

```python
# 修改这部分 SQL - 根据你的图片存储方式调整
query = """
    SELECT
        v.sku,
        v.id as variant_id,
        v.product_id,
        p.name as product_title,
        v.title as variant_title,
        p.category,
        v.price,
        v.inventory_quantity,
        v.weight,
        v.barcode,
        COALESCE(v.image_url, pi.url) as image_url  # 图片字段
    FROM product_variants v
    JOIN products p ON v.product_id = p.id
    LEFT JOIN product_images pi ON pi.product_id = p.id AND pi.position = 1
    WHERE v.sku IS NOT NULL AND v.sku != ''
    ORDER BY v.id
"""
```

## 字段映射说明

系统期望的字段和你的数据库字段的对应关系：

| 系统字段 | 说明 | 你的数据库字段 |
|---------|------|---------------|
| sku | SKU 编码（必需） | 例如: `variant_code`, `item_no` |
| product_title | 产品名称 | 例如: `product_name`, `title` |
| variant_title | 变体名称 | 例如: `variant_name`, `spec` |
| category | 分类 | 例如: `category_name`, `type` |
| image_url | 图片 URL（必需） | 例如: `img_url`, `photo` |
| price | 价格 | 例如: `sale_price`, `unit_price` |
| inventory_quantity | 库存 | 例如: `stock`, `qty` |

## 最小化数据要求

系统**最少需要**以下字段：

1. **SKU 编码** - 唯一标识每个产品变体
2. **图片 URL** - 用于训练和识别
3. **产品标题** - 用于显示结果

可选但建议包含的字段：
- 分类 (category)
- 价格 (price)
- 库存 (inventory_quantity)

## 性能优化建议

### 1. 添加索引

```sql
-- SKU 索引（必需）
CREATE INDEX idx_sku ON product_variants(sku);

-- 产品分类索引
CREATE INDEX idx_category ON products(category);

-- 外键索引
CREATE INDEX idx_product_id ON product_variants(product_id);
```

### 2. 查询优化

对于大数据量（>100K SKU），建议：

```sql
-- 添加复合索引
CREATE INDEX idx_sku_image ON product_variants(sku, image_url);

-- 分区表（如果 SKU 数量超过百万）
ALTER TABLE product_variants
PARTITION BY RANGE (id) (
    PARTITION p0 VALUES LESS THAN (100000),
    PARTITION p1 VALUES LESS THAN (200000),
    PARTITION p2 VALUES LESS THAN MAXVALUE
);
```

## 测试数据库连接

使用以下 Python 脚本测试连接：

```python
from src.api.mysql_client import MySQLClient

# 连接数据库
client = MySQLClient(
    host='localhost',
    database='your_database',
    user='your_user',
    password='your_password'
)

# 测试连接
client.connect()

# 获取统计信息
stats = client.get_stats()
print(stats)

# 测试查询
skus = client.get_sku_with_images()
print(f"Found {len(skus)} SKUs")

# 关闭连接
client.disconnect()
```

## 常见问题

### Q: 我的表结构完全不同怎么办？

A: 你需要修改 `src/api/mysql_client.py` 中的 SQL 查询。关键是确保返回的数据包含：
- sku（字符串）
- image_url（字符串URL）
- title（产品名称）

### Q: 图片存储在文件系统而不是 URL？

A: 修改查询，将文件路径转换为 URL，或直接使用本地路径：

```sql
SELECT
    CONCAT('/path/to/images/', v.image_filename) as image_url
FROM product_variants v
```

### Q: 没有 product_variants 表，所有信息都在一个表？

A: 简化查询，直接从单表读取：

```python
def get_sku_with_images(self):
    query = """
        SELECT
            sku,
            product_name as product_title,
            category,
            image_url,
            price
        FROM your_single_table
        WHERE sku IS NOT NULL
    """
    return self.execute_query(query)
```

## 下一步

配置好数据库后：

1. 配置 `.env` 文件中的数据库连接信息
2. 运行 `python scripts/download_from_mysql.py --use-optimized-query` 测试数据获取
3. 继续构建向量数据库
