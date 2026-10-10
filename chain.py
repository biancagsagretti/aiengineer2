import asyncio
import logging

from dotenv import load_dotenv
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import ValidationError

from schemas import AnalisisTecnico

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# Valores de finish_reason que indican que el modelo cortó la respuesta.

FINISH_REASONS_TRUNCADOS = {"MAX_TOKENS", "LENGTH"}


class RespuestaIncompleta(Exception):
    """El modelo cortó la respuesta (por ejemplo, por falta de tokens)."""


def verificar_respuesta(resp: dict) -> AnalisisTecnico:
    """Revisa finish_reason y el parseo antes de aceptar el resultado.

    Recibe el dict que devuelve with_structured_output(include_raw=True):
    {"raw": AIMessage, "parsed": AnalisisTecnico | None, "parsing_error": Exception | None}
    Lanza una excepción si la salida está cortada o inválida, para que
    .with_retry() vuelva a intentar.
    """
    raw = resp.get("raw")
    metadata = getattr(raw, "response_metadata", None) or {}
    finish_reason = metadata.get("finish_reason")
    log.info("finish_reason=%s", finish_reason)

    if finish_reason and str(finish_reason).upper() in FINISH_REASONS_TRUNCADOS:
        log.warning("Respuesta truncada (finish_reason=%s); se reintentará.", finish_reason)
        raise RespuestaIncompleta(f"La respuesta se cortó: finish_reason={finish_reason}")

    if resp.get("parsing_error") is not None:
        log.warning("Error de parseo/validación: %s", resp["parsing_error"])
        raise OutputParserException(f"Salida inválida: {resp['parsing_error']}")

    if resp.get("parsed") is None:
        log.warning("El modelo no devolvió un objeto parseado; se reintentará.")
        raise OutputParserException("El modelo no devolvió un objeto parseado.")

    return resp["parsed"]


def construir_cadena(max_output_tokens: int | None = None):
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.8-flash",
        temperature=0.0,
        max_output_tokens=max_output_tokens,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Eres un experto en TI. Extrae las tecnologías, "
                   "clasifica la criticidad (baja, media, alta) y resume."),
        ("human", "Analiza el siguiente texto:\n\n{texto}"),
    ])

    # include_raw=True devuelve el mensaje original (con finish_reason)
    # junto con el objeto parseado, en lugar de lanzar la excepción de inmediato.
    modelo_estructurado = llm.with_structured_output(AnalisisTecnico, include_raw=True)

    # El reintento envuelve modelo + verificación: si la verificación lanza
    # una excepción, se vuelve a llamar al modelo.
    modelo_verificado = (modelo_estructurado | RunnableLambda(verificar_respuesta)).with_retry(
        retry_if_exception_type=(
            ValidationError,
            OutputParserException,
            RespuestaIncompleta,
        ),
        stop_after_attempt=3,
        wait_exponential_jitter=True,
    )

    return prompt | modelo_verificado


async def process_text(text: str, max_output_tokens: int | None = None) -> AnalisisTecnico:
    log.info("Procesando texto (%d caracteres)", len(text))
    try:
        resultado = await construir_cadena(max_output_tokens).ainvoke({"texto": text})
    except (ValidationError, OutputParserException, RespuestaIncompleta) as e:
        log.error("Validación fallida tras reintentos: %s", e)
        raise
    log.info("Validación OK: %s", resultado.model_dump())
    return resultado


if __name__ == "__main__":
    texto = ("Meta4 utiliza Oracle 19c como base de datos; "
             "hay timeouts por conexiones de más de 300 segundos.")
    print(asyncio.run(process_text(texto)).model_dump_json(indent=2))