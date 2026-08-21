"""Database clients package: Supabase + Pinecone + Redis."""

from api.db.pinecone_client import PineconeIndexWrapper, get_pinecone_client
from api.db.redis_client import (
    CacheNamespace,
    cache_get,
    cache_set,
    get_redis_async,
    get_redis_sync,
)
from api.db.supabase_client import get_supabase_admin, get_supabase_anon

__all__ = [
    "CacheNamespace",
    "PineconeIndexWrapper",
    "cache_get",
    "cache_set",
    "get_pinecone_client",
    "get_redis_async",
    "get_redis_sync",
    "get_supabase_admin",
    "get_supabase_anon",
]
