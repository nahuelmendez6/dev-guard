import sys
import os

sys.path.insert(0, os.path.abspath("src/agent"))

from graph import build_graph
from state import GeneratedCode
from time_travel import print_history, get_checkpoint_by_index, fork_state, replay_from


def run_demo():
    print("🚀 INICIANDO DEMOSTRACIÓN DE TIME TRAVEL\n")
    app = build_graph()

    # Hilo de sesión único para esta prueba
    config = {
        "configurable": {"thread_id": "test-timetravel-session"},
        "recursion_limit": 20,
    }

    # 1. Ejecución normal inicial
    peticion = "Crea una función de python llamada calcular_iva que reciba un precio y devuelva el 21%"
    print(f"1️⃣ Enviando petición: '{peticion}'")
    app.invoke({"user_request": peticion}, config)

    # 2. Vemos el historial generado hasta la pausa de aprobación (HITL)
    print("\n2️⃣ Historial tras la primera ejecución (pausado en aprobación):")
    print_history(app, config)

    snapshot_pausa = app.get_state(config)
    print(f"Estado en pausa. Nodo pendiente: {snapshot_pausa.next}")

    # 3. Viaje en el tiempo (Forking):
    # En lugar de aprobar el código que hizo el LLM, retrocedemos al checkpoint previo
    # e inyectamos un código completamente nuestro
    print("\n3️⃣ VIAJE EN EL TIEMPO: Inyectando código manual (Forking)...")

    codigo_manual = GeneratedCode(
        code=(
            "def calcular_iva(precio: float) -> float:\n"
            "    # Código inyectado manualmente vía Time Travel\n"
            "    return precio * 0.21\n"
        ),
        explanation="Corregido e implementado manualmente vía fork_state",
    )

    # Tomamos el checkpoint inmediatamente anterior a la pausa
    past_config = get_checkpoint_by_index(app, config, index=1)
    if not past_config:
        print("❌ No se encontró el checkpoint anterior.")
        return

    # Inyectamos el nuevo código con as_node='generate_code'
    # Esto le dice al grafo: 'generate_code ya terminó y entregó este nuevo código'
    forked_config = fork_state(
        app,
        target_config=past_config,
        values={"code": codigo_manual},
        as_node="generate_code",
    )
    print("✅ Fork registrado en la memoria de LangGraph.")

    # 4. Replay desde la bifurcación:
    # El grafo se reanuda, pasa por el validador (revisa que el código sea Python válido)
    # y llega nuevamente a la pausa de aprobación, ¡sin volver a llamar a la API del LLM!
    print("\n4️⃣ Reanudando ejecución desde el nuevo checkpoint (Replay)...")
    replay_from(app, forked_config)

    # 5. Verificamos el historial final
    print("\n5️⃣ Historial actualizado con la nueva rama (Fork):")
    print_history(app, config)

    snapshot_final = app.get_state(config)
    codigo_en_memoria = snapshot_final.values.get("code")
    print("📝 Código actualmente en memoria:")
    print(codigo_en_memoria.code if codigo_en_memoria else "Sin código")


if __name__ == "__main__":
    run_demo()