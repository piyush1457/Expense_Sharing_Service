import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Create in-memory SQLite engine for isolated test runs
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Enforce foreign key constraints in in-memory test database
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

@pytest.fixture(scope="function")
def db_session():
    """Provides a transactional database session for each test function."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Provides a TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def sample_users(client) -> list:
    """Fixture that registers Mohit, Rahul, and Ankit in the system."""
    users = [
        {"name": "Mohit", "email": "mohit@example.com"},
        {"name": "Rahul", "email": "rahul@example.com"},
        {"name": "Ankit", "email": "ankit@example.com"}
    ]
    created = []
    for u in users:
        response = client.post("/users", json=u)
        assert response.status_code == 201
        created.append(response.json())
    return created

@pytest.fixture(scope="function")
def sample_group(client, sample_users) -> dict:
    """Fixture that creates group 'Goa Trip' and adds Mohit, Rahul, and Ankit as members."""
    mohit = sample_users[0]
    rahul = sample_users[1]
    ankit = sample_users[2]

    # Create Group
    response = client.post("/groups", json={"name": "Goa Trip", "created_by": mohit["id"]})
    assert response.status_code == 201
    group = response.json()

    # Add all three to group
    for u in [mohit, rahul, ankit]:
        res = client.post(f"/groups/{group['id']}/members", json={"user_id": u["id"]})
        assert res.status_code == 200

    return group
