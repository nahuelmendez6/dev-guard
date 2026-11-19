from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState, PetitionAnalisys, GeneratedCode
from llm import get_llm
from tools import validate_syntax
from langgraph.types import interrupt

def analize_petition_node(state: AgentState) -> dict:
    """
    This node receives the user request and uses the LLM to analize it
    """
    # 1. Instance model
    llm = get_llm(temperature=0.0)
    structure_llm = llm.with_structured_output(PetitionAnalisys)

    previous_code = state.get("code")
    previous_analysis = state.get("petition_analysis")

    # 2. Read request from state
    messages = [
        SystemMessage(content="""
            You are an analyzer of technical requests.

            Analyze the user's request and determine:
            - Whether it is a programming task.
            - What programming language is required.
            - What the user wants to accomplish.

            Consider the previous code and analysis when interpreting
            requests that refer to previous work.
        """),
        HumanMessage(content=f"""
            Previous analysis:
            {previous_analysis}

            Previous code:
            {previous_code}

            New user request:
            {state["user_request"]}
        """)
    ]

    response = structure_llm.invoke(messages)

    # 3. Return only the part of the state that we want to update
    # Reinicio de límites por turno
    # Asegura que cada nueva consulta empiece con presupuesto fresco de reintentos
    return {
        "petition_analysis": response,
        "attempts": 0,
        "validation_errors": [],
        "user_approval": None    
    }



def generate_code_node(state: AgentState) -> dict:
    """
    Node that receives the analysis and generates code based on the intent
    """
    print(f"[Node: Generator] Writing code in {state['petition_analysis'].language_detected}...")
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(GeneratedCode)

    current_code_obj = state.get("code")
    current_code_str = current_code_obj.code if current_code_obj else None
    previous_errors = state.get("validation_errors", [])

    prompt = f"""Write code to solve this task: '{state['petition_analysis'].main_intent}'.
            The user originally requested: '{state['user_request']}'
            Requested language: {state['petition_analysis'].language_detected}
            Strictly return the code without markdown formatting (without ```python, etc.).
            IMPORTANT: Always provide the complete, fully implemented  
            function with its body and return statement. Never return  
            only the function signature.
            """

    # SELF-CORRECTION logic
    
    if len(previous_errors) > 0:
        prompt += "\n\n ATTENTION: Your previous attempt failed with the following syntax errors: \n"
        for error in previous_errors:
            prompt += f"- {error}\n"
        
        if current_code_str:
            prompt += f"\nCode that caused the syntax errors: \n{current_code_str}\n"

            prompt += "\n Fix the code based strictly on these errors."

    elif current_code_str:
        prompt += f"\n\nExisting base code to modify:\n{current_code_str}\n"
        prompt += "\nModify or rewrite this code to satisfy the user request."

    response = structured_llm.invoke([HumanMessage(content=prompt)])

    return {"code": response, "attempts": state.get("attempts", 0) + 1}


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
        print(f"Found {len(errors)} errors.")
    else:
        print("Syntactically correct code")

    return {"validation_errors": errors}


def save_code_to_disk_node(state: AgentState) -> dict:
    """
    Node that stops execution to ask for user approval to save the code to disk
    """
    print("\n[Node: Human in the Loop] Esperando aprobación del usuario...")

    # extract code from state
    code_str = state["code"].code if state.get("code") else "<no code generated>"

    # call interrupt
    decision = interrupt({        
        "action":"approve_code",
        "message": "The code has been generated and validated. Do you approve saving it to disk?",
        "code": code_str}
    )

    # when the graph is resumed, the user decision will be stored in the state
    # and execution will continuae from here
    print(f"\n[Node: Human in the Loop] User answer: {decision}")

    is_approved = decision.get("approved", False) if isinstance(decision, dict) else bool(decision)
    target_file = decision.get("filename", "generated_code.py") if isinstance(decision, dict) else "generated_code.py"


    if is_approved and code_str:
        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(code_str)
            print(f"💾 [HITL]: Código guardado con éxito en '{target_file}'.")
        except Exception as e:
            print(f"❌ [HITL]: Error al guardar el código en '{target_file}': {e}")

    else:
        print("🛑 [HITL]: Operación cancelada por el usuario.")

    return {"user_approval": is_approved}