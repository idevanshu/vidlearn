import os
import json
try:
    import redis
except ImportError:
    redis = None

REDIS_URL = os.getenv("REDIS_URL")
if redis and REDIS_URL:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
else:
    redis_client = None

# For local fallback
progress_data = {"step": "Not started", "message": ""}

def set_progress(progress_info, user_id="global"):
    data = json.dumps(progress_info)
    if redis_client:
        redis_client.set(f"progress:{user_id}", data)
    else:
        global progress_data
        progress_data = progress_info

def get_progress(user_id="global"):
    if redis_client:
        data = redis_client.get(f"progress:{user_id}")
        if data:
            return json.loads(data)
        else:
            return {"step": "Not started", "message": ""}
    else:
        global progress_data
        return progress_data
