from typing import List

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


from sqlalchemy_nested_mutable import MutableList, TrackedList, TrackedDict


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(30))
    aliases = mapped_column(MutableList[str].as_mutable(ARRAY(sa.String(128))), default=list)
    schedule = mapped_column(
        MutableList[List[str]].as_mutable(ARRAY(sa.String(128), dimensions=2)), default=list
    )  # a user's weekly schedule, e.g. [ ['meeting', 'launch'], ['training', 'presentation'] ]


class UserV2(Base):
    """Use JSONB to store array data"""
    __tablename__ = "user_account_v2"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(30))
    aliases = mapped_column(MutableList[str].as_mutable(JSONB), default=list)
    schedule = mapped_column(MutableList[List[str]].as_mutable(JSONB), default=list)


@pytest.fixture(scope="module", autouse=True)
def _with_tables(session):
    Base.metadata.create_all(session.bind)
    yield
    session.execute(sa.text("""
    DROP TABLE user_account CASCADE;
    DROP TABLE user_account_v2 CASCADE;
    """))
    session.commit()


def test_mutable_list(session):
    session.add(u := User(name="foo", aliases=["bar", "baz"]))
    session.commit()

    assert isinstance(u.aliases, MutableList)

    u.aliases.append("qux")
    assert u.aliases == ["bar", "baz", "qux"]

    session.commit()
    assert u.aliases == ["bar", "baz", "qux"]


def test_nested_mutable_list(session):
    session.add(u := User(
        name="foo", schedule=[["meeting", "launch"], ["training", "presentation"]]
    ))
    session.commit()

    assert isinstance(u.aliases, MutableList)
    assert u.schedule == [["meeting", "launch"], ["training", "presentation"]]

    # Mutation at top level
    u.schedule.append(["breakfast", "consulting"])
    session.commit()
    assert u.schedule == [["meeting", "launch"], ["training", "presentation"], ["breakfast", "consulting"]]

    # Mutation at nested level
    u.schedule[0][0] = "breakfast"
    session.commit()
    assert u.schedule == [["breakfast", "launch"], ["training", "presentation"], ["breakfast", "consulting"]]

    u.schedule.pop()
    session.commit()
    assert u.schedule == [["breakfast", "launch"], ["training", "presentation"]]


def test_mutable_list_stored_as_jsonb(session):
    session.add(u := UserV2(name="foo", aliases=["bar", "baz"]))
    session.commit()

    assert isinstance(u.aliases, MutableList)

    u.aliases.append("qux")
    assert u.aliases == ["bar", "baz", "qux"]

    session.commit()
    assert u.aliases == ["bar", "baz", "qux"]


def test_nested_mutable_list_stored_as_jsonb(session):
    session.add(u := UserV2(
        name="foo", schedule=[["meeting", "launch"], ["training", "presentation"]]
    ))
    session.commit()

    assert isinstance(u.aliases, MutableList)
    assert u.schedule == [["meeting", "launch"], ["training", "presentation"]]

    # Mutation at top level
    u.schedule.append(["breakfast", "consulting"])
    session.commit()
    assert u.schedule == [["meeting", "launch"], ["training", "presentation"], ["breakfast", "consulting"]]

    # Mutation at nested level
    u.schedule[0].insert(0, "breakfast")
    session.commit()
    assert u.schedule == [["breakfast", "meeting", "launch"], ["training", "presentation"], ["breakfast", "consulting"]]

    u.schedule.pop()
    session.commit()
    assert u.schedule == [["breakfast", "meeting", "launch"], ["training", "presentation"]]


def test_mutable_list_mixed_with_dict(session):
    session.add(u := UserV2(
        name="foo", schedule=[
            {"day": "mon", "events": ["meeting", "launch"]},
            {"day": "tue", "events": ["training", "presentation"]},
        ]
    ))
    session.commit()
    assert isinstance(u.schedule, MutableList)
    assert isinstance(u.schedule[0], TrackedDict)
    assert isinstance(u.schedule[0]["events"], TrackedList)

    u.schedule[0]["events"].insert(0, "breakfast")
    session.commit()
    assert u.schedule[0] == {"day": "mon", "events": ["breakfast", "meeting", "launch"]}
