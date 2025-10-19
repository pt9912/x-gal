"""Compatibility checking for GAL configurations across providers.

This module provides functionality to check if a GAL configuration
is compatible with specific gateway providers and to compare
compatibility across multiple providers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from gal.config import Config, Route, Service


class FeatureSupport(Enum):
    """Level of support for a feature."""

    FULL = "full"  # ✅ Fully supported
    PARTIAL = "partial"  # ⚠️ Partially supported / requires workarounds
    UNSUPPORTED = "unsupported"  # ❌ Not supported


@dataclass
class FeatureCheck:
    """Result of checking a single feature."""

    feature_name: str
    support: FeatureSupport
    message: str = ""
    recommendation: str = ""


@dataclass
class CompatibilityReport:
    """Detailed compatibility report for a provider."""

    provider: str
    compatible: bool
    compatibility_score: float  # 0.0 to 1.0
    features_checked: int
    features_supported: List[FeatureCheck] = field(default_factory=list)
    features_partial: List[FeatureCheck] = field(default_factory=list)
    features_unsupported: List[FeatureCheck] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def get_summary(self) -> str:
        """Get human-readable summary."""
        total = self.features_checked
        supported = len(self.features_supported)
        partial = len(self.features_partial)
        unsupported = len(self.features_unsupported)

        status = "✅ Compatible" if self.compatible else "❌ Incompatible"
        score_pct = int(self.compatibility_score * 100)

        summary = [
            f"{status} with {self.provider.title()}",
            f"Compatibility: {score_pct}% ({supported}/{total} features fully supported)",
        ]

        if partial > 0:
            summary.append(f"Partial Support: {partial} features require workarounds")

        if unsupported > 0:
            summary.append(f"Unsupported: {unsupported} features not available")

        return "\n".join(summary)


class CompatibilityChecker:
    """Check GAL config compatibility with providers."""

    # Feature support matrix for all providers
    # Format: {feature_name: {provider_name: FeatureSupport}}
    FEATURE_MATRIX: Dict[str, Dict[str, FeatureSupport]] = {
        "routing_path_prefix": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "http_methods": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "load_balancing_round_robin": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "load_balancing_least_conn": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "load_balancing_ip_hash": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.PARTIAL,  # Limited sticky sessions
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "health_check_active": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.UNSUPPORTED,  # OSS only has passive
            "nginx": FeatureSupport.UNSUPPORTED,  # Only passive
            "haproxy": FeatureSupport.FULL,
        },
        "health_check_passive": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "rate_limiting": {
            "envoy": FeatureSupport.PARTIAL,  # Global only in OSS
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "authentication_basic": {
            "envoy": FeatureSupport.PARTIAL,  # Via Lua filter
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "authentication_api_key": {
            "envoy": FeatureSupport.PARTIAL,  # Via Lua filter
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.PARTIAL,  # Via forwardAuth
            "nginx": FeatureSupport.PARTIAL,  # Via Lua (OpenResty)
            "haproxy": FeatureSupport.FULL,
        },
        "authentication_jwt": {
            "envoy": FeatureSupport.FULL,  # Native JWT filter
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.PARTIAL,  # Via forwardAuth
            "nginx": FeatureSupport.PARTIAL,  # Via lua-resty-jwt
            "haproxy": FeatureSupport.PARTIAL,  # Via Lua scripting
        },
        "headers_request": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "headers_response": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "cors": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "sticky_sessions": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "circuit_breaker": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.PARTIAL,  # Third-party plugin
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.UNSUPPORTED,
            "haproxy": FeatureSupport.PARTIAL,  # observe layer7
        },
        "timeout_config": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.FULL,
            "haproxy": FeatureSupport.FULL,
        },
        "retry_policy": {
            "envoy": FeatureSupport.FULL,
            "kong": FeatureSupport.FULL,
            "apisix": FeatureSupport.FULL,
            "traefik": FeatureSupport.FULL,
            "nginx": FeatureSupport.PARTIAL,  # Via Lua
            "haproxy": FeatureSupport.FULL,
        },
    }

    def check_provider(self, config: Config, target_provider: str) -> CompatibilityReport:
        """Check if config is compatible with target provider.

        Args:
            config: GAL configuration to check
            target_provider: Target provider name (envoy, kong, apisix, traefik, nginx, haproxy)

        Returns:
            CompatibilityReport with detailed compatibility information
        """
        provider_name = target_provider.lower()

        # Validate provider exists in feature matrix
        valid_providers = ["envoy", "kong", "apisix", "traefik", "nginx", "haproxy"]
        if provider_name not in valid_providers:
            return CompatibilityReport(
                provider=provider_name,
                compatible=False,
                compatibility_score=0.0,
                features_checked=0,
                warnings=[
                    f"Unknown provider: {provider_name}. Valid providers: {', '.join(valid_providers)}"
                ],
            )

        features_supported = []
        features_partial = []
        features_unsupported = []
        warnings = []
        recommendations = []

        # Check features used in config
        features_used = self._extract_features_from_config(config)

        for feature_name in features_used:
            support = self._get_feature_support(feature_name, provider_name)
            check = FeatureCheck(
                feature_name=feature_name,
                support=support,
            )

            if support == FeatureSupport.FULL:
                check.message = f"✅ {self._get_feature_display_name(feature_name)} fully supported"
                features_supported.append(check)
            elif support == FeatureSupport.PARTIAL:
                check.message = (
                    f"⚠️ {self._get_feature_display_name(feature_name)} partially supported"
                )
                check.recommendation = self._get_feature_recommendation(feature_name, provider_name)
                features_partial.append(check)
                warnings.append(check.message)
                if check.recommendation:
                    recommendations.append(check.recommendation)
            else:  # UNSUPPORTED
                check.message = f"❌ {self._get_feature_display_name(feature_name)} not supported"
                check.recommendation = self._get_feature_recommendation(feature_name, provider_name)
                features_unsupported.append(check)
                warnings.append(check.message)
                if check.recommendation:
                    recommendations.append(check.recommendation)

        # Calculate compatibility score
        total = len(features_used)
        if total == 0:
            compatibility_score = 1.0
        else:
            # Full support = 1.0, partial = 0.5, unsupported = 0.0
            score = (
                len(features_supported) * 1.0
                + len(features_partial) * 0.5
                + len(features_unsupported) * 0.0
            ) / total
            compatibility_score = score

        # Consider compatible if score >= 0.8 (80%)
        compatible = compatibility_score >= 0.8

        return CompatibilityReport(
            provider=provider_name,
            compatible=compatible,
            compatibility_score=compatibility_score,
            features_checked=total,
            features_supported=features_supported,
            features_partial=features_partial,
            features_unsupported=features_unsupported,
            warnings=warnings,
            recommendations=recommendations,
        )

    def compare_providers(self, config: Config, providers: List[str]) -> List[CompatibilityReport]:
        """Compare config compatibility across multiple providers.

        Args:
            config: GAL configuration to check
            providers: List of provider names to compare

        Returns:
            List of CompatibilityReport objects for each provider
        """
        results = []
        for provider_name in providers:
            results.append(self.check_provider(config, provider_name))
        return results

    def _extract_features_from_config(self, config: Config) -> List[str]:
        """Extract list of features used in config."""
        features = set()

        for service in config.services:
            # Routing features
            for route in service.routes:
                features.add("routing_path_prefix")
                if route.methods:
                    features.add("http_methods")

                # Rate limiting
                if route.rate_limit:
                    rl = route.rate_limit
                    enabled = (
                        rl.get("enabled") if isinstance(rl, dict) else getattr(rl, "enabled", False)
                    )
                    if enabled:
                        features.add("rate_limiting")

                # Authentication
                if route.authentication:
                    auth = route.authentication
                    enabled = (
                        auth.get("enabled")
                        if isinstance(auth, dict)
                        else getattr(auth, "enabled", False)
                    )
                    if enabled:
                        auth_type = (
                            auth.get("type")
                            if isinstance(auth, dict)
                            else getattr(auth, "type", None)
                        )
                        if auth_type == "basic":
                            features.add("authentication_basic")
                        elif auth_type == "api_key":
                            features.add("authentication_api_key")
                        elif auth_type == "jwt":
                            features.add("authentication_jwt")

                # CORS
                if route.cors:
                    cors = route.cors
                    enabled = (
                        cors.get("enabled")
                        if isinstance(cors, dict)
                        else getattr(cors, "enabled", False)
                    )
                    if enabled:
                        features.add("cors")

                # Circuit breaker
                if route.circuit_breaker:
                    cb = route.circuit_breaker
                    enabled = (
                        cb.get("enabled") if isinstance(cb, dict) else getattr(cb, "enabled", False)
                    )
                    if enabled:
                        features.add("circuit_breaker")

                # Timeouts
                if route.timeout:
                    features.add("timeout_config")

                # Retry
                if route.retry:
                    features.add("retry_policy")

            # Upstream features
            if service.upstream:
                upstream = service.upstream

                # Load balancing
                if upstream.load_balancer:
                    lb = upstream.load_balancer
                    # Handle both dict and object forms
                    algorithm = (
                        lb.get("algorithm")
                        if isinstance(lb, dict)
                        else getattr(lb, "algorithm", None)
                    )
                    if algorithm == "round_robin":
                        features.add("load_balancing_round_robin")
                    elif algorithm == "least_conn":
                        features.add("load_balancing_least_conn")
                    elif algorithm == "ip_hash":
                        features.add("load_balancing_ip_hash")

                    # Sticky sessions
                    sticky = (
                        lb.get("sticky_sessions")
                        if isinstance(lb, dict)
                        else getattr(lb, "sticky_sessions", False)
                    )
                    if sticky:
                        features.add("sticky_sessions")

                # Health checks
                if upstream.health_check:
                    hc = upstream.health_check
                    # Handle both dict and object forms
                    if isinstance(hc, dict):
                        if hc.get("active") and hc["active"].get("enabled"):
                            features.add("health_check_active")
                        if hc.get("passive") and hc["passive"].get("enabled"):
                            features.add("health_check_passive")
                    else:
                        if hasattr(hc, "active") and hc.active and hc.active.enabled:
                            features.add("health_check_active")
                        if hasattr(hc, "passive") and hc.passive and hc.passive.enabled:
                            features.add("health_check_passive")

            # Headers
            if service.transformation and service.transformation.headers:
                headers = service.transformation.headers
                if headers.request_add or headers.request_set or headers.request_remove:
                    features.add("headers_request")
                if headers.response_add or headers.response_set or headers.response_remove:
                    features.add("headers_response")

        return sorted(list(features))

    def _get_feature_support(self, feature_name: str, provider: str) -> FeatureSupport:
        """Get support level for a feature on a provider."""
        if feature_name not in self.FEATURE_MATRIX:
            return FeatureSupport.UNSUPPORTED

        provider_support = self.FEATURE_MATRIX[feature_name]
        return provider_support.get(provider, FeatureSupport.UNSUPPORTED)

    def _get_feature_display_name(self, feature_name: str) -> str:
        """Get human-readable feature name."""
        display_names = {
            "routing_path_prefix": "Path-based Routing",
            "http_methods": "HTTP Methods",
            "load_balancing_round_robin": "Load Balancing (Round Robin)",
            "load_balancing_least_conn": "Load Balancing (Least Connections)",
            "load_balancing_ip_hash": "Load Balancing (IP Hash)",
            "health_check_active": "Active Health Checks",
            "health_check_passive": "Passive Health Checks",
            "rate_limiting": "Rate Limiting",
            "authentication_basic": "Basic Authentication",
            "authentication_api_key": "API Key Authentication",
            "authentication_jwt": "JWT Authentication",
            "headers_request": "Request Header Manipulation",
            "headers_response": "Response Header Manipulation",
            "cors": "CORS",
            "sticky_sessions": "Sticky Sessions",
            "circuit_breaker": "Circuit Breaker",
            "timeout_config": "Timeout Configuration",
            "retry_policy": "Retry Policy",
        }
        return display_names.get(feature_name, feature_name)

    def _get_feature_recommendation(self, feature_name: str, provider: str) -> str:
        """Get recommendation for unsupported/partial features."""
        recommendations = {
            (
                "health_check_active",
                "traefik",
            ): "Traefik OSS only supports passive health checks. Consider Traefik Enterprise or use passive checks.",
            (
                "health_check_active",
                "nginx",
            ): "Nginx OSS only supports passive health checks (max_fails/fail_timeout). Consider Nginx Plus or use passive checks.",
            (
                "rate_limiting",
                "envoy",
            ): "Envoy OSS rate limiting is global. For per-route limits, use external rate limit service.",
            (
                "authentication_basic",
                "envoy",
            ): "Basic auth requires Lua filter. Consider using external auth service (ext_authz).",
            (
                "authentication_api_key",
                "envoy",
            ): "API key auth requires Lua filter. Consider using external auth service (ext_authz).",
            (
                "authentication_api_key",
                "traefik",
            ): "API key auth requires forwardAuth middleware with external validator.",
            (
                "authentication_api_key",
                "nginx",
            ): "API key auth requires OpenResty with Lua scripting.",
            (
                "authentication_jwt",
                "traefik",
            ): "JWT auth requires forwardAuth middleware with external JWT validator.",
            (
                "authentication_jwt",
                "nginx",
            ): "JWT auth requires OpenResty with lua-resty-jwt library.",
            (
                "authentication_jwt",
                "haproxy",
            ): "JWT auth requires Lua scripting or external auth service.",
            (
                "circuit_breaker",
                "kong",
            ): "Circuit breaker requires third-party plugin (kong-circuit-breaker).",
            (
                "circuit_breaker",
                "nginx",
            ): "Circuit breaker not natively supported. Consider custom Lua implementation.",
            (
                "circuit_breaker",
                "haproxy",
            ): "Circuit breaker has limited support via 'observe layer7'. Consider using Envoy or APISIX.",
            (
                "retry_policy",
                "nginx",
            ): "Retry policy requires custom Lua implementation (OpenResty).",
            (
                "load_balancing_ip_hash",
                "traefik",
            ): "IP hash via sticky sessions with cookie. May not be true consistent hashing.",
        }
        return recommendations.get((feature_name, provider), "")
