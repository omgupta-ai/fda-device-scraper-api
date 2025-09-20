"""
FDA Device Scraper Module
Handles web scraping of FDA TPLC database using Selenium.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time


logger = logging.getLogger(__name__)

class FDADeviceScraper:
    """Scraper for FDA TPLC database"""
    
    def __init__(self):
        self.base_url = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfTPLC/tplc.cfm"
        self.driver = None
        
    def _setup_driver(self):
        """Initialize Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        chrome_service = webdriver.chrome.service.Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        self.driver.implicitly_wait(10)
        
    def _cleanup_driver(self):
        """Clean up WebDriver resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            
    async def search_devices(self, device_name: str, product_code: Optional[str] = None, min_year: int = 2020) -> List[str]:
        """
        Search for devices in FDA TPLC database and return list of device detail page URLs.
        
        Args:
            device_name: Name of device to search for
            product_code: Optional product code filter
            min_year: Minimum year for reports
            
        Returns:
            List of URLs to device detail pages
        """
        
        try:
            self._setup_driver()
            
            logger.info(f"Navigating to FDA TPLC search page")
            self.driver.get(self.base_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            # Find and fill the search form
            logger.info(f"Filling search form with device_name: {device_name}")
            
            # Look for device name input field (may have different names/IDs)
            device_input = None
            possible_selectors = [
                "input[name*='device']",
                "input[name*='Device']", 
                "input[id*='device']",
                "input[placeholder*='device']",
                "input[placeholder*='Device']"
            ]
            
            for selector in possible_selectors:
                try:
                    device_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
                    
            if not device_input:
                # Fallback: try to find any text input
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    if inp.get_attribute("type") in ["text", "search", None]:
                        device_input = inp
                        break
            
            if device_input:
                device_input.clear()
                device_input.send_keys(device_name)
                logger.info("Device name entered successfully")
            else:
                raise Exception("Could not find device name input field")
            
            # Set minimum year if there's a year selector
            try:
                year_select = Select(self.driver.find_element(By.NAME, "min_report_year"))
                year_select.select_by_value(str(min_year))
                logger.info(f"Min year set to {min_year}")
            except NoSuchElementException:
                logger.warning("Year selector not found, continuing without year filter")
            
            # Add product code if provided
            if product_code:
                try:
                    product_input = self.driver.find_element(By.NAME, "productcode")
                    product_input.clear()
                    product_input.send_keys(product_code)
                    logger.info(f"Product code {product_code} entered")
                except NoSuchElementException:
                    logger.warning("Product code field not found")
            
            # Submit the form
            submit_button = None
            try:
                # Try different submit button possibilities
                submit_selectors = [
                    "input[type='submit']",
                    "button[type='submit']",
                    "input[value*='Search']",
                    "button:contains('Search')"
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        break
                    except NoSuchElementException:
                        continue
                        
                if submit_button:
                    submit_button.click()
                    logger.info("Search form submitted")
                else:
                    # Fallback: submit the form directly
                    form = self.driver.find_element(By.TAG_NAME, "form")
                    form.submit()
                    logger.info("Form submitted directly")
                    
            except Exception as e:
                logger.error(f"Error submitting form: {e}")
                raise
            
            # Wait for results page to load
            time.sleep(3)
            
            # Extract device detail page links
            device_links = self._extract_device_links()
            
            logger.info(f"Found {len(device_links)} device links")
            return device_links
            
        except Exception as e:
            logger.error(f"Error during device search: {e}")
            raise
        finally:
            self._cleanup_driver()
    
    def _extract_device_links(self) -> List[str]:
        """Extract device detail page links from search results"""
        
        device_links = []
        
        try:
            # Wait a bit for results to load
            time.sleep(2)
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for links that go to device detail pages
            # These typically have patterns like "tplc.cfm?id=XXXX" or similar
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                
                # Check if this looks like a device detail page link
                if 'tplc.cfm' in href and ('id=' in href or 'ID=' in href):
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        full_url = "https://www.accessdata.fda.gov" + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfTPLC/" + href
                    
                    device_links.append(full_url)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_links = []
            for link in device_links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)
            
            return unique_links
            
        except Exception as e:
            logger.error(f"Error extracting device links: {e}")
            return []
    
    async def scrape_device_details(self, device_url: str) -> Dict[str, Any]:
        """
        Scrape details from a specific device page.
        
        Args:
            device_url: URL of the device detail page
            
        Returns:
            Dictionary with raw scraped data
        """
        
        try:
            self._setup_driver()
            
            logger.info(f"Scraping device details from: {device_url}")
            self.driver.get(device_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(2)  # Additional wait for dynamic content
            
            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract device information
            device_data = {
                'url': device_url,
                'device_name': self._extract_device_name(soup),
                'device_problems': self._extract_device_problems(soup),
                'patient_problems': self._extract_patient_problems(soup),
                'raw_html': str(soup)  # Keep for debugging
            }
            
            return device_data
            
        except Exception as e:
            logger.error(f"Error scraping device details from {device_url}: {e}")
            raise
        finally:
            self._cleanup_driver()
    
    def _extract_device_name(self, soup: BeautifulSoup) -> str:
        """Extract device name from the page"""
        
        # Try various selectors for device name
        selectors_to_try = [
            'h1',
            'h2', 
            '.device-name',
            '#device-name',
            'td:contains("Device Name")',
            'strong:contains("Device")'
        ]
        
        for selector in selectors_to_try:
            try:
                if ':contains(' in selector:
                    # Handle contains selector differently
                    elements = soup.find_all(text=re.compile(r'Device.*Name', re.I))
                    if elements:
                        parent = elements[0].parent
                        if parent and parent.next_sibling:
                            return str(parent.next_sibling).strip()
                else:
                    element = soup.select_one(selector)
                    if element and element.text.strip():
                        return element.text.strip()
            except:
                continue
        
        return "Unknown Device"
    
    def _extract_device_problems(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract device problems from the page"""
        
        problems = []
        
        try:
            # Look for sections containing "Device Problem" or similar
            tables = soup.find_all('table')
            
            for table in tables:
                # Check if this table contains device problems
                headers = [th.get_text().strip().lower() for th in table.find_all(['th', 'td']) if th.get_text().strip()]
                
                if any('device' in h and 'problem' in h for h in headers):
                    problems.extend(self._parse_problem_table(table, 'device'))
            
            # Also look for links that contain device problem information
            links = soup.find_all('a', href=True)
            for link in links:
                if 'maude' in link['href'].lower() and 'device' in link.get_text().lower():
                    problem_data = self._extract_problem_from_link(link)
                    if problem_data:
                        problems.append(problem_data)
        
        except Exception as e:
            logger.error(f"Error extracting device problems: {e}")
        
        return problems
    
    def _extract_patient_problems(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract patient problems from the page"""
        
        problems = []
        
        try:
            # Look for sections containing "Patient Problem" or similar
            tables = soup.find_all('table')
            
            for table in tables:
                headers = [th.get_text().strip().lower() for th in table.find_all(['th', 'td']) if th.get_text().strip()]
                
                if any('patient' in h and 'problem' in h for h in headers):
                    problems.extend(self._parse_problem_table(table, 'patient'))
            
            # Also look for links
            links = soup.find_all('a', href=True)
            for link in links:
                if 'maude' in link['href'].lower() and 'patient' in link.get_text().lower():
                    problem_data = self._extract_problem_from_link(link)
                    if problem_data:
                        problems.append(problem_data)
        
        except Exception as e:
            logger.error(f"Error extracting patient problems: {e}")
        
        return problems
    
    def _parse_problem_table(self, table, problem_type: str) -> List[Dict[str, Any]]:
        """Parse a table containing problem data"""
        
        problems = []
        
        try:
            rows = table.find_all('tr')
            
            for row in rows[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 2:
                    problem_name = cells[0].get_text().strip()
                    count_text = cells[1].get_text().strip() if len(cells) > 1 else "0"
                    
                    # Extract count (look for numbers)
                    count_match = re.search(r'\d+', count_text)
                    count = int(count_match.group()) if count_match else 0
                    
                    # Look for MAUDE link in this row
                    maude_link = ""
                    for cell in cells:
                        link = cell.find('a', href=True)
                        if link and 'maude' in link['href'].lower():
                            maude_link = self._make_absolute_url(link['href'])
                            break
                    
                    if problem_name and problem_name.lower() not in ['problem', 'count', 'total']:
                        problems.append({
                            'problem_name': problem_name,
                            'count': count,
                            'maude_link': maude_link,
                            'type': problem_type
                        })
        
        except Exception as e:
            logger.error(f"Error parsing problem table: {e}")
        
        return problems
    
    def _extract_problem_from_link(self, link) -> Optional[Dict[str, Any]]:
        """Extract problem information from a MAUDE link"""
        
        try:
            problem_name = link.get_text().strip()
            maude_url = self._make_absolute_url(link['href'])
            
            # Try to extract count from link text or nearby elements
            count = 0
            parent = link.parent
            if parent:
                text = parent.get_text()
                count_match = re.search(r'(\d+)', text)
                if count_match:
                    count = int(count_match.group(1))
            
            return {
                'problem_name': problem_name,
                'count': count,
                'maude_link': maude_url,
                'type': 'unknown'
            }
        
        except Exception as e:
            logger.error(f"Error extracting problem from link: {e}")
            return None
    
    def _make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute URL"""
        
        if url.startswith('http'):
            return url
        elif url.startswith('/'):
            return "https://www.accessdata.fda.gov" + url
        else:
            return "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/" + url