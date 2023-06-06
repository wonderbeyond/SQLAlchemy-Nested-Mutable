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
