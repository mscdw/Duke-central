from app.db.mongodb import db
from datetime import datetime

def insert_appearance_events(events: list):
    if events:
        db.appearances.insert_many([event.dict() for event in events])

def get_all_appearance_events(start_date: datetime = None, end_date: datetime = None, personIdOnly: bool = False, personId: str = None):
    query = {}
    if start_date and end_date:
        query["eventStartTime"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["eventStartTime"] = {"$gte": start_date}
    elif end_date:
        query["eventStartTime"] = {"$lte": end_date}
    if personIdOnly:
        query["personId"] = {"$ne": None}
    if personId:
        query["personId"] = personId
    return list(db.appearances.find(query))
