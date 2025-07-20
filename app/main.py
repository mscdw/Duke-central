from fastapi import FastAPI
from app.api.appearance_router import router as appearance_router
from app.api.event_router import router as event_router
from app.core.logging import get_logger
from app.db import connect_to_mongo, close_mongo_connection

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

@app.on_event("startup")
def startup_db_client():
    logger.info("Starting up and connecting to MongoDB.")
    connect_to_mongo()

@app.on_event("shutdown")
def shutdown_db_client():
    logger.info("Shutting down and closing MongoDB connection.")
    close_mongo_connection()

@app.get("/")
def index():
    return "Welcome to Duke central Analytics API"

# Add routers to the application
app.include_router(appearance_router, tags=["Appearances"])
app.include_router(event_router, tags=["Events"])