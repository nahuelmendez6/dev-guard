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

# Importamos utilidades visuales de Rich
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


def show_banner(thread_id: str):
    """Muestra el banner de bienvenida con diseño y comandos disponibles."""
    menu_text = (
        "[bold cyan]🤖 Dev-Guard CLI[/bold cyan] - [dim]Agente Autónomo con Human-in-the-Loop y Time Travel[/dim]\n\n"
        "[bold yellow]Comandos disponibles:[/bold yellow]\n"
        "  [cyan]•[/cyan] [bold white]salir[/bold white] o [bold white]exit[/bold white]   [dim]-> Terminar el programa[/dim]\n"
        "  [cyan]•[/cyan] [bold white]reset[/bold white]            [dim]-> Reiniciar memoria y comenzar nueva sesión[/dim]\n"
        "  [cyan]•[/cyan] [bold white]historial[/bold white]        [dim]-> Inspeccionar checkpoints en el tiempo (git log)[/dim]\n"
        "  [cyan]•[/cyan] [bold white]replay <idx>[/bold white]    [dim]-> Reanudar desde un checkpoint (ej: replay 1)[/dim]"
    )
    console.print(
        Panel(
            menu_text,
            title="[bold magenta]🛡️  DEV-GUARD[/bold magenta]",
            subtitle=f"[dim]Sesión activa: [yellow]{thread_id}[/yellow][/dim]",
            border_style="bright_blue",
            padding=(1, 2)
        )
    )


def main():
    # Inicializamos el grafo y la sesión
    app = build_graph()
    thread_id = f"session-cli-{uuid.uuid4().hex[:6]}"

    show_banner(thread_id)

    # Configuración de sesión con límite de recursión
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 20
    }

    while True:
        try:
            # Captura de entrada con estilo
            console.print()
            user_input = console.input("[bold green]❯[/bold green] [bold white]Usuario[/bold white] > ").strip()

            if not user_input:
                continue

            # Condición de salida
            if user_input.lower() in ["salir", "exit", "quit"]:
                console.print("\n[bold cyan]👋 Saliendo de Dev-Guard. ¡Hasta luego![/bold cyan]\n")
                break

            # Comando para reiniciar la sesión
            if user_input.lower() in ["reset", "clear", "nuevo"]:
                thread_id = f"session-cli-{uuid.uuid4().hex[:6]}"
                config["configurable"]["thread_id"] = thread_id
                console.print(f"\n[bold green]🔄 Memoria reiniciada.[/bold green] Nueva sesión: [yellow]{thread_id}[/yellow]")
                continue

            # ==========================================================
            # COMANDO TIME TRAVEL 1: Ver Historial
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
                    console.print("[bold yellow]⚠️  Uso correcto:[/bold yellow] [white]replay <numero_indice>[/white] [dim](ejemplo: replay 1)[/dim]")
                    console.print("💡 Usa primero [bold cyan]historial[/bold cyan] para ver los índices disponibles.")
                    continue

                target_idx = int(partes[1])
                target_config = get_checkpoint_by_index(app, config, target_idx)
                if not target_config:
                    console.print(f"[bold red]❌ No existe ningún checkpoint con el índice [{target_idx}].[/bold red]")
                    continue

                with console.status(f"[bold magenta]🕰 [Time Travel] Reanudando desde checkpoint [{target_idx}]...[/bold magenta]", spinner="aesthetic"):
                    replay_from(app, target_config)
            else:
                # Flujo normal: invocación del grafo
                if len(user_input) > 4000:
                    console.print("[bold red]❌ La entrada excede el límite de 4000 caracteres.[/bold red]")
                    continue

                with console.status("[bold cyan]🤖 Procesando con el agente...[/bold cyan]", spinner="dots"):
                    app.invoke({"user_request": user_input}, config)

            # ==========================================================
            # GESTIÓN DEL ESTADO E INTERRUPCIONES (HITL + FORKING)
            # ==========================================================
            while True:
                snapshot = app.get_state(config)

                # CASO A: Pausado esperando aprobación humana (HITL)
                if snapshot.tasks and snapshot.tasks[0].interrupts:
                    info_interrupcion = snapshot.tasks[0].interrupts[0].value
                    codigo_actual = info_interrupcion.get("code", "")
                    mensaje_nodo = info_interrupcion.get("message", "Aprobación requerida")

                    # Mostramos el código con resaltado sintáctico real de Python
                    syntax = Syntax(codigo_actual, "python", theme="monokai", line_numbers=True, word_wrap=True)
                    console.print()
                    console.print(Panel(
                        syntax,
                        title="[bold green]📝 CÓDIGO GENERADO[/bold green]",
                        subtitle=f"[dim]{mensaje_nodo}[/dim]",
                        border_style="bright_green",
                        padding=(1, 2)
                    ))

                    # Menú estilizado de decisiones
                    opciones_panel = (
                        "[bold green][S][/bold green]í       -> [white]Aprobar y guardar código en archivo[/white]\n"
                        "[bold red][N][/bold red]o       -> [white]Rechazar código[/white]\n"
                        "[bold yellow][E][/bold yellow]ditar   -> [white]Modificar código manualmente ([bold cyan]Time Travel Fork[/bold cyan])[/white]"
                    )
                    console.print(Panel(opciones_panel, title="[bold magenta]⚡ Opciones Human-in-the-Loop[/bold magenta]", border_style="magenta"))

                    decision = console.input("\n[bold yellow]¿Qué deseas hacer?[/bold yellow] [dim](sí/no/editar)[/dim]: ").strip().lower()

                    # ------------------------------------------------------
                    # OPCIÓN TIME TRAVEL: Forking y edición manual
                    # ------------------------------------------------------
                    if decision in ["editar", "edit", "fork", "e"]:
                        console.print(Panel(
                            "Escribe o pega tu código a continuación.\n"
                            "Cuando termines, escribe [bold yellow]FIN[/bold yellow] en una línea vacía y presiona [bold]Enter[/bold].",
                            title="[bold yellow]✏️ Modo Edición Manual (Time Travel Fork)[/bold yellow]",
                            border_style="yellow"
                        ))

                        lineas = []
                        while True:
                            linea = input()
                            if linea.strip() == "FIN":
                                break
                            lineas.append(linea)
                        codigo_editado = "\n".join(lineas)

                        # Checkpoint previo a la pausa (índice 1)
                        target_config = get_checkpoint_by_index(app, config, index=1)
                        if not target_config:
                            console.print("[bold red]❌ No se pudo recuperar el checkpoint para editar.[/bold red]")
                            break

                        nuevo_codigo_obj = GeneratedCode(
                            code=codigo_editado,
                            explanation="Código editado manualmente por el usuario vía Time Travel"
                        )

                        # Forking con as_node='generate_code'
                        forked_config = fork_state(
                            app,
                            target_config=target_config,
                            values={"code": nuevo_codigo_obj},
                            as_node="generate_code"
                        )

                        # Reanudar validación con spinner
                        with console.status("[bold cyan]🔄 Validando código editado con el validador sintáctico...[/bold cyan]", spinner="dots"):
                            replay_from(app, forked_config)
                        continue

                    # ------------------------------------------------------
                    # OPCIÓN NORMAL: Sí o No (Aprobación estándar)
                    # ------------------------------------------------------
                    aprobado = decision in ["sí", "si", "yes", "y", "s"]
                    nombre_archivo = "generated_code.py"

                    if aprobado:
                        custom_name = console.input("[dim]Nombre del archivo (Enter para 'generated_code.py'): [/dim]").strip()
                        if custom_name:
                            nombre_archivo = custom_name

                    with console.status("[bold green]💾 Guardando estado y procesando decisión...[/bold green]", spinner="dots"):
                        app.invoke(
                            Command(resume={"approved": aprobado, "filename": nombre_archivo}),
                            config
                        )

                    if aprobado:
                        console.print(f"\n[bold green]✅ Código aprobado y guardado exitosamente en '{nombre_archivo}'.[/bold green]")
                    else:
                        console.print("\n[bold red]❌ Código rechazado. Operación cancelada por el usuario.[/bold red]")

                    break

                # CASO B: Grafo completado sin interrupciones pendientes
                else:
                    analysis = snapshot.values.get("petition_analysis")
                    attempts = snapshot.values.get("attempts", 0)

                    if analysis and not analysis.is_code_task:
                        console.print("\n[yellow]⚠️  La petición no es una tarea de programación. No se generó código.[/yellow]")
                    elif attempts >= 3:
                        errors = snapshot.values.get("validation_errors", [])
                        console.print("\n[bold red]⚠️  Se alcanzó el límite de intentos para generar código válido.[/bold red]")
                        for err in errors:
                            console.print(f"   [red]• {err}[/red]")
                    else:
                        console.print("\n[dim]✔ Turno completado.[/dim]")

                    break

        except GraphRecursionError:
            console.print("\n[bold red]🚨 Error: Se alcanzó el límite máximo de pasos en el grafo. Operación abortada.[/bold red]")
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]⚠️  Operación interrumpida por el usuario (Ctrl+C).[/bold yellow]")
            confirmar = console.input("¿Deseas salir de Dev-Guard? (s/n): ").strip().lower()
            if confirmar in ["s", "si", "sí", "y", "yes"]:
                console.print("[bold cyan]👋 ¡Hasta luego![/bold cyan]\n")
                break
        except EOFError:
            console.print("\n[bold cyan]Saliendo de Dev-Guard. ¡Hasta luego![/bold cyan]\n")
            break
        except Exception as e:
            error_msg = str(e)
            console.print(f"\n[bold red]❌ Error durante la ejecución:[/bold red]")
            if "429" in error_msg or "ResourceExhausted" in error_msg:
                console.print("   • Se ha superado la cuota de peticiones (Rate Limit). Espera unos segundos.")
            elif "timeout" in error_msg.lower():
                console.print("   • La API tardó demasiado en responder (Timeout).")
            elif "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                console.print("   • Error de autenticación. Verifica las API keys en tu archivo .env.")
            else:
                console.print(f"   • Detalle: {error_msg}")
            console.print("[dim]💡 Puedes continuar con otra petición.[/dim]")


if __name__ == "__main__":
    main()
