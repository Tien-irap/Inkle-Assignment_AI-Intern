from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
from app.core.logger import logs
import logging

class AsyncDBConnection:
    """
    Manages the asynchronous connection to the MongoDB database.
    Only used when STORAGE_MODE=mongodb
    """
    _client: AsyncIOMotorClient | None = None

    def __init__(self):
        if settings.STORAGE_MODE == "mongodb":
            if AsyncDBConnection._client is None:
                # Motor client is non-blocking
                AsyncDBConnection._client = AsyncIOMotorClient(settings.MONGO_URI)
                logs.log(logging.INFO, "MongoDB connection initialized")
        else:
            logs.log(logging.INFO, "Using local file storage - MongoDB not initialized")

    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Returns the async database instance.
        Only available when STORAGE_MODE=mongodb
        """
        if settings.STORAGE_MODE != "mongodb":
            raise RuntimeError("MongoDB not available - STORAGE_MODE is set to 'local'")
        
        if AsyncDBConnection._client is None:
            self.__init__()
        
        client = AsyncDBConnection._client
        return client[settings.MONGO_DB_NAME]

# Instantiate the connection manager
db_connection = AsyncDBConnection()

# Dependency for FastAPI
async def get_db() -> AsyncIOMotorDatabase:
    if settings.STORAGE_MODE != "mongodb":
        raise RuntimeError("MongoDB not available - using local storage")
    return db_connection.get_database()