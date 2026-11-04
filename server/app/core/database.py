from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None


mongo = MongoDB()


async def connect_to_mongo():
    mongo.client = AsyncIOMotorClient(settings.MONGODB_URL)


async def close_mongo_connection():
    if mongo.client:
        mongo.client.close()


def get_database():
    return mongo.client[settings.MONGODB_DB]
