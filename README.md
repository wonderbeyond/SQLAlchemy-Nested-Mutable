SQLAlchemy-Nested-Mutable
=========================

An advanced SQLAlchemy column type factory that helps map compound Python types (e.g. `list`, `dict`, *Pydantic Model* and their hybrids) to database types (e.g. `ARRAY`, `JSONB`),
And keep track of mutations in deeply nested data structures so that SQLAlchemy can emit proper *UPDATE* statements.

SQLAlchemy-Nested-Mutable is highly inspired by SQLAlchemy-JSON<sup>[[0]](https://github.com/edelooff/sqlalchemy-json)</sup><sup>[[1]](https://variable-scope.com/posts/mutation-tracking-in-nested-json-structures-using-sqlalchemy)</sup>.
However, it does not limit the mapped Python type to be `dict` or `list`.

---

## Why this package?

* By default, SQLAlchemy does not track in-place mutations for non-scalar data types
  such as `list` and `dict` (which are usually mapped with `ARRAY` and `JSON/JSONB`).

* Even though SQLAlchemy provides [an extension](https://docs.sqlalchemy.org/en/20/orm/extensions/mutable.html)
  to track mutations on compound objects, it's too shallow, i.e. it only tracks mutations on the first level of the compound object.

* There exists the [SQLAlchemy-JSON](https://github.com/edelooff/sqlalchemy-json) package
  to help track mutations on nested `dict` or `list` data structures.
  However, the db type is limited to `JSON(B)`.

* Also, I would like the mapped Python types can be subclasses of the Pydantic BaseModelModel,
  which have strong schemas, with the db type be schema-less JSON.


## Installation

```shell
pip install sqlalchemy-nested-mutable
```

## Usage

> NOTE the example below is first updated in `examples/user-addresses.py` and then updated here.

```python
from typing import Optional, List

import pydantic
import sqlalchemy as sa
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column
from sqlalchemy_nested_mutable import MutablePydanticBaseModel


class Base(DeclarativeBase):
    pass


class Addresses(MutablePydanticBaseModel):
    """A container for storing various addresses of users.

    NOTE: for working with pydantic model, use a subclass of `MutablePydanticBaseModel` for column mapping.
    However, the nested models (e.g. `AddressItem` below) should be direct subclasses of `pydantic.BaseModel`.
    """

    class AddressItem(pydantic.BaseModel):
        street: str
        city: str
        area: Optional[str]

    preferred: AddressItem
    work: Optional[AddressItem]
    home: Optional[AddressItem]
    others: List[AddressItem] = []


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(30))
    addresses: Mapped[Addresses] = mapped_column(Addresses.as_mutable(), nullable=True)


engine = sa.create_engine("sqlite://")
Base.metadata.create_all(engine)

with Session(engine) as s:
    s.add(u := User(name="foo", addresses={"preferred": {"street": "bar", "city": "baz"}}))
    assert isinstance(u.addresses, MutablePydanticBaseModel)
    s.commit()

    u.addresses.preferred.street = "bar2"
    s.commit()
    assert u.addresses.preferred.street == "bar2"

    u.addresses.others.append(Addresses.AddressItem.parse_obj({"street": "bar3", "city": "baz3"}))
    s.commit()
    assert isinstance(u.addresses.others[0], Addresses.AddressItem)

    print(u.addresses.dict())
```

For more usage, please refer to the following test files:

* tests/test_mutable_list.py
* tests/test_mutable_dict.py
* tests/test_mutable_pydantic_type.py
