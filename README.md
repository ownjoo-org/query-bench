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

You'll see a numbered menu of available tools. Pick one; it clones the repo into your home
directory inside the container, runs `pip install -r requirements.txt`, and execs into an
interactive shell in that directory. From there, e.g.:

```bash
python main.py --help
```

(Entry point filename varies per tool — the menu tells you which one after setup.)

## What's in it

- `git`, `python-3.14` + a venv with `rich` (for the menu UI itself; not restricted to the target
  tools' own dependencies, which get installed fresh into the same venv per-tool)
- Non-root by default (`toolrunner` user); the venv is `chown`'d to that user at build time so
  runtime `pip install` (of whatever tool you pick) actually has write permission

## Tools in the menu

| Tool | Entry point | Notes |
|---|---|---|
| [query_checkmarx_one](https://github.com/ownjoo-org/query_checkmarx_one) | `main.py` | Checkmarx One SAST/SCA findings |
| [query_kibana](https://github.com/ownjoo-org/query_kibana) | `main.py` | |
| [query_radiant_vds](https://github.com/ownjoo-org/query_radiant_vds) | `main.py` | Radiant Logic IDM (ADAP/REST endpoint) |
| [query_sysdig](https://github.com/ownjoo-org/query_sysdig) | `main.py` | |
| [query_zafran](https://github.com/ownjoo-org/query_zafran) | `qz.py` | Assets/findings via ZQL, local SQLite join + SQL query mode |

`query_ionix_async` is intentionally excluded — it's a private repo, so a customer container
without their own GitHub credentials can't clone it. Public `query_*` tools not yet on this list
can be added to `TOOLS` in [`menu.py`](menu.py).

## Adding a tool to the menu

Add an entry to the `TOOLS` list in `menu.py`:

```python
{
    "name": "query_something",
    "repo": "https://github.com/ownjoo-org/query_something.git",
    "entrypoint": "main.py",
    "description": "One-line description",
},
```

The only requirement is that the target repo installs cleanly via `pip install -r requirements.txt`
(all current entries do — three of them previously didn't, due to a stale dependency reference;
see git history / [ownjoo-org/utils](https://github.com/ownjoo-org/utils) for context).
