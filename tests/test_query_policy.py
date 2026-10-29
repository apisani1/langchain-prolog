"""Tests for the query policy that stops queries from calling anything but the rules and safe predicates."""

from pathlib import Path

import janus_swi as janus
import pytest
from langchain_core.tools import ToolException
from pydantic import ValidationError

from langchain_prolog import (
    PrologConfig,
    PrologQueryNotAllowedError,
    PrologRunnable,
    PrologRuntimeError,
    PrologTool,
    PrologValueError,
)


TEST_DIR = Path(__file__).parent / "test_scripts"

# Rules are loaded into one Prolog process shared by every test, so each test uses its own predicate names.
FAMILY_RULES = """
policy_parent(john, bianca, mary).
policy_parent(john, bianca, michael).
policy_parent(peter, patricia, jennifer).
policy_partner(X, Y) :- policy_parent(X, Y, _).
policy_greet :- write('hello'), nl.
"""


@pytest.fixture
def rules_file(tmp_path):
    path = tmp_path / "family_policy.pl"
    path.write_text(FAMILY_RULES)
    return path


@pytest.fixture
def runnable(rules_file):
    schema = PrologRunnable.create_schema("policy_partner", ["X", "Y"])
    return PrologRunnable(PrologConfig(rules_file=rules_file, default_predicate="policy_partner", query_schema=schema))


@pytest.fixture
def tool(rules_file):
    schema = PrologRunnable.create_schema("policy_partner", ["X", "Y"])
    return PrologTool(
        name="policy_tool",
        description="Partners",
        prolog_config=PrologConfig(rules_file=rules_file, default_predicate="policy_partner", query_schema=schema),
    )


@pytest.fixture
def string_tool(rules_file):
    return PrologTool(
        name="policy_string_tool",
        description="Partners",
        prolog_config=PrologConfig(rules_file=rules_file, default_predicate="policy_partner"),
    )


def assert_not_allowed(runnable, query):
    with pytest.raises(PrologQueryNotAllowedError):
        runnable.invoke(query)


# --- The attacks the policy exists for ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "shell('touch {marker}')",
        "policy_partner(X, Y), shell('touch {marker}')",
        "shell('touch {marker}'), policy_partner(X, Y)",
        "(policy_partner(X, Y) ; shell('touch {marker}'))",
        "(fail -> true ; shell('touch {marker}'))",
        "\\+ shell('touch {marker}')",
        "once(shell('touch {marker}'))",
        "ignore(shell('touch {marker}'))",
        "forall(true, shell('touch {marker}'))",
        "findall(X, shell('touch {marker}'), L)",
        "bagof(X, Y^shell('touch {marker}'), L)",
        "setof(X, shell('touch {marker}'), L)",
        "aggregate_all(count, shell('touch {marker}'), C)",
        "call(shell('touch {marker}'))",
        "G = shell('touch {marker}'), call(G)",
        "system:shell('touch {marker}')",
        "user:shell('touch {marker}')",
        "process_create(path(touch), ['{marker}'], [])",
        "open('{marker}', write, S), close(S)",
        "tell('{marker}')",
        "delete_file('{marker}')",
        "consult('{marker}')",
        "consult_ex('{marker}')",
        "safe_query:register_rules('{marker}')",
        "halt",
        "halt(1)",
    ],
)
def test_dangerous_goals_are_refused_and_have_no_effect(runnable, tmp_path, query):
    marker = tmp_path / "marker"
    with pytest.raises(PrologQueryNotAllowedError):
        runnable.invoke(query.format(marker=marker))
    assert not marker.exists()


@pytest.mark.parametrize(
    "query",
    [
        # The library's own predicates are visible to queries and must not be callable
        "register_rules('{marker}')",
        "prepare_query('true', any, '', 0, [], S, M)",
        "load_files('{marker}')",
        "ensure_loaded('{marker}')",
        "use_module('{marker}')",
        # Hiding a goal in layout or comments, or where a quoting rule might confuse a check
        "policy_partner(X, Y)\n, shell('touch {marker}')",
        "policy_partner(X, Y), % a comment\n shell('touch {marker}')",
        "X = 0'a, shell('touch {marker}')",
        # Goals built at run time
        "term_to_atom(T, 'shell(ls)'), call(T)",
        "maplist(shell, [ls])",
        "not(shell(ls))",
        "thread_create(shell(ls), Id)",
        "forall(policy_partner(X, _), forall(true, shell(ls)))",
        "(policy_partner(john, _) -> (true ; shell(ls)) ; true)",
        # Changing the language or the environment
        "op(200, xfy, policy_partner)",
        "set_prolog_flag(double_quotes, codes)",
        "getenv('HOME', H)",
    ],
)
def test_more_ways_to_run_what_the_policy_forbids(runnable, tmp_path, query):
    marker = tmp_path / "marker"
    marker.write_text("x = 1.\n")  # a real file, so that a load would run it
    with pytest.raises(PrologRuntimeError):
        runnable.invoke(query.format(marker=marker))


def test_a_file_the_query_names_is_not_loaded(runnable, tmp_path):
    evil = tmp_path / "evil.pl"
    evil.write_text(f"policy_evil(1).\n:- shell('touch {tmp_path / 'ran'}').\n")
    for query in [f"consult('{evil}')", f"load_files('{evil}')", f"register_rules('{evil}'), policy_evil(X)"]:
        with pytest.raises(PrologRuntimeError):
            runnable.invoke(query)
    assert not (tmp_path / "ran").exists()
    with pytest.raises(PrologRuntimeError):
        runnable.invoke("policy_evil(X)")


def test_database_cannot_be_changed(runnable):
    for query in ["assertz(policy_evil(1))", "asserta(policy_evil(1))", "retract(policy_parent(john, _, _))"]:
        assert_not_allowed(runnable, query)
    assert runnable.invoke("policy_parent(john, X, Y)") == [
        {"X": "bianca", "Y": "mary"},
        {"X": "bianca", "Y": "michael"},
    ]


@pytest.mark.parametrize(
    "query",
    [
        "G",  # unbound goal
        "policy_partner(X, Y), G",
        ":- shell(ls)",  # directive
        "policy_partner(X, Y) :- shell(ls)",  # clause
        "policy_partner(a, b). shell(ls).",  # second term after the first one
        "policy_partner(a, b). :- shell(ls).",
        "42",  # not callable
        "[shell(ls)]",
    ],
)
def test_shapes_that_are_not_a_plain_query_are_refused(runnable, query):
    with pytest.raises(PrologRuntimeError):
        runnable.invoke(query)


def test_the_closing_full_stop_is_optional(runnable):
    assert runnable.invoke("policy_partner(john, Y)") == runnable.invoke("policy_partner(john, Y).")
    assert runnable.invoke("policy_partner(john, Y).  ") == runnable.invoke("policy_partner(john, Y)")


# --- Injection through the values of a schema or through arguments-only queries ---------------------------------


@pytest.mark.parametrize(
    "x",
    [
        "a, _), shell('touch {marker}'), policy_partner(_",
        "a, b), shell('touch {marker}'), policy_partner(c",
        "a), shell('touch {marker}'",
    ],
)
def test_schema_value_cannot_add_goals(runnable, tmp_path, x):
    marker = tmp_path / "marker"
    with pytest.raises(PrologRuntimeError):
        runnable.invoke({"X": x.format(marker=marker), "Y": None})
    assert not marker.exists()


def test_schema_value_cannot_change_the_number_of_arguments(runnable):
    # Without the check this builds policy_partner(john, bianca, extra), which would ask for another predicate
    with pytest.raises(PrologQueryNotAllowedError, match="single call of policy_partner/2"):
        runnable.invoke({"X": "john, bianca", "Y": "extra"})


def test_schema_input_in_the_tool_is_checked_too(tool, tmp_path):
    marker = tmp_path / "marker"
    with pytest.raises(ToolException):
        tool.invoke({"X": f"a, b), shell('touch {marker}'), policy_partner(c", "Y": "d"})
    assert not marker.exists()


@pytest.mark.parametrize(
    "arguments",
    [
        "john, Y), shell('touch {marker}'), policy_partner(a, (b",
        "john, Y), (shell('touch {marker}'), true",
        "X), halt, policy_partner(Y",
    ],
)
def test_arguments_only_query_cannot_add_goals(runnable, tmp_path, arguments):
    marker = tmp_path / "marker"
    with pytest.raises((PrologRuntimeError, PrologValueError)):
        runnable.invoke(arguments.format(marker=marker))
    assert not marker.exists()


def test_arguments_only_query_is_one_call_of_the_default_predicate(runnable):
    assert runnable.invoke("john, Y") == [{"Y": "bianca"}, {"Y": "bianca"}]


def test_tool_refuses_what_the_runnable_refuses(string_tool, tmp_path):
    marker = tmp_path / "marker"
    with pytest.raises(ToolException, match="not allowed"):
        string_tool.run(f"shell('touch {marker}')")
    assert not marker.exists()


def test_stream_and_batch_are_checked(runnable, tmp_path):
    marker = tmp_path / "marker"
    with pytest.raises(PrologQueryNotAllowedError):
        list(runnable.stream(f"shell('touch {marker}')"))
    results = runnable.batch(["policy_partner(john, Y)", f"shell('touch {marker}')"], return_exceptions=True)
    assert isinstance(results[0], list)
    assert isinstance(results[1], PrologRuntimeError)
    assert not marker.exists()


def test_refusal_is_a_runtime_error(runnable):
    """Code that caught PrologRuntimeError for failed queries keeps working."""
    with pytest.raises(PrologRuntimeError):
        runnable.invoke("shell(ls)")


# --- What must keep working ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected",
    [
        ("policy_partner(john, Y)", [{"Y": "bianca"}, {"Y": "bianca"}]),
        ("policy_partner(X, Y), X \\= john", [{"X": "peter", "Y": "patricia"}]),
        ("policy_partner(peter, patricia)", True),
        ("policy_partner(nobody, _)", False),
        ("findall(X, policy_partner(X, _), L), X = 1", [{"X": 1, "L": ["john", "john", "peter"]}]),
        ("setof(X, Y^policy_partner(X, Y), L), X = 1, Y = 2", [{"X": 1, "Y": 2, "L": ["john", "peter"]}]),
        ("aggregate_all(count, policy_partner(_, _), N)", [{"N": 3}]),
        ("member(X, [1, 2, 3]), X > 1, Y is X * 2", [{"X": 2, "Y": 4}, {"X": 3, "Y": 6}]),
        ("\\+ policy_partner(nobody, _)", True),
        ("forall(member(_, [1, 2]), 1 > 0)", True),
        ("atom_length(hello, N)", [{"N": 5}]),
        ("X = 'A b', atom_string(X, S)", [{"X": "A b", "S": "A b"}]),
        ("length(L, 2), L = [a|_], L = [_, b]", [{"L": ["a", "b"]}]),
    ],
)
def test_legitimate_queries(runnable, query, expected):
    assert runnable.invoke(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "policy_partner(X, Y)",
        "policy_partner(john, _Z)",
        "findall(X, policy_partner(X, _), L)",  # janus cannot return unbound variables, with or without the policy
        "X = f(A, B, A), A = 1",
        "atom(a), X = 'it''s', Y = \"a b\", Z = [1, 2.5, 0'a]",
        "atom(a), X is 2 ** 10 mod 7",
        "(X = 1 ; X = 2), X > 1",
        "(policy_partner(john, Y) -> true ; Y = none)",
        "policy_partner(john, Y), !",
        "atom(a), X = a:b:c",
        "atom(a), X = (a :- b, c)",
        "atom(a), X = {a, b}",
        "atom(a), X = - 1, Y is - X",
        "atom(a), X == Y",
        "policy_partner(john Y)",
    ],
)
def test_checked_queries_give_the_answers_of_unchecked_queries(rules_file, query):
    """Re-generating the text of a checked query must not change what it means."""
    checked = PrologRunnable(PrologConfig(rules_file=rules_file))
    unchecked = PrologRunnable(PrologConfig(rules_file=rules_file, unrestricted_queries=True))

    def outcome(r):
        try:
            return r.invoke(query)
        except PrologRuntimeError as e:
            return type(e).__mro__[-3].__name__, "Arguments are not sufficiently instantiated" in str(e)

    assert outcome(checked) == outcome(unchecked)


def test_zero_arity_and_default_predicate_still_work(rules_file):
    zero = PrologRunnable(PrologConfig(rules_file=rules_file, default_predicate="policy_greet"))
    assert zero.invoke(None) is True
    assert zero.invoke("policy_greet()") is True


def test_prolog_kwargs_still_reach_the_query(runnable):
    """The variable names of a checked query are the ones the caller wrote, so `inputs` can still bind them."""
    config = {"configurable": {"prolog_kwargs": {"inputs": {"Who": "john"}}}}
    assert runnable.invoke("policy_partner(Who, Y)", config=config) == [{"Y": "bianca"}, {"Y": "bianca"}]


def test_variable_names_and_quoted_atoms_survive_the_check(runnable):
    result = runnable.invoke("Person = 'John Smith', Other = \"text\", policy_partner(john, Child)")
    assert result[0]["Person"] == "John Smith"
    # What "text" reads as depends on the double_quotes flag, which an init file may change, so compare against
    # an unchecked query instead of a fixed value
    assert result[0]["Other"] == janus.query_once('Other = "text"')["Other"]
    assert result[0]["Child"] == "bianca"


def test_argument_mistakes_say_which_arities_exist(runnable):
    with pytest.raises(PrologQueryNotAllowedError, match=r"policy_partner/2 is defined"):
        runnable.invoke("policy_partner(a, b, c)")


def test_syntax_errors_are_reported(runnable):
    with pytest.raises(PrologRuntimeError, match="Syntax error"):
        runnable.invoke("policy_partner(john, [Y)")


# --- Which predicates the rules files provide ---------------------------------------------------------------------


def test_predicates_of_included_files_are_callable(tmp_path):
    (tmp_path / "policy_part.pl").write_text("policy_included(1).\npolicy_included(2).\n")
    rules = tmp_path / "policy_main.pl"
    rules.write_text(":- include(policy_part).\npolicy_main(X) :- policy_included(X).\n")
    r = PrologRunnable(PrologConfig(rules_file=rules))
    assert r.invoke("policy_main(X)") == [{"X": 1}, {"X": 2}]
    assert r.invoke("policy_included(X)") == [{"X": 1}, {"X": 2}]


def test_rules_files_can_use_libraries_but_queries_cannot_reach_them(tmp_path):
    rules = tmp_path / "policy_lib.pl"
    rules.write_text(":- use_module(library(readutil)).\n" "policy_files(L) :- findall(X, member(X, [a, b]), L).\n")
    r = PrologRunnable(PrologConfig(rules_file=rules))
    assert r.invoke("policy_files(L)") == [{"L": ["a", "b"]}]
    for query in ["read_file_to_string('x', S, [])", "read_term_from_atom(a, T, [])"]:
        assert_not_allowed(r, query)


def test_libraries_outside_the_prolog_home_are_not_callable(tmp_path):
    """A library a rules file loads stays out of reach of queries, even when it is not a system library."""
    (tmp_path / "policy_extlib.pl").write_text(":- module(policy_extlib, [policy_ext_run/1]).\npolicy_ext_run(x).\n")
    rules = tmp_path / "policy_uses_ext.pl"
    rules.write_text(":- use_module(policy_extlib).\npolicy_via_ext(X) :- policy_ext_run(X).\n")
    r = PrologRunnable(PrologConfig(rules_file=rules))
    assert r.invoke("policy_via_ext(X)") == [{"X": "x"}]
    assert_not_allowed(r, "policy_ext_run(X)")


def test_a_rules_file_that_is_a_module_exports_its_predicates(tmp_path):
    rules = tmp_path / "policy_mod_rules.pl"
    rules.write_text(
        ":- module(policy_mod_rules, [policy_exported/1]).\n"
        "policy_exported(X) :- policy_hidden(X).\n"
        "policy_hidden(1).\n"
    )
    r = PrologRunnable(PrologConfig(rules_file=rules))
    assert r.invoke("policy_exported(X)") == [{"X": 1}]
    assert_not_allowed(r, "policy_hidden(X)")


def test_a_rule_may_use_what_a_query_may_not(tmp_path):
    """The rules file is trusted code; only the query is checked."""
    marker = tmp_path / "marker"
    rules = tmp_path / "policy_trusted.pl"
    rules.write_text(f"policy_touch :- shell('touch {marker}').\n")
    r = PrologRunnable(PrologConfig(rules_file=rules, default_predicate="policy_touch"))
    assert r.invoke(None) is True
    assert marker.exists()


def test_rules_path_with_a_quote_is_loaded_as_a_path(tmp_path):
    rules = tmp_path / "it's a rules file.pl"
    rules.write_text("policy_quoted(yes).\n")
    r = PrologRunnable(PrologConfig(rules_file=rules))
    assert r.invoke("policy_quoted(X)") == [{"X": "yes"}]


def test_rules_loaded_later_become_callable(runnable, tmp_path):
    rules = tmp_path / "policy_later.pl"
    rules.write_text("policy_later(ok).\n")
    assert_not_allowed(runnable, "policy_later(X)")
    runnable.load_rules(rules)
    assert runnable.invoke("policy_later(X)") == [{"X": "ok"}]


# --- Configuration ------------------------------------------------------------------------------------------------


def test_allowed_predicates_extend_the_policy(rules_file):
    config = {"rules_file": rules_file, "allowed_predicates": ["format/2"]}
    assert PrologRunnable(config).invoke("format('~w', [x])") is True
    assert_not_allowed(PrologRunnable(PrologConfig(rules_file=rules_file)), "format('~w', [x])")


@pytest.mark.parametrize("entry", ["format", "format/x", "Format/2", "shell(ls)/1", "a/b/2", "", "format/2, shell/1"])
def test_allowed_predicates_must_be_indicators(entry):
    with pytest.raises((PrologValueError, ValidationError)):
        PrologConfig(allowed_predicates=[entry])


def test_allowed_predicates_do_not_open_other_predicates(rules_file):
    r = PrologRunnable(PrologConfig(rules_file=rules_file, allowed_predicates=["format/2"]))
    assert_not_allowed(r, "format('~w', [x]), shell(ls)")
    assert_not_allowed(r, "format(user_output, '~w', [x])")  # format/3 was not allowed


def test_unrestricted_queries_turn_the_policy_off(rules_file):
    r = PrologRunnable(PrologConfig(rules_file=rules_file, unrestricted_queries=True))
    assert r.invoke("assertz(policy_unrestricted(1))") is True
    assert r.invoke("policy_unrestricted(X)") == [{"X": 1}]


def test_policy_is_on_by_default(rules_file):
    assert PrologConfig(rules_file=rules_file).unrestricted_queries is False
    assert PrologConfig(rules_file=rules_file).allowed_predicates == []
