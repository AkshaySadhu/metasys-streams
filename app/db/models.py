from sqlalchemy import Column, String, TIMESTAMP, BOOLEAN
from sqlalchemy.dialects.mysql import INTEGER, FLOAT

from app.db.base import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(INTEGER, primary_key=True, index=True, autoincrement=True)
    eventId = Column(String(255), unique=True)
    guid = Column(String(255))
    presentValue = Column(FLOAT)
    event_metadata = Column(String(255))
    stream_id = Column(String(255))
    timestamp = Column(TIMESTAMP)

    def __repr__(self):
        return f"<Event(event_id={self.event_id})>"


class Subscriptions(Base):
    __tablename__ = "subscriptions"
    id = Column(INTEGER, primary_key=True, index=True, autoincrement=True)
    guid = Column(String(255))
    active = Column(BOOLEAN)
