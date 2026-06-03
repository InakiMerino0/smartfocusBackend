### Entregables

[Elevator pitch y Video demo](https://drive.google.com/drive/folders/1-8_IEUGDoZFjD3P0Bwc_E0rWwYzz267X?usp=sharing)


[Informe PDF](https://docs.google.com/document/d/1RWNLFnqIgU6TwNfBVo5oVZ2RNO22OuTfbsB4CIG3P2Y/edit?tab=t.0)


---

# SmartFocus API

### Secretario personal con IA para la vida académica.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)

---

## Menos Estrés, Mejores Resultados

En el mundo académico actual, el tiempo es el recurso más valioso y escaso. La frustración de gestionar múltiples materias, fechas de entrega y exámenes puede ser abrumadora, llevando a muchos estudiantes al límite.

**SmartFocus** nació para solucionar este problema. No es solo otra app de tareas; es un **asistente inteligente diseñado para ser tu secretario personal**. Nuestra visión es crear una herramienta tan intuitiva y potente que se convierta en un aliado fundamental en el éxito académico de sus usuarios, permitiéndoles organizarse sin esfuerzo para que puedan concentrarse en lo que realmente importa: aprender.


---

## Características Actuales (MVP)

Este proyecto es un MVP funcional que sienta las bases del proyecto. Actualmente, la API es capaz de:

*  **Procesamiento de Lenguaje Natural y Voz:** Interactúa con la API usando comandos de texto o de voz para gestionar tu agenda.
*  **Gestión Completa de Materias:** Añade, modifica y elimina tus cursos fácilmente.
*  **Organización de Eventos:** Crea tareas, recordatorios de exámenes o fechas de entrega con descripciones y plazos.
*  **Acciones Inteligentes:** Usa lenguaje natural para realizar operaciones complejas como *"elimina todos los eventos de la materia física"*.
*  **Autenticación Segura:** Sistema robusto basado en JWT para proteger la información de cada usuario.

---

##  Stack Tecnológico

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![AWS](https://img.shields.io/badge/Amazon_AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-8E75B7?style=for-the-badge&logo=google-gemini&logoColor=white)
![CI/CD](https://img.shields.io/badge/CI%2FCD-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)

---

##  Arquitectura y Flujos de Datos

El backend sigue una arquitectura limpia por capas para separar responsabilidades (`routers`, `services`, `integrations`, `models`), garantizando un código mantenible y escalable.

### Diagrama de la Base de Datos

```mermaid
erDiagram
    USUARIOS ||--o{ MATERIAS : "es dueño de"
    MATERIAS ||--o{ EVENTOS : "contiene"

    USUARIOS {
        int id PK
        string username
        string email
        string hashed_password
    }
    MATERIAS {
        int id PK
        string nombre
        string descripcion
        int usuario_id FK
    }
    EVENTOS {
        int id PK
        string nombre
        string descripcion
        datetime fecha
        string estado
        int materia_id FK
    }
```

---

### Flujo de Comando (Texto a Acción)

```mermaid
sequenceDiagram
    participant Client
    participant SmartFocus API
    participant Whisper API
    participant Gemini API
    participant Database

    alt Comando vía Texto
        Client->>SmartFocus API: POST /v1/nl/command (con texto y JWT)
    else Comando vía Audio
        Client->>SmartFocus API: POST /v1/whisper/transcribe (con audio y JWT)
        SmartFocus API->>Whisper API: Enviar audio para transcripción
        Whisper API-->>SmartFocus API: Devolver texto transcrito
    end

    %% --- El flujo común de procesamiento comienza aquí ---
    SmartFocus API->>SmartFocus API: 1. Verificar token JWT del usuario
    SmartFocus API->>Gemini API: 2. Enviar texto para generar plan de acciones
    Gemini API-->>SmartFocus API: 3. Devolver plan (ej: crear evento)
    SmartFocus API->>Database: 4. Ejecutar acciones en la BBDD
    Database-->>SmartFocus API: 5. Confirmar ejecución
    SmartFocus API-->>Client: 6. Devolver resultado (200 OK)
```

---

##  Guía de Inicio Rápido

Sigue estos pasos para clonar, configurar y ejecutar el proyecto en tu máquina local. Se asume que ya tienes **Git**, **Docker** y **Docker Compose** instalados.

### 1. Clona el Repositorio

Abre tu terminal y ejecuta el siguiente comando para descargar el código fuente:

```bash
git clone [https://github.com/InakiMerino0/smartfocusBackend.git](https://github.com/InakiMerino0/smartfocusBackend.git)
```

### 2. Navega al Directorio del Proyecto
Una vez clonado, entra en la carpeta del proyecto:

Bash
```
cd smartfocusBackend
```
### 3. Crea tu Archivo de Configuración (.env)
El proyecto utiliza variables de entorno para gestionar claves de API y configuraciones. Debes crear tu propio archivo .env a partir de la plantilla proporcionada.

Bash
```
cp .env.example .env
```
### 4. Configura tus Variables de Entorno
Ahora, abre el archivo .env que acabas de crear con tu editor de texto preferido. Es crucial que añadas tus propias claves de API y credenciales para que la aplicación funcione.

```
# .env

# --- PostgreSQL Database ---
POSTGRES_USER=tu_usuario_de_db
POSTGRES_PASSWORD=tu_contraseña_segura
POSTGRES_DB=smartfocusdb
DB_HOST=db
DB_PORT=5432

# --- JWT Authentication ---
SECRET_KEY=genera_una_clave_secreta_larga_y_aleatoria
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# --- External APIs ---
GEMINI_API_KEY=tu_clave_de_api_de_google_gemini
OPENAI_API_KEY=tu_clave_de_api_de_openai

```
### 5. Levanta los Servicios con Docker Compose
Este comando leerá el archivo docker-compose.yml, construirá las imágenes de la API y la base de datos, y las ejecutará en contenedores aislados en segundo plano (-d).

Bash
```
docker-compose up -d
```
### 6. Verifica que Funciona 
Si todo ha ido bien, la API estará funcionando. La mejor forma de probarla es a través de la documentación interactiva de Swagger UI, que te permite interactuar con todos los endpoints directamente desde el navegador.

API disponible en: http://localhost:8000

Documentación Interactiva: http://localhost:8000/docs


## Roadmap a seguir

[ ] IA Avanzada: Mejorar el motor de NLP para entender peticiones mucho más complejas y contextuales.

[ ] Roadmaps de Estudio: Generación automática de planes de estudio para preparar exámenes.

[ ] Estados Personalizables: Permitir a los usuarios crear estados personalizados para sus tareas y eventos, al estilo Notion.

[ ] Integración OAuth con Calendarios Externos: Sincronización con Google Calendar, Notion Calendar, etc.
