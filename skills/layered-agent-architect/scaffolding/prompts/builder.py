from prompts.templates import SYSTEM_PROMPT, PLANNING_PROMPT


def build_system_prompt(tools: list[str] | None = None) -> str:
    """State 기반으로 시스템 프롬프트를 동적 조합한다."""
    base = SYSTEM_PROMPT
    if tools:
        base += f"\n\n사용 가능한 도구: {', '.join(tools)}"
    return base


def build_prompt_from_state(state: dict) -> str:
    """State에서 컨텍스트를 추출하여 프롬프트를 조합한다."""
    tools = state.get("available_tools", [])
    context = state.get("current_plan", "")
    return PLANNING_PROMPT.format(tools=tools, context=context)
