from langchain_core.tools import BaseTool
import logging

logger = logging.getLogger(__name__)


class AgentTool(BaseTool):
    """공통 에러 핸들링과 로깅을 포함하는 도구 베이스 클래스."""

    def _handle_error(self, error: Exception) -> str:
        logger.error(f"Tool {self.name} failed: {error}")
        return f"도구 실행 중 오류 발생: {error}"
