from __future__ import annotations

import logging
import typing
import fileseq
import pathlib
from arnold import *
import copy
from typing import Dict, List

from silex_client.action.command_base import CommandBase
from silex_client.action.parameter_buffer import ParameterBuffer
from silex_client.utils.parameter_types import ListParameterMeta, TextParameterMeta
from silex_client.utils import files, constants

import silex_maya.utils.thread as thread_maya


# Forward references
if typing.TYPE_CHECKING:
    from silex_client.action.action_query import ActionQuery


class GetAssReferences(CommandBase):
    """
    Retrieve a stored value from the action's global store
    """

    parameters = {
        "ass_files": {"type": ListParameterMeta(pathlib.Path), "value": []},
    }

    def _get_references_in_ass(self, ass_file: pathlib.Path) -> Dict[str, pathlib.Path]:
        """Parse an .ass file for references then return a dictionary : dict(node_name: reference_path)"""

        # Open ass file
        AiBegin()
        AiMsgSetConsoleFlags(AI_LOG_ALL)
        AiASSLoad(str(ass_file), AI_NODE_ALL)

        node_to_path_dict = dict()

        # Iter through all shading nodes
        iter = AiUniverseGetNodeIterator(AI_NODE_ALL)

        while not AiNodeIteratorFinished(iter):
            node = AiNodeIteratorGetNext(iter)
            node_name = AiNodeGetName(node)

            if AiNodeIs(node, 'image'):
                # Look for textures (images)
                node_to_path_dict[node_name] = pathlib.Path(AiNodeGetStr( node, "filename" ))
          
            elif AiNodeIs(node, 'procedural'):
                # Look for procedurals (can be ass references,...)
                node_to_path_dict[node_name] = pathlib.Path(AiNodeGetStr( node, "filename" ))

            elif AiNodeIs(node, 'volume'):
                # Look for procedurals (can be ass references,...)
                node_to_path_dict[node_name] = pathlib.Path(AiNodeGetStr( node, "filename" ))

            elif AiNodeIs(node, 'photometric_light'):
                # Look for photometric_light
                node_to_path_dict[node_name] = pathlib.Path(AiNodeGetStr( node, "filename" ))

        AiNodeIteratorDestroy(iter)
        AiEnd()

        return node_to_path_dict

    @CommandBase.conform_command()
    async def __call__(
        self,
        parameters: Dict[str, Any],
        action_query: ActionQuery,
        logger: logging.Logger,
    ):
        ass_files: List[pathlib.Path] = parameters["ass_files"]

        # Get texture paths in the .ass file
        node_to_path_dict: Dict[
            str, pathlib.Path
        ] = await thread_maya.execute_in_main_thread(
            self._get_references_in_ass, ass_files[0]
        )

        temp_dict: Dict[str, pathlib.Path] = dict()

        for node, reference in node_to_path_dict.items():
            temp_list = []
        
            # Add sequence to the references list
            sequence =  files.expand_template_to_sequence(reference, constants.ARNOLD_MATCH_SEQUENCE)

            if sequence and not files.is_valid_pipeline_path(pathlib.Path(sequence[0])):
                for path in sequence:

                    # Check if path already conformed                    
                    temp_list.append(pathlib.Path(path))                    

                temp_dict[node] = temp_list

            else:
                # Add, non-sequence paths to the references list
                if not files.is_valid_pipeline_path(pathlib.Path(reference)):
                    temp_dict[node] = [reference]
        
        node_names = list(temp_dict.keys())
        references = list(temp_dict.values())

        # Display a message to the user to inform about all the references to conform
        message = f"The vrscenes\n{fileseq.findSequencesInList(ass_files)[0]}\nis referencing non conformed file(s) :\n\n"
        for file_path in references:
            message += f"- {file_path}\n"

        message += "\nThese files must be conformed and repathed first. "
        message += "Press continue to conform and repath them"
        info_parameter = ParameterBuffer(
            type=TextParameterMeta("info"),
            name="info",
            label="Info",
            value=message,
        )

        # Send the message to inform the user
        if references and not skip_prompt:
            await self.prompt_user(action_query, {"info": info_parameter})

        return {
            "node_names": node_names,
            "references": references,
        }
