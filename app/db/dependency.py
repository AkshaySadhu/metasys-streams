from contextlib import contextmanager

from app.db.databases import db_instance


class DBSession:

    @contextmanager
    def session_context(self):
        """Provides a database session context manager."""
        db = db_instance.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


db_session = DBSession()
