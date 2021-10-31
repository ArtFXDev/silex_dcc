"""
@author: TD gang

Base class that every command should inherit from
"""

from __future__ import annotations

import copy
import functools
import os
import traceback
from typing import List, TYPE_CHECKING, Any, Callable, Dict

from silex_client.utils.enums import Execution, Status
from silex_client.utils.log import logger
from silex_client.utils.parameter_types import CommandParameterMeta

# Forward references
if TYPE_CHECKING:
    from silex_client.action.action_query import ActionQuery
    from silex_client.action.command_buffer import CommandBuffer

# Type for parameters
CommandParameters = Dict[str, Dict[str, Any]]


class CommandBase:
    """
    Base class that every command should inherit from
    """

    #: Dictionary that represent the command's parameters
    parameters: CommandParameters = {}

    #: List that represent the required context metadata
    required_metadata: List[str] = []

    def __init__(self, command_buffer: CommandBuffer):
        self.command_buffer = command_buffer

    @property
    def type_name(self) -> str:
        """
        Shortcut to get the type name of the command
        """
        return self.__class__.__name__

    def check_parameters(self, parameters: CommandParameters) -> bool:
        """
        Check the if the input kwargs are valid accoring to the parameters list
        and conform it if nessesary
        """
        for parameter_name, parameter_buffer in self.command_buffer.parameters.items():
            # Check if the parameter is here
            if parameter_name not in parameters.keys():
                logger.error(
                    "Could not execute %s: The parameter %s is missing",
                    self.command_buffer.name,
                    parameter_name,
                )
                return False

            # Check if the parameter is the right type
            try:
                parameters[parameter_name] = parameter_buffer.type(
                    parameters[parameter_name]
                )
            except (ValueError, TypeError):
                logger.error(
                    "Could not execute %s: The parameter %s is invalid (%s)",
                    self.command_buffer.name,
                    parameter_name,
                    parameters[parameter_name],
                )
                return False

        return True

    def check_context_metadata(self, context_metadata: Dict[str, Any]):
        """
        Check if the context snapshot stored in the buffer contains all the required
        data for the command
        """
        for metadata in self.required_metadata:
            if context_metadata.get(metadata) is None:
                logger.error(
                    "Could not execute command %s: The context is missing required metadata %s",
                    self.command_buffer.name,
                    metadata,
                )
                return False
        return True

    @staticmethod
    def conform_command():
        """
        Helper decorator that conform the input and the output
        Meant to be used with the __call__ method of CommandBase objects
        """

        def decorator_conform_command(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper_conform_command(
                command: CommandBase, *args, **kwargs
            ) -> None:
                parameters: CommandParameters = kwargs.get("parameters", args[1])
                action_query: ActionQuery = kwargs.get("action_query", args[2])

                # Make sure the given parameters are valid
                if not command.check_parameters(parameters):
                    command.command_buffer.status = Status.INVALID
                    return
                # Make sure all the required metatada is here
                if not command.check_context_metadata(action_query.context_metadata):
                    command.command_buffer.status = Status.INVALID
                    return
                command.command_buffer.status = Status.PROCESSING

                await action_query.async_update_websocket()

                try:
                    output = await func(command, *args, **kwargs)
                    command.command_buffer.output_result = output
                    execution_type = action_query.execution_type
                    if execution_type == Execution.FORWARD:
                        command.command_buffer.status = Status.COMPLETED
                    elif execution_type == Execution.BACKWARD:
                        command.command_buffer.status = Status.INITIALIZED
                except Exception as exception:
                    logger.error(
                        "An error occured while executing the command %s: %s",
                        command.command_buffer.name,
                        exception,
                    )
                    if os.getenv("SILEX_LOG_LEVEL") == "DEBUG":
                        traceback.print_tb(exception.__traceback__)
                    command.command_buffer.status = Status.ERROR

                await action_query.async_update_websocket()

            return wrapper_conform_command

        return decorator_conform_command

    async def __call__(
        self, upstream: Any, parameters: Dict[str, Any], action_query: ActionQuery
    ) -> Any:
        def default(upstream, parameters, action_query):
            raise NotImplementedError(
                "This command does not have any execution function"
            )

        self.conform_command()(default)

    async def undo(
        self, upstream: Any, parameters: Dict[str, Any], action_query: ActionQuery
    ) -> Any:
        def default(upstream, parameters, action_query):
            raise NotImplementedError(
                "This command does not have any execution function"
            )

        self.conform_command()(default)
