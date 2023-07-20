from __future__ import annotations

from typing import TYPE_CHECKING, List, Iterable, TypeVar
from typing_extensions import Self

import sqlalchemy as sa
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.sql.type_api import TypeEngine

from .trackable import TrackedObject, TrackedList, TrackedDict, TrackedPydanticBaseModel
from ._typing import _T
from ._compat import pydantic

_P = TypeVar("_P", bound='MutablePydanticBaseModel')


class MutableList(TrackedList, Mutable, List[_T]):
    """
    A mutable list that tracks changes to itself and its children.

    Used as top-level mapped object. e.g.

        aliases: Mapped[list[str]] = mapped_column(MutableList.as_mutable(ARRAY(String(128))))
        schedule: Mapped[list[list[str]]] = mapped_column(MutableList.as_mutable(ARRAY(sa.String(128), dimensions=2)))
    """
    @classmethod
    def coerce(cls, key, value):
        return value if isinstance(value, cls) else cls(value)

    def __init__(self, __iterable: Iterable[_T]):
        super().__init__(TrackedObject.make_nested_trackable(__iterable, self))


class MutableDict(TrackedDict, Mutable):
    @classmethod
    def coerce(cls, key, value):
        return value if isinstance(value, cls) else cls(value)

    def __init__(self, source=(), **kwds):
        super().__init__(TrackedObject.make_nested_trackable(dict(source, **kwds), self))


if pydantic is not None:
    class PydanticType(sa.types.TypeDecorator, TypeEngine[_P]):
        """
        Inspired by https://gist.github.com/imankulov/4051b7805ad737ace7d8de3d3f934d6b
        """
        cache_ok = True
        impl = sa.types.JSON

        def __init__(self, pydantic_type: type[_P], sqltype: TypeEngine[_T] = None):
            super().__init__()
            self.pydantic_type = pydantic_type
            self.sqltype = sqltype

        def load_dialect_impl(self, dialect):
            from sqlalchemy.dialects.postgresql import JSONB

            if self.sqltype is not None:
                return dialect.type_descriptor(self.sqltype)

            if dialect.name == "postgresql":
                return dialect.type_descriptor(JSONB())
            return dialect.type_descriptor(sa.JSON())

        def __repr__(self):
            # NOTE: the `__repr__` is used by Alembic to generate the migration script.
            return f'PydanticType({self.pydantic_type.__name__})'

        def process_bind_param(self, value, dialect):
            return value.dict() if value else None

        def process_result_value(self, value, dialect) -> _P | None:
            return None if value is None else pydantic.parse_obj_as(self.pydantic_type, value)

    class MutablePydanticBaseModel(TrackedPydanticBaseModel, Mutable):
        @classmethod
        def coerce(cls, key, value) -> Self:
            return value if isinstance(value, cls) else cls.parse_obj(value)

        def dict(self, *args, **kwargs):
            res = super().dict(*args, **kwargs)
            res.pop('_parents', None)
            return res

        @classmethod
        def as_mutable(cls, sqltype: TypeEngine[_T] = None) -> TypeEngine[Self]:
            return super().as_mutable(PydanticType(cls, sqltype))
elif not TYPE_CHECKING:
    class PydanticType:
        def __new__(cls, *a, **k):
            raise RuntimeError("PydanticType requires pydantic to be installed")

    class MutablePydanticBaseModel:
        def __new__(cls, *a, **k):
            raise RuntimeError("MutablePydanticBaseModel requires pydantic to be installed")
