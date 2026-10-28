import langchain

langchain.debug = True

from langgraph.graph import StateGraph, START, END
from state import AgentState
from nodes import analize_petition_node

def build_graph():
    # 1. Instantiate the graph engine with our schema
    builder = StateGraph(AgentState)

    # 2. Add our worker node
    builder.add_node("analizer", analize_petition_node)

    # 3. Define edges
    builder.add_edge(START, "analizer")
    builder.add_edge("analizer", END)

    # 4. Compile to convert it into an executable app
    return builder.compile()

if __name__ == "__main__":
    app = build_graph()

    # Define initial state
    initial_state = {
        "user_request": "Por favor, créame una función en JavaScript para sumar dos números.",
        "petition_analysis": None
    }

    print("🚀 Iniciando ejecución del grafo...")
    # app.invoke arranca el motor pasándole el estado inicial
    resultado_final = app.invoke(initial_state)

    print("\n✅ Grafo terminado. Estado final en memoria:")
    print(f"Es código: {resultado_final['petition_analysis'].is_code_task}")
    print(f"Lenguaje : {resultado_final['petition_analysis'].language_detected}")
    print(f"Intención: {resultado_final['petition_analysis'].main_intent}")