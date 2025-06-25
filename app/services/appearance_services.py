from app.crud.appearance_operations import insert_appearance_events, get_all_appearance_events
from app.models.appearance_models import AppearanceRequest
from datetime import datetime

def store_appearances_data(request: AppearanceRequest):
    insert_appearance_events(request.results)
    return {"inserted": len(request.results)}

def get_appearances_data(start_date: datetime = None, end_date: datetime = None, personIdOnly: bool = False):
    return get_all_appearance_events(start_date, end_date, personIdOnly)
