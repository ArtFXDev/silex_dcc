from __future__ import annotations
import typing
from typing import Any, Dict
from gazu.exception import MethodNotAllowedException

from silex_client.action.command_base import CommandBase

if typing.TYPE_CHECKING:
    from silex_client.action.action_query import ActionQuery

import gazu.task
import gazu.files
import os


class FileStructure(CommandBase):
    """
    Copy file and override if necessary
    """

    

    @CommandBase.conform_command()
    async def __call__(
        self, upstream: Any, parameters: Dict[str, Any], action_query: ActionQuery
    ):

        project_id: str = action_query.context_metadata.get('project_id')

        tasks = await gazu.task.all_tasks_for_project(project_id)

        for task in tasks:

            working_path = await gazu.files.build_working_file_path(
                task = task
            )

            working_path_work = os.path.dirname(working_path)
            working_path_work = working_path_work.replace('/', f'{os.path.sep}')
            decompo = working_path_work.split(os.path.sep)

            os.makedirs(working_path_work,exist_ok=True)

            if decompo[3] == "shots":
                sequ_path = f'{os.path.join(*decompo[:3])}{os.path.sep}sequences{os.path.sep}{decompo[4]}{os.path.sep}{decompo[6]}{os.path.sep}work'
                os.makedirs(sequ_path,exist_ok=True)

            rushes = f'{os.path.join(*decompo[:3])}{os.path.sep}rushes'
            os.makedirs(rushes,exist_ok=True)