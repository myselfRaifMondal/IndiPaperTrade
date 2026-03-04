# News API Documentation

Flask-based REST API for real-time Indian financial markets news aggregation.

## Overview

The News API aggregates RSS feeds from 8 major Indian financial sources and provides:
- Real-time news updates (30-second polling)
- Automatic deduplication
- Caching for performance
- RESTful JSON endpoints
- Web-based dashboard

## Architecture

```
api/
├── app.py              # Flask application and routes
├── news_service.py     # Business logic, caching, RSS fetching
└── __init__.py         # Package initialization

templates/
└── dashboard.html      # Web-based news dashboard

run_news_api.py         # Server startup script
```

## News Sources

1. **NSE Announcements** - Corporate announcements from NSE
2. **NSE Circulars** - Regulatory circulars from NSE
3. **BSE Announcements** - Corporate filings from BSE
4. **RBI Press Releases** - Reserve Bank of India updates
5. **SEBI** - Securities and Exchange Board updates
6. **MoneyControl** - Top financial news
7. **Economic Times Markets** - Market news and analysis
8. **Live Mint Markets** - Business and market updates

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Verify Flask is installed:**
```bash
python -c "import flask; print(f'Flask {flask.__version__}')"
```

## Running the Server

### Quick Start

```bash
python run_news_api.py
```

Server will start on `http://localhost:5000`

### Custom Port

```bash
NEWS_API_PORT=8080 python run_news_api.py
```

### Development Mode

```bash
FLASK_ENV=development python run_news_api.py
```

## API Endpoints

### 1. Get Latest News

**Endpoint:** `GET /api/news`

**Description:** Fetch latest news from all sources

**Response:**
```json
{
  "news": [
    {
      "id": "abc123...",
      "title": "Stock Market Update",
      "source": "NSE Announcements",
      "url": "https://...",
      "published": "Mon, 04 Mar 2026 14:30:00 GMT",
      "summary": "Brief description..."
    }
  ],
  "count": 50,
  "last_updated": "2026-03-04T14:30:15"
}
```

**Parameters:**
- `count` (optional): Number of items to return (default: all cached)
  - Example: `/api/news?count=20`

### 2. List News Sources

**Endpoint:** `GET /api/news/sources`

**Description:** Get list of configured RSS feed sources

**Response:**
```json
{
  "sources": [
    "NSE Announcements",
    "NSE Circulars",
    "BSE Announcements",
    "RBI Press Releases",
    "SEBI",
    "MoneyControl",
    "Economic Times",
    "Live Mint"
  ],
  "count": 8
}
```

### 3. Service Status

**Endpoint:** `GET /api/news/status`

**Description:** Get service health and statistics

**Response:**
```json
{
  "is_running": true,
  "cached_items": 97,
  "last_update": "2026-03-04T14:30:15",
  "total_fetches": 45,
  "failed_fetches": 2,
  "update_interval": 30,
  "sources_count": 8
}
```

### 4. Force Refresh

**Endpoint:** `POST /api/news/refresh`

**Description:** Trigger immediate news update (bypasses 30-second interval)

**Response:**
```json
{
  "message": "News refresh triggered",
  "status": "success"
}
```

### 5. Web Dashboard

**Endpoint:** `GET /`

**Description:** Opens web-based news dashboard with:
- Auto-refreshing news (every 30 seconds)
- Click-to-open articles
- Real-time status indicators
- Smooth scrolling interface

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEWS_API_PORT` | `5000` | Server port |
| `FLASK_ENV` | `production` | Environment (`development` or `production`) |
| `NEWS_UPDATE_INTERVAL` | `30` | Seconds between RSS feed updates |
| `NEWS_MAX_ITEMS` | `100` | Maximum cached news items |

### Example Configuration

```bash
# .env file
NEWS_API_PORT=5000
FLASK_ENV=development
NEWS_UPDATE_INTERVAL=30
NEWS_MAX_ITEMS=100
```

## Usage Examples

### cURL Examples

**Get latest 10 news items:**
```bash
curl http://localhost:5000/api/news?count=10
```

**Get all sources:**
```bash
curl http://localhost:5000/api/news/sources
```

**Check service status:**
```bash
curl http://localhost:5000/api/news/status
```

**Force refresh:**
```bash
curl -X POST http://localhost:5000/api/news/refresh
```

### Python Client Example

```python
import requests

# Fetch news
response = requests.get('http://localhost:5000/api/news', params={'count': 20})
data = response.json()

for item in data['news']:
    print(f"{item['source']}: {item['title']}")
    print(f"  URL: {item['url']}")
    print(f"  Published: {item['published']}\n")
```

### JavaScript Client Example

```javascript
// Fetch and display news
async function getNews() {
    const response = await fetch('http://localhost:5000/api/news?count=20');
    const data = await response.json();
    
    data.news.forEach(item => {
        console.log(`${item.source}: ${item.title}`);
        console.log(`  ${item.url}`);
    });
}

// Auto-refresh every 30 seconds
setInterval(getNews, 30000);
```

## Features

### Deduplication

News items are automatically deduplicated based on:
- Title + URL hash (MD5)
- Prevents duplicate articles from appearing
- Works across all sources

### Caching

- In-memory cache (OrderedDict)
- Thread-safe operations with Lock
- Stores up to 100 items (configurable)
- Sorted by publication time (newest first)

### Error Handling

- Graceful degradation on feed failures
- Timeout protection (15 seconds per feed)
- Logs errors without crashing
- Continues with available data

### Performance

- Background thread for updates (non-blocking)
- 30-second update interval (configurable)
- Concurrent-ready (can parallelize feed fetching)
- Efficient memory usage with caching limits

## Integration

### With PyQt6 Terminal

The Flask API can run alongside the existing PyQt6 trading terminal:

```python
# Start both services
from threading import Thread

# Start Flask API in background
api_thread = Thread(target=start_api_server, daemon=True)
api_thread.start()

# Start PyQt6 terminal
start_trading_terminal()
```

### With Streamlit Dashboard

Embed the API in a Streamlit dashboard:

```python
import streamlit as st
import requests

st.title("Market News")

response = requests.get('http://localhost:5000/api/news', params={'count': 10})
news = response.json()['news']

for item in news:
    st.markdown(f"**{item['source']}**: [{item['title']}]({item['url']})")
    st.caption(item['published'])
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or use a different port
NEWS_API_PORT=8080 python run_news_api.py
```

### No News Loading

1. Check service status: `curl http://localhost:5000/api/news/status`
2. View logs for errors
3. Verify internet connectivity
4. Check if RSS feeds are accessible

### CORS Issues

If accessing from a different domain:
- CORS is pre-configured in `app.py`
- Allows all origins by default
- Modify `CORS(app, resources={...})` for restrictions

### Slow Performance

- Reduce `NEWS_MAX_ITEMS` if memory is constrained
- Increase `NEWS_UPDATE_INTERVAL` to reduce API calls
- Consider caching at reverse proxy level

## Development

### Running Tests

```bash
# Test single feed
python -c "from api.news_service import NewsService; ns = NewsService(); ns.update_cache(); print(len(ns.get_latest_news()))"

# Test API endpoint
curl http://localhost:5000/api/news | python -m json.tool
```

### Adding New Sources

Edit `api/news_service.py`:

```python
FEEDS = {
    # ... existing feeds ...
    "New Source": "https://example.com/rss.xml",
}
```

### Logging

Logs are written to console. Configure in `app.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5000 'api:create_app()'
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "run_news_api.py"]
```

### Systemd Service

```ini
[Unit]
Description=IndiPaperTrade News API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/IndiPaperTrade
ExecStart=/usr/bin/python3 run_news_api.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Security Considerations

- No authentication required (public API)
- Rate limiting not implemented (add if needed)
- HTTPS recommended for production
- Sanitize HTML content (already implemented)
- No user data stored

## License

Part of IndiPaperTrade project.

## Support

For issues or questions, refer to the main project documentation.
