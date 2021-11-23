"""
@author: TD gang

Dataclass used to store the data related to a step
"""

from __future__ import annotations

import copy
import re
import uuid as unique_id
from dataclasses import dataclass, field, fields
from typing import Dict, Any, Optional, List

import jsondiff
import dacite.config as dacite_config
import dacite.core as dacite

from silex_client.action.command_buffer import CommandBuffer
from silex_client.utils.datatypes import CommandOutput
from silex_client.utils.enums import Status


@dataclass()
class StepBuffer:
    """
    Store the data of a step, it is used as a comunication payload with the UI
    """

    #: The list of fields that should be ignored when serializing this buffer to json
    PRIVATE_FIELDS = ["outdated_cache", "serialize_cache"]

    #: Name of the step, must have no space or special characters
    name: str
    #: The index of the step, to set the order in which they should be executed
    index: int
    #: The status of the step, this value is readonly, it is computed from the commands's status
    status: Status = field(init=False)  # type: ignore
    #: The name of the step, meant to be displayed
    label: Optional[str] = field(compare=False, repr=False, default=None)
    #: Specify if the step must be displayed by the UI or not
    hide: bool = field(compare=False, repr=False, default=False)
    #: Small explanation for the UI
    tooltip: str = field(compare=False, repr=False, default="")
    #: Dict that represent the parameters of the command, their type, value, name...
    commands: Dict[str, CommandBuffer] = field(default_factory=dict)
    #: A Unique ID to help differentiate multiple actions
    uuid: str = field(default_factory=lambda: str(unique_id.uuid4()))
    #: Marquer to know if the serialize cache is outdated or not
    outdated_cache: bool = field(compare=False, repr=False, default=True)
    #: Cache the serialize output
    serialize_cache: dict = field(compare=False, repr=False, default_factory=dict)

    def __setattr__(self, name, value):
        super().__setattr__("outdated_cache", True)
        super().__setattr__(name, value)

    def __post_init__(self):
        slugify_pattern = re.compile("[^A-Za-z0-9]")
        # Set the command label
        if self.label is None:
            self.label = slugify_pattern.sub(" ", self.name)
            self.label = self.label.title()

    @property
    def outdated_caches(self):
        return self.outdated_cache or not all(not command.outdated_caches for command in self.commands.values())

    def serialize(self, ignore_fields: List[str] = None) -> Dict[str, Any]:
        """
        Convert the step's data into json so it can be sent to the UI
        """
        if not self.outdated_caches:
            return self.serialize_cache

        if ignore_fields is None:
            ignore_fields = self.PRIVATE_FIELDS

        result = []

        for f in fields(self):
            if f.name in ignore_fields:
                continue
            elif f.name == "commands":
                commands = getattr(self, f.name)
                command_value = {}
                for command_name, command in commands.items():
                    command_value[command_name] = command.serialize()
                result.append((f.name, command_value))
            else:
                result.append((f.name, getattr(self, f.name)))

        self.serialize_cache = dict(result)
        self.outdated_cache = False
        return self.serialize_cache

    def _deserialize_commands(self, command_data: Any) -> Any:
        command_name = command_data.get("name")
        command = self.commands.get(command_name)
        if command is None:
            return CommandBuffer.construct(command_data)

        command.deserialize(command_data)
        return command

    def deserialize(self, serialized_data: Dict[str, Any], force=True) -> None:
        """
        Convert back the action's data from json into this object
        """
        # Don't take the modifications of the hidden steps
        if self.hide and not force:
            return

        # Patch the current step data
        current_step_data = self.serialize()
        current_step_data = {key: value for key, value in current_step_data.items() if key != "commands"}
        serialized_data = jsondiff.patch(current_step_data, serialized_data)

        # Format the commands corectly
        for command_name, command in serialized_data.get("commands", {}).items():
            command["name"] = command_name

        config = dacite_config.Config(
            cast=[Status, CommandOutput],
            type_hooks={CommandBuffer: self._deserialize_commands},
        )
        new_data = dacite.from_dict(StepBuffer, serialized_data, config)

        for private_field in self.PRIVATE_FIELDS:
            setattr(new_data, private_field, getattr(self, private_field))

        self.commands.update(new_data.commands)
        self.__dict__.update({key: value for key, value in new_data.__dict__.items() if key != "commands"})
        self.outdated_cache = True

    @classmethod
    def construct(cls, serialized_data: Dict[str, Any]) -> StepBuffer:
        """
        Create an step buffer from serialized data
        """
        config = dacite_config.Config(cast=[Status, CommandOutput])
        if "commands" in serialized_data:
            filtered_data = copy.deepcopy(serialized_data)
            del filtered_data["commands"]
            step = dacite.from_dict(StepBuffer, filtered_data, config)
        else:
            step = dacite.from_dict(StepBuffer, serialized_data, config)

        step.deserialize(serialized_data, force=True)
        return step

    @property  # type: ignore
    def status(self) -> Status:
        """
        The status of the action depends of the status of its commands
        """
        status = Status.COMPLETED
        for command in self.commands.values():
            status = command.status if command.status > status else status

        # If some commands are completed and the rest initialized, then the step is processing
        if status is Status.INITIALIZED and Status.COMPLETED in [
            command.status for command in self.commands.values()
        ]:
            status = Status.PROCESSING

        return status

    @status.setter
    def status(self, other) -> None:
        """
        The status property is readonly, however
        we need to implement this since it is also a property
        and the datablass module tries to set it
        """
