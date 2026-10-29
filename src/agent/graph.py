import langchain

langchain.debug = True

from langgraph.graph import StateGraph, START, END
from state import AgentState
from nodes import analize_petition_node, generate_code_node


# 1. Deterministic routing function
def route_after_analysis(state: AgentState) -> str:
    """
    Decides if generate code or finish
    """
    analysis = state.get("petition_analysis")

    if analysis and analysis.is_code_task:
        print("[Router]: Routing to code generation...")
        return "generate_code"

    print("[Router] Finishing execution.")
    return "end"




def build_graph():
    # 1. Instantiate the graph engine with our schema
    builder = StateGraph(AgentState)

    # 2. Add our worker node
    builder.add_node("analizer", analize_petition_node)
    builder.add_node("generate_code", generate_code_node)

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


    builder.add_edge("analizer", END)

    # 4. Compile to convert it into an executable app
    return builder.compile()

if __name__ == "__main__":
    app = build_graph()

    # Define initial state
    
    # Case 1: Valid request
    print("\n --- TEST 1: VALID REQUEST ---")
    valid_state = {
        "user_request": "Escribe una función de Python para validar que una contraseña tenga al menos 8 caracteres y un número.",
        "petition_analysis": None,
        "code": None,
        "attempts": 0
    }

    result = app.invoke(valid_state)
    print(f"\n Test 1 result: {result['code'].code if result.get('code') else 'No code'}")

    # Case 2: Invalid petition 
    print("\n --- TEST 1: NO VALID REQUEST ---")
    no_valid_state = {
        "user_request": "¿Cual es la capital de Francia?",
        "petition_analysis": None,
        "code": None,
        "attempts": 0
    }
    
    invalid_result = app.invoke(no_valid_state)
    print(f"\n Test 2 result: {invalid_result.get('code', 'Correcto, no se genero codigo')}")
