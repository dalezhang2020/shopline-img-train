"""Shopline API Client for fetching SKU and product data"""

import os
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import json

logger = logging.getLogger(__name__)


class ShoplineClient:
    """Client for interacting with Shopline API"""

    def __init__(
        self,
        access_token: Optional[str] = None,
        shop_name: Optional[str] = None,
        api_url: str = "https://api.shoplineapp.com",
        api_version: str = "v1",
    ):
        """
        Initialize Shopline API client

        Args:
            access_token: Shopline API access token
            shop_name: Shop name/identifier
            api_url: Base API URL
            api_version: API version
        """
        self.access_token = access_token or os.getenv("SHOPLINE_ACCESS_TOKEN")
        self.shop_name = shop_name or os.getenv("SHOPLINE_SHOP_NAME")
        self.api_url = api_url
        self.api_version = api_version

        if not self.access_token:
            raise ValueError("Access token is required. Set SHOPLINE_ACCESS_TOKEN environment variable.")

        if not self.shop_name:
            raise ValueError("Shop name is required. Set SHOPLINE_SHOP_NAME environment variable.")

        # Setup session with retry strategy
        self.session = self._create_session()

        logger.info(f"Initialized Shopline client for shop: {self.shop_name}")

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        return session

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make API request with error handling

        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request body data

        Returns:
            Response data as dictionary
        """
        url = f"{self.api_url}/{self.api_version}/{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            logger.error(f"Response content: {e.response.text if e.response else 'No response'}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def get_products(
        self,
        limit: int = 100,
        page: int = 1,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch products from Shopline

        Args:
            limit: Number of products per page
            page: Page number
            category: Filter by category

        Returns:
            List of product data dictionaries
        """
        params = {
            "limit": limit,
            "page": page,
        }

        if category:
            params["category"] = category

        logger.info(f"Fetching products (page {page}, limit {limit})")
        response = self._make_request("products", params=params)

        products = response.get("products", [])
        logger.info(f"Retrieved {len(products)} products")

        return products

    def get_all_products(
        self,
        categories: Optional[List[str]] = None,
        batch_size: int = 100,
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
                page = 1
                while True:
                    products = self.get_products(
                        limit=batch_size,
                        page=page,
                        category=category
                    )

                    if not products:
                        break

                    all_products.extend(products)
                    page += 1
                    time.sleep(0.5)  # Rate limiting
        else:
            # Fetch all products
            page = 1
            while True:
                products = self.get_products(limit=batch_size, page=page)

                if not products:
                    break

                all_products.extend(products)
                page += 1
                time.sleep(0.5)  # Rate limiting

        logger.info(f"Total products fetched: {len(all_products)}")
        return all_products

    def get_product_variants(self, product_id: str) -> List[Dict[str, Any]]:
        """
        Get variants (SKUs) for a specific product

        Args:
            product_id: Product ID

        Returns:
            List of variant/SKU data
        """
        endpoint = f"products/{product_id}/variants"
        response = self._make_request(endpoint)
        return response.get("variants", [])

    def download_image(self, image_url: str, save_path: Path) -> bool:
        """
        Download product image

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

    def extract_sku_data(self, product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract SKU data from product information

        Args:
            product: Product data dictionary

        Returns:
            List of SKU data with images
        """
        sku_data = []

        product_id = product.get("id")
        product_title = product.get("title", "")
        product_category = product.get("category", "")
        product_images = product.get("images", [])

        # Get variants (SKUs)
        variants = product.get("variants", [])

        for variant in variants:
            sku = variant.get("sku")
            if not sku:
                continue

            # Get variant-specific image or use product image
            variant_image = variant.get("image_url")
            if not variant_image and product_images:
                variant_image = product_images[0].get("src")

            sku_info = {
                "sku": sku,
                "product_id": product_id,
                "variant_id": variant.get("id"),
                "title": f"{product_title} - {variant.get('title', '')}".strip(" - "),
                "category": product_category,
                "image_url": variant_image,
                "price": variant.get("price"),
                "inventory": variant.get("inventory_quantity", 0),
                "weight": variant.get("weight"),
                "barcode": variant.get("barcode"),
                "metadata": {
                    "product_title": product_title,
                    "variant_title": variant.get("title"),
                    "product_type": product.get("product_type"),
                    "vendor": product.get("vendor"),
                    "tags": product.get("tags", []),
                }
            }

            sku_data.append(sku_info)

        return sku_data

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
