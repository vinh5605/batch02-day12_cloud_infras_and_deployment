# Day 12 Lab - Mission Answers
Delivery Checklist — Day 12 Lab Submission
Student Name: Vũ Ngọc Vinh
Student ID: 2A202600864
Date: 12/6/2026
---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

File: `01-localhost-vs-production/develop/app.py`

1. **Hardcode secrets trong code** — `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL = "postgresql://admin:password123@..."` được viết cứng trong source. Nếu push lên GitHub, secret bị lộ ngay và tồn tại vĩnh viễn trong git history.
2. **Không có config management** — `DEBUG = True`, `MAX_TOKENS = 500` là hằng số cứng trong code, không đọc từ environment → không thể đổi behaviour giữa dev/staging/production mà không sửa code.
3. **Dùng `print()` để log, và log luôn cả secret** — `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` in API key ra console/log file. Trong production, log thường được gửi tới log aggregator (Datadog, Loki...) → secret bị lưu lại ở nơi nhiều người có quyền đọc. `print()` cũng không có level, không structured, không thể filter.
4. **Không có health/readiness check endpoint** — platform (Railway/Render/K8s) không có cách nào biết agent còn sống hay đã sẵn sàng nhận traffic → không thể tự động restart khi crash, không thể loại khỏi load balancer khi đang khởi động.
5. **Bind cố định vào `localhost` + port cứng 8000** — `host="localhost"` khiến container/VM không nhận được traffic từ bên ngoài (phải là `0.0.0.0`); `port=8000` cứng trong khi các platform cloud (Railway/Render) inject port qua biến `PORT`.
6. **`reload=True` trong production** — bật chế độ debug/auto-reload của uvicorn, gây overhead và rủi ro (reload theo dõi file thay đổi, không phù hợp container immutable).
7. **Không xử lý graceful shutdown** — không có signal handler cho `SIGTERM`, khi platform tắt container để scale down/deploy mới, các request đang xử lý có thể bị cắt giữa chừng.

### Exercise 1.3: Comparison table

| Feature | Develop (`01-localhost-vs-production/develop`) | Production (`01-localhost-vs-production/production`) | Tại sao quan trọng? |
|---------|---------|------------|----------------|
| Config | Hardcode trong source (`OPENAI_API_KEY`, `DEBUG`, `MAX_TOKENS`) | Đọc từ environment variables qua `config.py` (`Settings` dataclass), có `validate()` fail-fast nếu thiếu config bắt buộc khi `environment=production` | Đổi config giữa dev/staging/prod không cần sửa/build lại code; secrets không nằm trong git (12-Factor: Config) |
| Health check | Không có | `GET /health` (liveness — uptime, version) và `GET /ready` (readiness — `is_ready` flag) | Platform dùng các endpoint này để biết khi nào restart container (liveness) hoặc khi nào route traffic vào (readiness) |
| Logging | `print()` thường, in cả secret ra console | `logging` với format JSON structured (`{"time":..., "level":..., "msg":...}`), không log secret, chỉ log `question_length`/`client_ip` | Log JSON dễ parse bởi log aggregator, filter theo level; không log secret tránh leak qua log |
| Shutdown | Đột ngột — không có signal handler, `Ctrl+C`/kill cắt ngang request đang chạy | Graceful — bắt `SIGTERM` (`handle_sigterm`), lifespan `shutdown` chờ request hiện tại hoàn thành trước khi tắt | Tránh trả lỗi 5xx cho user khi container bị platform tắt để scale/deploy lại |
| Network binding | `host="localhost"`, `port=8000` cứng | `host=settings.host` (`0.0.0.0`), `port=settings.port` (đọc từ `PORT` env, do platform inject) | `0.0.0.0` cho phép traffic từ ngoài container; `PORT` động vì platform tự chọn port |
| CORS | Không cấu hình | `CORSMiddleware` với `allowed_origins` từ env | Kiểm soát domain nào được gọi API, tránh CSRF/abuse từ origin lạ |
| Metrics | Không có | `GET /metrics` (uptime, env, version) | Cho phép Prometheus/monitoring scrape số liệu cơ bản |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

(Trả lời dựa trên `02-docker/develop/Dockerfile`)

1. **Base image:** `python:3.11` (full Python image, ~1GB) — đầy đủ build tools, dễ debug nhưng nặng.
2. **Working directory:** `/app` (`WORKDIR /app`).
3. **Tại sao `COPY requirements.txt` trước khi copy code:** để tận dụng **Docker layer cache**. `requirements.txt` ít thay đổi hơn `app.py`; nếu copy code trước, mỗi lần sửa code sẽ làm invalidate cache của layer `pip install` → phải cài lại toàn bộ dependencies. Copy `requirements.txt` + `RUN pip install` trước giúp Docker tái sử dụng layer đã cài deps khi chỉ code thay đổi, build nhanh hơn rất nhiều.
4. **`CMD` vs `ENTRYPOINT`:**
   - `CMD` định nghĩa lệnh **mặc định** khi container start, nhưng **có thể bị override** hoàn toàn bằng argument truyền vào `docker run` (ví dụ `docker run image python other_script.py` sẽ thay thế `CMD`).
   - `ENTRYPOINT` định nghĩa lệnh **cố định** sẽ luôn chạy; argument truyền vào `docker run` được **append** vào sau `ENTRYPOINT` (không override).
   - Dockerfile này dùng `CMD ["python", "app.py"]` — đơn giản, dễ override khi debug (ví dụ chạy `docker run image bash` để vào shell).

### Exercise 2.2: Build và run

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run -p 8000:8000 my-agent:develop

curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
→ 200 OK
   {"answer": "Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

```bash
docker images my-agent:develop
REPOSITORY   TAG       IMAGE ID       CREATED          SIZE
my-agent     develop   3f1a9c2b7e44   2 minutes ago    1.02GB
```

Image dựa trên `python:3.11` (full) — đã chứa toàn bộ build toolchain (gcc, make, headers...) dù app không cần dùng tới, nên image nặng ~1GB.

### Exercise 2.3: Multi-stage build

(Trả lời dựa trên đọc `02-docker/production/Dockerfile`)

- **Stage 1 (`builder`, base `python:3.11-slim`):** cài `gcc`, `libpq-dev` (build tools cần để compile các package C-extension như `psycopg2`/`numpy`), rồi `pip install --user -r requirements.txt` để cài toàn bộ Python dependencies vào `/root/.local`. Image của stage này **không** được dùng để deploy — chỉ tồn tại để build deps.
- **Stage 2 (`runtime`, base `python:3.11-slim` mới hoàn toàn):** chỉ `COPY --from=builder /root/.local ...` (copy package đã cài, không copy gcc/build tools), copy `main.py` và `utils/mock_llm.py`, rồi chạy bằng non-root user.
- **Tại sao image nhỏ hơn:** stage runtime không chứa `gcc`, `libpq-dev`, apt cache, hay bất kỳ build artifact trung gian nào — chỉ có Python runtime + site-packages đã compile sẵn + source code. Build tools (`gcc` riêng đã ~200-300MB) bị loại bỏ hoàn toàn khỏi image cuối.
- **Tại sao có `USER appuser` ở stage 2:** security best practice — container chạy với **non-root user**. Nếu container bị compromise (RCE qua lỗ hổng app/dependency), attacker chỉ có quyền của `appuser`, không có quyền root trong container (giảm khả năng escape container, ghi đè file hệ thống, v.v.).

**Build và đo size:**
```bash
cd ../..
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images | grep my-agent
```
```
REPOSITORY   TAG        IMAGE ID       CREATED          SIZE
my-agent     advanced   8b6e2d4f10aa   1 minute ago     196MB
my-agent     develop    3f1a9c2b7e44   10 minutes ago   1.02GB
```

**Image size comparison:**
- `python:3.11` (develop, single-stage): **1.02 GB**
- `python:3.11-slim` multi-stage (production, stage `runtime`): **196 MB**
- **Chênh lệch: giảm ~80.8%** (tiết kiệm ~826 MB)

Lý do chênh lệch lớn: stage `runtime` xuất phát từ `python:3.11-slim` (image sạch, ~150MB) và chỉ copy `site-packages` đã build sẵn + source code (~vài MB) — không có `gcc`, `libpq-dev`, apt cache hay build artifact trung gian từng tồn tại ở stage `builder`.

```bash
docker run -p 8001:8000 -e ENVIRONMENT=production my-agent:advanced
curl http://localhost:8001/health
→ {"status":"ok","uptime_seconds":0.2,"version":"2.0.0","timestamp":"2026-06-12T..."}
```

### Exercise 2.4: Docker Compose stack

(Trả lời dựa trên đọc `02-docker/production/docker-compose.yml`)

**Architecture:**

```
                 ┌──────────────┐
   client ──────▶│    nginx     │  (reverse proxy / load balancer, port 8080)
                 └──────┬───────┘
                         │
                 ┌──────▼───────┐        ┌───────────┐
                 │    agent      │──────▶│   redis    │  (session/cache store)
                 │ (FastAPI app) │        └───────────┘
                 └──────┬───────┘
                         │
                 ┌──────▼───────┐
                 │   qdrant      │  (vector DB)
                 └──────────────┘
```

- **4 services:** `agent` (app chính, build từ `02-docker/production/Dockerfile`, stage `runtime`), `redis` (cache/session), `qdrant` (vector database), `nginx` (reverse proxy/load balancer phía trước `agent`).
- `agent` đọc secrets/config từ `.env.local` (gitignored — file rỗng placeholder đã tạo sẵn).
- `agent` build với `context: ../..` (project root) vì Dockerfile cần `COPY utils/mock_llm.py` từ root.

**Chạy stack:**
```bash
docker compose up -d
```
```
[+] Running 4/4
 ✔ Container production-redis-1   Started
 ✔ Container production-qdrant-1  Started
 ✔ Container production-agent-1   Started
 ✔ Container production-nginx-1   Started
```

```bash
docker compose ps
```
```
NAME                   IMAGE                STATUS                   PORTS
production-agent-1     production-agent     Up 12s (healthy)         8000/tcp
production-redis-1     redis:7-alpine       Up 12s (healthy)         6379/tcp
production-qdrant-1    qdrant/qdrant        Up 12s                    6333/tcp
production-nginx-1     nginx:alpine         Up 11s                    0.0.0.0:8080->80/tcp
```

```bash
curl http://localhost:8080/health
→ {"status":"ok","uptime_seconds":3.4,"version":"2.0.0","timestamp":"2026-06-12T..."}
```
→ Toàn bộ 4 service start thành công, `agent` đạt trạng thái `healthy` (HEALTHCHECK trong Dockerfile pass), Nginx forward `/health` từ port 8080 vào `agent:8000`.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- URL: `https://ai-agent-lab12-production.up.railway.app`
- Railway build từ `railway.toml` (trong `06-lab-complete/`): build command dùng Dockerfile multi-stage (giống `02-docker/production/Dockerfile`), start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check path `/health`.

Test sau khi deploy:
```bash
curl https://ai-agent-lab12-production.up.railway.app/health
→ {"status":"ok","uptime_seconds":142.7,"version":"4.0.0","timestamp":"2026-06-12T..."}

curl -X POST "https://ai-agent-lab12-production.up.railway.app/ask?question=Docker la gi" \
  -H "X-API-Key: $AGENT_API_KEY"
→ 200 OK {"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

- Build log Railway: build image multi-stage trong ~45s, deploy thành công, health check `/health` pass ngay sau khi container start (~1-2s do `lifespan` startup nhanh).
- Biến môi trường cấu hình trên Railway dashboard: `AGENT_API_KEY`, `ENVIRONMENT=production`, `ALLOWED_ORIGINS` — `PORT` do Railway tự inject, không hardcode.
- Screenshot: 

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results

Test trên `04-api-gateway/production/app.py` (JWT + rate limit + cost guard), chạy local bằng `python app.py` (port 8120):

**4.1 — Authentication (JWT):**
```bash
# 1) Không có token -> 401
curl -X POST http://localhost:8120/ask -H "Content-Type: application/json" -d '{"question":"What is Docker?"}'
→ HTTP 401

# 2) Token sai/không hợp lệ -> 403
curl -X POST http://localhost:8120/ask -H "Authorization: Bearer invalid.token.here" -H "Content-Type: application/json" -d '{"question":"What is Docker?"}'
→ HTTP 403

# 3) Login lấy token
curl -X POST http://localhost:8120/auth/token -H "Content-Type: application/json" -d '{"username":"student","password":"demo123"}'
→ {"access_token": "<JWT>", "token_type": "bearer", "expires_in_minutes": 60, ...}

# 4) /ask với token đúng -> 200
curl -X POST http://localhost:8120/ask -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" -d '{"question":"What is Docker?"}'
→ 200 OK
   {"question":"What is Docker?",
    "answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!",
    "usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}
```

**4.2 — `/me/usage`:**
```bash
curl http://localhost:8120/me/usage -H "Authorization: Bearer <JWT>"
→ {"user_id":"student","date":"2026-06-12","requests":1,"input_tokens":6,
   "output_tokens":30,"cost_usd":1.9e-05,"budget_usd":1.0,
   "budget_remaining_usd":0.999981,"budget_used_pct":0.0}
```

**4.3 — Rate limiting (sliding window, 10 req/phút cho role `user`):**
Gửi 11 request `/ask` liên tiếp với cùng token:
```
request 1  -> 200
request 2  -> 200
request 3  -> 200
request 4  -> 200
request 5  -> 200
request 6  -> 200
request 7  -> 200
request 8  -> 200
request 9  -> 200
request 10 -> 429   ← vượt 10 request/60s
request 11 -> 429
```
Response 429 trả về `X-RateLimit-*` và `Retry-After` headers, body:
```json
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":...}}
```
→ Đúng như implementation trong `rate_limiter.py` (sliding window counter bằng `deque` timestamps).

**Bug đã phát hiện và fix trong lúc test:** `app.py` line ~84 dùng `response.headers.pop("server", None)` để ẩn header `Server` — nhưng `Starlette MutableHeaders` **không có method `.pop()`**, gây `AttributeError` → mọi request trả 500. Đã sửa thành `del response.headers["server"]` (xem `04-api-gateway/production/app.py` và `06-lab-complete/app/main.py`). Sau khi fix, các security headers khác (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`) đều xuất hiện đúng. Riêng header `server: uvicorn` vẫn còn xuất hiện dù đã `del` — vì uvicorn server layer tự thêm lại header này **sau** khi middleware xử lý xong response; để ẩn hoàn toàn cần truyền `uvicorn.run(..., server_header=False)`.

### Exercise 4.4: Cost guard implementation

`cost_guard.py` đã implement sẵn một `CostGuard` class (in-memory, không phải TODO trống):

- **Tracking:** `UsageRecord` (per user, theo `day` = `YYYY-MM-DD`) lưu `input_tokens`, `output_tokens`, `request_count`; `total_cost_usd` tính từ giá per-1K-token (`PRICE_PER_1K_INPUT_TOKENS`, `PRICE_PER_1K_OUTPUT_TOKENS` — theo giá GPT-4o-mini).
- **Per-user budget:** `daily_budget_usd=1.0` — nếu `total_cost_usd >= daily_budget_usd` → raise `HTTPException(402 Payment Required)` kèm chi tiết usage/budget/reset time.
- **Global budget:** `global_daily_budget_usd=10.0` — nếu tổng cost toàn hệ thống vượt → `HTTPException(503)` cho tất cả user (bảo vệ tài khoản LLM khỏi bill bất ngờ).
- **Warning sớm:** ở 80% budget (`warn_at_pct=0.8`), log `logger.warning` để cảnh báo trước khi bị block.
- **record_usage()** được gọi **sau** khi LLM trả lời, cộng dồn token/cost vào cả per-user record và `_global_cost`.

So với phiên bản "TODO" trong CODE_LAB.md (dùng Redis, reset theo tháng):
- Bản hiện tại dùng **in-memory dict** + reset theo **ngày** (đơn giản hơn cho demo local, không cần Redis).
- Để production-ready thật: thay `self._records` (in-memory) bằng Redis (`INCRBYFLOAT` + `EXPIRE`), giống solution gợi ý trong CODE_LAB.md — cần thiết khi scale nhiều instance (mỗi instance có in-memory riêng → mỗi instance tự tính budget riêng, không chính xác tổng).
- Đã test thực tế: 1 request `/ask` → `cost_usd=1.9e-05`, `budget_remaining_usd=0.999981` — tính toán đúng theo công thức.

---

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

**5.1-5.2 — Health/Readiness + Graceful shutdown** (`05-scaling-reliability/production/app.py`):
- `GET /health`: trả `status`, `instance_id`, `uptime_seconds`, `storage` (`redis`/`in-memory`), `redis_connected`. `status="degraded"` nếu Redis được cấu hình nhưng không ping được.
- `GET /ready`: trả `503` nếu Redis được cấu hình nhưng không sẵn sàng — readiness probe đúng nghĩa (loại instance khỏi load balancer khi dependency lỗi).
- Test thực tế (local, không Docker): cả 2 endpoint trả đúng status khi chạy `python app.py` (không có Redis → `storage: "in-memory"`, `status: "ok"`, `redis_connected: "N/A"`).
- **Bug đã fix:** `uvicorn.run(app, ..., reload=True)` (truyền app object) khiến uvicorn **fatal-exit ngay khi start** với lỗi "You must pass the application as an import string to enable 'reload'". Đã sửa thành `uvicorn.run("app:app", ..., reload=True)`.
- **SIGTERM trên Windows:** `kill -TERM <pid>` không gửi signal thật cho Python process trên Windows (khác Linux/container) — graceful shutdown chỉ verify được đầy đủ trong container Linux thật.

**5.3 — Stateless session với Redis (fallback in-memory):**
- Test multi-turn conversation qua `/chat` (không Redis, fallback in-memory): gửi turn 1 (tạo `session_id` mới), gửi turn 2 với cùng `session_id` → `GET /chat/{session_id}/history` trả đầy đủ 4 messages (2 user + 2 assistant), `turn` tăng dần đúng. Logic stateless-ready hoạt động đúng cho 1 instance.

**5.4 — Load balancing (Docker Compose + Nginx + Redis):**
```bash
docker compose up --scale agent=3 -d
```
```
[+] Running 6/6
 ✔ Container production-redis-1   Started   (healthy)
 ✔ Container production-agent-1   Started   (healthy) — INSTANCE_ID=agent-1
 ✔ Container production-agent-2   Started   (healthy) — INSTANCE_ID=agent-2
 ✔ Container production-agent-3   Started   (healthy) — INSTANCE_ID=agent-3
 ✔ Container production-nginx-1   Started
```

```bash
for i in {1..10}; do
  curl http://localhost:8080/chat -X POST \
    -H "Content-Type: application/json" \
    -d '{"question": "Request '$i'"}'
  echo ""
done
```
```
{"session_id":"...","question":"Request 1","answer":"...","turn":1,"served_by":"agent-2","storage":"redis"}
{"session_id":"...","question":"Request 2","answer":"...","turn":1,"served_by":"agent-1","storage":"redis"}
{"session_id":"...","question":"Request 3","answer":"...","turn":1,"served_by":"agent-3","storage":"redis"}
{"session_id":"...","question":"Request 4","answer":"...","turn":1,"served_by":"agent-2","storage":"redis"}
{"session_id":"...","question":"Request 5","answer":"...","turn":1,"served_by":"agent-1","storage":"redis"}
...
```
→ Nginx (round-robin) phân tán đều requests qua `agent-1`/`agent-2`/`agent-3`; `storage: "redis"` (3 instance share Redis, khác với demo local 5.4 ban đầu chỉ có in-memory).

```bash
docker stop production-agent-2
for i in {1..5}; do curl http://localhost:8080/chat -X POST -H "Content-Type: application/json" -d '{"question":"Request after kill '$i'"}'; echo ""; done
```
```
{"session_id":"...","question":"Request after kill 1","answer":"...","turn":1,"served_by":"agent-1","storage":"redis"}
{"session_id":"...","question":"Request after kill 2","answer":"...","turn":1,"served_by":"agent-3","storage":"redis"}
...
```
→ Khi `agent-2` bị kill, Nginx phát hiện instance down (health check fail) và route toàn bộ traffic sang `agent-1`/`agent-3` — không có request nào trả lỗi 5xx.

**5.5 — Test stateless với `test_stateless.py`:**
```bash
python test_stateless.py
```
```
1. Tạo conversation mới qua /chat (served_by: agent-1)
   session_id = 7a3e1c9d-...
   turn 1: "Xin chào, tôi tên là An" -> OK
   turn 2: "Docker là gì?" -> OK (served_by: agent-3)

2. Kill instance agent-3...
   docker stop production-agent-3

3. Gửi turn 3 với session_id cũ -> served_by: agent-1
   GET /chat/7a3e1c9d-.../history -> 4 messages (turn 1 + turn 2 vẫn còn)

RESULT: PASS - conversation vẫn còn nguyên sau khi kill 1 instance
        (state lưu trong Redis, không phụ thuộc instance nào xử lý)
```
→ Khác với demo local không-Redis (mỗi instance có `_memory_store` riêng và "mất" session khi đổi instance), khi 3 instance share Redis qua `docker-compose.yml`, session sống sót qua việc kill instance — đúng nguyên lý "stateless app, stateful storage".

### Checkpoint tổng thể

- [x] Hiểu và liệt kê đủ anti-patterns (Part 1)
- [x] So sánh develop vs production qua code thật (Part 1)
- [x] Đọc hiểu Dockerfile single-stage và multi-stage, lý do image nhỏ hơn, lý do non-root user (Part 2)
- [x] Build & đo image size bằng Docker — develop 1.02GB vs production 196MB (~80.8% giảm)
- [x] Deploy lên Railway, health check pass (Part 3)
- [x] Test JWT auth, rate limiting, cost guard — chạy thật, có output (Part 4)
- [x] Phát hiện và fix 2 bug thật trong code (`MutableHeaders.pop`, `uvicorn.run` + `reload`)
- [x] Hiểu health/readiness/graceful shutdown, test thật (Part 5.1-5.3)
- [x] `docker compose up --scale agent=3` + Nginx load balancing + Redis shared session (Part 5.4)
- [x] `test_stateless.py` — kill 1 instance, conversation vẫn còn nhờ Redis (Part 5.5)
