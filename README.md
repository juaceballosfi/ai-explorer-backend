# 🧠 AI Knowledge Explorer API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-00000F?style=for-the-badge&logo=mysql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

AI Knowledge Explorer es una API robusta construida con **FastAPI** diseñada para la gestión, análisis automatizado y exploración conversacional de documentos utilizando Modelos de Lenguaje Avanzados (LLMs).

---

## ✨ Características Principales

- **📂 Gestión de Documentos:** Sube de forma segura archivos de texto y almacena sus metadatos (tamaño, ruta, fecha) en una base de datos MySQL relacional.
- **🔍 Análisis Estructurado Inteligente:** Emplea un modelo LLM especializado en razonamiento para extraer automáticamente información en un esquema JSON validado con:
  - Resumen ejecutivo del documento.
  - Palabras clave (Keywords).
  - Categorización.
  - Posibles preguntas y respuestas (Q&A).
- **💬 Interacción Conversacional Contextual:** Permite hacer preguntas sobre el documento subido manteniendo memoria conversacional en cada sesión. El historial de chat es persistido automáticamente en la base de datos para retomar la conversación en cualquier momento.
- **🔒 Seguridad por API Key:** Rutas protegidas mediante un header personalizado (`x-api-key`) para restringir el acceso a operaciones sensibles de la API.
- **🐳 Infraestructura Preparada:** Orquestación de la base de datos MySQL lista para desarrollo utilizando Docker Compose.

---

## 📋 Requisitos Previos

- **Python 3.8+**
- **Docker** y **Docker Compose** (para ejecutar la instancia de la base de datos)
- Una clave de acceso válida (API Key) para el servicio LLM de Fi Apps.

---

## ⚙️ Configuración del Entorno

1. **Clonar el repositorio y acceder al directorio:**
   ```bash
   cd knowledge-explorer
   ```

2. **Variables de Entorno (`.env`):**
   Crea o renombra el archivo `.env.example` a `.env` y configura las siguientes variables para tu entorno:

   ```env
   # Configuración de Base de Datos MySQL
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=tu_password
   MYSQL_DATABASE=knowledge_db

   # Seguridad de la API Propia
   AI_EXPLORER_API_KEY=tu_api_key_secreta_para_proteger_los_endpoints

   # Configuración de LLM (API Externa Fi Apps)
   FI_APPS_API_URL=https://api.fiapps.com/v1/chat/completions # O la URL correspondiente
   FI_APPS_API_KEY=tu_token_de_fi_apps
   ```

3. **Desplegar la Base de Datos MySQL:**
   ```bash
   docker-compose up -d
   ```

4. **Instalar Dependencias de Python:**
   Es muy recomendable utilizar un entorno virtual (venv):
   ```bash
   python -m venv venv
   
   # Activar el entorno virtual en Windows:
   .\venv\Scripts\activate
   # En Linux/macOS:
   # source venv/bin/activate
   
   pip install -r requirements.txt
   ```

---

## 🚀 Ejecución de la API

Para levantar el servidor de desarrollo (que incluye recarga automática al detectar cambios):

```bash
uvicorn main:app --reload
```

El servidor estará escuchando en `http://localhost:8000`.

### 📚 Documentación Interactiva (Swagger UI)
FastAPI genera automáticamente documentación interactiva. Una vez ejecutada la API, puedes probar directamente los endpoints desde el navegador en:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

*(Nota: En Swagger, deberás añadir tu `AI_EXPLORER_API_KEY` temporalmente si usas extensiones o clientes HTTP para realizar pruebas en las rutas protegidas).*

---

## 🌐 Endpoints Principales

| Método | Endpoint | Descripción | Autenticación |
| :--- | :--- | :--- | :---: |
| `GET` | `/health` | Verifica si el servicio de la API está en línea. | No |
| `GET` | `/documents` | Obtiene el listado de todos los documentos ordenados por fecha. | **Sí** |
| `POST` | `/documents/upload` | Sube un archivo de texto para su almacenamiento y registro en BBDD. (Máximo: 150 KB). | **Sí** |
| `POST` | `/documents/{doc_id}/analyze` | Desencadena el análisis con LLM (razonamiento) de un documento y guarda resultados. | **Sí** |
| `GET` | `/documents/{doc_id}/analysis` | Recupera el JSON con el análisis estructurado (Resumen, Keywords, Q&A) almacenado. | **Sí** |
| `GET` | `/documents/{doc_id}/chat` | Obtiene el historial completo de la conversación guardada para un documento. | **Sí** |
| `POST` | `/documents/{doc_id}/chat` | Permite enviar preguntas sobre el documento (el historial se recupera y guarda de la BBDD). | **Sí** |

**Header de Autenticación Requerido:**
Para consultar los endpoints protegidos (marcados con **Sí**), incluye en las peticiones HTTP la cabecera `x-api-key` con el valor que configuraste en tu `.env` bajo `AI_EXPLORER_API_KEY`.

---

## 🏗️ Arquitectura y Estructura del Código

- **`main.py`:** Punto de entrada de la aplicación FastAPI. Define y orquesta las rutas (endpoints), la validación de archivos, el CORS y la autenticación.
- **`database.py`:** Administra la creación de conexiones a MySQL utilizando `mysql-connector-python` e inicializa automáticamente el esquema de tablas si no existe.
- **`models.py`:** Contiene los esquemas de validación de datos basados en Pydantic (`ChatRequest`, `DocumentUploadResponse`) para los inputs y outputs de la API.
- **`llm_service.py`:** Módulo asíncrono para gestionar la comunicación HTTP (vía `httpx`) con el proveedor de LLM. Incluye manejo de timeouts y delegación de excepciones de red.
- **`docker-compose.yml`:** Definición IaC (Infrastructure as Code) para desplegar el contenedor de MySQL con las variables de entorno asociadas de forma instantánea.
