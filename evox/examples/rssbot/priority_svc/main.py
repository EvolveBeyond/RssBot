"""
Priority Service - Demonstrates priority queue and aggressive cache fallback features

This service demonstrates the advanced features of Evox:
1. Priority-aware request queuing
2. Aggressive cache fallback mechanisms
3. Health monitoring integration
"""

from evox.core import (
    service, get, post, data_io, data_intent, 
    proxy, PriorityLevel
)
import asyncio
import time


# Create service with health endpoint
svc = service("priority_svc") \
    .port(8002) \
    .health("/health") \
    .build()


# Declare a cacheable data model with aggressive fallback
@data_intent.cacheable(
    ttl="1h", 
    consistency="eventual",
    fallback="aggressive",
    max_stale="24h"
)
class PriorityTask:
    def __init__(self, task_id: int, name: str, priority: str):
        self.task_id = task_id
        self.name = name
        self.priority = priority


# High priority endpoint - user-facing critical operation
@get("/tasks/critical/{task_id}", priority="high")
async def get_critical_task(task_id: int):
    """High priority endpoint for critical user tasks"""
    # Read with aggressive fallback
    task = await data_io.read(
        f"task:{task_id}", 
        fallback="aggressive", 
        max_stale="24h"
    )
    
    if not task:
        # Simulate slow database operation
        await asyncio.sleep(2)
        task = {
            "id": task_id,
            "name": f"Critical Task {task_id}",
            "priority": "high",
            "status": "completed"
        }
        # Cache with 1 hour TTL
        await data_io.write(f"task:{task_id}", task, ttl=3600)
    
    return task


# Medium priority endpoint - default operations
@get("/tasks/regular/{task_id}", priority="medium")
async def get_regular_task(task_id: int):
    """Medium priority endpoint for regular tasks"""
    # Read with normal caching
    task = await data_io.read(f"task:{task_id}")
    
    if not task:
        # Simulate moderate database operation
        await asyncio.sleep(1)
        task = {
            "id": task_id,
            "name": f"Regular Task {task_id}",
            "priority": "medium",
            "status": "pending"
        }
        # Cache with 30 minute TTL
        await data_io.write(f"task:{task_id}", task, ttl=1800)
    
    return task


# Low priority endpoint - background operations
@get("/tasks/background/{task_id}", priority="low")
async def get_background_task(task_id: int):
    """Low priority endpoint for background tasks"""
    # Read with normal caching
    task = await data_io.read(f"task:{task_id}")
    
    if not task:
        # Simulate fast operation
        task = {
            "id": task_id,
            "name": f"Background Task {task_id}",
            "priority": "low",
            "status": "queued"
        }
        # Cache with 10 minute TTL
        await data_io.write(f"task:{task_id}", task, ttl=600)
    
    return task


# Endpoint that calls multiple services with different priorities
@get("/tasks/batch", priority="high")
async def batch_process_tasks():
    """Batch process tasks with different priorities"""
    # Gather multiple service calls with different priorities and concurrency control
    results = await proxy.gather(
        proxy.priority_svc.get_critical_task(1),
        proxy.priority_svc.get_regular_task(2),
        proxy.priority_svc.get_background_task(3),
        priority="high",
        concurrency=3
    )
    
    return {
        "batch_results": results,
        "processed_at": time.time()
    }


# Startup handler
@svc.on_startup
async def startup():
    print("Priority service started on port 8002")
    # Pre-populate some cache entries
    await data_io.write("task:1", {
        "id": 1,
        "name": "Preloaded Critical Task",
        "priority": "high",
        "status": "ready"
    }, ttl=7200)  # 2 hour TTL


# Shutdown handler
@svc.on_shutdown
async def shutdown():
    print("Priority service shutting down")


# Background task for cache maintenance
@svc.background_task(interval=300)  # Every 5 minutes
async def maintain_cache():
    """Background task to maintain cache health"""
    print("Running cache maintenance...")
    stats = data_io.get_cache_stats()
    print(f"Cache stats: {stats}")


if __name__ == "__main__":
    svc.run(dev=True)