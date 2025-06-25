from fastapi import FastAPI
from app.api.appearance_router import router
from app.core.logging import get_logger

logger = get_logger("central-base")

app = FastAPI(
    title="Central analytics app",
    description="FastAPI application for interacting with site events data and doing analytics.",
    version="1.0.0",
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

@app.get("/")
def index():
    return "Welcome to Duke central Analytics API"

app.include_router(router)