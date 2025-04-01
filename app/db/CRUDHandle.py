from sqlalchemy.orm import Session

from app.db.models import Event, Subscriptions


class EventCrudHandler:
    def __init__(self, db_session: Session):
        self.db = db_session

    def store_event_mysql(self, data: Event):
        """Store event data into MySQL using singleton DB instance."""
        try:
            self.db.add(data)
            self.db.commit()
        except Exception as e:
            raise e

    def get_subscriptions(self):
        try:
            subscriptions = self.db.query(Subscriptions.guid).filter_by(active=True).all()
            return [subscription.guid for subscription in subscriptions]
        except Exception as e:
            raise e

    def add_subscription(self, subscription: Subscriptions):
        try:
            self.db.add(subscription)
            self.db.commit()
        except Exception as e:
            raise e
