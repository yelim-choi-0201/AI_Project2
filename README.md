# 역별 승하차 이용 분석 · Streamlit 대시보드

원본 `station_daily_usage.csv`와
`역별_승하차_결과해석_보고서_가독성개선.docx`를 대화형 앱으로 옮긴 배포용 프로젝트입니다.
공개 배포가 완료된 프로젝트를 내려받는 것이 아니라, **사용자 계정에서 배포할 소스 묶음**입니다.

## 포함 화면

- **한눈에 보기**: 승차·하차·합계·일평균, 역별 주말 증감률, 누적 규모와 집계표.
- **평일·주말 비교**: 관측 일수를 고려한 일평균 막대그래프, 증감률과 원본 해석.
- **역별 추이**: 역 선택, 승차·하차 / 합계 전환, 주말 음영, 통일된 세로축, 최대·최소일.
- **종합 해석**: 승차·하차 차이, 운영 검토 방향, 분석의 한계. 원본 전체 기간 기준으로 고정.
- **데이터·보고서**: 품질 점검, CSV 다운로드, 기존 Word 보고서 다운로드.

조회 기간과 역을 바꾸면 수치·표·그래프가 재계산됩니다.
원본 보고서의 해석을 필터 결과에 그대로 적용하지 않도록 고정 해석에는 전체 기간을 명시했습니다.
실시간 데이터 수집, 로그인, 외부 데이터 전송, 유료 API 호출은 앱에 구현하지 않았습니다.

## 원본 수치

분석 기간은 2026-09-07~2026-09-20입니다. 4개 역, 14일(평일 10일 / 주말 4일), 56행입니다.

| 역명 | 승차 | 하차 | 승하차 합계 | 평일 대비 주말 일평균 |
|---|---:|---:|---:|---:|
| 가람역 | 11,575 | 10,556 | 22,131 | -32.0% |
| 누리역 | 8,497 | 8,146 | 16,643 | -20.0% |
| 해솔역 | 7,511 | 7,452 | 14,963 | +97.4% |
| 한빛역 | 5,010 | 5,208 | 10,218 | +24.5% |
| 전체 | 32,593 | 31,362 | 63,955 | +3.8% |

단위는 사람 수가 아니라 건수입니다. 민원건수는 승하차 해석에 사용하지 않습니다.
차이와 증감률은 반올림 전 평균으로 계산하며 화면에는 소수점 첫째 자리로 반올림합니다.

## 가장 간단한 공개 배포: Streamlit Community Cloud

1. ZIP을 풀고 프로젝트의 **내용물**을 GitHub 저장소 루트에 올립니다.
   `app.py`, `analytics.py`, `charts.py`, `report_content.py`, `requirements.txt`,
   `.streamlit/config.toml`, `.gitattributes`, `data/`, `assets/`가 포함되어야 합니다.
   ZIP 파일 자체만 업로드하면 앱이 실행되지 않습니다.
2. Streamlit Community Cloud에 로그인하고 GitHub 계정을 연결합니다.
3. **Create app → Yup, I have an app**을 선택합니다.
4. 저장소와 브랜치를 선택하고 **Main file path**에 `app.py`를 입력합니다.
   브랜치를 `main`으로 만들었다면 `main`을 선택합니다.
5. **Advanced settings → Python version**을 `3.13`으로 선택합니다.
   이 프로젝트의 계산·그래프 검증 환경은 Python 3.13입니다.
   API 키와 secrets는 필요하지 않습니다.
6. **Deploy**를 누른 뒤 로그에서 설치와 실행 결과를 확인합니다.
   배포가 성공해야 `*.streamlit.app` 주소가 발급됩니다.
   이 문서에는 아직 발급되지 않은 주소를 기재하지 않았습니다.

공식 안내:
- 배포: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- 파일 구성: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization
- 의존성: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies

### 공개 범위 확인

공개 앱에서는 포함한 데이터와 Word 보고서의 다운로드가 가능합니다.
공개하면 안 되는 자료라면 저장소·앱의 접근 권한을 먼저 제한하거나,
`app.py`의 다운로드 영역과 제공 데이터를 조정한 뒤 배포하세요.
이 프로젝트는 배포 서비스의 유료 리소스를 자동 생성하지 않습니다.

## 로컬 실행

Python 3.13 기준입니다. 압축을 푼 폴더에서 실행합니다.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

python -m pip install -r requirements.txt
python -m streamlit run app.py
```

터미널에 표시되는 로컬 주소로 접속합니다. 로컬 실행 주소는 공개 배포 URL이 아닙니다.

## Docker / Railway 등 컨테이너 환경

`Dockerfile`을 포함했습니다. 서비스를 생성하는 계정·권한은 사용자가 준비해야 합니다.
컨테이너 플랫폼에서 Dockerfile 빌드를 선택하고 해당 플랫폼에서 도메인을 연결하세요.
플랫폼이 제공하는 `PORT`를 사용하며, 지정되지 않으면 8501번으로 실행합니다.

```bash
docker build -t station-usage-app .
docker run --rm -p 8501:8501 station-usage-app
```

Docker 빌드와 외부 클라우드 배포는 이 작업 환경에서 실행하지 않았습니다.

## 테스트

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

계산 테스트는 보고서 합계·평일/주말 평균·최대/최소일·필터·반올림·잘못된 입력을 검증합니다.
그래프 테스트는 원본 숫자·주말 표시·단일 날짜 처리를 검증합니다.
`tests/test_app.py`는 Streamlit의 `AppTest`로 앱 초기 화면과 필터를 검사합니다.
Streamlit이 설치되지 않은 환경에서는 해당 테스트 모듈만 건너뜁니다.
실제 수행 결과와 미수행 항목은 `VALIDATION.md`를 확인하세요.

## 파일 구조

```text
station_usage_app/
  app.py
  analytics.py
  charts.py
  report_content.py
  requirements.txt
  requirements-dev.txt
  .streamlit/config.toml
  data/station_daily_usage.csv
  assets/station_report.docx
  tests/
  Dockerfile
  .dockerignore
  .gitignore
  .gitattributes
  README.md
  VALIDATION.md
```

CSV는 원본 체크섬으로 고정되어 있습니다. 데이터를 다른 것으로 바꿀 때는
`analytics.py`의 검증 기준과 `report_content.py`의 해석을 함께 갱신해야 합니다.
이는 원본과 다른 데이터에 기존 보고서 결론이 잘못 표시되는 것을 막기 위한 장치입니다.

## 출처

- 원본 데이터: 업로드된 `station_daily_usage.csv` (56행·6열)
- 원본 해석: `역별_승하차_결과해석_보고서_가독성개선.docx`, 2026.10.21, 01~05절
- 앱의 날짜·역 필터, 다운로드, 상호작용 기능은 원본 해석을 살펴보기 위한 인터페이스입니다.
  새로운 이용 목적·혼잡 원인·운영 효과를 추정하는 모델은 추가하지 않았습니다.
