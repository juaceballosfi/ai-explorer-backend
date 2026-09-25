from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json
import os
import shutil

from database import get_connection, init_db
from models import ChatMessage, DocumentUploadResponse
from llm_service import call_llm

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
app = FastAPI(title="AI Knowledge Explorer API", root_path=os.getenv("ROOT_PATH", ""))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

init_db()


# --- SEGURIDAD: API key propia para proteger endpoints sensibles ---
def verificar_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("AI_EXPLORER_API_KEY"):
        raise HTTPException(status_code=401, detail="API key inválida")


# --- ENDPOINTS ---


@app.get("/health")
def health_check():
    """
    Verifica el estado de salud de la API.

    Este endpoint público no requiere autenticación y se utiliza para
    comprobar rápidamente si el servidor web está activo y respondiendo
    correctamente a las peticiones HTTP.

    Returns:
        dict: Un diccionario con el estado 'ok' y un mensaje de confirmación.
    """
    return {"status": "ok", "message": "API corriendo correctamente"}


@app.get(
    "/documents",
    dependencies=[Depends(verificar_api_key)],
)
def list_documents():
    """
    Recupera una lista de todos los documentos almacenados en la base de datos.

    Obtiene los metadatos de los documentos ordenados por fecha de subida de 
    forma descendente (los más recientes primero). No devuelve el contenido 
    ni el análisis de los mismos, solo la información general.

    Returns:
        list: Lista de diccionarios con la información básica de cada documento 
              (id, nombre, tamaño y fecha de subida).
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, size, upload_date FROM documents ORDER BY upload_date DESC"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows


@app.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(verificar_api_key)],
)
async def upload_document(file: UploadFile = File(...)):
    """
    Sube un nuevo documento al servidor para su posterior análisis.

    Guarda el archivo de texto en el sistema de archivos local de forma segura
    y registra sus metadatos (nombre, tamaño, ubicación y fecha) en la base
    de datos. Cuenta con validación de tamaño para prevenir archivos muy pesados.

    Args:
        file (UploadFile): El archivo a subir enviado a través de form-data.

    Returns:
        dict: Diccionario que contiene el ID asignado, nombre del archivo,
              tamaño y un mensaje de éxito.

    Raises:
        HTTPException: Si el archivo supera el límite de tamaño permitido.
    """
    # Mover el cursor al final del archivo para obtener su tamaño en bytes
    file.file.seek(0, 2)
    file_size = file.file.tell()
    # Devolver el cursor al inicio para poder leer y guardar el archivo correctamente
    file.file.seek(0)

    if file_size > 150 * 1024:
        raise HTTPException(
            status_code=400, detail="El archivo supera el límite recomendado de 150 KB."
        )

    # Sanitizamos el nombre para evitar path traversal (ej. "../../algo")
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (name, size, local_url, upload_date) VALUES (%s, %s, %s, %s)",
        (safe_filename, file_size, file_path, datetime.now().isoformat()),
    )
    doc_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return {
        "id": doc_id,
        "name": safe_filename,
        "size": file_size,
        "message": "Archivo subido y metadatos guardados correctamente.",
    }


@app.post(
    "/documents/{doc_id}/analyze",
    dependencies=[Depends(verificar_api_key)],
)
async def analyze_document(doc_id: int):
    """
    Procesa y analiza el contenido de un documento previamente subido.

    Lee el archivo desde el almacenamiento local y utiliza un modelo de lenguaje
    (LLM Reasoning) avanzado para extraer información clave estructurada: un resumen,
    palabras clave, categoría y un listado de preguntas y respuestas relevantes.
    El resultado en formato JSON se almacena en la base de datos para consultas futuras.

    Args:
        doc_id (int): El identificador único del documento a analizar.

    Returns:
        dict: Objeto indicando éxito junto con el análisis estructurado.

    Raises:
        HTTPException: (404) Si el documento no se encuentra, o (500) si falla la lectura.
    """
    # 1. Buscar la ruta del archivo y cerrar la conexión de inmediato
    # Es crucial cerrar la conexión rápido para no agotar el pool de conexiones durante la espera del LLM
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT local_url FROM documents WHERE id = %s", (doc_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    local_url = row[0]

    # 2. Leer el archivo (no necesita conexión a MySQL)
    try:
        with open(local_url, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo archivo: {str(e)}")

    prompt_sistema = """
    Eres un arquitecto de software analizando documentación.
    Analiza el documento proporcionado y devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura exacta:
    {
        "resumen": "string",
        "keywords": ["keyword1", "keyword2"],
        "categoria": "string",
        "preguntas_respuestas": [{"pregunta": "string", "respuesta": "string"}]
    }
    No incluyas markdown, saludos, ni texto fuera del JSON.
    """

    # 3. Llamar al servicio LLM externo (operación de red lenta)
    # Se usa temperatura baja (0.1) para obtener respuestas más deterministas y ceñidas al prompt
    analysis_text = await call_llm(
        model="Reasoning",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": content},
        ],
        temperature=0.1,
    )
    # Limpieza básica para asegurar que el string sea un JSON válido en caso de que el LLM incluya formato de código Markdown
    analysis_text = analysis_text.replace("```json", "").replace("```", "").strip()

    # 4. Abrir una conexión NUEVA y temporal solo para guardar el resultado final
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE documents SET analysis_result = %s WHERE id = %s",
        (analysis_text, doc_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Análisis completado", "analysis": json.loads(analysis_text)}


@app.get(
    "/documents/{doc_id}/analysis",
    dependencies=[Depends(verificar_api_key)],
)
def get_analysis(doc_id: int):
    """
    Recupera el análisis de un documento almacenado en la base de datos.

    Consulta y devuelve la estructura JSON con el análisis detallado (resumen,
    keywords, categoría, etc.) generado previamente por el endpoint de análisis.

    Args:
        doc_id (int): El identificador único del documento.

    Returns:
        dict: El análisis estructurado del documento en formato JSON.

    Raises:
        HTTPException: (404) Si el documento no existe o si todavía
                       no ha sido analizado.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT analysis_result FROM documents WHERE id = %s", (doc_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row or not row[0]:
        raise HTTPException(
            status_code=404, detail="Análisis no encontrado o aún no procesado"
        )

    return json.loads(row[0])


@app.get(
    "/documents/{doc_id}/chat",
    dependencies=[Depends(verificar_api_key)],
)
def get_chat_history(doc_id: int):
    """
    Recupera el historial de chat persistido para un documento específico.

    Consulta la base de datos para obtener todos los mensajes (preguntas del usuario 
    y respuestas del asistente) asociados a un documento, ordenados cronológicamente.
    
    Args:
        doc_id (int): El identificador único del documento.

    Returns:
        list: Lista de mensajes en formato de diccionario conteniendo el rol,
              el contenido del mensaje y la fecha de creación.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT role, content, created_at FROM chat_messages WHERE document_id = %s ORDER BY created_at ASC",
        (doc_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows


@app.post(
    "/documents/{doc_id}/chat",
    dependencies=[Depends(verificar_api_key)],
)
async def chat_with_document(doc_id: int, request: ChatMessage):
    """
    Permite interactuar conversacionalmente con un documento específico persistiendo memoria.

    Implementa un chat contextual donde el documento sirve como base de
    conocimiento. El LLM recibe el contenido del documento, recupera el historial de la
    conversación previa directamente de la base de datos y la nueva pregunta del usuario, 
    para generar respuestas coherentes. Finalmente, guarda la interacción en la base de datos.

    Args:
        doc_id (int): El ID del documento sobre el cual se va a consultar.
        request (ChatMessage): Objeto que contiene la nueva pregunta del usuario.

    Returns:
        dict: Un diccionario con la pregunta formulada y la respuesta generada
              por el asistente virtual.

    Raises:
        HTTPException: (404) Si el documento no existe, o (500) por errores de lectura.
    """
    # 1. Recuperar ubicación del archivo y liberar conexión a la BBDD inmediatamente
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT local_url FROM documents WHERE id = %s", (doc_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    local_url = row[0]

    # 2. Leer el texto completo del documento
    try:
        with open(local_url, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo archivo: {str(e)}")

    # 3. Construir la lista de mensajes: system -> history -> pregunta actual
    prompt_sistema = f"""
    Eres un asistente técnico que ayuda a analizar documentación de software.
    Responde basándote ÚNICAMENTE en el contexto proporcionado.

    CONTEXTO DEL DOCUMENTO:
    {content}
    """

    # Recuperar el historial de chat de la base de datos
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT role, content FROM chat_messages WHERE document_id = %s ORDER BY created_at ASC",
        (doc_id,),
    )
    historial = cursor.fetchall()
    cursor.close()
    conn.close()

    messages = [{"role": "system", "content": prompt_sistema}]

    for msg in historial:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": request.content})

    # 4. Ejecutar la llamada asíncrona al LLM
    # Se usa el modelo 'Performance' (más rápido para chat) y una temperatura moderada (0.3)
    # para permitir cierta naturalidad en la respuesta sin perder precisión respecto al contexto.
    respuesta_texto = await call_llm(
        model="Performance",
        messages=messages,
        temperature=0.3,
        timeout=30.0,  # Timeout superior por si el contexto procesado es muy amplio
    )

    # 5. Persistir la interacción actual en la base de datos
    ahora = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_messages (document_id, role, content, created_at) VALUES (%s, %s, %s, %s)",
        (doc_id, "user", request.content, ahora),
    )
    cursor.execute(
        "INSERT INTO chat_messages (document_id, role, content, created_at) VALUES (%s, %s, %s, %s)",
        (doc_id, "assistant", respuesta_texto, ahora),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"pregunta": request.content, "respuesta": respuesta_texto}
