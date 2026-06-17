## Tool Interface

The PrologTool class allows the generation of langchain tools that use Prolog rules to generate answers.

See the Runnable Interface section for the conventions on hown to pass variables and values to the Prolog interpreter.

Let's use the following set of Prolog rules in the file `family.pl`:

```prolog
parent(john, bianca, mary).
parent(john, bianca, michael).
parent(peter, patricia, jennifer).
partner(X, Y) :- parent(X, Y, _).
```

There are two diferent ways to use a PrologTool to query Prolog:

### 1) Using a Prolog tool with an LLM and function calling

First create the Prolog tool:
```python
from langchain_prolog import PrologConfig, PrologRunnable, PrologTool

schema = PrologRunnable.create_schema("parent", ["man", "woman", "child"])
config = PrologConfig(
    rules_file="family.pl",
    query_schema=schema,
)
prolog_tool = PrologTool(
    prolog_config=config,
    name="family_query",
    description="""
        Query family relationships using Prolog.
        parent(X, Y, Z) implies only that Z is a child of X and Y.
        Input must be a dictionary like:
        {
            'man': 'richard',
            'woman': 'valery',
            'child': None,
        
        }
        Use 'None' to indicate a variable that need to be instantiated by Prolog
        The query will return:
            - 'True': if the relationship 'child' is a child of 'men' and 'women' holds.
            - 'False' if the relationship 'child' is a child of 'man' and 'woman' does not holds.
            - A list of dictionaries with all the answers to the Prolog query
        Do not use double quotes.
    """,
)
```

Then bind it to the LLM model and query the model:
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools([prolog_tool])
messages = [HumanMessage("Who are John's children?")]
response = llm_with_tools.invoke(messages)
messages.append(response)
print(response.tool_calls[0])
```
The LLM will respond with a tool call request:
```python
{'name': 'family_query',
 'args': {'man': 'john', 'woman': None, 'child': None},
 'id': 'call_V6NUsJwhF41G9G7q6TBmghR0',
 'type': 'tool_call'}
 ```
 The tool takes this request and queries the Prolog database:
 ```python
 tool_msg = prolog_tool.invoke(response.tool_calls[0])
messages.append(tool_msg)
print(tool_msg)
 ```
The tool returns a list with all the solutions for the query:
 ```python
 content='[{"Woman": "bianca", "Child": "mary"}, {"Woman": "bianca", "Child": "michael"}]'
 name='family_query'
 tool_call_id='call_V6NUsJwhF41G9G7q6TBmghR0'
 ```
 That we then pass to the LLM:
 ```python
 answer = llm_with_tools.invoke(messages)
 print(answer.content)
 ```
 And the LLM answers the original query using the tool response:
 ```python
 John has two children: Mary and Michael. Their mother is Bianca.
 ```

### 2) Using a Prolog tool with a LangChain agent

First create the Prolog tool:
```python
from langchain_prolog import PrologConfig, PrologRunnable, PrologTool

schema = PrologRunnable.create_schema("parent", ["man", "woman", "child"])
config = PrologConfig(
    rules_file="family.pl",
    query_schema=schema,
)
prolog_tool = PrologTool(
    prolog_config=config,
    name="family_query",
    description="""
        Query family relationships using Prolog.
        parent(X, Y, Z) implies only that Z is a child of X and Y.
        Input must be a dictionary like:
        {
            'man': 'richard',
            'woman': 'valery',
            'child': None,
        
        }
        Use 'None' to indicate a variable that need to be instantiated by Prolog
        The query will return:
            - 'True': if the relationship 'child' is a child of 'men' and 'women' holds.
            - 'False' if the relationship 'child' is a child of 'man' and 'woman' does not holds.
            - A list of dictionaries with all the answers to the Prolog query
        Do not use double quotes.
    """,
)
```
Then pass it to the agent's constructor:
```python
from langchain.agents import create_agent

llm = ChatOpenAI(model="gpt-4o-mini")
agent_executor = create_agent(
    llm,
    [prolog_tool],
    system_prompt="You are a helpful assistant",
)
```
The agent takes the query and uses the Prolog tool if needed:
```python
answer = agent_executor.invoke({"messages": [("human", "Who are John's children?")]})
print(answer["messages"][-1].content)
```
The agent receives the tool response and generates the answer:
```python
John has two children: Mary and Michael. Their mother is Bianca.
```
