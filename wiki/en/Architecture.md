# RssBot System Architecture

The RssBot platform is designed based on a Hybrid Microservices architecture, aiming to provide maximum flexibility, stability, and scalability.

## Core Components

The RssBot architecture consists of two main parts:

1.  **Core Platform:** The brain of the system, located in the `src/rssbot/` path.
2.  **Services:** Independent functional units, each responsible for a specific task, located in the `services/` directory.

---

### 1. Core Platform

The core platform includes the following critical components that manage and coordinate the entire system:

#### **Core Controller**

-   **Path:** `src/rssbot/core/controller.py`
-   **Responsibility:** This controller is the beating heart of the platform. Its main task is Service Discovery, managing their lifecycle, and deciding how to route requests.
-   **Functionality:** On startup, the controller identifies all available services and, based on each service's configuration, decides whether to load it as an **In-Process Router** or communicate with it via a **REST API**.

#### **Cached Registry**

-   **Path:** `src/rssbot/discovery/cached_registry.py`
-   **Responsibility:** This component caches information about active services, their Health Status, and their Connection Method in Redis.
-   **Advantage:** By using Redis, service discovery is performed in under a millisecond, which significantly increases the speed of communication between services.

#### **ServiceProxy**

-   **Path:** `src/rssbot/discovery/proxy.py`
-   **Responsibility:** This class is an intelligent tool for communication between services. Developers can easily call methods of a target service without worrying about its implementation details.
-   **Functionality:** The `ServiceProxy` automatically queries the cached registry and selects the best communication method:
    -   **Router Mode:** If the target service is loaded as an internal router, its method is called directly without network overhead.
    -   **REST Mode:** If the service is running independently, the `ServiceProxy` sends an HTTP request to the corresponding endpoint.
    -   **Hybrid Mode:** A combination of the two modes above, maximizing flexibility.

---

### 2. Services

Each service is an independent FastAPI application that provides a specific functionality. This independence allows teams to develop and deploy their service without affecting other parts of the system.

**Examples of Services:**

-   **`channel_mgr_svc`:** Manages channels and RSS feeds.
-   **`ai_svc`:** Provides artificial intelligence capabilities like content summarization.
-   **`bot_svc`:** Communicates with the Telegram API and sends messages.
-   **`user_svc`:** Manages users and subscriptions.

This modular and flexible architecture makes RssBot a powerful platform ready for future developments.
=======
# 🏗️ Architecture Overview

Complete guide to RssBot Platform's revolutionary hybrid microservices architecture.

## 🎯 Architecture Philosophy

RssBot Platform introduces **Per-Service Connection Autonomy** - a paradigm where each microservice independently chooses its connection method:

- **🔗 Router Mode**: Direct function calls for maximum performance
- **🌐 REST Mode**: HTTP APIs for scalability and language independence  
- **⚡ Hybrid Mode**: Intelligent switching based on load, health, and context
- **🚫 Disabled Mode**: Complete service isolation for maintenance/security

This approach combines the **performance benefits of monoliths** with the **scalability of microservices**.

## 🏛️ System Architecture

```mermaid
graph TB
    subgraph "🌐 External World"
        TG[Telegram API]
        OPENAI[OpenAI API]
        STRIPE[Stripe API]
        RSS[RSS Feeds]
        WEB[Web Clients]
    end
    
    subgraph "🎯 Core Platform (src/rssbot/)"
        CTRL[Controller Engine<br/>🎮 Orchestration & Routing]
        REG[Service Registry<br/>📋 Redis-Cached Discovery]
        DISC[Health Monitor<br/>🏥 Auto-Healing]
        PROXY[Service Proxy<br/>🔀 Smart Routing]
        CACHE[Multi-Level Cache<br/>⚡ Performance Layer]
    end
    
    subgraph "📡 Microservices (services/)"
        DB[Database Service<br/>🗄️ Data Persistence]
        BOT[Bot Service<br/>🤖 Telegram Integration]
        AI[AI Service<br/>🧠 OpenAI Processing]
        FMT[Formatting Service<br/>📝 Content Templates]
        USER[User Service<br/>👥 Management]
        PAY[Payment Service<br/>💳 Stripe Integration]
        ADMIN[Admin Service<br/>⚙️ Management Panel]
        CHAN[Channel Manager<br/>📢 RSS Distribution]
    end
    
    subgraph "🗄️ Data Layer"
        REDIS[(Redis<br/>⚡ Cache + Registry)]
        POSTGRES[(PostgreSQL<br/>🗃️ Primary Database)]
        SQLITE[(SQLite<br/>📦 Local/Development)]
    end
    
    WEB --> CTRL
    CTRL <--> REG
    REG <--> REDIS
    CTRL --> DISC
    CTRL --> PROXY
    CTRL <--> CACHE
    
    PROXY <--> DB
    PROXY <--> BOT
    PROXY <--> AI
    PROXY <--> FMT
    PROXY <--> USER
    PROXY <--> PAY
    PROXY <--> ADMIN
    PROXY <--> CHAN
    
    DB --> POSTGRES
    DB --> SQLITE
    BOT <--> TG
    AI <--> OPENAI
    PAY <--> STRIPE
    CHAN --> RSS
    
    CACHE <--> REDIS
```

## 🔄 Connection Methods Deep Dive

### 1. Router Mode (Direct Integration)

**When to Use**: Core services, high-frequency calls, development

```python
# Direct function call - no HTTP overhead
@app.include_router(service_router, prefix="/services/ai_svc")

async def process_content(data: ContentRequest) -> ContentResponse:
    # Direct function call within same process
    return await ai_service.process(data)
```

**Characteristics**:
- ✅ **Fastest Performance**: No HTTP serialization overhead
- ✅ **Type Safety**: Full Python type checking
- ✅ **Shared Resources**: Memory, connections, cache
- ✅ **Simple Debugging**: Single process stack traces
- ❌ **Language Lock-in**: Python only
- ❌ **Single Point of Failure**: Process crash affects all services

**Performance**: ~0.1ms call overhead

### 2. REST Mode (HTTP Microservices)

**When to Use**: Independent services, different languages, maximum scalability

```python
# HTTP call to independent service
async def process_content(data: ContentRequest) -> ContentResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{service_url}/process", json=data.dict())
        return ContentResponse.parse_obj(response.json())
```

**Characteristics**:
- ✅ **Language Agnostic**: Any programming language
- ✅ **Independent Scaling**: Per-service resource allocation
- ✅ **Fault Isolation**: Service failures don't affect others
- ✅ **Distributed Deployment**: Services can run on different hosts
- ❌ **Network Overhead**: HTTP serialization/deserialization
- ❌ **Complex Debugging**: Distributed tracing required

**Performance**: ~5-50ms call overhead (depending on network)

### 3. Hybrid Mode (Intelligent Switching)

**When to Use**: Production environments, variable load patterns

```python
# Intelligent decision-making
async def process_content(data: ContentRequest) -> ContentResponse:
    service_info = await registry.get_service("ai_svc")
    
    # Decision factors:
    # - Service health and load
    # - Network conditions  
    # - Data size and priority
    # - Historical performance
    
    if should_use_direct(service_info, data):
        return await ai_service.process(data)  # Router mode
    else:
        return await http_call(service_info.url, data)  # REST mode
```

**Decision Algorithm**:
```python
def should_use_direct(service: ServiceInfo, request: Request) -> bool:
    return (
        service.is_local and                    # Same host
        service.health_score > 0.8 and         # Healthy
        service.current_load < 0.7 and         # Not overloaded
        request.priority == "high" and          # Important request
        request.data_size < 1024 * 1024        # Small payload
    )
```

**Characteristics**:
- ✅ **Best of Both Worlds**: Performance + scalability
- ✅ **Adaptive**: Responds to changing conditions
- ✅ **Fault Tolerant**: Automatic failover
- ✅ **Load Aware**: Intelligent load distribution
- ❌ **Complex Logic**: Sophisticated decision making
- ❌ **Configuration**: Requires tuning

### 4. Disabled Mode (Service Isolation)

**When to Use**: Maintenance, security isolation, feature flags

```python
# Service completely disabled
async def process_content(data: ContentRequest) -> ContentResponse:
    raise ServiceDisabledException(
        "AI service is temporarily disabled for maintenance"
    )
```

**Use Cases**:
- 🔧 **Maintenance Mode**: Disable service during updates
- 🔒 **Security Isolation**: Isolate compromised services
- 🚩 **Feature Flags**: Gradually roll out new services
- 🧪 **Testing**: Simulate service failures

## 📋 Service Registry Architecture

### Redis-Cached Registry

The service registry is the heart of the platform, providing sub-millisecond service discovery:

```python
class CachedServiceRegistry:
    def __init__(self):
        self.redis = Redis(decode_responses=True)
        self.db = DatabaseConnection()
        self.cache = LRUCache(maxsize=1000)
    
    async def get_service(self, name: str) -> ServiceInfo:
        # Level 1: In-memory cache (0.01ms)
        if name in self.cache:
            return self.cache[name]
        
        # Level 2: Redis cache (0.1-1ms)
        cached = await self.redis.get(f"service:{name}")
        if cached:
            service = ServiceInfo.parse_raw(cached)
            self.cache[name] = service
            return service
        
        # Level 3: Database (10-100ms)
        service = await self.db.get_service(name)
        if service:
            # Cache for future requests
            await self.redis.set(f"service:{name}", service.json(), ex=300)
            self.cache[name] = service
            return service
        
        raise ServiceNotFoundException(name)
```

### Service Discovery Performance

| Cache Level | Latency | Hit Rate | Description |
|-------------|---------|----------|-------------|
| **Memory** | ~0.01ms | 80-90% | LRU cache for frequently accessed services |
| **Redis** | ~0.1ms | 15-18% | Distributed cache for service metadata |
| **Database** | ~10ms | 1-2% | Authoritative source, cache misses only |

**Total Performance**: ~1000x faster than pure database queries

## 🏥 Health Monitoring & Auto-Healing

### Multi-Layer Health Checks

```python
class HealthChecker:
    async def check_service_health(self, service: ServiceInfo) -> HealthStatus:
        checks = await asyncio.gather(
            self.check_process_health(service),     # Process alive?
            self.check_endpoint_health(service),    # HTTP responsive?
            self.check_dependency_health(service),  # Dependencies OK?
            self.check_performance_health(service), # Performance within SLA?
            return_exceptions=True
        )
        
        return HealthStatus.from_checks(checks)

class AutoHealer:
    async def handle_unhealthy_service(self, service: ServiceInfo):
        if service.connection_method == "hybrid":
            # Try switching to alternative method
            await self.switch_connection_method(service)
        elif service.health_score < 0.3:
            # Remove from load balancer rotation
            await self.remove_from_rotation(service)
        elif service.consecutive_failures > 5:
            # Attempt service restart
            await self.restart_service(service)
```

### Health Metrics

```python
@dataclass
class HealthStatus:
    score: float          # 0.0 to 1.0
    latency: float        # Average response time
    success_rate: float   # Success rate over time window
    load: float          # Current CPU/memory usage
    dependencies: Dict[str, bool]  # Dependency health
    last_check: datetime
    consecutive_failures: int
    
    def is_healthy(self) -> bool:
        return (
            self.score > 0.7 and
            self.latency < 1000 and  # ms
            self.success_rate > 0.95 and
            self.load < 0.8
        )
```

## 🔀 Smart Service Proxy

The service proxy is responsible for intelligent routing and load balancing:

```python
class ServiceProxy:
    async def call_service(self, service_name: str, method: str, **kwargs):
        service = await self.registry.get_service(service_name)
        
        # Route based on connection method
        router_map = {
            "router": self._direct_call,
            "rest": self._http_call, 
            "hybrid": self._hybrid_call,
            "disabled": self._disabled_call
        }
        
        handler = router_map[service.connection_method]
        
        # Execute with monitoring
        start_time = time.time()
        try:
            result = await handler(service, method, **kwargs)
            await self._record_success(service, time.time() - start_time)
            return result
        except Exception as e:
            await self._record_failure(service, e)
            raise

    async def _hybrid_call(self, service: ServiceInfo, method: str, **kwargs):
        # Intelligent routing decision
        if await self._should_use_direct(service, kwargs):
            return await self._direct_call(service, method, **kwargs)
        else:
            return await self._http_call(service, method, **kwargs)
    
    async def _should_use_direct(self, service: ServiceInfo, request_data: dict) -> bool:
        return (
            service.is_local and                           # Same process/host
            service.health.score > 0.8 and                # Healthy service
            service.health.load < 0.7 and                 # Not overloaded
            len(str(request_data)) < 1024 * 1024 and      # Small request
            service.health.latency < 100                   # Fast service
        )
```

### Load Balancing Strategies

```python
class LoadBalancer:
    async def select_instance(self, service_name: str) -> ServiceInstance:
        instances = await self.registry.get_service_instances(service_name)
        healthy_instances = [i for i in instances if i.is_healthy()]
        
        if not healthy_instances:
            raise NoHealthyInstancesException(service_name)
        
        # Weighted round-robin based on health score and load
        weights = [
            instance.health.score * (1 - instance.health.load)
            for instance in healthy_instances
        ]
        
        return self._weighted_choice(healthy_instances, weights)
```

## 📊 Performance Architecture

### Multi-Level Caching Strategy

```python
class CacheManager:
    def __init__(self):
        # L1: Process memory (fastest)
        self.l1_cache = LRUCache(maxsize=1000)
        
        # L2: Redis (fast, shared)
        self.l2_cache = RedisCache()
        
        # L3: Database (slowest, authoritative)
        self.l3_store = DatabaseConnection()
    
    async def get(self, key: str) -> Optional[Any]:
        # Try L1 cache
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # Try L2 cache
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value
        
        # Fallback to L3
        value = await self.l3_store.get(key)
        if value:
            await self.l2_cache.set(key, value, ex=300)
            self.l1_cache[key] = value
            return value
        
        return None
```

### Async Performance Patterns

```python
# Concurrent service calls
async def process_multiple_feeds(feed_urls: List[str]) -> List[ProcessedFeed]:
    tasks = [
        process_single_feed(url)
        for url in feed_urls
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)

# Request pipelining
async def batch_ai_processing(requests: List[AIRequest]) -> List[AIResponse]:
    # Group small requests for batch processing
    if all(req.is_small() for req in requests):
        return await ai_service.batch_process(requests)
    else:
        # Process large requests individually
        return await asyncio.gather(*[
            ai_service.process(req) for req in requests
        ])
```

## 🔒 Security Architecture

### Service-to-Service Authentication

```python
class ServiceAuth:
    def __init__(self):
        self.secret_key = os.getenv("SERVICE_SECRET_KEY")
        self.token_cache = LRUCache(maxsize=1000)
    
    def generate_service_token(self, service_name: str) -> str:
        payload = {
            "service": service_name,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "scope": self.get_service_permissions(service_name)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    async def verify_service_token(self, token: str) -> ServiceIdentity:
        # Check cache first
        if token in self.token_cache:
            return self.token_cache[token]
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            identity = ServiceIdentity.from_payload(payload)
            self.token_cache[token] = identity
            return identity
        except jwt.InvalidTokenError:
            raise UnauthorizedException("Invalid service token")
```

### Input Validation & Sanitization

```python
# Automatic input validation with Pydantic
class ServiceRequest(BaseModel):
    service_name: str = Field(..., regex=r"^[a-z_]+$")
    method: str = Field(..., regex=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    data: Dict[str, Any] = Field(..., max_items=100)
    
    @validator("data")
    def validate_data_size(cls, v):
        serialized = json.dumps(v)
        if len(serialized) > 1_000_000:  # 1MB limit
            raise ValueError("Request data exceeds size limit")
        return v
    
    @validator("service_name")
    def validate_service_exists(cls, v):
        # Validate against known services
        if v not in KNOWN_SERVICES:
            raise ValueError(f"Unknown service: {v}")
        return v
```

## 🚀 Deployment Architectures

### Single-Host Deployment

```yaml
# Docker Compose for single-host deployment
version: '3.8'
services:
  rssbot-platform:
    build: .
    ports:
      - "8004:8004"
    environment:
      - ENVIRONMENT=production
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@postgres:5432/rssbot
    depends_on:
      - redis
      - postgres
    
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: rssbot
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Multi-Host Kubernetes Deployment

```yaml
# Kubernetes deployment with service mesh
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rssbot-controller
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rssbot-controller
  template:
    spec:
      containers:
      - name: controller
        image: rssbot/controller:latest
        ports:
        - containerPort: 8004
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
# Independent services can be scaled separately
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rssbot-ai-service
spec:
  replicas: 2  # Scale AI service independently
  selector:
    matchLabels:
      app: rssbot-ai
  template:
    spec:
      containers:
      - name: ai-service
        image: rssbot/ai-service:latest
        ports:
        - containerPort: 8003
```

## 📈 Scaling Patterns

### Horizontal Scaling

```python
# Service instances can be scaled independently
class ServiceRegistry:
    async def register_service_instance(self, service_name: str, instance: ServiceInstance):
        # Add new instance to load balancer pool
        await self.redis.sadd(f"instances:{service_name}", instance.id)
        await self.redis.hset(f"instance:{instance.id}", instance.dict())
        
        # Update load balancer weights
        await self.update_load_balancer(service_name)
    
    async def get_service_instances(self, service_name: str) -> List[ServiceInstance]:
        instance_ids = await self.redis.smembers(f"instances:{service_name}")
        instances = []
        
        for instance_id in instance_ids:
            instance_data = await self.redis.hgetall(f"instance:{instance_id}")
            if instance_data:
                instances.append(ServiceInstance.parse_obj(instance_data))
        
        return instances
```

### Auto-Scaling Triggers

```python
class AutoScaler:
    async def should_scale_up(self, service_name: str) -> bool:
        metrics = await self.get_service_metrics(service_name)
        
        return (
            metrics.cpu_usage > 0.8 or           # High CPU
            metrics.memory_usage > 0.85 or       # High memory  
            metrics.request_queue_length > 100 or # Queue backup
            metrics.avg_response_time > 1000     # Slow responses
        )
    
    async def should_scale_down(self, service_name: str) -> bool:
        metrics = await self.get_service_metrics(service_name)
        
        return (
            metrics.cpu_usage < 0.3 and          # Low CPU
            metrics.memory_usage < 0.4 and       # Low memory
            metrics.request_rate < 10 and        # Low traffic
            len(await self.get_instances(service_name)) > 1  # Multiple instances
        )
```

---

**This architecture enables RssBot Platform to achieve unprecedented flexibility, performance, and scalability in the microservices landscape. 🚀**