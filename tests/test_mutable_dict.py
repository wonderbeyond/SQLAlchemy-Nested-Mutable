import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from sqlalchemy_nested_mutable import MutableDict, TrackedDict, TrackedList


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(30))
    addresses = mapped_column(MutableDict.as_mutable(JSONB), default=dict)


@pytest.fixture(scope="module", autouse=True)
def _with_tables(session):
    Base.metadata.create_all(session.bind)
    yield
    session.execute(sa.text("""
    DROP TABLE user_account CASCADE;
    """))
    session.commit()


def test_mutable_dict(session):
    session.add(u := User(name="foo", addresses={
        "home": {"street": "123 Main Street", "city": "New York"},
        "work": "456 Wall Street",
    }))
    session.commit()

    assert isinstance(u.addresses, MutableDict)
    assert u.addresses["home"] == {"street": "123 Main Street", "city": "New York"}
    assert isinstance(u.addresses['home'], TrackedDict)
    assert isinstance(u.addresses['work'], str)

    # Shallow change
    u.addresses["realtime"] = "999 RT Street"
    session.commit()
    assert u.addresses["realtime"] == "999 RT Street"

    # Deep change
    u.addresses["home"]["street"] = "124 Main Street"
    session.commit()
    assert u.addresses["home"] == {"street": "124 Main Street", "city": "New York"}

    # Change by update()
    u.addresses["home"].update({"street": "125 Main Street"})
    session.commit()
    assert u.addresses["home"] == {"street": "125 Main Street", "city": "New York"}

    u.addresses["home"].update({"area": "America"}, street="126 Main Street")
    session.commit()
    assert u.addresses["home"] == {"street": "126 Main Street", "city": "New York", "area": "America"}


def test_mutable_dict_mixed_with_list(session):
    session.add(u := User(name="bar", addresses={
        "home": {"street": "123 Main Street", "city": "New York"},
        "work": "456 Wall Street",
        "others": [
            {"label": "secret0", "address": "789 Moon Street"},
        ]
    }))
    session.commit()

    assert isinstance(u.addresses["others"], TrackedList)
    assert u.addresses["others"] == [{"label": "secret0", "address": "789 Moon Street"}]

    # Deep change on list value
    u.addresses["others"].append({"label": "secret1", "address": "790 Moon Street"})
    session.commit()
    assert u.addresses["others"] == [
        {"label": "secret0", "address": "789 Moon Street"},
        {"label": "secret1", "address": "790 Moon Street"},
    ]

    # Deep change across list and dict values
    u.addresses["others"][1].update(address="791 Moon Street")
    session.commit()
    assert u.addresses["others"] == [
        {"label": "secret0", "address": "789 Moon Street"},
        {"label": "secret1", "address": "791 Moon Street"},
    ]
