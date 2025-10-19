#!/usr/bin/env python3
"""
GAL CLI Tool
"""

import logging
import sys
from pathlib import Path

import click

from gal.compatibility import CompatibilityChecker, FeatureSupport
from gal.manager import Manager
from gal.providers import (
    APISIXProvider,
    EnvoyProvider,
    HAProxyProvider,
    KongProvider,
    NginxProvider,
    TraefikProvider,
)

# Configure logging
logger = logging.getLogger()


def setup_logging(log_level):
    """Configure logging based on user-specified level."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@click.group()
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["debug", "info", "warning", "error"], case_sensitive=False),
    default="warning",
    help="Set logging level (default: warning)",
)
@click.pass_context
def cli(ctx, log_level):
    """Gateway Abstraction Layer (GAL) CLI"""
    ctx.ensure_object(dict)
    ctx.obj["LOG_LEVEL"] = log_level
    setup_logging(log_level)


@cli.command()
@click.option("--config", "-c", required=True, help="Configuration file path")
@click.option("--provider", "-p", help="Provider name (overrides config)")
@click.option("--output", "-o", help="Output file (default: stdout)")
def generate(config, provider, output):
    """Generate gateway configuration"""
    try:
        manager = Manager()
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())
        manager.register_provider(APISIXProvider())
        manager.register_provider(TraefikProvider())
        manager.register_provider(NginxProvider())
        manager.register_provider(HAProxyProvider())

        cfg = manager.load_config(config)

        if provider:
            cfg.provider = provider

        click.echo(f"Generating configuration for: {cfg.provider}")
        click.echo(
            f"Services: {len(cfg.services)} ({len(cfg.get_grpc_services())} gRPC, {len(cfg.get_rest_services())} REST)"
        )

        result = manager.generate(cfg)

        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w") as f:
                f.write(result)
            click.echo(f"✓ Configuration written to: {output}")
        else:
            click.echo("\n" + result)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", required=True, help="Configuration file path")
def validate(config):
    """Validate configuration"""
    try:
        manager = Manager()
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())
        manager.register_provider(APISIXProvider())
        manager.register_provider(TraefikProvider())
        manager.register_provider(NginxProvider())
        manager.register_provider(HAProxyProvider())

        cfg = manager.load_config(config)
        manager.validate(cfg)  # Validate with provider-specific rules

        click.echo(f"✓ Configuration is valid")
        click.echo(f"  Provider: {cfg.provider}")
        click.echo(f"  Services: {len(cfg.services)}")
        click.echo(f"  gRPC services: {len(cfg.get_grpc_services())}")
        click.echo(f"  REST services: {len(cfg.get_rest_services())}")

    except Exception as e:
        click.echo(f"✗ Configuration is invalid: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", required=True, help="Configuration file path")
@click.option("--output-dir", "-o", default="generated", help="Output directory")
def generate_all(config, output_dir):
    """Generate configurations for all providers"""
    providers = ["envoy", "kong", "apisix", "traefik", "nginx", "haproxy"]
    extensions = {
        "envoy": "yaml",
        "kong": "yaml",
        "apisix": "json",
        "traefik": "yaml",
        "nginx": "conf",
        "haproxy": "cfg",
    }

    try:
        manager = Manager()
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())
        manager.register_provider(APISIXProvider())
        manager.register_provider(TraefikProvider())
        manager.register_provider(NginxProvider())
        manager.register_provider(HAProxyProvider())

        cfg = manager.load_config(config)
        original_provider = cfg.provider

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        click.echo(f"Generating configurations for all providers...")
        click.echo(f"Output directory: {output_path.absolute()}")
        click.echo("")

        for provider in providers:
            cfg.provider = provider
            result = manager.generate(cfg)

            ext = extensions.get(provider, "txt")
            output_file = output_path / f"{provider}.{ext}"

            with open(output_file, "w") as f:
                f.write(result)

            click.echo(f"  ✓ {provider}: {output_file}")

        cfg.provider = original_provider
        click.echo(f"\n✓ All configurations generated successfully")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", required=True, help="Configuration file path")
def info(config):
    """Show configuration information"""
    try:
        manager = Manager()
        cfg = manager.load_config(config)

        click.echo("=" * 60)
        click.echo("GAL Configuration Information")
        click.echo("=" * 60)
        click.echo(f"Provider: {cfg.provider}")
        click.echo(f"Version: {cfg.version}")
        click.echo("")
        click.echo("Global Settings:")
        click.echo(f"  Host: {cfg.global_config.host}")
        click.echo(f"  Port: {cfg.global_config.port}")
        click.echo(f"  Admin Port: {cfg.global_config.admin_port}")
        click.echo(f"  Timeout: {cfg.global_config.timeout}")
        click.echo("")
        click.echo(f"Services ({len(cfg.services)} total):")
        click.echo("")

        for service in cfg.services:
            click.echo(f"  • {service.name}")
            click.echo(f"    Type: {service.type}")
            click.echo(f"    Upstream: {service.upstream.host}:{service.upstream.port}")
            click.echo(f"    Routes: {len(service.routes)}")

            if service.transformation and service.transformation.enabled:
                click.echo(f"    Transformations: ✓ Enabled")
                click.echo(f"      Defaults: {len(service.transformation.defaults)} fields")
                click.echo(f"      Computed: {len(service.transformation.computed_fields)} fields")
                if service.transformation.validation:
                    click.echo(
                        f"      Required: {', '.join(service.transformation.validation.required_fields)}"
                    )
            else:
                click.echo(f"    Transformations: ✗ Disabled")
            click.echo("")

        if cfg.plugins:
            click.echo(f"Plugins ({len(cfg.plugins)}):")
            for plugin in cfg.plugins:
                status = "✓" if plugin.enabled else "✗"
                click.echo(f"  {status} {plugin.name}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--provider",
    "-p",
    required=True,
    type=click.Choice(
        ["envoy", "kong", "apisix", "traefik", "nginx", "haproxy"], case_sensitive=False
    ),
    help="Source provider to import from",
)
@click.option(
    "--input",
    "-i",
    "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Provider-specific configuration file to import",
)
@click.option(
    "--output",
    "-o",
    "output_file",
    required=True,
    type=click.Path(dir_okay=False),
    help="Output GAL configuration file (YAML)",
)
def import_config(provider, input_file, output_file):
    """Import provider-specific configuration to GAL format"""
    try:
        click.echo(f"Importing {provider} configuration from: {input_file}")

        # Create manager and register providers
        manager = Manager()
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())
        manager.register_provider(APISIXProvider())
        manager.register_provider(TraefikProvider())
        manager.register_provider(NginxProvider())
        manager.register_provider(HAProxyProvider())

        # Get the provider instance
        provider_instance = manager.get_provider(provider)
        if not provider_instance:
            click.echo(f"Error: Provider '{provider}' not found", err=True)
            sys.exit(1)

        # Read provider-specific config
        with open(input_file, "r") as f:
            provider_config = f.read()

        click.echo(f"Parsing {provider} configuration...")

        # Parse to GAL format
        try:
            gal_config = provider_instance.parse(provider_config)
        except NotImplementedError as e:
            click.echo(f"Error: {e}", err=True)
            click.echo(f"\n💡 Tip: Check the v1.3.0 roadmap for implementation timeline.", err=True)
            sys.exit(1)

        # Convert GAL Config to YAML
        import yaml

        from gal.config import Config

        # Build YAML structure
        config_dict = {
            "version": gal_config.version,
            "provider": gal_config.provider,
            "global": {
                "host": gal_config.global_config.host,
                "port": gal_config.global_config.port,
            },
            "services": [],
        }

        for service in gal_config.services:
            service_dict = {
                "name": service.name,
                "type": service.type,
                "protocol": service.protocol,
                "upstream": {
                    "targets": [
                        {"host": t.host, "port": t.port, "weight": t.weight}
                        for t in service.upstream.targets
                    ]
                },
                "routes": [{"path_prefix": r.path_prefix} for r in service.routes],
            }

            # Add health checks if present
            if service.upstream.health_check:
                hc = service.upstream.health_check
                hc_dict = {}
                if hasattr(hc, "active") and hc.active:
                    hc_dict["active"] = {
                        "enabled": hc.active.enabled,
                        "http_path": hc.active.http_path,
                        "interval": hc.active.interval,
                        "timeout": hc.active.timeout,
                        "unhealthy_threshold": hc.active.unhealthy_threshold,
                        "healthy_threshold": hc.active.healthy_threshold,
                    }
                if hasattr(hc, "passive") and hc.passive:
                    hc_dict["passive"] = {
                        "enabled": hc.passive.enabled,
                        "max_failures": hc.passive.max_failures,
                    }
                if hc_dict:
                    service_dict["upstream"]["health_check"] = hc_dict

            # Add load balancer if present
            if service.upstream.load_balancer:
                service_dict["upstream"]["load_balancer"] = {
                    "algorithm": service.upstream.load_balancer.algorithm
                }

            config_dict["services"].append(service_dict)

        # Write to output file
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, sort_keys=False)

        click.echo(f"\n✓ Successfully imported configuration!")
        click.echo(f"  Source:      {input_file} ({provider})")
        click.echo(f"  Destination: {output_file} (GAL YAML)")
        click.echo(f"  Services:    {len(gal_config.services)}")
        click.echo(f"  Routes:      {sum(len(s.routes) for s in gal_config.services)}")

        click.echo(f"\n💡 Next steps:")
        click.echo(f"   1. Review the generated GAL config: {output_file}")
        click.echo(f"   2. Generate config for target provider:")
        click.echo(f"      gal generate --config {output_file} --provider <target-provider>")

    except FileNotFoundError as e:
        click.echo(f"Error: File not found: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


@cli.command()
def list_providers():
    """List all available providers"""
    click.echo("Available providers:")
    click.echo("  • envoy   - Envoy Proxy")
    click.echo("  • kong    - Kong API Gateway")
    click.echo("  • apisix  - Apache APISIX")
    click.echo("  • traefik - Traefik")
    click.echo("  • nginx   - Nginx Open Source")
    click.echo("  • haproxy - HAProxy Load Balancer")


@cli.command()
@click.option("--config", "-c", required=True, help="Configuration file path")
@click.option(
    "--target-provider",
    "-p",
    required=True,
    type=click.Choice(
        ["envoy", "kong", "apisix", "traefik", "nginx", "haproxy"], case_sensitive=False
    ),
    help="Target provider to check compatibility with",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed feature information")
def check_compatibility(config, target_provider, verbose):
    """Check GAL config compatibility with a target provider"""
    try:
        # Load config
        manager = Manager()
        cfg = manager.load_config(config)

        # Create compatibility checker
        checker = CompatibilityChecker()

        # Check compatibility
        click.echo(f"Checking compatibility with {target_provider}...")
        click.echo("")

        report = checker.check_provider(cfg, target_provider)

        # Display results
        _display_compatibility_report(report, verbose)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", required=True, help="Configuration file path")
@click.option(
    "--providers",
    "-p",
    help="Comma-separated list of providers to compare (default: all)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed feature information")
def compare_providers(config, providers, verbose):
    """Compare GAL config compatibility across multiple providers"""
    try:
        # Load config
        manager = Manager()
        cfg = manager.load_config(config)

        # Parse provider list
        if providers:
            provider_list = [p.strip().lower() for p in providers.split(",")]
        else:
            provider_list = ["envoy", "kong", "apisix", "traefik", "nginx", "haproxy"]

        # Create compatibility checker
        checker = CompatibilityChecker()

        # Compare providers
        click.echo(f"Comparing compatibility across {len(provider_list)} providers...")
        click.echo("")

        reports = checker.compare_providers(cfg, provider_list)

        # Display comparison table
        _display_comparison_table(reports)

        # Show detailed reports if verbose
        if verbose:
            click.echo("\n" + "=" * 80)
            click.echo("DETAILED REPORTS")
            click.echo("=" * 80)
            for report in reports:
                click.echo("")
                _display_compatibility_report(report, verbose=True)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


def _display_compatibility_report(report, verbose=False):
    """Display a single compatibility report."""
    # Header
    click.echo("=" * 80)
    click.echo(f"COMPATIBILITY REPORT: {report.provider.upper()}")
    click.echo("=" * 80)

    # Overall status
    status_symbol = "✅" if report.compatible else "❌"
    status_text = "COMPATIBLE" if report.compatible else "NOT COMPATIBLE"
    score_percent = report.compatibility_score * 100

    click.echo(f"\n{status_symbol} Status: {status_text}")
    click.echo(f"📊 Compatibility Score: {score_percent:.1f}%")
    click.echo(f"🔍 Features Checked: {report.features_checked}")
    click.echo("")

    # Feature summary
    click.echo(f"✅ Fully Supported:   {len(report.features_supported)}")
    click.echo(f"⚠️  Partially Supported: {len(report.features_partial)}")
    click.echo(f"❌ Not Supported:     {len(report.features_unsupported)}")
    click.echo("")

    # Warnings
    if report.warnings:
        click.echo("⚠️  WARNINGS:")
        for warning in report.warnings:
            click.echo(f"  • {warning}")
        click.echo("")

    # Recommendations
    if report.recommendations:
        click.echo("💡 RECOMMENDATIONS:")
        for rec in report.recommendations:
            click.echo(f"  • {rec}")
        click.echo("")

    # Detailed feature list (if verbose)
    if verbose:
        if report.features_supported:
            click.echo("✅ FULLY SUPPORTED FEATURES:")
            for feature in report.features_supported:
                click.echo(f"  • {feature.feature_name}")
                if feature.message:
                    click.echo(f"    {feature.message}")
            click.echo("")

        if report.features_partial:
            click.echo("⚠️  PARTIALLY SUPPORTED FEATURES:")
            for feature in report.features_partial:
                click.echo(f"  • {feature.feature_name}")
                if feature.message:
                    click.echo(f"    {feature.message}")
                if feature.recommendation:
                    click.echo(f"    💡 {feature.recommendation}")
            click.echo("")

        if report.features_unsupported:
            click.echo("❌ UNSUPPORTED FEATURES:")
            for feature in report.features_unsupported:
                click.echo(f"  • {feature.feature_name}")
                if feature.message:
                    click.echo(f"    {feature.message}")
                if feature.recommendation:
                    click.echo(f"    💡 {feature.recommendation}")
            click.echo("")


def _display_comparison_table(reports):
    """Display comparison table across multiple providers."""
    click.echo("=" * 100)
    click.echo("PROVIDER COMPARISON")
    click.echo("=" * 100)
    click.echo("")

    # Table header
    click.echo(
        f"{'Provider':<12} {'Status':<15} {'Score':<10} {'Supported':<12} {'Partial':<10} {'Unsupported':<12}"
    )
    click.echo("-" * 100)

    # Sort by score (descending)
    sorted_reports = sorted(reports, key=lambda r: r.compatibility_score, reverse=True)

    for report in sorted_reports:
        status_symbol = "✅" if report.compatible else "❌"
        status_text = "Compatible" if report.compatible else "Incompatible"
        score_percent = f"{report.compatibility_score * 100:.1f}%"

        click.echo(
            f"{report.provider:<12} {status_symbol} {status_text:<13} {score_percent:<10} "
            f"{len(report.features_supported):<12} {len(report.features_partial):<10} "
            f"{len(report.features_unsupported):<12}"
        )

    click.echo("")

    # Summary
    compatible_count = sum(1 for r in reports if r.compatible)
    click.echo(f"Summary: {compatible_count}/{len(reports)} providers are compatible")
    click.echo("")

    # Best provider recommendation
    best = sorted_reports[0]
    if best.compatibility_score == 1.0:
        click.echo(f"✨ Best choice: {best.provider} (100% compatible)")
    else:
        click.echo(
            f"💡 Best choice: {best.provider} ({best.compatibility_score * 100:.1f}% compatible)"
        )


if __name__ == "__main__":
    cli()
