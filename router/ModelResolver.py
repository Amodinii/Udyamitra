from typing import Type, List
from pydantic import BaseModel
import inspect
import importlib
from functools import lru_cache

from Logging.logger import logger


class ModelResolver:
    def __init__(self, module_path: str = "utility.model"):
        """
        Initializes the resolver by importing the target module.
        """
        try:
            self.module = importlib.import_module(module_path)
            logger.debug(f"Successfully imported module: {module_path}")
        except ImportError as e:
            raise ImportError(f"Failed to import module '{module_path}': {e}") from e

    @lru_cache(maxsize=None)
    def resolve(self, class_name: str) -> Type[BaseModel]:
        """
        Resolves a class name (e.g., 'SchemeMetadata') to the actual Pydantic model class.
        """
        cls = getattr(self.module, class_name, None)
        if not cls:
            raise ValueError(f"Class '{class_name}' not found in module '{self.module.__name__}'")
        if not inspect.isclass(cls) or not issubclass(cls, BaseModel):
            raise TypeError(f"'{class_name}' is not a valid Pydantic model.")
        logger.debug(f"Resolved model '{class_name}' to {cls}")
        return cls

    def list_models(self) -> List[str]:
        """
        Returns a list of all available Pydantic model class names in the module.
        """
        return sorted([
            name for name, obj in vars(self.module).items()
            if inspect.isclass(obj) and issubclass(obj, BaseModel)
        ])