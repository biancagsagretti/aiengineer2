"""Mini-script de prueba asíncrono para el pipeline de extracción técnica.

Ejecuta un caso normal y varios textos ambiguos para observar si el
validador lanza excepciones o si el modelo se recupera con los reintentos.

Uso:
    python test_chain.py
"""
import asyncio
import logging

from chain import process_text

log = logging.getLogger("test_chain")

CASO_NORMAL = (
    "La API en FastAPI usa Redis como caché y PostgreSQL para persistencia; "
    "hay timeouts por conexiones concurrentes."
)

CASOS_AMBIGUOS = [
    "Se cayó todo otra vez, avisen cuando esté arreglado.",
    "Hay un problema con el sistema que usamos desde hace tiempo.",
    "error 1",
]


async def ejecutar_caso(nombre: str, texto: str) -> bool:
    """Procesa un texto y devuelve True si el pipeline produjo un objeto válido."""
    log.info("=== %s ===", nombre)
    try:
        resultado = await process_text(texto)
    except Exception as e:
        log.warning("%s -> falló: %s: %s", nombre, type(e).__name__, e)
        return False
    print(f"\n[{nombre}]")
    print(resultado.model_dump_json(indent=2))
    return True


async def main() -> None:
    resultados = {"normal": await ejecutar_caso("Caso normal", CASO_NORMAL)}

    for i, texto in enumerate(CASOS_AMBIGUOS, start=1):
        nombre = f"Caso ambiguo {i}"
        resultados[nombre] = await ejecutar_caso(nombre, texto)

    print("\n--- Resumen ---")
    for nombre, ok in resultados.items():
        print(f"{nombre}: {'OK' if ok else 'FALLÓ'}")


if __name__ == "__main__":
    asyncio.run(main())
