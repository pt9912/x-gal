"""
Tests for HAProxy Config Import (v1.3.0 Feature 6)

Comprehensive test suite for HAProxy haproxy.cfg parsing and import.
Tests cover frontends, backends, listen sections, ACLs, load balancing,
health checks, sticky sessions, and header manipulation.
"""

import pytest

from gal.parsers.haproxy_parser import HAProxyConfigParser, SectionType
from gal.providers.haproxy import HAProxyProvider


class TestHAProxyParserBasic:
    """Test basic HAProxy config parser functionality."""

    def test_parse_empty_config(self):
        """Test that empty config raises ValueError."""
        parser = HAProxyConfigParser()

        with pytest.raises(ValueError, match="Empty configuration"):
            parser.parse("")

    def test_parse_global_section(self):
        """Test parsing global section."""
        parser = HAProxyConfigParser()

        haproxy_cfg = """
global
    daemon
    maxconn 256
"""

        sections = parser.parse(haproxy_cfg)

        assert len(sections) == 1
        assert sections[0].type == SectionType.GLOBAL
        assert sections[0].name is None
        assert len(sections[0].directives) == 2

    def test_parse_defaults_section(self):
        """Test parsing defaults section."""
        parser = HAProxyConfigParser()

        haproxy_cfg = """
defaults
    mode http
    timeout client 30s
    timeout server 30s
"""

        sections = parser.parse(haproxy_cfg)

        assert len(sections) == 1
        assert sections[0].type == SectionType.DEFAULTS
        assert len(sections[0].directives) == 3

    def test_parse_frontend_section(self):
        """Test parsing frontend section."""
        parser = HAProxyConfigParser()

        haproxy_cfg = """
frontend http_front
    bind *:80
    default_backend servers
"""

        sections = parser.parse(haproxy_cfg)

        assert len(sections) == 1
        assert sections[0].type == SectionType.FRONTEND
        assert sections[0].name == "http_front"
        assert len(sections[0].directives) == 2

    def test_parse_backend_section(self):
        """Test parsing backend section."""
        parser = HAProxyConfigParser()

        haproxy_cfg = """
backend servers
    balance roundrobin
    server srv1 192.168.1.1:8080 check
    server srv2 192.168.1.2:8080 check
"""

        sections = parser.parse(haproxy_cfg)

        assert len(sections) == 1
        assert sections[0].type == SectionType.BACKEND
        assert sections[0].name == "servers"
        assert len(sections[0].directives) == 3

    def test_parse_listen_section(self):
        """Test parsing listen section."""
        parser = HAProxyConfigParser()

        haproxy_cfg = """
listen stats
    bind *:8080
    stats enable
    stats uri /stats
"""

        sections = parser.parse(haproxy_cfg)

        assert len(sections) == 1
        assert sections[0].type == SectionType.LISTEN
        assert sections[0].name == "stats"

    def test_parse_multiple_sections(self):
        """Test parsing config with multiple sections."""
        parser = HAProxyConfigParser()

        haproxy_cfg = """
global
    daemon

defaults
    mode http

frontend http_front
    bind *:80

backend servers
    server srv1 192.168.1.1:8080
"""

        sections = parser.parse(haproxy_cfg)

        assert len(sections) == 4
        assert sections[0].type == SectionType.GLOBAL
        assert sections[1].type == SectionType.DEFAULTS
        assert sections[2].type == SectionType.FRONTEND
        assert sections[3].type == SectionType.BACKEND

    def test_parse_with_comments(self):
        """Test that comments are properly removed."""
        parser = HAProxyConfigParser()

        haproxy_cfg = """
# Main config
global
    daemon  # Run as daemon

# Backend servers
backend servers
    server srv1 192.168.1.1:8080  # Primary server
"""

        sections = parser.parse(haproxy_cfg)

        # Comments should be removed
        assert len(sections) == 2


class TestHAProxyImportBasic:
    """Test basic HAProxy config import to GAL."""

    def test_import_simple_backend(self):
        """Test importing a simple HAProxy backend."""
        provider = HAProxyProvider()

        haproxy_cfg = """
frontend http_front
    bind *:80
    default_backend app_backend

backend app_backend
    balance roundrobin
    server srv1 app.internal:8080
"""

        config = provider.parse(haproxy_cfg)

        assert len(config.services) == 1
        assert config.services[0].name == "app_backend"
        assert len(config.services[0].upstream.targets) == 1
        assert config.services[0].upstream.targets[0].host == "app.internal"
        assert config.services[0].upstream.targets[0].port == 8080

    def test_import_multiple_servers(self):
        """Test importing backend with multiple servers."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app_backend
    balance roundrobin
    server srv1 server1:8080 weight 2
    server srv2 server2:8080 weight 1
    server srv3 server3:9000
"""

        config = provider.parse(haproxy_cfg)

        assert len(config.services[0].upstream.targets) == 3
        assert config.services[0].upstream.targets[0].host == "server1"
        assert config.services[0].upstream.targets[0].port == 8080
        assert config.services[0].upstream.targets[0].weight == 2
        assert config.services[0].upstream.targets[1].weight == 1
        assert config.services[0].upstream.targets[2].weight == 1

    def test_import_multiple_backends(self):
        """Test importing multiple backends."""
        provider = HAProxyProvider()

        haproxy_cfg = """
frontend http_front
    bind *:80
    use_backend api_backend if { path_beg /api }
    use_backend web_backend if { path_beg /web }
    default_backend app_backend

backend api_backend
    server api1 api.internal:8080

backend web_backend
    server web1 web.internal:8080

backend app_backend
    server app1 app.internal:8080
"""

        config = provider.parse(haproxy_cfg)

        assert len(config.services) == 3
        service_names = {s.name for s in config.services}
        assert "api_backend" in service_names
        assert "web_backend" in service_names
        assert "app_backend" in service_names

    def test_import_listen_section(self):
        """Test importing listen section (combined frontend+backend)."""
        provider = HAProxyProvider()

        haproxy_cfg = """
listen web_app
    bind *:8080
    balance roundrobin
    server srv1 192.168.1.1:8080
    server srv2 192.168.1.2:8080
"""

        config = provider.parse(haproxy_cfg)

        assert len(config.services) == 1
        assert config.services[0].name == "web_app"
        assert len(config.services[0].upstream.targets) == 2

    def test_import_global_config(self):
        """Test extracting global config from defaults/frontend."""
        provider = HAProxyProvider()

        haproxy_cfg = """
defaults
    timeout client 50s
    timeout server 50s

frontend http_front
    bind 0.0.0.0:8080
    default_backend app

backend app
    server srv1 app:8080
"""

        config = provider.parse(haproxy_cfg)

        assert config.global_config.host == "0.0.0.0"
        assert config.global_config.port == 8080
        assert config.global_config.timeout == "50s"


class TestHAProxyImportLoadBalancing:
    """Test load balancing algorithm import."""

    def test_import_roundrobin(self):
        """Test importing roundrobin algorithm."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    balance roundrobin
    server srv1 app:8080
"""

        config = provider.parse(haproxy_cfg)

        assert config.services[0].upstream.load_balancer.algorithm == "round_robin"

    def test_import_leastconn(self):
        """Test importing leastconn algorithm."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    balance leastconn
    server srv1 app:8080
"""

        config = provider.parse(haproxy_cfg)

        assert config.services[0].upstream.load_balancer.algorithm == "least_connections"

    def test_import_source(self):
        """Test importing source (IP hash) algorithm."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    balance source
    server srv1 app:8080
"""

        config = provider.parse(haproxy_cfg)

        assert config.services[0].upstream.load_balancer.algorithm == "ip_hash"

    def test_import_uri(self):
        """Test importing URI hash algorithm."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    balance uri
    server srv1 app:8080
"""

        config = provider.parse(haproxy_cfg)

        assert config.services[0].upstream.load_balancer.algorithm == "uri_hash"


class TestHAProxyImportHealthChecks:
    """Test health check configuration import."""

    def test_import_httpchk_simple(self):
        """Test importing simple HTTP health check."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    option httpchk
    server srv1 app:8080 check
"""

        config = provider.parse(haproxy_cfg)

        assert config.services[0].upstream.health_check is not None
        assert config.services[0].upstream.health_check.active is not None
        assert config.services[0].upstream.health_check.active.http_path == "/"

    def test_import_httpchk_with_path(self):
        """Test importing HTTP health check with custom path."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    option httpchk GET /health HTTP/1.1
    server srv1 app:8080 check
"""

        config = provider.parse(haproxy_cfg)

        assert config.services[0].upstream.health_check.active.http_path == "/health"

    def test_import_http_check_v2(self):
        """Test importing HAProxy 2.0+ http-check syntax."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    http-check send meth GET uri /status
    server srv1 app:8080 check
"""

        config = provider.parse(haproxy_cfg)

        assert config.services[0].upstream.health_check is not None


class TestHAProxyImportStickySessions:
    """Test sticky session configuration import."""

    def test_import_cookie_sticky(self):
        """Test importing cookie-based sticky sessions."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    cookie SERVERID insert indirect nocache
    server srv1 app1:8080 check cookie srv1
    server srv2 app2:8080 check cookie srv2
"""

        config = provider.parse(haproxy_cfg)

        assert config.services[0].upstream.load_balancer.sticky_sessions is True
        assert config.services[0].upstream.load_balancer.cookie_name == "SERVERID"


class TestHAProxyImportHeaders:
    """Test header manipulation import."""

    def test_import_set_header(self):
        """Test importing http-request set-header."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    http-request set-header X-Forwarded-For %[src]
    http-request set-header X-Custom-Header "CustomValue"
    server srv1 app:8080
"""

        config = provider.parse(haproxy_cfg)

        assert config.services[0].transformation is not None
        assert config.services[0].transformation.headers is not None
        assert "X-Forwarded-For" in config.services[0].transformation.headers.request_add
        assert "X-Custom-Header" in config.services[0].transformation.headers.request_add


class TestHAProxyImportRouting:
    """Test routing and ACL import."""

    def test_import_path_based_routing(self):
        """Test importing path-based routing with ACLs."""
        provider = HAProxyProvider()

        haproxy_cfg = """
frontend http_front
    bind *:80
    use_backend api_backend if { path_beg /api }
    use_backend web_backend if { path_beg /web }
    default_backend app_backend

backend api_backend
    server api1 api:8080

backend web_backend
    server web1 web:8080

backend app_backend
    server app1 app:8080
"""

        config = provider.parse(haproxy_cfg)

        # Find api_backend service
        api_service = next(s for s in config.services if s.name == "api_backend")
        assert len(api_service.routes) >= 1
        # Check if any route has /api prefix
        api_routes = [r for r in api_service.routes if r.path_prefix == "/api"]
        assert len(api_routes) > 0

    def test_import_default_backend(self):
        """Test importing default_backend directive."""
        provider = HAProxyProvider()

        haproxy_cfg = """
frontend http_front
    bind *:80
    default_backend app_backend

backend app_backend
    server app1 app:8080
"""

        config = provider.parse(haproxy_cfg)

        assert len(config.services[0].routes) >= 1
        assert config.services[0].routes[0].path_prefix == "/"


class TestHAProxyImportEdgeCases:
    """Test edge cases and error handling."""

    def test_import_backend_without_servers(self):
        """Test importing backend without server directives."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend empty_backend
    balance roundrobin
"""

        config = provider.parse(haproxy_cfg)

        assert len(config.services) == 1
        assert len(config.services[0].upstream.targets) == 0

    def test_import_unnamed_section(self):
        """Test importing section without name."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend
    server srv1 app:8080
"""

        config = provider.parse(haproxy_cfg)

        # Should handle gracefully
        assert len(config.services) == 1

    def test_import_with_invalid_server(self):
        """Test importing with malformed server directive."""
        provider = HAProxyProvider()

        haproxy_cfg = """
backend app
    server srv1 invalid_address
    server srv2 app:8080
"""

        config = provider.parse(haproxy_cfg)

        # Should skip invalid server and parse valid one
        assert len(config.services[0].upstream.targets) == 1
        assert config.services[0].upstream.targets[0].host == "app"


class TestHAProxyImportComplex:
    """Test complex real-world HAProxy configurations."""

    def test_import_production_like_config(self):
        """Test importing production-like HAProxy config."""
        provider = HAProxyProvider()

        haproxy_cfg = """
global
    daemon
    maxconn 256

defaults
    mode http
    timeout client 30s
    timeout server 30s
    timeout connect 10s

frontend http_front
    bind *:80
    use_backend api_backend if { path_beg /api }
    use_backend static_backend if { path_beg /static }
    default_backend app_backend

backend api_backend
    balance roundrobin
    option httpchk GET /health HTTP/1.1
    http-request set-header X-Backend api
    server api1 api1.internal:8080 check weight 2
    server api2 api2.internal:8080 check weight 1

backend static_backend
    balance leastconn
    server static1 static.internal:8080

backend app_backend
    balance source
    cookie APPID insert indirect
    server app1 app1.internal:8080 check cookie app1
    server app2 app2.internal:8080 check cookie app2
"""

        config = provider.parse(haproxy_cfg)

        # Verify services
        assert len(config.services) == 3

        # Verify api_backend
        api_service = next(s for s in config.services if s.name == "api_backend")
        assert api_service.upstream.load_balancer.algorithm == "round_robin"
        assert len(api_service.upstream.targets) == 2
        assert api_service.upstream.health_check is not None
        assert api_service.transformation is not None
        assert api_service.transformation.headers is not None

        # Verify app_backend sticky sessions
        app_service = next(s for s in config.services if s.name == "app_backend")
        assert app_service.upstream.load_balancer.sticky_sessions is True
        assert app_service.upstream.load_balancer.cookie_name == "APPID"
