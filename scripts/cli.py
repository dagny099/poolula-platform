#!/usr/bin/env python3
"""
Poolula Platform CLI

Quick Win command-line interface for common operations.
"""

import click
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@click.group()
@click.version_option(version="0.1.0", prog_name="poolula")
def cli():
    """
    Poolula Platform CLI - Manage your rental property business.

    Examples:
        poolula chat                           # Launch interactive chatbot
        poolula import-csv transactions.csv    # Import bank transactions
        poolula review-transactions            # Categorize uncategorized transactions
        poolula list-properties                # Show all properties
        poolula health                         # Check system health
    """
    pass


@cli.command()
def chat():
    """Launch interactive chatbot session."""
    click.echo("🤖 Poolula Chatbot")
    click.echo("=" * 50)
    click.echo()
    click.echo("Ask me questions about your business!")
    click.echo("Examples:")
    click.echo("  - What was my revenue last month?")
    click.echo("  - Show me all utilities expenses")
    click.echo("  - What's my depreciable basis?")
    click.echo()
    click.echo("Type 'exit' or 'quit' to end the session.")
    click.echo("=" * 50)
    click.echo()

    # Import chatbot modules
    try:
        from apps.chatbot.rag_system import RAGSystem
        from apps.chatbot.config import Config

        config = Config()
        rag_system = RAGSystem(config)

        session_id = f"cli_{click.get_current_context().params.get('session_id', 'default')}"

        while True:
            try:
                user_input = click.prompt(click.style("\nYou", fg="cyan"), type=str)

                if user_input.lower() in ["exit", "quit", "q"]:
                    click.echo("\n👋 Goodbye!")
                    break

                with click.progressbar(length=1, label="Thinking...") as bar:
                    response, sources = rag_system.query(user_input, session_id=session_id)
                    bar.update(1)

                click.echo()
                click.secho("Assistant:", fg="green", bold=True)
                click.echo(response)

                if sources:
                    click.echo()
                    click.secho("Sources:", fg="yellow", dim=True)
                    for i, source in enumerate(sources, 1):
                        course = source.get('course_title', 'Unknown')
                        lesson = source.get('lesson_number', 'N/A')
                        click.echo(f"  [{i}] {course} - Lesson {lesson}", dim=True)

            except KeyboardInterrupt:
                click.echo("\n\n👋 Goodbye!")
                break
            except Exception as e:
                click.secho(f"\n❌ Error: {str(e)}", fg="red")

    except ImportError as e:
        click.secho("❌ Chatbot not available. Install RAG dependencies:", fg="red")
        click.echo("   uv sync --group rag")
        click.echo(f"\n   Error: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--property-id', help='Property ID to associate transactions with')
@click.option('--dry-run', is_flag=True, help='Preview import without saving')
def import_csv(csv_file: str, property_id: Optional[str], dry_run: bool):
    """
    Import transactions from a CSV file.

    Supports Airbnb and bank statement CSV formats.

    \b
    Examples:
        poolula import-csv airbnb_nov_2024.csv
        poolula import-csv bank_statement.csv --property-id 12345678-1234-...
        poolula import-csv transactions.csv --dry-run
    """
    click.echo(f"📄 Importing transactions from: {csv_file}")

    if dry_run:
        click.secho("🔍 DRY RUN MODE - No changes will be saved", fg="yellow")

    click.echo()

    # TODO: Implement CSV import logic in Phase 2 Week 4
    click.secho("⚠️  CSV import feature coming in Phase 2 Week 4", fg="yellow")
    click.echo()
    click.echo("For now, use the API:")
    click.echo(f"  curl -X POST http://localhost:8082/api/v1/transactions/import \\")
    click.echo(f"    -F 'file=@{csv_file}'")

    if property_id:
        click.echo(f"    -F 'property_id={property_id}'")


@cli.command()
@click.option('--category', help='Filter by category (e.g., UNCATEGORIZED)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--limit', default=20, help='Number of transactions to review')
def review_transactions(category: Optional[str], start_date: Optional[str], limit: int):
    """
    Interactively review and categorize transactions.

    \b
    Examples:
        poolula review-transactions
        poolula review-transactions --category UNCATEGORIZED
        poolula review-transactions --start-date 2024-11-01 --limit 10
    """
    click.echo("📝 Review Transactions")
    click.echo("=" * 50)

    # TODO: Implement transaction review workflow in Phase 2 Week 4
    click.secho("\n⚠️  Transaction review workflow coming in Phase 2 Week 4", fg="yellow")
    click.echo()
    click.echo("For now, use the chatbot:")
    click.echo("  poolula chat")
    click.echo('  > "Show me uncategorized transactions"')


@cli.command()
@click.option('--status', help='Filter by status (ACTIVE, INACTIVE, etc.)')
def list_properties(status: Optional[str]):
    """
    List all properties.

    \b
    Examples:
        poolula list-properties
        poolula list-properties --status ACTIVE
    """
    import requests

    api_url = "http://localhost:8082/api/v1/properties"
    params = {}
    if status:
        params['status'] = status

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()

        properties = response.json()

        if not properties:
            click.echo("No properties found.")
            return

        click.echo(f"\n🏠 Found {len(properties)} propert{'y' if len(properties) == 1 else 'ies'}:\n")

        for prop in properties:
            click.secho(f"  {prop['address']}", fg="cyan", bold=True)
            click.echo(f"    ID: {prop['id']}")
            click.echo(f"    Status: {prop['status']}")
            click.echo(f"    Acquisition: {prop['acquisition_date']}")
            click.echo(f"    Purchase Price: ${prop['purchase_price_total']}")

            if prop.get('placed_in_service'):
                click.echo(f"    In Service: {prop['placed_in_service']}")

            # Calculate depreciable basis
            building = float(prop.get('building_basis', 0))
            ffe = float(prop.get('ffe_basis', 0))
            depreciable = building + ffe

            if depreciable > 0:
                click.echo(f"    Depreciable Basis: ${depreciable:,.2f}")

            click.echo()

    except requests.exceptions.ConnectionError:
        click.secho("❌ Cannot connect to API server.", fg="red")
        click.echo("\nStart the API server:")
        click.echo("  uv run uvicorn apps.api.main:app --reload --port 8082")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        click.secho(f"❌ Error: {str(e)}", fg="red")
        sys.exit(1)


@cli.command()
@click.option('--property-id', help='Show basis for specific property')
def show_basis(property_id: Optional[str]):
    """
    Show depreciable basis for properties.

    \b
    Examples:
        poolula show-basis
        poolula show-basis --property-id 12345678-1234-...
    """
    import requests

    api_url = "http://localhost:8082/api/v1/properties"

    if property_id:
        api_url = f"{api_url}/{property_id}"

    try:
        response = requests.get(api_url)
        response.raise_for_status()

        data = response.json()
        properties = [data] if property_id else data

        if not properties:
            click.echo("No properties found.")
            return

        click.echo("\n📊 Depreciable Basis Report\n")
        click.echo("=" * 70)

        total_land = 0
        total_building = 0
        total_ffe = 0

        for prop in properties:
            land = float(prop.get('land_basis', 0))
            building = float(prop.get('building_basis', 0))
            ffe = float(prop.get('ffe_basis', 0))
            depreciable = building + ffe

            total_land += land
            total_building += building
            total_ffe += ffe

            click.secho(f"\n{prop['address']}", fg="cyan", bold=True)
            click.echo(f"  Land Basis:       ${land:>12,.2f}  (not depreciable)")
            click.echo(f"  Building Basis:   ${building:>12,.2f}  (27.5 years)")
            click.echo(f"  FFE Basis:        ${ffe:>12,.2f}  (5 years)")
            click.echo(f"  " + "-" * 40)
            click.secho(f"  Depreciable:      ${depreciable:>12,.2f}", fg="green", bold=True)

            if prop.get('placed_in_service'):
                click.echo(f"  In Service:       {prop['placed_in_service']}")

        if len(properties) > 1:
            total_depreciable = total_building + total_ffe

            click.echo("\n" + "=" * 70)
            click.secho("TOTAL (All Properties)", fg="yellow", bold=True)
            click.echo(f"  Land Basis:       ${total_land:>12,.2f}")
            click.echo(f"  Building Basis:   ${total_building:>12,.2f}")
            click.echo(f"  FFE Basis:        ${total_ffe:>12,.2f}")
            click.echo(f"  " + "-" * 40)
            click.secho(f"  Depreciable:      ${total_depreciable:>12,.2f}", fg="green", bold=True)
            click.echo()

    except requests.exceptions.ConnectionError:
        click.secho("❌ Cannot connect to API server.", fg="red")
        click.echo("\nStart the API server:")
        click.echo("  uv run uvicorn apps.api.main:app --reload --port 8082")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        click.secho(f"❌ Error: {str(e)}", fg="red")
        sys.exit(1)


@cli.command()
def health():
    """Check system health."""
    import requests

    click.echo("🏥 Poolula Platform Health Check")
    click.echo("=" * 50)
    click.echo()

    # Check API health
    try:
        response = requests.get("http://localhost:8082/health", timeout=5)
        response.raise_for_status()

        health_data = response.json()

        click.secho("✅ API Server:", fg="green", bold=True)
        click.echo(f"   Status: {health_data.get('status', 'unknown')}")
        click.echo(f"   Version: {health_data.get('api_version', 'unknown')}")
        click.echo(f"   Database: {'✅ Connected' if health_data.get('database_connected') else '❌ Disconnected'}")
        click.echo()

    except requests.exceptions.ConnectionError:
        click.secho("❌ API Server: Not running", fg="red")
        click.echo("   Start with: uv run uvicorn apps.api.main:app --reload --port 8082")
        click.echo()

    # Check database
    try:
        from core.database.connection import get_session
        from sqlmodel import text

        session = next(get_session())
        session.exec(text("SELECT 1"))

        click.secho("✅ Database:", fg="green", bold=True)
        click.echo("   SQLite connection successful")
        click.echo()

    except Exception as e:
        click.secho("❌ Database: Connection failed", fg="red")
        click.echo(f"   Error: {str(e)}")
        click.echo()

    # Check chatbot dependencies
    try:
        import anthropic
        import chromadb

        click.secho("✅ Chatbot Dependencies:", fg="green", bold=True)
        click.echo("   anthropic: installed")
        click.echo("   chromadb: installed")
        click.echo()

    except ImportError as e:
        click.secho("⚠️  Chatbot Dependencies: Not installed", fg="yellow")
        click.echo("   Install with: uv sync --group rag")
        click.echo()

    click.echo("=" * 50)


if __name__ == '__main__':
    cli()
