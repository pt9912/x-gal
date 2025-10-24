#!/usr/bin/env python3
"""
Generate an RSA key pair and JWKS for testing JWT validation with Envoy.
Outputs JWKS JSON to jwks.json and private key to private_key.pem.
"""

import base64
import json

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generiere ein RSA-Schlüsselpaar
private_key = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend()
)
public_key = private_key.public_key()

# Extrahiere Modulus (n) und Exponent (e)
public_numbers = public_key.public_numbers()
n = (
    base64.urlsafe_b64encode(
        public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, byteorder="big")
    )
    .decode("utf-8")
    .rstrip("=")
)
e = (
    base64.urlsafe_b64encode(
        public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, byteorder="big")
    )
    .decode("utf-8")
    .rstrip("=")
)

# Erstelle JWKS
jwks = {"keys": [{"kty": "RSA", "kid": "test-key", "n": n, "e": e, "alg": "RS256", "use": "sig"}]}

# Speichere JWKS in Datei
with open("/app/jwks.json", "w") as f:
    json.dump(jwks, f, indent=2)

# Speichere privaten Schlüssel
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
with open("/app/private_key.pem", "wb") as f:
    f.write(private_pem)

print("JWKS saved to /app/jwks.json")
print("Private key saved to /app/private_key.pem")
