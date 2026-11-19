import sys
import os
import uuid

# 1. Aseguramos que Python encuentre los modulos dentro de src/agent
sys.path.insert(0, os.path.abspath("src/agent"))

from graph import build_graph
from langgraph.types import Command
from langgraph.errors import GraphRecursionError

def main():
        print("=" * 50)                                    
        print("🤖 Dev-Guard (CLI Interactivo)")            
        print("Comandos disponibles:")                     
        print("  • 'salir' o 'exit' -> Terminar programa") 
        print("  • 'reset'          -> Reiniciar memoria de la sesión")                                        
        print("=" * 50 + "\n")  

        # 2. Inicializamos el grafo
        app = build_graph()
        thread_id = f"session-cli-{uuid.uuid4().hex[:6]}"  # Generamos un ID único para la sesión

        # 3. COnfigurams la sesion (thread_id permite recordar el contexto)
        # limite de recursion para evitar ciclos infinitos
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 20
        }

        while True:
            try:
                # 4. Capturamos el texto del usuario
                user_input = input("\nUsuario > ").strip()

                # Condicion de salida
                if not user_input:
                    continue
                if user_input.lower() in ["salir", "exit", "quit"]:
                    print("Saliendo de Dev-Guard. ¡Hasta luego!")
                    break

                if user_input.lower() in ["reset", "clear", "nuevo"]:
                    thread_id = f"session-cli-{uuid.uuid4().hex[:6]}"  # Generamos un nuevo ID único para la sesión
                    config["configurable"]["thread_id"] = thread_id
                    print("🔄 Memoria de la sesión reiniciada. Historial limpio")
                    continue

                if len(user_input) > 4000:
                    print("❌ La entrada excede el límite de 4000 caracteres.")
                    continue

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
                    nombre_archivo = "generated_code.py" # Nombre por defecto

                    if aprobado:
                        custom_name = input("Ingrese el nombre del archivo para guardar el código (o presione Enter para usar 'generated_code.py'): ").strip()
                        if custom_name:
                            nombre_archivo = custom_name

                    # Reanudamos el gafo inyectando la decision
                    app.invoke(Command(resume={"approved": aprobado}), config)

                    if aprobado:
                        print("✅ Código aprobado y guardado en disco.")
                    else:
                        print("❌ Código rechazado. No se guardará en disco.")

                # CASO B: El grafo terminó directamente (sin interrupciones)
                else:
                    analysis = snapshot.state.get("petition_analysis")
                    attempts = snapshot.state.get("attempts", 0)

                    if analysis and not analysis.is_code_task:
                        print("⚠️ La petición del usuario no es una tarea de código. No se generará código.")
                    elif attempts > 3:
                        errors = snapshot.state.get("validation_errors", [])
                        print("⚠️ Se alcanzó el límite de intentos para generar código. No se generará código.")
                        for err in errors:
                            print(f"  - {err}")
                    else:
                        print("⚠️ El grafo terminó sin generar código ni requerir aprobación.")


                    if analysis and not analysis.is_code_task:
                        print("⚠️ La petición del usuario no es una tarea de código. No se generará código.")
                    else:
                        print("⚠️ El grafo terminó sin generar código ni requerir aprobación.")
            except GraphRecursionError as e:
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
                print("\n❌ Error durante la ejecución:")  
                if "429" in error_msg or                   
                "ResourceExhausted" in error_msg:          
                    print("   • Se ha superado la cuota o límite de peticiones (Rate Limit). Espera unos segundos.")                
                elif "timeout" in error_msg.lower():       
                    print("   • La API tardó demasiado en responder (Timeout).")                 
                elif "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():       
                    print("   • Error de autenticación. Verifica las API keys en tu archivo  .env.")                                
                else:                                      
                    print(f"   • Detalle: {error_msg}")    
                print("💡 Puedes continuar con otra petición.")  


if __name__ == "__main__":
    main()