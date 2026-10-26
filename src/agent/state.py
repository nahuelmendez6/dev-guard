from typing import TypedDict
from pydantic import BaseModel, Field

# 1. Data schema for the agent state
class PetitionAnalisys(BaseModel):
    is_code_task: bool = Field(description="True if the user is requesting to write, review, or analyze code")
    language_detected: str = Field(description="Detected programming language in the user's request, if applicable")
    main_intent: str = Field(description="Summary of the user's main intent in maximum 5 words")


# 2. TypedDict for the agent state
class AgentState(TypedDict):
    user_request: str
    petition_analysis: PetitionAnalisys | None