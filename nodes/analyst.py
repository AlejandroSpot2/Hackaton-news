"""
Analyst node - generates the final news digest report.
"""
import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from models import GraphState, NewsDigest

load_dotenv()

# Initialize model
model = ChatOpenAI(model="gpt-5-2025-08-07", temperature=0.0)


def analyze_news_node(state: GraphState) -> dict:
    """
    Generate a structured news digest from the collected content.
    
    Args:
        state: Current graph state containing raw_content and objective
        
    Returns:
        Dictionary with the final NewsDigest
    """
    print("--- GENERANDO REPORTE ---")
    
    date = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""Eres un analista de noticias profesional especializado en el sector inmobiliario comercial de México.
La fecha de hoy es {date}.

Objetivo del reporte: {state.get("objective", "Resumen de noticias del sector CRE México")}

Tu tarea es generar un resumen estructurado de noticias.
Por cada tema relevante, escribe:
1. Un título descriptivo
2. Un artículo de 100 a 150 palabras resumiendo los puntos clave con datos concretos (cifras, empresas, ubicaciones)
3. Lista las URLs de las fuentes externas utilizadas (campo "sources")

Datos de noticias recopilados:
{state["raw_content"]}
"""

    digest = model.with_structured_output(NewsDigest).invoke(prompt)

    return {"digest": digest}
