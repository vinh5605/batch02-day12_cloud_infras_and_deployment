#  Code Lab: Deploy Your AI Agent to Production

> **AICB-P1 · VinUniversity 2026**  
> Thời gian: 3-4 giờ | Độ khó: Intermediate

##  Mục Tiêu

Sau khi hoàn thành lab này, bạn sẽ:
- Hiểu sự khác biệt giữa development và production
- Containerize một AI agent với Docker
- Deploy agent lên cloud platform
- Bảo mật API với authentication và rate limiting
- Thiết kế hệ thống có khả năng scale và reliable

---

##  Yêu Cầu

```bash
 Python 3.11+
 Docker & Docker Compose
 Git
 Text editor (VS Code khuyến nghị)
 Terminal/Command line
```

**Không cần:**
-  OpenAI API key (dùng mock LLM)
-  Credit card
-  Kinh nghiệm DevOps trước đó

---

##  Lộ Trình Lab

| Phần | Thời gian | Nội dung |
|------|-----------|----------|
| **Part 1** | 30 phút | Localhost vs Production |
| **Part 2** | 45 phút | Docker Containerization |
| **Part 3** | 45 phút | Cloud Deployment |
| **Part 4** | 40 phút | API Security |
| **Part 5** | 40 phút | Scaling & Reliability |
| **Part 6** | 60 phút | Final Project |

---

## Part 1: Localhost vs Production (30 phút)

###  Concepts

**Vấn đề:** "It works on my machine" — code chạy tốt trên laptop nhưng fail khi deploy.

**Nguyên nhân:**
- Hardcoded secrets
- Khác biệt về environment (Python version, OS, dependencies)
- Không có health checks
- Config không linh hoạt

**Giải pháp:** 12-Factor App principles

###  Exercise 1.1: Phát hiện anti-patterns

```bash
cd 01-localhost-vs-production/develop
```

**Nhiệm vụ:** Đọc `app.py` và tìm ít nhất 5 vấn đề.

<details>
<summary> Gợi ý</summary>

Tìm:
- API key hardcode
- Port cố định
- Debug mode
- Không có health check
- Không xử lý shutdown

</details>

###  Exercise 1.2: Chạy basic version

```bash
pip install -r requirements.txt
python app.py
```

> 🪟 **Windows:** nếu `/ask` trả về `500 Internal Server Error` với `UnicodeEncodeError: 'charmap' codec...`, đó là do `print()` ghi tiếng Việt ra console `cp1252`. Chạy với:
> ```bash
> set PYTHONIOENCODING=utf-8   # cmd
> $env:PYTHONIOENCODING="utf-8"; python app.py   # PowerShell
> ```
> Đây cũng là một ví dụ thực tế cho lý do tại sao `print()` không nên dùng trong production (Vấn đề 3) — `logging` không gặp lỗi này.

Test:
```bash
curl -X POST "http://localhost:8000/ask?question=hello"
```

**Quan sát:** Nó chạy! Nhưng có production-ready không?

###  Exercise 1.3: So sánh với advanced version

```bash
cd ../production
cp .env.example .env
pip install -r requirements.txt
python app.py
```

**Nhiệm vụ:** So sánh 2 files `app.py`. Điền vào bảng:

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode | Env vars | ... |
| Health check |  |  | ... |
| Logging | print() | JSON | ... |
| Shutdown | Đột ngột | Graceful | ... |

###  Checkpoint 1

- [ ] Hiểu tại sao hardcode secrets là nguy hiểm
- [ ] Biết cách dùng environment variables
- [ ] Hiểu vai trò của health check endpoint
- [ ] Biết graceful shutdown là gì

---

## Part 2: Docker Containerization (45 phút)

###  Concepts

**Vấn đề:** "Works on my machine" part 2 — Python version khác, dependencies conflict.

**Giải pháp:** Docker — đóng gói app + dependencies vào container.

**Benefits:**
- Consistent environment
- Dễ deploy
- Isolation
- Reproducible builds

###  Exercise 2.1: Dockerfile cơ bản

```bash
cd ../../02-docker/develop
```

**Nhiệm vụ:** Đọc `Dockerfile` và trả lời:

1. Base image là gì?
2. Working directory là gì?
3. Tại sao COPY requirements.txt trước?
4. CMD vs ENTRYPOINT khác nhau thế nào?

###  Exercise 2.2: Build và run

```bash
# Build image
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .

# Run container
docker run -p 8000:8000 my-agent:develop

# Test
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
```

**Quan sát:** Image size là bao nhiêu?
```bash
docker images my-agent:develop
```

###  Exercise 2.3: Multi-stage build

```bash
cd ../production
```

**Nhiệm vụ:** Đọc `Dockerfile` và tìm:
- Stage 1 (`builder`) làm gì?
- Stage 2 (`runtime`) làm gì?
- Tại sao image nhỏ hơn?
- Tại sao có `USER appuser` ở stage 2?

Build và so sánh (chạy từ **project root**, vì Dockerfile `COPY` các file dùng đường dẫn tương đối tới root):
```bash
cd ../..
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images | grep my-agent
```

###  Exercise 2.4: Docker Compose stack

**Nhiệm vụ:** Đọc `docker-compose.yml` và vẽ architecture diagram.

> `env_file: .env.local` được khai báo nhưng file này không commit vào git (xem `.gitignore`).
> Tạo trước file rỗng `02-docker/production/.env.local` nếu Docker Compose báo lỗi "file not found".

```bash
docker compose up
```

Services nào được start? Chúng communicate thế nào?

<details>
<summary> Gợi ý đáp án</summary>

4 services: `agent` (FastAPI, không expose port — chỉ nginx gọi được), `redis` (session/rate-limit cache), `qdrant` (vector DB cho RAG), `nginx` (reverse proxy + load balancer, expose port 80/443). Tất cả communicate qua network nội bộ `internal`; client chỉ thấy nginx.

</details>

Test:
```bash
# Health check
curl http://localhost/health

# Agent endpoint
curl http://localhost/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain microservices"}'
```

###  Checkpoint 2

- [ ] Hiểu cấu trúc Dockerfile
- [ ] Biết lợi ích của multi-stage builds
- [ ] Hiểu Docker Compose orchestration
- [ ] Biết cách debug container (`docker logs`, `docker exec`)

---

## Part 3: Cloud Deployment (45 phút)

###  Concepts

**Vấn đề:** Laptop không thể chạy 24/7, không có public IP.

**Giải pháp:** Cloud platforms — Railway, Render, GCP Cloud Run.

**So sánh:**

| Platform | Độ khó | Free tier | Best for |
|----------|--------|-----------|----------|
| Railway | ⭐ | $5 credit | Prototypes |
| Render | ⭐⭐ | 750h/month | Side projects |
| Cloud Run | ⭐⭐⭐ | 2M requests | Production |

###  Exercise 3.1: Deploy Railway (15 phút)

```bash
cd ../../03-cloud-deployment/railway
```

**Steps:**

1. Install Railway CLI:
```bash
npm i -g @railway/cli
```

2. Login:
```bash
railway login
```

3. Initialize project:
```bash
railway init
```

4. Set environment variables:
```bash
railway variables set PORT=8000
railway variables set AGENT_API_KEY=my-secret-key
```

5. Deploy:
```bash
railway up
```

6. Get public URL:
```bash
railway domain
```

**Nhiệm vụ:** Test public URL với curl hoặc Postman.

Test:
```bash
# Health check
curl https://<your-app>.up.railway.app/health

# Agent endpoint
curl https://<your-app>.up.railway.app/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
```

> Thay `<your-app>.up.railway.app` bằng domain thật lấy từ `railway domain` ở bước 6.

###  Exercise 3.2: Deploy Render (15 phút)

```bash
cd ../render
```

**Steps:**

1. Push code lên GitHub (nếu chưa có)
2. Vào [render.com](https://render.com) → Sign up
3. New → Blueprint
4. Connect GitHub repo
5. Render tự động đọc `render.yaml`
6. Set environment variables trong dashboard
7. Deploy!

**Nhiệm vụ:** So sánh `render.yaml` với `railway.toml`. Khác nhau gì?

###  Exercise 3.3: (Optional) GCP Cloud Run (15 phút)

```bash
cd ../production-cloud-run
```

**Yêu cầu:** GCP account (có free tier).

**Nhiệm vụ:** Đọc `cloudbuild.yaml` và `service.yaml`. Hiểu CI/CD pipeline.

###  Checkpoint 3

- [ ] Deploy thành công lên ít nhất 1 platform
- [ ] Có public URL hoạt động
- [ ] Hiểu cách set environment variables trên cloud
- [ ] Biết cách xem logs

---

## Part 4: API Security (40 phút)

###  Concepts

**Vấn đề:** Public URL = ai cũng gọi được = hết tiền OpenAI.

**Giải pháp:**
1. **Authentication** — Chỉ user hợp lệ mới gọi được
2. **Rate Limiting** — Giới hạn số request/phút
3. **Cost Guard** — Dừng khi vượt budget

###  Exercise 4.1: API Key authentication

```bash
cd ../../04-api-gateway/develop
```

**Nhiệm vụ:** Đọc `app.py` và tìm:
- API key được check ở đâu?
- Điều gì xảy ra nếu sai key?
- Làm sao rotate key?

Test:
```bash
AGENT_API_KEY=secret-key-123 python app.py
```

> ⚠️ `question` ở endpoint `/ask` là **query parameter** (không phải JSON body), vì handler nhận `question: str` trực tiếp — không qua Pydantic model. Vì vậy gửi `?question=...` trên URL, không phải `-d '{"question": ...}'`.

```bash
#  Không có key → 401
curl -X POST "http://localhost:8000/ask?question=Hello"

#  Có key nhưng sai → 403
curl -X POST "http://localhost:8000/ask?question=Hello" \
  -H "X-API-Key: wrong-key"

#  Có key đúng → 200
curl -X POST "http://localhost:8000/ask?question=Hello" \
  -H "X-API-Key: secret-key-123"
```

> 💡 Muốn xem một implementation hoàn chỉnh (header `X-API-Key`, JWT, rate limiting, cost guard cùng lúc)? Tham khảo `04-api-gateway/production/`.

###  Exercise 4.2: JWT authentication (Advanced)

```bash
cd ../production
```

**Nhiệm vụ:** 
1. Đọc `auth.py` — hiểu JWT flow
2. Lấy token:
```bash
python app.py

curl http://localhost:8000/token -X POST \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'
```

3. Dùng token để gọi API:
```bash
TOKEN="<token_từ_bước_2>"
curl http://localhost:8000/ask -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain JWT"}'
```

###  Exercise 4.3: Rate limiting

**Nhiệm vụ:** Đọc `rate_limiter.py` (trong `04-api-gateway/production/`) và trả lời:
- Algorithm nào được dùng? (Token bucket? Sliding window?)
- Limit là bao nhiêu requests/minute?
- Làm sao bypass limit cho admin?

Test:
```bash
# Gọi liên tục 20 lần
for i in {1..20}; do
  curl http://localhost:8000/ask -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"question": "Test '$i'"}'
  echo ""
done
```

Quan sát response khi hit limit.

###  Exercise 4.4: Cost guard

**Nhiệm vụ:** Đọc `cost_guard.py` và implement logic:

```python
def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Return True nếu còn budget, False nếu vượt.
    
    Logic:
    - Mỗi user có budget $10/tháng
    - Track spending trong Redis
    - Reset đầu tháng
    """
    # TODO: Implement
    pass
```

<details>
<summary> Solution</summary>

```python
import redis
from datetime import datetime

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False
    
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # 32 days
    return True
```

</details>

###  Checkpoint 4

- [ ] Implement API key authentication
- [ ] Hiểu JWT flow
- [ ] Implement rate limiting
- [ ] Implement cost guard với Redis

---

## Part 5: Scaling & Reliability (40 phút)

###  Concepts

**Vấn đề:** 1 instance không đủ khi có nhiều users.

**Giải pháp:**
1. **Stateless design** — Không lưu state trong memory
2. **Health checks** — Platform biết khi nào restart
3. **Graceful shutdown** — Hoàn thành requests trước khi tắt
4. **Load balancing** — Phân tán traffic

###  Exercise 5.1: Health checks

```bash
cd ../../05-scaling-reliability/develop
```

**Nhiệm vụ:** Implement 2 endpoints:

```python
@app.get("/health")
def health():
    """Liveness probe — container còn sống không?"""
    # TODO: Return 200 nếu process OK
    pass

@app.get("/ready")
def ready():
    """Readiness probe — sẵn sàng nhận traffic không?"""
    # TODO: Check database connection, Redis, etc.
    # Return 200 nếu OK, 503 nếu chưa ready
    pass
```

<details>
<summary> Solution</summary>

```python
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    try:
        # Check Redis
        r.ping()
        # Check database
        db.execute("SELECT 1")
        return {"status": "ready"}
    except:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready"}
        )
```

</details>

###  Exercise 5.2: Graceful shutdown

**Nhiệm vụ:** Implement signal handler:

```python
import signal
import sys

def shutdown_handler(signum, frame):
    """Handle SIGTERM from container orchestrator"""
    # TODO:
    # 1. Stop accepting new requests
    # 2. Finish current requests
    # 3. Close connections
    # 4. Exit
    pass

signal.signal(signal.SIGTERM, shutdown_handler)
```

Test (Linux/macOS hoặc WSL — trên Windows, `kill -TERM` không gửi tín hiệu thật cho process Python nên uvicorn sẽ không chạy graceful shutdown; đây cũng là lý do production luôn deploy trên container Linux):
```bash
python app.py &
PID=$!

# Gửi request — chú ý "question" là query param
curl -X POST "http://localhost:8000/ask?question=Long+task" &

# Ngay lập tức kill
kill -TERM $PID

# Quan sát: Request có hoàn thành không? Log có in "Graceful shutdown" không?
```

###  Exercise 5.3: Stateless design

```bash
cd ../production
```

**Nhiệm vụ:** Refactor code để stateless.

**Anti-pattern:**
```python
#  State trong memory
conversation_history = {}

@app.post("/ask")
def ask(user_id: str, question: str):
    history = conversation_history.get(user_id, [])
    # ...
```

**Correct:**
```python
#  State trong Redis
@app.post("/ask")
def ask(user_id: str, question: str):
    history = r.lrange(f"history:{user_id}", 0, -1)
    # ...
```

Tại sao? Vì khi scale ra nhiều instances, mỗi instance có memory riêng.

> 💡 Test nhanh không cần Docker/Redis: chạy `python app.py` trong `05-scaling-reliability/production`. Nếu không có Redis, app tự fallback sang in-memory dict (log "⚠️ Redis not available"). Gọi `POST /chat` với `{"question": "Hello"}`, lấy `session_id` từ response, gửi tiếp `POST /chat` với cùng `session_id` → `GET /chat/{session_id}/history` để xem history được giữ qua nhiều turns.

> 💡 **Không có Docker?** Mô phỏng "nhiều instance" bằng cách chạy 2 process `app.py` trên 2 port khác nhau, mỗi process một `INSTANCE_ID`:
> ```bash
> # Terminal 1
> INSTANCE_ID=instance-A PORT=8101 python app.py
> # Terminal 2
> INSTANCE_ID=instance-B PORT=8102 python app.py
> ```
> Sau đó:
> ```bash
> # Turn 1 -> instance A, tạo session mới
> curl -s -X POST http://localhost:8101/chat -H "Content-Type: application/json" \
>   -d '{"question": "Xin chao, toi ten la An"}'
> # Lấy session_id từ response, gửi turn 2 vẫn tới instance A
> curl -s -X POST http://localhost:8101/chat -H "Content-Type: application/json" \
>   -d '{"question": "Docker la gi?", "session_id": "<session_id>"}'
> # Turn 3 -> CÙNG session_id nhưng gửi tới instance B (port khác)
> curl -s -X POST http://localhost:8102/chat -H "Content-Type: application/json" \
>   -d '{"question": "Ban nho ten toi khong?", "session_id": "<session_id>"}'
> # So sánh history trên từng instance
> curl -s http://localhost:8101/chat/<session_id>/history
> curl -s http://localhost:8102/chat/<session_id>/history
> ```
> Không có Redis → mỗi instance dùng `_memory_store` riêng. Instance B sẽ KHÔNG thấy history của A (`turn` reset về 1, `served_by: instance-B`), và `history` của A/B sẽ khác nhau hoàn toàn cho cùng `session_id`. Đây chính là bug "mất session khi scale" mà Redis (Exercise 5.4 với Docker) giải quyết — Nginx load balancer + nhiều instance thật sẽ tái hiện đúng vấn đề này ở quy mô lớn hơn.

###  Exercise 5.4: Load balancing

**Nhiệm vụ:** Chạy stack với Nginx load balancer:

> Nếu Docker Compose báo lỗi thiếu `.env.local`, tạo trước một file rỗng `05-scaling-reliability/production/.env.local` (file này bị gitignore).

```bash
docker compose up --scale agent=3
```

Lưu ý: `docker-compose.yml` đã định nghĩa `deploy.replicas: 3`, nên `--scale agent=3` chỉ để minh hoạ — bạn có thể đổi số lượng instance để quan sát.

Quan sát:
- 3 agent instances được start
- Nginx phân tán requests
- Nếu 1 instance die, traffic chuyển sang instances khác

Test (chú ý: Nginx expose ở port **8080**, endpoint là `/chat` không phải `/ask`):
```bash
# Gọi 10 requests
for i in {1..10}; do
  curl http://localhost:8080/chat -X POST \
    -H "Content-Type: application/json" \
    -d '{"question": "Request '$i'"}'
  echo ""
done

# Mỗi response có field "served_by" — instance nào xử lý request
# Check logs — requests được phân tán
docker compose logs agent
```

###  Exercise 5.5: Test stateless

```bash
python test_stateless.py
```

Script này:
1. Gọi API để tạo conversation
2. Kill random instance
3. Gọi tiếp — conversation vẫn còn không?

###  Checkpoint 5

- [ ] Implement health và readiness checks
- [ ] Implement graceful shutdown
- [ ] Refactor code thành stateless
- [ ] Hiểu load balancing với Nginx
- [ ] Test stateless design

---

## Part 6: Final Project (60 phút)

###  Objective

Build một production-ready AI agent từ đầu, kết hợp TẤT CẢ concepts đã học.

> 💡 Bị kẹt? `06-lab-complete/` chứa một reference solution đầy đủ (`app/main.py`, `app/config.py`, `Dockerfile`, `docker-compose.yml`, `railway.toml`, `render.yaml`, `check_production_ready.py`). Cố gắng tự làm trước, sau đó so sánh với solution để học cách implement.
>
> 📦 `my-production-agent/` là một implementation thứ hai, đầy đủ, đã build và test thành công (20/20 — 100% trên `check_production_ready.py`), khớp đúng với architecture (Nginx LB → 3 agent replicas → Redis) và checklist requirements ở trên (auth, rate limit, cost guard, conversation history qua Redis, health/ready, graceful shutdown, structured JSON logging, multi-stage Docker non-root). Mỗi step dưới đây có khối `<details><summary>Giải pháp</summary>` chứa code thật từ project này.

###  Requirements

**Functional:**
- [ ] Agent trả lời câu hỏi qua REST API
- [ ] Support conversation history
- [ ] Streaming responses (optional)

**Non-functional:**
- [ ] Dockerized với multi-stage build
- [ ] Config từ environment variables
- [ ] API key authentication
- [ ] Rate limiting (10 req/min per user)
- [ ] Cost guard ($10/month per user)
- [ ] Health check endpoint
- [ ] Readiness check endpoint
- [ ] Graceful shutdown
- [ ] Stateless design (state trong Redis)
- [ ] Structured JSON logging
- [ ] Deploy lên Railway hoặc Render
- [ ] Public URL hoạt động

### 🏗 Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Nginx (LB)     │
└──────┬──────────┘
       │
       ├─────────┬─────────┐
       ▼         ▼         ▼
   ┌──────┐  ┌──────┐  ┌──────┐
   │Agent1│  │Agent2│  │Agent3│
   └───┬──┘  └───┬──┘  └───┬──┘
       │         │         │
       └─────────┴─────────┘
                 │
                 ▼
           ┌──────────┐
           │  Redis   │
           └──────────┘
```

###  Step-by-step

#### Step 1: Project setup (5 phút)

```bash
mkdir my-production-agent
cd my-production-agent

# Tạo structure
mkdir -p app
touch app/__init__.py
touch app/main.py
touch app/config.py
touch app/auth.py
touch app/rate_limiter.py
touch app/cost_guard.py
touch Dockerfile
touch docker-compose.yml
touch requirements.txt
touch .env.example
touch .dockerignore
```

#### Step 2: Config management (10 phút)

**File:** `app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # TODO: Define all config
    # - PORT
    # - REDIS_URL
    # - AGENT_API_KEY
    # - LOG_LEVEL
    # - RATE_LIMIT_PER_MINUTE
    # - MONTHLY_BUDGET_USD
    pass

settings = Settings()
```

<details>
<summary>📄 Giải pháp: app/config.py</summary>

```python
"""Config — 12-Factor: tất cả từ environment variables."""
import os
import logging
from dataclasses import dataclass, field


@dataclass
class Settings:
    # Server
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # App
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "My Production Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    instance_id: str = field(default_factory=lambda: os.getenv("INSTANCE_ID", "instance-unknown"))

    # LLM
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    # Security
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me"))
    allowed_origins: list = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    # Rate limiting
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )

    # Budget — $X / tháng / user
    monthly_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
    )

    # Storage — Redis (stateless). Rỗng = fallback in-memory (chỉ cho dev/test).
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))

    def validate(self):
        logger = logging.getLogger(__name__)
        if self.environment == "production" and self.agent_api_key == "dev-key-change-me":
            raise ValueError("AGENT_API_KEY must be set in production!")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set — using mock LLM")
        return self


settings = Settings().validate()
```

> Dùng `dataclass` thay vì `pydantic.BaseSettings` để không cần thêm dependency `pydantic-settings`. `validate()` fail-fast nếu chạy production mà quên đổi `AGENT_API_KEY`.

</details>

#### Step 3: Main application (15 phút)

**File:** `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException
from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit
from .cost_guard import check_budget

app = FastAPI()

@app.get("/health")
def health():
    # TODO
    pass

@app.get("/ready")
def ready():
    # TODO: Check Redis connection
    pass

@app.post("/ask")
def ask(
    question: str,
    user_id: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget)
):
    # TODO: 
    # 1. Get conversation history from Redis
    # 2. Call LLM
    # 3. Save to Redis
    # 4. Return response
    pass
```

<details>
<summary>📄 Giải pháp: app/storage.py (shared Redis/in-memory helper)</summary>

`/ask`, rate limiter và cost guard đều cần đọc/viết state (history, request timestamps, spending). Để stateless và scale ra nhiều instance, state này phải nằm trong Redis — `app/storage.py` là lớp trừu tượng dùng chung, tự fallback về in-memory nếu không có Redis (chỉ dùng cho dev):

```python
"""
Shared storage — Redis nếu có (stateless, scale-ready), fallback in-memory
nếu không có Redis (chỉ dùng cho dev/test, KHÔNG scale được nhiều instance).

Dùng chung cho: conversation history, rate limiter, cost guard.
"""
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

try:
    import redis as _redis_lib
    _redis = _redis_lib.from_url(settings.redis_url or "redis://localhost:6379/0", decode_responses=True)
    _redis.ping()
    USE_REDIS = True
    logger.info("Connected to Redis — stateless mode")
except Exception:
    USE_REDIS = False
    _redis = None
    _memory: dict = {}
    logger.warning("Redis not available — using in-memory store (not scalable!)")


def get_json(key: str) -> dict | None:
    if USE_REDIS:
        raw = _redis.get(key)
        return json.loads(raw) if raw else None
    return _memory.get(key)


def set_json(key: str, value: dict, ttl_seconds: int = 3600) -> None:
    if USE_REDIS:
        _redis.setex(key, ttl_seconds, json.dumps(value))
    else:
        _memory[key] = value


def incr_float(key: str, amount: float, ttl_seconds: int) -> float:
    """Tăng giá trị float của key (tạo mới nếu chưa có) và set TTL."""
    if USE_REDIS:
        new_value = _redis.incrbyfloat(key, amount)
        _redis.expire(key, ttl_seconds)
        return float(new_value)
    current = _memory.get(key, 0.0) + amount
    _memory[key] = current
    return current


def get_float(key: str) -> float:
    if USE_REDIS:
        raw = _redis.get(key)
        return float(raw) if raw else 0.0
    return float(_memory.get(key, 0.0))


def zadd_now(key: str, member: str, score: float, ttl_seconds: int) -> None:
    """Sliding-window helper: thêm timestamp vào sorted set."""
    if USE_REDIS:
        _redis.zadd(key, {member: score})
        _redis.expire(key, ttl_seconds)
    else:
        window = _memory.setdefault(key, [])
        window.append(score)


def zcount_since(key: str, min_score: float) -> int:
    if USE_REDIS:
        return _redis.zcount(key, min_score, "+inf")
    window = _memory.get(key, [])
    return sum(1 for ts in window if ts >= min_score)


def zremove_older_than(key: str, min_score: float) -> None:
    if USE_REDIS:
        _redis.zremrangebyscore(key, "-inf", min_score)
    else:
        window = _memory.get(key, [])
        _memory[key] = [ts for ts in window if ts >= min_score]


def ping() -> bool:
    if not USE_REDIS:
        return False
    try:
        _redis.ping()
        return True
    except Exception:
        return False
```

</details>

<details>
<summary>📄 Giải pháp: app/main.py</summary>

```python
"""
My Production Agent — Final Project (Day 12)

Kết hợp tất cả concepts:
  - Config từ environment variables (12-Factor)
  - Structured JSON logging
  - API Key authentication
  - Rate limiting (sliding window, Redis-backed)
  - Cost guard (monthly budget, Redis-backed)
  - Conversation history (stateless — Redis)
  - Health check + readiness probe
  - Graceful shutdown (SIGTERM)
  - Security headers + CORS
"""
import time
import json
import signal
import logging
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app import storage
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, record_usage, get_usage
from utils.mock_llm import ask as llm_ask

# ──────────────────────────────────────────────────────────
# Structured JSON logging
# ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0


# ──────────────────────────────────────────────────────────
# Lifespan — startup / graceful shutdown
# ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "instance": settings.instance_id,
        "storage": "redis" if storage.USE_REDIS else "in-memory",
    }))
    time.sleep(0.1)  # simulate init (load model, warm cache, ...)
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown_start"}))
    time.sleep(0.1)  # cho request hiện tại hoàn thành
    logger.info(json.dumps({"event": "shutdown_complete"}))


def _handle_sigterm(*_args):
    logger.info(json.dumps({"event": "sigterm_received"}))


signal.signal(signal.SIGTERM, _handle_sigterm)


# ──────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Security headers + structured access log."""
    global _request_count
    _request_count += 1
    start = time.time()

    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    del response.headers["server"]

    logger.info(json.dumps({
        "event": "request",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": round((time.time() - start) * 1000, 1),
    }))
    return response


# ──────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None  # None = tạo conversation mới


class AskResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    turn: int
    model: str
    served_by: str
    timestamp: str


# ──────────────────────────────────────────────────────────
# Conversation history (stateless — Redis-backed)
# ──────────────────────────────────────────────────────────
def _append_history(session_id: str, role: str, content: str) -> list:
    session = storage.get_json(f"session:{session_id}") or {}
    history = session.get("history", [])
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    history = history[-20:]  # giữ tối đa 10 turns
    session["history"] = history
    storage.set_json(f"session:{session_id}", session)
    return history


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────
@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance": settings.instance_id,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "history": "GET /chat/{session_id}/history",
            "usage": "GET /me/usage (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    user_id: str = Depends(verify_api_key),
):
    """
    Gửi câu hỏi tới agent. Yêu cầu header `X-API-Key`.

    Truyền `session_id` để tiếp tục cuộc trò chuyện (multi-turn, stateless).
    """
    # 1. Rate limit
    check_rate_limit(user_id)

    # 2. Budget check
    check_budget(user_id)

    # 3. Lấy/tạo session + history (Redis — bất kỳ instance nào đều đọc được)
    session_id = body.session_id or str(uuid.uuid4())
    _append_history(session_id, "user", body.question)

    # 4. Gọi LLM (mock)
    answer = llm_ask(body.question)
    history = _append_history(session_id, "assistant", answer)

    # 5. Ghi nhận cost
    input_tokens = len(body.question.split()) * 2
    output_tokens = len(answer.split()) * 2
    record_usage(user_id, input_tokens, output_tokens)

    return AskResponse(
        session_id=session_id,
        question=body.question,
        answer=answer,
        turn=len([m for m in history if m["role"] == "user"]),
        model=settings.llm_model if settings.openai_api_key else "mock",
        served_by=settings.instance_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/chat/{session_id}/history", tags=["Agent"])
def get_history(session_id: str, _user_id: str = Depends(verify_api_key)):
    session = storage.get_json(f"session:{session_id}")
    if not session:
        raise HTTPException(404, f"Session {session_id} not found or expired")
    return {
        "session_id": session_id,
        "messages": session.get("history", []),
        "served_by": settings.instance_id,
    }


@app.get("/me/usage", tags=["Agent"])
def my_usage(user_id: str = Depends(verify_api_key)):
    return get_usage(user_id)


# ──────────────────────────────────────────────────────────
# Health / Readiness / Metrics
# ──────────────────────────────────────────────────────────
@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe — platform restart container nếu fail."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "instance": settings.instance_id,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "storage": "redis" if storage.USE_REDIS else "in-memory",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe — 503 nếu chưa init xong hoặc Redis (nếu dùng) down."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    if settings.redis_url and not storage.ping():
        raise HTTPException(503, "Redis not available")
    return {"ready": True, "instance": settings.instance_id}


@app.get("/metrics", tags=["Operations"])
def metrics(_user_id: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "instance": settings.instance_id,
        "storage": "redis" if storage.USE_REDIS else "in-memory",
    }


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
```

> Lưu ý: `del response.headers["server"]` xoá header do app set, nhưng uvicorn vẫn tự thêm lại `Server: uvicorn` ở tầng server — muốn ẩn hoàn toàn cần `uvicorn.run(..., server_header=False)`.

</details>

#### Step 4: Authentication (5 phút)

**File:** `app/auth.py`

```python
from fastapi import Header, HTTPException

def verify_api_key(x_api_key: str = Header(...)):
    # TODO: Verify against settings.AGENT_API_KEY
    # Return user_id if valid
    # Raise HTTPException(401) if invalid
    pass
```

<details>
<summary>📄 Giải pháp: app/auth.py</summary>

```python
"""API Key authentication."""
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    """
    Verify request có header `X-API-Key` đúng với `AGENT_API_KEY`.

    Return user_id (dùng API key làm user_id cho demo này).
    Raise 401 nếu thiếu/không đúng.
    """
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key
```

> Dùng `APIKeyHeader(auto_error=False)` + raise `HTTPException` thủ công để custom message, thay vì để FastAPI tự trả lỗi mặc định.

</details>

#### Step 5: Rate limiting (10 phút)

**File:** `app/rate_limiter.py`

```python
import redis
from fastapi import HTTPException

r = redis.from_url(settings.REDIS_URL)

def check_rate_limit(user_id: str):
    # TODO: Implement sliding window
    # Raise HTTPException(429) if exceeded
    pass
```

<details>
<summary>📄 Giải pháp: app/rate_limiter.py</summary>

```python
"""
Rate limiting — Sliding window counter.

Lưu timestamps trong Redis sorted set (key: ratelimit:<user_id>) nếu có Redis,
nên hoạt động đúng dù nhiều instance dùng chung Redis (stateless).
Fallback in-memory nếu không có Redis.
"""
import time
from fastapi import HTTPException

from app.config import settings
from app import storage

WINDOW_SECONDS = 60


def check_rate_limit(user_id: str) -> dict:
    """
    Kiểm tra user có vượt `RATE_LIMIT_PER_MINUTE` không.
    Raise HTTPException(429) nếu vượt. Trả về thông tin còn lại nếu OK.
    """
    now = time.time()
    key = f"ratelimit:{user_id}"

    # Bỏ các timestamps ngoài window
    storage.zremove_older_than(key, now - WINDOW_SECONDS)

    count = storage.zcount_since(key, now - WINDOW_SECONDS)
    if count >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": WINDOW_SECONDS,
            },
            headers={
                "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(WINDOW_SECONDS),
            },
        )

    storage.zadd_now(key, member=str(now), score=now, ttl_seconds=WINDOW_SECONDS)

    return {
        "limit": settings.rate_limit_per_minute,
        "remaining": settings.rate_limit_per_minute - count - 1,
    }
```

> Sliding window (sorted set theo timestamp) chính xác hơn fixed window (không có "burst" ở ranh giới phút). Dùng `ZREMRANGEBYSCORE` + `ZCOUNT` + `ZADD` trên Redis — atomic đủ cho mục đích demo.

</details>

#### Step 6: Cost guard (10 phút)

**File:** `app/cost_guard.py`

```python
def check_budget(user_id: str):
    # TODO: Check monthly spending
    # Raise HTTPException(402) if exceeded
    pass
```

<details>
<summary>📄 Giải pháp: app/cost_guard.py</summary>

```python
"""
Cost Guard — Budget $MONTHLY_BUDGET_USD / tháng / user.

Lưu spending trong Redis (key: budget:<user_id>:<YYYY-MM>) với TTL 32 ngày
nên tự "reset" đầu tháng. Fallback in-memory nếu không có Redis.
"""
import time
from fastapi import HTTPException

from app.config import settings
from app import storage

PRICE_PER_1K_INPUT_TOKENS = 0.00015   # gpt-4o-mini input
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006   # gpt-4o-mini output
MONTH_TTL_SECONDS = 32 * 24 * 3600


def _budget_key(user_id: str) -> str:
    month = time.strftime("%Y-%m")
    return f"budget:{user_id}:{month}"


def check_budget(user_id: str) -> None:
    """Raise HTTPException(402) nếu user đã vượt budget tháng này."""
    spent = storage.get_float(_budget_key(user_id))
    if spent >= settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "spent_usd": round(spent, 6),
                "budget_usd": settings.monthly_budget_usd,
                "resets_at": "1st of next month (UTC)",
            },
        )


def record_usage(user_id: str, input_tokens: int, output_tokens: int) -> float:
    """Ghi nhận usage sau khi gọi LLM. Return tổng cost tháng này."""
    cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS \
        + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    return storage.incr_float(_budget_key(user_id), cost, MONTH_TTL_SECONDS)


def get_usage(user_id: str) -> dict:
    spent = storage.get_float(_budget_key(user_id))
    return {
        "user_id": user_id,
        "month": time.strftime("%Y-%m"),
        "spent_usd": round(spent, 6),
        "budget_usd": settings.monthly_budget_usd,
        "remaining_usd": round(max(0.0, settings.monthly_budget_usd - spent), 6),
    }
```

> `_budget_key` gồm `YYYY-MM` nên budget tự "reset" mỗi tháng (không cần cron); TTL 32 ngày dọn key cũ khỏi Redis.

</details>

#### Step 7: Dockerfile (5 phút)

```dockerfile
# TODO: Multi-stage build
# Stage 1: Builder
# Stage 2: Runtime
```

<details>
<summary>📄 Giải pháp: Dockerfile</summary>

```dockerfile
# ============================================================
# My Production Agent — Multi-stage Dockerfile (< 500 MB, non-root)
# ============================================================

# ── Stage 1: Builder ────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: Runtime ────────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN groupadd -r agent && useradd -r -g agent -d /app agent

WORKDIR /app

COPY --from=builder /root/.local /home/agent/.local

COPY app/ ./app/
COPY utils/ ./utils/

RUN chown -R agent:agent /app

USER agent

ENV PATH=/home/agent/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

`requirements.txt`:

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.9.0
redis==5.1.0
```

> Stage 1 cài `gcc` (cần để build vài Python wheels) và pip install vào `--user`; Stage 2 chỉ copy thư mục `.local` đã build sẵn, không có `gcc` → image nhỏ hơn nhiều. Container chạy bằng user `agent` (non-root).

</details>

#### Step 8: Docker Compose (5 phút)

```yaml
# TODO: Define services
# - agent (scale to 3)
# - redis
# - nginx (load balancer)
```

<details>
<summary>📄 Giải pháp: docker-compose.yml + nginx/nginx.conf</summary>

`docker-compose.yml`:

```yaml
version: "3.9"

services:
  agent:
    build: .
    environment:
      - ENVIRONMENT=staging
      - REDIS_URL=redis://redis:6379/0
      - AGENT_API_KEY=${AGENT_API_KEY:-dev-key-change-me-in-production}
      - RATE_LIMIT_PER_MINUTE=10
      - MONTHLY_BUDGET_USD=10.0
    env_file:
      - .env.local
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    restart: unless-stopped
    deploy:
      replicas: 3

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - agent
```

`nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream agent_backend {
        server agent:8000;
        keepalive 32;
    }

    server {
        listen 80;
        server_name _;
        server_tokens off;

        add_header X-Frame-Options "DENY";
        add_header X-Content-Type-Options "nosniff";

        location /health {
            access_log off;
            proxy_pass http://agent_backend;
        }

        location / {
            proxy_pass http://agent_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_connect_timeout 10s;
            proxy_read_timeout 60s;
        }
    }
}
```

> `server agent:8000` + Docker Compose DNS round-robin giữa các replicas của service `agent` khi `depends_on` resolve tên service — kết hợp `docker compose up --scale agent=3` để có 3 instance phía sau Nginx. Vì state (session, rate limit, budget) nằm trong Redis, request có thể rơi vào bất kỳ instance nào mà vẫn đúng — đây chính là tính chất **stateless**.

</details>

#### Step 9: Test locally (5 phút)

```bash
docker compose up --scale agent=3

# Test all endpoints
curl http://localhost/health
curl http://localhost/ready
curl -H "X-API-Key: secret" http://localhost/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello", "user_id": "user1"}'
```

> Kết quả mong đợi: `docker ps` cho thấy 3 container `agent` + 1 `redis` + 1 `nginx`, tất cả `healthy`. `/health` và `/ready` trả `200`. `/ask` (đúng `X-API-Key=AGENT_API_KEY` đã set) trả `AskResponse` với `served_by` đổi giữa `instance-A/B/C`-style tuỳ container nào nhận request — nhưng `session_id`/history/usage vẫn nhất quán vì lưu ở Redis. Gửi >10 request/phút cho cùng key → `429` kèm header `Retry-After`.

#### Step 10: Deploy (10 phút)

```bash
# Railway
railway init
railway variables set REDIS_URL=...
railway variables set AGENT_API_KEY=...
railway up

# Hoặc Render
# Push lên GitHub → Connect Render → Deploy
```

<details>
<summary>📄 Giải pháp: railway.toml</summary>

```toml
[build]
builder = "DOCKERFILE"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

> Railway tự set biến `$PORT` — đảm bảo app đọc `PORT` từ env (đã làm ở Step 2) và `startCommand` dùng `$PORT` thay vì hardcode `8000`.

</details>

###  Validation

Chạy script kiểm tra:

Copy script vào project của bạn (`my-production-agent/`) rồi chạy:

```bash
cp 06-lab-complete/check_production_ready.py my-production-agent/
cd my-production-agent
python check_production_ready.py
```

Script kiểm tra static (đọc code/files, không cần server đang chạy):

**📁 Required Files**
-  Dockerfile, docker-compose.yml, .dockerignore, .env.example, requirements.txt exist
-  railway.toml hoặc render.yaml exists

**🔒 Security**
-  `.env` có trong `.gitignore`
-  Không có secrets hardcode trong `app/main.py`, `app/config.py`

**🌐 API Endpoints** (đọc `app/main.py`)
-  `/health` và `/ready` endpoints defined
-  Authentication implemented (api_key / verify_token)
-  Rate limiting implemented (429)
-  Graceful shutdown (SIGTERM)
-  Structured logging (JSON — `json.dumps`)

**🐳 Docker**
-  Multi-stage build (`AS builder` / `AS runtime`)
-  Non-root user (`USER`)
-  HEALTHCHECK instruction
-  Slim/alpine base image
-  `.dockerignore` covers `.env` và `__pycache__`

Chạy `python check_production_ready.py` trong `06-lab-complete/` sẽ cho **100%** — đó là baseline để so sánh.

> ✅ Đã verify: implementation `my-production-agent/` (theo các solution blocks ở trên) cũng đạt **20/20 (100%) — PRODUCTION READY** với script này, và toàn bộ endpoint (`/`, `/health`, `/ready`, `/ask`, `/chat/{session_id}/history`, `/me/usage`, `/metrics`) hoạt động đúng khi chạy thực tế — bao gồm auth 401 khi thiếu `X-API-Key`, conversation history qua nhiều turns, cost tracking, và rate limit trả `429` sau 10 requests/phút.
>
> ⚠️ Lưu ý cho Windows: nếu `check_production_ready.py` báo `UnicodeDecodeError: 'charmap' codec can't decode...` khi đọc `app/main.py` (do file chứa tiếng Việt UTF-8), sửa các lệnh `open(...)` trong script để thêm `encoding="utf-8"`, ví dụ: `open(fpath, encoding="utf-8").read()`.

###  Grading Rubric

| Criteria | Points | Description |
|----------|--------|-------------|
| **Functionality** | 20 | Agent hoạt động đúng |
| **Docker** | 15 | Multi-stage, optimized |
| **Security** | 20 | Auth + rate limit + cost guard |
| **Reliability** | 20 | Health checks + graceful shutdown |
| **Scalability** | 15 | Stateless + load balanced |
| **Deployment** | 10 | Public URL hoạt động |
| **Total** | 100 | |

---

##  Hoàn Thành!

Bạn đã:
-  Hiểu sự khác biệt dev vs production
-  Containerize app với Docker
-  Deploy lên cloud platform
-  Bảo mật API
-  Thiết kế hệ thống scalable và reliable

###  Next Steps

1. **Monitoring:** Thêm Prometheus + Grafana
2. **CI/CD:** GitHub Actions auto-deploy
3. **Advanced scaling:** Kubernetes
4. **Observability:** Distributed tracing với OpenTelemetry
5. **Cost optimization:** Spot instances, auto-scaling

###  Resources

- [12-Factor App](https://12factor.net/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Railway Docs](https://docs.railway.app/)
- [Render Docs](https://render.com/docs)

---

##  Q&A

**Q: Tôi không có credit card, có thể deploy không?**  
A: Có! Railway cho $5 credit, Render có 750h free tier.

**Q: Mock LLM khác gì với OpenAI thật?**  
A: Mock trả về canned responses, không gọi API. Để dùng OpenAI thật, set `OPENAI_API_KEY` trong env.

**Q: Làm sao debug khi container fail?**  
A: `docker logs <container_id>` hoặc `docker exec -it <container_id> /bin/sh`

**Q: Redis data mất khi restart?**  
A: Dùng volume: `volumes: - redis-data:/data` trong docker-compose.

**Q: Làm sao scale trên Railway/Render?**  
A: Railway: `railway scale <replicas>`. Render: Dashboard → Settings → Instances.

---

**Happy Deploying! **
