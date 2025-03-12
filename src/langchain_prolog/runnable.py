__all__ = ["PrologConfig", "PrologInput", "PrologSolution", "PrologResult", "PrologRunnable"]
from importlib import resources
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

import janus_swi as janus
import langchain
from langchain_core.callbacks.manager import (
    BaseCallbackHandler,
    CallbackManager,
    Callbacks,
)
from langchain_core.globals import get_verbose
from langchain_core.runnables import Runnable
from langchain_core.runnables.config import (
    RunnableConfig,
    get_config_list,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    create_model,
    field_validator,
)

from .exceptions import (
    PrologFileNotFoundError,
    PrologRuntimeError,
    PrologValueError,
)


langchain.verbose = False
langchain.debug = False
langchain.llm_cache = False

PrologInput = Optional[Union[str, Dict[Any, Any], BaseModel]]
PrologSolution = Dict[Any, Any]
PrologResult = Union[Literal[True], Literal[False], List[PrologSolution], PrologRuntimeError]


class _DoNothing(BaseCallbackHandler):
    """
    A callback handler that does nothing.
    It is used when PrologRunnable is used as a tool and not as a chain.
    """

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        pass

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        pass

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        pass


class PrologConfig(BaseModel):
    """Configuration for the Prolog interpreter."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
    rules_file: Optional[Union[str, Path]] = Field(default=None, description="Path to the Prolog rules file")
    default_predicate: Optional[str] = Field(
        default=None,
        description="Default predicate to use when no predicate is specified",
    )
    query_schema: Optional[Type[BaseModel]] = Field(default=None, description="Pydantic model for input validation")
    prolog_flags: Dict[str, Any] = Field(default_factory=dict, description="Custom Prolog flags to set")

    @field_validator("rules_file", mode="before")
    def validate_rules_file(cls, v: Optional[Union[str, Path]]) -> Optional[Path]:
        if v is None:
            return None
        path = Path(v)
        if not path.exists():
            raise PrologFileNotFoundError(f"Prolog rules file not found: {path}")
        return path

    @field_validator("default_predicate", mode="before")
    def validate_default_predicate(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise PrologValueError("Default predicate cannot be empty")
            if not v.isidentifier():
                raise PrologValueError("Default predicate must be a valid Prolog identifier")
        return v

    @field_validator("prolog_flags", mode="before")
    def validate_prolog_flags(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        valid_flags = set()
        flags_iter = janus.query("current_prolog_flag(Flag, Value).")
        while flags_iter:
            try:
                flag = flags_iter.next()
                if not flag:
                    break
                valid_flags.add(flag["Flag"])
            except Exception:
                pass
        invalid_flags = set(v.keys()) - valid_flags
        if invalid_flags:
            raise PrologValueError(f"Invalid Prolog flags: {invalid_flags}")
        return v


class PrologRunnable(Runnable[PrologInput, PrologResult]):
    """A runnable that executes Prolog queries."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    _prolog_config: PrologConfig = PrivateAttr()

    def __init__(
        self,
        prolog_config: Optional[Union[PrologConfig, Dict]] = None,
        *,
        verbose: bool = False,
        callbacks: Optional[Callbacks] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize PrologRunnable with configuration.

        Args:
            prolog_config (PologConfig | dict, optional): Configuration for the Prolog interpreter
            verbose (bool): Whether to enable verbose output. Defaults to False.
            callbacks (Callbacks, optional): Callback functions.
            tags (list[str], optional): Optional list of tags.
            metadata (dict, optional): Optional metadata dictionary.
            name (str, optional): The name of the Runnable. Used for debugging and tracing.
            **kwargs: Additional arguments passed to the Runnable class constructor

        Raises:
            PrologValueError: If the configuration is invalid
            PrologFileNotFoundError: If the rules file doesn't exist
            PrologRuntimeError: If rules can't be loaded
        """
        # Convert dict to PrologConfig if necessary
        if isinstance(prolog_config, dict):
            prolog_config = PrologConfig(**prolog_config)
        elif prolog_config is None:
            prolog_config = PrologConfig()

        self._prolog_config = prolog_config.model_copy()

        # Set Prolog flags
        for flag, value in prolog_config.prolog_flags.items():
            try:
                janus.query_once(f"set_prolog_flag({flag}, {value}).")
            except Exception as e:
                raise PrologRuntimeError(f"Error setting Prolog flag {flag} to {value}: {str(e)}")

        # Load the consult_ex module
        try:
            with resources.files("langchain_prolog").joinpath("consult_ex.pl").open("r") as f:
                consult_ex_path = Path(f.name)
                janus.consult(str(consult_ex_path))
        except Exception as e:
            raise PrologRuntimeError(f"Error loading Prolog consult_ex module: {str(e)}")

        # Load rules file if specified
        if prolog_config.rules_file:
            self.load_rules(prolog_config.rules_file)

        self.verbose = verbose or get_verbose()
        self.callbacks = callbacks
        self.tags = tags or []
        self.tags.append("prolog")
        self.metadata = metadata or {}
        self.metadata["prolog_config"] = prolog_config.model_dump()
        self.name = name or self.__class__.__name__

        Runnable.__init__(self, **kwargs)

    @property
    def prolog_config(self) -> PrologConfig:
        """Get the Prolog configuration."""
        return self._prolog_config

    def load_rules(self, rules_file: Union[str, Path]) -> None:
        """
        Load Prolog rules from a file.

        Args:
            rules_file (str | Path): Path to the Prolog rules file

        Raises:
            PrologFileNotFoundError: If rules_file doesn't exist
            PrologRuntimeError: If rules can't be loaded or have gramatical errors
        """
        rules_path = Path(rules_file)
        if not rules_path.exists():
            raise PrologFileNotFoundError(f"Prolog rules file not found: {rules_file}")
        try:
            # Convert path to Prolog atom string (with single quotes)
            prolog_path = f"'{str(rules_path)}'"
            janus.query_once(f"consult_ex({prolog_path})")
        except Exception as e:
            raise PrologRuntimeError(f"Error loading Prolog rules: {str(e)}")

    @classmethod
    def create_schema(cls, predicate_name: str, arg_names: List[str]) -> Type[BaseModel]:
        """
        Create a Pydantic model for a Prolog predicate.

        Args:
            predicate_name (str): Name (functor) of the Prolog predicate
            arg_names (list[str]): List of argument names in order

        Returns:
            BaseModel: Pydantic model class for the predicate

        Raises:
            PrologValueError: If predicate_name is empty or arg_names contains invalid names
        """
        if not predicate_name or not isinstance(predicate_name, str) or not predicate_name.isidentifier():
            raise PrologValueError("predicate_name must be valid Python identifiers")

        if not all(isinstance(name, str) and name.isidentifier() for name in arg_names):
            raise PrologValueError("All argument names must be valid Python identifiers")

        fields: Dict[str, Any] = {name: (Optional[Any], ...) for name in arg_names}

        return create_model(f"{predicate_name}", __config__=ConfigDict(), **fields)

    def _process_input(self, input_data: PrologInput) -> Union[str, BaseModel]:
        """
        Process and validate input data.

        Args:
            input_data (str | dict | BaseModel): Input data to process

        Returns:
            str | BaseModel: Processed input ready for query building

        Raises:
            PrologValueError: If input type is invalid or schema is missing
        """
        if input_data is None:
            if not self._prolog_config.default_predicate:
                raise PrologValueError("Input data cannot be None if no default predicate set")
            return self._prolog_config.default_predicate + "()"
        if isinstance(input_data, (str, BaseModel)):
            return input_data
        if isinstance(input_data, dict) and self._prolog_config.query_schema:
            return self._prolog_config.query_schema(**input_data)
        raise PrologValueError("Invalid input type or missing schema for dictionary input")

    def _build_query(self, input_data: Union[str, BaseModel]) -> str:
        """
        Build a Prolog query from input data.

        Args:
            input_data (str | BaseModel): String query or Pydantic model instance

        Returns:
            str: Prolog query string

        Raises:
            PrologValueError: If input_data is of invalid type or invalid query format
        """
        if isinstance(input_data, str):
            if not input_data.strip() and not self._prolog_config.default_predicate:
                raise PrologValueError("Prolog query string cannot be empty")

            # Check if the input contains parentheses
            if "(" in input_data:
                # Validate parentheses matching
                if input_data.count("(") != input_data.count(")"):
                    raise PrologValueError("Mismatched parentheses in query")
                return input_data

            # Use default predicate if no explicit predicate is provided
            if not self._prolog_config.default_predicate:
                raise PrologValueError(f"No default predicate set for argument-only query: {input_data}")
            return f"{self._prolog_config.default_predicate}({input_data})"

        if isinstance(input_data, BaseModel):
            # Convert Pydantic model to Prolog query. None values are converted to Prolog variables
            params = []
            for field_name, field_value in input_data:
                value = field_value if field_value is not None else field_name.capitalize()
                params.append(str(value))
            return f"{input_data.__class__.__name__}({', '.join(params)})"

        raise PrologValueError("Input must be either string or valid Pydantic model")

    @staticmethod
    def _get_prolog_kwargs(config: RunnableConfig) -> Dict[str, str]:
        return config.get("configurable", {}).get("prolog_kwargs", {})

    def _execute_query(self, query: str, **kwargs: Any) -> Iterator[Dict[Any, Any]]:
        """
        Execute a Prolog query safely.

        Args:
            query (str): Prolog query string
            **kwargs: Additional arguments for query execution.
                    Supported keyword arguments: inputs, truth_vals

        Returns:
            Iterator of query solutions

        Raises:
            PrologValueError: If unsupported query keyword arguments are provided
            PrologRuntimeError: If query execution fails
        """
        valid_kwargs = {"inputs", "truth_vals"}
        invalid_kwargs = set(kwargs.keys()) - valid_kwargs
        if invalid_kwargs:
            raise PrologValueError(f"Unsupported query arguments: {invalid_kwargs}")

        try:
            return janus.query(query, **kwargs)
        except Exception as e:
            raise PrologRuntimeError(f"Prolog execution error: {str(e)}")

    @staticmethod
    def _clean_solution(solution: Dict[Any, Any]) -> PrologSolution:
        """Clean a single solution dictionary."""
        return {k: v for k, v in solution.items() if k != "truth"}

    def invoke(self, input: PrologInput, config: Optional[RunnableConfig] = None, **kwargs: Any) -> PrologResult:
        """
        Execute a Prolog query and return all solutions at once.

        Args:
            input (str | dict | BaseModel): Prolog query
            config (RunnableConfig, optional): Optional langchain runnable configuration
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals

        Returns:
            Prolog query result. True, False or a list of dictionaries

        Raises:
            PrologValueError: If input type is invalid or schema is missing for a dictionay input
            PrologRuntimeError: If query execution fails
        """
        config = config or {}

        if self.__class__.__name__ == "PrologRunnable":
            callback_manager = CallbackManager.configure(
                inheritable_callbacks=config.get("callbacks"),
                local_callbacks=self.callbacks,
                verbose=config.get("verbose", self.verbose),  # type: ignore
                inheritable_tags=config.get("tags"),
                local_tags=self.tags,
                inheritable_metadata=config.get("metadata"),
                local_metadata=self.metadata,
            )
            run_manager = callback_manager.on_chain_start(
                {"name": config.get("run_name") or self.get_name()},
                {"input": input},
                **kwargs,
            )
        else:
            # PrologRunnable is being used as a tool
            run_manager = _DoNothing()  # type: ignore

        try:
            result: PrologResult

            processed_input = self._process_input(input)
            query = self._build_query(processed_input)
            prolog_kwargs = self._get_prolog_kwargs(config)
            solutions = list(self._execute_query(query, **prolog_kwargs))

            if len(solutions) == 0 or all(sol == {"truth": False} for sol in solutions):
                result = False
            elif all(sol == {"truth": True} for sol in solutions):
                result = True
            else:
                result = [self._clean_solution(sol) for sol in solutions]

            run_manager.on_chain_end({"output": result})

            return result

        except (PrologValueError, PrologRuntimeError) as e:
            run_manager.on_chain_error(e)
            raise
        except Exception as e:
            run_manager.on_chain_error(e)
            raise PrologRuntimeError(f"Prolog execution error: {str(e)}")

    async def ainvoke(
        self,
        input: PrologInput,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> PrologResult:
        """
        Execute a Prolog query asynchronously and return all the solutions at once.

        Args:
            input (str, dict, BaseModel): Prolog query
            config (RunnableConfig, optional): langchain runnable configuration
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals

        Returns:
            PrologResult: Query result. True, False or a list of dictionaries

        Raises:
            PrologValueError: If input type is invalid or schema is missing for a dictionay input
            PrologRuntimeError: If query execution fails
        """
        return self.invoke(input, config=config, **kwargs)

    def stream(  # noqa: R701
        self, input: PrologInput, config: Optional[RunnableConfig] = None, **kwargs: Any
    ) -> Iterator[PrologResult]:
        """
        Execute a Prolog query and yield solutions one by one.

        Args:
            input (str, dict, BaseModel): Prolog query
            config (RunnableConfig, optional): langchain runnable configuration
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals

        Yields:
            PrologResult: Query result. True, False or a list of dictionaries

        Raises:
            PrologValueError: If input type is invalid or schema is missing for dictionary input
            PrologRuntimeError: If query execution fails
        """
        config = config or {}

        if self.__class__.__name__ == "PrologRunnable":
            callback_manager = CallbackManager.configure(
                inheritable_callbacks=config.get("callbacks"),
                local_callbacks=self.callbacks,
                verbose=config.get("verbose", self.verbose),  # type: ignore
                inheritable_tags=config.get("tags"),
                local_tags=self.tags,
                inheritable_metadata=config.get("metadata"),
                local_metadata=self.metadata,
            )
            run_manager = callback_manager.on_chain_start(
                {"name": config.get("run_name") or self.get_name()},
                {"input": input},
                **kwargs,
            )
        else:
            # PrologRunnable is being used as a tool
            run_manager = _DoNothing()  # type: ignore

        try:
            processed_input = self._process_input(input)
            query = self._build_query(processed_input)
            prolog_kwargs = self._get_prolog_kwargs(config)

            # Create an iterator for the solutions
            solutions_iter = self._execute_query(query, **prolog_kwargs)

            # Try to get the first solution
            try:
                first_solution = next(solutions_iter, None)
            except StopIteration:
                run_manager.on_chain_end({"output": False})
                yield False
                return

            # If there's no first solution, yield False
            if first_solution is None:
                run_manager.on_chain_end({"output": False})
                yield False
                return

            # If all the solutions have only the same truth value, yield True or False
            if first_solution == {"truth": True} or first_solution == {"truth": False}:
                # Store solutions to check if they're all the same
                solutions = [first_solution]
                for solution in solutions_iter:
                    solutions.append(solution)

                if all(sol == {"truth": False} for sol in solutions):
                    run_manager.on_chain_end({"output": False})
                    yield False
                    return

                if all(sol == {"truth": True} for sol in solutions):
                    run_manager.on_chain_end({"output": True})
                    yield True
                    return

                # Yield solutions one by one
                all_results = []
                for solution in solutions:
                    result = [self._clean_solution(solution)]
                    all_results.append(result)
                    yield result
            else:
                # Yield solutions one by one
                first_result = [self._clean_solution(first_solution)]
                all_results = [first_result]
                yield first_result
                for solution in solutions_iter:
                    result = [self._clean_solution(solution)]
                    all_results.append(result)
                    yield result

            run_manager.on_chain_end({"output": all_results})

        except (PrologValueError, PrologRuntimeError) as e:
            run_manager.on_chain_error(e)
            raise
        except Exception as e:
            run_manager.on_chain_error(e)
            raise PrologRuntimeError(f"Prolog execution error: {str(e)}")

    async def astream(
        self, input: PrologInput, config: Optional[RunnableConfig] = None, **kwargs: Any
    ) -> AsyncIterator[PrologResult]:
        """
        Execute Prolog query asynchronously and yield results one by one.

        Args:
            input (str, dict, BaseModel): Prolog query
            config (RunnableConfig, optional): langchain runnable configuration
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals

        Yields:
            PrologResult: Query result. True, False or a list of dictionaries

        Raises:
            PrologValueError: If input type is invalid or schema is missing
            PrologRuntimeError: If query execution fails
        """
        for result in self.stream(input, config=config, **kwargs):
            yield result

    def batch(
        self,
        inputs: List[PrologInput],
        config: Optional[Union[RunnableConfig, List[RunnableConfig]]] = None,
        *,
        return_exceptions: bool = False,
        **kwargs: Optional[Any],
    ) -> List[PrologResult]:
        """
        Execute multiple Prolog queries and return all solutions.

        Args:
            inputs (list[str | dict | BaseModel]): List of Prolog queries
            config (RunnableConfig | list[RunnableConfig], optional): Optional langchain runnable configuration(s)
            return_exceptions (bool): If True, include exceptions as PrologRuntimeError in the results.
                                      Defaults to False.
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals

        Returns:
            A list of Prolog queries results (True, False or a list of dictionaries).
            If return_exceptions is True, exception trowing queries return PrologRuntimeError as the result

        Raises:
            PrologValueError: If inputs is not a list
            PrologRuntimeError: If execution fails and return_exceptions is False

        Todo:
            Implement batch execution using Prolog built-in concurrency
        """

        if not isinstance(inputs, list):
            raise PrologValueError("PrologRunnable batch inputs must be a list")

        configs = get_config_list(config, len(inputs))
        results: List[PrologResult] = []

        for input_item, config_item in zip(inputs, configs):
            try:
                result = self.invoke(input_item, config=config_item, **kwargs)
                results.append(result)
            except Exception as e:
                if return_exceptions:
                    results.append(PrologRuntimeError(str(e)))
                else:
                    raise PrologRuntimeError(f"Prolog batch execution error: {str(e)}")

        return results

    async def abatch(
        self,
        inputs: List[PrologInput],
        config: Optional[Union[RunnableConfig, List[RunnableConfig]]] = None,
        *,
        return_exceptions: bool = False,
        **kwargs: Optional[Any],
    ) -> List[PrologResult]:
        """
        Execute multiple Prolog queries asynchronously and return all solutions.

        Args:
            inputs (list[str | dict | BaseModel]): List of Prolog queries
            config (list[RunnableConfig], optional): Optional langchain runnable configuration(s)
            return_exceptions (bool): If True, include exceptions as PrologRuntimeError in the results.
                                    Defaults to False.
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals

        Returns:
            List of Prolog queries results (True, False or list of dictionaries).
            If return_exceptions is True, exception trowing queries return PrologRuntimeError as a result

        Raises:
            PrologValueError: If inputs is not a list
            PrologRuntimeError: If execution fails and return_exceptions is False
        """
        return self.batch(inputs, config=config, return_exceptions=return_exceptions, **kwargs)

    def batch_as_completed(
        self,
        inputs: Sequence[PrologInput],
        config: Optional[Union[RunnableConfig, Sequence[RunnableConfig]]] = None,
        *,
        return_exceptions: bool = False,
        **kwargs: Optional[Any],
    ) -> Iterator[Tuple[int, PrologResult]]:
        """
        Execute multiple Prolog queries and yield results one by one.

        Args:
            inputs (sequence[str | dict | BaseModel]): Sequence of Prolog queries
            config (RunnableConfig | sequence[RunnableConfig], optional): Optional configuration(s) for the runnable
            return_exceptions: If True, include exceptions as PrologRuntimeError in results
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals


        Yields:
            Tuples with enumerations of Prolog Query solutions.
            If return_exceptions is True, exception trowing queries yield PrologRuntimeError as the result

        Raises:
            PrologValueError: If inputs is not a list
            PrologRuntimeError: If execution fails and return_exceptions is False
        """
        if not isinstance(inputs, list):
            raise PrologValueError("PrologRunnable batch_as_completed inputs must be a list")

        configs = get_config_list(config, len(inputs))

        for i, (input_item, config_item) in enumerate(zip(inputs, configs)):
            try:
                result = self.invoke(input_item, config=config_item, **kwargs)
                yield (i, result)
            except Exception as e:
                if return_exceptions:
                    yield (i, PrologRuntimeError(str(e)))
                else:
                    raise PrologRuntimeError(f"Prolog batch_as_completed execution error: {str(e)}")

    async def abatch_as_completed(
        self,
        inputs: Sequence[PrologInput],
        config: Optional[Union[RunnableConfig, Sequence[RunnableConfig]]] = None,
        *,
        return_exceptions: bool = False,
        **kwargs: Optional[Any],
    ) -> AsyncIterator[Tuple[int, PrologResult]]:
        """
        Execute multiple Prolog queries asynchronously and yield results one by one.

        Args:
            inputs (sequence[str | dict | BaseModel]): Sequence of Prolog queries
            config (RunnableConfig | sequence[RunnableConfig], optional): Optional configuration(s) for the runnable
            return_exceptions: If True, include exceptions as PrologRuntimeError in results
            **kwargs: Additional arguments for Prolog query execution.
                    Supported keyword arguments by janus-swi: inputs, truth_vals


        Yields:
            Tuple with enumerations of Prolog Query solutions.
            If return_exceptions is True, exception trowing queries yield PrologRuntimeError as the result

        Raises:
            PrologValueError: If inputs is not a list
            PrologRuntimeError: If execution fails and return_exceptions is False
        """
        for result in self.batch_as_completed(inputs, config=config, return_exceptions=return_exceptions, **kwargs):
            yield result
