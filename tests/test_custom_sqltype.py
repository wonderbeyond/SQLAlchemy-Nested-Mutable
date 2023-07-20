from typing import Optional, List

import pytest
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy_nested_mutable._compat import pydantic
import sqlalchemy as sa
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from sqlalchemy_nested_mutable import MutablePydanticBaseModel


class Base(DeclarativeBase):
    pass


class Addresses(MutablePydanticBaseModel):
    class AddressItem(pydantic.BaseModel):
        street: str
        city: str
        area: Optional[str]

    work: List[AddressItem] = []
    home: List[AddressItem] = []


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(30))
    addresses_default: Mapped[Optional[Addresses]] = mapped_column(Addresses.as_mutable())
    addresses_json: Mapped[Optional[Addresses]] = mapped_column(Addresses.as_mutable(JSON))
    addresses_jsonb: Mapped[Optional[Addresses]] = mapped_column(Addresses.as_mutable(JSONB))


@pytest.fixture(scope="module", autouse=True)
def _with_tables(session):
    Base.metadata.create_all(session.bind)
    yield
    session.execute(sa.text("""
    DROP TABLE user_account CASCADE;
    """))
    session.commit()


def test_mutable_pydantic_type(session):
    session.add(User(name="foo"))
    session.commit()
    assert session.scalar(sa.select(sa.func.pg_typeof(User.addresses_default))) == "jsonb"
    assert session.scalar(sa.select(sa.func.pg_typeof(User.addresses_json))) == "json"
    assert session.scalar(sa.select(sa.func.pg_typeof(User.addresses_jsonb))) == "jsonb"
