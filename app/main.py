# Duke-central/app/main.py

from fastapi import FastAPI

# === CHANGE 1: Give each router a unique name upon import ===
from app.api.appearance_router import router as appearance_router
from app.api.anomaly_endpoints import router as anomaly_endpoints_router 
# --- ADDED: Import the new visualization router ---
from app.api.visualization_endpoints import router as visualization_endpoints_router
# =============================================================
from app.api.event_router import router as event_router
from app.api.user_router import router as user_router


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

# === CHANGE 2: Use the unique router names here ===
# Existing routers
app.include_router(appearance_router, tags=["Appearances"])
app.include_router(anomaly_endpoints_router, tags=["Anomalies"])

# --- ADDED: Include the new visualization router ---
# This makes the /get-visualization endpoint live.
# The 'tags' argument groups it nicely in the API documentation.
app.include_router(visualization_endpoints_router, tags=["Visualizations"])
# =================================================

# --- ADDED: Include the new event router ---
# This makes the /store-events endpoint live.
app.include_router(event_router, tags=["Events"])

# --- ADDED: Include the new user router ---
# This makes the / endpoint live.
app.include_router(user_router, tags=["Users"])