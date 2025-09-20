"""
FDA Device & Patient Problem Extraction API
FastAPI web service that scrapes FDA TPLC database for device problems.
"""

from fastapi import FastAPI, HTTPException, Query
from typing import Optional, Dict, List, Any
import logging
from scraper import FDADeviceScraper
from parser_1 import DeviceDataParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="FDA Device Problem Extraction API",
    description="Extract device and patient problems from FDA TPLC database",
    version="1.0.0"
)

# Initialize scraper and parser
scraper = FDADeviceScraper()
parser = DeviceDataParser()

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "FDA Device Problem Extraction API",
        "docs": "/docs",
        "endpoint": "/scrape"
    }

@app.get("/scrape")
async def scrape_device_problems(
    device_name: str = Query(..., description="Name of the device to search for"),
    product_code: Optional[str] = Query(None, description="Optional product code filter"),
    min_year: int = Query(2020, description="Minimum year for reports", ge=2000, le=2024)
) -> Dict[str, Any]:
    """
    Scrape FDA TPLC database for device and patient problems.
    
    Args:
        device_name: Name of the device to search for (required)
        product_code: Optional product code to filter results
        min_year: Minimum year for reports (default: 2020)
        
    Returns:
        JSON response with device problems and patient problems
    """
    
    try:
        logger.info(f"Starting scrape for device: {device_name}, product_code: {product_code}, min_year: {min_year}")
        
        # Step 1: Perform search and get device detail page links
        device_links = await scraper.search_devices(
            device_name=device_name,
            product_code=product_code,
            min_year=min_year
        )
        
        if not device_links:
            return {
                "search_params": {
                    "device_name": device_name,
                    "product_code": product_code,
                    "min_year": min_year
                },
                "message": "No devices found matching the search criteria",
                "devices": []
            }
        
        logger.info(f"Found {len(device_links)} device links to scrape")
        
        # Step 2: Extract data from each device detail page
        all_devices_data = []
        
        for device_link in device_links:
            try:
                # Scrape device detail page
                raw_device_data = await scraper.scrape_device_details(device_link)
                
                # Parse and structure the data
                parsed_device = parser.parse_device_data(raw_device_data)
                
                all_devices_data.append(parsed_device)
                
            except Exception as e:
                logger.error(f"Error processing device {device_link}: {str(e)}")
                # Continue with other devices even if one fails
                continue
        
        # Step 3: Return structured response
        response = {
            "search_params": {
                "device_name": device_name,
                "product_code": product_code,
                "min_year": min_year
            },
            "total_devices_found": len(all_devices_data),
            "devices": all_devices_data
        }
        
        logger.info(f"Successfully scraped {len(all_devices_data)} devices")
        return response
        
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error scraping FDA database: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "FDA Device Scraper"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)