# Shopline Product Scraper

A robust, asynchronous web scraper for fetching product and SKU information from Shopline stores. Built with Python, FastAPI, and asyncio for high-performance data collection.

## Features

- **Asynchronous scraping** - Fast, concurrent data fetching using aiohttp
- **Complete product data** - Retrieves products, variants, images, pricing, and inventory
- **History tracking** - Automatic daily snapshots of SKU data
- **Flexible sync modes** - Replace or append data
- **REST API** - Easy integration with FastAPI endpoints
- **CLI interface** - Command-line tool for direct execution
- **Robust error handling** - Retry logic and comprehensive logging
- **Database integration** - PostgreSQL with SQLAlchemy async support

## Architecture

```
shopline-img-train/
├── config.py          # Configuration management
├── database.py        # Database connection and operations
├── models.py          # Data models and schemas
├── scraper.py         # Core scraping logic
├── main.py            # FastAPI application
├── cli.py             # Command-line interface
├── schema.sql         # Database schema
├── requirements.txt   # Python dependencies
└── .env              # Environment variables (create from .env.example)
```

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd shopline-img-train
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up database**
   ```bash
   psql -U your_user -d your_database -f schema.sql
   ```

## Configuration

Edit `.env` file with your settings:

```env
# Shopline API Configuration
SHOPLINE_DOMAIN=your_store_domain
API_VERSION=v20251201
API_TOKEN=Bearer your_api_token_here

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Application Settings
DEFAULT_IMAGE_URL=https://example.com/default.jpg
LOG_LEVEL=INFO
```

### Getting Shopline API Token

1. Log in to your Shopline admin panel
2. Navigate to Apps & Integrations
3. Create a new API token with appropriate permissions
4. Copy the token and add it to your `.env` file

## Usage

### API Server

Start the FastAPI server:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### API Endpoints

**GET /** - API information
```bash
curl http://localhost:8000/
```

**GET /health** - Health check
```bash
curl http://localhost:8000/health
```

**POST /sync** - Sync products
```bash
# Replace mode (default)
curl -X POST "http://localhost:8000/sync?mode=replace&save_history=true"

# Append mode
curl -X POST "http://localhost:8000/sync?mode=append&save_history=true"
```

### Command-Line Interface

Run the scraper directly:

```bash
# Replace mode with history
python cli.py --mode replace

# Append mode without history
python cli.py --mode append --no-history

# Test database connection
python cli.py --test-db
```

**CLI Options:**
- `--mode {replace,append}` - Sync mode (default: replace)
- `--no-history` - Skip saving history records
- `--test-db` - Test database connection only

## Data Flow

1. **Fetch Products** - Retrieves all products from Shopline API with pagination
2. **Process Variants** - Extracts variant information from each product
3. **Fetch Images** - Gets product images (with fallback logic)
4. **Clean Data** - Validates and normalizes data
5. **Save to Database** - Stores SKU information in main table
6. **Save History** - Creates daily snapshot in history table

## Database Schema

### api_bc_skuinfo (Main Table)

Stores current SKU information:

| Column | Type | Description |
|--------|------|-------------|
| product_id | VARCHAR(100) | Shopline product ID |
| listing_id | VARCHAR(100) | Product listing ID (SPU) |
| website_name | VARCHAR(500) | Product title |
| sku | VARCHAR(200) | SKU code |
| price | DECIMAL(10,2) | Current price |
| sale_price | DECIMAL(10,2) | Compare at price |
| inventory_level | INTEGER | Stock quantity |
| image_url | TEXT | Variant image URL |
| productimg_url | TEXT | Product main image URL |
| variant_id | VARCHAR(100) | Variant ID |
| is_visible | VARCHAR(1) | Visibility status |
| custom_url | VARCHAR(500) | Product URL path |
| handle | VARCHAR(200) | Product handle |

### hisrecord_bcsku (History Table)

Stores daily snapshots:

| Column | Type | Description |
|--------|------|-------------|
| listing_id | VARCHAR(100) | Product listing ID |
| sku | VARCHAR(200) | SKU code |
| price | DECIMAL(10,2) | Price at time of record |
| sale_price | DECIMAL(10,2) | Sale price at time of record |
| inventory_level | INTEGER | Stock at time of record |
| is_visible | VARCHAR(1) | Visibility status |
| recorddate | DATE | Record date |

## Sync Modes

### Replace Mode
- Truncates existing data in main table
- Inserts fresh data from API
- Recommended for daily full syncs

### Append Mode
- Keeps existing data
- Adds new records
- Useful for incremental updates

## Error Handling

The scraper includes comprehensive error handling:

- **Network errors** - Automatic retry with exponential backoff
- **API rate limiting** - Built-in delays between requests
- **Missing images** - Fallback to backup API or default image
- **Invalid data** - Validation and sanitization
- **Database errors** - Transaction rollback and logging

## Logging

Logs include:

- API request progress
- Data processing statistics
- Error messages with stack traces
- Performance metrics

Log level can be configured via `LOG_LEVEL` in `.env`.

## Performance

- **Concurrent fetching** - Up to 10 concurrent product processing tasks
- **Batch operations** - Efficient bulk database inserts
- **Pagination** - Handles large product catalogs (250 items per page)
- **Connection pooling** - Optimized database connections

## Development

### Running Tests

```bash
# Add your test commands here
pytest tests/
```

### Code Style

```bash
# Format code
black .

# Lint code
flake8 .
```

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
python cli.py --test-db
```

### API Authentication Errors

- Verify `API_TOKEN` is correct and includes "Bearer " prefix
- Check token hasn't expired
- Ensure API permissions are sufficient

### No Products Found

- Verify `SHOPLINE_DOMAIN` is correct
- Check API version compatibility
- Confirm store has published products

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
- Open an issue on GitHub
- Contact: [your-email@example.com]

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [aiohttp](https://docs.aiohttp.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Pydantic](https://docs.pydantic.dev/)
