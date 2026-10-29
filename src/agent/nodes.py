from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState, PetitionAnalisys, GeneratedCode
from llm import get_llm
from tools import validate_syntax

def analize_petition_node(state: AgentState) -> dict:
    """
    This node receives the user request and uses the LLM to analize it
    """
    # 1. Instance model
    llm = get_llm(temperature=0.0)
    structure_llm = llm.with_structured_output(PetitionAnalisys)

    # 2. Read request from state
    messages = [
        SystemMessage(content="You are an analyzer of technical requests. Extract the information."),
        HumanMessage(content=state["user_request"])
    ]

    response = structure_llm.invoke(messages)

    # 3. Return only the part of the state that we want to update
    return {"petition_analysis": response, "attempts": state.get("attempts", 0) + 1}



def generate_code_node(state: AgentState) -> dict:
    """
    Node that receives the analysis and generates code based on the intent
    """
    print(f"[Node: Generator] Writing code in {state['petition_analysis'].language_detected}...")
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(GeneratedCode)

    prompt = f"""Write code to solve this task: '{state['petition_analysis'].main_intent}'.
            The user originally requested: '{state['user_request']}'
            Requested language: {state['petition_analysis'].language_detected}
            Strictly return the code without markdown formatting (without ```python, etc.)."""

    # SELF-CORRECTION logic
    previous_errors = state.get("validation_errors", [])
    if len(previus_errors) > 0:
        prompt += "\n\n ATTENTION: Your previous attempt failed with the following syntax errors: \n"
        for error in previous_errors:
            prompt += f"- {error}\n"
        prompt += "\n Fix the code based strictly on these errors."



    response = structured_llm.invoke([HumanMessage(content=prompt)])

    return {"code": response}


def validate_code_node(state: AgentState) -> dict:
    """
    Deterministc Node - Code validator
    """

    print("[Node: Validator] Inspecting code syntax")

    # Get generate code from previous step
    code = state["code"].code
    language = state["petition_analysis"].language_detected

    # the tool just validate python code (for now)
    if language.lower() == "python":
        errors = validate_syntax(code)

    else:
        errors = []

    if len(errors) > 0:
        print(f"Found len{errors} errors.")
    else:
        print("Syntactically correct code")

    return {"validation_errors": errors}