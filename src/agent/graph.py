import langchain

langchain.debug = False

from langgraph.graph import StateGraph, START, END
from state import AgentState
from nodes import analize_petition_node, generate_code_node, validate_code_node, save_code_to_disk_node
# Import MemorySaver
from langgraph.checkpoint.memory import MemorySaver

# 1. Deterministic routing function
def route_after_analysis(state: AgentState) -> str:
    """
    Decides if generate code or finish
    """
    analysis = state.get("petition_analysis")

    if analysis and analysis.is_code_task:
        print("[Router 1]: Routing to code generation...")
        return "generate_code"

    print("[Router 1] Finishing execution.")
    return "end"

def route_after_validation(state: AgentState) -> str:
    """
    Decides if code is valid or if it must be fixed
    """
    errors = state.get("validation_errors", [])
    attempts = state.get("attempts", 0)
    MAX_ATTEMPTS = 3

    if len(errors) == 0:
        print("[Router 2]: Without syntax errors. Succesful")
        return "user_approval"

    elif len(errors) > 0 and attempts < MAX_ATTEMPTS:
        print(f"[Router 2] Errors detected. Trying agaun (Attempt {attempts + 1}/{MAX_ATTEMPTS})")
        return "generate_code"


    print(f"[Router 2] Attempts limit reached ({attempts}/{MAX_ATTEMPTS})")
    return "end"



def build_graph():
    # 1. Instantiate the graph engine with our schema
    builder = StateGraph(AgentState)

    # 2. Add our worker node
    builder.add_node("analizer", analize_petition_node)
    builder.add_node("generate_code", generate_code_node)
    builder.add_node("validator", validate_code_node)
    builder.add_node("user_approval", save_code_to_disk_node)

    # 3. Define edges
    builder.add_edge(START, "analizer")

    # Condition edge
    builder.add_conditional_edges(
        "analizer", # origin
        route_after_analysis,
        {
            "generate_code": "generate_code",
            "end": END
        }
    )

    # after code generation always go to validator
    builder.add_edge("generate_code", "validator")


    # second decision after validation
    builder.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "generate_code": "generate_code",
            "user_approval": "user_approval",
            "end": END
        }
    )

    builder.add_edge("user_approval", END)

    #builder.add_edge("analizer", END)

    # initialize memory
    memory = MemorySaver()

    # 4. Compile to convert it into an executable app
    return builder.compile(checkpointer=memory)

if __name__ == "__main__":

    from langgraph.types import Command

    app = build_graph()

    config = {"configurable": {"thread_id":"test-session-1"}}

    initial_state = {
        "user_request": "Escribe una funcion de python para sumar dos numeros",
        "petition_analysis": None,
        "code": None,
        "attempts": 0,
        "validation_errors": [],
        "user_approval": None
    }

    print("\n--- INICIANDO EJECUCIÓN ---")
    # 2. Primera ejecución. El grafo correrá hasta llegar al nodo con interrupt()
    app.invoke(initial_state, config)

    # 3. Comprobamos el estado del grafo
    snapshot = app.get_state(config)

    # snapshot.next nos dice qué nodo(s) están pendientes de ejecutarse.
    # Si está pausado por un interrupt, nos mostrará el nodo en el que se pausó.
    print("\n--- ESTADO DEL GRAFO TRAS LA PRIMERA LLAMADA ---")
    print("Nodos pendientes (pausados):", snapshot.next)

    # Podemos extraer el mensaje que enviamos en el interrupt()
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        info_interrupcion = snapshot.tasks[0].interrupts[0].value
        print("\nMensaje desde el nodo:", info_interrupcion["message"])
        print("Código a revisar:\n", info_interrupcion["code"])

    # 4. Simulamos que el usuario lee la consola y decide aprobarlo
    print("\n[Simulación de Humano] Escribiendo 'sí' para aprobar...")
    decision_del_usuario = {"approved": True} 

    # 5. Reanudamos la ejecución inyectando la respuesta con Command
    print("\n--- REANUDANDO EJECUCIÓN ---")
    resultado_final = app.invoke(Command(resume=decision_del_usuario), config)
    
    print("\n--- EJECUCIÓN FINALIZADA ---")
    print("Estado final del user_approval:", resultado_final.get("user_approval"))