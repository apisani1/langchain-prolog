from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterator,
)

import pytest

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tools import (
    BaseTool,
    ToolException,
)
from langchain_prolog import (
    PrologConfig,
    PrologFileNotFoundError,
    PrologRunnable,
    PrologTool,
    ValidationError,
)

import importlib
import langchain_prolog

# Force reload after changes
importlib.reload(langchain_prolog)


# Get the path to the test directory
TEST_DIR = Path(__file__).parent / "test_scripts"


@pytest.fixture
def prolog_tool():
    config = PrologConfig(
        rules_file=TEST_DIR / "family.pl",
        default_predicate="partner",
    )
    return PrologTool(
        name="family_query",
        description="""Query family relationships using Prolog. Input can be a query string like 'parent(john, X, Y)'
        or 'john, X, Y'. You have to specify 3 parameters. Do not use quotes.""",
        prolog_config=config,
    )


@pytest.fixture
def prolog_tool_with_schema():
    schema = PrologRunnable.create_schema("partner", ["X", "Y"])
    config = PrologConfig(
        rules_file=TEST_DIR / "family.pl",
        default_predicate="partner",
        query_schema=schema,
    )
    return PrologTool(
        name="family_query",
        description="""Query family relationships using Prolog. Input can be a query string like 'parent(john, X, Y)'
        or 'john, X, Y'. You have to specify 3 parameters. Do not use quotes.""",
        prolog_config=config,
    )


@pytest.fixture
def zero_arity_tool():
    """Create a tool with zero-arity predicate."""
    schema = PrologRunnable.create_schema("hello", [])
    config = PrologConfig(
        rules_file=TEST_DIR / "family.pl",
        default_predicate="hello",
        query_schema=schema,
    )
    return PrologTool(
        name="zero_arity",
        description="Test zero-arity predicates",
        prolog_config=config,
    )


def test_tool_initialization(prolog_tool):
    """Test basic tool initialization and inheritance."""
    assert isinstance(prolog_tool, BaseTool)
    assert prolog_tool.name == "family_query"
    assert "Query family relationships" in prolog_tool.description
    assert prolog_tool.prolog is not None


def test_tool_run(prolog_tool, prolog_tool_with_schema):
    """Test running the tool with various inputs."""
    # Test with string query
    result = prolog_tool.run("john, Y")
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(sol == {"Y": "bianca"} for sol in result)

    # Test with full predicate
    result = prolog_tool.run("partner(john, Y)")
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(sol == {"Y": "bianca"} for sol in result)

    # Test with dictionary input
    result = prolog_tool_with_schema.run({"X": "john", "Y": None})
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(sol == {"Y": "bianca"} for sol in result)

    # Test with pedantic object input
    args = prolog_tool_with_schema.prolog.prolog_config.query_schema(X="john", Y=None)
    result = prolog_tool_with_schema.run(args)
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(sol == {"Y": "bianca"} for sol in result)


def test_tool_arun(prolog_tool):
    """Test running the tool asynchronously."""
    import asyncio

    async def async_test():
        result = await prolog_tool.arun("john, Y")
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(sol == {"Y": "bianca"} for sol in result)

    asyncio.run(async_test())


def test_schema_validation(prolog_tool_with_schema):
    """Test tool with schema validation."""
    # Test with valid dict input
    result = prolog_tool_with_schema.run({"X": "john", "Y": None})
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(sol == {"Y": "bianca"} for sol in result)

    # Test with invalid dict input
    with pytest.raises(ValidationError):
        prolog_tool_with_schema.run({"invalid_field": "value"})


def test_tool_error_handling(prolog_tool):
    """Test error handling in the tool."""
    # Test with invalid predicate
    with pytest.raises(ToolException):
        prolog_tool.run("invalid_predicate(X)")

    # Test with incorrect arity
    with pytest.raises(ToolException):
        prolog_tool.run("partner(X, Y, Z)")

    # Test with syntax error
    with pytest.raises(ToolException):
        prolog_tool.run("partner(X, Y")


def test_tool_with_different_configs():
    """Test tool initialization with different configurations."""
    # Test with minimal config
    minimal_tool = PrologTool(
        name="minimal",
        description="Minimal tool",
        prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
    )
    assert minimal_tool.prolog is not None

    # Test with default predicate
    default_predicate_tool = PrologTool(
        name="minimal",
        description="Minimal tool",
        prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl", default_predicate="partner"),
    )
    assert default_predicate_tool.prolog is not None

    # Test with input schema
    schema = PrologRunnable.create_schema("partner", ["X", "Y"])
    input_schema_tool = PrologTool(
        name="minimal",
        description="Minimal tool",
        prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl", query_schema=schema),
    )
    assert input_schema_tool.prolog is not None

    # Test with custom flags
    custom_tool = PrologTool(
        name="custom",
        description="Custom tool",
        prolog_config=PrologConfig(
            rules_file=TEST_DIR / "family.pl", prolog_flags={"debug": "true"}
        ),
    )
    assert custom_tool.prolog is not None


def test_tool_invalid_initialization():
    """Test invalid tool initialization scenarios."""
    # Test with missing required arguments
    with pytest.raises(TypeError):
        PrologTool()  # type: ignore

    # Test with invalid rules file
    with pytest.raises(PrologFileNotFoundError):
        PrologTool(
            name="invalid",
            description="Invalid tool",
            prolog_config=PrologConfig(rules_file="nonexistent.pl"),
        )

    # Test with func parameter (should raise error)
    with pytest.raises(TypeError):
        PrologTool(
            name="invalid",
            description="Invalid tool",
            prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
            func=lambda x: x,
        )


def test_tool_response_format():
    """Test tool with different response format configurations."""
    # Test with default response format
    tool = PrologTool(
        name="default",
        description="Default format",
        prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
        response_format="content",
    )
    result = tool.run("partner(john, Y)")
    assert isinstance(result, list)

    # Artifacts are not yet supported
    with pytest.raises(ValueError):
        tool = PrologTool(
            name="default",
            description="Default format",
            prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
            response_format="content_and_artifact",
        )
        result = tool.run("partner(john, Y)")
        # assert isinstance(result, tuple)

    # Test with invalid response format
    with pytest.raises(ValueError):
        PrologTool(
            name="invalid",
            description="Invalid format",
            prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
            response_format="invalid",
        )


def test_tool_with_callbacks():
    """Test tool with callback handling."""
    callback_called = False

    class TestCallback(BaseCallbackHandler):
        def on_tool_start(self, serialized: Dict, input_str: str, **kwargs: Any) -> None:
            nonlocal callback_called
            callback_called = True
            assert input_str == "john, Y"

    tool = PrologTool(
        name="callback_test",
        description="Test callbacks",
        prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
        callbacks=[TestCallback()],
    )

    tool.run("partner(john, Y)")
    assert callback_called


@pytest.mark.asyncio
async def test_tool_async_callbacks():
    """Test tool with async callback handling."""
    callback_called = False

    class TestAsyncCallback(BaseCallbackHandler):
        async def on_tool_start(self, serialized: Dict, input_str: str, **kwargs: Any) -> None:
            nonlocal callback_called
            callback_called = True
            assert input_str == "partner(john, Y)"

    tool = PrologTool(
        name="async_callback_test",
        description="Test async callbacks",
        prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
        callbacks=[TestAsyncCallback()],
    )

    await tool.arun("partner(john, Y)")
    assert callback_called


def test_tool_metadata():
    """Test tool metadata handling."""
    metadata = {"version": "1.0", "author": "test"}
    tool = PrologTool(
        name="metadata_test",
        description="Test metadata",
        prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
        metadata=metadata,
    )

    assert tool.metadata == metadata
    assert "prolog_config" in tool.prolog.metadata


def test_tool_tags():
    """Test tool tags handling."""
    tags = ["test", "family"]
    tool = PrologTool(
        name="tags_test",
        description="Test tags",
        prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
        tags=tags,
    )

    assert all(tag in tool.tags for tag in tags)
    assert "prolog" in tool.prolog.tags


def test_tool_result_types(prolog_tool):
    """Test different types of results from the tool."""
    # Test list result
    result = prolog_tool.run("john, Y")
    assert isinstance(result, list)
    assert len(result) == 2

    # Test True result
    result = prolog_tool.run("john, bianca")
    assert result is True

    # Test False result
    result = prolog_tool.run("john, invalid_person")
    assert result is False


def test_tool_zero_arity(zero_arity_tool):
    """Test tool with zero-arity predicates."""
    # Test with None input. Requires query_schema definition.
    result = zero_arity_tool.run(None)
    assert result is True

    # Test with empty dictionary. Requires query_schema definition.
    result = zero_arity_tool.run({})
    assert result is True

    # Test with empty string
    result = zero_arity_tool.run("")
    assert result is True

    # Test with explicit predicate
    result = zero_arity_tool.run("hello()")
    assert result is True


@pytest.mark.asyncio
async def test_tool_streaming(prolog_tool):
    """Test tool with streaming results."""

    # Test synchronous streaming
    stream_results = prolog_tool.stream("partner(X, Y)")
    assert isinstance(stream_results, Iterator)
    results = list(stream_results)
    assert len(results) > 0

    # Test asynchronous streaming
    async_stream = prolog_tool.astream("partner(X, Y)")
    assert isinstance(async_stream, AsyncIterator)
    async_results = [result async for result in async_stream]
    assert len(async_results) > 0


def test_tool_batch_processing(prolog_tool):
    """Test tool batch processing capabilities."""
    queries = [
        "john, Y",
        "partner(peter, patricia)",
        "invalid_query",
    ]

    # Test with return_exceptions=True
    results = prolog_tool.batch(queries, return_exceptions=True)
    assert len(results) == 3
    assert isinstance(results[0], list)  # Valid query
    assert results[1] is True  # True result
    assert isinstance(results[2], ToolException)  # Error

    # Test with return_exceptions=False
    with pytest.raises(ToolException):
        prolog_tool.batch(queries, return_exceptions=False)


@pytest.mark.asyncio
async def test_tool_async_batch(prolog_tool):
    """Test tool async batch processing."""
    queries = [
        "partner(john, Y)",
        "partner(peter, patricia)",
    ]

    results = await prolog_tool.abatch(queries)
    assert len(results) == 2
    assert isinstance(results[0], list)
    assert results[1] is True


def test_tool_verbose_mode():
    """Test tool in verbose mode."""
    output_captured = []

    class VerboseCallback(BaseCallbackHandler):
        def on_tool_start(self, serialized: Dict, input_str: str, **kwargs: Any) -> None:
            output_captured.append(f"Starting: {input_str}")

        def on_tool_end(self, output: str, **kwargs: Any) -> None:
            output_captured.append(f"Ending: {output}")

    tool = PrologTool(
        name="verbose_test",
        description="Test verbose mode",
        prolog_config=PrologConfig(rules_file=TEST_DIR / "family.pl"),
        verbose=True,
        callbacks=[VerboseCallback()],
    )

    tool.run("partner(john, Y)")
    assert len(output_captured) == 2
    assert "Starting: " in output_captured[0]
    assert "Ending: " in output_captured[1]


def test_tool_input_validation(prolog_tool, prolog_tool_with_schema):
    """Test tool input validation."""
    # Test with valid inputs
    expected_result = {"Y": "bianca"}
    assert expected_result in prolog_tool.run("partner(john, Y)")
    assert expected_result in prolog_tool.run("john, Y")
    assert expected_result in prolog_tool_with_schema.run({"X": "john", "Y": "Y"})
    assert expected_result in prolog_tool_with_schema.run({"X": "john", "Y": None})

    # Test with invalid inputs
    with pytest.raises(TypeError):
        prolog_tool.run(123)  # type: ignore

    with pytest.raises(TypeError):
        prolog_tool.run(None)

    with pytest.raises(ToolException):
        prolog_tool.run("invalid_query")

    with pytest.raises(ToolException):
        prolog_tool.run({"invalid_field": "value"})


def test_tool_error_propagation(prolog_tool):
    """Test how different types of errors are propagated."""
    # Test syntax error
    with pytest.raises(ToolException) as exc_info:
        prolog_tool.run("partner(")
    assert "mismatched parentheses in query" in str(exc_info.value).lower()

    # Test undefined predicate
    with pytest.raises(ToolException) as exc_info:
        prolog_tool.run("undefined_pred(X)")
    assert "undefined_pred" in str(exc_info.value).lower()

    # Test invalid arity
    with pytest.raises(ToolException) as exc_info:
        prolog_tool.run("partner(X, Y, Z)")  # partner is binary
    assert "there are definitions for" in str(exc_info.value).lower()


def test_tool_config_inheritance():
    """Test tool configuration inheritance behavior."""
    parent_config = PrologConfig(
        rules_file=TEST_DIR / "family.pl",
        default_predicate="partner",
        prolog_flags={"debug": "true"},
    )

    # Create tool with parent config
    tool = PrologTool(
        name="inheritance_test",
        description="Test config inheritance",
        prolog_config=parent_config,
    )

    # Verify inherited configuration
    assert tool.prolog.prolog_config.rules_file == parent_config.rules_file
    assert tool.prolog.prolog_config.default_predicate == parent_config.default_predicate
    assert tool.prolog.prolog_config.prolog_flags == parent_config.prolog_flags

    # Test that changes to parent config don't affect tool
    parent_config.default_predicate = "different"
    assert tool.prolog.prolog_config.default_predicate == "partner"
