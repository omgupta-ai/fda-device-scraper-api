"""
Test file for FDA Device API
Basic tests to verify API functionality.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_scrape_endpoint_missing_device_name():
    """Test scrape endpoint without required device_name parameter"""
    response = client.get("/scrape")
    assert response.status_code == 422  # Validation error

def test_scrape_endpoint_with_device_name():
    """Test scrape endpoint with device_name - this will actually scrape so it may be slow"""
    # Note: This test will make real HTTP requests to FDA
    response = client.get("/scrape?device_name=syringe")
    
    # Should return 200 even if no results found
    assert response.status_code == 200
    
    data = response.json()
    assert "search_params" in data
    assert "devices" in data
    assert data["search_params"]["device_name"] == "syringe"

def test_scrape_endpoint_with_all_params():
    """Test scrape endpoint with all parameters"""
    response = client.get("/scrape?device_name=pacemaker&product_code=DXT&min_year=2021")
    
    assert response.status_code == 200
    data = response.json()
    assert data["search_params"]["device_name"] == "pacemaker"
    assert data["search_params"]["product_code"] == "DXT"
    assert data["search_params"]["min_year"] == 2021

def test_scrape_endpoint_invalid_year():
    """Test scrape endpoint with invalid year"""
    response = client.get("/scrape?device_name=syringe&min_year=1900")
    assert response.status_code == 422  # Validation error

if __name__ == "__main__":
    # Run basic tests
    print("Running basic API tests...")
    
    print("Testing root endpoint...")
    test_root_endpoint()
    print("✓ Root endpoint works")
    
    print("Testing health endpoint...")
    test_health_endpoint()
    print("✓ Health endpoint works")
    
    print("Testing validation...")
    test_scrape_endpoint_missing_device_name()
    print("✓ Validation works")
    
    test_scrape_endpoint_invalid_year()
    print("✓ Year validation works")
    
    print("\nAll basic tests passed!")
    print("Note: Run full scraping tests with: python -m pytest test_api.py -v")
