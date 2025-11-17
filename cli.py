"""
Command-line interface for Shopline scraper
"""
import asyncio
import argparse
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import AsyncSessionLocal, test_connection
from scraper import sync_shopline_skuinfo

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Shopline Product Scraper CLI')
    parser.add_argument(
        '--mode',
        choices=['replace', 'append'],
        default='replace',
        help='Sync mode: replace (truncate first) or append (add to existing)'
    )
    parser.add_argument(
        '--no-history',
        action='store_true',
        help='Skip saving history records'
    )
    parser.add_argument(
        '--test-db',
        action='store_true',
        help='Test database connection only'
    )

    args = parser.parse_args()

    # Test database connection if requested
    if args.test_db:
        logger.info("Testing database connection...")
        if await test_connection():
            logger.info("✓ Database connection successful")
            return 0
        else:
            logger.error("✗ Database connection failed")
            return 1

    # Run sync operation
    save_history = not args.no_history

    logger.info("=" * 60)
    logger.info("Shopline Product Scraper")
    logger.info("=" * 60)
    logger.info(f"Domain: {settings.SHOPLINE_DOMAIN}")
    logger.info(f"API Version: {settings.API_VERSION}")
    logger.info(f"Sync Mode: {args.mode}")
    logger.info(f"Save History: {save_history}")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            result = await sync_shopline_skuinfo(
                db,
                mode=args.mode,
                save_history=save_history
            )

            logger.info("=" * 60)
            logger.info("Sync Complete")
            logger.info("=" * 60)
            logger.info(f"Status: {'Success' if result.success else 'Failed'}")
            logger.info(f"Message: {result.message}")
            logger.info(f"Records Synced: {result.records_synced}")
            logger.info(f"Execution Time: {result.execution_time:.2f}s")
            logger.info(f"Table: {result.table_name}")
            logger.info(f"Mode: {result.sync_mode}")
            if result.error:
                logger.error(f"Error: {result.error}")
            logger.info("=" * 60)

            return 0 if result.success else 1

        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
