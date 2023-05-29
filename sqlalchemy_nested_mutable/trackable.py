from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union, Any, Tuple, Dict, List, Iterable, Self, overload
from weakref import WeakValueDictionary

from sqlalchemy.util.typing import SupportsIndex, TypeGuard
from sqlalchemy.ext.mutable import Mutable

from ._typing import _T, _KT, _VT
from ._compat import pydantic

parents_track: WeakValueDictionary[int, object] = WeakValueDictionary()


class TrackedObject:
    """
    Represents an object in a nested context whose parent can be tracked.

    The top object in the parent link should be an instance of `Mutable`.
    """
    def __del__(self):
        if (id_ := id(self)) in parents_track:
            del parents_track[id_]

    def changed(self):
        if (id_ := id(self)) in parents_track:
            parent = parents_track[id_]
            parent.changed()
        elif isinstance(self, Mutable):
            super().changed()

    @classmethod
    def make_nested_trackable(cls, val: _T, parent: Mutable):
        new_val: Any = val

        if isinstance(val, dict):
            new_val = TrackedDict((k, cls.make_nested_trackable(v, parent)) for k, v in val.items())
        elif isinstance(val, list):
            new_val = TrackedList(cls.make_nested_trackable(o, parent) for o in val)
        elif isinstance(val, pydantic.BaseModel) and not isinstance(val, TrackedPydanticBaseModel):
            model_cls = type('Tracked' + val.__class__.__name__, (TrackedPydanticBaseModel, val.__class__), {})
            model_cls.__doc__ = (
                f"This class is composed of `{val.__class__.__name__}` and `TrackedPydanticBaseModel` "
                "to make it trackable in nested context."
            )
            new_val = model_cls.parse_obj(val.dict())  # type: ignore

        if isinstance(new_val, cls):
            parents_track[id(new_val)] = parent

        return new_val


class TrackedList(TrackedObject, List[_T]):
    def __reduce_ex__(
        self, proto: SupportsIndex
    ) -> Tuple[type, Tuple[List[int]]]:
        return (self.__class__, (list(self),))

    # needed for backwards compatibility with
    # older pickles
    def __setstate__(self, state: Iterable[_T]) -> None:
        self[:] = state

    def is_scalar(self, value: _T | Iterable[_T]) -> TypeGuard[_T]:
        return not isinstance(value, Iterable)

    def is_iterable(self, value: _T | Iterable[_T]) -> TypeGuard[Iterable[_T]]:
        return isinstance(value, Iterable)

    def __setitem__(
        self, index: SupportsIndex | slice, value: _T | Iterable[_T]
    ) -> None:
        """Detect list set events and emit change events."""
        super().__setitem__(index, TrackedObject.make_nested_trackable(value, self))
        self.changed()

    def __delitem__(self, index: SupportsIndex | slice) -> None:
        """Detect list del events and emit change events."""
        super().__delitem__(index)
        self.changed()

    def pop(self, *arg: SupportsIndex) -> _T:
        result = super().pop(*arg)
        self.changed()
        return result

    def append(self, x: _T) -> None:
        super().append(TrackedObject.make_nested_trackable(x, self))
        self.changed()

    def extend(self, x: Iterable[_T]) -> None:
        super().extend(x)
        self.changed()

    def __iadd__(self, x: Iterable[_T]) -> Self:  # type: ignore
        self.extend(TrackedObject.make_nested_trackable(v, self) for v in x)
        return self

    def insert(self, i: SupportsIndex, x: _T) -> None:
        super().insert(i, TrackedObject.make_nested_trackable(x, self))
        self.changed()

    def remove(self, i: _T) -> None:
        super().remove(i)
        self.changed()

    def clear(self) -> None:
        super().clear()
        self.changed()

    def sort(self, **kw: Any) -> None:
        super().sort(**kw)
        self.changed()

    def reverse(self) -> None:
        super().reverse()
        self.changed()


class TrackedDict(TrackedObject, Dict[_KT, _VT]):
    def __setitem__(self, key: _KT, value: _VT) -> None:
        """Detect dictionary set events and emit change events."""
        super().__setitem__(key, value)
        self.changed()

    if TYPE_CHECKING:
        # from https://github.com/python/mypy/issues/14858

        @overload
        def setdefault(
            self: TrackedDict[_KT, Optional[_T]], key: _KT, value: None = None
        ) -> Optional[_T]:
            ...

        @overload
        def setdefault(self, key: _KT, value: _VT) -> _VT:
            ...

        def setdefault(self, key: _KT, value: object = None) -> object:
            ...

    else:

        def setdefault(self, key, value=None):  # noqa: F811
            result = super().setdefault(key, value=TrackedObject.make_nested_trackable(value, self))
            self.changed()
            return result

    def __delitem__(self, key: _KT) -> None:
        """Detect dictionary del events and emit change events."""
        super().__delitem__(key)
        self.changed()

    def update(self, *a: Any, **kw: _VT) -> None:
        a = tuple(TrackedObject.make_nested_trackable(e, self) for e in a)
        kw = {k: TrackedObject.make_nested_trackable(v, self) for k, v in kw.items()}
        super().update(*a, **kw)
        self.changed()

    if TYPE_CHECKING:

        @overload
        def pop(self, __key: _KT) -> _VT:
            ...

        @overload
        def pop(self, __key: _KT, __default: _VT | _T) -> _VT | _T:
            ...

        def pop(
            self, __key: _KT, __default: _VT | _T | None = None
        ) -> _VT | _T:
            ...

    else:

        def pop(self, *arg):  # noqa: F811
            result = super().pop(*arg)
            self.changed()
            return result

    def popitem(self) -> Tuple[_KT, _VT]:
        result = super().popitem()
        self.changed()
        return result

    def clear(self) -> None:
        super().clear()
        self.changed()

    def __setstate__(
        self, state: Union[Dict[str, int], Dict[str, str]]
    ) -> None:
        self.update(state)


if pydantic is not None:
    class TrackedPydanticBaseModel(TrackedObject, Mutable, pydantic.BaseModel):
        @classmethod
        def coerce(cls, key, value):
            return value if isinstance(value, cls) else cls.parse_obj(value)

        def __init__(self, **data):
            super().__init__(**data)
            for field in self.__fields__.values():
                setattr(
                    self,
                    field.name,
                    TrackedObject.make_nested_trackable(getattr(self, field.name), self)
                )

        def __setattr__(self, name, value):
            prev_value = getattr(self, name, None)
            super().__setattr__(name, value)
            if prev_value != getattr(self, name):
                self.changed()
elif not TYPE_CHECKING:
    class TrackedPydanticBaseModel:
        def __new__(cls, *a, **k):
            raise RuntimeError("pydantic is not installed!")
