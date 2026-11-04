from typing import TypedDict
from pydantic import BaseModel, Field

# 1. Data schema for the agent state
class PetitionAnalisys(BaseModel):
    is_code_task: bool = Field(
        description="Obligatorio. True si el usuario pide escribir, revisar o analizar código. IMPORTANTE: Debe ser un valor booleano nativo (true o false), NUNCA un string."
    )
    language_detected: str = Field(
        description="Lenguaje de programación detectado. IMPORTANTE: Usa exactamente la clave 'language_detected' sin espacios. Si no hay lenguaje, devuelve 'None'."
    )
    main_intent: str = Field(
        description="Resumen de la intención principal del usuario en máximo 5 palabras."
    )

# 2. Second step schema (code generation)
class GeneratedCode(BaseModel):
    code: str = Field(description="Raw source code")
    explanation: str = Field(description="Brief explanation of the approach")


# 3. Graph global state (memory)
class AgentState(TypedDict):
    user_request: str
    petition_analysis: PetitionAnalisys | None
    code: GeneratedCode | None
    attempts: int
    validation_errors: list[str]
    user_approval: bool | None