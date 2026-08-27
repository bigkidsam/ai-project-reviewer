"""Unit and integration tests for Authentication API endpoints."""

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.models import Base
from backend.app.db.session import get_db

# Create test engine with StaticPool so all threads share the in-memory SQLite database
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)

    def test_demo_login(self):
        response = self.client.post("/auth/demo")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["username"], "demo_user")
        self.assertEqual(data["email"], "demo@reviewer.ai")

    def test_register_and_login(self):
        # Register new user
        reg_payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123",
        }
        reg_resp = self.client.post("/auth/register", json=reg_payload)
        self.assertEqual(reg_resp.status_code, 200)
        reg_data = reg_resp.json()
        self.assertIn("access_token", reg_data)
        self.assertEqual(reg_data["username"], "testuser")

        # Login with username
        login_payload = {
            "username_or_email": "testuser",
            "password": "securepassword123",
        }
        login_resp = self.client.post("/auth/login", json=login_payload)
        self.assertEqual(login_resp.status_code, 200)
        login_data = login_resp.json()
        self.assertIn("access_token", login_data)

        # Login with email
        login_email_payload = {
            "username_or_email": "test@example.com",
            "password": "securepassword123",
        }
        login_email_resp = self.client.post("/auth/login", json=login_email_payload)
        self.assertEqual(login_email_resp.status_code, 200)

    def test_invalid_login(self):
        payload = {
            "username_or_email": "nonexistent",
            "password": "wrongpassword",
        }
        resp = self.client.post("/auth/login", json=payload)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("detail", resp.json())

    def test_duplicate_registration(self):
        reg_payload = {
            "username": "dupuser",
            "email": "dup@example.com",
            "password": "password123",
        }
        self.client.post("/auth/register", json=reg_payload)

        # Duplicate registration
        resp = self.client.post("/auth/register", json=reg_payload)
        self.assertEqual(resp.status_code, 400)

    def test_get_me_authenticated(self):
        demo_resp = self.client.post("/auth/demo")
        token = demo_resp.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        me_resp = self.client.get("/auth/me", headers=headers)
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.json()
        self.assertEqual(me_data["username"], "demo_user")
        self.assertEqual(me_data["email"], "demo@reviewer.ai")

    def test_get_me_unauthenticated(self):
        me_resp = self.client.get("/auth/me")
        self.assertEqual(me_resp.status_code, 401)
