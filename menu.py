#!/usr/bin/env python3
import os
import subprocess
import sys

from rich.console import Console
from rich.prompt import IntPrompt
from rich.table import Table

TOOLS = [
    {
        "name": "query_checkmarx_one",
        "repo": "https://github.com/ownjoo-org/query_checkmarx_one.git",
        "entrypoint": "main.py",
        "description": "Query Checkmarx One SAST/SCA findings",
    },
    {
        "name": "query_kibana",
        "repo": "https://github.com/ownjoo-org/query_kibana.git",
        "entrypoint": "main.py",
        "description": "Query Kibana",
    },
    {
        "name": "query_radiant_vds",
        "repo": "https://github.com/ownjoo-org/query_radiant_vds.git",
        "entrypoint": "main.py",
        "description": "Query Radiant Logic IDM (ADAP/REST endpoint)",
    },
    {
        "name": "query_sysdig",
        "repo": "https://github.com/ownjoo-org/query_sysdig.git",
        "entrypoint": "main.py",
        "description": "Query Sysdig",
    },
    {
        "name": "query_zafran",
        "repo": "https://github.com/ownjoo-org/query_zafran.git",
        "entrypoint": "qz.py",
        "description": "Query Zafran assets/findings (ZQL), local SQLite join + SQL query mode",
    },
]

console = Console()


def main() -> None:
    table = Table(title="ownjoo-org query tools")
    table.add_column("#", style="bold cyan", justify="right")
    table.add_column("Tool")
    table.add_column("Description")
    for i, tool in enumerate(TOOLS, start=1):
        table.add_row(str(i), tool["name"], tool["description"])
    console.print(table)

    choice = IntPrompt.ask(
        "Select a tool to clone and set up",
        choices=[str(i) for i in range(1, len(TOOLS) + 1)],
    )
    tool = TOOLS[choice - 1]

    work_dir = os.path.expanduser(f"~/{tool['name']}")
    console.print(f"\n[bold]Cloning[/bold] {tool['repo']} -> {work_dir}")
    subprocess.run(["git", "clone", "--depth", "1", tool["repo"], work_dir], check=True)

    os.chdir(work_dir)

    requirements = os.path.join(work_dir, "requirements.txt")
    if os.path.exists(requirements):
        console.print("[bold]Installing[/bold] requirements.txt")
        subprocess.run(["pip", "install", "--no-cache-dir", "-r", requirements], check=True)
    else:
        console.print("[yellow]No requirements.txt found — skipping pip install[/yellow]")

    console.print(
        f"\n[bold green]Ready.[/bold green] You're in {work_dir}.\n"
        f"Try: [bold]python {tool['entrypoint']} --help[/bold]\n"
    )

    shell = os.environ.get("SHELL", "/bin/sh")
    os.execvp(shell, [shell])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        console.print(f"[bold red]Command failed:[/bold red] {exc}")
        sys.exit(exc.returncode)
    except KeyboardInterrupt:
        sys.exit(130)
