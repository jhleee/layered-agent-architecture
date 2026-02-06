# 제11장 Config 레이어

> [← 이전: 제10장 Interfaces 레이어](./10-interfaces-레이어.md) | [목차](./index.md)

---

## 이 장의 파일 범위

```
config/
├── settings.py    ← 11.1
└── agents.yaml    ← 11.2
```

`config/` 레이어는 **하드코딩된 설정값을 외부로 추출**하여 코드 변경 없이 동작을 전환할 수 있게 한다. [제2장 설계 원칙](./02-설계-원칙.md)의 원칙 6(설정 외부화)을 구현하는 레이어이다.

---

## 11.1 환경 변수 관리 (settings.py)

### 11.1.1 Pydantic Settings 기반 설계

`settings.py`는 **Pydantic Settings**를 사용하여 환경 변수를 타입 안전하게 관리한다. `.env` 파일에서 자동으로 값을 로딩하며, 누락된 필수 값은 애플리케이션 시작 시 즉시 에러를 발생시킨다.

### 11.1.2 코드

```python
# config/settings.py

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 전역 설정.

    환경 변수 또는 .env 파일에서 값을 로딩한다.
    필수/선택 구분이 명확하며, 타입 검증이 자동으로 수행된다.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ──────────────────────────────────────
    # 필수 설정
    # ──────────────────────────────────────
    openai_api_key: str                     # OpenAI API 키

    # ──────────────────────────────────────
    # 선택 설정 (기본값 있음)
    # ──────────────────────────────────────
    environment: str = "development"        # development | staging | production
    model_name: str = "gpt-4o"             # 기본 LLM 모델명
    model_temperature: float = 0.0          # 기본 temperature
    max_iterations: int = 5                 # 에이전트 최대 반복 횟수

    # 데이터베이스 (프로덕션 체크포인터용)
    database_url: str = "sqlite:///agent.db"

    # API 서버
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # 로깅
    log_level: str = "INFO"

    # LangSmith (선택적 트레이싱)
    langsmith_api_key: str | None = None
    langsmith_project: str = "agent-system"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings 인스턴스를 싱글턴으로 반환한다.

    @lru_cache로 애플리케이션 수명 동안 동일한 인스턴스를 재사용한다.
    """
    return Settings()
```

### 11.1.3 필수/선택 설정값 구분

| 유형 | 특징 | 예시 |
|---|---|---|
| **필수** | 기본값 없음, 누락 시 `ValidationError` | `openai_api_key` |
| **선택** | 기본값 제공, 환경 변수로 덮어쓰기 가능 | `environment`, `model_name` |
| **선택 (None 허용)** | 기능 활성화 여부를 제어 | `langsmith_api_key` |

### 11.1.4 타입 안전성 보장

Pydantic Settings의 타입 검증 덕분에 잘못된 설정값이 조기에 감지된다:

```bash
# .env 파일
MAX_ITERATIONS=abc     # int가 아닌 값
API_PORT=not_a_number  # int가 아닌 값

# → 앱 시작 시 즉시 ValidationError 발생
# pydantic_core._pydantic_core.ValidationError:
# 2 validation errors for Settings
#   max_iterations: Input should be a valid integer
#   api_port: Input should be a valid integer
```

### 11.1.5 .env 파일 템플릿

```bash
# .env.example — 프로젝트에 포함, 실제 .env는 .gitignore 처리

# ── 필수 ──
OPENAI_API_KEY=sk-your-api-key-here

# ── 환경 ──
ENVIRONMENT=development    # development | staging | production

# ── 모델 ──
MODEL_NAME=gpt-4o
MODEL_TEMPERATURE=0.0
MAX_ITERATIONS=5

# ── 데이터베이스 ──
DATABASE_URL=sqlite:///agent.db

# ── API 서버 ──
API_HOST=0.0.0.0
API_PORT=8000

# ── 로깅 ──
LOG_LEVEL=INFO

# ── LangSmith (선택) ──
# LANGSMITH_API_KEY=ls-your-key-here
# LANGSMITH_PROJECT=agent-system
```

---

## 11.2 선언적 에이전트 구성 (agents.yaml)

### 11.2.1 왜 YAML인가

`settings.py`는 **시스템 수준 설정** (API 키, 서버 포트 등)을 관리한다. 반면 `agents.yaml`은 **에이전트의 행동을 선언적으로 정의**한다. YAML을 사용하는 이유:

- **비개발자도 수정 가능:** 프롬프트, 도구 목록 변경에 Python 지식이 불필요
- **코드 변경 없는 행동 변경:** YAML만 수정하여 에이전트 동작을 전환
- **환경별 구성 분리:** `agents.dev.yaml`, `agents.prod.yaml` 등

### 11.2.2 구성 스키마

```yaml
# config/agents.yaml

# 기본 에이전트 설정
default:
  model: "gpt-4o"
  temperature: 0
  max_iterations: 5
  system_prompt_version: "v1"
  tools:
    - search
    - calculator

# 에이전트별 설정 (default를 오버라이드)
agents:
  researcher:
    model: "gpt-4o"
    temperature: 0
    max_iterations: 8
    tools:
      - search
      - database
    system_prompt_version: "v1"
    description: "정보 수집 및 분석 전문 에이전트"

  writer:
    model: "gpt-4o"
    temperature: 0.7
    max_iterations: 3
    tools: []
    system_prompt_version: "v1"
    description: "문서 작성 전문 에이전트"

  calculator_agent:
    model: "gpt-4o-mini"
    temperature: 0
    max_iterations: 3
    tools:
      - calculator
    description: "수학 계산 전문 에이전트"
```

### 11.2.3 YAML 로더

```python
# config/ 내부 또는 별도 유틸

import yaml
from pathlib import Path


def load_agent_config(agent_name: str = "default") -> dict:
    """agents.yaml에서 에이전트 설정을 로딩한다.

    Args:
        agent_name: 에이전트 이름. "default"이면 기본 설정 반환.

    Returns:
        에이전트 설정 딕셔너리
    """
    config_path = Path(__file__).parent / "agents.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # default 설정을 기반으로 에이전트별 설정을 병합
    default_config = config.get("default", {})

    if agent_name == "default":
        return default_config

    agent_config = config.get("agents", {}).get(agent_name, {})

    # default를 기반으로 에이전트 설정을 오버라이드
    merged = {**default_config, **agent_config}
    return merged
```

### 11.2.4 활용 예시

```python
# nodes/reasoning.py 에서 YAML 설정 활용
from config.settings import get_settings

# agents.yaml의 설정에 따라 모델 선택
agent_config = load_agent_config("researcher")
model = get_model(
    model_name=agent_config["model"],
    temperature=agent_config["temperature"],
)
tools = get_tools(agent_config["tools"])
```

---

## 11.3 환경별 설정 전략

### 11.3.1 설정 우선순위

설정값은 다음 우선순위로 적용된다 (상위가 우선):

```
1. 환경 변수 (OS 레벨)          ← 최우선
2. .env 파일                    ← 로컬 개발용
3. Settings 클래스의 기본값      ← 폴백
```

이는 Pydantic Settings의 기본 동작이다. 프로덕션 배포 시에는 환경 변수를 직접 주입하고, 로컬 개발 시에는 `.env` 파일을 사용한다.

### 11.3.2 환경별 구성 예시

**개발 환경:**
```bash
ENVIRONMENT=development
OPENAI_API_KEY=sk-dev-key
MODEL_NAME=gpt-4o-mini          # 비용 절감
MAX_ITERATIONS=3                 # 빠른 반복
LOG_LEVEL=DEBUG
```

**스테이징 환경:**
```bash
ENVIRONMENT=staging
OPENAI_API_KEY=sk-staging-key
DATABASE_URL=sqlite:///staging.db
MODEL_NAME=gpt-4o
LOG_LEVEL=INFO
```

**프로덕션 환경:**
```bash
ENVIRONMENT=production
OPENAI_API_KEY=sk-prod-key
DATABASE_URL=postgresql://user:pass@db:5432/agent
MODEL_NAME=gpt-4o
MAX_ITERATIONS=5
LOG_LEVEL=WARNING
LANGSMITH_API_KEY=ls-prod-key    # 트레이싱 활성화
```

### 11.3.3 시크릿 관리 가이드라인

| 항목 | 개발 | 프로덕션 |
|---|---|---|
| **API 키** | `.env` 파일 (gitignore 처리) | 시크릿 매니저 (AWS Secrets Manager, Vault 등) |
| **DB 비밀번호** | `.env` 파일 | 환경 변수 주입 (K8s Secret, Docker Secret 등) |
| **커밋 금지** | `.env`, `*.key`, `credentials.*` | 동일 + CI/CD에서 검증 |

```bash
# .gitignore
.env
*.key
credentials.*
```

---

## config/ 레이어 정리

| 파일 | 역할 | 관리 대상 |
|---|---|---|
| `settings.py` | 시스템 설정 (환경 변수 기반) | API 키, 환경, 서버 설정 |
| `agents.yaml` | 에이전트 행동 정의 (선언적) | 모델, 도구, 프롬프트 버전 |

Config 레이어의 핵심 가치는 **코드 배포 없이 동작을 전환**할 수 있다는 점이다:
- 환경 변수 변경으로 개발/프로덕션 전환
- YAML 수정으로 에이전트 행동 변경
- 시크릿은 코드 밖에서 안전하게 관리

---

> [← 이전: 제10장 Interfaces 레이어](./10-interfaces-레이어.md) | [목차](./index.md)
