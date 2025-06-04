from app.db.mongodb import db

def insert_appearance_events(events: list):
    if events:
        db.appearances.insert_many([event.dict() for event in events])
