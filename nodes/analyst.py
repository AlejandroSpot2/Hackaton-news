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

    visual_analysis = state.get("visual_analysis", [])
    video_context = ""
    if visual_analysis:
        video_context = "\n\nANÁLISIS DE CONTENIDO EN VIDEO:\n"
        for va in visual_analysis:
            video_context += f"\nVideo: {va['video_title']}\nURL: {va['video_url']}\nAnálisis: {va['analysis']}\n"

    prompt = f"""Eres un analista de noticias profesional especializado en el sector inmobiliario comercial de México.
La fecha de hoy es {date}.

Objetivo del reporte: {state.get("objective", "Resumen de noticias del sector CRE México")}

Tu tarea es generar un resumen estructurado de noticias.
Por cada tema relevante, escribe:
1. Un título descriptivo
2. Un artículo de 100 a 150 palabras resumiendo los puntos clave con datos concretos (cifras, empresas, ubicaciones)
3. Lista las URLs de las fuentes externas utilizadas (campo "sources"); incluye URLs de videos relevantes cuando aplique

Si existe análisis de video, intégralo en las secciones pertinentes e incluye las URLs de los videos en el campo "sources".

Datos de noticias recopilados:
{state["raw_content"]}{video_context}
"""

    digest = model.with_structured_output(NewsDigest).invoke(prompt)

    return {"digest": digest}
