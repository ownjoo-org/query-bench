#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt
from rich.table import Table

ORG = "ownjoo-org"
TOOL_PREFIX = "query_"
GITHUB_API = f"https://api.github.com/orgs/{ORG}/repos"
DISCLAIMER_PATH = "/usr/local/share/query-bench/DISCLAIMER.md"

console = Console()


def show_disclaimer_and_confirm() -> None:
    with open(DISCLAIMER_PATH, encoding="utf-8") as f:
        text = f.read()
    console.print(Panel(Markdown(text), title="Disclaimer", border_style="yellow"))
    if not Confirm.ask("Do you acknowledge and accept these terms?", default=False):
        console.print("[red]Not accepted — exiting.[/red]")
        sys.exit(1)


def _api_get(url: str) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "query-bench"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def fetch_query_tools() -> list[dict]:
    tools = []
    page = 1
    try:
        while True:
            data = _api_get(f"{GITHUB_API}?type=public&per_page=100&page={page}")
            if not data:
                break
            for repo in data:
                name = repo["name"]
                if name.startswith(TOOL_PREFIX) and not repo.get("archived"):
                    tools.append(
                        {
                            "name": name,
                            "repo": repo["clone_url"],
                            "description": repo.get("description") or "",
                        }
                    )
            page += 1
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        console.print(f"[bold red]Failed to reach GitHub API:[/bold red] {exc}")
        if isinstance(exc, urllib.error.HTTPError) and exc.code == 403:
            console.print(
                "[yellow]This may be a GitHub API rate limit (60/hr unauthenticated). "
                "Set GITHUB_TOKEN to raise it.[/yellow]"
            )
        sys.exit(1)
    tools.sort(key=lambda t: t["name"])
    return tools


def detect_entrypoint(work_dir: str) -> str | None:
    if os.path.exists(os.path.join(work_dir, "main.py")):
        return "main.py"
    py_files = sorted(
        f
        for f in os.listdir(work_dir)
        if f.endswith(".py") and not f.startswith("_") and f != "setup.py"
    )
    if len(py_files) == 1:
        return py_files[0]
    # Multiple top-level scripts (e.g. helper modules alongside the entry point) —
    # narrow to whichever one is actually runnable as a script.
    runnable = []
    for f in py_files:
        try:
            with open(os.path.join(work_dir, f), encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except OSError:
            continue
        if '__name__ == "__main__"' in content or "__name__ == '__main__'" in content:
            runnable.append(f)
    return runnable[0] if len(runnable) == 1 else None


def main() -> None:
    show_disclaimer_and_confirm()

    console.print("[dim]Fetching available tools from GitHub...[/dim]")
    tools = fetch_query_tools()
    if not tools:
        console.print(f"[red]No {TOOL_PREFIX}* tools found under {ORG}.[/red]")
        sys.exit(1)

    table = Table(title="ownjoo-org query tools")
    table.add_column("#", style="bold cyan", justify="right")
    table.add_column("Tool")
    table.add_column("Description")
    for i, tool in enumerate(tools, start=1):
        table.add_row(str(i), tool["name"], tool["description"])
    console.print(table)

    choice = IntPrompt.ask(
        "Select a tool to clone and set up",
        choices=[str(i) for i in range(1, len(tools) + 1)],
    )
    tool = tools[choice - 1]

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

    entrypoint = detect_entrypoint(work_dir)
    hint = (
        f"Try: [bold]python {entrypoint} --help[/bold]"
        if entrypoint
        else "Check the repo's README for how to run it."
    )
    console.print(f"\n[bold green]Ready.[/bold green] You're in {work_dir}.\n{hint}\n")

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
