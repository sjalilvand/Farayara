"""پیکربندی تست‌ها — دیتابیس موقت مستقل"""
import os
import tempfile

_tmpdir = tempfile.mkdtemp(prefix="farayara_test_")
os.environ["FARAYARA_DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed()
    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_headers(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def operator_headers(client):
    r = client.post("/api/v1/auth/login", json={"username": "operator", "password": "Oper@1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def auditor_headers(client):
    r = client.post("/api/v1/auth/login", json={"username": "auditor", "password": "Audit@1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def steward_headers(client):
    r = client.post("/api/v1/auth/login", json={"username": "steward", "password": "Data@1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def assessor_headers(client):
    r = client.post("/api/v1/auth/login", json={"username": "assessor", "password": "Assess@1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def pdesigner_headers(client):
    r = client.post("/api/v1/auth/login", json={"username": "pdesigner", "password": "Proc@1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def fdesigner_headers(client):
    r = client.post("/api/v1/auth/login", json={"username": "fdesigner", "password": "Form@1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def contract_headers(client):
    r = client.post("/api/v1/auth/login", json={"username": "contractx", "password": "Contract@1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
