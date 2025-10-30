"""
OSINT Investigator - Command Line Interface
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from dotenv import load_dotenv

from .modules.email_investigator import EmailInvestigator
from .modules.phone_investigator import PhoneInvestigator
from .modules.username_investigator import UsernameInvestigator
from .utils.reporter import Reporter
from .utils.logger import setup_logging

# Load environment variables
load_dotenv()

console = Console()


class OSINTInvestigator:
    """Main OSINT investigation orchestrator"""

    def __init__(self):
        self.email_investigator = EmailInvestigator()
        self.phone_investigator = PhoneInvestigator()
        self.username_investigator = UsernameInvestigator()
        self.reporter = Reporter()

    async def investigate_email(self, email: str) -> dict:
        """Investigate an email address"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"[cyan]Investigating email: {email}...", total=None)
            result = await self.email_investigator.investigate(email)
            progress.update(task, completed=True)
        return result

    async def investigate_phone(self, phone: str) -> dict:
        """Investigate a phone number"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"[cyan]Investigating phone: {phone}...", total=None)
            result = await self.phone_investigator.investigate(phone)
            progress.update(task, completed=True)
        return result

    async def investigate_username(self, username: str) -> dict:
        """Investigate a username"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"[cyan]Investigating username: {username}...", total=None)
            result = await self.username_investigator.investigate(username)
            progress.update(task, completed=True)
        return result


def print_banner():
    """Print application banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║              🔍 OSINT INVESTIGATOR 🔍                     ║
    ║                                                           ║
    ║       Comprehensive Open Source Intelligence Tool        ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_results(results: dict):
    """Pretty print investigation results"""
    target = results.get('target', 'Unknown')
    inv_type = results.get('type', 'unknown')

    # Summary panel
    summary = f"""
    [bold]Target:[/bold] {target}
    [bold]Type:[/bold] {inv_type.upper()}
    [bold]Modules Run:[/bold] {results.get('modules_run', 0)}
    [bold]Successful Checks:[/bold] {results.get('successful_checks', 0)}
    """

    console.print(Panel(summary, title="📊 Investigation Summary", border_style="green"))

    # Results table
    table = Table(title="🔎 Detailed Results", show_header=True, header_style="bold magenta")
    table.add_column("Module", style="cyan")
    table.add_column("Source", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Key Findings", style="white")

    for result in results.get('results', []):
        if isinstance(result, dict):
            module = result.get('module', 'Unknown')
            source = result.get('source', 'Unknown')
            status = result.get('status', 'unknown')
            data = result.get('data', {})

            # Extract key findings
            findings = []
            if inv_type == 'email':
                if 'platforms_found' in data:
                    findings.append(f"Found on {data['platforms_found']} platforms")
                if 'breach_count' in data:
                    findings.append(f"{data['breach_count']} breaches")
                if 'is_compromised' in data and data['is_compromised']:
                    findings.append("⚠️ COMPROMISED")
                if 'score' in data:
                    findings.append(f"Score: {data['score']}")

            elif inv_type == 'phone':
                if 'valid' in data:
                    findings.append(f"Valid: {data['valid']}")
                if 'carrier' in data:
                    findings.append(f"Carrier: {data['carrier']}")
                if 'country' in data:
                    findings.append(f"Country: {data['country']}")
                if 'line_type' in data:
                    findings.append(f"Type: {data['line_type']}")

            elif inv_type == 'username':
                if 'found_count' in data:
                    findings.append(f"Found on {data['found_count']} sites")
                if 'unique_accounts_found' in results:
                    findings.append(f"Total unique: {results['unique_accounts_found']}")

            findings_str = ", ".join(findings) if findings else "See detailed report"

            status_emoji = {
                'success': '✅',
                'error': '❌',
                'partial': '⚠️',
                'skipped': '⏭️'
            }

            table.add_row(
                module,
                source,
                f"{status_emoji.get(status, '❓')} {status}",
                findings_str
            )

    console.print(table)

    # Show accounts found for username
    if inv_type == 'username' and 'accounts' in results:
        accounts = results['accounts']
        if accounts:
            console.print(f"\n[bold green]Found {len(accounts)} accounts:[/bold green]")
            for i, account in enumerate(accounts[:20], 1):  # Show first 20
                site = account.get('site', account.get('platform', 'Unknown'))
                url = account.get('url', 'N/A')
                console.print(f"  {i}. [cyan]{site}[/cyan]: {url}")

            if len(accounts) > 20:
                console.print(f"\n  ... and {len(accounts) - 20} more (see full report)")


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """OSINT Investigator - Comprehensive OSINT Toolkit"""
    pass


@cli.command()
@click.argument('email')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', type=click.Choice(['json', 'html', 'both']), default='both', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def email(email: str, output: Optional[str], format: str, verbose: bool):
    """Investigate an email address"""
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)

    print_banner()
    console.print(f"\n[bold cyan]🔍 Starting email investigation: {email}[/bold cyan]\n")

    investigator = OSINTInvestigator()
    results = asyncio.run(investigator.investigate_email(email))

    print_results(results)

    # Save report
    if output or format:
        output_path = output or f"./output/email_{email.replace('@', '_at_')}"
        investigator.reporter.generate_report(results, output_path, format)
        console.print(f"\n[green]✅ Report saved to: {output_path}[/green]")


@cli.command()
@click.argument('phone')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', type=click.Choice(['json', 'html', 'both']), default='both', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def phone(phone: str, output: Optional[str], format: str, verbose: bool):
    """Investigate a phone number"""
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)

    print_banner()
    console.print(f"\n[bold cyan]📱 Starting phone investigation: {phone}[/bold cyan]\n")

    investigator = OSINTInvestigator()
    results = asyncio.run(investigator.investigate_phone(phone))

    print_results(results)

    # Save report
    if output or format:
        output_path = output or f"./output/phone_{phone.replace('+', '').replace(' ', '_')}"
        investigator.reporter.generate_report(results, output_path, format)
        console.print(f"\n[green]✅ Report saved to: {output_path}[/green]")


@cli.command()
@click.argument('username')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', type=click.Choice(['json', 'html', 'both']), default='both', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def username(username: str, output: Optional[str], format: str, verbose: bool):
    """Investigate a username"""
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)

    print_banner()
    console.print(f"\n[bold cyan]👤 Starting username investigation: {username}[/bold cyan]\n")

    investigator = OSINTInvestigator()
    results = asyncio.run(investigator.investigate_username(username))

    print_results(results)

    # Save report
    if output or format:
        output_path = output or f"./output/username_{username}"
        investigator.reporter.generate_report(results, output_path, format)
        console.print(f"\n[green]✅ Report saved to: {output_path}[/green]")


@cli.command()
@click.option('--email', '-e', multiple=True, help='Email addresses to investigate')
@click.option('--phone', '-p', multiple=True, help='Phone numbers to investigate')
@click.option('--username', '-u', multiple=True, help='Usernames to investigate')
@click.option('--output', '-o', help='Output directory')
@click.option('--format', '-f', type=click.Choice(['json', 'html', 'both']), default='both', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def batch(email: tuple, phone: tuple, username: tuple, output: Optional[str], format: str, verbose: bool):
    """Batch investigation of multiple targets"""
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)

    print_banner()

    investigator = OSINTInvestigator()
    all_results = []

    # Process emails
    for em in email:
        console.print(f"\n[bold cyan]🔍 Investigating email: {em}[/bold cyan]\n")
        result = asyncio.run(investigator.investigate_email(em))
        all_results.append(result)
        print_results(result)

    # Process phones
    for ph in phone:
        console.print(f"\n[bold cyan]📱 Investigating phone: {ph}[/bold cyan]\n")
        result = asyncio.run(investigator.investigate_phone(ph))
        all_results.append(result)
        print_results(result)

    # Process usernames
    for un in username:
        console.print(f"\n[bold cyan]👤 Investigating username: {un}[/bold cyan]\n")
        result = asyncio.run(investigator.investigate_username(un))
        all_results.append(result)
        print_results(result)

    # Save batch report
    if output or format:
        output_path = output or "./output/batch_investigation"
        for i, result in enumerate(all_results, 1):
            target = result.get('target', f'target_{i}')
            inv_type = result.get('type', 'unknown')
            file_path = f"{output_path}_{inv_type}_{target}"
            investigator.reporter.generate_report(result, file_path, format)

        console.print(f"\n[green]✅ {len(all_results)} reports saved to: {output_path}*[/green]")


@cli.command()
def interactive():
    """Interactive mode"""
    print_banner()

    console.print("\n[bold yellow]Interactive OSINT Investigator[/bold yellow]")
    console.print("Commands: email, phone, username, batch, quit\n")

    investigator = OSINTInvestigator()

    while True:
        try:
            command = console.input("[bold cyan]osint>[/bold cyan] ").strip()

            if command.lower() in ['quit', 'exit', 'q']:
                console.print("[yellow]Goodbye![/yellow]")
                break

            elif command.startswith('email '):
                email_addr = command.split(' ', 1)[1]
                result = asyncio.run(investigator.investigate_email(email_addr))
                print_results(result)

            elif command.startswith('phone '):
                phone_num = command.split(' ', 1)[1]
                result = asyncio.run(investigator.investigate_phone(phone_num))
                print_results(result)

            elif command.startswith('username '):
                user = command.split(' ', 1)[1]
                result = asyncio.run(investigator.investigate_username(user))
                print_results(result)

            elif command == 'help':
                console.print("""
[bold]Available commands:[/bold]
  email <email>       - Investigate an email address
  phone <phone>       - Investigate a phone number
  username <user>     - Investigate a username
  help                - Show this help
  quit/exit/q         - Exit interactive mode
                """)

            else:
                console.print("[red]Unknown command. Type 'help' for available commands.[/red]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'quit' to exit[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


if __name__ == '__main__':
    cli()
