# LangChain-Prolog

A Python library that integrates SWI-Prolog with LangChain, allowing seamless
blending of Prolog's logic programming capabilities into LangChain applications.


## Features

- Seamless integration between LangChain and SWI-Prolog
- Use Prolog queries as LangChain runnables and tools
- Invoke Prolog predicates from LangChain LLM models, chains and agents
- Support for both synchronous and asynchronous operations
- Comprehensive error handling and logging
- Cross-platform support (macOS, Linux, Windows)

## Installation

#### Prerequisites

- Python 3.10 or later
- SWI-Prolog installed on your system
- The following python libraries installed:
    - langchain 0.3.0 or later
    - janus-swi 1.5.0 or later
    - pydantic 0.2.0 or later

langchain-prolog can be installed using pip:
```bash
pip install langchain-prolog
```
