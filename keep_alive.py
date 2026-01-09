"""
Multi-Endpoint Keep-Alive Service
Pings multiple RunPod serverless endpoints to prevent cold starts.
Runs as a web service for Render.com free tier compatibility.
"""

import os
import time
import logging
import threading
from datetime import datetime
from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Configuration
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
PING_INTERVAL = int(os.environ.get("PING_INTERVAL", "3000"))  # 50 minutes
PORT = int(os.environ.get("PORT", "10000"))

# All endpoints to keep warm
ENDPOINTS = [
    {"id": "hk5uyae5jtmhmy", "name": "Sam (vLLM)"},
    {"id": "or07okhb435hr6", "name": "fast-worker"},
    {"id": "2ufs6kt7vd3r6v", "name": "quality-worker"},
]

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Track status
status = {"ping_count": 0, "last_ping": None, "results": {}}

def ping_endpoint(endpoint_id, endpoint_name):
    """Send minimal request to keep worker warm."""
    url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": {
            "prompt": "<s>[INST] Hi [/INST]",
            "max_tokens": 1,
            "temperature": 0.1
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        data = response.json()
        if response.status_code == 200:
            logger.info(f"  [{endpoint_name}] Ping OK - Status: {data.get('status', 'unknown')}")
            return "OK"
        else:
            logger.warning(f"  [{endpoint_name}] Ping returned {response.status_code}")
            return f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        logger.warning(f"  [{endpoint_name}] Ping timed out")
        return "TIMEOUT"
    except Exception as e:
        logger.error(f"  [{endpoint_name}] Ping failed: {e}")
        return f"ERROR: {e}"

def check_health(endpoint_id, endpoint_name):
    """Check endpoint health status."""
    url = f"https://api.runpod.ai/v2/{endpoint_id}/health"
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        workers = data.get("workers", {})
        ready = workers.get("ready", 0)
        idle = workers.get("idle", 0)
        init = workers.get("initializing", 0)
        logger.info(f"  [{endpoint_name}] ready={ready}, idle={idle}, init={init}")
        return ready > 0 or idle > 0
    except Exception as e:
        logger.error(f"  [{endpoint_name}] Health check failed: {e}")
        return False

def keep_alive_loop():
    """Background thread that pings endpoints."""
    global status
    logger.info("=" * 60)
    logger.info("Keep-Alive Background Thread Started")
    logger.info(f"Endpoints: {len(ENDPOINTS)}")
    logger.info(f"Ping interval: {PING_INTERVAL} seconds")
    logger.info("=" * 60)

    if not RUNPOD_API_KEY:
        logger.error("RUNPOD_API_KEY not set!")
        return

    while True:
        status["ping_count"] += 1
        status["last_ping"] = datetime.now().isoformat()
        logger.info(f"\n--- Ping #{status['ping_count']} at {status['last_ping']} ---")

        for endpoint in ENDPOINTS:
            ep_id = endpoint["id"]
            ep_name = endpoint["name"]
            is_healthy = check_health(ep_id, ep_name)

            if is_healthy:
                result = ping_endpoint(ep_id, ep_name)
            else:
                result = "SKIPPED (no workers)"
                logger.info(f"  [{ep_name}] No ready workers, skipping ping")

            status["results"][ep_name] = result

        logger.info(f"\nSleeping {PING_INTERVAL} seconds until next ping...")
        time.sleep(PING_INTERVAL)

@app.route("/")
def home():
    """Health check endpoint."""
    return jsonify({
        "status": "running",
        "service": "RunPod Keep-Alive",
        "ping_count": status["ping_count"],
        "last_ping": status["last_ping"],
        "endpoints": [ep["name"] for ep in ENDPOINTS],
        "results": status["results"]
    })

@app.route("/health")
def health():
    """Simple health check."""
    return "OK"

if __name__ == "__main__":
    # Start background thread
    thread = threading.Thread(target=keep_alive_loop, daemon=True)
    thread.start()

    # Start Flask server
    logger.info(f"Starting web server on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
