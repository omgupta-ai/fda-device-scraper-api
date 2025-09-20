# FDA Device Problem Extraction API

> FastAPI web service that extracts device and patient problems from the FDA TPLC database with MAUDE adverse event links.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API
python main.py

# Test at http://localhost:8000/docs
```

## 📋 API Usage

**Endpoint:** `GET /scrape`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `device_name` | ✅ | Device to search for |
| `product_code` | ❌ | FDA product code filter |
| `min_year` | ❌ | Minimum report year (default: 2020) |

**Example:**
```
GET /scrape?device_name=syringe&min_year=2020
```

## 🏗️ Tech Stack

- **FastAPI** - Web framework
- **Selenium** - Web scraping 
- **BeautifulSoup** - HTML parsing
- **ChromeDriver** - Browser automation

## 📦 Project Structure

```
├── main.py          # FastAPI application
├── scraper.py       # Web scraping logic
├── parser.py        # Data processing
├── requirements.txt # Dependencies
└── README.md        # Documentation
```

## 🔧 Setup

1. **Clone the repository**
2. **Create virtual environment:** `python -m venv fda_env`
3. **Activate environment:** `source fda_env/bin/activate`
4. **Install dependencies:** `pip install -r requirements.txt`
5. **Install ChromeDriver:** `pip install webdriver-manager`
6. **Run application:** `python main.py`

## 🧪 Testing

- **Swagger UI:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Sample Test:** Try `device_name=syringe`

## 📊 Sample Response

```json
{
  "search_params": {
    "device_name": "syringe",
    "min_year": 2020
  },
  "total_devices_found": 2,
  "devices": [
    {
      "device_name": "Auto-Disable Syringe",
      "device_problems": [
        {
          "problem_name": "Device Malfunction", 
          "count": 45,
          "maude_link": "https://www.accessdata.fda.gov/..."
        }
      ],
      "patient_problems": [...]
    }
  ]
}
```

## ⚠️ Notes

- First run downloads ChromeDriver automatically
- Each search takes 30-60 seconds (real FDA website scraping)
- Handles edge cases gracefully (no results, timeouts, etc.)

---

*Built for FDA device safety research and regulatory compliance.*
