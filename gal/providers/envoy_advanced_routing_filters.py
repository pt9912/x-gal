"""
Envoy Advanced Routing Filter Generators

This module contains helper functions for generating Envoy HTTP filters
for JWT authentication and GeoIP-based routing in advanced routing scenarios.
"""

from typing import List
from ..config import JWTFilterConfig, GeoIPFilterConfig, JWTClaimMatchRule, GeoMatchRule


def generate_jwt_authn_filter(jwt_config: JWTFilterConfig, output: List[str]) -> None:
    """Generate Envoy JWT Authentication filter configuration.

    Args:
        jwt_config: JWT filter configuration
        output: Output list to append YAML lines to
    """
    output.append("          - name: envoy.filters.http.jwt_authn")
    output.append("            typed_config:")
    output.append(
        "              '@type': type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication"
    )
    output.append("              providers:")
    output.append("                jwt_provider:")

    if jwt_config.issuer:
        output.append(f"                  issuer: '{jwt_config.issuer}'")

    if jwt_config.audience:
        output.append("                  audiences:")
        output.append(f"                    - '{jwt_config.audience}'")

    if jwt_config.jwks_uri:
        output.append("                  remote_jwks:")
        output.append("                    http_uri:")
        output.append(f"                      uri: '{jwt_config.jwks_uri}'")
        output.append(f"                      cluster: {jwt_config.jwks_cluster}")
        output.append("                      timeout: 5s")
        output.append("                    cache_duration:")
        output.append("                      seconds: 300")

    # Store JWT payload in metadata for routing decisions
    output.append(f"                  payload_in_metadata: '{jwt_config.payload_in_metadata}'")

    if jwt_config.forward_payload_header:
        output.append(f"                  forward_payload_header: '{jwt_config.forward_payload_header}'")

    # Rules: JWT is optional for all routes (but required for JWT claim-based routing)
    output.append("              rules:")
    output.append("              - match:")
    output.append("                  prefix: '/'")
    output.append("                requires:")
    output.append("                  allow_missing_or_failed: {}")


def generate_geoip_ext_authz_filter(geoip_config: GeoIPFilterConfig, output: List[str]) -> None:
    """Generate Envoy External Authorization filter for GeoIP lookup.

    Args:
        geoip_config: GeoIP filter configuration
        output: Output list to append YAML lines to
    """
    output.append("          - name: envoy.filters.http.ext_authz")
    output.append("            typed_config:")
    output.append(
        "              '@type': type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz"
    )
    output.append("              transport_api_version: V3")

    # Use HTTP service for GeoIP lookup
    output.append("              http_service:")
    output.append("                server_uri:")
    output.append(f"                  uri: '{geoip_config.geoip_service_uri}'")
    output.append(f"                  cluster: {geoip_config.geoip_cluster}")
    output.append(f"                  timeout: {geoip_config.timeout_ms / 1000:.1f}s")

    # Forward headers for IP extraction
    output.append("                authorization_request:")
    output.append("                  allowed_headers:")
    output.append("                    patterns:")
    output.append("                      - exact: 'x-forwarded-for'")
    output.append("                      - exact: 'x-real-ip'")

    # Allow GeoIP metadata in response
    output.append("                authorization_response:")
    output.append("                  allowed_upstream_headers:")
    output.append("                    patterns:")
    output.append("                      - exact: 'x-geo-country'")
    output.append("                      - exact: 'x-geo-region'")

    # Failure mode
    if geoip_config.failure_mode_allow:
        output.append("              failure_mode_allow: true")

    # Store GeoIP metadata for routing
    output.append("              metadata_context_namespaces:")
    output.append("                - envoy.filters.http.ext_authz")


def generate_lua_filter_for_advanced_routing(
    jwt_rules: List[JWTClaimMatchRule],
    geo_rules: List[GeoMatchRule],
    jwt_config: JWTFilterConfig,
    output: List[str]
) -> None:
    """Generate Lua filter for JWT claim and GeoIP metadata processing.

    This filter extracts JWT claims and GeoIP metadata and adds them as headers
    for debugging and downstream services.

    Args:
        jwt_rules: JWT claim-based routing rules
        geo_rules: Geographic routing rules
        jwt_config: JWT filter configuration
        output: Output list to append YAML lines to
    """
    output.append("          - name: envoy.filters.http.lua")
    output.append("            typed_config:")
    output.append(
        "              '@type': type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua"
    )
    output.append("              default_source_code:")
    output.append("                inline_string: |")
    output.append("                  function envoy_on_request(request_handle)")

    # JWT Claim Extraction
    if jwt_rules:
        output.append("                    -- Extract JWT payload metadata")
        output.append("                    local metadata = request_handle:metadata()")
        output.append("                    if metadata ~= nil then")
        output.append(f"                      local jwt_payload = metadata:get('{jwt_config.payload_in_metadata}')")
        output.append("                      if jwt_payload ~= nil then")

        # Extract specific claims mentioned in rules
        claim_names = {rule.claim_name for rule in jwt_rules}
        for claim_name in claim_names:
            output.append(f"                        -- Extract '{claim_name}' claim")
            output.append(f"                        if jwt_payload['{claim_name}'] ~= nil then")
            output.append(f"                          request_handle:headers():add('X-JWT-{claim_name.title()}', tostring(jwt_payload['{claim_name}']))")
            output.append("                        end")

        # Common claims
        output.append("                        -- Extract common claims")
        output.append("                        if jwt_payload['sub'] ~= nil then")
        output.append("                          request_handle:headers():add('X-JWT-Subject', jwt_payload['sub'])")
        output.append("                        end")

        output.append("                      end")
        output.append("                    end")

    # GeoIP Metadata Extraction
    if geo_rules:
        output.append("")
        output.append("                    -- Extract GeoIP metadata from ext_authz")
        output.append("                    local geo_metadata = request_handle:metadata():get('envoy.filters.http.ext_authz')")
        output.append("                    if geo_metadata ~= nil then")
        output.append("                      if geo_metadata['country'] ~= nil then")
        output.append("                        request_handle:headers():add('X-Geo-Country', geo_metadata['country'])")
        output.append("                      end")
        output.append("                      if geo_metadata['region'] ~= nil then")
        output.append("                        request_handle:headers():add('X-Geo-Region', geo_metadata['region'])")
        output.append("                      end")
        output.append("                    end")

    # Logging
    output.append("")
    output.append("                    -- Log routing decision")
    output.append("                    local path = request_handle:headers():get(':path')")
    output.append("                    local method = request_handle:headers():get(':method')")
    output.append("                    request_handle:logInfo(string.format('Advanced Routing: %s %s', method, path))")

    output.append("                  end")

    # Response handler (optional - for debugging)
    output.append("")
    output.append("                  function envoy_on_response(response_handle)")
    output.append("                    -- Add routing metadata to response headers for debugging")
    output.append("                    local metadata = response_handle:metadata()")
    output.append("                    if metadata ~= nil and metadata['envoy.lb'] ~= nil then")
    output.append("                      local routing_rule = metadata['envoy.lb']['routing_rule']")
    output.append("                      if routing_rule ~= nil then")
    output.append("                        response_handle:headers():add('X-Routing-Rule', routing_rule)")
    output.append("                      end")
    output.append("                    end")
    output.append("                  end")


def generate_jwks_cluster(jwt_config: JWTFilterConfig, output: List[str]) -> None:
    """Generate Envoy cluster configuration for JWKS fetching.

    Args:
        jwt_config: JWT filter configuration
        output: Output list to append YAML lines to
    """
    if not jwt_config.jwks_uri:
        return

    # Extract host and port from JWKS URI
    # Format: http://host:port/path or https://host:port/path
    import urllib.parse
    parsed = urllib.parse.urlparse(jwt_config.jwks_uri)
    host = parsed.hostname or "jwks-service"
    port = parsed.port or (443 if parsed.scheme == "https" else 8080)

    output.append(f"  - name: {jwt_config.jwks_cluster}")
    output.append("    type: STRICT_DNS")
    output.append("    lb_policy: ROUND_ROBIN")
    output.append("    connect_timeout: 5s")
    output.append("    load_assignment:")
    output.append(f"      cluster_name: {jwt_config.jwks_cluster}")
    output.append("      endpoints:")
    output.append("      - lb_endpoints:")
    output.append("        - endpoint:")
    output.append("            address:")
    output.append("              socket_address:")
    output.append(f"                address: {host}")
    output.append(f"                port_value: {port}")
    output.append(f"    # JWKS service for JWT validation")


def generate_geoip_cluster(geoip_config: GeoIPFilterConfig, output: List[str]) -> None:
    """Generate Envoy cluster configuration for GeoIP service.

    Args:
        geoip_config: GeoIP filter configuration
        output: Output list to append YAML lines to
    """
    if not geoip_config.geoip_service_uri:
        return

    # Extract host and port from GeoIP service URI
    import urllib.parse
    parsed = urllib.parse.urlparse(geoip_config.geoip_service_uri)
    host = parsed.hostname or "geoip-service"
    port = parsed.port or 8080

    output.append(f"  - name: {geoip_config.geoip_cluster}")
    output.append("    type: STRICT_DNS")
    output.append("    lb_policy: ROUND_ROBIN")
    output.append("    connect_timeout: 5s")
    output.append("    load_assignment:")
    output.append(f"      cluster_name: {geoip_config.geoip_cluster}")
    output.append("      endpoints:")
    output.append("      - lb_endpoints:")
    output.append("        - endpoint:")
    output.append("            address:")
    output.append("              socket_address:")
    output.append(f"                address: {host}")
    output.append(f"                port_value: {port}")
    output.append(f"    # GeoIP service for geographic routing")
