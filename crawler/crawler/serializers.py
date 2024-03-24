from os import PathLike
from pathlib import Path
from types import TracebackType
from typing import Any, Generic, Iterator, Type, TypeVar
import orjson
from loguru import logger
from pydantic import BaseModel



BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class NdjsonReader(Generic[BaseModelT]):
    def __init__(
        self,
        path: "PathLike[Any]",
        model: type[BaseModelT],
        validate: bool = False,
        strict: bool = True,
    ):
        self.path = Path(path)
        self.model = model
        self.validate = validate
        self.strict = strict

    def __enter__(self):
        self.file = self.path.open("r")
        return self

    def __exit__(
        self, exc_type: Type[Exception], exc_value: Exception, traceback: TracebackType
    ):
        self.file.close()

    def __iter__(
        self,
    ) -> Iterator[BaseModelT]:
        for line in self.file:
            try:
                if self.validate:
                    yield self.model.model_validate_json(line)
                else:
                    parsed = orjson.loads(line)
                    yield self.model.model_construct(**parsed)
            except Exception as e:
                if self.strict:
                    raise e
                else:
                    logger.error(f"Error parsing line: {line}")
                    logger.error(e)
