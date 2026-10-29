## Query Safety

Prolog is a general programming language: `shell/1` runs a command, `assertz/1` changes the database and `open/3`
reads and writes files. A query that reaches the interpreter as text can do any of that, and the query of a
`PrologTool` is written by an LLM, which can be steered by anything it reads.

So queries are checked before they run. The text is parsed, every goal in it is checked, and the query that runs is
generated from the checked term, never copied from the text. A query may call:

- control constructs (`,`, `;`, `->`, `\+`) and the meta predicates `findall`, `bagof`, `setof`, `aggregate_all`,
  `forall`, `once` and `ignore`, whose goal arguments are checked in turn;
- the predicates defined by your rules files, and the files they `include` or load, which are trusted;
- a fixed set of predicates that only compute: unification and comparison, arithmetic, type checks and the usual list,
  atom and string predicates (`member/2`, `append/3`, `length/2`, `atom_length/2`, `sub_atom/5` and the like);
- the predicates you list in `allowed_predicates`.

Everything else is refused with a `PrologQueryNotAllowedError`, which is a `PrologRuntimeError`. That includes
module-qualified goals (`user:shell(ls)`), goals that are not known until run time (`call/1`, an unbound variable),
directives, clauses and anything after the first term. With a schema, a value cannot add goals or arguments: the query
must be one call of the schema predicate with one argument per field.

```python
from langchain_prolog import PrologConfig, PrologRunnable

prolog = PrologRunnable(PrologConfig(rules_file="family.pl"))
prolog.invoke("shell('rm -rf ~')")
```
```text
PrologQueryNotAllowedError: Prolog execution error: query not allowed: Predicate shell/1 is not allowed in queries
```

Your rules are not checked: `shell/1` inside a rule works, so a rule can offer a controlled version of something the
queries may not do.

### Allowing more predicates

List extra predicates as `name/arity`:

```python
config = PrologConfig(rules_file="family.pl", allowed_predicates=["format/2"])
```

Allow only predicates that cannot hurt when an LLM picks their arguments.

### Turning the check off

`unrestricted_queries=True` skips the check. Use it only when every query comes from your own code, and never for a
`PrologTool` that an LLM drives. A warning is logged when it is on.

### What the check does not cover

- Resource use. `between(1, inf, X), fail`, `length(L, N)` with both unbound and huge arithmetic all run until they
  finish. Run untrusted queries in a process with limits on time and memory.
- Your rules. A rule that calls one of its own arguments (`call/N`, `assertz/1`, `shell/1`) hands that power to every
  query that can reach it, so write rules for queries you do not control the way you would write a public API.
- A shared interpreter. All runnables in a process share one Prolog database, so a query can call the predicates of any
  rules file loaded in the process, not only its own.
