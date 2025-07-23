from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None

    def get_client(self) -> AsyncIOMotorClient:
        return self.client

    def get_database(self):
        return self.database

db = Database()

async def connect_to_mongo():
    """Create database connection"""
    try:
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            server_api=ServerApi('1'),
            maxPoolSize=10,
            minPoolSize=10,
        )
        
        # Test connection
        await db.client.admin.command('ping')
        
        db.database = db.client[settings.DATABASE_NAME]
        
        logger.info(f"Connected to MongoDB at {settings.MONGODB_URL}")
        logger.info(f"Using database: {settings.DATABASE_NAME}")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    try:
        if db.client:
            db.client.close()
            logger.info("Disconnected from MongoDB")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")

async def create_indexes():
    """Create database indexes for optimal performance"""
    try:
        # Users collection indexes
        await db.database.users.create_index("email", unique=True)
        await db.database.users.create_index("username", unique=True)
        await db.database.users.create_index("google_id")
        
        # Environments collection indexes
        await db.database.environments.create_index("user_id")
        await db.database.environments.create_index([("user_id", 1), ("status", 1)])
        await db.database.environments.create_index("created_at")
        
        # Sessions collection indexes
        await db.database.sessions.create_index("user_id")
        await db.database.sessions.create_index("environment_id")
        await db.database.sessions.create_index("expires_at", expireAfterSeconds=0)
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

def get_database():
    """Dependency to get database instance"""
    return db.database