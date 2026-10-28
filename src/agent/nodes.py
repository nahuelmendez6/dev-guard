from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState, PetitionAnalisys
from llm import get_llm

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
    return {"petition_analysis": response}