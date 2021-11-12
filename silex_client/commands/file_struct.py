from __future__ import annotations
import typing
from typing import Any, Dict, List

from silex_client.action.command_base import CommandBase
from silex_client.utils.log import logger

if typing.TYPE_CHECKING:
    from silex_client.action.action_query import ActionQuery

import gazu.project
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

        # get all project for the user
        projects: List[Dict[Any]] = await gazu.project.all_open_projects()

        if not projects:
            logger.error('No project found')
            return

        # create structure for each project
        for project in projects:

            # get tasks paths
            tasks: Any = await gazu.task.all_tasks_for_project(project)

            if tasks:

                for task in tasks:

                    working_path = await gazu.files.build_working_file_path(
                        task=task
                    )

                    working_path_work: str = os.path.dirname(working_path)
                    working_path_work: str = working_path_work.replace(
                        '/', f'{os.path.sep}')
                    decompo: list[str] = working_path_work.split(os.path.sep)

                    os.makedirs(working_path_work, exist_ok=True)

                    # create sequences folder
                    if decompo[3] == "shots":
                        sequ_path: str = f'{os.path.join(*decompo[:3])}{os.path.sep}sequences{os.path.sep}{decompo[4]}{os.path.sep}{decompo[6]}{os.path.sep}work'

                    # create rushes folder
                    rushes: str = f'{os.path.join(*decompo[:3])}{os.path.sep}editing'
                logger.info('{} was created !'.format(project['name']))

            else:
                logger.error('no tasks found')
                logger.error('{} was not created !'.format(project['name']))
