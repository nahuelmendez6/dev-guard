import langchain

langchain.debug = False

from langgraph.graph import StateGraph, START, END
from state import AgentState
from nodes import analize_petition_node, generate_code_node, validate_code_node
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
        return "end"

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
            "end": END
        }
    )

    #builder.add_edge("analizer", END)

    # initialize memory
    memory = MemorySaver()

    # 4. Compile to convert it into an executable app
    return builder.compile(checkpointer=memory)

if __name__ == "__main__":
    app = build_graph()

    # unique id configuration
    config = {"configurable": {"thread_id":"test-session-1"}}

    initial_state = {
        "user_request": "Escribeu una funcion de python para sumar dos numeros",
        "petition_analysis": None,
        "code": None,
        "attempts": 0,
        "validation_errors": []
    }

    result = app.invoke(initial_state, config)
    print("\n Execution 1 finished. Generated Cide: \n", result.get("code").code)

    # Memory test
    print("\n --- MEMORY TEST ---")
    new_request = {
        "user_request": "Ahora modifica ese mismo código para que reste en lugar de sumar.",
        "attempts": 0,
        "validation_errors": []
    }

    result_memory = app.invoke(new_request, config)
    print("\n Execution 2 finished. Updated code: \n", result_memory.get("code").code)