import sys
import os
import uuid

# 1. Aseguramos que Python encuentre los módulos dentro de src/agent
sys.path.insert(0, os.path.abspath("src/agent"))

from graph import build_graph
from state import GeneratedCode
from time_travel import print_history, get_checkpoint_by_index, fork_state, replay_from
from langgraph.types import Command
from langgraph.errors import GraphRecursionError


def main():
    # Mensaje de bienvenida con los comandos disponibles (incluyendo Time Travel)
    print("=" * 60)
    print("🤖 Dev-Guard (CLI Interactivo con Time Travel)")
    print("Comandos disponibles:")
    print("  • 'salir' o 'exit'   -> Terminar programa")
    print("  • 'reset'            -> Reiniciar memoria de la sesión")
    print("  • 'historial'        -> Ver checkpoints (git log del agente)")
    print("  • 'replay <indice>'  -> Volver a un punto anterior (ej: replay 1)")
    print("=" * 60 + "\n")

    # 2. Inicializamos el grafo y la memoria
    app = build_graph()
    thread_id = f"session-cli-{uuid.uuid4().hex[:6]}"  # Identificador único de sesión

    # 3. Configuración de la sesión (thread_id y límite de pasos para evitar bucles)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 20
    }

    while True:
        try:
            # 4. Capturamos la entrada del usuario
            user_input = input("\nUsuario > ").strip()

            # Validación de entrada vacía
            if not user_input:
                continue

            # Condición de salida
            if user_input.lower() in ["salir", "exit", "quit"]:
                print("Saliendo de Dev-Guard. ¡Hasta luego!")
                break

            # Comando para reiniciar la sesión actual
            if user_input.lower() in ["reset", "clear", "nuevo"]:
                thread_id = f"session-cli-{uuid.uuid4().hex[:6]}"
                config["configurable"]["thread_id"] = thread_id
                print(f"🔄 Memoria de la sesión reiniciada. Nueva sesión: {thread_id}")
                continue

            # ==========================================================
            # COMANDO TIME TRAVEL 1: Ver Historial de Checkpoints
            # ==========================================================
            if user_input.lower() in ["historial", "/historial", "history"]:
                print_history(app, config)
                continue

            # ==========================================================
            # COMANDO TIME TRAVEL 2: Replay desde un Checkpoint Pasado
            # ==========================================================
            if user_input.lower().startswith("replay"):
                partes = user_input.split()
                if len(partes) < 2 or not partes[1].isdigit():
                    print("⚠️ Uso correcto: replay <numero_indice> (ejemplo: replay 1)")
                    print("💡 Usa primero 'historial' para ver los índices disponibles.")
                    continue

                target_idx = int(partes[1])
                target_config = get_checkpoint_by_index(app, config, target_idx)
                if not target_config:
                    print(f"❌ No existe ningún checkpoint con el índice [{target_idx}].")
                    continue

                print(f"🕰 [Time Travel]: Viajando al checkpoint [{target_idx}]...")
                replay_from(app, target_config)
            else:
                # Flujo normal: validación de tamaño e invocación inicial del grafo
                if len(user_input) > 4000:
                    print("❌ La entrada excede el límite de 4000 caracteres.")
                    continue

                print(f"[Procesando]: {user_input}")
                app.invoke({"user_request": user_input}, config)

            # ==========================================================
            # 5. GESTIÓN DEL ESTADO E INTERRUPCIONES (HITL + FORKING)
            # ==========================================================
            while True:
                # Comprobamos el estado actual del grafo (HEAD)
                snapshot = app.get_state(config)

                # CASO A: El grafo se pausó esperando interacción humana (HITL)
                if snapshot.tasks and snapshot.tasks[0].interrupts:
                    info_interrupcion = snapshot.tasks[0].interrupts[0].value

                    print("\n" + "=" * 45)
                    print("📝 CÓDIGO GENERADO:")
                    print("=" * 45)
                    codigo_actual = info_interrupcion.get("code", "")
                    print(codigo_actual)
                    print("=" * 45)
                    print(f"Mensaje: {info_interrupcion.get('message')}")

                    # Mostramos las 3 opciones disponibles para el usuario
                    print("\nOpciones:")
                    print("  • 'sí'     -> Aprobar y guardar en disco")
                    print("  • 'no'     -> Rechazar código")
                    print("  • 'editar' -> Modificar código manualmente (Time Travel Fork)")

                    decision = input("\n¿Qué deseas hacer?: ").strip().lower()

                    # ------------------------------------------------------
                    # OPCIÓN TIME TRAVEL: Forking y modificación manual
                    # ------------------------------------------------------
                    if decision in ["editar", "edit", "fork"]:
                        print("\n✏️ Escribe o pega tu código (escribe 'FIN' en una línea vacía al terminar):")
                        lineas = []
                        while True:
                            linea = input()
                            if linea.strip() == "FIN":
                                break
                            lineas.append(linea)
                        codigo_editado = "\n".join(lineas)

                        # Paso 1: Obtenemos el checkpoint previo a la pausa (índice 1)
                        target_config = get_checkpoint_by_index(app, config, index=1)
                        if not target_config:
                            print("❌ No se pudo recuperar el checkpoint para editar.")
                            break

                        # Paso 2: Creamos el objeto GeneratedCode con el código manual
                        nuevo_codigo_obj = GeneratedCode(
                            code=codigo_editado,
                            explanation="Código editado manualmente por el usuario vía Time Travel"
                        )

                        # Paso 3: Forking con as_node='generate_code'
                        # Le decimos a LangGraph que el nodo generate_code produjo este nuevo código,
                        # obligando al router a saltar al validador sin consultar a la API del LLM.
                        forked_config = fork_state(
                            app,
                            target_config=target_config,
                            values={"code": nuevo_codigo_obj},
                            as_node="generate_code"
                        )

                        # Paso 4: Replay desde el fork para validar la sintaxis
                        print("🔄 [Time Travel]: Inyectando código en memoria y reanudando validador...")
                        replay_from(app, forked_config)
                        # El bucle interno continúa para evaluar el nuevo estado tras la validación
                        continue

                    # ------------------------------------------------------
                    # OPCIÓN NORMAL: Sí o No (Aprobación estándar)
                    # ------------------------------------------------------
                    aprobado = decision in ["sí", "si", "yes", "y", "s"]
                    nombre_archivo = "generated_code.py"

                    if aprobado:
                        custom_name = input("Nombre del archivo (Enter para 'generated_code.py'): ").strip()
                        if custom_name:
                            nombre_archivo = custom_name

                    # Reanudamos el nodo 'user_approval' inyectando la decisión
                    app.invoke(
                        Command(resume={"approved": aprobado, "filename": nombre_archivo}),
                        config
                    )

                    if aprobado:
                        print(f"✅ Código aprobado y guardado en '{nombre_archivo}'.")
                    else:
                        print("❌ Código rechazado. No se guardará en disco.")

                    # Terminamos la gestión de este turno
                    break

                # CASO B: El grafo terminó directamente (sin interrupciones activas)
                else:
                    analysis = snapshot.values.get("petition_analysis")
                    attempts = snapshot.values.get("attempts", 0)

                    if analysis and not analysis.is_code_task:
                        print("⚠️ La petición no es una tarea de programación. No se generará código.")
                    elif attempts >= 3:
                        errors = snapshot.values.get("validation_errors", [])
                        print("⚠️ Se alcanzó el límite de intentos para generar código. No se generará código.")
                        for err in errors:
                            print(f"  - {err}")
                    else:
                        print("ℹ️ Turno completado.")

                    # Salimos del bucle interno de procesamiento
                    break

        except GraphRecursionError:
            print("🚨 Error: Se alcanzó el límite máximo de pasos en el grafo. Operación abortada.")
        except KeyboardInterrupt:
            print("\n\n⚠️ Operación interrumpida por el usuario (Ctrl+C).")
            confirmar = input("¿Deseas salir de Dev-Guard? (s/n): ").strip().lower()
            if confirmar in ["s", "si", "sí", "y", "yes"]:
                print("👋 ¡Hasta luego!")
                break
        except EOFError:
            print("\nSaliendo de Dev-Guard. ¡Hasta luego!")
            break
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ Error durante la ejecución:")
            if "429" in error_msg or "ResourceExhausted" in error_msg:
                print("   • Se ha superado la cuota de peticiones (Rate Limit). Espera unos segundos.")
            elif "timeout" in error_msg.lower():
                print("   • La API tardó demasiado en responder (Timeout).")
            elif "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                print("   • Error de autenticación. Verifica las API keys en tu archivo .env.")
            else:
                print(f"   • Detalle: {error_msg}")
            print("💡 Puedes continuar con otra petición.")


if __name__ == "__main__":
    main()
