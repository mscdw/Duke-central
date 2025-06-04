import logging
import json
from fastapi import APIRouter
from fastapi.responses import  Response
from app.models.appearance_models import AppearanceRequest, AppearanceEvent
from app.services.appearance_services import store_appearances_data, get_appearances_data

router = APIRouter()
logger = logging.getLogger("appearance-endpoints")

@router.post("/store-appearances", response_class=Response)
def store_appearances(request: AppearanceRequest):
    resp = store_appearances_data(request)
    if resp:
        return Response(content=json.dumps(resp), status_code=200, media_type="application/json")
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/get-appearances", response_model=list[AppearanceEvent])
def get_appearances():
    appearances = get_appearances_data()
    if appearances:
        return [AppearanceEvent(**a) for a in appearances]
    else:
        return []
