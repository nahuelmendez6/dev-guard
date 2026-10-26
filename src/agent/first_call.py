from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from llm import get_llm

# 1. Definir el esquema estrucuto
class AnalisisPeticion(BaseModel):
    es_tarea_de_codigo: bool = Field(description="True si el usuario pide escribir, revisar o analizar codigo")
    lenguaje_detectado: str = Field(description="Lenguaje de programacion detectado en la peticion del usuario, si aplica")
    intencion_principal: str = Field(description="Resumen de maximo 5 palabras de la intencion principal del usuario")

def probar_llamada_estructurada():
    # 2. Instanciar el modelo
    llm = get_llm(temperature=0.0)

    # 3. Unir el modelo con nuestro esquema Pydantic
    # Esto transforma el LLM: en lugar de devolver texto, devolverá un objeto AnalisisPeticion
    structured_llm = llm.with_structured_output(AnalisisPeticion)

    # 4. Crear el historial de mensajes
    mensajes = [
        SystemMessage(content="Eres un analizador de peticiones técnicas. Extrae la información solicitada."),
        HumanMessage(content="Necesito que escribas una función de Python para validar si una contraseña es segura.")
    ]

    print("⏳ Enviando petición al LLM...")
    
    # 5. Invocar al modelo
    respuesta = structured_llm.invoke(mensajes)

    # 6. Inspeccionar el resultado
    print("\n✅ ¡Respuesta recibida!")
    print(f"Tipo de dato en Python: {type(respuesta)}")
    print("-" * 30)
    # Como es un objeto Pydantic, podemos acceder a sus atributos con punto (.)
    print(f"Es código : {respuesta.es_tarea_de_codigo}")
    print(f"Lenguaje  : {respuesta.lenguaje_detectado}")
    print(f"Intención : {respuesta.intencion_principal}")


if __name__ == "__main__":
    probar_llamada_estructurada()