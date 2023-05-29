from typing import List

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(30))
    aliases: Mapped[List[str]] = mapped_column(ARRAY(sa.String(128)))
    addresses: Mapped[dict] = mapped_column(JSONB, default=dict)


@pytest.fixture(scope="module", autouse=True)
def _with_tables(session):
    Base.metadata.create_all(session.bind)
    yield
    session.execute(sa.text("DROP TABLE user_account CASCADE;"))
    session.commit()


def test_sa_array_not_mutable(session):
    session.add(u := User(name="foo", aliases=["bar", "baz"]))
    session.commit()

    u.aliases.append("qux")
    assert u.aliases == ["bar", "baz", "qux"]

    session.commit()

    assert u.aliases == ["bar", "baz"]


def test_sa_jsonb_not_mutable(session):
    session.add(u := User(
        name="bar",
        aliases=["baz", "qux"],
        addresses={
            "home": "bar",
            "work": "baz",
            "email": "xyz@example.com"
        }
    ))
    session.commit()

    u.addresses["email"] = "abc@example.com"
    assert u.addresses["email"] == "abc@example.com"

    session.commit()

    assert u.addresses["email"] == "xyz@example.com"
