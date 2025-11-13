import time
import hashlib
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class CacheEntry:
    """Represents a cached query result"""
    data: Any
    timestamp: float
    ttl_minutes: int
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        return time.time() - self.timestamp > (self.ttl_minutes * 60)
    
    def get_age_seconds(self) -> int:
        """Get the age of the cache entry in seconds"""
        return int(time.time() - self.timestamp)

class QueryResultCache:
    """In-memory cache for query results with TTL (Time To Live) support"""
    
    def __init__(self, default_ttl_minutes: int = 5):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl_minutes
        self.hit_count = 0
        self.miss_count = 0
        self.last_cleanup = time.time()
    
    def _generate_cache_key(self, query: str, filters: Dict[str, Any] = None) -> str:
        """Generate a unique cache key for a query and filters"""
        # Create a normalized string representation of the query and filters
        cache_data = {
            'query': query.lower().strip(),
            'filters': filters or {}
        }
        
        # Convert to string and hash for consistent key generation
        cache_string = str(sorted(cache_data.items()))
        return hashlib.md5(cache_string.encode('utf-8')).hexdigest()
    
    def get(self, query: str, filters: Dict[str, Any] = None) -> Optional[Any]:
        """Get a cached result if available and not expired"""
        key = self._generate_cache_key(query, filters)
        
        if key in self.cache:
            entry = self.cache[key]
            
            if not entry.is_expired():
                self.hit_count += 1
                print(f"Cache HIT for query '{query[:50]}...' (age: {entry.get_age_seconds()}s)")
                return entry.data
            else:
                # Entry expired, remove it
                del self.cache[key]
                print(f"Cache entry expired for query '{query[:50]}...'")
        
        self.miss_count += 1
        print(f"Cache MISS for query '{query[:50]}...'")
        return None
    
    def set(self, query: str, data: Any, filters: Dict[str, Any] = None, ttl_minutes: Optional[int] = None) -> None:
        """Store a query result in the cache"""
        key = self._generate_cache_key(query, filters)
        ttl = ttl_minutes if ttl_minutes is not None else self.default_ttl
        
        self.cache[key] = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl_minutes=ttl
        )
        
        print(f"Cached result for query '{query[:50]}...' (TTL: {ttl}min)")
        
        # Periodically clean up expired entries
        self._maybe_cleanup()
    
    def _maybe_cleanup(self):
        """Clean up expired entries if it's been a while since last cleanup"""
        current_time = time.time()
        
        # Clean up every 5 minutes
        if current_time - self.last_cleanup > 300:
            self.cleanup_expired()
            self.last_cleanup = current_time
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache"""
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            print(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def clear(self):
        """Clear all cached entries"""
        count = len(self.cache)
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        print(f"Cleared {count} cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_entries": len(self.cache),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size_bytes": self._estimate_cache_size()
        }
    
    def _estimate_cache_size(self) -> int:
        """Rough estimate of cache memory usage"""
        # This is a very rough estimate
        size = 0
        for entry in self.cache.values():
            # Estimate based on string length of data
            if hasattr(entry.data, '__len__'):
                size += len(str(entry.data))
            else:
                size += 1000  # Default estimate for complex objects
        return size
    
    def get_cache_info(self) -> str:
        """Get formatted cache information for display"""
        stats = self.get_stats()
        
        # Count expired entries
        expired_count = sum(1 for entry in self.cache.values() if entry.is_expired())
        
        return f"""Cache Statistics:
- Total entries: {stats['total_entries']} ({expired_count} expired)
- Cache hits: {stats['hit_count']}
- Cache misses: {stats['miss_count']}
- Hit rate: {stats['hit_rate_percent']}%
- Estimated size: {stats['cache_size_bytes']:,} bytes
"""