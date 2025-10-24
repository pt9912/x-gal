#!/usr/bin/env python3
"""
Generate RSA keys, JWKS, and JWT tokens locally (no Docker needed).
Run this script in the keygen directory.
"""

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import base64
import json
import time
import os


def base64url_encode(data):
    """Encode data as base64url (without padding)"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def generate_keys_and_jwks(output_dir="keys"):
    """Generate RSA key pair and JWKS"""
    os.makedirs(output_dir, exist_ok=True)

    print("🔑 Generating RSA key pair...")

    # Generate RSA key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    # Extract public key numbers for JWKS
    public_numbers = public_key.public_numbers()
    n = base64url_encode(
        public_numbers.n.to_bytes(
            (public_numbers.n.bit_length() + 7) // 8,
            byteorder='big'
        )
    )
    e = base64url_encode(
        public_numbers.e.to_bytes(
            (public_numbers.e.bit_length() + 7) // 8,
            byteorder='big'
        )
    )

    # Create JWKS
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key",
                "n": n,
                "e": e,
                "alg": "RS256",
                "use": "sig"
            }
        ]
    }

    # Save JWKS
    jwks_path = os.path.join(output_dir, "jwks.json")
    with open(jwks_path, "w") as f:
        json.dump(jwks, f, indent=2)
    print(f"✅ JWKS saved to: {jwks_path}")

    # Save private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_key_path = os.path.join(output_dir, "private_key.pem")
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    print(f"✅ Private key saved to: {private_key_path}")

    return private_key


def generate_jwt(private_key, payload, kid="test-key"):
    """Generate a JWT token signed with RS256"""

    # JWT Header
    header = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": kid
    }

    # Encode header and payload
    header_b64 = base64url_encode(json.dumps(header, separators=(',', ':')))
    payload_b64 = base64url_encode(json.dumps(payload, separators=(',', ':')))

    # Create message to sign
    message = f"{header_b64}.{payload_b64}".encode('utf-8')

    # Sign with RSA-SHA256
    signature = private_key.sign(
        message,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # Encode signature
    signature_b64 = base64url_encode(signature)

    # Combine into JWT
    jwt_token = f"{header_b64}.{payload_b64}.{signature_b64}"

    return jwt_token


def generate_tokens(private_key, output_dir="keys"):
    """Generate JWT tokens with different claims"""

    print("\n🎫 Generating JWT tokens...")

    now = int(time.time())

    # Admin token
    admin_payload = {
        "sub": "test-admin-user",
        "name": "Admin User",
        "role": "admin",
        "aud": "x-gal-test",
        "iss": "https://jwks-service",
        "iat": now,
        "exp": now + 36000  # Valid for 10 hours
    }
    admin_token = generate_jwt(private_key, admin_payload)
    with open(os.path.join(output_dir, "admin_token.jwt"), "w") as f:
        f.write(admin_token)
    print(f"✅ Admin token saved")

    # User token
    user_payload = {
        "sub": "test-user",
        "name": "Regular User",
        "role": "user",
        "aud": "x-gal-test",
        "iss": "https://jwks-service",
        "iat": now,
        "exp": now + 36000
    }
    user_token = generate_jwt(private_key, user_payload)
    with open(os.path.join(output_dir, "user_token.jwt"), "w") as f:
        f.write(user_token)
    print(f"✅ User token saved")

    # Beta token
    beta_payload = {
        "sub": "test-beta-user",
        "name": "Beta User",
        "role": "beta",
        "aud": "x-gal-test",
        "iss": "https://jwks-service",
        "iat": now,
        "exp": now + 36000
    }
    beta_token = generate_jwt(private_key, beta_payload)
    with open(os.path.join(output_dir, "beta_token.jwt"), "w") as f:
        f.write(beta_token)
    print(f"✅ Beta token saved")

    # Save summary
    summary = {
        "admin": {"token": admin_token, "payload": admin_payload},
        "user": {"token": user_token, "payload": user_payload},
        "beta": {"token": beta_token, "payload": beta_payload}
    }
    with open(os.path.join(output_dir, "tokens_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    return admin_token, user_token, beta_token


def main():
    """Main function"""
    print("=" * 80)
    print("JWT Key & Token Generator (Local)")
    print("=" * 80)
    print()

    # Generate keys and JWKS
    private_key = generate_keys_and_jwks()

    # Generate tokens
    admin_token, user_token, beta_token = generate_tokens(private_key)

    print()
    print("=" * 80)
    print("✅ All done!")
    print("=" * 80)
    print()
    print("Generated files in ./keys/:")
    print("  - jwks.json          (Public JWKS for Envoy)")
    print("  - private_key.pem    (Private key for signing)")
    print("  - admin_token.jwt    (Token with role=admin)")
    print("  - user_token.jwt     (Token with role=user)")
    print("  - beta_token.jwt     (Token with role=beta)")
    print("  - tokens_summary.json")
    print()
    print("Test commands:")
    print(f"  export ADMIN_TOKEN=$(cat keys/admin_token.jwt)")
    print(f'  curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8080/api/admin/test')
    print()


if __name__ == "__main__":
    main()
