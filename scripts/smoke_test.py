#!/usr/bin/env python3
"""
Smoke Test Suite for RssBot Platform

This script runs basic smoke tests to ensure the platform is functioning
correctly after deployment or configuration changes.
"""
import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
import json

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rssbot.core.config import get_config
from rssbot.discovery.cached_registry import get_cached_registry
from rssbot.models.service_registry import ConnectionMethod


class SmokeTestRunner:
    """
    Comprehensive smoke test runner for RssBot Platform.
    
    Tests critical paths and functionality to ensure system health.
    """
    
    def __init__(self) -> None:
        """Initialize the smoke test runner."""
        self.config = get_config()
        self.base_url = f"http://localhost:{self.config.controller_service_port}"
        self.service_token = self.config.service_token
        self.test_results: Dict[str, Dict[str, Any]] = {}
        
    async def run_all_tests(self) -> bool:
        """
        Run all smoke tests.
        
        Returns:
            True if all tests pass, False otherwise
        """
        print("🧪 Starting RssBot Platform Smoke Tests")
        print("=" * 60)
        
        tests = [
            ("Platform Health", self.test_platform_health),
            ("Service Registry", self.test_service_registry),
            ("Cache Operations", self.test_cache_operations),
            ("Connection Methods", self.test_connection_methods),
            ("Admin APIs", self.test_admin_apis),
            ("Service Discovery", self.test_service_discovery),
            ("Error Handling", self.test_error_handling),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name} tests...")
            
            try:
                start_time = time.time()
                result = await test_func()
                end_time = time.time()
                
                self.test_results[test_name] = {
                    "passed": result,
                    "duration": round(end_time - start_time, 3),
                    "error": None
                }
                
                if result:
                    print(f"  ✅ {test_name} PASSED ({end_time - start_time:.3f}s)")
                    passed += 1
                else:
                    print(f"  ❌ {test_name} FAILED")
                    
            except Exception as e:
                print(f"  💥 {test_name} CRASHED: {e}")
                self.test_results[test_name] = {
                    "passed": False,
                    "duration": 0,
                    "error": str(e)
                }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 SMOKE TEST SUMMARY")
        print("=" * 60)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            duration = f"{result['duration']}s"
            print(f"  {status:8} {test_name:20} {duration:>8}")
            
            if result["error"]:
                print(f"           Error: {result['error']}")
        
        success_rate = (passed / total) * 100
        print(f"\nOverall: {passed}/{total} tests passed ({success_rate:.1f}%)")
        
        if passed == total:
            print("🎉 All smoke tests PASSED! Platform is healthy.")
            return True
        else:
            print("⚠️  Some tests FAILED. Please investigate.")
            return False
    
    async def test_platform_health(self) -> bool:
        """Test platform health endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=10.0)
                
                if response.status_code != 200:
                    print(f"    ❌ Health endpoint returned {response.status_code}")
                    return False
                
                data = response.json()
                
                # Check required fields
                required_fields = ["status", "architecture", "platform"]
                for field in required_fields:
                    if field not in data:
                        print(f"    ❌ Missing field '{field}' in health response")
                        return False
                
                # Check architecture type
                if data["architecture"] != "per_service_core_controller":
                    print(f"    ❌ Unexpected architecture: {data['architecture']}")
                    return False
                
                print(f"    ✅ Platform healthy: {data['status']}")
                print(f"    ✅ Architecture: {data['architecture']}")
                return True
                
        except Exception as e:
            print(f"    💥 Health test failed: {e}")
            return False
    
    async def test_service_registry(self) -> bool:
        """Test service registry functionality."""
        try:
            cached_registry = await get_cached_registry()
            
            # Test registry initialization
            if not cached_registry:
                print("    ❌ Failed to get cached registry")
                return False
            
            # Test service discovery
            test_service = await cached_registry.registry_manager.get_service_by_name("controller_svc")
            if test_service:
                print(f"    ✅ Found controller service in registry")
            else:
                print(f"    ⚠️  Controller service not in registry (might be expected)")
            
            # Test connection method decision
            try:
                should_router = await cached_registry.should_use_router("ai_svc")
                print(f"    ✅ Connection decision for ai_svc: {'router' if should_router else 'rest'}")
            except Exception as e:
                print(f"    ⚠️  Connection decision failed: {e}")
            
            return True
            
        except Exception as e:
            print(f"    💥 Registry test failed: {e}")
            return False
    
    async def test_cache_operations(self) -> bool:
        """Test cache operations."""
        try:
            headers = {"X-Service-Token": self.service_token}
            
            async with httpx.AsyncClient() as client:
                # Test cache stats
                response = await client.get(
                    f"{self.base_url}/admin/cache/stats",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    print(f"    ❌ Cache stats returned {response.status_code}")
                    return False
                
                stats = response.json()
                cache_available = stats.get("cache_stats", {}).get("cache_available", False)
                print(f"    ✅ Cache available: {cache_available}")
                
                # Test cache invalidation
                response = await client.delete(
                    f"{self.base_url}/admin/cache",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    print(f"    ❌ Cache invalidation returned {response.status_code}")
                    return False
                
                print("    ✅ Cache invalidation successful")
                return True
                
        except Exception as e:
            print(f"    💥 Cache test failed: {e}")
            return False
    
    async def test_connection_methods(self) -> bool:
        """Test connection method configuration."""
        try:
            headers = {
                "X-Service-Token": self.service_token,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                # Test getting connection method
                response = await client.get(
                    f"{self.base_url}/services/ai_svc/connection-method",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    current_method = data.get("effective_method", "unknown")
                    print(f"    ✅ Current ai_svc method: {current_method}")
                else:
                    print(f"    ⚠️  Get connection method returned {response.status_code}")
                
                # Test setting connection method
                test_method = "rest"  # Safe to test with REST
                response = await client.post(
                    f"{self.base_url}/services/ai_svc/connection-method",
                    headers=headers,
                    json={"connection_method": test_method},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    print(f"    ✅ Successfully set ai_svc to {test_method}")
                    return True
                else:
                    print(f"    ❌ Set connection method returned {response.status_code}")
                    return False
                
        except Exception as e:
            print(f"    💥 Connection method test failed: {e}")
            return False
    
    async def test_admin_apis(self) -> bool:
        """Test admin API endpoints."""
        try:
            headers = {"X-Service-Token": self.service_token}
            
            async with httpx.AsyncClient() as client:
                # Test services list
                response = await client.get(
                    f"{self.base_url}/services",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    services = response.json()
                    service_count = len(services.get("services", []))
                    print(f"    ✅ Found {service_count} services in registry")
                else:
                    print(f"    ❌ Services list returned {response.status_code}")
                    return False
                
                # Test bulk update (with empty payload)
                response = await client.post(
                    f"{self.base_url}/admin/bulk-connection-methods",
                    headers={**headers, "Content-Type": "application/json"},
                    json={},  # Empty update
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    print("    ✅ Bulk update API accessible")
                else:
                    print(f"    ⚠️  Bulk update returned {response.status_code}")
                
                return True
                
        except Exception as e:
            print(f"    💥 Admin API test failed: {e}")
            return False
    
    async def test_service_discovery(self) -> bool:
        """Test service discovery functionality."""
        try:
            cached_registry = await get_cached_registry()
            
            # Test active services
            active_services = await cached_registry.registry_manager.get_active_services()
            print(f"    ✅ Found {len(active_services)} active services")
            
            # Test router services
            router_services = await cached_registry.get_services_for_router_mounting()
            print(f"    ✅ Found {len(router_services)} router services")
            
            # List discovered services
            for service in active_services[:5]:  # Limit to first 5
                method = await cached_registry.get_effective_connection_method(service.name)
                print(f"      - {service.name}: {method.value} (health: {service.health_status})")
            
            return True
            
        except Exception as e:
            print(f"    💥 Service discovery test failed: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling and edge cases."""
        try:
            headers = {"X-Service-Token": self.service_token}
            
            async with httpx.AsyncClient() as client:
                # Test invalid service name
                response = await client.get(
                    f"{self.base_url}/services/nonexistent_service/connection-method",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 404:
                    print("    ✅ Correctly handles nonexistent service")
                else:
                    print(f"    ⚠️  Unexpected response for invalid service: {response.status_code}")
                
                # Test invalid token
                invalid_headers = {"X-Service-Token": "invalid_token"}
                response = await client.get(
                    f"{self.base_url}/services",
                    headers=invalid_headers,
                    timeout=10.0
                )
                
                if response.status_code == 401:
                    print("    ✅ Correctly rejects invalid tokens")
                else:
                    print(f"    ⚠️  Unexpected response for invalid token: {response.status_code}")
                
                # Test invalid JSON
                response = await client.post(
                    f"{self.base_url}/services/ai_svc/connection-method",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"connection_method": "invalid_method"},
                    timeout=10.0
                )
                
                if response.status_code == 400:
                    print("    ✅ Correctly rejects invalid connection methods")
                else:
                    print(f"    ⚠️  Unexpected response for invalid method: {response.status_code}")
                
                return True
                
        except Exception as e:
            print(f"    💥 Error handling test failed: {e}")
            return False


async def main() -> int:
    """
    Main entry point for smoke tests.
    
    Returns:
        0 if all tests pass, 1 if any fail
    """
    runner = SmokeTestRunner()
    
    try:
        success = await runner.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Smoke test runner crashed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)