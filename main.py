from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json
import os
import shutil

from database import get_connection, init_db
from models import ChatRequest, DocumentUploadResponse
from llm_service import call_llm

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
import os

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


# --- ENDPOINTS ---


@app.get("/health")
def health_check():
    """Fase 1: Endpoint de comprobación del servidor"""
    return {"status": "ok", "message": "API corriendo correctamente"}


@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Fase 2: Subir archivo y guardar metadatos"""
    file.file.seek(0, 2)
    file_size = file.file.tell()
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


@app.post("/documents/{doc_id}/analyze")
async def analyze_document(doc_id: int):
    """Fase 3: Extraer texto y generar análisis estructurado con el modelo Reasoning"""
    # 1. Buscar la ruta del archivo y cerrar la conexión de inmediato
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

    # 3. Llamar al LLM (operación lenta, sin conexión MySQL abierta mientras tanto)
    analysis_text = await call_llm(
        model="Reasoning",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": content},
        ],
        temperature=0.1,
    )
    analysis_text = analysis_text.replace("```json", "").replace("```", "").strip()

    # 4. Abrir una conexión NUEVA solo para guardar el resultado
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


@app.get("/documents/{doc_id}/analysis")
def get_analysis(doc_id: int):
    """Fase 3: Recuperar el análisis previamente guardado"""
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


@app.post("/documents/{doc_id}/chat")
async def chat_with_document(doc_id: int, request: ChatRequest):
    """Fase 4: Chat con memoria usando el rol assistant"""
    # 1. Conexión + SELECT local_url, cerrada de inmediato
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

    messages = [{"role": "system", "content": prompt_sistema}]

    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": request.nueva_pregunta})

    # 4. Llamar al LLM (conexión MySQL ya cerrada durante esta espera)
    respuesta_texto = await call_llm(
        model="Performance",
        messages=messages,
        temperature=0.3,
        timeout=30.0,
    )

    return {"pregunta": request.nueva_pregunta, "respuesta": respuesta_texto}
