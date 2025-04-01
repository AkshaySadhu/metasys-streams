from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import config


class Database:
    """Singleton Database Connection"""
    _instance = None  # Static variable to hold the single instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)

            # Create the engine and session only once
            cls._instance.engine = create_engine(config.MYSQL_URL)
            cls._instance.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=cls._instance.engine
            )

        return cls._instance


# Create a global database instance
db_instance = Database()
