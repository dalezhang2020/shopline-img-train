#!/usr/bin/env python3
"""
Test MySQL database connection
"""
import os
from dotenv import load_dotenv
import pymysql

def test_connection():
    """Test MySQL database connection"""
    load_dotenv()

    config = {
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

    print(f"正在连接数据库：{config['host']}:{config['port']}...")
    print(f"数据库：{config['database']}")
    print(f"用户：{config['user']}")

    try:
        # 建立连接
        connection = pymysql.connect(**config)
        print("✓ 数据库连接成功！")

        # 获取基本信息
        with connection.cursor() as cursor:
            # 检查表是否存在
            cursor.execute("SELECT COUNT(*) as count FROM api_scm_skuinfo LIMIT 1")
            result = cursor.fetchone()
            if result:
                print(f"✓ api_scm_skuinfo 表存在")

                # 获取SKU数量
                cursor.execute("SELECT COUNT(*) as count FROM api_scm_skuinfo WHERE image_url != '**'")
                sku_count = cursor.fetchone()['count']
                print(f"✓ 找到 {sku_count} 个有图片的SKU")
            else:
                print("✗ api_scm_skuinfo 表不存在或无法访问")

        connection.close()
        return True

    except Exception as e:
        print(f"✗ 连接失败：{e}")
        return False

if __name__ == '__main__':
    test_connection()
