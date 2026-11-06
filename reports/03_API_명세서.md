# API 명세서

## 1. API 목록

| API ID | Method | URL | 요청 형태 | 성공 HTTP | 주요 응답 | 실패 HTTP |
|---|---|---|---|---:|---|---|
| API-01 | GET | `/health` | 없음 | 200 | `status` | 서버 미실행 시 HTTP 응답 없음 |
| API-02 | POST | `/api/sync/classify/` | `multipart/form-data` / `image` | 200 | `model_id`, `top1`, `all`, `inference_ms`, `cache_hit` | 400, 413 |
| API-03 | POST | `/api/async/classify/` | `multipart/form-data` / `image` | 202 | `job_id`, `status`, `check_url` | 400, 413, 503 |
| API-04 | GET | `/api/async/jobs/{job_id}/` | 정수형 `job_id` | 200 | `status`, `top1`, `all`, `inference_ms`, `cache_hit`, `error_message` | 404 |
| WEB-01 | GET | `/vision/sync/` | 없음 | 200 | HTML | — |
| WEB-02 | GET | `/vision/async/` | 없음 | 200 | HTML | — |

공통 규칙: 업로드 파일은 5MB 이하여야 한다. `202`는 작업 접수이고, 분석 완료는 API-04의 `status: done`으로 확인한다.

## 2. API-02 동기 분류

| 항목 | 내용 |
|---|---|
| URL | `/api/sync/classify/` |
| Method | POST |
| Content-Type | `multipart/form-data` |
| 요청 필드 | `image`: 이미지 파일, 5MB 이하 |
| 성공 코드 | 200 OK (분류가 끝난 뒤 반환) |
| 오류 코드 | 400 올바르지 않은 이미지, 413 5MB 초과 |

**성공 응답 (실제 결과, 입력: `healthy_test.1`)**

```json
{
  "model_id": "artifacts/beans_resnet18",
  "top1": {"label": "healthy", "score": 0.8166828155517578},
  "all": [
    {"label": "healthy", "score": 0.8166828155517578},
    {"label": "bean_rust", "score": 0.11441823840141296},
    {"label": "angular_leaf_spot", "score": 0.06889893859624863}
  ],
  "inference_ms": 20.65,
  "cache_hit": false
}
```

**오류 응답 (실제 결과, 입력: 텍스트 파일 `bad.txt`)**

```json
{"detail": "올바른 이미지 파일이 아닙니다."}
```

## 3. API-03 비동기 작업 접수

| 항목 | 내용 |
|---|---|
| URL | `/api/async/classify/` |
| Method | POST |
| 요청 필드 | `image`: 이미지 파일, 5MB 이하 |
| 성공 코드 | 202 Accepted (작업 접수, 분석 완료 아님) |
| 오류 코드 | 400 올바르지 않은 이미지, 413 5MB 초과, 503 작업 큐 등록 실패 |

**성공 응답 (실제 결과, job_id=40)**

```json
{"job_id":40,"status":"queued","check_url":"/api/async/jobs/40/"}
```

**오류 응답 (실제 결과, 입력: 텍스트 파일 `bad.txt`)**

```json
{"detail": "올바른 이미지 파일이 아닙니다."}
```

## 4. API-04 작업 상태 조회

| 항목 | 내용 |
|---|---|
| URL | `/api/async/jobs/{job_id}/` |
| Method | GET |
| 성공 코드 | 200 OK (`status`가 `queued`, `running`, `done`, `failed` 중 하나) |
| 오류 코드 | 404 해당 작업 없음 |

**완료 응답 (실제 결과, job_id=6, 캐시 MISS)**

```json
{
  "job_id": 6,
  "status": "done",
  "model_id": "artifacts/beans_resnet18",
  "top1": {"label": "angular_leaf_spot", "score": 0.5182246565818787},
  "all": [
    {"label": "angular_leaf_spot", "score": 0.5182246565818787},
    {"label": "bean_rust", "score": 0.33965110778808594},
    {"label": "healthy", "score": 0.142124205827713}
  ],
  "inference_ms": 23.53,
  "cache_hit": false,
  "error_message": null
}
```

**캐시 HIT 응답 (실제 결과, job_id=7, 같은 이미지)**

```json
{
  "job_id": 7,
  "status": "done",
  "model_id": "artifacts/beans_resnet18",
  "top1": {"label": "angular_leaf_spot", "score": 0.5182246565818787},
  "all": [
    {"label": "angular_leaf_spot", "score": 0.5182246565818787},
    {"label": "bean_rust", "score": 0.33965110778808594},
    {"label": "healthy", "score": 0.142124205827713}
  ],
  "inference_ms": null,
  "cache_hit": true,
  "error_message": null
}
```

**대기 응답 (실제 결과, job_id=8, Worker 중지 중)**

```json
{"job_id": 8, "status": "queued", "model_id": "artifacts/beans_resnet18", "top1": null, "all": null, "inference_ms": null, "cache_hit": null, "error_message": null}
```

**오류 응답 (실제 결과, job_id=9999999)**

```json
{"detail": "해당 작업이 없습니다."}
```

## 5. 실행 근거표

| 검증 ID      | 테스트 입력                     |      실제 상태코드 | 첨부 증빙                          |
| ---------- | -------------------------- | -----------: | ------------------------------ |
| API-02-T01 | `healthy_test.1` (healthy) |          200 | `evidence/api_sync_200.png`    |
| API-02-T02 | `bad.txt`                  |          400 | `evidence/bad_image_sync.png`  |
| API-03-T01 | 이미지 업로드 (job_id=40)        |          202 | `evidence/api_async_202.png`   |
| API-03-T02 | `bad.txt`                  |          400 | `evidence/bad_image_async.png` |
| API-04-T01 | job_id=6 (Worker 처리 후)     |   200 / done | `evidence/api_job_done.png`    |
| API-04-T02 | job_id=8 (Worker 중지 중)     | 200 / queued | `evidence/worker_stopped.png`  |
| API-04-T03 | job_id=9999999             |          404 | `evidence/api_404.png`         |
| API-01     | GET /health                |          200 | `evidence/health.png`          |

- 413(5MB 초과)과 503(작업 큐 등록 실패)은 코드에 정의되어 있으나 실제 환경에서는 시험하지 않았다. 모의 테스트(`tests/test_api.py`)에서만 다룬다.
- `all`은 API 응답 필드명이고, `all_scores`는 DB 컬럼명이다.
- `inference_ms: null`은 캐시 HIT에서 추론을 생략했다는 뜻이다.
