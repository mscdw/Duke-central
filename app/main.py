import logging
from fastapi import FastAPI

logger = logging.getLogger("central-base")

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
    return "Welcome to Duke central Anaytics API"
