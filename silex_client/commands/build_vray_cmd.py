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



class VrayCommand(CommandBase):
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
        "skip_existing": {
            "label": "Skip existing frames",
            "type": bool,
            "value": True
        }
    }

    @CommandBase.conform_command()
    async def __call__(
        self, upstream: Any, parameters: Dict[str, Any], action_query: ActionQuery
    ):

        # author.setEngineClientParam(debug=True)

        scene: pathlib.Path = parameters.get('scene_file')
        frame_range: List[int] =  parameters.get("frame_range")
        frame_step: int = parameters.get("frame_step")
        
        # job = author.Job(title=f"vray render {scene.stem}")

        arg_list = [
            "C:/Maya2022/Maya2022/vray/bin/vray.exe",
            "-display=0",
            "-progressUpdateFreq=2000",
            "-progressUseColor=0",
            "-progressUseCR=0",
            f"-sceneFile={scene}",
            # "-rtEngine=5", # couda
            # f"-imgFile={scene.parents[0] / 'render' / scene.stem}.png"
        ]

        chunks = list()
        cmd_dict = dict()

        if frame_range[1] - frame_step <= 0:
            chunks.append((frame_range[0], frame_range[1]))
        else:
            for frame in range(frame_range[0], frame_range[1] - frame_step, frame_step):
                end_frame = frame + frame_step - 1
                chunks.append((frame, end_frame))

            rest = frame_range[1] % frame_step
            if rest:
                chunks.append((frame_range[1] - rest, frame_range[1]))


        for start, end in chunks:
            logger.info(f"Creating a new task with frames: {start} {end}")
            cmd_dict[f"frames={start}-{end}"] = arg_list + [f"-frames={start}-{end}"]
        
        return {
                "commands": cmd_dict,
                "file_name": scene.stem
                }
