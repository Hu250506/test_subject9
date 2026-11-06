# FastAPI Beans ResNet18 동기·비동기 평가 프로젝트

## 1. 환경
- Windows + WSL2 Ubuntu 22.04, Python 3.10 가상환경(`.venv`)
- Docker Desktop / Docker Compose
- Docker: Redis 6379, PostgreSQL 5432
- Python 프로세스: FastAPI(uvicorn), Celery Worker

## 2. 데이터 준비
- 제공 원본 `validation/`의 각 클래스 이미지를 코드 실행용 `dataset/val/`에 배치
- `dataset/train/`, `dataset/val/`, `dataset/test/` 모두 동일 3클래스(`angular_leaf_spot`, `bean_rust`, `healthy`)
- 데이터셋의 공개·배포 권한 확인 후 공유

## 3. 모델 준비
```bash
python -m training.finetune --data dataset --output artifacts/beans_resnet18 --epochs 3 --batch-size 8 --freeze-backbone
```
- 모델 저장: `artifacts/beans_resnet18/`
- `.env`: `MODEL_PATH=artifacts/beans_resnet18`

## 4. 구동 순서
1. `source .venv/bin/activate`
2. `python -m pip install -r requirements.txt` (최초 1회)
3. `docker compose up -d redis postgres`
4. `docker compose exec redis redis-cli ping` 결과 `PONG` 확인
5. 별도 터미널: `celery -A ai.celery_app:celery_app worker --loglevel=info --pool=solo --concurrency=1`
6. 별도 터미널: `uvicorn main:app --reload`
7. 동기 화면: http://127.0.0.1:8000/vision/sync/
8. 비동기 화면: http://127.0.0.1:8000/vision/async/
9. API 문서: http://127.0.0.1:8000/docs

`compose.yaml`에는 `web`, `worker`, `trainer`(Docker 전체 실행용) 서비스도 정의되어 있으나, 이 프로젝트의 검증은 위 순서(Redis·PostgreSQL만 Docker)로 진행했다. 8000 포트 충돌을 피하려면 두 방식을 동시에 실행하지 않는다.

## 5. 확인할 응답
- `/health`: `{"status":"ok"}`
- 동기 POST: `top1`, `all`, `cache_hit`, `inference_ms`
- 비동기 POST: `202`, `job_id`; GET: `status=done`
- PostgreSQL: `image_jobs`에 비동기 작업 기록
  ```bash
  docker compose exec postgres psql -U vision_user -d vision_db -c 'SELECT id, status, top1_label, cache_hit, inference_ms FROM image_jobs ORDER BY id DESC LIMIT 10;'
  ```
- 모의 테스트: `python -m pytest -q tests/test_api.py` (가짜 모델·SQLite 사용, 실환경 검증이 아님)

## 6. 결과물 위치
- 개별 보고서: `reports/01_*.md` ~ `reports/08_*.md`
- 측정 원본: `reports/data/timings.csv` (재측정: `python reports/measure_timings.py`)
- 실행 증빙: `reports/evidence/`
- 학습 결과: `artifacts/beans_resnet18/training_report.json`

## 7. 제출 및 보안
- `.env`, 비밀번호, API 키는 GitHub에 업로드하지 않음 (`.env.example`만 포함)
- 데이터셋·가중치 대용량 파일은 허용된 제출 경로로 별도 전달
- GitHub에서 제외한 파일(`dataset/`, `artifacts/`)은 위 2, 3장의 절차로 준비
