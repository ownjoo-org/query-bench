#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request

from oj_toolkit.console import Box, Output, Table

ORG = "ownjoo-org"
TOOL_PREFIX = "query_"
GITHUB_API = f"https://api.github.com/orgs/{ORG}/repos"
DISCLAIMER_PATH = "/usr/local/share/query-bench/DISCLAIMER.md"

out = Output()


def confirm(prompt: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        resp = input(f"{prompt} {suffix}: ").strip().lower()
        if not resp:
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        out.out("Please enter y or n.")


def choose(prompt: str, n: int) -> int:
    while True:
        resp = input(f"{prompt} [1-{n}]: ").strip()
        if resp.isdigit() and 1 <= int(resp) <= n:
            return int(resp)
        out.out(f"Please enter a number between 1 and {n}.")


def show_disclaimer_and_confirm() -> None:
    with open(DISCLAIMER_PATH, encoding="utf-8") as f:
        raw = f.read()

    # Plain-text rendering: strip Markdown syntax rather than parsing it.
    text = re.sub(r"^#.*\n+", "", raw.strip())
    text = text.replace("**", "")

    box = Box(style="auto", title="Disclaimer", padding=1)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for i, para in enumerate(paragraphs):
        if i > 0:
            box.add_line("")
        for line in textwrap.wrap(" ".join(para.split()), width=76):
            box.add_line(line)
    box.out()

    if not confirm("Do you acknowledge and accept these terms?", default=False):
        out.out_red("Not accepted — exiting.")
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
        out.err_red(f"Failed to reach GitHub API: {exc}")
        if isinstance(exc, urllib.error.HTTPError) and exc.code == 403:
            out.err_yellow(
                "This may be a GitHub API rate limit (60/hr unauthenticated). "
                "Set GITHUB_TOKEN to raise it."
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

    out.out("Fetching available tools from GitHub...")
    tools = fetch_query_tools()
    if not tools:
        out.out_red(f"No {TOOL_PREFIX}* tools found under {ORG}.")
        sys.exit(1)

    table = Table(headers=["#", "Tool", "Description"], style="auto")
    for i, tool in enumerate(tools, start=1):
        table.add_row(i, tool["name"], tool["description"])
    table.out()

    choice = choose("Select a tool to clone and set up", len(tools))
    tool = tools[choice - 1]

    work_dir = os.path.expanduser(f"~/{tool['name']}")
    out.out(f"\nCloning {tool['repo']} -> {work_dir}")
    subprocess.run(["git", "clone", "--depth", "1", tool["repo"], work_dir], check=True)

    os.chdir(work_dir)

    requirements = os.path.join(work_dir, "requirements.txt")
    if os.path.exists(requirements):
        out.out("Installing requirements.txt")
        subprocess.run(["pip", "install", "--no-cache-dir", "-r", requirements], check=True)
    else:
        out.out_yellow("No requirements.txt found — skipping pip install")

    entrypoint = detect_entrypoint(work_dir)
    hint = (
        f"Try: python {entrypoint} --help"
        if entrypoint
        else "Check the repo's README for how to run it."
    )
    if os.path.ismount("/output"):
        output_note = "/output is mounted — write results there to keep them after this container exits."
    else:
        output_note = (
            "No host directory is mounted at /output, so anything you write inside this "
            "container is lost when it exits. Restart with -v <local-dir>:/output to keep "
            "results."
        )
    out.out_green(f"\nReady. You're in {work_dir}.")
    out.out(f"{hint}\n{output_note}\n")

    # os.execvp replaces the process image immediately, bypassing Python's
    # normal interpreter shutdown -- anything still sitting in stdout's
    # buffer (oj_toolkit's Output defaults to flush=False) would be lost
    # rather than ever reaching the terminal.
    sys.stdout.flush()

    shell = os.environ.get("SHELL", "/bin/sh")
    os.execvp(shell, [shell])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        out.err_red(f"Command failed: {exc}")
        sys.exit(exc.returncode)
    except KeyboardInterrupt:
        sys.exit(130)
