#!/usr/bin/env python3
"""
Rokan CLI — Command interface for the System.
Cross-platform (Linux + Windows). Everything flows through Agent Core.
"""

import sys
import click
from pathlib import Path


@click.group(invoke_without_command=True)
@click.version_option(version="2.0.0", prog_name="rokan")
@click.pass_context
def cli(ctx):
    """Rokan — The System. Ambient intelligence for your machine."""
    if ctx.invoked_subcommand is None:
        # Default: launch GUI desktop app, fallback to TUI
        try:
            import flask
            ctx.invoke(gui)
        except ImportError:
            ctx.invoke(tui)


@cli.command()
def tui():
    """Launch the Rokan TUI (terminal interface)"""
    try:
        from rokan_tui.app import run
        run()
    except ImportError as e:
        click.echo(f"[ERROR] Missing dependency: {e}")
        click.echo("Run: pip install -r requirements.txt")
    except Exception as e:
        click.echo(f"[ERROR] {e}")


@cli.command()
def gui():
    """Launch Rokan as a native desktop app (GTK window)"""
    try:
        from rokan_gui.window import launch
        launch()
    except SystemExit:
        raise
    except ImportError as e:
        click.echo(f"[ERROR] Missing dependency: {e}")
        click.echo("Run: pip install flask pywebview")
        click.echo("And: sudo apt install python3-gi gir1.2-webkit2-4.1")
    except Exception as e:
        click.echo(f"[ERROR] {e}")


@cli.command()
def status():
    """Show Rokan system status"""
    try:
        from rokan_core.agent import RokanAgent
        agent = RokanAgent()

        model_status = agent.get_model_status()
        mem_stats = agent.memory.stats()
        skills = agent.skills.list_skills()
    except Exception as e:
        click.echo(f"[ERROR] {e}")
        return

    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
    except ImportError:
        cpu = mem = disk = None

    click.echo("╔═══════════════════════════════════════════╗")
    click.echo("║          ROKAN — System Report            ║")
    click.echo("╠═══════════════════════════════════════════╣")
    click.echo("║  Version:    2.0.0                        ║")

    llm_ok = any(model_status.values())
    click.echo(f"║  LLM:        {'✓ ONLINE' if llm_ok else '✗ OFFLINE (set NVIDIA_API_KEY)':30s}  ║")
    for slot, ok in model_status.items():
        tag = "✓" if ok else "✗"
        click.echo(f"║    {tag} {slot.upper():12s}                         ║")

    if cpu is not None:
        click.echo(f"║  CPU:        {cpu:5.1f}% ({psutil.cpu_count()} cores)           ║")
        click.echo(f"║  RAM:        {mem.percent:.0f}% ({mem.used//(1024**3)}G/{mem.total//(1024**3)}G)             ║")
        click.echo(f"║  Disk:       {disk.percent:.0f}% ({disk.used//(1024**3)}G/{disk.total//(1024**3)}G)            ║")

    click.echo(f"║  Memory:     {mem_stats['total_memories']} entries, {mem_stats['sessions']} sessions  ║")
    click.echo(f"║  Skills:     {len(skills)} active                     ║")
    click.echo("╚═══════════════════════════════════════════╝")


@cli.command()
@click.argument("prompt", nargs=-1, required=True)
@click.option("--think", is_flag=True, help="Use reasoning model")
@click.option("--code", is_flag=True, help="Use code model")
@click.option("--fast", is_flag=True, help="Use fast model")
def ask(prompt, think, code, fast):
    """Ask Rokan a question (streams to stdout)

    Examples:
      rokan ask "What's the weather?"
      rokan ask --think "Analyze this complex problem"
      rokan ask --code "Write a Python function"
      rokan ask --fast "Quick summary"
    """
    question = " ".join(prompt)

    try:
        from rokan_core.agent import RokanAgent
        agent = RokanAgent()

        for chunk in agent.process(
            question,
            use_reasoning=think,
            use_code=code,
            use_fast=fast,
        ):
            ctype = chunk["type"]
            if ctype == "reasoning" and think:
                sys.stdout.write(f"\n[REASONING]\n{chunk['text']}\n\n[RESPONSE]\n")
                sys.stdout.flush()
            elif ctype == "content":
                sys.stdout.write(chunk["text"])
                sys.stdout.flush()
            elif ctype in ("system", "skill"):
                click.echo(chunk["text"], err=True)
            elif ctype == "error":
                click.echo(chunk["text"], err=True)
                return
        click.echo()
    except ImportError as e:
        click.echo(f"[ERROR] Missing dependency: {e}", err=True)


@cli.command()
@click.argument("text", nargs=-1)
def remember(text):
    """Store a fact in memory

    Examples:
      rokan remember "I prefer dark mode"
      rokan remember "My project uses Python 3.12"
    """
    if not text:
        click.echo("Usage: rokan remember 'something to remember'")
        return
    fact = " ".join(text)
    try:
        from rokan_core.memory_store import MemoryStore
        mem = MemoryStore()
        mem.store(fact, tier="semantic")
        click.echo(f"✓ Remembered: {fact}")
    except Exception as e:
        click.echo(f"[ERROR] {e}")


@cli.command()
@click.argument("query", nargs=-1)
def recall(query):
    """Search through memories

    Examples:
      rokan recall "dark mode"
      rokan recall "project setup"
    """
    if not query:
        click.echo("Usage: rokan recall 'search query'")
        return
    q = " ".join(query)
    try:
        from rokan_core.memory_store import MemoryStore
        mem = MemoryStore()
        results = mem.recall(q, limit=10)
        if not results:
            click.echo(f"No memories matching '{q}'.")
            return
        click.echo(f"Memories matching '{q}':")
        for r in results:
            click.echo(f"  [{r['tier']}] {r['content']} ({r['created_at'][:10]})")
    except Exception as e:
        click.echo(f"[ERROR] {e}")


@cli.command()
def memory():
    """Show memory statistics"""
    try:
        from rokan_core.memory_store import MemoryStore
        mem = MemoryStore()
        stats = mem.stats()
        click.echo("╔══ Memory ═══════════════════════════════╗")
        click.echo(f"║  Total:     {stats['total_memories']:6d} entries              ║")
        for tier, count in stats["tiers"].items():
            click.echo(f"║    {tier:12s} {count:5d}                   ║")
        click.echo(f"║  Sessions:  {stats['sessions']:6d}                       ║")
        click.echo(f"║  Messages:  {stats['total_messages']:6d}                       ║")
        click.echo("╚═════════════════════════════════════════╝")
    except Exception as e:
        click.echo(f"[ERROR] {e}")


@cli.command()
def models():
    """Show available model stack"""
    from rokan_tui.nvidia_client import MODELS

    click.echo("╔══════════════════════════════════════════════════════╗")
    click.echo("║          ROKAN Model Stack (NVIDIA NIM)              ║")
    click.echo("╠══════════════════════════════════════════════════════╣")
    for slot, model in MODELS.items():
        click.echo(f"║  {slot.upper():10s}  {model:40s} ║")
    click.echo("╚══════════════════════════════════════════════════════╝")


@cli.command(name="system")
def system_cmd():
    """Show live system metrics"""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        load = psutil.getloadavg()

        click.echo("╔══ System Metrics ════════════════════════╗")
        click.echo(f"║  CPU:   {cpu:5.1f}%  ({psutil.cpu_count()} cores)             ║")
        click.echo(f"║  RAM:   {mem.percent:.0f}% — {mem.used//(1024**3)}G / {mem.total//(1024**3)}G               ║")
        click.echo(f"║  Disk:  {disk.percent:.0f}% — {disk.used//(1024**3)}G / {disk.total//(1024**3)}G              ║")
        click.echo(f"║  Load:  {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}              ║")
        click.echo("╚══════════════════════════════════════════╝")
    except ImportError:
        click.echo("[ERROR] psutil not installed.")


@cli.command()
def skills():
    """List active skills"""
    try:
        from rokan_core.agent import RokanAgent
        agent = RokanAgent()
        for s in agent.skills.list_skills():
            click.echo(f"  /{s['name']:10s} — {s['description']}")
            if s['triggers']:
                click.echo(f"              triggers: {', '.join(s['triggers'][:5])}")
    except Exception as e:
        click.echo(f"[ERROR] {e}")


@cli.command()
def setup():
    """Check dependencies and configuration"""
    import shutil
    import os

    click.echo("╔══ Rokan Setup Check ════════════════════╗")
    click.echo("║  Checking dependencies...                ║")
    click.echo("╚═════════════════════════════════════════╝")
    click.echo()

    checks = {
        "Python 3.10+": True,
        "psutil": _check_import("psutil"),
        "textual": _check_import("textual"),
        "openai": _check_import("openai"),
        "pydantic": _check_import("pydantic"),
        "pyyaml": _check_import("yaml"),
        "edge-tts": _check_import("edge_tts"),
        "NVIDIA_API_KEY": bool(os.getenv("NVIDIA_API_KEY")),
        "mpv (voice)": bool(shutil.which("mpv")),
    }

    all_ok = True
    for name, ok in checks.items():
        icon = "✓" if ok else "✗"
        click.echo(f"  {icon}  {name}")
        if not ok:
            all_ok = False

    click.echo()
    if all_ok:
        click.echo("  All systems operational. Run: rokan")
    else:
        missing = [k for k, v in checks.items() if not v]
        click.echo(f"  Missing: {', '.join(missing)}")
        click.echo("  Run: pip install -r requirements.txt")
        click.echo("  Set: export NVIDIA_API_KEY='nvapi-...'")


def _check_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def main():
    """Entry point"""
    cli()


if __name__ == "__main__":
    main()
