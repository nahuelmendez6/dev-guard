import os
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

# Cargamos las variables de entorno
load_dotenv()

def get_llm(temperature float | None = None) -> BaseChatModel:
    """
    Función fábrica que devuelve una instacia de un modelo de chat compatible
    con LangChain/LangGraph según las variables configuradas en .env
    """
    provider = os.getenv("LLM_PROVIDER", "google").lower().strip()
    model_name = os.getenv("LLM_MODEL_NAME", "gemini-3.8-flash").strip()

    # Si no se pasa temperatura por parámetro, se lee desde .env
    if temperature is None:
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    if provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key.startswith("YOUR_"):
            raise ValueError("La variable de entorno GOOGLE_API_KEY no está configurada correctamente.")

        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key
        )

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("YOUR_"):
            raise ValueError("La variable de entorno OPENAI_API_KEY no está configurada correctamente.")

        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=api_key
        )

    elif provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key.startswith("YOUR_"):
            raise ValueError("La variable de entorno GROQ_API_KEY no está configurada correctamente.")

        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model_name,
            temperature=temperature,
            groq_api_key=api_key
        )

    else:
        raise ValueError(
            f"Proveedor '{provider}' no soportado."
            "Usa 'google', 'openai' o 'groq' como valor de la variable de entorno LLM_PROVIDER."
        )

    if __name__ == "__main__":
        # Bloque de prueba rapida para verificar la configuracion sin hacer llamadas a la API aun
        try:
            llm = get_llm()
            print("✅ Configuración agnóstica verificada con éxito.")
            print(f"   • Clase instanciada : {llm.__class__.__name__}")
            print(f"   • Proveedor activo  : {os.getenv('LLM_PROVIDER')}")
            print(f"   • Modelo configurado: {os.getenv('LLM_MODEL')}")
        except Exception as e:
            print(f"❌ Error de configuración: {e}")