# Feature 7: Compatibility Checker

**Status:** 🔄 Geplant
**Aufwand:** 2 Wochen
**Release:** v1.3.0-rc1 (Woche 10)
**Priorität:** 🟡 Mittel

## Übersicht

Der Compatibility Checker validiert, ob eine GAL-Konfiguration auf einem Ziel-Provider funktioniert, und zeigt Feature-Kompatibilität für mehrere Provider gleichzeitig an. Dies hilft Nutzern, **vor der Migration** zu verstehen, welche Features unterstützt werden.

## Use Cases

1. **Pre-Migration Validation**: Prüfe ob Nginx-Config auf HAProxy portierbar ist
2. **Multi-Provider Comparison**: Vergleiche Feature-Support für Envoy vs Kong vs Nginx
3. **Feature Discovery**: Finde heraus, welcher Provider alle benötigten Features unterstützt

## Implementierung

### CLI Commands

```bash
# Check if config works on target provider
gal validate --config gal-config.yaml --target-provider haproxy

# Compare config across multiple providers
gal compare --config gal-config.yaml --providers envoy,kong,nginx,haproxy

# Generate compatibility report
gal compatibility-report --config gal-config.yaml --output compatibility.md
```

### Core Komponente: CompatibilityChecker

```python
# gal/compatibility.py

from typing import List, Dict, Any, Set
from dataclasses import dataclass
from enum import Enum

from gal.config import Config, Service, Route
from gal.provider import Provider

class CompatibilityLevel(Enum):
    """Compatibility level for a feature."""
    FULL = "full"          # ✅ Full support, no limitations
    PARTIAL = "partial"    # ⚠️ Supported with limitations
    UNSUPPORTED = "unsupported"  # ❌ Not supported
    MANUAL = "manual"      # 🔧 Requires manual configuration

@dataclass
class FeatureCompatibility:
    """Compatibility status for a single feature."""
    feature_name: str
    level: CompatibilityLevel
    message: str
    workaround: Optional[str] = None

@dataclass
class ProviderCompatibility:
    """Overall compatibility for a provider."""
    provider_name: str
    compatible: bool
    features: List[FeatureCompatibility]
    warnings: List[str]
    errors: List[str]

class CompatibilityChecker:
    """Check config compatibility across providers."""

    def __init__(self):
        # Feature support matrix
        self.feature_matrix = self._build_feature_matrix()

    def _build_feature_matrix(self) -> Dict[str, Dict[str, CompatibilityLevel]]:
        """Build feature support matrix for all providers.

        Returns:
            Dict: {feature_name: {provider_name: CompatibilityLevel}}
        """
        return {
            "rate_limiting": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.FULL,
                "nginx": CompatibilityLevel.FULL,
                "haproxy": CompatibilityLevel.FULL
            },
            "basic_auth": {
                "envoy": CompatibilityLevel.PARTIAL,  # Requires Lua
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.FULL,
                "nginx": CompatibilityLevel.FULL,
                "haproxy": CompatibilityLevel.PARTIAL  # Basic support
            },
            "api_key_auth": {
                "envoy": CompatibilityLevel.PARTIAL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.MANUAL,
                "nginx": CompatibilityLevel.MANUAL,
                "haproxy": CompatibilityLevel.MANUAL
            },
            "jwt_auth": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.PARTIAL,  # ForwardAuth
                "nginx": CompatibilityLevel.MANUAL,  # OpenResty
                "haproxy": CompatibilityLevel.MANUAL  # Lua
            },
            "active_health_checks": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.UNSUPPORTED,  # Plus only
                "nginx": CompatibilityLevel.UNSUPPORTED,  # Plus only
                "haproxy": CompatibilityLevel.FULL
            },
            "passive_health_checks": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.PARTIAL,
                "nginx": CompatibilityLevel.FULL,
                "haproxy": CompatibilityLevel.FULL
            },
            "circuit_breaker": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.UNSUPPORTED,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.UNSUPPORTED,
                "nginx": CompatibilityLevel.PARTIAL,  # Via Lua
                "haproxy": CompatibilityLevel.PARTIAL  # Via fall/rise
            },
            "cors": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.FULL,
                "nginx": CompatibilityLevel.FULL,
                "haproxy": CompatibilityLevel.FULL
            },
            "headers": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.FULL,
                "nginx": CompatibilityLevel.FULL,
                "haproxy": CompatibilityLevel.FULL
            },
            "load_balancing_round_robin": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.FULL,
                "nginx": CompatibilityLevel.FULL,
                "haproxy": CompatibilityLevel.FULL
            },
            "load_balancing_least_conn": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.FULL,
                "nginx": CompatibilityLevel.FULL,
                "haproxy": CompatibilityLevel.FULL
            },
            "load_balancing_ip_hash": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.FULL,
                "apisix": CompatibilityLevel.FULL,
                "traefik": CompatibilityLevel.UNSUPPORTED,
                "nginx": CompatibilityLevel.FULL,
                "haproxy": CompatibilityLevel.FULL
            },
            "sticky_sessions": {
                "envoy": CompatibilityLevel.FULL,
                "kong": CompatibilityLevel.UNSUPPORTED,
                "apisix": CompatibilityLevel.UNSUPPORTED,
                "traefik": CompatibilityLevel.FULL,
                "nginx": CompatibilityLevel.PARTIAL,
                "haproxy": CompatibilityLevel.FULL
            }
        }

    def check_compatibility(
        self,
        config: Config,
        target_provider: str
    ) -> ProviderCompatibility:
        """Check if config is compatible with target provider.

        Args:
            config: GAL configuration
            target_provider: Target provider name (envoy, kong, etc.)

        Returns:
            ProviderCompatibility: Compatibility report
        """
        features = []
        warnings = []
        errors = []

        # Check each feature used in config
        used_features = self._extract_features_from_config(config)

        for feature_name in used_features:
            if feature_name not in self.feature_matrix:
                # Unknown feature
                warnings.append(f"Unknown feature: {feature_name}")
                continue

            level = self.feature_matrix[feature_name].get(
                target_provider,
                CompatibilityLevel.UNSUPPORTED
            )

            message = self._get_compatibility_message(feature_name, target_provider, level)
            workaround = self._get_workaround(feature_name, target_provider, level)

            features.append(FeatureCompatibility(
                feature_name=feature_name,
                level=level,
                message=message,
                workaround=workaround
            ))

            # Add to warnings/errors
            if level == CompatibilityLevel.UNSUPPORTED:
                errors.append(f"{feature_name}: Not supported on {target_provider}")
            elif level == CompatibilityLevel.PARTIAL:
                warnings.append(f"{feature_name}: Limited support on {target_provider}")
            elif level == CompatibilityLevel.MANUAL:
                warnings.append(f"{feature_name}: Requires manual configuration on {target_provider}")

        # Overall compatibility
        compatible = len(errors) == 0

        return ProviderCompatibility(
            provider_name=target_provider,
            compatible=compatible,
            features=features,
            warnings=warnings,
            errors=errors
        )

    def compare_providers(
        self,
        config: Config,
        providers: List[str]
    ) -> Dict[str, ProviderCompatibility]:
        """Compare config compatibility across multiple providers.

        Args:
            config: GAL configuration
            providers: List of provider names

        Returns:
            Dict: {provider_name: ProviderCompatibility}
        """
        results = {}

        for provider in providers:
            results[provider] = self.check_compatibility(config, provider)

        return results

    def _extract_features_from_config(self, config: Config) -> Set[str]:
        """Extract list of features used in config."""
        features = set()

        for service in config.services:
            # Load balancing
            if service.upstream and service.upstream.load_balancer:
                algorithm = service.upstream.load_balancer.algorithm
                features.add(f"load_balancing_{algorithm}")

                if service.upstream.load_balancer.sticky_sessions:
                    features.add("sticky_sessions")

            # Health checks
            if service.upstream and service.upstream.health_check:
                if service.upstream.health_check.active:
                    features.add("active_health_checks")
                if service.upstream.health_check.passive:
                    features.add("passive_health_checks")

            # Routes
            for route in service.routes:
                if route.rate_limit and route.rate_limit.enabled:
                    features.add("rate_limiting")

                if route.authentication and route.authentication.enabled:
                    auth_type = route.authentication.type
                    if auth_type == "basic":
                        features.add("basic_auth")
                    elif auth_type == "api_key":
                        features.add("api_key_auth")
                    elif auth_type == "jwt":
                        features.add("jwt_auth")

                if route.headers:
                    features.add("headers")

                if route.cors and route.cors.enabled:
                    features.add("cors")

                if route.circuit_breaker and route.circuit_breaker.enabled:
                    features.add("circuit_breaker")

        return features

    def _get_compatibility_message(
        self,
        feature_name: str,
        provider: str,
        level: CompatibilityLevel
    ) -> str:
        """Get user-friendly compatibility message."""
        messages = {
            (CompatibilityLevel.FULL, None): "✅ Fully supported",
            (CompatibilityLevel.PARTIAL, "basic_auth"): "⚠️ Supported but users must be configured separately",
            (CompatibilityLevel.PARTIAL, "jwt_auth"): "⚠️ Requires external auth service or additional setup",
            (CompatibilityLevel.UNSUPPORTED, "active_health_checks"): "❌ Only available in Plus/Enterprise version",
            (CompatibilityLevel.MANUAL, "api_key_auth"): "🔧 Requires manual header validation setup",
            (CompatibilityLevel.MANUAL, "jwt_auth"): "🔧 Requires OpenResty/Lua scripting"
        }

        key = (level, feature_name)
        if key in messages:
            return messages[key]

        key = (level, None)
        if key in messages:
            return messages[key]

        return f"{level.value.title()} support"

    def _get_workaround(
        self,
        feature_name: str,
        provider: str,
        level: CompatibilityLevel
    ) -> Optional[str]:
        """Get workaround suggestion for limited/unsupported features."""
        if level == CompatibilityLevel.FULL:
            return None

        workarounds = {
            ("jwt_auth", "nginx"): "Use OpenResty with lua-resty-jwt plugin",
            ("jwt_auth", "haproxy"): "Use HAProxy Lua scripts or external auth service",
            ("active_health_checks", "nginx"): "Upgrade to Nginx Plus or use passive health checks",
            ("active_health_checks", "traefik"): "Upgrade to Traefik Enterprise or use passive health checks",
            ("circuit_breaker", "kong"): "Use rate limiting as alternative or implement in application",
            ("api_key_auth", "nginx"): "Validate X-API-Key header using Lua or map directive"
        }

        return workarounds.get((feature_name, provider))

    def generate_compatibility_report(
        self,
        config: Config,
        providers: List[str]
    ) -> str:
        """Generate Markdown compatibility report.

        Args:
            config: GAL configuration
            providers: List of providers to compare

        Returns:
            str: Markdown formatted report
        """
        results = self.compare_providers(config, providers)

        report = ["# GAL Compatibility Report\n"]
        report.append(f"**Config:** {config.version}\n")
        report.append(f"**Providers:** {', '.join(providers)}\n\n")

        # Summary table
        report.append("## Summary\n\n")
        report.append("| Provider | Compatible | Warnings | Errors |\n")
        report.append("|----------|------------|----------|--------|\n")

        for provider in providers:
            compat = results[provider]
            compatible_emoji = "✅" if compat.compatible else "❌"
            report.append(
                f"| {provider} | {compatible_emoji} | {len(compat.warnings)} | {len(compat.errors)} |\n"
            )

        # Detailed feature comparison
        report.append("\n## Feature Support Matrix\n\n")

        # Get all features
        all_features = set()
        for compat in results.values():
            for feature in compat.features:
                all_features.add(feature.feature_name)

        # Table header
        report.append("| Feature | " + " | ".join(providers) + " |\n")
        report.append("|---------|" + "|".join(["-------"] * len(providers)) + "|\n")

        # Table rows
        for feature_name in sorted(all_features):
            row = f"| {feature_name} | "

            for provider in providers:
                compat = results[provider]
                feature_compat = next(
                    (f for f in compat.features if f.feature_name == feature_name),
                    None
                )

                if feature_compat:
                    if feature_compat.level == CompatibilityLevel.FULL:
                        symbol = "✅"
                    elif feature_compat.level == CompatibilityLevel.PARTIAL:
                        symbol = "⚠️"
                    elif feature_compat.level == CompatibilityLevel.MANUAL:
                        symbol = "🔧"
                    else:
                        symbol = "❌"
                    row += f"{symbol} | "
                else:
                    row += "- | "

            report.append(row + "\n")

        # Warnings and errors per provider
        report.append("\n## Provider Details\n\n")

        for provider in providers:
            compat = results[provider]

            report.append(f"### {provider.title()}\n\n")

            if compat.compatible:
                report.append(f"✅ **Compatible** - Configuration will work on {provider}\n\n")
            else:
                report.append(f"❌ **Incompatible** - {len(compat.errors)} critical issue(s)\n\n")

            if compat.errors:
                report.append("**Errors:**\n\n")
                for error in compat.errors:
                    report.append(f"- ❌ {error}\n")
                report.append("\n")

            if compat.warnings:
                report.append("**Warnings:**\n\n")
                for warning in compat.warnings:
                    report.append(f"- ⚠️ {warning}\n")
                report.append("\n")

            # Workarounds
            features_with_workarounds = [
                f for f in compat.features
                if f.workaround
            ]

            if features_with_workarounds:
                report.append("**Workarounds:**\n\n")
                for feature in features_with_workarounds:
                    report.append(f"- **{feature.feature_name}**: {feature.workaround}\n")
                report.append("\n")

        return "".join(report)
```

### CLI Integration

```python
# gal-cli.py

@cli.command("compare")
@click.option("--config", required=True, help="GAL configuration file")
@click.option("--providers", required=True, help="Comma-separated provider list")
@click.option("--output", help="Output report file (Markdown)")
def compare_providers(config, providers, output):
    """Compare config compatibility across providers."""
    # Load config
    config_obj = load_config(config)

    # Parse providers
    provider_list = [p.strip() for p in providers.split(",")]

    # Check compatibility
    checker = CompatibilityChecker()
    report = checker.generate_compatibility_report(config_obj, provider_list)

    if output:
        with open(output, "w") as f:
            f.write(report)
        click.echo(f"✅ Compatibility report written to {output}")
    else:
        click.echo(report)


@cli.command("validate")
@click.option("--config", required=True, help="GAL configuration file")
@click.option("--target-provider", help="Target provider for compatibility check")
def validate_config(config, target_provider):
    """Validate GAL configuration."""
    config_obj = load_config(config)

    # Basic validation
    if not config_obj.services:
        click.echo("❌ No services defined", err=True)
        sys.exit(1)

    click.echo("✅ Configuration is valid")

    # Provider-specific validation
    if target_provider:
        checker = CompatibilityChecker()
        compat = checker.check_compatibility(config_obj, target_provider)

        if compat.compatible:
            click.echo(f"✅ Compatible with {target_provider}")
        else:
            click.echo(f"❌ Not compatible with {target_provider}")

            for error in compat.errors:
                click.echo(f"  - {error}", err=True)

            sys.exit(1)

        if compat.warnings:
            click.echo(f"\n⚠️  Warnings:")
            for warning in compat.warnings:
                click.echo(f"  - {warning}")
```

## CLI Usage

### Beispiel 1: Single Provider Check

```bash
$ gal validate --config gal-config.yaml --target-provider haproxy

✅ Configuration is valid
✅ Compatible with haproxy

⚠️  Warnings:
  - jwt_auth: Requires manual configuration on haproxy
  - active_health_checks: Full support
```

### Beispiel 2: Multi-Provider Comparison

```bash
$ gal compare --config gal-config.yaml --providers envoy,kong,nginx,haproxy --output comparison.md

✅ Compatibility report written to comparison.md
```

**comparison.md:**

```markdown
# GAL Compatibility Report

**Config:** 1.0
**Providers:** envoy, kong, nginx, haproxy

## Summary

| Provider | Compatible | Warnings | Errors |
|----------|------------|----------|--------|
| envoy | ✅ | 0 | 0 |
| kong | ✅ | 1 | 0 |
| nginx | ❌ | 2 | 1 |
| haproxy | ✅ | 1 | 0 |

## Feature Support Matrix

| Feature | envoy | kong | nginx | haproxy |
|---------|-------|------|-------|---------|
| active_health_checks | ✅ | ✅ | ❌ | ✅ |
| jwt_auth | ✅ | ✅ | 🔧 | 🔧 |
| rate_limiting | ✅ | ✅ | ✅ | ✅ |

## Provider Details

### Nginx

❌ **Incompatible** - 1 critical issue(s)

**Errors:**
- ❌ active_health_checks: Not supported on nginx

**Warnings:**
- ⚠️ jwt_auth: Requires manual configuration on nginx

**Workarounds:**
- **active_health_checks**: Upgrade to Nginx Plus or use passive health checks
- **jwt_auth**: Use OpenResty with lua-resty-jwt plugin
```

## Test Cases

20+ Tests:
- Feature extraction from config
- Compatibility checking (single provider)
- Multi-provider comparison
- Report generation (Markdown)
- Edge cases (unknown features, all providers compatible)
- CLI integration tests

## Akzeptanzkriterien

- ✅ Feature-Support-Matrix für alle 6 Provider
- ✅ Single-Provider Compatibility Check
- ✅ Multi-Provider Comparison
- ✅ Markdown Report Generation
- ✅ Workaround Suggestions
- ✅ CLI Integration (validate, compare)
- ✅ 20+ Tests, 90%+ Coverage

## Implementierungs-Reihenfolge

1. **Tag 1-3**: CompatibilityChecker + Feature Matrix
2. **Tag 4-5**: check_compatibility() + compare_providers()
3. **Tag 6-7**: Report Generation (Markdown)
4. **Tag 8-9**: CLI Integration
5. **Tag 10-12**: Tests + Edge Cases + Documentation
6. **Tag 13-14**: Refinement + User Feedback

## Nächste Schritte

Nach Completion:
1. Release als v1.3.0-rc1
2. User Feedback
3. Migration Assistant (Feature 8) beginnen
