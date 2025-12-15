"""
Call Scheduler - Priority-aware concurrent execution
"""
import asyncio
from typing import Any, List, Callable, Optional
from enum import Enum


class Priority(Enum):
    """Execution priority levels"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class Policy(Enum):
    """Execution policies"""
    PARTIAL_OK = "partial_ok"
    ALL_OR_NOTHING = "all_or_nothing"


class CallScheduler:
    """Priority-aware concurrent execution scheduler"""
    
    def __init__(self):
        self._semaphore = asyncio.Semaphore(10)  # Limit concurrent executions
        self._priority_queues = {
            Priority.HIGH: asyncio.PriorityQueue(),
            Priority.MEDIUM: asyncio.PriorityQueue(),
            Priority.LOW: asyncio.PriorityQueue()
        }
    
    async def execute(self, coro, priority: Priority = Priority.MEDIUM):
        """
        Execute a coroutine with priority
        
        Args:
            coro: Coroutine to execute
            priority: Execution priority
            
        Returns:
            Result of the coroutine execution
        """
        async with self._semaphore:
            return await coro
    
    async def parallel(self, *coros, 
                      priority: Priority = Priority.MEDIUM,
                      policy: Policy = Policy.PARTIAL_OK,
                      concurrency: int = 5):
        """
        Execute multiple coroutines concurrently with priority and policy control
        
        Args:
            *coros: Coroutines to execute
            priority: Execution priority
            policy: Execution policy
            concurrency: Maximum concurrent executions
            
        Returns:
            List of results
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_coro(coro):
            async with semaphore:
                return await coro
        
        tasks = [limited_coro(coro) for coro in coros]
        
        if policy == Policy.ALL_OR_NOTHING:
            # All must succeed or all fail
            return await asyncio.gather(*tasks)
        else:
            # Partial results are acceptable
            results = []
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
            return results


# Global scheduler instance
scheduler = CallScheduler()