#!/usr/bin/env python3
"""
Rokan CLI — Command interface for The Player
Linux-first AI assistant with NVIDIA NIM backbone.
Summit Level System (Sung Jin-Woo edition).
"""

import click
from pathlib import Path


@click.group(invoke_without_command=True)
@click.version_option(version="2.0.0", prog_name="rokan")
@click.pass_context
def cli(ctx):
    """Rokan — The Player. Linux-first. NVIDIA NIM powered."""
    if ctx.invoked_subcommand is None:
        # Default action: launch TUI
        ctx.invoke(tui)


@cli.command()
def tui():
    """Launch the Rokan TUI (default)"""
    try:
        from rokan_tui.app import run
        run()
    except ImportError as e:
        click.echo(f"[ERROR] Missing dependency: {e}")
        click.echo("Run: pip install -r requirements.txt")
    except Exception as e:
        click.echo(f"[ERROR] {e}")


@cli.command()
def status():
    """Show Rokan system status"""
    try:
        from rokan_tui.nvidia_client import NvidiaNIMClient, MODELS
        client = NvidiaNIMClient()
        has_key = client._available
    except ImportError:
        has_key = False
        MODELS = {}
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
    except ImportError:
        cpu = mem = disk = None

    click.echo("╔══════════════════════════════════════════╗")
    click.echo("║          ROKAN — Status Report           ║")
    click.echo("╠══════════════════════════════════════════╣")
    click.echo(f"║  Version:    2.0.0                       ║")
    click.echo(f"║  NVIDIA NIM: {'✓ ACTIVE' if has_key else '✗ OFFLINE':15s}              ║")
    if cpu is not None:
        click.echo(f"║  CPU:        {cpu:5.1f}%                      ║")
        click.echo(f"║  RAM:        {mem.percent:.0f}% ({mem.used//(1024**3)}G/{mem.total//(1024**3)}G)              ║")
        click.echo(f"║  Disk:       {disk.percent:.0f}% ({disk.used//(1024**3)}G/{disk.total//(1024**3)}G)             ║")
    click.echo("╠══════════════════════════════════════════╣")
    click.echo("║  Model Stack:                            ║")
    click.echo("║    PRIMARY  meta/llama-3.3-70b-instruct  ║")
    click.echo("║    REASON   z-ai/glm4.7                  ║")
    click.echo("║    FAST     stepfun-ai/step-3.5-flash    ║")
    click.echo("║    CODE     qwen/qwq-32b                 ║")
    click.echo("╚══════════════════════════════════════════╝")


@cli.command()
@click.argument("prompt", nargs=-1, required=True)
@click.option("--think", is_flag=True, help="Use reasoning model (GLM 4.7)")
@click.option("--code", is_flag=True, help="Use code model (QwQ 32B)")
@click.option("--fast", is_flag=True, help="Use fast model (Step 3.5 Flash)")
def ask(prompt, think, code, fast):
    """Ask Rokan a question (non-interactive, streams to stdout)

    Examples:
      rokan ask "What's the weather?"
      rokan ask --think "Analyze this complex problem"
      rokan ask --code "Write a Python function"
      rokan ask --fast "Quick summary on Linux kernels"
    """
    import sys
    import os

    question = " ".join(prompt)

    try:
        from rokan_tui.nvidia_client import NvidiaNIMClient
        client = NvidiaNIMClient()

        messages = [{"role": "user", "content": question}]
        for chunk in client.chat_stream(
            messages,
            use_reasoning=think,
            use_code=code,
            use_fast=fast,
        ):
            if chunk["type"] == "reasoning" and think:
                # Show reasoning in markdown format for better readability
                sys.stdout.write(f"\n[REASONING]\n{chunk['text']}\n\n[RESPONSE]\n")
                sys.stdout.flush()
            elif chunk["type"] == "content":
                sys.stdout.write(chunk["text"])
                sys.stdout.flush()
            elif chunk["type"] == "error":
                click.echo(chunk["text"], err=True)
                return
        click.echo()  # trailing newline
    except ImportError as e:
        click.echo(f"[ERROR] Missing dependency: {e}", err=True)


@cli.command()
def models():
    """Show available model stack"""
    try:
        from rokan_tui.nvidia_client import MODELS
    except ImportError:
        MODELS = {}

    click.echo("╔══════════════════════════════════════════════════════════╗")
    click.echo("║          ROKAN Model Stack (NVIDIA NIM)                  ║")
    click.echo("╠══════════════════════════════════════════════════════════╣")
    click.echo("║  PRIMARY (default)                                       ║")
    click.echo(f"║    Model:       {MODELS.get('primary', 'meta/llama-3.3-70b-instruct')}")
    click.echo("║    Temp:        0.75  │  Top-P: 0.9  │  Max: 4096 tokens║")
    click.echo("║    Best for:    General queries, reasoning               ║")
    click.echo("║                                                          ║")
    click.echo("║  REASONING (--think)                                     ║")
    click.echo(f"║    Model:       {MODELS.get('reasoning', 'z-ai/glm4.7')}")
    click.echo("║    Temp:        1.0   │  Top-P: 1.0  │  Max: 16384      ║")
    click.echo("║    Best for:    Deep analysis, complex problems          ║")
    click.echo("║                                                          ║")
    click.echo("║  FAST (--fast)                                           ║")
    click.echo(f"║    Model:       {MODELS.get('fast', 'stepfun-ai/step-3.5-flash')}")
    click.echo("║    Temp:        0.8   │  Top-P: 0.9  │  Max: 8192       ║")
    click.echo("║    Best for:    Quick answers, low latency               ║")
    click.echo("║                                                          ║")
    click.echo("║  CODE (--code)                                           ║")
    click.echo(f"║    Model:       {MODELS.get('code', 'qwen/qwq-32b')}")
    click.echo("║    Temp:        0.6   │  Top-P: 0.9  │  Max: 16384      ║")
    click.echo("║    Best for:    Code generation, debugging               ║")
    click.echo("╚══════════════════════════════════════════════════════════╝")


@cli.command()
def system():
    """Show live system metrics"""
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        load = psutil.getloadavg()

        click.echo("╔══ System Metrics ═══════════════════════╗")
        click.echo(f"║  CPU:   {cpu:5.1f}%  ({psutil.cpu_count()} cores)            ║")
        click.echo(f"║  RAM:   {mem.percent:.0f}% — {mem.used//(1024**3)}G / {mem.total//(1024**3)}G              ║")
        click.echo(f"║  Disk:  {disk.percent:.0f}% — {disk.used//(1024**3)}G / {disk.total//(1024**3)}G             ║")
        click.echo(f"║  Load:  {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}             ║")
        click.echo("╚═════════════════════════════════════════╝")
    except ImportError:
        click.echo("[ERROR] psutil not installed.")


@cli.command()
def config():
    """Show configuration paths"""
    click.echo("╔══ Configuration ════════════════════════╗")
    click.echo(f"║  Config: ~/.openclaw/config.yaml         ║")
    click.echo(f"║  Skills: ~/.openclaw/skills/             ║")
    click.echo(f"║  Data:   ~/.rokan/                       ║")
    click.echo(f"║  Logs:   ~/.rokan/logs/                  ║")
    click.echo("╚═════════════════════════════════════════╝")


@cli.command()
def setup():
    """Run Rokan setup wizard"""
    import shutil
    import os

    click.echo("╔══ Rokan Setup ══════════════════════════╗")
    click.echo("║  Checking dependencies...                ║")
    click.echo("╚═════════════════════════════════════════╝")
    click.echo()

    checks = {
        "Python 3.10+": True,
        "psutil": _check_import("psutil"),
        "textual": _check_import("textual"),
        "openai": _check_import("openai"),
        "edge-tts": _check_import("edge_tts"),
        "NVIDIA_API_KEY": bool(os.getenv("NVIDIA_API_KEY")),
        "mpv (voice)": bool(shutil.which("mpv")),
    }

    for name, ok in checks.items():
        icon = "✓" if ok else "✗"
        click.echo(f"  {icon}  {name}")

    click.echo()
    missing = [k for k, v in checks.items() if not v]
    if missing:
        click.echo(f"  Missing: {', '.join(missing)}")
        click.echo("  Run: pip install -r requirements.txt")
    else:
        click.echo("  All systems operational. Run: rokan")


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
