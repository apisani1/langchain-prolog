from inspect import signature
from typing import (
    Any,
    Dict,
    Optional,
    Union,
)

from pydantic import Field

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import (
    BaseTool,
    Tool,
)
from langchain_core.tools.base import _get_runnable_config_param
from langchain_prolog import (
    PrologConfig,
    PrologRunnable,
)

from .exceptions import PrologToolException


class _PrologRunnableWrapper(PrologRunnable):
    pass


class PrologTool(Tool):
    """Tool for executing Prolog queries."""

    prolog: PrologRunnable = Field(  # type: ignore
        default=None,
        exclude=True,
        description="PrologRunnable instance to be used for invoking Prolog queries",
    )

    def __init__(
        self,
        name: str,
        description: str,
        prolog_config: Optional[Union[PrologConfig, Dict]] = None,
        prolog_kwargs: Optional[Dict] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Prolog tool.

        Args:
            name (str): The name of the tool.
            description (str): A description of what the tool does.
            prolog_config (PrologConfig | dict): Configuration for the Prolog interpreter.
            return_direct (bool): Whether to return the output directly. Defaults to False.
            verbose (bool): Whether to enable verbose output. Defaults to False.
            callbacks (Callbacks, optional): Callback functions to be called during tool execution.
            tags (list[str], optional): Optional list of tags.
            metadata (dict, optional): Optional metadata dictionary.
            handle_tool_error(bool | str | Callable, optional): How to handle tool execution errors.
            handle_validation_error (bool | str | Callable, optional): How to handle input validation errors.
            response_format ("content" | "content_and_artifact"): Format of the tool's response.
            **kwargs: Additional arguments passed to BaseTool.
        """
        # Initialize the PrologRunnable
        prolog_kwargs = prolog_kwargs or {}
        prolog = _PrologRunnableWrapper(
            prolog_config=prolog_config,
            **prolog_kwargs,
        )

        # Call Tool initializer
        super().__init__(
            name=name,
            description=description,
            func=prolog.invoke,
            args_schema=prolog.prolog_config.query_schema,
            **kwargs,
        )

        self.prolog = prolog

    def _to_args_and_kwargs(
        self, tool_input: Union[str, dict], tool_call_id: Optional[str]
    ) -> tuple[tuple, dict]:
        """Handle tool input for function calling."""
        args, kwargs = BaseTool._to_args_and_kwargs(self, tool_input, tool_call_id)
        args = args if isinstance(args, tuple) else () if args is None else (args,)
        kwargs = (
            kwargs if isinstance(kwargs, dict) else {} if kwargs is None else {"__arg1": kwargs}
        )
        all_args = list(args) + list(kwargs.values())
        if len(args) != 0 or "__arg1" in kwargs:
            return tuple(all_args), {}
        return (kwargs,), {}

    def _run(
        self,
        *args: Any,
        config: RunnableConfig,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute the Prolog query.

        Args:
            args: Args for the Prolog query to execute
            config (RunnableConfig, optional): Optional langchain runnable configuration
            run_manager (CallbackManagerForToolRun, optional): Optional callback manager for then tool run
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals
        Returns:
            Prolog query result. True, False or list of dictionaries

        Raises:
            PrologToolException: If the query execution fails
        """
        try:
            if run_manager and signature(self.prolog.invoke).parameters.get("callbacks"):
                kwargs["callbacks"] = run_manager.get_child()
            if config_param := _get_runnable_config_param(self.prolog.invoke):
                kwargs[config_param] = config
            return self.prolog.invoke(*args, **kwargs)
        except Exception as e:
            raise PrologToolException(f"Unexpected error during Prolog tool execution: {str(e)}")

    async def _arun(
        self,
        *args: Any,
        config: RunnableConfig,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute the Prolog query asynchronously.

        Args:
            args: Args for the Prolog query to execute
            config (RunnableConfig, optional): Optional langchain runnable configuration
            run_manager (CallbackManagerForToolRun, optional): Optional callback manager for then tool run
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals
        Returns:
            Prolog query result. True, False or list of dictionaries

        Raises:
            PrologToolException: If the query execution fails
        """
        if run_manager:
            run_manager = run_manager.get_sync()  # type: ignore
        return self._run(*args, config=config, run_manager=run_manager, **kwargs)  # type: ignore
