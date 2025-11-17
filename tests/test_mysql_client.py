"""Tests for MySQL client"""

import pytest
from unittest.mock import Mock, patch
from src.api.mysql_client import MySQLClient


def test_mysql_client_initialization():
    """Test MySQL client initialization"""
    client = MySQLClient(
        host="localhost",
        database="test_db",
        user="test_user",
        password="test_pass"
    )

    assert client.host == "localhost"
    assert client.database == "test_db"
    assert client.user == "test_user"
    assert client.port == 3306


@patch('mysql.connector.connect')
def test_mysql_connection(mock_connect):
    """Test MySQL connection"""
    mock_conn = Mock()
    mock_conn.is_connected.return_value = True
    mock_connect.return_value = mock_conn

    client = MySQLClient(
        host="localhost",
        database="test_db",
        user="test_user",
        password="test_pass"
    )

    client.connect()
    assert client.connection is not None
    mock_connect.assert_called_once()


def test_sku_extraction():
    """Test SKU data extraction"""
    client = MySQLClient(
        host="localhost",
        database="test_db",
        user="test_user",
        password="test_pass"
    )

    product = {
        "product_id": 1,
        "title": "Test Product",
        "category": "FURNITURE",
        "variants": [
            {
                "id": 1,
                "sku": "SKU-001",
                "title": "Variant 1",
                "price": 99.99,
                "image_url": "https://example.com/image.jpg"
            }
        ]
    }

    sku_data = client.extract_sku_data(product)

    assert len(sku_data) == 1
    assert sku_data[0]["sku"] == "SKU-001"
    assert sku_data[0]["category"] == "FURNITURE"
    assert sku_data[0]["price"] == 99.99
