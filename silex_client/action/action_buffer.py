from __future__ import annotations
import uuid
import copy
import json
from typing import Any
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass, field, asdict

from silex_client.action.command_buffer import CommandBuffer
from silex_client.utils.merge import merge_data
from silex_client.utils.log import logger
from silex_client.utils.enums import Status


@dataclass()
class ActionBuffer():
    """
    Store the state of an action, it is used as a comunication payload with the UI
    """

    # Define the mandatory keys and types for each attribibutes of a buffer
    STEP_TEMPLATE = {"index": int, "commands": list}
    COMMAND_TEMPLATE = {"path": str}

    #: The name of the action (usualy the same as the config file)
    name: str = field()
    uid: uuid.UUID = field(default_factory=uuid.uuid1, init=False)
    #: A dict of list of commands ordered by step names
    commands: dict = field(default_factory=OrderedDict, init=False)
    #: Dict of variables that are global to all the commands of this action
    variables: dict = field(compare=False, default_factory=dict, init=False)
    #: Snapshot of the context's metadata when this buffer is created
    context_metadata: dict = field(default_factory=dict)

    def __iter__(self) -> ActionCommandIterator:
        return ActionCommandIterator(self)

    def serialize(self) -> str:
        """
        Convert the action's data into json so it can be sent to the UI
        """
        dictionary_representation = asdict(self)
        # Convert the uuid into a json serialisable format
        dictionary_representation["uid"] = dictionary_representation["uid"].hex
        return json.dumps(dictionary_representation)

    def deserialize(self, serealised_data: dict):
        """
        Convert back the action's data from json into this object
        """
        raise NotImplementedError("This feature is WIP")

    @property
    def status(self):
        """
        The status of the action depends of the status of its commands
        """
        status = Status.COMPLETED
        for command in self:
            status = command.status if command.status > status else status

        return status

    def update_commands(self, commands: dict):
        """
        Check and conform a dict that represent the commands, generally comming
        from a config file. Filters out all the invalid data by checkinh if it matches the
        templates arguments
        """
        if not isinstance(commands, dict):
            logger.error("Invalid commands for action %s", self.name)

        filtered_commands = copy.deepcopy(commands)

        # Check if the steps are valid
        for name, step in commands.items():
            for key, value in self.STEP_TEMPLATE.items():
                if not isinstance(step, dict):
                    del filtered_commands[name]
                    break
                if key not in step or not isinstance(step[key], value):
                    del filtered_commands[name]
                    break

            # If the step has been deleted don't check the commands
            if name not in filtered_commands:
                continue

            # Check if the commands are valid
            for command in step["commands"]:
                for key, value in self.COMMAND_TEMPLATE.items():
                    if not isinstance(command, dict):
                        filtered_commands[name]["commands"].remove(command)
                        break
                    if key not in command or not isinstance(
                            command[key], value):
                        filtered_commands[name]["commands"].remove(command)
                        break

        # Override the existing commands with the new ones
        commands = merge_data(filtered_commands, dict(self.commands))
        # Convert the dict
        commands = self._dict_to_command_buffer(commands)

        # Sort the steps using the index key
        sort_cmds = sorted(commands.items(), key=lambda item: item[1]["index"])
        self.commands = OrderedDict(sort_cmds)

    @staticmethod
    def _dict_to_command_buffer(command_dict: dict) -> dict:
        """
        Convert a dict of command to a dict of CommandBuffer object
        Filters out all the invalid commands
        """
        for step_name, step_value in command_dict.items():
            for index, command in enumerate(step_value["commands"]):
                # Create the command buffer and check if it is valid
                command_buffer = CommandBuffer(**command)
                if command_buffer.status is Status.INVALID:
                    del command_dict[step_name]["commands"][index]
                    continue
                # Override the dict to a CommandBuffer object
                command_dict[step_name]["commands"][index] = command_buffer

        return command_dict

    def get_commands(self, step: str = None) -> list:
        """
        Helper to get a command that belong to this action
        The data is quite nested, this is just for conveniance
        """
        # Return the commands of the queried step
        if step is not None and step in self.commands:
            return self.commands[step]["commands"]

        # If no steps given return all the commands flattened
        return [
            command for step in self.commands.values()
            for command in step["commands"]
        ]

    def get_parameter(self, step: str, index: int, name: str):
        """
        Helper to get a parameter of a command that belong to this action
        The data is quite nested, this is just for conveniance
        """
        command = self.get_commands(step)[index]
        return command.parameters.get(name, None)

    def set_parameter(self, step: str, index: int, name: str,
                      value: Any) -> None:
        """
        Helper to set a parameter of a command that belong to this action
        The data is quite nested, this is just for conveniance
        """
        parameter = self.get_parameter(step, index, name)
        # Check if the given value is the right type
        if parameter is None or not isinstance(value,
                                               parameter.get("type", object)):
            try:
                value = parameter["type"](value)
            except:
                logger.error("Could not set parameter %s: Invalid value", name)
                return

        parameter["value"] = value

class ActionCommandIterator(Iterator):
    def __init__(self, buffer: ActionBuffer):
        self.buffer = buffer

        # Initialize the step iterator
        self._step_iter = iter(self.buffer.commands.items())
        self._current_step = next(self._step_iter)

        # Initialize the command iterator
        self._command_iter = iter(self._current_step[1]["commands"])


    def __next__(self) -> CommandBuffer:
        # Get the next command in the current step if available
        try:
            command = next(self._command_iter)
            return command
        # Get the next step available and rerun the loop
        except StopIteration:
            # No need to catch the StopIteration exception
            # Since it will just end the loop has we would want
            self._current_step = next(self._step_iter)
            self._command_iter = iter(self._current_step[1]["commands"])
            return self.__next__()

