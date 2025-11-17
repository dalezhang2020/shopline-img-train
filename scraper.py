"""
Shopline product scraper module
"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import save_to_database, execute_query
from models import SyncResponse

logger = logging.getLogger(__name__)


def safe_float(value: Any) -> Optional[float]:
    """
    Safely convert value to float

    Args:
        value: Value to convert

    Returns:
        Float value or None
    """
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


async def fetch_backup_image(session: aiohttp.ClientSession, product_id: str) -> str:
    """
    Fetch backup product image from alternative API

    Args:
        session: aiohttp session
        product_id: Product ID

    Returns:
        Image URL
    """
    url = f"https://{settings.SHOPLINE_DOMAIN}.myshopline.com/admin/openapi/{settings.API_VERSION}/products/{product_id}.json"

    headers = {
        'Authorization': settings.API_TOKEN,
        'Content-Type': 'application/json; charset=utf-8',
        'accept': 'application/json'
    }

    try:
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
            ssl=False
        ) as response:
            if response.status == 200:
                data = await response.json()
                image = data.get('image', {})
                return image.get('src', settings.DEFAULT_IMAGE_URL) if image else settings.DEFAULT_IMAGE_URL
    except Exception as e:
        logger.warning(f"Failed to fetch backup image for product {product_id}: {str(e)}")

    return settings.DEFAULT_IMAGE_URL


def extract_variants_from_product(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract variant information from product data

    Args:
        product: Shopline product data

    Returns:
        List of variant data
    """
    variants = product.get('variants', [])
    product_title = product.get('website_name', '')

    result = []
    for variant in variants:
        variant_title = variant.get('title', '')
        full_name = f"{product_title} - {variant_title}" if variant_title else product_title

        result.append({
            'product_id': product['product_id'],
            'listing_id': product['listing_id'],
            'website_name': full_name,
            'is_visible': product['is_visible'],
            'date_created': product['date_created'],
            'sku': variant.get('sku', ''),
            'price': safe_float(variant.get('price')),
            'sale_price': safe_float(variant.get('compare_at_price')),
            'inventory_level': variant.get('inventory_quantity', 0),
            'image_url': variant.get('image', {}).get('src', '') if variant.get('image') else '',
            'custom_url': product['custom_url'],
            'handle': product.get('handle', ''),
            'inventory_item_id': variant.get('inventory_item_id', ''),
            'productimg_url': product.get('productimg_url', settings.DEFAULT_IMAGE_URL),
            'variant_id': variant.get('id', '')
        })

    return result


async def process_product_with_image(
    session: aiohttp.ClientSession,
    product: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Process single product, fetch image and variant information

    Args:
        session: aiohttp session
        product: Product data

    Returns:
        List of variants with images
    """
    # Get product image
    image = product.get('image', {})
    img_url = image.get('src', '') if image else ''

    # If image URL too short, fetch from backup API
    if len(img_url) < 20:
        img_url = await fetch_backup_image(session, product['product_id'])

    product['productimg_url'] = img_url

    # Extract variant information
    variants = extract_variants_from_product(product)

    return variants


async def fetch_shopline_products() -> List[Dict[str, Any]]:
    """
    Fetch all product data from Shopline API

    Returns:
        List of product data
    """
    url = f"https://{settings.SHOPLINE_DOMAIN}.myshopline.com/admin/openapi/{settings.API_VERSION}/products/products.json"
    product_data = []
    page_info = None
    total_products = 0

    headers = {
        'Authorization': settings.API_TOKEN,
        'Content-Type': 'application/json; charset=utf-8',
        'accept': 'application/json'
    }

    logger.info("Starting to fetch Shopline product data...")

    async with aiohttp.ClientSession() as session:
        while True:
            params = {
                'limit': 250,
                'fields': 'id,title,handle,status,created_at,spu,variants,image,path'
            }
            if page_info:
                params['page_info'] = page_info

            try:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                    ssl=False
                ) as response:
                    response.raise_for_status()
                    results = await response.json()

                    # Shopline API returns product array directly
                    products = results if isinstance(results, list) else results.get('products', [])

                    if not products:
                        break

                    # Extract product information
                    for product in products:
                        product_data.append({
                            'product_id': product['id'],
                            'listing_id': product.get('spu', ''),
                            'website_name': product.get('title', ''),
                            'is_visible': '1' if product.get('status', '') == 'active' else '0',
                            'date_created': product.get('created_at', ''),
                            'custom_url': product.get('path', ''),
                            'handle': product.get('handle', ''),
                            'variants': product.get('variants', []),
                            'image': product.get('image', {})
                        })

                    total_products += len(products)
                    logger.info(f"Fetched {total_products} products")

                    # Check if there's a next page
                    link_header = response.headers.get('Link', '')
                    if 'rel="next"' in link_header:
                        match = re.search(r'page_info=([^>]+)>', link_header)
                        if match:
                            page_info = match.group(1)
                        else:
                            break
                    else:
                        break

                    await asyncio.sleep(0.2)  # Rate limiting

            except Exception as e:
                logger.error(f"Failed to fetch product data: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to fetch products: {str(e)}")

    logger.info(f"Total {total_products} products fetched, processing variant information...")
    return product_data


async def process_products_to_variants(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process product list to extract all variant information

    Args:
        products: List of product data

    Returns:
        List of variant data
    """
    all_variants = []

    async with aiohttp.ClientSession() as session:
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(10)

        async def process_with_semaphore(product):
            async with semaphore:
                return await process_product_with_image(session, product)

        # Process all products concurrently
        tasks = [process_with_semaphore(product) for product in products]
        results = await asyncio.gather(*tasks)

        # Flatten results
        for variants in results:
            all_variants.extend(variants)

    logger.info(f"Processing complete, total {len(all_variants)} SKU records")
    return all_variants


def clean_variant_data(variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean and transform variant data

    Args:
        variants: Raw variant data

    Returns:
        Cleaned variant data
    """
    cleaned = []

    for variant in variants:
        # Process image URL
        image_url = variant.get('image_url', '').strip()
        if not image_url or len(image_url) < 20:
            image_url = variant.get('productimg_url', settings.DEFAULT_IMAGE_URL)
        variant['image_url'] = image_url

        # Fill empty string fields
        for field in ['sku', 'custom_url', 'website_name', 'listing_id', 'handle']:
            if not variant.get(field):
                variant[field] = ' '

        # Only keep records with SKU
        if variant.get('sku', '').strip():
            cleaned.append(variant)

    return cleaned


async def sync_shopline_skuinfo(
    db: AsyncSession,
    mode: str = "replace",
    save_history: bool = True
) -> SyncResponse:
    """
    Sync Shopline SKU information

    Args:
        db: Database session
        mode: Sync mode - 'replace' or 'append'
        save_history: Whether to save history records

    Returns:
        Sync response
    """
    start_time = datetime.now()

    try:
        logger.info(f"Starting Shopline SKU information sync (mode: {mode})")

        # 1. Fetch product data
        products = await fetch_shopline_products()

        if not products:
            return SyncResponse(
                success=True,
                message="No product data found",
                records_synced=0,
                execution_time=0,
                table_name=settings.TARGET_TABLE,
                sync_mode=mode
            )

        # 2. Process products to extract variant information
        variants = await process_products_to_variants(products)

        # 3. Clean data
        cleaned_variants = clean_variant_data(variants)

        if not cleaned_variants:
            return SyncResponse(
                success=True,
                message="No valid SKU data found",
                records_synced=0,
                execution_time=(datetime.now() - start_time).total_seconds(),
                table_name=settings.TARGET_TABLE,
                sync_mode=mode
            )

        # 4. Save to main table
        logger.info(f"Starting to save {len(cleaned_variants)} SKU records to database...")
        records_saved = await save_to_database(db, cleaned_variants, settings.TARGET_TABLE, mode)

        # 5. Handle history records
        history_saved = 0
        if save_history:
            current_date = datetime.now().strftime('%Y-%m-%d')

            # Query max date in history table
            max_date_query = f"SELECT MAX(recorddate) as maxdate FROM {settings.HISTORY_TABLE}"
            result = await execute_query(db, max_date_query)
            max_date = result[0]['maxdate'] if result and result[0]['maxdate'] else None

            if max_date == current_date:
                logger.info("Today's history record already exists, skipping")
            else:
                logger.info("Starting to save history records...")
                # Prepare history record data
                history_data = []
                for variant in cleaned_variants:
                    history_record = {
                        'listing_id': variant['listing_id'],
                        'sku': variant['sku'],
                        'price': variant['price'],
                        'sale_price': variant['sale_price'],
                        'inventory_level': variant['inventory_level'],
                        'is_visible': variant['is_visible'],
                        'recorddate': current_date
                    }
                    history_data.append(history_record)

                history_saved = await save_to_database(db, history_data, settings.HISTORY_TABLE, 'add')
                logger.info(f"History record save complete: {history_saved} records")

        execution_time = (datetime.now() - start_time).total_seconds()

        message = f"Successfully synced {records_saved} SKU records"
        if history_saved > 0:
            message += f", saved {history_saved} history records"

        return SyncResponse(
            success=True,
            message=message,
            records_synced=records_saved,
            execution_time=execution_time,
            table_name=settings.TARGET_TABLE,
            sync_mode=mode
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SKU sync failed: {str(e)}")
        execution_time = (datetime.now() - start_time).total_seconds()

        return SyncResponse(
            success=False,
            message="SKU sync operation failed",
            records_synced=0,
            execution_time=execution_time,
            error=str(e),
            table_name=settings.TARGET_TABLE,
            sync_mode=mode
        )
