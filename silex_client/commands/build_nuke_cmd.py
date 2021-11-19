from __future__ import annotations

import pathlib
import typing
from typing import Any, Dict, List

from silex_client.action.command_base import CommandBase
from silex_client.utils.parameter_types import IntArrayParameterMeta
from silex_client.utils.log import logger

# Forward references
if typing.TYPE_CHECKING:
    from silex_client.action.action_query import ActionQuery


class BuildNukeCommand(CommandBase):
    """
    Put the given file on database and to locked file system
    """

    parameters = {
        "scene_file": {
            "label": "Scene file",
            "type": pathlib.Path
        },
        "frame_range": {
            "label": "Frame range",
            "type": IntArrayParameterMeta(2),
            "value": [0, 100]
        },
        "task_size": {
            "label": "Task size",
            "type": int,
            "value": 10,
        },
    }

    def _chunks(self, lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    @CommandBase.conform_command()
    async def __call__(
        self, upstream: Any, parameters: Dict[str, Any], action_query: ActionQuery
    ):
        scene: pathlib.Path = parameters['scene_file']
        frame_range: List[int] = parameters["frame_range"]
        task_size: int = parameters["task_size"]

        arg_list = [
            # V-Ray exe path
            "C:/Nuke13.0v3/Nuke13.0.exe",

            # Execute in interactive mode
            "-i",

            # Specify the scene file
            "-x",
            f"{scene}",
        ]

        chunks = list(self._chunks(
            range(frame_range[0], frame_range[1] + 1), task_size))
        cmd_dict = dict()


        for chunk in chunks:
            start, end = chunk[0], chunk[-1]
            logger.info(f"Creating a new task with frames: {start} {end}")
            cmd_dict[f"frames={start}-{end}"] = arg_list + \
                ["-F", f"{start}-{end}"]

        return {
            "commands": cmd_dict,
            "file_name": scene.stem
        }

