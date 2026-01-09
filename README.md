# Sam Keep-Alive Service

Prevents cold starts by pinging RunPod serverless endpoint every 4 minutes.

## Deploy to Render.com (Free)

1. Push this folder to GitHub
2. Go to https://render.com
3. New → Background Worker
4. Connect your GitHub repo
5. Set environment variables:
   - `RUNPOD_API_KEY`: Your RunPod API key
   - `RUNPOD_ENDPOINT_ID`: mn17kw1071462p
   - `PING_INTERVAL`: 240 (seconds)

## Cost

- Render.com free tier: $0/month
- RunPod ping cost: ~$4.32/month
  - 1 ping every 4 min = 15 pings/hour = 360 pings/day = 10,800 pings/month
  - Each ping uses ~1 second of A100 time
  - 10,800 seconds = 3 hours @ $1.44/hr = ~$4.32/month

## How It Works

1. Service runs 24/7 on Render free tier
2. Every 4 minutes, sends minimal request to Sam endpoint
3. Keeps at least 1 worker warm and ready
4. Cold starts avoided = instant responses for users

## Local Testing

```bash
export RUNPOD_API_KEY="your-key"
export RUNPOD_ENDPOINT_ID="mn17kw1071462p"
python keep_alive.py
```
