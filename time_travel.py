"""
Módulo de utilidades para Time Travel (Replay y Forking) en LangGraph

Permite inspeccionar el historia lde checkpoints de un hilo de ejecución,
seleccionar un estado pasado, crear bifurcaciones (forks) alterando datos
históricos y reanudar (replay) el gafo desde cualquier punto temporal

"""
from typing import Any, Dict, List, Optional, Tuple
from langgraph.graph.state import CompiledStateGraph
from state import AgentState, GeneratedCode

def print_history(
    app: CompiledStateGraph, 
    config: Dict[str, Any], 
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Imprime en consola una vista de estilo 'git log' con los checkpoints del hilo actual.

    Args:
        app: Grafo de LangGraph compilado con un checkpointer activo.
        config: Diccionario de configuración que contiene el 'thread_id' de la sesión
        limit: Número máximo de checkpointer recientes a mostrar

    Returns:
        Lista de diccionarios con un resumen de cada checkpoint (indice, IDs, paso, nodo pendiente y config completa) para facilitar su seleccion en una CLI
    """
    print("\n" + "=" * 65)
    print(" HISTORIAL DE CHECKPOINTS (TIME TRAVEL)")
    print("=" * 65)

    # Recupera todos los snapshots del hilo ordenados del más reciente (idx=0) al mas antiguo
    history = list(app.get_state_history(config))
    if not history:
        print(" (No hay historial disponible para esta sesion)")
        print("=" * 65 + \n)
        return []

    checkpoints_summary = []

    # Itera sobre los snapshots hasta alcanzar el límite indicado
    for idx, snapshot in enumerate(history[:limit]):
        # 1. Identificador del checkpoint: extrae el UUID y lo acorta a 8 caracteres (estilo Git)
        chk_id = snapshot.config.get("configurable", {}).get("checkpoint_id", "N/A")
        short_id = chk_id[:8] if chk_id != "N/A" else "N/A"

        # 2. Metadatos de ejecución: número de paso y siguiente nodo pendiente
        # Si snapshot.next está vacío, significa que el grafo ya terminó (llegó a END)
        step = snapshot.metadata.get("step", "?")
        next_node = snapshot.next if snapshot.next else "(Fin de ejecución)"

        # 3. Inspección del estado de negocio guardado en este instante
        state_values = snapshot.values or {}
        code_obj = state_values.get("code")
        has_code = "Sí" if code_obj else "No"
        errors = len(state_values.get("validation_errors", []))

        # Almacena el resumen y la configuración exacta del checkpoint para indexación rápida
        checkpoints_summary.append({
            "index": idx,
            "checkpoint_id": chk_id,
            "short_id": short_id,
            "step": step,
            "next": next_node,
            "config": snapshot.config
        })

        # Marca el índice 0 como el estado más reciente (HEAD)
        head_tag = " <-- [HEAD actual]" if idx == 0 else ""

        # Muestra la línea principal del checkpoint
        print(f"[{idx}] ID: {short_id}... | Paso: {step} | Pendiente: {next_node}{head_tag}")

        # Si ya existe un objeto GeneratedCode válido, muestra la primera línea (máx. 40 chars) y errores
        if code_obj and isinstance(code_obj, GeneratedCode):
            resumen_codigo = code_obj.code.strip().split("\n")[0][:40]
            print(f"     └─ Código: {resumen_codigo}... | Errores: {errors}")

        print("-" * 65)

    print("=" * 65 + "\n")
    return checkpoints_summary


def get_checkpoint_by_index(
    app: CompiledStateGraph,
    config: Dict[str, Any],
    index: int
) -> Optional[Dict[str, Any]]:
    """
    Obtiene la configuración específica (thread_id + checkpoint_id) de un checkpoint
    según su posición en el historial.

    Args:
        app: Grafo de LangGraph compilado.
        config: Configuración base con el 'thread_id' del hilo.
        index: Posición temporal (0 = estado más reciente, 1 = inmediatamente anterior, etc.).

    Returns:
        Diccionario 'config' apuntando a ese checkpoint exacto, o None si el índice no existe.
    """
    history = list(app.get_state_history(config))
    if 0 <= index < len(history):
        return history[index].config
    return None