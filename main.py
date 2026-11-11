import sys
import os

# 1. Aseguramos que Python encuentre los modulos dentro de src/agent
sys.path.insert(0, os.path.abspath("src/agent"))

from graph import build_graph
from langgraph.types import Command

def main():
        print("========================================")      
        print("🤖 Bienvenido a Dev-Guard (CLI Interactivo)")   
        print("Escribe 'salir' o 'exit' para terminar.")       
        print("========================================\n")

        # 2. Inicializamos el grafo
        app = build_graph()

        # 3. COnfigurams la sesion (thread_id permite recordar el contexto)
        config = {"configurable": {"thread_id":"session-cli-1"}}

        while True:
            # 4. Capturamos el texto del usuario
            user_input = input("\nUsuario > ").strip()

            # Condicion de salida
            if not user_input:
                continue
            if user_input.lower() in ["salir", "exit", "quit"]:
                print("Saliendo de Dev-Guard. ¡Hasta luego!")
                break

            # TODO: Aqui invocaremos el grafo y gestionaremos la pausa de aprobacion
            print(f"[Procesando]: {user_input}")

            # Primera llamada
            app.invoke({"user_request": user_input}, config)

            # comprobamos el estado del grafo
            snapshot = app.get_state(config)

            # CASO A: El grafo se pausó esperando aprobacion del usuario
            if snapshot.tasks and snapshot.tasks[0].interrupts:
                info_interrupcion = snapshot.tasks[0].interrupts[0].value
                snapshot.tasks[0].interrupts[0].value

                print("\n" + "="*40)                           
                print("📝 CÓDIGO GENERADO:")                   
                print("="*40)
                print(info_interrupcion.get("code", ""))       
                print("="*40)
                print(f"Mensaje: {info_interrupcion.get('message')}")  

                # Capturamos decision del usuario
                respuesta = input("\n¿Desea aprobar el código para guardarlo en disco? (sí/no): ").strip().lower()
                aprobado = respuesta in ["sí", "si", "yes", "y", "s"]

                # Reanudamos el gafo inyectando la decision
                app.invoke(Command(resume={"approved": aprobado}), config)

                if aprobado:
                    print("✅ Código aprobado y guardado en disco.")
                else:
                    print("❌ Código rechazado. No se guardará en disco.")

            # CASO B: El grafo terminó directamente (sin interrupciones)
            else:
                analysis = snapshot.state.get("petition_analysis")
                if analysis and not analysis.is_code_task:
                    print("⚠️ La petición del usuario no es una tarea de código. No se generará código.")
                else:
                    print("⚠️ El grafo terminó sin generar código ni requerir aprobación.")


if __name__ == "__main__":
    main()