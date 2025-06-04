from app.crud.appearance_operations import insert_appearance_events
from app.models.appearance_models import AppearanceRequest

def store_appearances_data(request: AppearanceRequest):
    insert_appearance_events(request.results)
    return {"inserted": len(request.results)}
