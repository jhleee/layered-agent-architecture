#!/usr/bin/env python3
"""AST 기반 import 의존성 분석 스크립트.

LangGraph 7-레이어 아키텍처의 의존성 규칙을 검증한다.
stdlib만 사용 (ast, pathlib, sys, os).

사용법:
    python lint_dependencies.py [project_root]
    python lint_dependencies.py ./agent_system

Exit codes:
    0 — 위반 없음 (통과)
    1 — 위반 발견
"""

import ast
import os
import sys
from pathlib import Path

# ──────────────────────────────────────
# 의존성 규칙 정의
# ──────────────────────────────────────

# 각 레이어가 import할 수 있는 레이어 목록
ALLOWED_DEPS: dict[str, set[str]] = {
    "core":       set(),                                          # 자기 완결
    "memory":     {"core"},
    "prompts":    {"core"},
    "tools":      {"core"},
    "nodes":      {"core", "prompts", "tools"},
    "graphs":     {"core", "nodes", "memory", "config"},
    "interfaces": {"core", "graphs"},
}

# config/는 수평 참조 허용: 어떤 레이어든 config를 import 가능
# → 모든 레이어의 ALLOWED_DEPS에 "config"를 추가
for layer in ALLOWED_DEPS:
    ALLOWED_DEPS[layer].add("config")

# 인식 대상 레이어 목록
KNOWN_LAYERS = set(ALLOWED_DEPS.keys()) | {"config"}


# ──────────────────────────────────────
# 유틸리티 함수
# ──────────────────────────────────────

def get_layer(filepath: Path, project_root: Path) -> str | None:
    """파일의 소속 레이어를 판별한다.

    Args:
        filepath: 분석 대상 파일 경로
        project_root: 프로젝트 루트 (agent_system/)

    Returns:
        레이어 이름 (예: "core", "nodes") 또는 None (레이어 외부)
    """
    try:
        rel = filepath.relative_to(project_root)
    except ValueError:
        return None

    parts = rel.parts
    if len(parts) < 2:
        # 루트 레벨 파일 (main.py 등) — 레이어 아님
        return None

    layer = parts[0]
    return layer if layer in KNOWN_LAYERS else None


def extract_imports(filepath: Path) -> list[dict]:
    """AST로 import 문을 추출한다.

    Args:
        filepath: Python 파일 경로

    Returns:
        [{"module": "core.state", "line": 3, "in_try_except": False}, ...]
    """
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    imports = []

    for node in ast.walk(tree):
        in_try_except = _is_in_try_except(node, tree)

        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "line": node.lineno,
                    "in_try_except": in_try_except,
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append({
                    "module": node.module,
                    "line": node.lineno,
                    "in_try_except": in_try_except,
                })

    return imports


def _is_in_try_except(node: ast.AST, tree: ast.Module) -> bool:
    """노드가 try/except 블록 내에 있는지 확인한다."""
    for parent in ast.walk(tree):
        if isinstance(parent, ast.Try):
            for handler in parent.handlers:
                if handler.name and "ImportError" in ast.dump(handler):
                    # handler의 자식 노드 범위 내에 있는지 확인
                    pass
            # 간단한 접근: try 블록의 라인 범위 내에 있는지 확인
            try_start = parent.lineno
            try_end = parent.end_lineno or parent.lineno
            if hasattr(node, "lineno"):
                if try_start <= node.lineno <= try_end:
                    # handler 중 ImportError를 잡는지 확인
                    for handler in parent.handlers:
                        if handler.type is None:
                            return True
                        if isinstance(handler.type, ast.Name) and handler.type.id == "ImportError":
                            return True
                        if isinstance(handler.type, ast.Tuple):
                            for elt in handler.type.elts:
                                if isinstance(elt, ast.Name) and elt.id == "ImportError":
                                    return True
    return False


def _get_target_layer(module: str) -> str | None:
    """import 모듈 경로에서 대상 레이어를 추출한다.

    Args:
        module: "core.state", "nodes.reasoning" 등

    Returns:
        레이어 이름 또는 None (프로젝트 외부 모듈)
    """
    top = module.split(".")[0]
    return top if top in KNOWN_LAYERS else None


# ──────────────────────────────────────
# 검증 로직
# ──────────────────────────────────────

def check_violations(project_root: str | Path) -> tuple[list[dict], list[dict]]:
    """프로젝트 전체의 의존성 위반을 검출한다.

    Args:
        project_root: agent_system/ 디렉토리 경로

    Returns:
        (violations, warnings) 튜플
        violations: [{"file": ..., "line": ..., "from": ..., "to": ..., "module": ...}]
        warnings: try/except ImportError 내 import (위반이 아닌 경고)
    """
    root = Path(project_root).resolve()
    violations = []
    warnings = []

    for py_file in root.rglob("*.py"):
        source_layer = get_layer(py_file, root)
        if source_layer is None:
            continue

        imports = extract_imports(py_file)

        for imp in imports:
            target_layer = _get_target_layer(imp["module"])
            if target_layer is None:
                continue  # 외부 라이브러리

            if target_layer == source_layer:
                continue  # 같은 레이어 내부 import (허용)

            allowed = ALLOWED_DEPS.get(source_layer, set())

            if target_layer not in allowed:
                entry = {
                    "file": str(py_file.relative_to(root)),
                    "line": imp["line"],
                    "from": source_layer,
                    "to": target_layer,
                    "module": imp["module"],
                }

                if imp["in_try_except"]:
                    warnings.append(entry)
                else:
                    violations.append(entry)

    return violations, warnings


# ──────────────────────────────────────
# 리포트 출력
# ──────────────────────────────────────

def print_report(violations: list[dict], warnings: list[dict]) -> None:
    """검증 결과를 출력한다."""
    if violations:
        print(f"\n{'='*60}")
        print(f"  VIOLATIONS: {len(violations)} dependency rule(s) broken")
        print(f"{'='*60}\n")
        for v in violations:
            print(f"  [ERROR] {v['file']}:{v['line']}")
            print(f"          {v['from']}/ -> {v['to']}/ (import {v['module']})")
            print()
    else:
        print(f"\n  All dependency rules passed.")

    if warnings:
        print(f"\n  WARNINGS: {len(warnings)} conditional import(s) (try/except)")
        print(f"  {'─'*56}\n")
        for w in warnings:
            print(f"  [WARN] {w['file']}:{w['line']}")
            print(f"         {w['from']}/ -> {w['to']}/ (import {w['module']})")
            print()

    total = len(violations) + len(warnings)
    print(f"\n  Summary: {len(violations)} error(s), {len(warnings)} warning(s)")


# ──────────────────────────────────────
# 메인
# ──────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = "."

    root = Path(project_root)
    if not root.is_dir():
        print(f"Error: '{project_root}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    print(f"\n  Linting dependencies in: {root.resolve()}")

    violations, warnings = check_violations(root)
    print_report(violations, warnings)

    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
