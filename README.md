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
docker run --rm -it query-bench
```

You'll first see a red-bordered [disclaimer](DISCLAIMER.md) (no warranty, no liability, no
security guarantee — see below) that you must explicitly accept to continue. After that, a
green-bordered menu queries the GitHub API live for every public `query_*` repo under `ownjoo-org`
and lists them — no rebuild needed when a new tool is added org-side. A `0` row is always
available to skip straight to a shell with nothing cloned.

Pick a tool and it clones the repo into your home directory inside the container, runs
`pip install -r requirements.txt`, lists the tool's `.py` files, and execs into an interactive
shell in that directory:

- **Exactly one `.py` file** (the common case): unambiguous entry point, so it just runs
  `python <file>.py -h` for you and shows the real usage output immediately.
- **Multiple `.py` files**: prints a `Try: python <file>.py --help` hint instead — the entry point
  is auto-detected (`main.py` if present, otherwise whichever file has an
  `if __name__ == "__main__":` guard), but not run automatically since which file matters more
  when there's more than one.

The GitHub API is unauthenticated by default (60 requests/hr per IP). If you're hitting that
limit, pass a token: `docker run --rm -it -e GITHUB_TOKEN=ghp_... query-bench`.

## Host isolation & cleanup

**Nothing this container does can reach the host filesystem.** Docker containers get their own
isolated root filesystem via Linux namespaces; unless you explicitly add `-v`/`--mount`, there is
no path inside the container leading to any host file — not restricted, genuinely absent. The
documented `docker run` command above has no mounts, no `--privileged`, and no elevated
capabilities (`--cap-add`) — none are ever needed for anything this container does (clone a repo,
pip install, run a Python script). It also runs as a non-root user (`toolrunner`) as defense in
depth. None of `-v`/`--mount`, `--privileged`, a Docker-socket mount, or `--net=host`/`--pid=host`
(the ways this guarantee could be broken) appear anywhere in this repo. Verify yourself:

```bash
docker run --rm query-bench sh -c 'ls / ; whoami'         # no host paths visible, non-root
docker inspect <container_id> --format '{{json .Mounts}}' # empty mount list
```

**Cleanup is `--rm`, not just stopping.** `docker stop` only halts the process — the container's
writable layer (the cloned repo, installed packages, anything typed at a tool's prompts, including
API credentials) still sits on disk until the container is actually *removed*. The documented run
command uses `--rm`, so Docker removes that layer automatically the moment the shell exits —
nothing from a session survives past that point, no separate cleanup step required.

This is distinct from **the image** (`query-bench:latest` itself — Python, git, `menu.py`,
`DISCLAIMER.md`): that's static, public, identical for every user, and persists in your local
Docker image cache after the container exits, same as any image you `docker pull` — that's normal
and contains nothing session- or customer-specific. Remove it explicitly with `docker rmi
query-bench` if you don't want it cached locally.

**Want the container instance to persist instead?** Drop `--rm`:

```bash
docker run -it query-bench
```

The stopped container (and its writable layer — the clone, installed packages, anything typed)
then sticks around on disk so you can `docker start -ai <container>` to resume it later, or
`docker cp <container>:/path ./local` to pull files out. You're opting back into the state
described above though — including that anything sensitive typed at a prompt (e.g. API
credentials) remains on disk until you `docker rm` it yourself.

**Want results to survive on purpose?** Mount a local directory at `/output` (created and owned by
the non-root user at build time, so this works cleanly whether or not anything's mounted there):

```bash
docker run --rm -it -v "$(pwd)/output:/output" query-bench
```

Point whichever tool you pick at `/output` for its results (e.g. `python main.py --output
/output/results.json`, or `cd /output` before running it, depending on that tool's own CLI). The
menu tells you after setup whether `/output` is actually mounted. This is the one deliberate,
opt-in exception to "nothing persists" — everything else about the isolation above still holds.

## Disclaimer

[`DISCLAIMER.md`](DISCLAIMER.md) is shown and must be explicitly accepted (`y`) before the menu
loads — declining exits immediately without cloning or installing anything. It draws a clear line:
this container and the `query_*` tools it clones are ownjoo.org's own code, but those tools pull in
numerous third-party libraries that aren't maintained by ownjoo.org and aren't under our control —
no warranty, no liability, and no guarantee of security for any of it, plus a recommendation that
your security team independently evaluate any tool before use. This is a plain-language disclaimer,
not legal advice — have it reviewed by counsel before relying on it.

## What's in it

- `git`, `python-3.14` + a venv with [`oj-toolkit`](https://github.com/ownjoo-org/utils) (this
  org's own console-formatting library — `Box`/`Table`/`Output` for the menu UI itself; not
  restricted to the target tools' own dependencies, which get installed fresh into the same venv
  per-tool). Building this menu found and fixed three real bugs in `oj-toolkit` along the way
  (a `Table` column-count bug, a `Box` titled-border width mismatch, and added the `border_color`
  feature this menu's red/green borders use) — released as 0.2.3, 0.2.4, and 0.3.0.
- Non-root by default (`toolrunner` user); the venv is `chown`'d to that user at build time so
  runtime `pip install` (of whatever tool you pick) actually has write permission
- `PYTHONUNBUFFERED=1` — without it, this menu's own status messages could print out of order
  relative to `git`/`pip`'s output, since Python block-buffers stdout when it isn't a TTY

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
