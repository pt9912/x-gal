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
    AzureAPIMProvider,
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
        manager.register_provider(AzureAPIMProvider())

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
        manager.register_provider(AzureAPIMProvider())

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
        manager.register_provider(AzureAPIMProvider())

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
        manager.register_provider(AzureAPIMProvider())

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


@cli.command()
@click.option("--source-provider", "-s", help="Source provider (skip interactive mode)")
@click.option("--source-config", "-i", help="Source configuration file")
@click.option("--target-provider", "-t", help="Target provider")
@click.option("--output-dir", "-o", help="Output directory for migration files")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
def migrate(source_provider, source_config, target_provider, output_dir, yes):
    """Interactive migration assistant to migrate between providers"""
    try:
        from datetime import datetime

        import yaml

        # Display welcome message
        click.echo("=" * 80)
        click.echo("🔀 GAL Migration Assistant")
        click.echo("=" * 80)
        click.echo()

        # Interactive prompts if options not provided
        if not source_provider:
            source_provider = click.prompt(
                "Source Provider",
                type=click.Choice(
                    ["envoy", "kong", "apisix", "traefik", "nginx", "haproxy"], case_sensitive=False
                ),
            )

        if not source_config:
            source_config = click.prompt(
                "Source Configuration File", type=click.Path(exists=True, dir_okay=False)
            )

        if not target_provider:
            target_provider = click.prompt(
                "Target Provider",
                type=click.Choice(
                    ["envoy", "kong", "apisix", "traefik", "nginx", "haproxy"], case_sensitive=False
                ),
            )

        if not output_dir:
            output_dir = click.prompt("Output Directory", default="./migration", type=click.Path())

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        click.echo()
        click.echo("Migration Plan:")
        click.echo(f"  Source: {source_provider} ({source_config})")
        click.echo(f"  Target: {target_provider}")
        click.echo(f"  Output: {output_dir}")
        click.echo()

        if not yes:
            if not click.confirm("Proceed with migration?", default=True):
                click.echo("Migration cancelled.")
                return

        click.echo()

        # Step 1/5: Reading source config
        click.echo("[1/5] 📖 Reading {} config...".format(source_provider.title()))

        # Create manager and register providers
        manager = Manager()
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())
        manager.register_provider(APISIXProvider())
        manager.register_provider(TraefikProvider())
        manager.register_provider(NginxProvider())
        manager.register_provider(HAProxyProvider())
        manager.register_provider(AzureAPIMProvider())

        # Get source provider instance
        source_instance = manager.get_provider(source_provider)
        if not source_instance:
            click.echo(f"❌ Error: Source provider '{source_provider}' not found", err=True)
            sys.exit(1)

        # Read source config
        with open(source_config, "r") as f:
            source_config_content = f.read()

        click.echo("   ✓ Config file read successfully")

        # Step 2/5: Parsing and analyzing
        click.echo("[2/5] 🔍 Parsing and analyzing...")

        try:
            gal_config = source_instance.parse(source_config_content)
            click.echo(f"   ✓ Parsed {len(gal_config.services)} services")
            total_routes = sum(len(s.routes) for s in gal_config.services)
            click.echo(f"   ✓ Found {total_routes} routes")
        except NotImplementedError:
            click.echo(f"❌ Error: {source_provider} import not yet implemented", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Error parsing config: {e}", err=True)
            sys.exit(1)

        # Step 3/5: Converting to GAL format
        click.echo("[3/5] 🔄 Converting to GAL format...")

        # Save GAL config
        gal_config_path = output_path / "gal-config.yaml"

        # Build YAML structure
        config_dict = {
            "version": gal_config.version,
            "provider": target_provider,  # Set to target provider
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

            # Add optional features if present
            if service.upstream.load_balancer:
                service_dict["upstream"]["load_balancer"] = {
                    "algorithm": service.upstream.load_balancer.algorithm
                }

            if service.upstream.health_check:
                hc = service.upstream.health_check
                hc_dict = {}
                if hasattr(hc, "active") and hc.active:
                    hc_dict["active"] = {
                        "enabled": hc.active.enabled,
                        "http_path": hc.active.http_path,
                        "interval": hc.active.interval,
                        "timeout": hc.active.timeout,
                    }
                if hasattr(hc, "passive") and hc.passive:
                    hc_dict["passive"] = {
                        "enabled": hc.passive.enabled,
                        "max_failures": hc.passive.max_failures,
                    }
                if hc_dict:
                    service_dict["upstream"]["health_check"] = hc_dict

            config_dict["services"].append(service_dict)

        with open(gal_config_path, "w") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, sort_keys=False)

        click.echo(f"   ✓ GAL config saved: {gal_config_path}")

        # Step 4/5: Validating compatibility
        click.echo(f"[4/5] ✅ Validating compatibility with {target_provider.title()}...")

        checker = CompatibilityChecker()
        compat_report = checker.check_provider(gal_config, target_provider)

        score_percent = compat_report.compatibility_score * 100
        click.echo(
            f"   ✓ Compatibility: {score_percent:.1f}% ({len(compat_report.features_supported)}/{compat_report.features_checked} features)"
        )

        if compat_report.features_partial:
            click.echo(f"   ⚠️  {len(compat_report.features_partial)} partially supported features")

        if compat_report.features_unsupported:
            click.echo(f"   ❌ {len(compat_report.features_unsupported)} unsupported features")

        # Step 5/5: Generating target config
        click.echo(f"[5/5] 🎯 Generating {target_provider.title()} config...")

        # Update config provider to target
        gal_config.provider = target_provider

        target_config = manager.generate(gal_config)

        # Determine file extension
        extensions = {
            "envoy": "yaml",
            "kong": "yaml",
            "apisix": "json",
            "traefik": "yaml",
            "nginx": "conf",
            "haproxy": "cfg",
        }
        ext = extensions.get(target_provider, "txt")
        target_config_path = output_path / f"{target_provider}.{ext}"

        with open(target_config_path, "w") as f:
            f.write(target_config)

        click.echo(f"   ✓ {target_provider.title()} config saved: {target_config_path}")

        # Generate migration report
        click.echo()
        click.echo("📄 Generating migration report...")

        report_path = output_path / "migration-report.md"
        report_content = _generate_migration_report(
            source_provider=source_provider,
            source_config=source_config,
            target_provider=target_provider,
            gal_config=gal_config,
            compat_report=compat_report,
            total_routes=total_routes,
        )

        with open(report_path, "w") as f:
            f.write(report_content)

        click.echo(f"   ✓ Migration report saved: {report_path}")

        # Success summary
        click.echo()
        click.echo("=" * 80)
        click.echo("✅ Migration complete!")
        click.echo("=" * 80)
        click.echo()
        click.echo("Files created:")
        click.echo(f"  📄 {gal_config_path} (GAL format)")
        click.echo(f"  📄 {target_config_path} ({target_provider.title()} config)")
        click.echo(f"  📄 {report_path} (Migration report)")
        click.echo()
        click.echo(
            f"Compatibility: {score_percent:.1f}% ({len(compat_report.features_supported)}/{compat_report.features_checked} features)"
        )

        if compat_report.warnings:
            click.echo(f"Warnings: {len(compat_report.warnings)}")
            for warning in compat_report.warnings[:3]:  # Show first 3
                click.echo(f"  ⚠️  {warning}")
            if len(compat_report.warnings) > 3:
                click.echo(f"  ... and {len(compat_report.warnings) - 3} more (see report)")

        click.echo()
        click.echo("Next steps:")
        click.echo("  1. Review migration-report.md")
        click.echo(f"  2. Test {target_provider}.{ext} in staging")
        click.echo("  3. Deploy to production")
        click.echo()

    except Exception as e:
        click.echo(f"❌ Migration failed: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


def _generate_migration_report(
    source_provider, source_config, target_provider, gal_config, compat_report, total_routes
):
    """Generate migration report in Markdown format."""
    from datetime import datetime

    report = []
    report.append(f"# Migration Report: {source_provider.title()} → {target_provider.title()}")
    report.append("")
    report.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Source:** {source_config} ({source_provider.title()})")
    report.append(f"**Target:** {target_provider.title()}")
    report.append("")

    # Summary
    report.append("## Summary")
    report.append("")
    score_percent = compat_report.compatibility_score * 100
    report.append(
        f"- **Compatibility:** {score_percent:.1f}% ({len(compat_report.features_supported)}/{compat_report.features_checked} features)"
    )
    report.append(f"- **Services Migrated:** {len(gal_config.services)}")
    report.append(f"- **Routes Migrated:** {total_routes}")
    report.append(f"- **Warnings:** {len(compat_report.warnings)}")
    report.append("")

    # Features Status
    report.append("## Features Status")
    report.append("")

    if compat_report.features_supported:
        report.append("### ✅ Fully Supported Features")
        report.append("")
        for feature in compat_report.features_supported:
            report.append(f"- **{feature.feature_name}:** {feature.message}")
        report.append("")

    if compat_report.features_partial:
        report.append("### ⚠️  Partially Supported Features")
        report.append("")
        for feature in compat_report.features_partial:
            report.append(f"- **{feature.feature_name}:** {feature.message}")
            if feature.recommendation:
                report.append(f"  - 💡 **Recommendation:** {feature.recommendation}")
        report.append("")

    if compat_report.features_unsupported:
        report.append("### ❌ Unsupported Features")
        report.append("")
        for feature in compat_report.features_unsupported:
            report.append(f"- **{feature.feature_name}:** {feature.message}")
            if feature.recommendation:
                report.append(f"  - 💡 **Recommendation:** {feature.recommendation}")
        report.append("")

    # Warnings & Recommendations
    if compat_report.warnings or compat_report.recommendations:
        report.append("## Warnings & Recommendations")
        report.append("")

        for i, warning in enumerate(compat_report.warnings, 1):
            report.append(f"{i}. **{warning}**")

        for rec in compat_report.recommendations:
            report.append(f"   - 💡 {rec}")
        report.append("")

    # Services Details
    report.append("## Services")
    report.append("")
    for service in gal_config.services:
        report.append(f"### {service.name}")
        report.append("")
        report.append(f"- **Type:** {service.type}")
        report.append(f"- **Protocol:** {service.protocol}")
        report.append(f"- **Upstream:** {service.upstream.host}:{service.upstream.port}")
        report.append(f"- **Routes:** {len(service.routes)}")

        if service.upstream.load_balancer:
            report.append(f"- **Load Balancer:** {service.upstream.load_balancer.algorithm}")

        if service.upstream.health_check:
            report.append("- **Health Checks:** Configured")

        report.append("")

    # Testing Checklist
    report.append("## Testing Checklist")
    report.append("")
    report.append("- [ ] Test in staging environment")
    report.append(f"- [ ] Verify all {total_routes} routes")
    report.append("- [ ] Check load balancing distribution")
    report.append("- [ ] Validate health check behavior")
    report.append("- [ ] Monitor backend connectivity")
    report.append("- [ ] Performance comparison")
    report.append("")

    # Next Steps
    report.append("## Next Steps")
    report.append("")
    report.append("1. ✅ Review this report")
    report.append("2. ⏳ Test in staging environment")
    if compat_report.features_partial or compat_report.features_unsupported:
        report.append("3. ⏳ Address partially supported/unsupported features")
        report.append("4. ⏳ Deploy to production")
        report.append("5. ⏳ Monitor and validate")
    else:
        report.append("3. ⏳ Deploy to production")
        report.append("4. ⏳ Monitor and validate")
    report.append("")

    return "\n".join(report)


if __name__ == "__main__":
    cli()
