# Pathray

> 웹사이트 구조 분석 및 ERD 자동 생성 도구

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 소개

웹사이트의 구조와 데이터를 체계적으로 파악하려면 수동으로 모든 페이지를 방문하고 데이터를 정리해야 합니다. 이 과정은 시간이 많이 걸리고, 누락이 발생하기 쉬우며, 데이터 간의 관계를 파악하기 어렵습니다.

**Pathray**는 웹사이트 URL 하나만 입력하면:

1. Playwright 기반으로 전체 사이트를 크롤링하고
2. 페이지별 데이터(테이블, 폼, 텍스트, 메타데이터)를 추출하여 정리하고
3. 데이터베이스 ERD를 자동 생성합니다

## 주요 기능

- **사이트맵 크롤링** — BFS 기반 재귀 크롤링, 동시성 제어, 중복/외부 링크 자동 필터링
- **데이터 추출** — HTML 테이블, 폼 필드, 텍스트, 메타데이터를 구조화된 JSON으로 변환
- **ERD 생성** — 엔티티/관계 자동 추론, Mermaid 다이어그램, SQL DDL, PNG/SVG 이미지 출력

## 데이터 흐름

```
[Root URL] → [Playwright Crawler] → [Sitemap JSON]
                                          |
                                   [Data Extractor]
                                          |
                               [Page Data JSON files]
                                          |
                                 [ERD Generator]
                                     |      |
                             [Mermaid ERD] [SQL DDL]
                                     |
                               [PNG/SVG Image]
```

## 설치

### 요구 사항

- Python 3.12 이상
- [uv](https://docs.astral.sh/uv/) 패키지 매니저
- Node.js (ERD 이미지 렌더링용, 선택)

### 설치 방법

```bash
# 저장소 클론
git clone https://github.com/choo121600/pathray.git
cd pathray

# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium
```

## 빠른 시작

### 전체 파이프라인 (권장)

```bash
# URL 하나로 크롤링 → 추출 → ERD 생성까지 한 번에 실행
pathray run https://example.com
```

### 단계별 실행

```bash
# 1. 사이트맵 생성
pathray crawl https://example.com --depth 3

# 2. 페이지 데이터 추출
pathray extract output/sitemap.json

# 3. ERD 생성
pathray erd output/data/
```

## CLI 레퍼런스

### 글로벌 옵션

| 옵션 | 설명 |
|------|------|
| `--version`, `-v` | 버전 출력 |
| `--help` | 도움말 표시 |

### `pathray crawl`

웹사이트를 크롤링하여 사이트맵을 생성합니다.

```
pathray crawl [OPTIONS] URL
```

| 옵션 | 단축 | 타입 | 기본값 | 설명 |
|------|------|------|--------|------|
| `URL` | | TEXT | (필수) | 크롤링 대상 URL |
| `--depth` | `-d` | INTEGER | `5` | 최대 크롤링 깊이 |
| `--concurrency` | `-c` | INTEGER | `3` | 최대 동시 크롤링 페이지 수 |
| `--output` | `-o` | TEXT | `output/sitemap.json` | 출력 파일 경로 |
| `--silent` | `-s` | | `false` | 진행 출력 비활성화 |

### `pathray extract`

사이트맵의 각 페이지를 방문하여 구조화된 데이터를 추출합니다.

```
pathray extract [OPTIONS] SITEMAP
```

| 옵션 | 단축 | 타입 | 기본값 | 설명 |
|------|------|------|--------|------|
| `SITEMAP` | | TEXT | (필수) | 사이트맵 JSON 파일 경로 |
| `--output` | `-o` | TEXT | `output/data/` | 추출 데이터 출력 디렉토리 |
| `--concurrency` | `-c` | INTEGER | `3` | 최대 동시 페이지 수 (최소 1) |
| `--silent` | `-s` | | `false` | 진행 출력 비활성화 |

### `pathray erd`

추출된 페이지 데이터로부터 ERD를 생성합니다.

```
pathray erd [OPTIONS] PAGES_DIR
```

| 옵션 | 단축 | 타입 | 기본값 | 설명 |
|------|------|------|--------|------|
| `PAGES_DIR` | | TEXT | (필수) | 추출된 페이지 디렉토리 경로 |
| `--output` | `-o` | TEXT | `output/erd.json` | 출력 파일 경로 |
| `--format` | `-f` | TEXT | `json` | 출력 형식 (`json`, `mermaid`) |
| `--threshold` | `-t` | FLOAT | `0.6` | 엔티티 병합 Jaccard 유사도 임계값 (0.0~1.0) |

### `pathray run`

전체 파이프라인을 한 번에 실행합니다: crawl → extract → erd

```
pathray run [OPTIONS] URL
```

| 옵션 | 단축 | 타입 | 기본값 | 설명 |
|------|------|------|--------|------|
| `URL` | | TEXT | (필수) | 대상 URL |
| `--output` | `-o` | TEXT | `output/` | 출력 디렉토리 |
| `--format` | `-f` | TEXT | `json` | ERD 출력 형식 (`json`, `mermaid`) |

## 출력 구조

```
output/
├── sitemap.json          # 크롤링된 사이트맵 (URL, 제목, 깊이, 상태코드)
├── data/
│   ├── page-000.json     # 페이지별 추출 데이터 (테이블, 폼, 텍스트, 메타)
│   ├── page-001.json
│   └── ...
├── summary.json          # 추출 요약 리포트 (총 페이지/테이블/폼/이미지 수)
├── erd.json              # 추론된 엔티티와 관계 (JSON)
├── erd.mmd               # Mermaid erDiagram 문법
├── erd.png               # ERD 이미지 (Node.js 필요)
├── erd.svg               # ERD SVG (Node.js 필요)
└── schema.sql            # SQL CREATE TABLE DDL
```

## 개발

### 개발 환경 설정

```bash
uv sync
uv run playwright install chromium
```

### 테스트 실행

```bash
# 전체 테스트
uv run pytest

# 커버리지 포함
uv run pytest --cov=pathray
```

### 린팅

```bash
uv run ruff check .
```

## 기술 스택

| 영역 | 기술 |
|------|------|
| 언어 | Python 3.12+ |
| 패키지 매니저 | uv |
| 크롤링 | Playwright |
| CLI | Typer + Rich |
| 데이터 모델 | Pydantic v2 |
| ERD 렌더링 | Mermaid (mermaid-cli) |
| 테스트 | pytest + pytest-asyncio |
| 린터 | ruff |

## License

MIT
