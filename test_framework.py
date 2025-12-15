"""
Test Framework - Comprehensive tests for Evox framework features

This script tests the core features of the Evox framework including:
1. Service creation and method chaining
2. Data IO with intent-aware behavior
3. Priority queue functionality
4. Aggressive cache fallback
5. Health monitoring
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evox.core import (
    service, get, post, data_io, data_intent, 
    proxy, PriorityLevel, get_priority_queue
)


async def test_service_creation():
    """Test service creation with fluent API"""
    print("Testing service creation...")
    
    # Create service using fluent API
    svc = service("test_svc").port(8080).health("/health").build()
    
    assert svc.name == "test_svc"
    assert svc._port == 8080
    print("✅ Service creation test passed")


async def test_data_io_basic():
    """Test basic data IO operations"""
    print("Testing basic data IO...")
    
    # Test write and read using default namespace
    # data_io is an accessor, we need to access a namespace (even default)
    data_io_instance = data_io.default  # Access the default namespace
    await data_io_instance.write("test_key", "test_value", ttl=60)
    result = await data_io_instance.read("test_key")
    
    assert result == "test_value"
    print("✅ Basic data IO test passed")


async def test_data_intent_declaration():
    """Test data intent declaration"""
    print("Testing data intent declaration...")
    
    @data_intent.cacheable(ttl="1h", consistency="eventual")
    class TestDataModel:
        def __init__(self, name: str):
            self.name = name
    
    # Check if intent was applied
    assert hasattr(TestDataModel, '_data_intent')
    assert TestDataModel._data_intent['ttl'] == "1h"
    print("✅ Data intent declaration test passed")


async def test_priority_queue():
    """Test priority queue functionality"""
    print("Testing priority queue...")
    
    # Get priority queue instance
    queue = get_priority_queue()
    
    # Test submitting a simple task
    async def simple_task():
        return "task_completed"
    
    result = await queue.submit(simple_task, priority=PriorityLevel.HIGH)
    assert result == "task_completed"
    
    print("✅ Priority queue test passed")


async def test_aggressive_cache_fallback():
    """Test aggressive cache fallback mechanism"""
    print("Testing aggressive cache fallback...")
    
    # Write data with short TTL using default namespace
    data_io_instance = data_io.default
    await data_io_instance.write("fallback_test", "original_value", ttl=1)  # 1 second
    
    # Wait for expiration
    await asyncio.sleep(1.1)
    
    # Try to read with aggressive fallback (should return stale data)
    result = await data_io_instance.read("fallback_test", fallback="aggressive", max_stale="1h")
    
    assert result == "original_value"
    print("✅ Aggressive cache fallback test passed")


async def test_queue_gather():
    """Test queue gather functionality"""
    print("Testing queue gather...")
    
    # Test gather with multiple concurrent calls using the queue directly
    queue = get_priority_queue()
    
    async def mock_service_call(value):
        await asyncio.sleep(0.1)  # Simulate async work
        return f"result_{value}"
    
    # Create actual coroutines
    coro1 = mock_service_call(1)
    coro2 = mock_service_call(2)
    coro3 = mock_service_call(3)
    
    results = await queue.gather(
        coro1,
        coro2,
        coro3,
        priority=PriorityLevel.HIGH,
        concurrency=2
    )
    
    expected = ["result_1", "result_2", "result_3"]
    assert results == expected
    print("✅ Queue gather test passed")


async def main():
    """Run all tests"""
    print("Running Evox Framework Tests")
    print("=" * 40)
    
    try:
        await test_service_creation()
        await test_data_io_basic()
        await test_data_intent_declaration()
        await test_priority_queue()
        await test_aggressive_cache_fallback()
        await test_queue_gather()
        
        print("\n🎉 All tests passed!")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)