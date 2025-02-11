# test_prolog.py
from pathlib import Path

import pytest
from pydantic import BaseModel

from langchain_prolog import (
    PrologConfig,
    PrologFileNotFoundError,
    PrologInput,
    PrologRunnable,
    PrologRuntimeError,
    PrologValueError,
)


# Get the path to the test directory
TEST_DIR = Path(__file__).parent / "test_scripts"


@pytest.fixture
def prolog_runnable():
    """Create a PrologRunnable instance with test rules."""
    SolveArgs = PrologRunnable.create_schema(predicate_name="partner", arg_names=["X", "Y"])
    config = PrologConfig(
        rules_file=TEST_DIR / "family.pl",
        default_predicate="partner",
        query_schema=SolveArgs,
    )
    return PrologRunnable(
        prolog_config=config,
    )


@pytest.fixture
def runnable_no_default():
    config = PrologConfig(rules_file=TEST_DIR / "family.pl")
    return PrologRunnable(prolog_config=config)


@pytest.fixture
def runnable_zero_arity():
    config = PrologConfig(rules_file=TEST_DIR / "family.pl", default_predicate="hello")
    return PrologRunnable(prolog_config=config)


@pytest.fixture
def solve_args():
    """Create the schema for partner/2 predicate."""
    return PrologRunnable.create_schema(predicate_name="partner", arg_names=["X", "Y"])


@pytest.mark.asyncio
async def test_invoke_all_solutions(prolog_runnable):
    """Test invoke with query that returns all solutions."""
    result = await prolog_runnable.ainvoke({"X": None, "Y": None})
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0] == {"X": "john", "Y": "bianca"}
    assert result[1] == {"X": "john", "Y": "bianca"}
    assert result[2] == {"X": "peter", "Y": "patricia"}


@pytest.mark.asyncio
async def test_invoke_filtered_solutions(prolog_runnable):
    """Test invoke with query that returns filtered solutions."""
    result = await prolog_runnable.ainvoke("john, Y")
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(sol == {"Y": "bianca"} for sol in result)


@pytest.mark.asyncio
async def test_invoke_with_model(prolog_runnable, solve_args):
    """Test invoke with Pydantic model input."""
    args = solve_args(X=None, Y=None)
    result = await prolog_runnable.ainvoke(args)
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0] == {"X": "john", "Y": "bianca"}
    assert result[1] == {"X": "john", "Y": "bianca"}
    assert result[2] == {"X": "peter", "Y": "patricia"}


@pytest.mark.asyncio
async def test_full_predicate_query(prolog_runnable):
    """Test using full predicate syntax."""
    result = await prolog_runnable.ainvoke("partner(john, Y)")
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(sol == {"Y": "bianca"} for sol in result)


@pytest.mark.asyncio
async def test_invoke_true_result(prolog_runnable):
    """Test invoke with query that returns multiple True."""
    result = await prolog_runnable.ainvoke("john, bianca")
    assert result is True


@pytest.mark.asyncio
async def test_invoke_false_result(prolog_runnable):
    """Test invoke with query that returns False."""
    result = await prolog_runnable.ainvoke("john, patricia")
    assert result is False


@pytest.mark.asyncio
async def test_invoke_single_solution(prolog_runnable):
    """Test invoke with query that returns a single solution."""
    result = await prolog_runnable.ainvoke("peter, patricia")
    assert result is True


@pytest.mark.asyncio
async def test_zero_arity_predicate(runnable_no_default):
    """Test predicate with no arguments."""
    result = await runnable_no_default.ainvoke("hello()")
    assert result is True


@pytest.mark.asyncio
async def test_zero_arity_default_predicate(runnable_zero_arity):
    """Test default predicate with no arguments."""
    result = await runnable_zero_arity.ainvoke(None)
    assert result is True
    result = await runnable_zero_arity.ainvoke("")
    assert result is True


@pytest.mark.asyncio
async def test_stream_all_solutions(prolog_runnable):
    """Test stream with query that returns all solutions."""
    results = [result async for result in prolog_runnable.astream({"X": None, "Y": None})]
    assert len(results) == 3
    assert results[0] == [{"X": "john", "Y": "bianca"}]
    assert results[1] == [{"X": "john", "Y": "bianca"}]
    assert results[2] == [{"X": "peter", "Y": "patricia"}]


@pytest.mark.asyncio
async def test_stream_filtered_solutions(prolog_runnable):
    """Test stream with query that returns filtered solutions."""
    results = [result async for result in prolog_runnable.astream("john, Y")]
    assert len(results) == 2
    assert all(sol == [{"Y": "bianca"}] for sol in results)


@pytest.mark.asyncio
async def test_stream_with_model(prolog_runnable, solve_args):
    """Test stream with Pydantic model input."""
    args = solve_args(X=None, Y=None)
    results = [result async for result in prolog_runnable.astream(args)]
    assert len(results) == 3
    assert results[0] == [{"X": "john", "Y": "bianca"}]
    assert results[1] == [{"X": "john", "Y": "bianca"}]
    assert results[2] == [{"X": "peter", "Y": "patricia"}]


@pytest.mark.asyncio
async def test_stream_full_predicate(prolog_runnable):
    """Test streaming with full predicate syntax."""
    results = [result async for result in prolog_runnable.astream("partner(john, Y)")]
    assert len(results) == 2
    assert all(isinstance(r, list) and len(r) == 1 for r in results)
    assert all(r[0]["Y"] == "bianca" for r in results)


@pytest.mark.asyncio
async def test_stream_true_result(prolog_runnable):
    """Test stream with query that returns True."""
    results = [result async for result in prolog_runnable.astream("john, bianca")]
    assert len(results) == 1
    assert results[0] is True


@pytest.mark.asyncio
async def test_stream_false_result(prolog_runnable):
    """Test stream with query that returns False."""
    results = [result async for result in prolog_runnable.astream("john, patricia")]
    assert len(results) == 1
    assert results[0] is False


@pytest.mark.asyncio
async def test_stream_single_solution(prolog_runnable):
    """Test stream with query that returns a single solution."""
    results = [result async for result in prolog_runnable.astream("peter, patricia")]
    assert len(results) == 1
    assert results[0] is True


@pytest.mark.asyncio
async def test_batch_processing(prolog_runnable, solve_args):
    """Test batch processing with various input types."""
    batch_inputs: list[PrologInput] = [
        {"X": None, "Y": None},
        "john, Y",
        solve_args(X=None, Y=None),
        "john, bianca",
        "john, patricia",
        "peter, patricia",
    ]

    results = await prolog_runnable.abatch(batch_inputs)
    assert len(results) == 6
    assert isinstance(results[0], list)  # All solutions
    assert len(results[0]) == 3
    assert isinstance(results[1], list)  # john's solutions
    assert len(results[1]) == 2
    assert isinstance(results[2], list)  # All solutions via model
    assert len(results[2]) == 3
    assert results[3] is True  # True result
    assert results[4] is False  # False result
    assert results[5] is True  # Single solution


@pytest.mark.asyncio
async def test_mixed_predicate_styles(prolog_runnable):
    """Test mixing full and default predicate styles in batch."""
    batch_inputs = [
        "partner(john, Y)",  # full predicate
        "john, Y",  # default predicate
    ]
    results = await prolog_runnable.abatch(batch_inputs)
    assert len(results) == 2
    assert results[0] == results[1]


@pytest.mark.asyncio
async def test_mixed_batch_with_none(runnable_zero_arity):
    """Test batch processing with mixed inputs including None."""
    batch_inputs = [
        None,  # zero-arity default predicate
        "partner(john, Y)",  # full predicate
        "hello()",  # zero-arity explicit
    ]
    results = await runnable_zero_arity.abatch(batch_inputs)
    assert len(results) == 3
    assert results[0] is True  # hello() succeeds
    assert isinstance(results[1], list)  # partner query returns solutions
    assert results[2] is True  # hello() succeeds


@pytest.mark.asyncio
async def test_batch_as_completed(prolog_runnable, solve_args):
    """Test batch processing with various input types."""
    batch_inputs: list[PrologInput] = [
        {"X": None, "Y": None},
        "john, Y",
        solve_args(X=None, Y=None),
        "john, bianca",
        "john, patricia",
        "peter, patricia",
    ]

    results = [result async for result in prolog_runnable.abatch_as_completed(batch_inputs)]
    assert len(results) == 6
    assert isinstance(results[0][1], list)  # All solutions
    assert len(results[0][1]) == 3
    assert isinstance(results[1][1], list)  # john's solutions
    assert len(results[1][1]) == 2
    assert isinstance(results[2][1], list)  # All solutions via model
    assert len(results[2][1]) == 3
    assert results[3][1] is True  # True result
    assert results[4][1] is False  # False result
    assert results[5][1] is True  # Single solution


@pytest.mark.asyncio
async def test_no_default_predicate(runnable_no_default):
    """Test using argument-style query without default predicate."""
    with pytest.raises(PrologValueError) as exc_info:
        await runnable_no_default.ainvoke("john, Y")
    assert "No default predicate set" in str(exc_info.value)


@pytest.mark.asyncio
async def test_none_input_without_default_predicate(runnable_no_default):
    """Test None input without default predicate."""
    with pytest.raises(PrologValueError) as exc_info:
        await runnable_no_default.ainvoke(None)
    assert "Input data cannot be None" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_full_predicate(runnable_no_default):
    """Test invalid full predicate syntax."""
    with pytest.raises(PrologRuntimeError) as exc_info:
        await runnable_no_default.ainvoke("invalid_predicate(X, Y)")
    assert "Prolog execution error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_arity_full_predicate(runnable_no_default):
    """Test full predicate with wrong number of arguments."""
    with pytest.raises(PrologRuntimeError) as exc_info:
        await runnable_no_default.ainvoke("partner(X, Y, Z)")  # partner is binary
    assert "Prolog execution error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_malformed_predicate_syntax(runnable_no_default):
    """Test malformed predicate syntax."""
    with pytest.raises(PrologValueError) as exc_info:
        await runnable_no_default.ainvoke("partner(X, Y")  # Missing closing parenthesis
    assert "Mismatched parentheses in query" in str(exc_info.value)


@pytest.mark.asyncio
async def test_missing_rules_file():
    """Test initialization with non-existent rules file."""
    with pytest.raises(PrologFileNotFoundError) as exc_info:
        PrologRunnable({"rules_file": "nonexistent.pl"})
    assert "Prolog rules file not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_prolog_syntax(tmp_path):
    """Test loading rules with invalid Prolog syntax."""
    invalid_rules = tmp_path / "invalid.pl"
    invalid_rules.write_text("invalid_syntax(.")

    with pytest.raises(PrologRuntimeError) as exc_info:
        PrologRunnable({"rules_file": invalid_rules})
    assert str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_input_type(prolog_runnable):
    """Test invoke with invalid input type."""
    with pytest.raises(PrologValueError) as exc_info:
        await prolog_runnable.ainvoke(123)  # type: ignore
    assert "Invalid input type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dict_input_without_schema(runnable_no_default):
    with pytest.raises(PrologValueError) as exc_info:
        await runnable_no_default.ainvoke({"X": None, "Y": None})
    assert "missing schema" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_prolog_query(prolog_runnable):
    """Test with a query that causes a Prolog execution error."""
    with pytest.raises(PrologRuntimeError) as exc_info:
        await prolog_runnable.ainvoke("invalid_predicate(X)")
    assert "Prolog execution error" in str(exc_info.value)


# Schema creation tests
@pytest.mark.asyncio
async def test_schema_creation():
    """Test schema creation with various arguments."""
    schema = PrologRunnable.create_schema("test", ["arg1", "arg2"])
    assert issubclass(schema, BaseModel)
    assert "arg1" in schema.model_fields
    assert "arg2" in schema.model_fields


# Batch processing error handling
@pytest.mark.asyncio
async def test_batch_with_mixed_valid_invalid(prolog_runnable):
    """Test batch processing with mix of valid and invalid inputs."""
    batch_inputs = [
        {"X": None, "Y": None},  # valid
        123,  # invalid type
        "john, Y",  # valid
    ]

    with pytest.raises(PrologRuntimeError) as exc_info:
        await prolog_runnable.abatch(batch_inputs)  # type: ignore
    assert "Prolog batch execution error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_empty_batch(prolog_runnable):
    """Test batch processing with empty input list."""
    assert await prolog_runnable.abatch([]) == []


# Stream error handling
@pytest.mark.asyncio
async def test_stream_error_handling(prolog_runnable):
    """Test stream method error handling."""
    with pytest.raises(PrologRuntimeError) as exc_info:
        [result async for result in prolog_runnable.astream("invalid_predicate(X)")]
    assert "Prolog execution error" in str(exc_info.value)


# Edge cases
@pytest.mark.asyncio
async def test_invoke_with_empty_string_no_matching_arity(prolog_runnable):
    """Test invoke with empty string."""
    with pytest.raises(PrologRuntimeError) as exc_info:
        await prolog_runnable.ainvoke("")
    assert "Prolog execution error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_schema_with_empty_args():
    """Test schema creation with no arguments."""
    schema = PrologRunnable.create_schema("test", [])
    assert issubclass(schema, BaseModel)
    assert len(schema.model_fields) == 0


@pytest.mark.asyncio
async def test_multiple_rule_files(tmp_path):
    """Test loading multiple rule files."""
    # Create two rule files
    rules1 = tmp_path / "rules1.pl"
    rules1.write_text("fact1(a).")
    rules2 = tmp_path / "rules2.pl"
    rules2.write_text("fact2(b).")

    runnable = PrologRunnable(PrologConfig(rules_file=rules1, default_predicate="fact1"))
    runnable.load_rules(rules2)

    # Both rules should be available
    assert await runnable.ainvoke("a") is True

    # Test second predicate
    runnable.prolog_config.default_predicate = "fact2"
    assert await runnable.ainvoke("b") is True


@pytest.mark.asyncio
async def test_config_handling(prolog_runnable):
    """Test that config parameter is accepted but not affecting execution."""
    result1 = await prolog_runnable.ainvoke("john, Y")
    result2 = await prolog_runnable.ainvoke("john, Y", config={"some_config": "value"})
    assert result1 == result2


@pytest.mark.asyncio
async def test_kwargs_handling(prolog_runnable):
    """Test that valid Prolog query parameters are accepted."""
    # maxresult is a valid parameter for Prolog queries
    result1 = await prolog_runnable.ainvoke("john, Y", maxresult=1)
    result2 = await prolog_runnable.ainvoke("john, Y", maxresult=2)

    # First result should be the same
    assert result1[0] == result2[0]
    # Second result should have more solutions if available
    assert len(result1) <= len(result2)


@pytest.mark.asyncio
async def test_batch_with_exceptions(prolog_runnable):
    """Test batch processing with return_exceptions=True."""
    batch_inputs = [
        {"X": None, "Y": None},  # valid
        "invalid_query(X)",  # will cause error
        "john, Y",  # valid
    ]

    # With return_exceptions=True
    results = await prolog_runnable.abatch(batch_inputs, return_exceptions=True)
    assert isinstance(results[0], list)  # Valid query returns list of solutions
    assert isinstance(results[1], PrologRuntimeError)  # Error query returns PrologRuntimeError
    assert isinstance(results[2], list)  # Valid query returns list of solutions

    # With return_exceptions=False
    with pytest.raises(PrologRuntimeError):
        await prolog_runnable.abatch(batch_inputs, return_exceptions=False)


@pytest.mark.asyncio
async def test_batch_result_types(prolog_runnable):
    """Test different result types in batch processing."""
    batch_inputs = [
        {"X": None, "Y": None},  # multiple solutions -> list
        "john, bianca",  # success without bindings -> True
        "invalid_person, Y",  # no solutions -> False
        "invalid_query(X)",  # error -> PrologRuntimeError
    ]

    results = await prolog_runnable.abatch(batch_inputs, return_exceptions=True)

    assert isinstance(results[0], list)  # Multiple solutions
    assert results[1] is True  # Success without bindings
    assert results[2] is False  # No solutions
    assert isinstance(results[3], PrologRuntimeError)  # Error
