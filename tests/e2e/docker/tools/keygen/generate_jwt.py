#!/usr/bin/env python3
"""
Generate a valid JWT token for testing Envoy JWT authentication.
Uses the private key from private_key.pem to sign the token.
"""

import base64
import json
import sys
import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def base64url_encode(data):
    """Encode data as base64url (without padding)"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def generate_jwt(private_key_path, payload, kid="test-key"):
    """Generate a JWT token signed with RS256"""

    # Load private key
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )

    # JWT Header
    header = {"alg": "RS256", "typ": "JWT", "kid": kid}

    # Encode header and payload
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")))
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")))

    # Create message to sign
    message = f"{header_b64}.{payload_b64}".encode("utf-8")

    # Sign with RSA-SHA256
    signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())

    # Encode signature
    signature_b64 = base64url_encode(signature)

    # Combine into JWT
    jwt_token = f"{header_b64}.{payload_b64}.{signature_b64}"

    return jwt_token


def main():
    """Generate JWT tokens with different claims"""

    private_key_path = "/app/private_key.pem"

    # Check if private key exists
    try:
        with open(private_key_path, "rb") as f:
            pass
    except FileNotFoundError:
        print(f"ERROR: Private key not found at {private_key_path}")
        print("Please run generate_jwks.py first to create the key pair")
        sys.exit(1)

    # Current timestamp
    now = int(time.time())

    # JWT Payload 1: Admin User
    admin_payload = {
        "sub": "test-admin-user",
        "name": "Admin User",
        "role": "admin",
        "aud": "x-gal-test",
        "iss": "https://jwks-service",
        "iat": now,
        "exp": now + 3600,  # Valid for 1 hour
    }

    # JWT Payload 2: Regular User
    user_payload = {
        "sub": "test-regular-user",
        "name": "Regular User",
        "role": "user",
        "aud": "x-gal-test",
        "iss": "https://jwks-service",
        "iat": now,
        "exp": now + 3600,
    }

    # JWT Payload 3: Beta User
    beta_payload = {
        "sub": "test-beta-user",
        "name": "Beta User",
        "role": "beta",
        "features": ["beta-access"],
        "aud": "x-gal-test",
        "iss": "https://jwks-service",
        "iat": now,
        "exp": now + 3600,
    }

    # Generate tokens
    admin_token = generate_jwt(private_key_path, admin_payload)
    user_token = generate_jwt(private_key_path, user_payload)
    beta_token = generate_jwt(private_key_path, beta_payload)

    # Save tokens to files
    with open("/app/admin_token.jwt", "w") as f:
        f.write(admin_token)

    with open("/app/user_token.jwt", "w") as f:
        f.write(user_token)

    with open("/app/beta_token.jwt", "w") as f:
        f.write(beta_token)

    # Print tokens
    print("=" * 80)
    print("JWT Tokens generated successfully!")
    print("=" * 80)
    print()

    print("1. ADMIN TOKEN (role=admin):")
    print(f"   File: /app/admin_token.jwt")
    print(f"   Claims: {json.dumps(admin_payload, indent=6)}")
    print(f"   Token: {admin_token[:50]}...{admin_token[-50:]}")
    print()

    print("2. USER TOKEN (role=user):")
    print(f"   File: /app/user_token.jwt")
    print(f"   Claims: {json.dumps(user_payload, indent=6)}")
    print(f"   Token: {user_token[:50]}...{user_token[-50:]}")
    print()

    print("3. BETA TOKEN (role=beta):")
    print(f"   File: /app/beta_token.jwt")
    print(f"   Claims: {json.dumps(beta_payload, indent=6)}")
    print(f"   Token: {beta_token[:50]}...{beta_token[-50:]}")
    print()

    print("=" * 80)
    print("Usage:")
    print("  curl -H 'Authorization: Bearer <token>' http://localhost:8080/api/admin/test")
    print("=" * 80)

    # Create a summary file
    with open("/app/tokens_summary.json", "w") as f:
        json.dump(
            {
                "admin": {"token": admin_token, "payload": admin_payload},
                "user": {"token": user_token, "payload": user_payload},
                "beta": {"token": beta_token, "payload": beta_payload},
            },
            f,
            indent=2,
        )

    print("\nAll tokens also saved to: /app/tokens_summary.json")


if __name__ == "__main__":
    main()
