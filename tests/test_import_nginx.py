"""
Tests for Nginx Config Import (v1.3.0 Feature 5)
"""

import pytest

from gal.providers.nginx import NginxProvider


class TestNginxImportBasic:
    """Test basic Nginx config import."""

    def test_import_simple_upstream(self):
        """Test importing a simple Nginx upstream."""
        provider = NginxProvider()

        nginx_conf = """
events {
    worker_connections 1024;
}

http {
    upstream upstream_api {
        server api.internal:8080;
    }

    server {
        listen 80;

        location /api {
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        assert len(config.services) == 1
        assert config.services[0].name == "api"
        assert len(config.services[0].upstream.targets) == 1
        assert config.services[0].upstream.targets[0].host == "api.internal"
        assert config.services[0].upstream.targets[0].port == 8080

    def test_import_multiple_servers(self):
        """Test importing upstream with multiple servers."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_lb {
        server server1:8080 weight=2;
        server server2:8080 weight=1;
        server server3:9000;
    }

    server {
        location /api {
            proxy_pass http://upstream_lb;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        assert len(config.services[0].upstream.targets) == 3
        assert config.services[0].upstream.targets[0].weight == 2
        assert config.services[0].upstream.targets[1].weight == 1
        assert config.services[0].upstream.targets[2].weight == 1

    def test_import_with_comments(self):
        """Test that comments are properly removed."""
        provider = NginxProvider()

        nginx_conf = """
# Main configuration file
events {}

http {
    # API upstream
    upstream upstream_api {
        server api:8080;  # Primary server
    }

    server {
        location /api {  # API endpoint
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        assert len(config.services) == 1
        assert config.services[0].name == "api"


class TestNginxImportLoadBalancing:
    """Test load balancing algorithm import."""

    def test_import_round_robin(self):
        """Test round robin (default) algorithm."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        server server1:8080;
        server server2:8080;
    }

    server {
        location /api {
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        assert config.services[0].upstream.load_balancer.algorithm == "round_robin"

    def test_import_least_conn(self):
        """Test least_conn algorithm."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        least_conn;
        server server1:8080;
        server server2:8080;
    }

    server {
        location /api {
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        assert config.services[0].upstream.load_balancer.algorithm == "least_conn"

    def test_import_ip_hash(self):
        """Test ip_hash algorithm."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        ip_hash;
        server server1:8080;
        server server2:8080;
    }

    server {
        location /api {
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        assert config.services[0].upstream.load_balancer.algorithm == "ip_hash"


class TestNginxImportHealthChecks:
    """Test health check import."""

    def test_import_passive_health_check(self):
        """Test passive health check parameters."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        server server1:8080 max_fails=3 fail_timeout=30s;
    }

    server {
        location /api {
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        hc = config.services[0].upstream.health_check
        assert hc is not None
        assert hc.passive.enabled is True
        assert hc.passive.max_failures == 3


class TestNginxImportRateLimiting:
    """Test rate limiting import."""

    def test_import_rate_limiting_per_second(self):
        """Test rate limiting with r/s."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    limit_req_zone $binary_remote_addr zone=api_rate:10m rate=100r/s;

    upstream upstream_api {
        server api:8080;
    }

    server {
        location /api {
            limit_req zone=api_rate burst=200;
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        route = config.services[0].routes[0]
        assert route.rate_limit is not None
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 100
        assert route.rate_limit.burst == 200

    def test_import_rate_limiting_per_minute(self):
        """Test rate limiting with r/m."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    limit_req_zone $binary_remote_addr zone=api_rate:10m rate=600r/m;

    upstream upstream_api {
        server api:8080;
    }

    server {
        location /api {
            limit_req zone=api_rate;
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        route = config.services[0].routes[0]
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 10  # 600 / 60


class TestNginxImportAuthentication:
    """Test authentication import."""

    def test_import_basic_auth(self):
        """Test basic auth import."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        server api:8080;
    }

    server {
        location /api {
            auth_basic "Protected Area";
            auth_basic_user_file /etc/nginx/.htpasswd;
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        route = config.services[0].routes[0]
        assert route.authentication is not None
        assert route.authentication.enabled is True
        assert route.authentication.type == "basic"

        # Check warnings
        warnings = provider.get_import_warnings()
        assert any("htpasswd" in w for w in warnings)


class TestNginxImportHeaders:
    """Test header import."""

    def test_import_request_headers(self):
        """Test request header import."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        server api:8080;
    }

    server {
        location /api {
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        route = config.services[0].routes[0]
        assert route.headers is not None
        assert route.headers.request_add is not None
        assert "X-Real-IP" in route.headers.request_add
        assert "X-Forwarded-For" in route.headers.request_add

    def test_import_response_headers(self):
        """Test response header import."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        server api:8080;
    }

    server {
        location /api {
            add_header X-Frame-Options "DENY";
            add_header X-Content-Type-Options "nosniff";
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        route = config.services[0].routes[0]
        assert route.headers is not None
        assert route.headers.response_add is not None
        assert route.headers.response_add["X-Frame-Options"] == "DENY"
        assert route.headers.response_add["X-Content-Type-Options"] == "nosniff"


class TestNginxImportCORS:
    """Test CORS import."""

    def test_import_cors_from_headers(self):
        """Test CORS extraction from add_header directives."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        server api:8080;
    }

    server {
        location /api {
            add_header Access-Control-Allow-Origin "https://app.example.com";
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE";
            add_header Access-Control-Allow-Headers "Content-Type, Authorization";
            add_header Access-Control-Allow-Credentials "true";
            add_header Access-Control-Max-Age "3600";
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        route = config.services[0].routes[0]
        assert route.cors is not None
        assert route.cors.enabled is True
        assert route.cors.allowed_origins == ["https://app.example.com"]
        assert route.cors.allowed_methods == ["GET", "POST", "PUT", "DELETE"]
        assert route.cors.allowed_headers == ["Content-Type", "Authorization"]
        assert route.cors.allow_credentials is True
        assert route.cors.max_age == "3600"

        # CORS headers should be removed from response_add
        assert route.headers.response_add == {} or route.headers.response_add is None

    def test_import_cors_wildcard_origin(self):
        """Test CORS with wildcard origin."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        server api:8080;
    }

    server {
        location /api {
            add_header Access-Control-Allow-Origin "*";
            add_header Access-Control-Allow-Methods "GET, POST";
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        route = config.services[0].routes[0]
        assert route.cors.allowed_origins == ["*"]


class TestNginxImportMultipleLocations:
    """Test multiple location blocks."""

    def test_import_multiple_locations(self):
        """Test importing multiple location blocks."""
        provider = NginxProvider()

        nginx_conf = """
events {}

http {
    upstream upstream_api {
        server api:8080;
    }

    server {
        location /users {
            proxy_pass http://upstream_api;
        }

        location /orders {
            proxy_pass http://upstream_api;
        }

        location /payments {
            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        assert len(config.services) == 1
        assert len(config.services[0].routes) == 3
        assert config.services[0].routes[0].path_prefix == "/users"
        assert config.services[0].routes[1].path_prefix == "/orders"
        assert config.services[0].routes[2].path_prefix == "/payments"


class TestNginxImportErrors:
    """Test error handling."""

    def test_import_empty_config(self):
        """Test importing empty config."""
        provider = NginxProvider()

        nginx_conf = ""

        with pytest.raises(ValueError, match="Empty configuration"):
            provider.parse(nginx_conf)

    def test_import_no_http_block(self):
        """Test importing config without http block."""
        provider = NginxProvider()

        nginx_conf = """
events {
    worker_connections 1024;
}
"""

        with pytest.raises(ValueError, match="No http block"):
            provider.parse(nginx_conf)


class TestNginxImportCombined:
    """Test combined features."""

    def test_import_production_config(self):
        """Test importing a production-like config with all features."""
        provider = NginxProvider()

        nginx_conf = """
events {
    worker_connections 1024;
}

http {
    limit_req_zone $binary_remote_addr zone=api_rate:10m rate=100r/s;

    upstream upstream_api {
        least_conn;
        server api-1:8080 weight=2 max_fails=3 fail_timeout=30s;
        server api-2:8080 weight=1;
    }

    server {
        listen 80;
        server_name api.example.com;

        location /api/v1 {
            limit_req zone=api_rate burst=200;

            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            add_header X-Frame-Options "DENY";
            add_header Access-Control-Allow-Origin "https://app.example.com";
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE";
            add_header Access-Control-Allow-Credentials "true";

            proxy_pass http://upstream_api;
        }
    }
}
"""

        config = provider.parse(nginx_conf)

        # Service and upstream
        assert len(config.services) == 1
        service = config.services[0]
        assert service.name == "api"
        assert len(service.upstream.targets) == 2
        assert service.upstream.load_balancer.algorithm == "least_conn"
        assert service.upstream.targets[0].weight == 2

        # Health checks
        assert service.upstream.health_check is not None
        assert service.upstream.health_check.passive.enabled is True
        assert service.upstream.health_check.passive.max_failures == 3

        # Route
        assert len(service.routes) == 1
        route = service.routes[0]
        assert route.path_prefix == "/api/v1"

        # Rate limiting
        assert route.rate_limit is not None
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 100
        assert route.rate_limit.burst == 200

        # Headers
        assert route.headers is not None
        assert "X-Real-IP" in route.headers.request_add
        assert route.headers.response_add["X-Frame-Options"] == "DENY"

        # CORS
        assert route.cors is not None
        assert route.cors.enabled is True
        assert route.cors.allowed_origins == ["https://app.example.com"]
        assert route.cors.allow_credentials is True
