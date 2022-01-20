from __future__ import annotations

import logging
import pathlib
import typing
from typing import Any, Dict, List

from fileseq import FrameSet
from silex_client.action.command_base import CommandBase
from silex_client.utils.command import CommandBuilder
from silex_client.utils.frames import split_frameset

# Forward references
if typing.TYPE_CHECKING:
    from silex_client.action.action_query import ActionQuery


class BuildNukeCommand(CommandBase):
    """
    Construct a Nuke command for the render farm
    """

    parameters = {
        "scene_file": {"label": "Scene file", "type": pathlib.Path},
        "frame_range": {
            "label": "Frame range (start, end, step)",
            "type": FrameSet,
            "value": "1-50x1",
        },
        "task_size": {
            "label": "Task size",
            "type": int,
            "value": 10,
        },
    }

    @CommandBase.conform_command()
    async def __call__(
        self,
        parameters: Dict[str, Any],
        action_query: ActionQuery,
        logger: logging.Logger,
    ):
        scene: pathlib.Path = parameters["scene_file"]
        frame_range: FrameSet = parameters["frame_range"]
        task_size: int = parameters["task_size"]

        nuke_cmd = CommandBuilder("nuke")
        nuke_cmd.add_rez_env(["nuke"])

        # Execute in interactive mode
        nuke_cmd.param("i")

        frame_chunks = split_frameset(frame_range, task_size)
        cmd_dict: Dict[str, List[str]] = {}

        for chunk in frame_chunks:
            # Specify the frames
            nuke_cmd.param("F", chunk.frameRange())

            # Specify the scene file
            nuke_cmd.param("x", str(scene))

            cmd_dict[chunk.frameRange()] = nuke_cmd.as_argv()

        return {"commands": cmd_dict, "file_name": scene.stem}
