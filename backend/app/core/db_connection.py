from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

class AsyncDBConnection:
    """
    Manages the asynchronous connection to the MongoDB database.
    """
    _client: AsyncIOMotorClient | None = None

    def __init__(self):
        if AsyncDBConnection._client is None:
            # Motor client is non-blocking
            AsyncDBConnection._client = AsyncIOMotorClient(settings.MONGO_URI)

    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Returns the async database instance.
        """
        if AsyncDBConnection._client is None:
            self.__init__()
        
        client = AsyncDBConnection._client
        return client[settings.MONGO_DB_NAME]

# Instantiate the connection manager
db_connection = AsyncDBConnection()

# Dependency for FastAPI
async def get_db() -> AsyncIOMotorDatabase:
    return db_connection.get_database()