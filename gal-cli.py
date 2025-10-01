#!/usr/bin/env python3
"""
GAL CLI Tool
"""

import click
import sys
from pathlib import Path

from gal.manager import Manager
from gal.providers import EnvoyProvider, KongProvider, APISIXProvider, TraefikProvider


@click.group()
def cli():
    """Gateway Abstraction Layer (GAL) CLI"""
    pass


@cli.command()
@click.option('--config', '-c', required=True, help='Configuration file path')
@click.option('--provider', '-p', help='Provider name (overrides config)')
@click.option('--output', '-o', help='Output file (default: stdout)')
def generate(config, provider, output):
    """Generate gateway configuration"""
    try:
        manager = Manager()
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())
        manager.register_provider(APISIXProvider())
        manager.register_provider(TraefikProvider())
        
        cfg = manager.load_config(config)
        
        if provider:
            cfg.provider = provider
        
        click.echo(f"Generating configuration for: {cfg.provider}")
        click.echo(f"Services: {len(cfg.services)} ({len(cfg.get_grpc_services())} gRPC, {len(cfg.get_rest_services())} REST)")
        
        result = manager.generate(cfg)
        
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, 'w') as f:
                f.write(result)
            click.echo(f"✓ Configuration written to: {output}")
        else:
            click.echo("\n" + result)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, help='Configuration file path')
def validate(config):
    """Validate configuration"""
    try:
        manager = Manager()
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())
        manager.register_provider(APISIXProvider())
        manager.register_provider(TraefikProvider())
        
        cfg = manager.load_config(config)
        click.echo(f"✓ Configuration is valid")
        click.echo(f"  Provider: {cfg.provider}")
        click.echo(f"  Services: {len(cfg.services)}")
        click.echo(f"  gRPC services: {len(cfg.get_grpc_services())}")
        click.echo(f"  REST services: {len(cfg.get_rest_services())}")
    
    except Exception as e:
        click.echo(f"✗ Configuration is invalid: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, help='Configuration file path')
@click.option('--output-dir', '-o', default='generated', help='Output directory')
def generate_all(config, output_dir):
    """Generate configurations for all providers"""
    providers = ['envoy', 'kong', 'apisix', 'traefik']
    extensions = {'envoy': 'yaml', 'kong': 'yaml', 'apisix': 'json', 'traefik': 'yaml'}
    
    try:
        manager = Manager()
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())
        manager.register_provider(APISIXProvider())
        manager.register_provider(TraefikProvider())
        
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
            
            ext = extensions.get(provider, 'txt')
            output_file = output_path / f"{provider}.{ext}"
            
            with open(output_file, 'w') as f:
                f.write(result)
            
            click.echo(f"  ✓ {provider}: {output_file}")
        
        cfg.provider = original_provider
        click.echo(f"\n✓ All configurations generated successfully")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, help='Configuration file path')
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
                    click.echo(f"      Required: {', '.join(service.transformation.validation.required_fields)}")
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
def list_providers():
    """List all available providers"""
    click.echo("Available providers:")
    click.echo("  • envoy   - Envoy Proxy")
    click.echo("  • kong    - Kong API Gateway")
    click.echo("  • apisix  - Apache APISIX")
    click.echo("  • traefik - Traefik")


if __name__ == '__main__':
    cli()
