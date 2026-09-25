# AI Knowledge Explorer API

AI Knowledge Explorer es una API construida con **FastAPI** que permite la gestión, análisis y chat interactivo con documentos utilizando modelos de lenguaje (LLM).

## Características Principales

*   **Subida de documentos:** Permite cargar archivos locales (hasta 150 KB) y guardar sus metadatos en una base de datos.
*   **Análisis automatizado:** Extrae un resumen estructurado (palabras clave, categoría y Q&A) del documento usando un LLM configurado para razonamiento.
*   **Chat interactivo (RAG):** Permite mantener una conversación en base al contenido del documento y al historial de mensajes enviados.
*   **Base de Datos Relacional:** Utiliza MySQL para persistir los metadatos de los documentos y los resultados del análisis.
*   **Contenedores:** Incluye configuración de Docker Compose para desplegar fácilmente la base de datos MySQL.

## Requisitos Previos

*   Python 3.8+
*   Docker y Docker Compose (para la base de datos MySQL)

## Configuración y Ejecución

1.  **Clonar y preparar el entorno:**
    Renombra el archivo `.env.example` a `.env` y configura tus credenciales, incluyendo la clave de API para el servicio LLM de Fi Apps (`FI_APPS_API_KEY`).

2.  **Iniciar la Base de Datos:**
    Levanta el contenedor de MySQL con Docker Compose:
    ```bash
    docker-compose up -d
    ```

3.  **Instalar las dependencias:**
    Crea un entorno virtual y asegúrate de instalar las dependencias requeridas (FastAPI, Uvicorn, python-dotenv, mysql-connector-python, httpx, etc.).

4.  **Ejecutar la API:**
    Levanta el servidor con Uvicorn:
    ```bash
    uvicorn main:app --reload
    ```
    La API estará disponible en `http://localhost:8000`. Puedes consultar la documentación interactiva (Swagger) en `http://localhost:8000/docs`.

## Endpoints Principales

*   `GET /health`: Comprueba el estado del servidor.
*   `POST /documents/upload`: Sube un archivo. Retorna el ID generado.
*   `POST /documents/{doc_id}/analyze`: Ejecuta el análisis LLM (Resumen, Categoría, Keywords) sobre el documento.
*   `GET /documents/{doc_id}/analysis`: Recupera el resultado de un análisis previo.
*   `POST /documents/{doc_id}/chat`: Permite hacer preguntas sobre el documento, manteniendo historial.

## Estructura del Proyecto

*   `main.py`: Configuración de FastAPI y definición de endpoints.
*   `database.py`: Manejo de conexión y configuración inicial de la base de datos MySQL.
*   `models.py`: Definición de esquemas Pydantic para validación de requests/responses.
*   `llm_service.py`: Integración asíncrona mediante HTTPX con la API de Fi Apps.
*   `docker-compose.yml`: Definición del servicio MySQL.
