"""MySQL database client for fetching SKU data"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import mysql.connector
from mysql.connector import Error
import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)


class MySQLClient:
    """Client for fetching SKU data from MySQL database"""

    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        port: int = 3306,
    ):
        """
        Initialize MySQL client

        Args:
            host: MySQL server host
            database: Database name
            user: Database user
            password: Database password
            port: MySQL server port (default: 3306)
        """
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.connection = None

        logger.info(f"Initialized MySQL client for {host}:{port}/{database}")

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
            )

            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                logger.info(f"Successfully connected to MySQL Server version {db_info}")
                cursor = self.connection.cursor()
                cursor.execute("SELECT DATABASE();")
                record = cursor.fetchone()
                logger.info(f"Connected to database: {record[0]}")
                cursor.close()

        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("MySQL connection closed")

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as list of dictionaries

        Args:
            query: SQL query string
            params: Query parameters (for prepared statements)

        Returns:
            List of result dictionaries
        """
        if not self.connection or not self.connection.is_connected():
            self.connect()

        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.close()
            return results

        except Error as e:
            logger.error(f"Error executing query: {e}")
            raise

    def get_products(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch products from database

        Args:
            limit: Maximum number of products to fetch
            offset: Number of products to skip
            category: Filter by category

        Returns:
            List of product data dictionaries

        Note: You may need to adjust the table names and column names
        based on your actual database schema
        """
        # Base query - ADJUST TABLE AND COLUMN NAMES AS NEEDED
        query = """
            SELECT
                p.id as product_id,
                p.name as title,
                p.category,
                p.description,
                p.created_at,
                p.updated_at
            FROM products p
        """

        conditions = []
        params = []

        if category:
            conditions.append("p.category = %s")
            params.append(category)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY p.id"

        if limit:
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])

        logger.info(f"Fetching products (limit={limit}, offset={offset}, category={category})")
        results = self.execute_query(query, tuple(params) if params else None)
        logger.info(f"Retrieved {len(results)} products")

        return results

    def get_product_variants(self, product_id: int) -> List[Dict[str, Any]]:
        """
        Get variants (SKUs) for a specific product

        Args:
            product_id: Product ID

        Returns:
            List of variant/SKU data

        Note: Adjust table and column names based on your schema
        """
        query = """
            SELECT
                v.id as variant_id,
                v.product_id,
                v.sku,
                v.title as variant_title,
                v.price,
                v.inventory_quantity,
                v.weight,
                v.barcode,
                v.image_url
            FROM product_variants v
            WHERE v.product_id = %s
        """

        results = self.execute_query(query, (product_id,))
        return results

    def get_all_products(
        self,
        categories: Optional[List[str]] = None,
        batch_size: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all products with pagination

        Args:
            categories: List of categories to filter
            batch_size: Number of products per batch

        Returns:
            List of all product data
        """
        all_products = []

        if categories:
            # Fetch products by category
            for category in categories:
                logger.info(f"Fetching products for category: {category}")
                offset = 0

                while True:
                    products = self.get_products(
                        limit=batch_size,
                        offset=offset,
                        category=category,
                    )

                    if not products:
                        break

                    all_products.extend(products)
                    offset += batch_size

        else:
            # Fetch all products
            offset = 0

            while True:
                products = self.get_products(limit=batch_size, offset=offset)

                if not products:
                    break

                all_products.extend(products)
                offset += batch_size

        logger.info(f"Total products fetched: {len(all_products)}")
        return all_products

    def get_sku_with_images(self) -> List[Dict[str, Any]]:
        """
        Fetch all SKUs with their images in one query (more efficient)

        Returns:
            List of SKU data with images

        Note: Adjust based on your schema. This assumes:
        - products table
        - product_variants table
        - product_images table (or images stored in variants)
        """
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
                COALESCE(v.image_url, pi.url) as image_url
            FROM product_variants v
            JOIN products p ON v.product_id = p.id
            LEFT JOIN product_images pi ON pi.product_id = p.id AND pi.position = 1
            WHERE v.sku IS NOT NULL AND v.sku != ''
            ORDER BY v.id
        """

        logger.info("Fetching all SKUs with images")
        results = self.execute_query(query)
        logger.info(f"Retrieved {len(results)} SKUs")

        return results

    def extract_sku_data(self, product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract SKU data from product information

        Args:
            product: Product data dictionary

        Returns:
            List of SKU data with images
        """
        product_id = product.get("product_id")

        # Get variants for this product
        variants = self.get_product_variants(product_id)

        sku_data = []

        for variant in variants:
            sku = variant.get("sku")
            if not sku:
                continue

            sku_info = {
                "sku": sku,
                "product_id": product_id,
                "variant_id": variant.get("variant_id"),
                "title": f"{product.get('title', '')} - {variant.get('variant_title', '')}".strip(" - "),
                "category": product.get("category"),
                "image_url": variant.get("image_url"),
                "price": variant.get("price"),
                "inventory": variant.get("inventory_quantity", 0),
                "weight": variant.get("weight"),
                "barcode": variant.get("barcode"),
                "metadata": {
                    "product_title": product.get("title"),
                    "variant_title": variant.get("variant_title"),
                    "description": product.get("description"),
                }
            }

            sku_data.append(sku_info)

        return sku_data

    def download_image(self, image_url: str, save_path: Path) -> bool:
        """
        Download product image from URL

        Args:
            image_url: URL of the image
            save_path: Path to save the image

        Returns:
            True if successful, False otherwise
        """
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)

            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.debug(f"Downloaded image: {save_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {e}")
            return False

    def save_sku_data(self, sku_data: List[Dict[str, Any]], output_path: Path):
        """
        Save SKU data to JSON file

        Args:
            sku_data: List of SKU data dictionaries
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sku_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(sku_data)} SKU records to {output_path}")

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}

        # Count total products
        query = "SELECT COUNT(*) as count FROM products"
        result = self.execute_query(query)
        stats['total_products'] = result[0]['count'] if result else 0

        # Count total SKUs
        query = "SELECT COUNT(*) as count FROM product_variants WHERE sku IS NOT NULL"
        result = self.execute_query(query)
        stats['total_skus'] = result[0]['count'] if result else 0

        # Count products by category
        query = "SELECT category, COUNT(*) as count FROM products GROUP BY category"
        result = self.execute_query(query)
        stats['products_by_category'] = {row['category']: row['count'] for row in result}

        return stats

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
