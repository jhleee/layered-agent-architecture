# 07 — 의존성 검증

> 작업 전 `assets/architecture-rules.md`를 먼저 읽는다.

---

## lint_dependencies.py 사용법

### 실행

```bash
# 프로젝트 루트에서 실행
python path/to/lint_dependencies.py ./src

# 또는 직접 경로 지정
python lint_dependencies.py /path/to/src
```

스크립트 위치: `scripts/lint_dependencies.py` (이 스킬 디렉토리 내)

### Exit Codes

| 코드 | 의미 |
|------|------|
| 0 | 통과 — 위반 없음 |
| 1 | 위반 발견 — 수정 필요 |

---

## 출력 예시

### 통과 시

```
  Linting dependencies in: /path/to/src

  All dependency rules passed.

  Summary: 0 error(s), 0 warning(s)
```

### 위반 시

```
  Linting dependencies in: /path/to/src

============================================================
  VIOLATIONS: 2 dependency rule(s) broken
============================================================

  [ERROR] core/models.py:5
          core/ -> nodes/ (import nodes.reasoning)

  [ERROR] tools/search.py:3
          tools/ -> graphs/ (import graphs.main)

  WARNINGS: 1 conditional import(s) (try/except)
  ────────────────────────────────────────────────────

  [WARN] interfaces/api.py:8
         interfaces/ -> memory/ (import memory.checkpointer)

  Summary: 2 error(s), 1 warning(s)
```

### 해석 가이드

- **ERROR**: 의존성 규칙 위반. 반드시 수정해야 한다
- **WARN**: `try/except ImportError` 내부의 import. 선택적 의존이므로 경고만 표시

---

## 수동 검증 체크리스트

lint 스크립트 외에 추가로 확인할 항목:

- [ ] `core/` 파일이 다른 레이어를 import하지 않는가
- [ ] `nodes/`가 `core/`, `prompts/`, `tools/`만 import하는가
- [ ] `graphs/`가 `nodes/`, `memory/`, `config/`, `core/`만 import하는가
- [ ] `interfaces/`가 `graphs/`, `core/`만 import하는가
- [ ] 순환 의존이 없는가 (A→B→A)
- [ ] `config/`를 참조하는 레이어가 의존 방향을 위반하지 않는가

---

## 의존성 매트릭스 빠른 참조

| Source ↓ / Target → | core | memory | prompts | tools | nodes | graphs | interfaces | config |
|---------------------|------|--------|---------|-------|-------|--------|------------|--------|
| **core** | - | X | X | X | X | X | X | O |
| **memory** | O | - | X | X | X | X | X | O |
| **prompts** | O | X | - | X | X | X | X | O |
| **tools** | O | X | X | - | X | X | X | O |
| **nodes** | O | X | O | O | - | X | X | O |
| **graphs** | O | O | X | X | O | - | X | O |
| **interfaces** | O | X | X | X | X | O | - | O |

`O` = import 허용, `X` = import 금지, `-` = 같은 레이어 (항상 허용)

**특수 규칙:**
- `config/` 열이 모두 `O` — 어떤 레이어든 config를 import할 수 있다 (수평 참조)
- `core/` 행이 대부분 `X` — core는 자기 완결 (config만 예외적 허용)
