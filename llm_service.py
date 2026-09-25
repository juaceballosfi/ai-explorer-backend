from dotenv import load_dotenv
import httpx
from fastapi import HTTPException
import os

load_dotenv()

FI_APPS_API_URL = os.getenv("FI_APPS_API_URL")
FI_APPS_API_KEY = os.getenv("FI_APPS_API_KEY")


async def call_llm(
    model: str, messages: list, temperature: float = 0.3, timeout: float = 30.0
) -> str:
    """
    Interactúa con la API externa para generar respuestas usando Modelos de Lenguaje (LLMs).
    
    Toma un historial de mensajes y una configuración específica (modelo, temperatura) y realiza
    una petición HTTP asíncrona al servicio de IA. Maneja los errores de red y de API 
    convirtiéndolos en excepciones HTTP estándar.
    
    Args:
        model (str): El nombre del modelo a utilizar (ej. "Reasoning", "Performance").
        messages (list): Lista de diccionarios representando el historial conversacional.
                         Formato esperado: [{"role": "system|user|assistant", "content": "..."}]
        temperature (float, optional): Grado de creatividad de la respuesta (0.0 a 1.0). Por defecto 0.3.
        timeout (float, optional): Tiempo de espera máximo en segundos. Por defecto 30.0.
        
    Returns:
        str: El texto de la respuesta generada por el modelo.
        
    Raises:
        HTTPException: (503) Si hay problemas de conexión, o el código de error correspondiente 
                       si la API remota rechaza la petición.
    """
    payload = {"model": model, "messages": messages, "temperature": temperature}

    headers = {
        "Authorization": f"Bearer {FI_APPS_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(FI_APPS_API_URL, headers=headers, json=payload)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail=f"No se pudo conectar con Fi Apps: {str(e)}"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Error en la API de Fi Apps: {response.text}",
        )

    llm_result = response.json()
    return llm_result["choices"][0]["message"]["content"]
