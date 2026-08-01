# query-bench

An interactive menu container for customers who don't have git or Python set up locally (or are
otherwise blocked) but need to run one of the [ownjoo-org](https://github.com/ownjoo-org)
`query_*` API tools. `docker run` it, pick a tool from the menu, and it clones the repo, installs
its dependencies, and drops you into a shell already `cd`'d into it — ready to run.

Base: [Chainguard Wolfi](https://github.com/wolfi-dev/os), matching the same supply-chain-hardened
approach as [`packet-bench`](https://github.com/ownjoo-org/packet-bench).

## Pull

```bash
docker pull speedimusmaximus/query-bench
```

Published automatically by [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml)
on every push to `main` (tag `latest`) and on `v*` tags (semver tags). Requires the
`DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` repo secrets to be configured before the workflow can push.
Images are cosign-signed and ship an attached SBOM.

## Build

```bash
docker build -t query-bench .
```

## Run

```bash
docker run -it query-bench
```

You'll first see a [disclaimer](DISCLAIMER.md) (no warranty, no liability, no security guarantee —
see below) that you must explicitly accept to continue. After that, the menu queries the GitHub
API live for every public `query_*` repo under `ownjoo-org` and lists them — no rebuild needed
when a new tool is added org-side. Pick one; it clones the repo into your home directory inside
the container, runs `pip install -r requirements.txt`, and execs into an interactive shell in that
directory, having auto-detected the tool's entry point (`main.py` if present, otherwise whichever
top-level `.py` file has an `if __name__ == "__main__":` guard). From there, e.g.:

```bash
python main.py --help
```

The GitHub API is unauthenticated by default (60 requests/hr per IP). If you're hitting that
limit, pass a token: `docker run -it -e GITHUB_TOKEN=ghp_... query-bench`.

## Disclaimer

[`DISCLAIMER.md`](DISCLAIMER.md) is shown and must be explicitly accepted (`y`) before the menu
loads — declining exits immediately without cloning or installing anything. It covers no
warranty, no liability, and no guarantee of security for this container or the third-party tools
and dependencies it clones (which aren't under our control), plus a recommendation that your
security team independently evaluate any tool before use. This is a plain-language disclaimer, not
legal advice — have it reviewed by counsel before relying on it.

## What's in it

- `git`, `python-3.14` + a venv with `rich` (for the menu UI itself; not restricted to the target
  tools' own dependencies, which get installed fresh into the same venv per-tool)
- Non-root by default (`toolrunner` user); the venv is `chown`'d to that user at build time so
  runtime `pip install` (of whatever tool you pick) actually has write permission

## Tool discovery

The menu is dynamic — it lists every public, non-archived repo under `ownjoo-org` whose name
starts with `query_`, fetched live via the GitHub API (see `fetch_query_tools()` in
[`menu.py`](menu.py)). Nothing to maintain here when a new query tool is added or removed org-side.

Private `query_*` repos (e.g. `query_ionix_async`) never appear — the unauthenticated API call
simply can't see them, so a customer without their own GitHub credentials can't be shown a tool
they couldn't clone anyway.

The only requirement for a tool to work through this menu is that it installs cleanly via
`pip install -r requirements.txt`. Three tools previously didn't, due to a stale dependency
reference; see git history / [ownjoo-org/utils](https://github.com/ownjoo-org/utils) for context.
Since the list is now fetched live, newly-added `query_*` repos aren't pre-vetted — if one fails to
install or run, that's a bug in that tool's own repo, not this container.
