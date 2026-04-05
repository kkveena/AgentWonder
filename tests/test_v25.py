"""Version 2.5 tests — structured logging, persistence, LLM client, LLM tools."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentwonder.logging import (
    StructuredFormatter,
    ConsoleFormatter,
    StructuredLogger,
    get_logger,
    configure_logging,
)
from agentwonder.runtime.session_store import (
    InMemorySessionStore,
    FileSessionStore,
    SessionStore,
    SessionNotFoundError,
)
from agentwonder.runtime.state_store import (
    InMemoryStateStore,
    FileStateStore,
    StateStore,
)
from agentwonder.runtime.llm_client import GeminiClient
from agentwonder.tools.llm_tools import LLMSummarizer, LLMClassifier


# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------

class TestStructuredLogging:
    def test_structured_formatter_json_output(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            "test.logger", logging.INFO, "test.py", 1, "hello world", (), None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "info"
        assert parsed["message"] == "hello world"
        assert "timestamp" in parsed

    def test_console_formatter(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            "test.logger", logging.INFO, "test.py", 1, "hello", (), None,
        )
        output = formatter.format(record)
        assert "INFO" in output
        assert "hello" in output

    def test_structured_logger_extras(self):
        base = logging.getLogger("test.extras")
        base.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        base.handlers = [handler]

        slogger = StructuredLogger(base)
        # This should not raise
        slogger.info("test msg", key1="val1", key2=42)
        slogger.debug("debug msg", run_id="r1")

    def test_get_logger_returns_structured(self):
        lg = get_logger("test.module")
        assert isinstance(lg, StructuredLogger)


# ---------------------------------------------------------------------------
# Persistence Protocols
# ---------------------------------------------------------------------------

class TestPersistenceProtocols:
    def test_in_memory_session_is_session_store(self):
        store = InMemorySessionStore()
        assert isinstance(store, SessionStore)

    def test_file_session_is_session_store(self, tmp_path):
        store = FileSessionStore(data_dir=tmp_path)
        assert isinstance(store, SessionStore)

    def test_in_memory_state_is_state_store(self):
        store = InMemoryStateStore()
        assert isinstance(store, StateStore)

    def test_file_state_is_state_store(self, tmp_path):
        store = FileStateStore(data_dir=tmp_path)
        assert isinstance(store, StateStore)


# ---------------------------------------------------------------------------
# File-backed Session Store
# ---------------------------------------------------------------------------

class TestFileSessionStore:
    def test_create_and_get(self, tmp_path):
        store = FileSessionStore(data_dir=tmp_path)
        session = store.create_session("run1")
        assert session["run_id"] == "run1"

        retrieved = store.get_session("run1")
        assert retrieved["run_id"] == "run1"

    def test_update_session(self, tmp_path):
        store = FileSessionStore(data_dir=tmp_path)
        store.create_session("run1")
        store.update_session("run1", {"key": "value"})
        session = store.get_session("run1")
        assert session["data"]["key"] == "value"

    def test_delete_session(self, tmp_path):
        store = FileSessionStore(data_dir=tmp_path)
        store.create_session("run1")
        store.delete_session("run1")
        with pytest.raises(SessionNotFoundError):
            store.get_session("run1")

    def test_persistence_across_instances(self, tmp_path):
        store1 = FileSessionStore(data_dir=tmp_path)
        store1.create_session("run1")
        store1.update_session("run1", {"persisted": True})

        # New instance, same directory
        store2 = FileSessionStore(data_dir=tmp_path)
        session = store2.get_session("run1")
        assert session["data"]["persisted"] is True

    def test_get_missing_raises(self, tmp_path):
        store = FileSessionStore(data_dir=tmp_path)
        with pytest.raises(SessionNotFoundError):
            store.get_session("nonexistent")


# ---------------------------------------------------------------------------
# File-backed State Store
# ---------------------------------------------------------------------------

class TestFileStateStore:
    def test_set_and_get(self, tmp_path):
        store = FileStateStore(data_dir=tmp_path)
        store.set("run1", "step1", {"result": "ok"})
        assert store.get("run1", "step1") == {"result": "ok"}

    def test_get_missing(self, tmp_path):
        store = FileStateStore(data_dir=tmp_path)
        assert store.get("run1", "step1") is None

    def test_get_all(self, tmp_path):
        store = FileStateStore(data_dir=tmp_path)
        store.set("run1", "s1", "a")
        store.set("run1", "s2", "b")
        assert store.get_all("run1") == {"s1": "a", "s2": "b"}

    def test_persistence_across_instances(self, tmp_path):
        store1 = FileStateStore(data_dir=tmp_path)
        store1.set("run1", "s1", {"data": 42})

        store2 = FileStateStore(data_dir=tmp_path)
        assert store2.get("run1", "s1") == {"data": 42}


# ---------------------------------------------------------------------------
# Gemini Client
# ---------------------------------------------------------------------------

class TestGeminiClient:
    def test_no_api_key_returns_unconfigured(self):
        with patch.dict("os.environ", {}, clear=True):
            client = GeminiClient.__new__(GeminiClient)
            client._api_key = ""
            client._model = "gemini-2.0-flash"
            client._client = None
            assert client.is_configured is False

    @pytest.mark.asyncio
    async def test_stub_response_without_key(self):
        client = GeminiClient.__new__(GeminiClient)
        client._api_key = ""
        client._model = "gemini-2.0-flash"
        client._client = None
        result = await client.generate("test prompt")
        assert "Stub" in result


# ---------------------------------------------------------------------------
# LLM Tools
# ---------------------------------------------------------------------------

class TestLLMSummarizer:
    @pytest.mark.asyncio
    async def test_stub_summarize(self):
        client = GeminiClient.__new__(GeminiClient)
        client._api_key = ""
        client._model = "gemini-2.0-flash"
        client._client = None

        tool = LLMSummarizer(client=client)
        result = await tool.call({"text": "This is a long document about AI."})
        assert result["status"] == "success"
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_empty_text(self):
        tool = LLMSummarizer()
        result = await tool.call({})
        assert result["status"] == "error"


class TestLLMClassifier:
    @pytest.mark.asyncio
    async def test_stub_classify(self):
        client = GeminiClient.__new__(GeminiClient)
        client._api_key = ""
        client._model = "gemini-2.0-flash"
        client._client = None

        tool = LLMClassifier(client=client)
        result = await tool.call({
            "text": "My internet is not working",
            "categories": ["billing", "technical", "general"],
        })
        assert result["status"] == "success"
        assert result["category"] in ["billing", "technical", "general"]

    @pytest.mark.asyncio
    async def test_empty_categories(self):
        tool = LLMClassifier()
        result = await tool.call({"text": "something", "categories": []})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_empty_text(self):
        tool = LLMClassifier()
        result = await tool.call({"text": "", "categories": ["a"]})
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Executor with LLM client (stub mode)
# ---------------------------------------------------------------------------

class TestExecutorWithLLMStub:
    """Verify executor works in stub mode (no API key)."""

    @pytest.mark.asyncio
    async def test_llm_agent_step_produces_stub_output(self):
        from agentwonder.compiler.loader import load_yaml
        from agentwonder.compiler.validators import validate_workflow, cross_validate_workflow
        from agentwonder.compiler.resolver import resolve_workflow
        from agentwonder.compiler.builder import build_plan
        from agentwonder.registry import TemplateRegistry, ToolRegistry, PromptRegistry, PolicyRegistry
        from agentwonder.runtime.executor import WorkflowExecutor
        from agentwonder.schemas.run import RunRequest
        from agentwonder.schemas.common import RunState

        config = Path("config")
        if not config.is_dir():
            pytest.skip("config/ not available")

        tr = TemplateRegistry(); tr.load_from_directory(config / "templates")
        tl = ToolRegistry(); tl.load_from_directory(config / "tools")
        pr = PromptRegistry(); pr.load_from_directory(config / "prompts")
        po = PolicyRegistry(); po.load_from_directory(config / "policies")

        tools_d = {t.id: t for t in tl.list_all()}
        templates_d = {t.id: t for t in tr.list_all()}
        prompts_d = {t.id: t for t in pr.list_all()}
        policies_d = {t.id: t for t in po.list_all()}

        raw = load_yaml(config / "workflows" / "break_resolution_v1.yaml")
        wf = validate_workflow(raw)
        errors = cross_validate_workflow(wf, tools_d, templates_d, policies_d, prompts_d)
        assert errors == []

        resolved = resolve_workflow(wf, tools_d, templates_d, prompts_d, policies_d)
        plan = build_plan(resolved)

        # Create executor with unconfigured client (stub mode)
        stub_client = GeminiClient.__new__(GeminiClient)
        stub_client._api_key = ""
        stub_client._model = "gemini-2.0-flash"
        stub_client._client = None

        executor = WorkflowExecutor(llm_client=stub_client)
        req = RunRequest(
            workflow_id="break_resolution_v1",
            inputs={"break_id": "B1", "source_system": "test"},
        )
        status = await executor.execute(req, plan)

        assert status.state == RunState.COMPLETED
        assert len(status.outputs) == 5

    @pytest.mark.asyncio
    async def test_llm_tool_configs_load(self):
        """Verify LLM tool YAML configs load and validate."""
        from agentwonder.registry import ToolRegistry

        config = Path("config")
        if not config.is_dir():
            pytest.skip("config/ not available")

        reg = ToolRegistry()
        reg.load_from_directory(config / "tools")
        tools = {t.id: t for t in reg.list_all()}

        assert "llm_summarizer" in tools
        assert "llm_classifier" in tools
        assert tools["llm_summarizer"].type == "llm"
        assert tools["llm_classifier"].type == "llm"
