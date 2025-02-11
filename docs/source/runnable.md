## Runnable Interface

The PrologRunnable class allows the generation of langchain runnables that use Prolog rules to generate answers.

Let's assume that we have the following set of Prolog rules in the file family.pl:

```prolog
parent(john, bianca, mary).
parent(john, bianca, michael).
parent(peter, patricia, jennifer).
partner(X, Y) :- parent(X, Y, _).
```

There are three diferent ways to use a PrologRunnable to query Prolog:

#### 1) Using a Prolog runnable with a full predicate string

```python
from langchain_prolog import PrologConfig, PrologRunnable

config = PrologConfig(rules_file="family.pl")
prolog = PrologRunnable(prolog_config=config)
result = prolog.invoke("partner(X, Y)")
print(result)
```
We can pass a string representing a single predicate query. The invoke method will return `True`, `False` or a list of dictionaries with all the solutions to the query:
```python
[{'X': 'john', 'Y': 'bianca'},
 {'X': 'john', 'Y': 'bianca'},
 {'X': 'peter', 'Y': 'patricia'}]
 ```

#### 2) Using a Prolog runnable with a default predicate

```python
from langchain_prolog import PrologConfig, PrologRunnable

config = PrologConfig(rules_file="family.pl", default_predicate="partner")
prolog = PrologRunnable(prolog_config=config)
result = prolog.invoke("peter, X")
print(result)
```
When using a default predicate, only the arguments for the predicate are passed to the Prolog runable, as a single string. Following Prolog conventions, uppercase identifiers are variables and lowercase identifiers are values (atoms or strings):

```python
[{'X': 'patricia'}]
```

### 3) Using a Prolog runnable with a dictionary and schema validation

```python
from langchain_prolog import PrologConfig, PrologRunnable

schema = PrologRunnable.create_schema("partner", ["man", "woman"])
config = PrologConfig(rules_file="family.pl", query_schema=schema)
prolog = PrologRunnable(prolog_config=config)
result = prolog.invoke({"man": None, "woman": "bianca"})
print(result)
```
If a schema is defined, we can pass a dictionary using the names of the parameters in the schema as the keys in the dictionary. The values can represent Prolog variables (uppercase first letter) or strings (lower case first letter). A `None` value is interpreted as a variable and replaced with the key capitalized:
```python
[{'Man': 'john'}, {'Man': 'john'}]
```

You can also pass a Pydantic object generated with the schema to the invoke method:
```python
args = schema(man='M', woman='W')
result = prolog.invoke(args)
print(result)
```
Uppercase values are treated as variables:
```python
[{'M': 'john', 'W': 'bianca'},
 {'M': 'john', 'W': 'bianca'},
 {'M': 'peter', 'W': 'patricia'}]
 ```
