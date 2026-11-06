import csv, hashlib, mimetypes, statistics, sys, time
from pathlib import Path
import httpx, redis

BASE = "http://127.0.0.1:8000"
IMG = Path(sys.argv[1] if len(sys.argv) > 1 else "dataset/test/angular_leaf_spot/angular_leaf_spot_test.6.jpg")
OUT = Path("reports/data/timings.csv")
cache = redis.Redis.from_url("redis://127.0.0.1:6379/1")
data = IMG.read_bytes()
mime = mimetypes.guess_type(IMG.name)[0] or "image/jpeg"
client = httpx.Client(timeout=60)
rows = []
print("image:", IMG, "| sha256:", hashlib.sha256(data).hexdigest())

def files():
    return {"image": (IMG.name, data, mime)}

def expect(status, j, where):
    if j["cache_hit"] != (status == "HIT"):
        print(f"  !! 경고: {where} 기대={status}, 실제 cache_hit={j['cache_hit']}")

def run_sync(run_id, status, record=True):
    t0 = time.perf_counter()
    resp = client.post(BASE + "/api/sync/classify/", files=files())
    ms = (time.perf_counter() - t0) * 1000
    resp.raise_for_status()
    j = resp.json()
    expect(status, j, f"sync run {run_id}")
    if record:
        rows.append([run_id, "sync", status, round(ms, 2), round(ms, 2), j["inference_ms"], ""])

def run_async(run_id, status, record=True):
    t0 = time.perf_counter()
    resp = client.post(BASE + "/api/async/classify/", files=files())
    http_ms = (time.perf_counter() - t0) * 1000
    resp.raise_for_status()
    job_id = resp.json()["job_id"]
    while True:
        j = client.get(f"{BASE}/api/async/jobs/{job_id}/").json()
        if j["status"] in ("done", "failed"):
            break
        if time.perf_counter() - t0 > 60:
            raise TimeoutError(f"job {job_id} 60초 초과")
        time.sleep(0.05)
    final_ms = (time.perf_counter() - t0) * 1000
    if j["status"] != "done":
        print(f"  !! job {job_id} 상태: {j['status']} {j.get('error_message')}")
    expect(status, j, f"async run {run_id}")
    if record:
        rows.append([run_id, "async", status, round(http_ms, 2), round(final_ms, 2), j["inference_ms"], job_id])

print("[워밍업] run_id=0 (모델 첫 로딩 포함, 비교에서 제외)")
cache.flushdb(); run_sync(0, "MISS")
cache.flushdb(); run_async(0, "MISS")

print("[동기 MISS x5]")
for i in range(1, 6):
    cache.flushdb(); run_sync(i, "MISS")
print("[동기 HIT x5]")
cache.flushdb(); run_sync(0, "MISS", record=False)
for i in range(1, 6):
    run_sync(i, "HIT")
print("[비동기 MISS x5]")
for i in range(1, 6):
    cache.flushdb(); run_async(i, "MISS")
print("[비동기 HIT x5]")
cache.flushdb(); run_async(0, "MISS", record=False)
for i in range(1, 6):
    run_async(i, "HIT")

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["run_id", "path", "cache_status", "http_ms", "final_ms", "inference_ms", "job_id"])
    w.writerows(rows)

def med(path, status, col):
    v = [r[col] for r in rows if r[1] == path and r[2] == status and r[0] != 0 and r[col] not in ("", None)]
    return round(statistics.median(v), 2) if v else None

print("\n=== 중앙값 요약 (ms, 워밍업 제외) ===")
for path, status in [("sync", "MISS"), ("sync", "HIT"), ("async", "MISS"), ("async", "HIT")]:
    print(f"{path:5} {status:4} http={med(path,status,3)}  final={med(path,status,4)}  inference={med(path,status,5)}")
sm, am = med("sync", "MISS", 3), med("async", "MISS", 3)
if sm and am:
    print(f"HTTP 응답시간 감소율(동기 MISS 대비 비동기 MISS 접수) = ({sm} - {am}) / {sm} x 100 = {round((sm-am)/sm*100, 2)}%")
print("저장:", OUT)
