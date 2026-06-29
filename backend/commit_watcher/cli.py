"""Typer CLI over the shared service layer."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
import yaml

from . import services
from .core import config_io
from .core.schemas import ChannelCreate, WatchCreate
from .db import init_db

app = typer.Typer(help="commit-watcher: poll any GitHub repo, filter commits, notify.")
watch_app = typer.Typer(help="Manage watches.")
channel_app = typer.Typer(help="Manage channels.")
config_app = typer.Typer(help="Import/export YAML config.")
app.add_typer(watch_app, name="watch")
app.add_typer(channel_app, name="channel")
app.add_typer(config_app, name="config")


@app.callback()
def _init() -> None:
    init_db()


# ---- watches ----------------------------------------------------------------
@watch_app.command("list")
def watch_list() -> None:
    for w in services.list_watches():
        flag = "" if w.enabled else " (disabled)"
        target = w.repo if w.kind == "issues" else f"{w.repo}@{w.branch or 'default'}"
        typer.echo(f"[{w.id}] {w.name} -> {w.kind}:{target}{flag}")


@watch_app.command("add")
def watch_add(
    file: Path = typer.Option(..., "--file", "-f", help="YAML/JSON file describing one watch"),
) -> None:
    raw = yaml.safe_load(file.read_text())
    w = services.create_watch(WatchCreate.model_validate(raw))
    typer.echo(f"created watch [{w.id}] {w.name}")


@watch_app.command("rm")
def watch_rm(watch_id: int) -> None:
    services.delete_watch(watch_id)
    typer.echo(f"deleted watch {watch_id}")


@watch_app.command("run")
def watch_run(watch_id: int) -> None:
    created = asyncio.run(services.process_watch(watch_id))
    typer.echo(f"{len(created)} new match(es)")


@watch_app.command("dry-run")
def watch_dry_run(watch_id: int, limit: int = 30) -> None:
    results = asyncio.run(services.dry_run(watch_id, limit=limit))
    for r in results:
        mark = "MATCH" if r.matched else "  -  "
        kw = f" [{', '.join(r.matched_keywords)}]" if r.matched_keywords else ""
        typer.echo(f"{mark} {r.sha[:7]} {(r.message or '').splitlines()[0][:60]}{kw}")


# ---- channels ---------------------------------------------------------------
@channel_app.command("list")
def channel_list() -> None:
    for c in services.list_channels():
        typer.echo(f"{c.name}\t{c.url}")


@channel_app.command("add")
def channel_add(name: str, url: str) -> None:
    services.create_channel(ChannelCreate(name=name, url=url))
    typer.echo(f"created channel {name}")


@channel_app.command("rm")
def channel_rm(name: str) -> None:
    services.delete_channel(name)
    typer.echo(f"deleted channel {name}")


@channel_app.command("test")
def channel_test(name: str) -> None:
    ok, err = asyncio.run(services.test_channel(name))
    typer.echo("ok" if ok else f"FAILED: {err}")
    raise typer.Exit(0 if ok else 1)


# ---- monitoring -------------------------------------------------------------
@app.command()
def matches(watch_id: int = typer.Option(None), limit: int = 50, as_json: bool = False) -> None:
    rows = services.list_matches(watch_id=watch_id, limit=limit)
    if as_json:
        typer.echo(json.dumps([m.model_dump(mode="json") for m in rows], indent=2))
        return
    for m in rows:
        kw = f" [{', '.join(m.matched_keywords)}]" if m.matched_keywords else ""
        typer.echo(f"{m.created_at:%Y-%m-%d %H:%M} {m.repo} {m.sha[:7]}{kw}")


@app.command()
def status() -> None:
    for st in services.get_status():
        typer.echo(
            f"{st.name}: polled={st.last_polled_at} status={st.last_status} "
            f"rate={st.rate_remaining} matches={st.match_count} "
            f"{'ERR: ' + st.last_error if st.last_error else ''}"
        )


# ---- config -----------------------------------------------------------------
@config_app.command("export")
def config_export(out: Path = typer.Option(None, "--out", "-o")) -> None:
    text = config_io.export_yaml()
    if out:
        out.write_text(text)
        typer.echo(f"wrote {out}")
    else:
        typer.echo(text)


@config_app.command("import")
def config_import(file: Path, replace: bool = False) -> None:
    n_ch, n_w = config_io.import_yaml(file.read_text(), replace=replace)
    typer.echo(f"imported {n_ch} channel(s), {n_w} watch(es)")


# ---- serve ------------------------------------------------------------------
@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the API + background poller (production entrypoint)."""
    import uvicorn

    uvicorn.run("commit_watcher.api.app:app", host=host, port=port)


if __name__ == "__main__":
    app()
