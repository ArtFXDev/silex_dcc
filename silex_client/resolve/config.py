import os
import copy
from typing import Union, Any

from silex_client.utils.log import logger
from silex_client.resolve.loader import Loader


class Config:
    """
    Utility class that lazy load and resolve the configurations on demand

    :ivar action_search_path: List of path to look for config files. The order matters.
    """

    def __init__(self, action_search_path: Union[list, str] = None):
        # List of the path to look for any included file
        self.action_search_path = ["/"]

        # Add the custom config search path
        if action_search_path is not None:
            if isinstance(action_search_path, str):
                self.action_search_path.append(action_search_path)
            else:
                self.action_search_path += action_search_path

        # Look for config search path in the environment variables
        env_config_path = os.getenv("SILEX_ACTION_CONFIG")
        if env_config_path is not None:
            self.action_search_path += env_config_path.split(os.pathsep)

    @property
    def actions(self) -> list:
        """
        List of all the available actions config found
        """
        # TODO: Add some search path according to the given kwargs
        search_path = copy.deepcopy(self.action_search_path)
        found_actions = []

        for path in search_path:
            for file_path in os.listdir(path):
                split_path = os.path.splitext(file_path)
                if os.path.splitext(file_path)[1] in [".yaml", ".yml"]:
                    action_path = os.path.abspath(os.path.join(path, file_path))
                    found_actions.append({"name": split_path[0], "path": action_path})

        return found_actions

    def resolve_action(self, action_name: str) -> Any:
        """
        Resolve a config file from its name by looking in the stored root path
        """
        # Find the action config
        if action_name not in [action["name"] for action in self.actions]:
            logger.error("Could not resolve config for the action %s", action_name)
            return None

        config_path = next(
            action["path"] for action in self.actions if action["name"] == action_name
        )
        logger.debug("Found action config at %s", config_path)
        return self._load_config(config_path)

    def _load_config(self, config_path: str) -> Any:
        # Load the config
        with open(config_path, "r", encoding="utf-8") as config_data:
            search_path = copy.deepcopy(self.action_search_path)
            loader = Loader(config_data, tuple(search_path))
            try:
                return loader.get_single_data()
            finally:
                loader.dispose()
