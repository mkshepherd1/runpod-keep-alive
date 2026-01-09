"""
Multi-Endpoint Keep-Alive Service
Pings multiple RunPod serverless endpoints every 4 minutes to prevent cold starts.
Deploy to Render.com free tier.
"""

import os
import time
import logging
from datetime import datetime
import requests

# Configuration
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
PING_INTERVAL = int(os.environ.get("PING_INTERVAL", "3000"))  # 50 minutes (idle timeout is 1 hour)

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

def ping_endpoint(endpoint_id, endpoint_name):
    """Send minimal request to keep worker warm."""
    url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }

    # Minimal request - just 1 token to keep warm
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
            status = data.get("status", "unknown")
            logger.info(f"  [{endpoint_name}] Ping OK - Status: {status}")
            return True
        else:
            logger.warning(f"  [{endpoint_name}] Ping returned {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        logger.warning(f"  [{endpoint_name}] Ping timed out (model may be loading)")
        return False
    except Exception as e:
        logger.error(f"  [{endpoint_name}] Ping failed: {e}")
        return False

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
        initializing = workers.get("initializing", 0)

        logger.info(f"  [{endpoint_name}] ready={ready}, idle={idle}, init={initializing}")
        return ready > 0 or idle > 0

    except Exception as e:
        logger.error(f"  [{endpoint_name}] Health check failed: {e}")
        return False

def main():
    """Main keep-alive loop."""
    logger.info("=" * 60)
    logger.info("Multi-Endpoint Keep-Alive Service Started")
    logger.info(f"Endpoints: {len(ENDPOINTS)}")
    for ep in ENDPOINTS:
        logger.info(f"  - {ep['name']} ({ep['id']})")
    logger.info(f"Ping interval: {PING_INTERVAL} seconds")
    logger.info("=" * 60)

    if not RUNPOD_API_KEY:
        logger.error("RUNPOD_API_KEY not set!")
        return

    ping_count = 0

    while True:
        ping_count += 1
        logger.info(f"\n--- Ping #{ping_count} at {datetime.now().isoformat()} ---")

        for endpoint in ENDPOINTS:
            ep_id = endpoint["id"]
            ep_name = endpoint["name"]

            # Check health first
            is_healthy = check_health(ep_id, ep_name)

            if is_healthy:
                # Send keep-alive ping
                ping_endpoint(ep_id, ep_name)
            else:
                logger.info(f"  [{ep_name}] No ready workers, skipping ping")

        # Wait for next ping
        logger.info(f"\nSleeping {PING_INTERVAL} seconds until next ping...")
        time.sleep(PING_INTERVAL)

if __name__ == "__main__":
    main()
