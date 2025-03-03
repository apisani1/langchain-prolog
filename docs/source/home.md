# LangChain-Prolog

A Python library that integrates SWI-Prolog with LangChain. It enables seamless blending of Prolog’s logic programming capabilities into LangChain applications, allowing rule-based reasoning, knowledge representation, and logical inference alongside GenAI models.


## Features

- Seamless integration between LangChain and SWI-Prolog
- Use Prolog queries as LangChain's runnables and tools
- Invoke Prolog predicates from LangChain's LLM models, chains and agents
- Support for both synchronous and asynchronous operations
- Comprehensive error handling and logging
- Cross-platform support (macOS, Linux, Windows)

## Installation

### Prerequisites

- Python 3.10 or later
- SWI-Prolog installed on your system
- The following Python libraries will be installed:
    - `langchain` 0.3.0 or later
    - `janus-swi` 1.5.0 or later
    - `pydantic` 2.0.0 or later

Once SWI-Prolog has been installed, langchain-prolog can be installed using pip:
```bash
pip install langchain-prolog
```
