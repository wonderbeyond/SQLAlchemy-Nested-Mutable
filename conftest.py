import random

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from pytest_docker_service import docker_container

from sqlalchemy_nested_mutable.testing.utils import wait_pg_ready

PG_PORT = "5432/tcp"

pg_container = docker_container(
    scope="session",
    image_name="postgres:15",
    container_name=f"pytest-svc-pg15-{random.randint(0, 1e8)}",
    ports={PG_PORT: None},
    environment={
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
    })


@pytest.fixture(scope="session")
def pg_dbinfo(pg_container):
    port = pg_container.port_map[PG_PORT]
    port = int(port[0] if isinstance(port, list) else port)
    dbinfo = {
        "port": port,
        "host": '127.0.0.1',
        "user": "test",
        "password": "test",
        "database": "test",
    }
    wait_pg_ready(dbinfo)
    print(f"Prepared PostgreSQL: {dbinfo}")
    yield dbinfo


@pytest.fixture(scope="session")
def session(pg_dbinfo):
    engine = sa.create_engine(
        "postgresql://{user}:{password}@{host}:{port}/{database}".format(**pg_dbinfo)
    )
    with sessionmaker(bind=engine)() as session:
        yield session
