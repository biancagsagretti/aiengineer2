# Pipeline de Extracción de Entidades Técnicas

Pipeline construido con **LangChain (LCEL)**, **Pydantic** y **Gemini** que recibe un texto sin procesar (un log de error o una descripción de arquitectura) y devuelve un objeto **validado** con las tecnologías detectadas, el nivel de criticidad y un resumen técnico.

## Características

- **Esquema Pydantic** (`schemas.py`) con validaciones: lista de tecnologías no vacía, enum de criticidad y resumen no vacío.
- **`ChatPromptTemplate`** modular, sin f-strings: LangChain gestiona las variables de entrada.
- **Cadena LCEL**: `prompt | model.with_structured_output(Schema).with_retry(...)`.
- **Resiliencia**: hasta 3 intentos con backoff exponencial y jitter ante JSON mal formado o incompleto.
- **Función asíncrona** `process_text(text)` basada en `.ainvoke()`.
- **Logs** para seguir la validación y los reintentos.

## Estructura del proyecto

```
.
├── chain.py            # Prompt + LLM + reintentos + process_text()
├── schemas.py          # Modelo Pydantic (contrato de salida)
├── test_chain.py       # Mini-script de prueba asíncrono
├── requirements.txt
├── .env                # NO se sube al repo (contiene tu API key)
├── .gitignore
└── README.md
```

## Instalación

1. Cloná el repositorio y entrá a la carpeta:

   ```bash
   git clone <URL_DEL_REPO>
   cd <NOMBRE_DEL_REPO>
   ```

2. Creá y activá un entorno virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Linux / macOS
   .venv\Scripts\activate         # Windows
   ```

3. Instalá las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

   Contenido sugerido de `requirements.txt`:

   ```
    langchain-core>=0.3
    langchain-google-genai>=2.0
    pydantic>=2.0
    python-dotenv>=1.0

   ```

4. Creá un archivo `.env` en la raíz con tu clave de Google AI Studio:

   ```
   GOOGLE_API_KEY=tu_clave_aqui
   ```

   > Asegurate de que `.env` esté listado en `.gitignore` (el archivo debe llamarse `.gitignore`, con el punto inicial).

## Uso

### Ejecutar el ejemplo incluido

```bash
python chain.py
```

### Usar `process_text` desde tu propio código

```python
import asyncio
from chain import process_text

texto = (
    "Meta4 utiliza Oracle 19c como base de datos; "
    "hay timeouts por conexiones de más de 300 segundos."
)

resultado = asyncio.run(process_text(texto))
print(resultado.model_dump_json(indent=2))
```

### Correr el mini-script de prueba

```bash
python test_chain.py
```

## Ejemplo de salida

**Entrada:**

```
"Meta4 utiliza Oracle 19c como base de datos; "
"hay timeouts por conexiones de más de 300 segundos."
```

**Salida (objeto validado):**

```json

{
  "tecnologias": [
    "Meta4",
    "Oracle 19c"
  ],
  "nivel_de_criticidad": "alta",
  "resumen_tecnico": "Se presentan timeouts en la aplicación Meta4 debido a conexiones hacia la base de datos Oracle 19c que exceden los 300 segundos de duración."
}
```

## Esquema de datos

| Campo | Tipo | Restricciones |
|---|---|---|
| `tecnologias` | `list[str]` | Mínimo 1 elemento |
| `nivel_de_criticidad` | `Enum` | `baja`, `media` o `alta` |
| `resumen_tecnico` | `str` | No puede estar vacío |

## Cómo funciona

```
texto crudo ──► ChatPromptTemplate ──► Gemini + with_structured_output ──► with_retry ──► objeto Pydantic
```

1. **Prompt**: `ChatPromptTemplate` recibe la variable `{texto}` e instruye al modelo a extraer tecnologías, clasificar la criticidad y resumir.
2. **Salida estructurada**: `.with_structured_output(AnalisisTecnico)` obliga al modelo a responder con el esquema y Pydantic valida el resultado.
3. **Reintentos**: `.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)` vuelve a llamar al modelo si la respuesta es inválida o hay un error transitorio.
4. **Logs**: `process_text` registra el inicio del procesamiento, los errores de validación y el resultado final.

## Prueba de estrés (texto ambiguo)

Para verificar la resiliencia, probá con textos que no contienen información técnica clara:

```python
import asyncio
from chain import process_text

textos_ambiguos = [
    "Se cayó todo otra vez, avisen cuando esté arreglado.",
    "Hay un problema con el sistema que usamos desde hace tiempo.",
]

for t in textos_ambiguos:
    try:
        print(asyncio.run(process_text(t)))
    except Exception as e:
        print(f"Falló la validación: {type(e).__name__}: {e}")
```

Comportamientos posibles:

- El modelo devuelve un objeto válido (por ejemplo, con criticidad `media`) y el pipeline lo acepta.
- La salida no cumple el esquema (lista de tecnologías vacía, enum inválido): se reintenta hasta 3 veces y, si sigue fallando, se registra el error y se propaga la excepción.

## Limitaciones y mejoras futuras


- Agregar tests automatizados con `pytest` y `pytest-asyncio`, usando un LLM simulado.
- Permitir cambiar de proveedor (`ChatOpenAI` / `ChatAnthropic`) por configuración.


## Incorporaciones
- Detección de respuestas truncadas: se revisa `finish_reason` (p. ej. `MAX_TOKENS`) y se reintenta si la salida quedó incompleta.
## Tecnologías

Python · LangChain · Pydantic · Google Gemini · asyncio
