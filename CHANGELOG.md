# Changelog

Alle bedeutenden Änderungen am Gateway Abstraction Layer (GAL) Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

## [1.1.0] - 2025-10-18

### Hinzugefügt

#### Traffic Management Features

- **Rate Limiting & Throttling**
  - Konfigurierbare Requests pro Sekunde und Burst-Limits
  - Mehrere Schlüsseltypen: IP-Adresse, Header, JWT Claim
  - Anpassbare Antwortmeldungen bei Überschreitung des Limits
  - Provider-Unterstützung: Envoy (local_ratelimit), Kong (rate-limiting), APISIX (limit-count), Traefik (RateLimit Middleware)
  - Dokumentation: [docs/guides/RATE_LIMITING.md](docs/guides/RATE_LIMITING.md)
  - 15+ neue Tests, 90% Code Coverage

- **Circuit Breaker Pattern**
  - Automatische Fehlererkennung und Wiederherstellung
  - Konfigurierbare Fehlerschwellwerte und Timeouts
  - Half-Open-State Testing
  - Provider-Unterstützung: APISIX (api-breaker), Traefik (CircuitBreaker), Envoy (Outlier Detection)
  - Kong: Benötigt Third-Party Plugin
  - Dokumentation: [docs/guides/CIRCUIT_BREAKER.md](docs/guides/CIRCUIT_BREAKER.md)
  - 30+ neue Tests

- **Health Checks & Load Balancing**
  - Active Health Checks (periodisches HTTP/TCP Probing)
  - Passive Health Checks (Traffic-basierte Fehlererkennung)
  - Mehrere Backend-Targets mit Gewichtungen
  - Load Balancing Algorithmen: Round Robin, Least Connections, IP Hash, Weighted
  - Sticky Sessions Unterstützung
  - Provider-Unterstützung: Alle 4 Provider (APISIX, Kong, Traefik, Envoy)
  - Dokumentation: [docs/guides/HEALTH_CHECKS.md](docs/guides/HEALTH_CHECKS.md)
  - 50+ neue Tests
  - 15 Beispiel-Szenarien in examples/health-checks-example.yaml

#### Security Features

- **Authentication & Authorization**
  - Basic Authentication (Benutzername/Passwort)
  - API Key Authentication (Header/Query-basiert)
  - JWT Token Validation (JWKS, Issuer/Audience Verifizierung)
  - Claims to Headers Mapping
  - Provider-Unterstützung: Alle 4 Provider mit nativen Plugins
  - Dokumentation: [docs/guides/AUTHENTICATION.md](docs/guides/AUTHENTICATION.md)
  - 33 neue Tests (21 Authentication + 12 Config)
  - 9 Beispiel-Szenarien in examples/authentication-test.yaml

- **Request/Response Header Manipulation**
  - Headers hinzufügen, setzen und entfernen für Requests und Responses
  - Route-Level und Service-Level Konfiguration
  - Template-Variablen-Unterstützung (UUID, Timestamps)
  - Security Headers (X-Frame-Options, CSP, etc.)
  - Provider-Unterstützung: Alle 4 Provider
  - Dokumentation: [docs/guides/HEADERS.md](docs/guides/HEADERS.md)
  - 30 neue Tests (16 Headers + 14 Config)
  - 10 Beispiel-Szenarien in examples/headers-test.yaml

- **CORS Policies**
  - Origin Whitelisting (spezifische Domains oder Wildcard)
  - Granulare HTTP Methoden und Header Kontrolle
  - Credentials Support (Cookies, Auth Headers)
  - Konfigurierbare Preflight Caching (max_age)
  - Provider-Unterstützung: Alle 4 Provider (Kong/APISIX native CORS, Traefik Headers, Envoy CORS Policy)
  - Dokumentation: [docs/guides/CORS.md](docs/guides/CORS.md)
  - 28 CORS Tests + 8 Config Tests
  - 15 Beispiel-Szenarien in examples/cors-example.yaml

#### Distribution & Publishing

- **PyPI Publication**
  - Package veröffentlicht als `gal-gateway` auf PyPI
  - Installation: `pip install gal-gateway`
  - Automatisierte Release-Pipeline über GitHub Actions
  - TestPyPI Unterstützung für Pre-Release Testing
  - Conditional Publishing basierend auf Tag-Format:
    - Pre-Release Tags (alpha/beta/rc) → TestPyPI
    - Stable Tags (vX.Y.Z) → PyPI
  - Package-Validierung mit `twine check`
  - Aktualisierte Keywords: rate-limiting, authentication, cors, circuit-breaker, health-checks, jwt, security
  - Aktualisierte Classifiers: HTTP Servers, Security, AsyncIO
  - Dokumentation: [docs/PYPI_PUBLISHING.md](docs/PYPI_PUBLISHING.md)
  - PyPI Package: https://pypi.org/project/gal-gateway/
  - TestPyPI Package: https://test.pypi.org/project/gal-gateway/

#### Dokumentation

- Umfassende Guides für alle neuen Features:
  - [RATE_LIMITING.md](docs/guides/RATE_LIMITING.md) - 600+ Zeilen
  - [AUTHENTICATION.md](docs/guides/AUTHENTICATION.md) - 923 Zeilen (Deutsch)
  - [HEADERS.md](docs/guides/HEADERS.md) - 700+ Zeilen
  - [CORS.md](docs/guides/CORS.md) - 1000+ Zeilen (Deutsch)
  - [CIRCUIT_BREAKER.md](docs/guides/CIRCUIT_BREAKER.md) - 1000+ Zeilen (Deutsch)
  - [HEALTH_CHECKS.md](docs/guides/HEALTH_CHECKS.md) - 1000+ Zeilen (Deutsch)
  - [PYPI_PUBLISHING.md](docs/PYPI_PUBLISHING.md) - 400+ Zeilen

- Beispiel-Konfigurationen:
  - examples/rate-limiting-example.yaml
  - examples/authentication-test.yaml
  - examples/headers-test.yaml
  - examples/cors-example.yaml (15 Szenarien)
  - examples/circuit-breaker-example.yaml (10+ Szenarien)
  - examples/health-checks-example.yaml (15 Szenarien)

- Aktualisierte README.md:
  - PyPI Installationsanweisungen
  - PyPI Badges (Version, Python-Versionen, Downloads)
  - Links zu PyPI und TestPyPI Packages

#### CI/CD Verbesserungen

- GitHub Actions CI/CD Workflows
  - Automatisierte Tests auf Python 3.10, 3.11, 3.12
  - Docker Image Building und Pushing zu GitHub Container Registry
  - Automatisierte Releases mit Changelog-Generierung
  - PyPI/TestPyPI Publishing bei Tags
- CHANGELOG.md für Tracking von Projekt-Änderungen
- VERSION Datei für Semantic Versioning

#### Claude Code Skills (Development Workflow)

- `documentation` Skill: Verwaltet und aktualisiert GAL Dokumentation
- `release` Skill: Automatisiert den kompletten Release-Prozess
- `actions-monitor` Skill: Überwacht GitHub Actions nach git push

### Geändert

- **Config Model Erweiterungen**
  - `RateLimitConfig` Dataclass hinzugefügt
  - `AuthenticationConfig` mit Basic/API Key/JWT Support hinzugefügt
  - `HeaderManipulation` Dataclass hinzugefügt
  - `CORSPolicy` Dataclass hinzugefügt
  - `CircuitBreakerConfig` Dataclass hinzugefügt
  - `HealthCheckConfig` mit Active/Passive Checks hinzugefügt
  - `LoadBalancerConfig` mit mehreren Algorithmen hinzugefügt
  - `Route` erweitert um alle neuen Features zu unterstützen
  - `Upstream` erweitert um mehrere Targets zu unterstützen

- **Provider Implementierungen**
  - Alle 4 Provider (Envoy, Kong, APISIX, Traefik) aktualisiert um neue Features zu unterstützen
  - Provider-spezifische Dokumentation für jedes Feature

- **Test Coverage**
  - Erhöht von 101 Tests (89% Coverage) auf 400+ Tests
  - Umfassende Test-Abdeckung für alle neuen Features
  - Provider-spezifische Tests für alle Features

### Behoben

- Verschiedene Bugfixes und Verbesserungen über alle Provider hinweg

## [1.0.0] - 2025-01-17

### Added

#### Core Features
- Gateway Abstraction Layer core implementation
- Support for 4 major API gateway providers:
  - Envoy Proxy (static configuration with Lua transformations)
  - Kong API Gateway (declarative DB-less mode)
  - Apache APISIX (JSON configuration with serverless functions)
  - Traefik (dynamic YAML configuration)

#### Configuration System
- YAML-based configuration format
- Service definitions with upstream targets
- Route configuration with path prefixes and HTTP methods
- Global gateway settings (host, port, admin port, timeout)
- Plugin system for gateway extensions

#### Request Transformations
- Default value injection for missing fields
- Computed fields with generators:
  - UUID generation with custom prefixes
  - Timestamp generation
- Request validation with required fields
- Provider-specific transformation implementations:
  - Envoy: Lua filters
  - Kong: request-transformer plugin
  - APISIX: serverless-pre-function with Lua
  - Traefik: middleware plugins (placeholder)

#### CLI Tool
- `generate`: Generate provider-specific configuration
- `generate-all`: Generate configurations for all providers
- `validate`: Validate configuration files
- `info`: Display configuration details
- `list-providers`: List all available providers
- `--log-level` option for controlling verbosity (debug, info, warning, error)

#### Deployment
- Provider deploy methods for all 4 providers:
  - File-based deployment
  - Admin API integration where available
  - Health check and verification
- Docker support with multi-stage builds
- Example configurations for all providers

#### Testing
- Comprehensive test suite with 101 tests:
  - Unit tests for all modules
  - Provider tests
  - CLI tests with Click CliRunner
  - End-to-end workflow tests
  - Deployment tests with mocking
  - Real-world scenario tests
- 89% code coverage
- pytest with pytest-cov

#### Logging
- Structured logging across all modules
- Hierarchical loggers (gal.manager, gal.providers.*, etc.)
- Multiple log levels: DEBUG, INFO, WARNING, ERROR
- CLI integration with --log-level flag
- Detailed operation tracking for debugging

#### Documentation
- Comprehensive README with quick start guide
- Architecture documentation (ARCHITECTURE.md)
- Provider comparison guide (PROVIDERS.md)
- Quick start guide (QUICKSTART.md)
- Transformation guide (TRANSFORMATIONS.md)
- Docker usage guide (DOCKER.md)
- Example configurations for all use cases
- Google-style docstrings for all classes and methods

#### Docker
- Multi-stage Dockerfile for optimized images
- Non-root user execution for security
- Health checks
- Generated config directories
- OCI standard labels for container metadata
- Support for amd64 and arm64 architectures

#### Development Tools
- Requirements management
- Git configuration
- Example configurations
- Docker Compose setup (planned)

### Technical Details

#### Architecture
- Provider interface pattern for extensibility
- Dataclass-based configuration models
- YAML configuration parser
- Manager orchestration layer
- Modular provider implementations

#### Dependencies
- Python 3.10+ support
- click >= 8.1.0 (CLI framework)
- pyyaml >= 6.0 (YAML parsing)
- pytest >= 8.0.0 (testing)
- pytest-cov >= 4.1.0 (coverage)
- requests >= 2.31.0 (HTTP client)

#### Code Quality
- Type hints throughout codebase
- Comprehensive docstrings
- Clean code structure
- Modular design
- Error handling and validation

### Security
- Non-root Docker user
- Input validation
- Secure defaults
- No hardcoded credentials (except APISIX default key with warning)

## [0.1.0] - Initial Development

### Added
- Project initialization
- Basic provider structure
- Configuration models
- Initial documentation

---

## Release Notes

### How to Upgrade

#### From Source
```bash
git pull origin main
pip install -r requirements.txt
```

#### Docker
```bash
docker pull ghcr.io/pt9912/x-gal:latest
```

### Breaking Changes
None in v1.0.0 (initial release)

### Deprecations
None

### Known Issues
- Traefik transformations require custom Go middleware (not included)
- Kong transformations use headers instead of body field injection
- Some provider deploy methods have limited test coverage for error paths

### Future Plans
- PyPI package publication
- Additional gateway providers (HAProxy, Nginx, etc.)
- Advanced transformation features
- Kubernetes deployment support
- Web UI for configuration management
- Configuration validation against provider schemas
- Migration tools between providers
- Performance benchmarking

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backwards compatible manner
- **PATCH** version for backwards compatible bug fixes

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.
