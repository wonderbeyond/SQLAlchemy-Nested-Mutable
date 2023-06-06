from typing import Optional, List

import pytest
from sqlalchemy_nested_mutable._compat import pydantic
import sqlalchemy as sa
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from sqlalchemy_nested_mutable import (
    MutablePydanticBaseModel,
    TrackedPydanticBaseModel,
    TrackedList,
)


class Base(DeclarativeBase):
    pass


class Addresses(MutablePydanticBaseModel):
    class AddressItem(pydantic.BaseModel):
        street: str
        city: str
        area: Optional[str]

    preferred: Optional[AddressItem]
    work: List[AddressItem] = []
    home: List[AddressItem] = []
    updated_time: Optional[str]


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(30))
    addresses: Mapped[Addresses] = mapped_column(Addresses.as_mutable(), nullable=True)


@pytest.fixture(scope="module", autouse=True)
def _with_tables(session):
    Base.metadata.create_all(session.bind)
    yield
    session.execute(sa.text("""
    DROP TABLE user_account CASCADE;
    """))
    session.commit()


def test_mutable_pydantic_type(session):
    session.add(u := User(name="foo", addresses={"preferred": {"street": "bar", "city": "baz"}}))
    session.commit()

    assert isinstance(u.addresses, MutablePydanticBaseModel)
    assert isinstance(u.addresses.preferred, Addresses.AddressItem)
    assert isinstance(u.addresses.preferred, TrackedPydanticBaseModel)
    assert isinstance(u.addresses.home, TrackedList)
    assert type(u.addresses.preferred).__name__ == "TrackedAddressItem"

    # Shallow change
    u.addresses.updated_time = "2021-01-01T00:00:00"
    session.commit()
    assert u.addresses.updated_time == "2021-01-01T00:00:00"

    # Deep change
    u.addresses.preferred.street = "bar2"
    session.commit()
    assert u.addresses.preferred.dict(exclude_none=True) == {"street": "bar2", "city": "baz"}

    # Append item to list property
    u.addresses.home.append(Addresses.AddressItem.parse_obj({"street": "bar3", "city": "baz"}))
    assert isinstance(u.addresses.home[0], TrackedPydanticBaseModel)
    session.commit()
    assert u.addresses.home[0].dict(exclude_none=True) == {"street": "bar3", "city": "baz"}

    # Change item in list property
    u.addresses.home[0].street = "bar4"
    session.commit()
    assert u.addresses.home[0].dict(exclude_none=True) == {"street": "bar4", "city": "baz"}
