"""
Módulo de utilidades para Time Travel (Replay y Forking) en LangGraph con Rich UI.

Permite inspeccionar el historial de checkpoints de un hilo de ejecución,
seleccionar un estado pasado, crear bifurcaciones (forks) alterando datos
históricos y reanudar (replay) el grafo desde cualquier punto temporal.
"""
from typing import Any, Dict, List, Optional
from langgraph.graph.state import CompiledStateGraph
from state import AgentState, GeneratedCode

from rich.console import Console
from rich.table import Table

console = Console()


def print_history(
    app: CompiledStateGraph,
    config: Dict[str, Any],
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Imprime en consola una tabla estilizada con Rich mostrando los checkpoints del hilo actual.

    Args:
        app: Grafo de LangGraph compilado con un checkpointer activo.
        config: Diccionario de configuración con el 'thread_id' de la sesión.
        limit: Número máximo de checkpoints recientes a mostrar.

    Returns:
        Lista de diccionarios con un resumen de cada checkpoint.
    """
    history = list(app.get_state_history(config))
    if not history:
        console.print("[yellow]⚠️  No hay historial disponible para esta sesión.[/yellow]\n")
        return []

    table = Table(
        title="🕰  LÍNEA TEMPORAL DE CHECKPOINTS (TIME TRAVEL)",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="bright_blue",
        show_lines=True
    )
    table.add_column("Índice", justify="center", style="bold yellow", width=10)
    table.add_column("ID Checkpoint", style="cyan", width=16)
    table.add_column("Paso", justify="center", style="green", width=6)
    table.add_column("Siguiente Nodo", style="white", width=24)
    table.add_column("Errores", justify="center", width=9)
    table.add_column("Vista Previa de Código", style="dim", overflow="ellipsis")

    checkpoints_summary = []

    for idx, snapshot in enumerate(history[:limit]):
        chk_id = snapshot.config.get("configurable", {}).get("checkpoint_id", "N/A")
        short_id = chk_id[:8] if chk_id != "N/A" else "N/A"
        step = str(snapshot.metadata.get("step", "?"))

        # Siguiente nodo pendiente
        if snapshot.next:
            next_str = ", ".join(snapshot.next)
            if "user_approval" in next_str:
                next_styled = f"[bold yellow]⏸ {next_str} (HITL)[/bold yellow]"
            elif "validator" in next_str:
                next_styled = f"[cyan]🔍 {next_str}[/cyan]"
            elif "generate_code" in next_str:
                next_styled = f"[blue]⚡ {next_str}[/blue]"
            else:
                next_styled = next_str
        else:
            next_styled = "[bold green]✔ (Completado)[/bold green]"

        state_values = snapshot.values or {}
        code_obj = state_values.get("code")
        errors = len(state_values.get("validation_errors", []))
        errors_str = f"[red]{errors}[/red]" if errors > 0 else "[green]0[/green]"

        code_preview = ""
        if code_obj and isinstance(code_obj, GeneratedCode):
            code_preview = code_obj.code.strip().split("\n")[0][:45]

        idx_str = f"[{idx}]"
        if idx == 0:
            idx_str = f"[bold green]▶ [{idx}][/bold green]"
            short_id = f"[bold green]{short_id} (HEAD)[/bold green]"

        checkpoints_summary.append({
            "index": idx,
            "checkpoint_id": chk_id,
            "short_id": short_id,
            "step": step,
            "next": snapshot.next,
            "config": snapshot.config
        })

        table.add_row(idx_str, short_id, step, next_styled, errors_str, code_preview)

    console.print()
    console.print(table)
    console.print()
    return checkpoints_summary


def get_checkpoint_by_index(
    app: CompiledStateGraph,
    config: Dict[str, Any],
    index: int
) -> Optional[Dict[str, Any]]:
    """
    Obtiene la configuración específica (thread_id + checkpoint_id) de un checkpoint
    según su posición en el historial.
    """
    history = list(app.get_state_history(config))
    if 0 <= index < len(history):
        return history[index].config
    return None


def fork_state(
    app: CompiledStateGraph,
    target_config: Dict[str, Any],
    values: Dict[str, Any],
    as_node: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crea una bifurcación (fork) del estado a partir de un checkpoint histórico,
    sin destruir la línea temporal original.
    """
    new_config = app.update_state(
        target_config,
        values=values,
        as_node=as_node
    )
    return new_config


def replay_from(
    app: CompiledStateGraph,
    target_config: Dict[str, Any]
) -> Any:
    """
    Reanuda la ejecución del grafo exactamente desde el checkpoint indicado.
    """
    return app.invoke(None, target_config)
