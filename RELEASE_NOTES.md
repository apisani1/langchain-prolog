## langchain-prolog v2.0.0

Prolog queries are now checked before they run. A `PrologTool` query is written by an LLM, and until this release it reached the interpreter unchecked, so it could call `shell/1`, `assertz/1` or open files with the privileges of your process. This release refuses those queries by default.

### Breaking Changes

- A query may call your rules, a fixed set of pure predicates (unification, comparison, arithmetic, type checks, list/atom/string predicates), the meta predicates `findall`, `bagof`, `setof`, `aggregate_all`, `forall`, `once` and `ignore` (whose goals are checked too), and anything you list in `allowed_predicates`. Everything else raises `PrologQueryNotAllowedError`.
- Refused goals include `shell/1`, `assertz/1`, file I/O, module-qualified goals, `call/1`, unbound goals, and anything after the first term.
- Predicates of libraries your rules file loads are no longer callable from queries; your rules can still use them. A rules file that is itself a module still exposes its exports.
- With a `query_schema` or `default_predicate`, a value can no longer add goals: the query must be a single call of that predicate.
- Wrong-arity calls now report which arities exist, e.g. `Predicate partner/3 is not allowed in queries, but partner/2 is defined`.

### Upgrading

- `PrologQueryNotAllowedError` is a `PrologRuntimeError`, so code that already catches `PrologRuntimeError` keeps working.
- If your queries call predicates outside your rules, list them: `PrologConfig(rules_file="family.pl", allowed_predicates=["format/2"])`. Allow only predicates that are harmless whatever arguments an LLM picks, and avoid meta predicates such as `maplist/2`, whose goal arguments are not checked.
- `unrestricted_queries=True` turns the check off and logs a warning. Use it only when every query comes from your own code.

### Added

- `PrologConfig.allowed_predicates` and `PrologConfig.unrestricted_queries`.
- `PrologQueryNotAllowedError`, exported from `langchain_prolog`.

### Security

- The rules file path is passed to Prolog as a value instead of being quoted into query text.

### Documentation

- New **Query Safety** guide covering what is allowed, how to allow more, and what the check does not cover (resource limits, rules that call their arguments, a shared interpreter).

**Full changelog**: https://github.com/apisani1/langchain-prolog/compare/v1.0.3...v2.0.0
