"""
Flask News API Server for Indian Financial Markets
Provides real-time RSS news aggregation and API endpoints
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
import logging
from datetime import datetime
import os

# Import our RSS feed manager
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.news_service import NewsService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize news service
news_service = NewsService(
    update_interval=30,  # Update every 30 seconds
    max_items=100
)

@app.route('/')
def index():
    """Serve the dashboard homepage."""
    return render_template('dashboard.html')

@app.route('/api/news', methods=['GET'])
def get_news():
    """
    Get latest financial news from all RSS feeds.
    
    Returns:
        JSON response with news items
        
    Example response:
    {
        "news": [
            {
                "title": "Company X announces dividend",
                "source": "NSE Announcements",
                "published": "2026-03-04T14:30:00",
                "url": "https://...",
                "id": "unique_id"
            }
        ],
        "count": 50,
        "last_updated": "2026-03-04T14:30:15"
    }
    """
    try:
        news_items = news_service.get_latest_news()
        
        # Format response
        response = {
            "news": [
                {
                    "title": item.title,
                    "source": item.source,
                    "published": item.published,
                    "url": item.link,
                    "id": item.id,
                    "summary": item.summary if hasattr(item, 'summary') else ""
                }
                for item in news_items
            ],
            "count": len(news_items),
            "last_updated": news_service.last_update.isoformat() if news_service.last_update else None,
            "status": "success"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "news": []
        }), 500

@app.route('/api/news/sources', methods=['GET'])
def get_sources():
    """
    Get list of configured news sources.
    
    Returns:
        JSON with list of sources
    """
    try:
        sources = news_service.get_sources()
        return jsonify({
            "sources": sources,
            "count": len(sources),
            "status": "success"
        }), 200
    except Exception as e:
        logger.error(f"Error fetching sources: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/news/status', methods=['GET'])
def get_status():
    """
    Get news service status and health check.
    
    Returns:
        JSON with service status
    """
    try:
        status = news_service.get_status()
        return jsonify({
            "status": "success",
            "service_status": status,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/news/refresh', methods=['POST'])
def refresh_news():
    """
    Manually trigger news refresh.
    
    Returns:
        JSON with refresh status
    """
    try:
        news_service.force_refresh()
        return jsonify({
            "status": "success",
            "message": "News refresh triggered",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error refreshing news: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "status": "error",
        "message": "Endpoint not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500

def start_server(host='0.0.0.0', port=5000, debug=False):
    """
    Start the Flask news API server.
    
    Args:
        host: Server host (default: 0.0.0.0)
        port: Server port (default: 5000)
        debug: Enable debug mode (default: False)
    """
    logger.info(f"Starting News API server on {host}:{port}")
    
    # Start news service background updates
    news_service.start()
    
    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        logger.info("Shutting down News API server...")
        news_service.stop()
    except Exception as e:
        logger.error(f"Server error: {e}")
        news_service.stop()

if __name__ == '__main__':
    # Run server
    start_server(
        host='0.0.0.0',
        port=int(os.getenv('NEWS_API_PORT', 5000)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
