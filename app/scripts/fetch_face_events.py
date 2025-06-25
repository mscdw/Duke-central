import asyncio
from datetime import datetime, timedelta
from app.core.logging import get_logger
from app.core.config import get_settings
from app.services.appearance_services import store_appearances_data
from app.models.appearance_models import AppearanceRequest
import httpx

logger = get_logger("face-events-script")
settings = get_settings()
verify_ssl = settings.VERIFY_SSL
fetch_url = f"http://localhost:8000/api/all-face-events-fetch"
post_url = f"http://10.89.26.170:8001/store-appearances"

START_DATE = "2025-06-02"
END_DATE = "2025-06-10"

def main():
    async def fetch_logic():
        current = datetime.strptime(START_DATE, "%Y-%m-%d")
        end = datetime.strptime(END_DATE, "%Y-%m-%d")
        while current <= end:
            from_time = current.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
            to_time = current.replace(hour=23, minute=59, second=59, microsecond=999).isoformat() + 'Z'
            try:
                logger.info(f"Fetching face events from {from_time} to {to_time}...")
                async with httpx.AsyncClient(verify=verify_ssl, timeout=600.0) as client:
                    response = await client.get(fetch_url, params={"from_time": from_time, "to_time": to_time})
                    if response.status_code != 200:
                        logger.error(f"HTTP {response.status_code} for {from_time}: {response.text}")
                        current += timedelta(days=1)
                        continue
                    payload = response.json()
                if not payload or not payload.get('results'):
                    logger.warning(f"No face events found for {from_time} to {to_time}.")
                else:
                    logger.info(f"Fetched {payload['total_length']} face events for {from_time} to {to_time}")
                    appearance_request = AppearanceRequest(**payload)
                    store_appearances_data(appearance_request)
                    logger.info(f"Stored {payload['total_length']} face events using service.")
                    async with httpx.AsyncClient(verify=verify_ssl, timeout=120.0) as client:
                        post_response = await client.post(post_url, json=payload)
                        logger.info(f"Posted data to {post_url}: {post_response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching face events for {from_time}: {e}")
            current += timedelta(days=1)
    asyncio.run(fetch_logic())

if __name__ == "__main__":
    main()
