"""
Tests for AWS API Gateway import functionality

Tests cover:
- OpenAPI 3.0 parsing with x-amazon-apigateway extensions
- HTTP_PROXY, AWS_PROXY, and MOCK integration imports
- Lambda Authorizer and Cognito User Pool imports
- API Key and CORS configuration imports
- Route and authentication extraction
"""

import json
import pytest

from gal.parsers.aws_apigateway_parser import AWSAPIGatewayParser
from gal.providers.aws_apigateway import AWSAPIGatewayProvider


class TestAWSAPIGatewayParser:
    """Test AWS API Gateway OpenAPI 3.0 parser"""

    def test_parse_basic_openapi(self):
        """Test parsing basic OpenAPI 3.0 spec"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "A test API"
            },
            "paths": {}
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)

        assert api.title == "Test API"
        assert api.version == "1.0.0"
        assert api.description == "A test API"

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises ValueError"""
        parser = AWSAPIGatewayParser()

        with pytest.raises(ValueError, match="Invalid OpenAPI format"):
            parser.parse("invalid json {{{")

    def test_parse_unsupported_openapi_version(self):
        """Test parsing unsupported OpenAPI version raises ValueError"""
        openapi_spec = json.dumps({
            "openapi": "2.0",
            "info": {"title": "Test", "version": "1.0"}
        })

        parser = AWSAPIGatewayParser()

        with pytest.raises(ValueError, match="Unsupported OpenAPI version"):
            parser.parse(openapi_spec)

    def test_extract_backend_url_http_proxy(self):
        """Test extracting backend URL from HTTP_PROXY integration"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/api": {
                    "get": {
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "uri": "https://backend.example.com/api"
                        }
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        backend_url = parser.extract_backend_url(api)

        assert backend_url == "https://backend.example.com"

    def test_extract_backend_url_no_integration(self):
        """Test extracting backend URL when no integration exists"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/api": {
                    "get": {
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        backend_url = parser.extract_backend_url(api)

        assert backend_url is None

    def test_extract_routes(self):
        """Test extracting routes from paths"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/users": {
                    "get": {"responses": {"200": {"description": "OK"}}},
                    "post": {"responses": {"201": {"description": "Created"}}}
                },
                "/users/{id}": {
                    "get": {"responses": {"200": {"description": "OK"}}},
                    "put": {"responses": {"200": {"description": "OK"}}},
                    "delete": {"responses": {"204": {"description": "No Content"}}}
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        routes = parser.extract_routes(api)

        assert len(routes) == 2
        assert routes[0]["path"] == "/users"
        assert set(routes[0]["methods"]) == {"GET", "POST"}
        assert routes[1]["path"] == "/users/{id}"
        assert set(routes[1]["methods"]) == {"GET", "PUT", "DELETE"}

    def test_extract_routes_skips_options(self):
        """Test that OPTIONS methods are skipped (CORS)"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/api": {
                    "get": {"responses": {"200": {"description": "OK"}}},
                    "options": {
                        "responses": {"200": {"description": "CORS"}},
                        "x-amazon-apigateway-integration": {"type": "mock"}
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        routes = parser.extract_routes(api)

        assert len(routes) == 1
        assert routes[0]["methods"] == ["GET"]

    def test_extract_authentication_api_key(self):
        """Test extracting API key authentication"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "components": {
                "securitySchemes": {
                    "api_key": {
                        "type": "apiKey",
                        "name": "x-api-key",
                        "in": "header"
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        auth_type, auth_config = parser.extract_authentication(api)

        assert auth_type == "api_key"
        assert auth_config["header_name"] == "x-api-key"

    def test_extract_authentication_cognito(self):
        """Test extracting Cognito User Pool authentication"""
        cognito_arn = "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_AbCdEfGhI"

        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "components": {
                "securitySchemes": {
                    "cognito_authorizer": {
                        "type": "apiKey",
                        "name": "Authorization",
                        "in": "header",
                        "x-amazon-apigateway-authtype": "cognito_user_pools",
                        "x-amazon-apigateway-authorizer": {
                            "type": "cognito_user_pools",
                            "providerARNs": [cognito_arn]
                        }
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        auth_type, auth_config = parser.extract_authentication(api)

        assert auth_type == "jwt"
        assert auth_config["authorizer_type"] == "cognito"
        assert auth_config["provider_arns"] == [cognito_arn]

    def test_extract_authentication_lambda_authorizer(self):
        """Test extracting Lambda Authorizer authentication"""
        lambda_arn = "arn:aws:lambda:us-east-1:123456789012:function:my-authorizer"
        authorizer_uri = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "components": {
                "securitySchemes": {
                    "lambda_authorizer": {
                        "type": "apiKey",
                        "name": "Authorization",
                        "in": "header",
                        "x-amazon-apigateway-authtype": "custom",
                        "x-amazon-apigateway-authorizer": {
                            "type": "token",
                            "authorizerUri": authorizer_uri,
                            "authorizerResultTtlInSeconds": 300
                        }
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        auth_type, auth_config = parser.extract_authentication(api)

        assert auth_type == "jwt"
        assert auth_config["authorizer_type"] == "lambda"
        assert auth_config["lambda_arn"] == lambda_arn
        assert auth_config["ttl"] == 300

    def test_extract_integration_type_http_proxy(self):
        """Test extracting HTTP_PROXY integration type"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/api": {
                    "get": {
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "uri": "https://backend.example.com/api"
                        }
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        integration_type = parser.extract_integration_type(api)

        assert integration_type == "HTTP_PROXY"

    def test_extract_integration_type_aws_proxy(self):
        """Test extracting AWS_PROXY integration type"""
        lambda_arn = "arn:aws:lambda:us-east-1:123456789012:function:my-function"
        uri = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/api": {
                    "post": {
                        "x-amazon-apigateway-integration": {
                            "type": "aws_proxy",
                            "httpMethod": "POST",
                            "uri": uri
                        }
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        integration_type = parser.extract_integration_type(api)

        assert integration_type == "AWS_PROXY"

    def test_extract_lambda_arn(self):
        """Test extracting Lambda function ARN from AWS_PROXY integration"""
        lambda_arn = "arn:aws:lambda:us-east-1:123456789012:function:my-function"
        uri = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/api": {
                    "post": {
                        "x-amazon-apigateway-integration": {
                            "type": "aws_proxy",
                            "uri": uri
                        }
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        extracted_arn = parser.extract_lambda_arn(api)

        assert extracted_arn == lambda_arn

    def test_extract_cors_config(self):
        """Test extracting CORS configuration from OPTIONS method"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/api": {
                    "options": {
                        "responses": {"200": {"description": "CORS"}},
                        "x-amazon-apigateway-integration": {
                            "type": "mock",
                            "responses": {
                                "default": {
                                    "statusCode": "200",
                                    "responseParameters": {
                                        "method.response.header.Access-Control-Allow-Origin": "'https://app.example.com'",
                                        "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE'",
                                        "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization'"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        })

        parser = AWSAPIGatewayParser()
        api = parser.parse(openapi_spec)
        cors_config = parser.extract_cors_config(api)

        assert cors_config["enabled"] is True
        assert "https://app.example.com" in cors_config["allow_origins"]
        assert set(cors_config["allow_methods"]) == {"GET", "POST", "PUT", "DELETE"}
        assert set(cors_config["allow_headers"]) == {"Content-Type", "Authorization"}


class TestAWSAPIGatewayProviderImport:
    """Test AWS API Gateway provider import functionality"""

    def test_import_basic_http_proxy(self):
        """Test importing basic HTTP_PROXY configuration"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {
                "title": "PetStore API",
                "version": "1.0.0",
                "description": "A simple Pet Store API"
            },
            "paths": {
                "/pets": {
                    "get": {
                        "responses": {"200": {"description": "Success"}},
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "httpMethod": "GET",
                            "uri": "https://petstore.example.com/pets"
                        }
                    },
                    "post": {
                        "responses": {"201": {"description": "Created"}},
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "httpMethod": "POST",
                            "uri": "https://petstore.example.com/pets"
                        }
                    }
                }
            }
        })

        provider = AWSAPIGatewayProvider()
        config = provider.parse(openapi_spec)

        assert config.version == "1.0"
        assert config.provider == "gal"
        assert len(config.services) == 1

        service = config.services[0]
        assert service.name == "imported-api"
        assert service.type == "rest"
        assert service.protocol == "https"
        assert service.upstream.host == "petstore.example.com"
        assert service.upstream.port == 443

        assert len(service.routes) == 1
        assert service.routes[0].path_prefix == "/pets"
        assert set(service.routes[0].methods) == {"GET", "POST"}

        aws_config = config.global_config.aws_apigateway
        assert aws_config.api_name == "PetStore API"
        assert aws_config.api_description == "A simple Pet Store API"
        assert aws_config.integration_type == "HTTP_PROXY"

    def test_import_lambda_integration(self):
        """Test importing AWS_PROXY (Lambda) configuration"""
        lambda_arn = "arn:aws:lambda:us-east-1:123456789012:function:my-function"
        uri = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Lambda API", "version": "1.0.0"},
            "paths": {
                "/lambda": {
                    "post": {
                        "responses": {"200": {"description": "Success"}},
                        "x-amazon-apigateway-integration": {
                            "type": "aws_proxy",
                            "httpMethod": "POST",
                            "uri": uri
                        }
                    }
                }
            }
        })

        provider = AWSAPIGatewayProvider()
        config = provider.parse(openapi_spec)

        aws_config = config.global_config.aws_apigateway
        assert aws_config.integration_type == "AWS_PROXY"
        assert aws_config.lambda_function_arn == lambda_arn

    def test_import_with_api_key(self):
        """Test importing with API key authentication"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Secured API", "version": "1.0.0"},
            "x-amazon-apigateway-api-key-source": "HEADER",
            "components": {
                "securitySchemes": {
                    "api_key": {
                        "type": "apiKey",
                        "name": "x-api-key",
                        "in": "header"
                    }
                }
            },
            "paths": {
                "/secure": {
                    "get": {
                        "security": [{"api_key": []}],
                        "responses": {"200": {"description": "Success"}},
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "uri": "https://api.example.com/secure"
                        }
                    }
                }
            }
        })

        provider = AWSAPIGatewayProvider()
        config = provider.parse(openapi_spec)

        aws_config = config.global_config.aws_apigateway
        assert aws_config.api_key_required is True

        service = config.services[0]
        assert service.routes[0].authentication is not None
        assert service.routes[0].authentication.type == "api_key"
        assert service.routes[0].authentication.api_key.key_name == "x-api-key"

    def test_import_with_cognito(self):
        """Test importing with Cognito User Pool authentication"""
        cognito_arn = "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_AbCdEfGhI"

        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Cognito API", "version": "1.0.0"},
            "components": {
                "securitySchemes": {
                    "cognito_authorizer": {
                        "type": "apiKey",
                        "name": "Authorization",
                        "in": "header",
                        "x-amazon-apigateway-authtype": "cognito_user_pools",
                        "x-amazon-apigateway-authorizer": {
                            "type": "cognito_user_pools",
                            "providerARNs": [cognito_arn]
                        }
                    }
                }
            },
            "paths": {
                "/user": {
                    "get": {
                        "responses": {"200": {"description": "Success"}},
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "uri": "https://api.example.com/user"
                        }
                    }
                }
            }
        })

        provider = AWSAPIGatewayProvider()
        config = provider.parse(openapi_spec)

        service = config.services[0]
        assert service.routes[0].authentication is not None
        assert service.routes[0].authentication.type == "jwt"
        assert service.routes[0].authentication.jwt.issuer.startswith("https://cognito-idp")

    def test_import_with_cors(self):
        """Test importing with CORS configuration"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "CORS API", "version": "1.0.0"},
            "paths": {
                "/api": {
                    "get": {
                        "responses": {"200": {"description": "Success"}},
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "uri": "https://api.example.com/api"
                        }
                    },
                    "options": {
                        "responses": {"200": {"description": "CORS"}},
                        "x-amazon-apigateway-integration": {
                            "type": "mock",
                            "responses": {
                                "default": {
                                    "responseParameters": {
                                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                                        "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'",
                                        "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization'"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        })

        provider = AWSAPIGatewayProvider()
        config = provider.parse(openapi_spec)

        aws_config = config.global_config.aws_apigateway
        assert aws_config.cors_enabled is True
        assert "*" in aws_config.cors_allow_origins
        assert "GET" in aws_config.cors_allow_methods
        assert "Content-Type" in aws_config.cors_allow_headers


class TestAWSAPIGatewayImportIntegration:
    """Test AWS API Gateway import integration scenarios"""

    def test_import_export_roundtrip(self):
        """Test importing and then exporting produces similar config"""
        original_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "Test roundtrip"
            },
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "Success"}},
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "uri": "https://backend.example.com/users"
                        }
                    }
                }
            }
        })

        provider = AWSAPIGatewayProvider()

        # Import
        config = provider.parse(original_spec)

        # Export
        generated_spec = provider.generate(config)
        generated = json.loads(generated_spec)

        # Verify structure
        assert generated["openapi"] == "3.0.1"
        assert generated["info"]["title"] == "Test API"
        assert "/users" in generated["paths"]
        assert "get" in generated["paths"]["/users"]
        assert "x-amazon-apigateway-integration" in generated["paths"]["/users"]["get"]

    def test_import_multiple_routes(self):
        """Test importing configuration with multiple routes"""
        openapi_spec = json.dumps({
            "openapi": "3.0.1",
            "info": {"title": "Multi-Route API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "Success"}},
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "uri": "https://api.example.com/users"
                        }
                    },
                    "post": {
                        "responses": {"201": {"description": "Created"}},
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "uri": "https://api.example.com/users"
                        }
                    }
                },
                "/products": {
                    "get": {
                        "responses": {"200": {"description": "Success"}},
                        "x-amazon-apigateway-integration": {
                            "type": "http_proxy",
                            "uri": "https://api.example.com/products"
                        }
                    }
                }
            }
        })

        provider = AWSAPIGatewayProvider()
        config = provider.parse(openapi_spec)

        assert len(config.services) == 1
        assert len(config.services[0].routes) == 2  # /users and /products
