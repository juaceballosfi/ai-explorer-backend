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
    Envía una conversación a un modelo de Fi Apps y devuelve el texto de la respuesta.
    Lanza HTTPException si Fi Apps responde con error o si no se puede alcanzar la API.
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
