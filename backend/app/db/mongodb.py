"""MongoDB Atlas connection and database operations."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def get_database() -> AsyncIOMotorDatabase:
    """Get the MongoDB database instance."""
    global _client, _db
    
    if _db is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongodb_uri)
        _db = _client[settings.mongodb_database]
        
        # Ensure indexes
        await _ensure_indexes(_db)
    
    return _db


async def _ensure_indexes(db: AsyncIOMotorDatabase):
    """Create necessary indexes for performance."""
    # Atomic units - query by version
    await db.atomic_units.create_index("version")
    await db.atomic_units.create_index([("version", 1), ("id", 1)], unique=True)
    await db.atomic_units.create_index("section")
    
    # Master versions - query by ID
    await db.master_versions.create_index("master_version_id", unique=True)
    await db.master_versions.create_index("created_at")
    
    # Parsed JDs
    await db.parsed_jds.create_index("jd_id", unique=True)
    await db.parsed_jds.create_index("created_at")
    
    # Compiles
    await db.compiles.create_index("compile_id", unique=True)
    await db.compiles.create_index("created_at")


async def close_database():
    """Close the database connection."""
    global _client, _db
    
    if _client is not None:
        _client.close()
        _client = None
        _db = None
