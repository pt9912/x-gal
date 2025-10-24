# JWT Keys and Tokens (Generated at Runtime)

This directory contains JWT keys and tokens that are **automatically generated at runtime** by the E2E test suite.

## Security Notice

⚠️ **These files are NOT committed to the repository for security reasons.**

- Private keys should never be stored in version control
- Keys are generated fresh for each test run
- Files in this directory are ignored by `.gitignore`

## Generated Files

When tests run, the following files are created:

- `private_key.pem` - RSA private key for signing JWT tokens
- `jwks.json` - JSON Web Key Set (public key) for JWT validation
- `admin_token.jwt` - JWT token with `role=admin`
- `user_token.jwt` - JWT token with `role=user`
- `beta_token.jwt` - JWT token with `role=beta`
- `tokens_summary.json` - Summary of all generated tokens

## How It Works

1. **Automatic Generation**: The `conftest.py` fixture `generate_test_keys()` automatically runs before E2E tests
2. **Manual Generation**: Run `python3 generate_local.py` in the `keygen/` directory
3. **Docker Generation**: The `generate_jwt.py` script runs inside Docker containers

## Manual Generation

If you need to generate keys manually:

```bash
cd tests/e2e/docker/tools/keygen
python3 generate_local.py
```

This will create all keys and tokens in the `keys/` subdirectory.

## Usage in Tests

E2E tests automatically use these generated keys for:
- JWT authentication testing with Envoy
- Advanced routing with JWT claim-based routing
- Testing different user roles (admin, user, beta)
