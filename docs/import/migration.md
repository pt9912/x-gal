# Feature 8: Migration Assistant

**Status:** 🔄 Geplant
**Aufwand:** 2 Wochen
**Release:** v1.3.0 Final (Woche 12)
**Priorität:** 🟡 Mittel

## Übersicht

Der Migration Assistant ist ein **interaktiver CLI-Workflow**, der Nutzer durch den kompletten Migrations-Prozess von einem Provider zu einem anderen führt. Er kombiniert Import, Compatibility Check und Export mit Schritt-für-Schritt-Anleitung.

## Use Cases

1. **Guided Migration**: Nginx → HAProxy Migration mit Anleitung
2. **Risk Assessment**: Zeige Risiken und Inkompatibilitäten vor Migration
3. **Rollback Plan**: Generiere Rollback-Dokumentation
4. **Documentation**: Erstelle Migration Report für Team

## Implementierung

### CLI Command

```bash
# Interactive migration workflow
gal migrate

# Non-interactive with parameters
gal migrate --source-provider nginx --source-config nginx.conf \
            --target-provider haproxy --output haproxy.cfg \
            --report migration-report.md
```

### Interactive Workflow

```python
# gal/migration_assistant.py

import click
from typing import Optional, Dict, Any
from pathlib import Path

from gal.config import Config
from gal.provider import Provider
from gal.providers import get_provider
from gal.compatibility import CompatibilityChecker

class MigrationAssistant:
    """Interactive migration assistant."""

    def __init__(self):
        self.checker = CompatibilityChecker()

    def run_interactive(self):
        """Run interactive migration workflow."""
        click.echo("=" * 60)
        click.echo("🚀 GAL Migration Assistant")
        click.echo("=" * 60)
        click.echo()

        # Step 1: Source Provider
        click.echo("📌 Step 1: Source Configuration")
        click.echo()

        source_provider = self._prompt_provider("Select source provider")
        source_config_path = click.prompt(
            "Path to source configuration file",
            type=click.Path(exists=True)
        )

        # Step 2: Import
        click.echo()
        click.echo("📥 Step 2: Importing Configuration...")
        click.echo()

        gal_config, import_warnings = self._import_config(
            source_provider,
            source_config_path
        )

        if import_warnings:
            click.echo("⚠️  Import Warnings:")
            for warning in import_warnings:
                click.echo(f"  - {warning}")
            click.echo()

        # Show imported config summary
        self._show_config_summary(gal_config)

        # Step 3: Target Provider
        click.echo()
        click.echo("📌 Step 3: Target Provider")
        click.echo()

        target_provider = self._prompt_provider(
            "Select target provider",
            exclude=[source_provider]
        )

        # Step 4: Compatibility Check
        click.echo()
        click.echo("🔍 Step 4: Compatibility Check...")
        click.echo()

        compat = self.checker.check_compatibility(gal_config, target_provider)

        self._show_compatibility_result(compat)

        if not compat.compatible:
            if not click.confirm("\n⚠️  Configuration is not fully compatible. Continue anyway?"):
                click.echo("❌ Migration cancelled.")
                return

        # Step 5: Generate Target Config
        click.echo()
        click.echo("⚙️  Step 5: Generating Target Configuration...")
        click.echo()

        output_path = click.prompt(
            "Output file path",
            default=f"generated/{target_provider}-config.yaml"
        )

        target_config = self._generate_config(gal_config, target_provider)

        # Write output
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(target_config)

        click.echo(f"✅ Target configuration written to: {output_path}")

        # Step 6: Migration Report
        click.echo()
        click.echo("📝 Step 6: Migration Report")
        click.echo()

        if click.confirm("Generate migration report?", default=True):
            report_path = click.prompt(
                "Report file path",
                default="migration-report.md"
            )

            report = self._generate_migration_report(
                source_provider,
                source_config_path,
                target_provider,
                output_path,
                gal_config,
                compat,
                import_warnings
            )

            Path(report_path).write_text(report)
            click.echo(f"✅ Migration report written to: {report_path}")

        # Step 7: Next Steps
        click.echo()
        click.echo("=" * 60)
        click.echo("✅ Migration Complete!")
        click.echo("=" * 60)
        click.echo()

        self._show_next_steps(target_provider, output_path, compat)

    def _prompt_provider(
        self,
        prompt_text: str,
        exclude: Optional[list] = None
    ) -> str:
        """Prompt user to select a provider."""
        providers = ["envoy", "kong", "apisix", "traefik", "nginx", "haproxy"]

        if exclude:
            providers = [p for p in providers if p not in exclude]

        click.echo(f"{prompt_text}:")
        for i, provider in enumerate(providers, 1):
            click.echo(f"  {i}. {provider}")

        choice = click.prompt(
            "Enter number",
            type=click.IntRange(1, len(providers))
        )

        return providers[choice - 1]

    def _import_config(
        self,
        provider_name: str,
        config_path: str
    ) -> tuple[Config, list]:
        """Import config from provider."""
        provider = get_provider(provider_name)

        with open(config_path, "r") as f:
            config_text = f.read()

        gal_config = provider.parse(config_text)
        warnings = provider.get_import_warnings()

        return gal_config, warnings

    def _generate_config(
        self,
        config: Config,
        provider_name: str
    ) -> str:
        """Generate config for target provider."""
        provider = get_provider(provider_name)
        return provider.generate(config)

    def _show_config_summary(self, config: Config):
        """Show summary of imported config."""
        click.echo("✅ Import successful!\n")
        click.echo(f"📊 Configuration Summary:")
        click.echo(f"  - Services: {len(config.services)}")

        total_routes = sum(len(s.routes) for s in config.services)
        total_targets = sum(
            len(s.upstream.targets) if s.upstream else 0
            for s in config.services
        )

        click.echo(f"  - Routes: {total_routes}")
        click.echo(f"  - Upstream Targets: {total_targets}")

    def _show_compatibility_result(self, compat):
        """Show compatibility check result."""
        if compat.compatible:
            click.echo(f"✅ Configuration is compatible with {compat.provider_name}")
        else:
            click.echo(f"❌ Configuration is NOT compatible with {compat.provider_name}")
            click.echo()
            click.echo("Errors:")
            for error in compat.errors:
                click.echo(f"  - ❌ {error}")

        if compat.warnings:
            click.echo()
            click.echo("Warnings:")
            for warning in compat.warnings:
                click.echo(f"  - ⚠️ {warning}")

    def _generate_migration_report(
        self,
        source_provider: str,
        source_config: str,
        target_provider: str,
        target_config: str,
        gal_config: Config,
        compat,
        import_warnings: list
    ) -> str:
        """Generate migration report in Markdown."""
        report = []

        # Header
        report.append(f"# Migration Report: {source_provider.title()} → {target_provider.title()}\n\n")
        report.append(f"**Date:** {self._get_timestamp()}\n")
        report.append(f"**GAL Version:** 1.3.0\n\n")

        # Summary
        report.append("## Summary\n\n")
        report.append(f"- **Source Provider:** {source_provider}\n")
        report.append(f"- **Source Config:** {source_config}\n")
        report.append(f"- **Target Provider:** {target_provider}\n")
        report.append(f"- **Target Config:** {target_config}\n")
        report.append(f"- **Status:** {'✅ Compatible' if compat.compatible else '❌ Incompatible'}\n\n")

        # Configuration Details
        report.append("## Configuration Details\n\n")
        report.append(f"- **Services:** {len(gal_config.services)}\n")

        total_routes = sum(len(s.routes) for s in gal_config.services)
        total_targets = sum(
            len(s.upstream.targets) if s.upstream else 0
            for s in gal_config.services
        )

        report.append(f"- **Routes:** {total_routes}\n")
        report.append(f"- **Upstream Targets:** {total_targets}\n\n")

        # Import Warnings
        if import_warnings:
            report.append("## Import Warnings\n\n")
            for warning in import_warnings:
                report.append(f"- ⚠️ {warning}\n")
            report.append("\n")

        # Compatibility Check
        report.append("## Compatibility Check\n\n")

        if compat.compatible:
            report.append("✅ **All features are compatible**\n\n")
        else:
            report.append("❌ **Some features are incompatible**\n\n")

            report.append("### Errors\n\n")
            for error in compat.errors:
                report.append(f"- ❌ {error}\n")
            report.append("\n")

        if compat.warnings:
            report.append("### Warnings\n\n")
            for warning in compat.warnings:
                report.append(f"- ⚠️ {warning}\n")
            report.append("\n")

        # Feature Support
        report.append("### Feature Support\n\n")
        report.append("| Feature | Status | Notes |\n")
        report.append("|---------|--------|-------|\n")

        for feature in compat.features:
            if feature.level.value == "full":
                status = "✅ Full"
            elif feature.level.value == "partial":
                status = "⚠️ Partial"
            elif feature.level.value == "manual":
                status = "🔧 Manual"
            else:
                status = "❌ Unsupported"

            notes = feature.workaround or feature.message
            report.append(f"| {feature.feature_name} | {status} | {notes} |\n")

        report.append("\n")

        # Next Steps
        report.append("## Next Steps\n\n")
        report.append("1. **Review Generated Configuration**\n")
        report.append(f"   - Check `{target_config}` for correctness\n")
        report.append("   - Validate syntax with target provider's tools\n\n")

        report.append("2. **Test in Staging**\n")
        report.append(f"   - Deploy to staging environment\n")
        report.append("   - Run integration tests\n")
        report.append("   - Verify all routes work correctly\n\n")

        if compat.warnings or not compat.compatible:
            report.append("3. **Address Warnings/Errors**\n")
            for feature in compat.features:
                if feature.workaround:
                    report.append(f"   - **{feature.feature_name}**: {feature.workaround}\n")
            report.append("\n")

        report.append("4. **Production Deployment**\n")
        report.append("   - Create rollback plan\n")
        report.append("   - Deploy during low-traffic window\n")
        report.append("   - Monitor logs and metrics\n\n")

        # Rollback Plan
        report.append("## Rollback Plan\n\n")
        report.append(f"If migration fails, revert to original configuration:\n\n")
        report.append(f"```bash\n")
        report.append(f"# Restore original {source_provider} config\n")
        report.append(f"cp {source_config}.backup {source_config}\n")
        report.append(f"# Restart {source_provider}\n")
        report.append(f"systemctl restart {source_provider}\n")
        report.append(f"```\n\n")

        # References
        report.append("## References\n\n")
        report.append(f"- [GAL Documentation](https://github.com/pt9912/x-gal)\n")
        report.append(f"- [{target_provider.title()} Documentation](#{target_provider}-docs)\n")
        report.append(f"- [Migration Guide](docs/guides/MIGRATION.md)\n")

        return "".join(report)

    def _show_next_steps(self, target_provider: str, output_path: str, compat):
        """Show next steps after migration."""
        click.echo("📋 Next Steps:\n")
        click.echo(f"1. Review generated config: {output_path}")
        click.echo(f"2. Validate syntax:")

        if target_provider == "nginx":
            click.echo(f"   nginx -t -c {output_path}")
        elif target_provider == "haproxy":
            click.echo(f"   haproxy -c -f {output_path}")
        elif target_provider == "envoy":
            click.echo(f"   envoy --mode validate -c {output_path}")
        else:
            click.echo(f"   (Check {target_provider} documentation for validation command)")

        click.echo(f"3. Test in staging environment")
        click.echo(f"4. Deploy to production")

        if not compat.compatible or compat.warnings:
            click.echo()
            click.echo("⚠️  Remember to address warnings before production deployment!")

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# CLI Integration
@cli.command("migrate")
@click.option("--source-provider", help="Source provider name")
@click.option("--source-config", help="Source config file path")
@click.option("--target-provider", help="Target provider name")
@click.option("--output", help="Output config file path")
@click.option("--report", help="Migration report path")
def migrate(source_provider, source_config, target_provider, output, report):
    """Migration assistant (interactive or scripted)."""
    assistant = MigrationAssistant()

    if source_provider and source_config and target_provider and output:
        # Non-interactive mode
        assistant.run_non_interactive(
            source_provider,
            source_config,
            target_provider,
            output,
            report
        )
    else:
        # Interactive mode
        assistant.run_interactive()
```

## Workflow-Beispiel

### Interaktiver Modus

```bash
$ gal migrate

============================================================
🚀 GAL Migration Assistant
============================================================

📌 Step 1: Source Configuration

Select source provider:
  1. envoy
  2. kong
  3. apisix
  4. traefik
  5. nginx
  6. haproxy
Enter number: 5

Path to source configuration file: /etc/nginx/nginx.conf

📥 Step 2: Importing Configuration...

✅ Import successful!

📊 Configuration Summary:
  - Services: 3
  - Routes: 8
  - Upstream Targets: 12

⚠️  Import Warnings:
  - Rate limiting config simplified - manual review recommended
  - JWT auth not supported - requires OpenResty

📌 Step 3: Target Provider

Select target provider:
  1. envoy
  2. kong
  3. apisix
  4. traefik
  5. haproxy
Enter number: 5

🔍 Step 4: Compatibility Check...

✅ Configuration is compatible with haproxy

Warnings:
  - ⚠️ JWT auth requires Lua scripting on haproxy

⚙️  Step 5: Generating Target Configuration...

Output file path [generated/haproxy-config.yaml]: haproxy.cfg

✅ Target configuration written to: haproxy.cfg

📝 Step 6: Migration Report

Generate migration report? [Y/n]: y
Report file path [migration-report.md]:

✅ Migration report written to: migration-report.md

============================================================
✅ Migration Complete!
============================================================

📋 Next Steps:

1. Review generated config: haproxy.cfg
2. Validate syntax:
   haproxy -c -f haproxy.cfg
3. Test in staging environment
4. Deploy to production

⚠️  Remember to address warnings before production deployment!
```

### Non-interaktiver Modus

```bash
$ gal migrate \
    --source-provider nginx \
    --source-config /etc/nginx/nginx.conf \
    --target-provider haproxy \
    --output haproxy.cfg \
    --report migration-report.md

📥 Importing nginx configuration...
✅ Import successful (3 services, 8 routes)

🔍 Checking compatibility with haproxy...
✅ Compatible (1 warning)

⚙️  Generating haproxy configuration...
✅ Written to haproxy.cfg

📝 Generating migration report...
✅ Written to migration-report.md

✅ Migration complete!
```

## Migration Report Format

```markdown
# Migration Report: Nginx → HAProxy

**Date:** 2025-10-18 14:30:00
**GAL Version:** 1.3.0

## Summary

- **Source Provider:** nginx
- **Source Config:** /etc/nginx/nginx.conf
- **Target Provider:** haproxy
- **Target Config:** haproxy.cfg
- **Status:** ✅ Compatible

## Configuration Details

- **Services:** 3
- **Routes:** 8
- **Upstream Targets:** 12

## Import Warnings

- ⚠️ Rate limiting config simplified - manual review recommended
- ⚠️ JWT auth not supported - requires OpenResty

## Compatibility Check

✅ **All features are compatible**

### Warnings

- ⚠️ JWT auth requires Lua scripting on haproxy

### Feature Support

| Feature | Status | Notes |
|---------|--------|-------|
| rate_limiting | ✅ Full | Fully supported |
| passive_health_checks | ✅ Full | Fully supported |
| load_balancing_least_conn | ✅ Full | Fully supported |
| jwt_auth | 🔧 Manual | Requires Lua scripting |

## Next Steps

1. **Review Generated Configuration**
   - Check `haproxy.cfg` for correctness
   - Validate syntax with target provider's tools

2. **Test in Staging**
   - Deploy to staging environment
   - Run integration tests
   - Verify all routes work correctly

3. **Address Warnings/Errors**
   - **jwt_auth**: Use HAProxy Lua scripts or external auth service

4. **Production Deployment**
   - Create rollback plan
   - Deploy during low-traffic window
   - Monitor logs and metrics

## Rollback Plan

If migration fails, revert to original configuration:

```bash
# Restore original nginx config
cp /etc/nginx/nginx.conf.backup /etc/nginx/nginx.conf
# Restart nginx
systemctl restart nginx
```

## References

- [GAL Documentation](https://github.com/pt9912/x-gal)
- [HAProxy Documentation](#haproxy-docs)
- [Migration Guide](docs/guides/MIGRATION.md)
```

## Test Cases

15+ Tests:
- Interactive mode flow
- Non-interactive mode
- Provider selection
- Config import
- Compatibility check
- Report generation
- Error handling (incompatible config)
- Edge cases (no services, empty config)

## Akzeptanzkriterien

- ✅ Interactive CLI workflow (step-by-step)
- ✅ Non-interactive mode (scripted)
- ✅ Provider selection UI
- ✅ Config import with warnings
- ✅ Compatibility check integration
- ✅ Migration report generation (Markdown)
- ✅ Next steps guidance
- ✅ Rollback plan in report
- ✅ CLI Integration
- ✅ 15+ Tests, 85%+ Coverage

## Implementierungs-Reihenfolge

1. **Tag 1-2**: MigrationAssistant class + Interactive prompts
2. **Tag 3-4**: Import + Compatibility Check integration
3. **Tag 5-6**: Config generation + Output
4. **Tag 7-8**: Migration report generation
5. **Tag 9-10**: Non-interactive mode
6. **Tag 11-12**: Next steps + Rollback plan
7. **Tag 13-14**: Tests + Refinement + Documentation

## Nächste Schritte

Nach Completion:
1. Release als v1.3.0 Final
2. User Feedback sammeln
3. v1.4.0 Planung (Cloud Providers)
