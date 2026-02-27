"""
Planner node - analyzes exploration results and decides what to search deeper.
"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from models import GraphState, SearchPlan

load_dotenv()

# Initialize model
model = ChatOpenAI(model="gpt-5-mini-2025-08-07", temperature=0.0)


def planner_node(state: GraphState) -> dict:
    """
    Analyze exploration results and generate specific search topics.
    
    This node receives real news data from the explorer and decides
    which topics deserve deeper investigation based on relevance,
    data richness, and alignment with the objective.
    
    Args:
        state: Current graph state containing exploration_results and objective
        
    Returns:
        Dictionary with topics list and planning_reasoning
    """
    print("--- PLANIFICANDO BUSQUEDAS ---")
    
    exploration_data = state.get("exploration_results", [])
    objective = state.get("objective", "noticias del sector inmobiliario comercial México")
    
    # Format exploration results for the prompt
    headlines_text = "\n".join([
        f"- {item['title']}: {item['snippet'][:200]}..."
        for item in exploration_data
    ])
    
    prompt = f"""Eres un analista de mercado inmobiliario en México.

OBJETIVO DEL REPORTE: {objective}

TITULARES Y NOTICIAS ENCONTRADAS:
{headlines_text}

TAREA:
Basándote en los titulares REALES, genera 3-5 búsquedas específicas para profundizar.

REGLAS CRÍTICAS PARA LOS TOPICS:
- Cada topic debe ser UN QUERY DE BÚSQUEDA CORTO (máximo 50-60 caracteres)
- NO incluyas explicaciones ni razonamientos en los topics
- El razonamiento va SOLO en el campo "reasoning", NO en los topics
- Los topics son SOLO las frases de búsqueda

EJEMPLOS CORRECTOS de topics:
- "Nearshoring parques industriales México 2026"
- "Vacancia oficinas Reforma CDMX 2026"
- "Amazon centro distribución Guadalajara"
- "Inversión industrial Monterrey nearshoring"

EJEMPLOS INCORRECTOS (NO hagas esto):
- "1) Nearshoring como motor... Razonamiento: el titular indica..." (MUY LARGO)
- "Búsqueda sobre inversiones en parques industriales considerando que..." (MUY LARGO)

Prioriza noticias con datos concretos (USD, m², empresas específicas).
"""
    
    plan = model.with_structured_output(SearchPlan).invoke(prompt)
    
    print(f"  -> Temas seleccionados: {len(plan.topics)}")
    for i, topic in enumerate(plan.topics, 1):
        print(f"     {i}. {topic}")
    
    return {
        "topics": plan.topics,
        "planning_reasoning": plan.reasoning
    }
