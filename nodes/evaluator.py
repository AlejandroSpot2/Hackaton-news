"""
Evaluator node - assesses coverage quality and decides if more search is needed.
"""
import os
from datetime import datetime
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from models import GraphState, Evaluation, MAX_SEARCH_ITERATIONS

load_dotenv()

# Initialize model
model = ChatOpenAI(model="gpt-5-mini-2025-08-07", temperature=0.0)


def _is_within_range(pub_date_str: str, start: str, end: str) -> bool:
    """Check if a published_date falls within [start, end]."""
    if not pub_date_str:
        return True  # no date = benefit of the doubt
    try:
        pub = parsedate_to_datetime(pub_date_str).date()
        return (
            datetime.strptime(start, "%Y-%m-%d").date()
            <= pub
            <= datetime.strptime(end, "%Y-%m-%d").date()
        )
    except (ValueError, TypeError):
        return True  # unparseable = keep


def evaluator_node(state: GraphState) -> dict:
    """
    Evaluate if the search results provide sufficient coverage.

    This node analyzes the collected content and determines if:
    - The objective is adequately covered
    - There's enough concrete data (numbers, companies, dates)
    - Important angles are missing
    - Sources fall within the required date range

    Args:
        state: Current graph state containing raw_content and objective

    Returns:
        Dictionary with Evaluation result
    """
    print("--- EVALUANDO COBERTURA ---")

    objective = state.get("objective", "noticias del sector inmobiliario comercial México")
    raw_content = state.get("raw_content", [])
    current_iterations = state.get("search_iterations", 0)
    start_date = state.get("start_date", "")
    end_date = state.get("end_date", "")

    # Summarize what we have
    topics_covered = [item["topic"] for item in raw_content]

    # Count sources and flag out-of-range ones
    total_sources = 0
    out_of_range = 0
    for item in raw_content:
        for source in item.get("sources", []):
            total_sources += 1
            pub = source.get("published_date", "")
            if pub and not _is_within_range(pub, start_date, end_date):
                out_of_range += 1

    if out_of_range:
        print(f"  -> Fuentes fuera de rango: {out_of_range}/{total_sources}")

    # Build content summary for evaluation (include dates)
    content_summary = []
    for item in raw_content:
        sources_text = "\n".join([
            f"  - [{s.get('published_date', 'sin fecha')}] {s['title'][:100]}"
            for s in item["sources"][:3]
        ])
        content_summary.append(f"Tema: {item['topic']}\nFuentes:\n{sources_text}")

    content_text = "\n\n".join(content_summary)

    prompt = f"""Eres un editor senior de noticias evaluando la cobertura de un reporte del sector inmobiliario comercial (CRE) de México.

OBJETIVO DEL REPORTE: {objective}
PERIODO REQUERIDO: {start_date} a {end_date}
ITERACIONES DE BÚSQUEDA: {current_iterations} de {MAX_SEARCH_ITERATIONS} máximo

CONTENIDO RECOPILADO:
{content_text}

TOTAL: {len(topics_covered)} temas, {total_sources} fuentes
FUENTES FUERA DE RANGO DE FECHAS: {out_of_range} de {total_sources}

EVALÚA CON RIGOR:
1. COBERTURA TEMÁTICA: ¿Los temas cubren los sub-temas del objetivo? (ej: si el objetivo menciona "parques industriales, oficinas y logística", debe haber al menos un tema por sub-sector)
2. CALIDAD DE DATOS: ¿Hay cifras concretas (m², montos en USD/MXN, porcentajes, tasas de vacancia)? Un tema sin datos duros es débil.
3. DIVERSIDAD DE FUENTES: ¿Hay al menos 2 fuentes distintas por tema? Un tema con solo 1 fuente es débil.
4. VIGENCIA: Si hay fuentes fuera del rango de fechas, eso reduce la calidad. Penaliza proporcionalmente.

CRITERIOS DE SUFICIENCIA:
- SUFICIENTE: >= 3 temas sólidos (con datos concretos + >= 2 fuentes cada uno) que cubran los sub-sectores del objetivo
- INSUFICIENTE: < 3 temas sólidos, O un sub-sector del objetivo sin cobertura, O mayoría de fuentes fuera de rango

Si la cobertura es insuficiente Y quedan iteraciones, sugiere 1-2 búsquedas adicionales enfocadas en lo que falta.
Si ya se alcanzó el máximo de iteraciones, marca is_sufficient=True.
"""

    evaluation = model.with_structured_output(Evaluation).invoke(prompt)

    status = "SUFICIENTE" if evaluation.is_sufficient else "NECESITA MAS"
    print(f"  -> Evaluacion: {status}")
    if not evaluation.is_sufficient and evaluation.missing_topics:
        topics_str = str(evaluation.missing_topics).encode("ascii", "replace").decode()
        print(f"  -> Temas faltantes: {topics_str}")

    return {"evaluation": evaluation}


def should_search_more(state: GraphState) -> str:
    """
    Conditional edge function to decide next step after evaluation.

    Args:
        state: Current graph state with evaluation result

    Returns:
        "buscador" to search more, or "analista" to generate report
    """
    evaluation = state.get("evaluation")
    current_iterations = state.get("search_iterations", 0)

    # No evaluation? Go to analyst
    if not evaluation:
        return "analista"

    # Coverage is sufficient? Go to analyst
    if evaluation.is_sufficient:
        return "analista"

    # Hit max iterations? Go to analyst anyway
    if current_iterations >= MAX_SEARCH_ITERATIONS:
        print(f"  -> Límite de iteraciones alcanzado ({MAX_SEARCH_ITERATIONS})")
        return "analista"

    # Need more search - update topics with missing ones
    if evaluation.missing_topics:
        # The missing topics will be searched in the next iteration
        print(f"  -> Buscando {len(evaluation.missing_topics)} temas adicionales")

    return "buscador"
