# ResNet18 콩잎 3클래스 Fine-tuning 결과보고서

- 평가 대상: 콩잎 질병 이미지 3종 분류 (angular_leaf_spot / bean_rust / healthy)
- 기준 모델: microsoft/resnet-18 (1,000개 ImageNet 출력층을 3클래스 출력층으로 교체)
- 학습 방식: Head-only (Backbone freeze)
- 입력 데이터: dataset/train, dataset/val
- 최종 보관 데이터: dataset/test (학습에 사용하지 않음)
- 모델 저장 위치: artifacts/beans_resnet18/
- 실험 상태: 학습 실행 완료, 모델 파일 생성 확인

## 1. 데이터 구성

데이터 출처는 Hugging Face `AI-Lab-Makerere/beans`이며, 제공된 `train` / `validation` / `test` ZIP을 사용했다.

| 클래스 | Train | Validation | Test |
|---|---:|---:|---:|
| angular_leaf_spot | 345 | 44 | 43 |
| bean_rust | 348 | 45 | 43 |
| healthy | 342 | 44 | 42 |
| 합계 | 1,035 | 133 | 128 |

- 위 개수는 `find dataset/<split>/<class> -maxdepth 1 -type f | wc -l`로 센 **파일 수**이다.
- 학습 코드가 실제로 읽은 개수(`training_report.json`): train 1,034 / val 133
- Train healthy 폴더에 확장자가 .120tore인 파일 1개(healthy_train.120tore)가 있으며, 이미지 확장자 필터(training/finetune.py 12행 EXTS)에 해당하지 않아 학습에서 제외되었다. 따라서 학습에 사용된 Train 이미지는 1,034장(healthy 341장)이다.

**원본과 실행용 폴더의 매핑**

| 제공 원본 폴더 | 코드 실행용 폴더 | 비고 |
|---|---|---|
| train | dataset/train | 학습용 |
| validation | dataset/val | 제공 코드가 `val` 폴더명을 읽기 때문에 이름만 변경해 배치 |
| test | dataset/test | 학습·모델 선택에 사용하지 않음 |

**중복·누출 점검**

- 방법: `dataset` 전체의 jpg/jpeg/png 파일에 SHA-256 해시를 계산해 같은 해시를 가진 파일이 있는지 확인
- 명령: `find dataset -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -exec sha256sum {} + | sort | uniq -w64 -D`
- 결과: 출력 없음 (바이트가 동일한 중복 파일 없음)
- 한계: 바이트가 완전히 같은 파일만 찾는다. 크기 변경·재저장된 유사 이미지나 같은 잎을 다른 각도로 찍은 사진은 탐지하지 못한다. 해시 점검은 jpg/jpeg/png만 대상으로 했으므로 위 .120tore 파일은 포함되지 않았다.

## 2. 실행 설정

| 파라미터            | 값                           | 근거                          |
| --------------- | --------------------------- | --------------------------- |
| base_model      | microsoft/resnet-18         | training_report.json        |
| epochs          | 3                           | training/finetune.py 기본값    |
| batch_size      | 8                           | training/finetune.py 기본값    |
| learning_rate   | 0.0002 (2e-4)               | training/finetune.py 기본값    |
| freeze_backbone | True (--freeze-backbone 사용) | 실행 시 `--freeze-backbone` 사용 |
| output          | artifacts/beans_resnet18    | 기본값                         |

실행 명령 :

```bash
python -m training.finetune --data dataset --output artifacts/beans_resnet18 --epochs 3 --batch-size 8 --freeze-backbone
```
```text
실행 명령은 학습 당시 터미널 로그에서 확인했으며, 해당 화면은 보존하지 못했다.
```
## 3. 학습 결과

`artifacts/beans_resnet18/training_report.json`의 값을 그대로 옮긴 것이다.

| Epoch | Train Loss | Validation Accuracy |
| ----- | ---------: | ------------------: |
| 1     |     0.9924 |              0.6617 |
| 2     |     0.8108 |              0.7669 |
| 3     |     0.7078 |              0.7669 |

- Best Validation Accuracy: 0.7669 (Validation 133장 중 102장)
- Best 모델 저장: artifacts/beans_resnet18/
- Test Accuracy: **미측정** (기본 코드에 Test 평가 절차 없음)
- 혼동행렬, Precision, Recall: **미측정**
- 관찰: Epoch 1에서 2로 넘어갈 때 Validation Accuracy가 올랐고, Epoch 3에서는 같은 값이었다. Train Loss는 3 epoch 동안 계속 감소했다.

## 4. 학습 방식 표기

- `--freeze-backbone`을 사용한 경우: Backbone을 고정하고 새 3클래스 분류 헤드만 학습했으므로 **Head-only Fine-tuning**으로 표기한다. 전체 모델 학습이라고 쓰지 않는다.
- 이 결과는 Head-only 기준선이며, Full Fine-tuning과의 비교는 수행하지 않았다.

## 5. 생성 파일 확인

- [x] config.json
- [x] model.safetensors
- [x] preprocessor_config.json
- [x] training_report.json

## 6. 서비스 연결 확인

- MODEL_PATH: artifacts/beans_resnet18

| 입력 파일(폴더 라벨)                                     |             예측 라벨 |     점수 | 일치  |
| ------------------------------------------------ | ----------------: | -----: | --- |
| bean_rust_test.5.jpg (bean_rust)                 | angular_leaf_spot | 0.3922 | 불일치 |
| healthy_test.1 (healthy)                         |           healthy | 0.8167 | 일치  |
| angular_leaf_spot_test.6.jpg (angular_leaf_spot) | angular_leaf_spot | 0.4712 | 일치  |
-  클래스당 1장씩의 시연 결과이며 모델의 정확도를 의미하지 않는다. Test Accuracy는 측정하지 않았다.
-  bean_rust 이미지는 angular_leaf_spot으로 예측되었다(점수: angular_leaf_spot 0.3922, bean_rust 0.3603, healthy 0.2476). 2026-11-06 동기 API(`/api/sync/classify/`) 재실행 결과다.
- angular_leaf_spot 이미지는 점수 차가 작았다(angular_leaf_spot 0.4712, bean_rust 0.4657).


## 7. 결과 판정

- 완료: 학습 실행 및 모델 파일 4종 생성
- 한계: Test 정량평가 미수행, Validation 133장 기준의 단일 실험, 3 epoch 학습, 시연 샘플 3장 중 1장이 오분류되었고, 일부 결과는 클래스 간 점수 차가 작았다.
- 증빙: evidence/model_folder.png (`ls artifacts/beans_resnet18/`), evidence/train_log.png (`cat training_report.json`)
- 원본 기록: reports/data/training_report.json
