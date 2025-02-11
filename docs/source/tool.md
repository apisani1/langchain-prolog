## Tool Interface

The PrologTool class allows the generation of langchain tools that use Prolog rules to generate answers.

See the Runnable Interface section for the conventions on hown to pass variables and values to the Prolog interpreter.

Let's assume that we have the following set of Prolog rules in the file family.pl:

```prolog
parent(john, bianca, mary).
parent(john, bianca, michael).
parent(peter, patricia, jennifer).
partner(X, Y) :- parent(X, Y, _).
```

There are two ways to use a Prolog tool:

### 1) Using a Prolog tool with an LLM and function calling

First create the Prolog tool:
```python
from langchain_prolog import PrologConfig, PrologTool

schema = PrologRunnable.create_schema('parent', ['men', 'women', 'child'])
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
        Input can be a query string like 'parent(john, X, Y)'
        or 'john, X, Y'"
        You have to specify 3 parameters: men, woman, child.
        Do not use quotes.
    """
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
 'args': {'men': 'john', 'women': None, 'child': None},
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
 content='[{"Women": "bianca", "Child": "mary"}, {"Women": "bianca", "Child": "michael"}]'
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

### 2) Using a Prolog tool with an agent

First create the Prolog tool:
```python
from langchain_prolog import PrologConfig, PrologTool

schema = PrologRunnable.create_schema('parent', ['men', 'women', 'child'])
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
        Input can be a query string like 'parent(john, X, Y)'
        or 'john, X, Y'"
        You have to specify 3 parameters: men, woman, child.
        Do not use quotes.
    """
)
```
Then pass it to the agent's constructor:
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

llm = ChatOpenAI(model="gpt-4o-mini")
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)
tools = [prolog_tool]
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
```
The agent takes the query and use the Prolog tool if needed:
```python
answer = agent_executor.invoke({"input": "Who are John's children?"})
print(answer)
```
Then the agent recieves the tool response as part of the {agent_scratchpad} placeholder and generates the answer:
```python
{'input': "Who are John's children?", 'output': 'John has two children: Mary and Michael, with Bianca as their mother.'}
