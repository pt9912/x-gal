# Architecture Overview

## System Design

```
┌─────────────────────────────────────────┐
│   gateway-config.yaml                    │
│   - Provider selection                   │
│   - Service definitions                  │
│   - Transformation rules                 │
└──────────────────┬──────────────────────┘
                   │
                   │ Config.from_yaml()
                   │
┌──────────────────▼──────────────────────┐
│   Manager                                │
│   - Load configuration                   │
│   - Register providers                   │
│   - Coordinate generation                │
└──────────────────┬──────────────────────┘
                   │
                   │ generate()
                   │
┌──────────────────▼──────────────────────┐
│   Provider (Interface)                   │
│   - validate()                           │
│   - generate()                           │
│   - deploy() [optional]                  │
└──────────────────┬──────────────────────┘
                   │
      ┌────────────┼────────────┬─────────┐
      │            │            │         │
┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐ ┌─▼──────┐
│   Envoy   │ │  Kong  │ │  APISIX  │ │Traefik │
│ Provider  │ │Provider│ │ Provider │ │Provider│
└───────────┘ └────────┘ └──────────┘ └────────┘
```

## Components

### 1. Configuration Models (`gal/config.py`)

**Dataclasses for type-safe configuration:**
- `Config`: Main configuration
- `Service`: Service definition
- `Transformation`: Transformation rules
- `Route`, `Upstream`, etc.

**Key features:**
- Type hints for IDE support
- Validation through Pydantic (optional)
- YAML parsing with `from_yaml()` classmethod

### 2. Manager (`gal/manager.py`)

**Orchestrates all operations:**
- Registers providers
- Loads configuration
- Validates before generation
- Delegates to appropriate provider

**Responsibilities:**
- Provider registry management
- Configuration loading and parsing
- Error handling and validation

### 3. Provider Interface (`gal/provider.py`)

**Abstract base class for all providers:**
```python
class Provider(ABC):
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def validate(self, config: Config) -> bool: ...
    
    @abstractmethod
    def generate(self, config: Config) -> str: ...
    
    def deploy(self, config: Config) -> bool: ...
```

### 4. Provider Implementations

Each provider generates native configuration:

**EnvoyProvider** (`providers/envoy.py`)
- Generates Envoy YAML
- Supports gRPC and HTTP
- Includes Lua filters for transformations

**KongProvider** (`providers/kong.py`)
- Generates Kong declarative config
- Includes plugin configurations
- Request transformer support

**APISIXProvider** (`providers/apisix.py`)
- Generates APISIX JSON
- Lua script generation
- Serverless functions for transformations

**TraefikProvider** (`providers/traefik.py`)
- Generates Traefik YAML
- Middleware support
- Dynamic configuration

### 5. CLI (`gal-cli.py`)

**Command-line interface using Click:**
- `generate`: Generate for one provider
- `generate-all`: Generate for all providers
- `validate`: Validate configuration
- `info`: Show configuration details
- `list-providers`: List available providers

## Data Flow

1. **Load**: YAML → Config objects
2. **Validate**: Check configuration validity
3. **Generate**: Config → Provider-specific output
4. **Output**: Write to file or stdout

## Design Principles

### Separation of Concerns
- Configuration parsing separate from generation
- Each provider independent
- Clear interfaces between components

### Extensibility
Adding a new provider requires:
1. Create new provider class
2. Implement Provider interface
3. Register in CLI
4. Done!

### Type Safety
- Python type hints throughout
- Dataclasses for structure
- IDE support and autocompletion

### Testability
- Pure functions where possible
- Dependency injection
- Mock-friendly interfaces

## Directory Structure

```
gal/
├── __init__.py           # Package initialization
├── config.py             # Configuration models
├── manager.py            # Orchestration
├── provider.py           # Provider interface
├── providers/            # Provider implementations
│   ├── __init__.py
│   ├── envoy.py
│   ├── kong.py
│   ├── apisix.py
│   └── traefik.py
└── transformation/       # Future: advanced transformations
    ├── __init__.py
    ├── engine.py
    └── generators.py
```

## Extension Points

### Adding New Providers
1. Subclass `Provider`
2. Implement required methods
3. Register in manager

### Adding New Features
1. Extend configuration models
2. Update provider implementations
3. Add CLI commands if needed

### Custom Transformations
1. Extend `Transformation` class
2. Implement in provider generators
3. Add to YAML schema
