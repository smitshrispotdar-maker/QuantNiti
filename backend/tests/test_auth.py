"""Authentication and security tests for QuantNiti."""
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime, timedelta, timezone

from app.main import app
from app.config import get_settings
from app.services.auth import (
    create_access_token, 
    decode_token, 
    hash_password, 
    verify_password,
    validate_password_strength,
    AuthError
)
from app.models import User, Base
from app.db import engine, SessionLocal


@pytest.fixture
def test_client():
    """Create a test client - database is set up by conftest.py"""
    return TestClient(app)


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def db_session():
    """Create a database session for tests that need real users."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(autouse=True)
def clear_auth_override():
    """Clear auth override for tests that need real authentication."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


class TestRateLimiting:
    """Tests for authentication rate limiting."""

    def test_login_rate_limit(self, test_client):
        """Test login endpoint rate limiting (10 requests/minute)."""
        # Make 10 requests - should succeed (return 401 for wrong password, not 429)
        for i in range(10):
            response = test_client.post(
                "/api/auth/login",
                json={"email": "test@test.com", "password": "wrong"}
            )
            assert response.status_code == 401  # Wrong credentials, not rate limited

        # 11th request should be rate limited
        response = test_client.post(
            "/api/auth/login",
            json={"email": "test@test.com", "password": "wrong"}
        )
        assert response.status_code == 429, f"Expected 429, got {response.status_code}: {response.text}"

    def test_register_rate_limit(self, test_client):
        """Test register endpoint rate limiting (5 requests/minute)."""
        # Make 5 requests - should succeed (return 400/409 for duplicate, not 429)
        for i in range(5):
            response = test_client.post(
                "/api/auth/register",
                json={"email": f"newuser{i}@test.com", "password": "password123456"}
            )
            # First should be 201, rest 409 (duplicate)
            assert response.status_code in (201, 409), f"Request {i}: {response.status_code}"

        # 6th request should be rate limited
        response = test_client.post(
            "/api/auth/register",
            json={"email": "newuser99@test.com", "password": "password123456"}
        )
        assert response.status_code == 429, f"Expected 429, got {response.status_code}: {response.text}"


class TestJWTValidation:
    """Tests for JWT token validation."""

    def test_valid_token(self, settings):
        """Test that a valid token works."""
        token = create_access_token(10)
        # Verify we can decode it
        user_id = decode_token(token)
        assert user_id == 10

    def test_expired_token(self, settings):
        """Test that an expired token is rejected."""
        # Create a token that's already expired
        expired_token = create_access_token(10, expires_delta=timedelta(seconds=-1))
        with pytest.raises(AuthError) as exc_info:
            decode_token(expired_token)
        assert "Invalid or expired token" in str(exc_info.value)

    def test_invalid_signature(self, settings):
        """Test that a token with wrong signature is rejected."""
        # Create token with different secret
        wrong_secret_token = jwt.encode(
            {"sub": "10", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
            "wrong-secret-key-that-is-long-enough-for-testing",
            algorithm="HS256"
        )
        with pytest.raises(AuthError) as exc_info:
            decode_token(wrong_secret_token)
        assert "Invalid or expired token" in str(exc_info.value)

    def test_malformed_token(self, settings):
        """Test that a malformed token is rejected."""
        with pytest.raises(AuthError) as exc_info:
            decode_token("not.a.valid.token")
        assert "Invalid or expired token" in str(exc_info.value)

    def test_wrong_algorithm(self, settings):
        """Test that token with wrong algorithm (e.g., RS256 instead of HS256) is rejected."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rs256_token = jwt.encode(
            {"sub": "10", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
            private_key,
            algorithm="RS256"
        )
        # This will fail because we expect HS256
        with pytest.raises(AuthError) as exc_info:
            decode_token(rs256_token)
        assert "Invalid or expired token" in str(exc_info.value)

    def test_missing_subject(self, settings):
        """Test that token without 'sub' claim is rejected."""
        no_sub_token = jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
            settings.JWT_SECRET_KEY,
            algorithm="HS256"
        )
        with pytest.raises(AuthError) as exc_info:
            decode_token(no_sub_token)
        assert "Invalid token: missing subject" in str(exc_info.value)

    def test_invalid_subject(self, settings):
        """Test that token with non-integer subject is rejected."""
        invalid_sub_token = jwt.encode(
            {"sub": "not-an-integer", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
            settings.JWT_SECRET_KEY,
            algorithm="HS256"
        )
        with pytest.raises(Exception) as exc_info:
            decode_token(invalid_sub_token)
        # ValueError is raised when converting "not-an-integer" to int
        assert "invalid literal for int()" in str(exc_info.value)

    def test_deleted_user(self, test_client, db_session):
        """Test that token for non-existent user is rejected via auth dependency."""
        # Create token for user ID 999 (doesn't exist)
        token = create_access_token(999)
        response = test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    def test_inactive_user(self, test_client, db_session):
        """Test that inactive user is rejected."""
        # Create an inactive user
        inactive_user = User(id=998, email="inactive2@test.com", hashed_password=hash_password("password123456"), is_active=False)
        db_session.add(inactive_user)
        db_session.commit()
        
        token = create_access_token(998)
        response = test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401


class TestPasswordSecurity:
    """Tests for password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing produces valid Argon2id hash."""
        password = "securepassword123456"
        hashed = hash_password(password)
        assert hashed.startswith("$argon2id$")
        assert verify_password(password, hashed)

    def test_verify_wrong_password(self):
        """Test that wrong password fails verification."""
        password = "securepassword123456"
        hashed = hash_password(password)
        assert not verify_password("wrongpassword", hashed)

    def test_password_min_length(self):
        """Test that short passwords are rejected."""
        with pytest.raises(ValueError):
            validate_password_strength("short")

    def test_password_max_length(self):
        """Test that overly long passwords are rejected."""
        with pytest.raises(ValueError):
            validate_password_strength("a" * 129)

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "securepassword123456"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestCORSAndSecurityHeaders:
    """Tests for CORS and security headers."""

    def test_cors_origin_allowed(self, test_client):
        """Test that allowed origin gets CORS headers."""
        response = test_client.options(
            "/api/auth/login",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"}
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_security_headers_present(self, test_client):
        """Test that security headers are present on responses."""
        response = test_client.get("/api/health")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "content-security-policy" in response.headers


class TestAuthenticationLogging:
    """Tests that auth events are logged appropriately (sanitized)."""

    def test_failed_login_logs_generic(self, test_client, caplog):
        """Test that failed login logs generic message without credentials."""
        import logging
        caplog.set_level(logging.WARNING)
        test_client.post("/api/auth/login", json={"email": "test@test.com", "password": "wrong"})
        # Check that warning was logged (JWT validation failure for wrong password)
        # The log should not contain the password
        for record in caplog.records:
            assert "wrong" not in record.message.lower() if "password" in record.message.lower() else True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])