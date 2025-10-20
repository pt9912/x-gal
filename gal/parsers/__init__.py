"""GAL Configuration Parsers.

This module contains custom parsers for provider-specific configuration formats.
"""

from gal.parsers.aws_apigateway_parser import AWSAPIGatewayAPI, AWSAPIGatewayParser
from gal.parsers.azure_apim_parser import AzureAPIMAPI, AzureAPIMParser
from gal.parsers.haproxy_parser import HAProxyConfigParser, HAProxySection, SectionType

__all__ = [
    "HAProxyConfigParser",
    "HAProxySection",
    "SectionType",
    "AWSAPIGatewayParser",
    "AWSAPIGatewayAPI",
    "AzureAPIMParser",
    "AzureAPIMAPI",
]
