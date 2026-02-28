# Estrategia de Integración: Pioneer AI en el Agente de Noticias

## Resumen ejecutivo

Este documento analiza cómo integrar **Pioneer AI** (plataforma de fine-tuning de modelos GLiNER) en el agente LangGraph para reducir la dependencia de OpenAI, disminuir costos, bajar la latencia y eliminar el rate limiting en nodos que no requieren generación de texto.

**Resultado esperado:** reducir las llamadas a OpenAI de **4–5 por ejecución a 1**, manteniendo o mejorando la calidad del output.

---

## 1. Diagnóstico: uso actual de OpenAI

El agente realiza 3 tipos de llamadas a OpenAI por cada ejecución:

| Nodo | Modelo | Llamadas/run | Tarea real |
|---|---|---|---|
| `planner.py` | gpt-5-mini | 1× | Genera 3-5 queries a partir de titulares |
| `evaluator.py` | gpt-5-mini | 1–2× (por el loop) | Clasifica si la cobertura es suficiente + identifica temas faltantes |
| `analyst.py` | gpt-5 | 1× | Redacta artículos de 100-150 palabras |

**Total: 3–4 llamadas mínimo, hasta 5 si el evaluador dispara el loop dos veces.**

El problema de rate limiting se concentra en `planner` + `evaluator` porque se ejecutan en rápida sucesión y antes del `analyst`. El `analyst` usa `gpt-5` (más caro y con límites más estrictos).

---

## 2. Qué puede y no puede hacer GLiNER

GLiNER (Generalist and Lightweight model for Named Entity Recognition) es un modelo de span-level classification que opera sobre texto de entrada y produce etiquetas estructuradas. **No genera texto libre.**

| Capacidad | GLiNER | Relevancia para el agente |
|---|---|---|
| Extracción de entidades (NER) | ✅ Excelente | Extraer companies, locations, metrics de headlines |
| Clasificación binaria (sí/no) | ✅ Excelente | `is_sufficient: bool` del evaluador |
| Clasificación multi-label | ✅ Bueno | `missing_topics` como categorías fijas |
| Extracción estructurada con schema | ✅ Bueno | SearchPlan simplificado |
| Generación de texto libre | ❌ Imposible | Artículos del analyst |
| Razonamiento complejo en cadena | ❌ Imposible | `reasoning` fields |
| Creatividad / variabilidad controlada | ❌ Imposible | Síntesis narrativa |

---

## 3. Análisis nodo por nodo

### 3.1 `planner.py` — Candidato parcial ⚠️

**Tarea actual:**
Recibe 10 titulares con snippets (~2,000 chars) y genera 3-5 queries de búsqueda + un campo `reasoning`.

```python
# Output actual
class SearchPlan(BaseModel):
    topics: list[str]   # "Nearshoring parques industriales México 2026"
    reasoning: str      # "Elegí estos temas porque..."
```

**Por qué NO es reemplazable directamente con Pioneer:**
- Los `topics` son texto generado creativo — Pioneer no puede inventar strings nuevos
- El campo `reasoning` es generación de texto pura

**Por qué SÍ puede beneficiarse de Pioneer (enfoque híbrido):**
Pioneer puede hacer el **paso de extracción de entidades** que actualmente el LLM hace implícitamente:

```
Headline: "BYD y Geely pujan por planta COMPAS en Aguascalientes"
↓ Pioneer extrae:
{
  "COMPANY": ["BYD", "Geely", "COMPAS"],
  "LOCATION": ["Aguascalientes"],
  "SECTOR": ["automotriz", "parques industriales"],
  "EVENT": ["adquisición de planta"]
}
↓ Template determinístico construye query:
"BYD Geely planta automotriz Aguascalientes 2026"
```

**Veredicto: Reemplazable con arquitectura híbrida Pioneer + templates.** El campo `reasoning` se puede eliminar o generar con una plantilla fija. La calidad de los queries será más predecible (menos creativa, más precisa para dominios fijos como CRE México).

---

### 3.2 `evaluator.py` — Candidato ideal ✅

**Tarea actual:**
Recibe un resumen de temas cubiertos (títulos de artículos + fechas) y decide:
1. ¿Es suficiente la cobertura? (`is_sufficient: bool`)
2. ¿Qué temas faltan? (`missing_topics: list[str]`)

```python
# Output actual
class Evaluation(BaseModel):
    is_sufficient: bool
    missing_topics: list[str]
    reasoning: str
```

**Por qué es el MEJOR candidato para Pioneer:**

**`is_sufficient`** es clasificación binaria pura:
- Input: resumen de cobertura textual
- Output: `True` / `False`
- Este es el caso de uso más básico y más preciso de GLiNER fine-tuneado

**`missing_topics`** es clasificación multi-label con taxonomía fija:
- Para el dominio CRE México existe un conjunto acotado de sub-sectores
- En lugar de generarlos, Pioneer clasifica cuáles de la lista están ausentes

```python
# Taxonomía fija CRE México (no generada, clasificada)
TOPICS_TAXONOMY = [
    "parques_industriales",
    "oficinas_corporativas",
    "logistica_bodegas",
    "fibras_industriales",
    "nearshoring",
    "vacancia_oficinas",
    "inversion_extranjera",
    "desarrollo_residencial_mixto",
]
```

**`reasoning`** se elimina o se genera con una plantilla: `"Faltan cobertura de: {missing_topics}"` — no necesita LLM.

**Veredicto: Reemplazable al 100% con Pioneer.** Es el caso de uso más limpio: clasificación binaria + multi-label sobre texto de entrada corto (~500 chars).

---

### 3.3 `analyst.py` — NO candidato ❌

**Tarea actual:**
Genera artículos de 100-150 palabras para cada tema con datos concretos, títulos descriptivos y lista de fuentes.

**Por qué NO puede reemplazarse con Pioneer:**
- La escritura de artículos es generación de texto narrativo
- Requiere síntesis, coherencia, densidad de información
- GLiNER no puede generar strings nuevos — solo etiquetar spans existentes
- Esta es la tarea de mayor valor del agente y requiere un LLM potente

**Veredicto: Permanece con gpt-5. Es el único nodo que justifica el costo y complejidad de un modelo generativo grande.**

---

## 4. Arquitectura propuesta

### Estado actual
```
explorador (Tavily)
    → planificador (gpt-5-mini) ← RATE LIMIT
        → buscador (Tavily)
            → extractor (Tavily)
                → evaluador (gpt-5-mini) ← RATE LIMIT (×1–2)
                    → analista (gpt-5) ← COSTOSO
```

### Arquitectura con Pioneer
```
explorador (Tavily)
    → planificador (Pioneer: extrae entidades → template construye queries)
        → buscador (Tavily)
            → extractor (Tavily)
                → evaluador (Pioneer: clasifica is_sufficient + missing_topics)
                    → analista (gpt-5) ← único LLM call
```

**Reducción de llamadas OpenAI: de 3–5 a 1 por ejecución (↓ 75–80%)**

---

## 5. Plan de fine-tuning

### 5.1 Modelo para el Evaluador (prioridad alta)

**Nombre sugerido:** `cre-coverage-evaluator`

**Tarea Pioneer:** clasificación binaria + multi-label

**Formato de entrada al modelo:**
```
Topics covered: [parques industriales nearshoring, FIBRAS Q1 2026, logística Bajío]
Sources per topic: [4, 2, 1]
Sources out of range: 0/7
Objective: noticias CRE México industrial oficinas logística
```

**Labels de entrenamiento:**
```json
{
  "is_sufficient": false,
  "missing_categories": ["oficinas_corporativas", "vacancia_oficinas"]
}
```

**Datos de entrenamiento — cómo generarlos:**

1. **Bootstrap desde runs actuales:** ejecutar el agente 30-50 veces con el evaluador OpenAI y guardar los pares (input_summary → Evaluation). Cada run que pase por el evaluador es un ejemplo de entrenamiento.

2. **Formato del dataset:**
```jsonl
{"text": "Topics covered: [nearshoring Monterrey, parques industriales Bajío]...",
 "entities": [{"label": "COVERAGE_INSUFFICIENT", "span": "..."}],
 "classification": "insufficient",
 "missing": ["oficinas_corporativas", "fibras_industriales"]}
```

3. **Volumen mínimo recomendado:** 100–200 ejemplos balanceados (50% sufficient, 50% insufficient con distintas combinaciones de missing topics).

**API call post-fine-tuning:**
```python
import requests

def pioneer_evaluate(content_summary: str) -> dict:
    response = requests.post(
        "https://pioneer.ai/inference",
        json={
            "model_id": "cre-coverage-evaluator",
            "task": "extract_entities",
            "text": content_summary,
            "schema": {
                "coverage_status": ["sufficient", "insufficient"],
                "missing_topics": TOPICS_TAXONOMY
            }
        }
    )
    return response.json()
```

---

### 5.2 Modelo para el Planner (prioridad media)

**Nombre sugerido:** `cre-headline-entity-extractor`

**Tarea Pioneer:** extracción de entidades nombradas de titulares

**Entidades a extraer:**
```
COMPANY    → BYD, Amazon, Prologis, VESTA, Finsa
LOCATION   → Monterrey, Bajío, CDMX, Guadalajara, Aguascalientes, Corredor Toluca
SECTOR     → parques industriales, oficinas, logística, nearshoring
METRIC     → m², USD, ha, tasa de vacancia, MXN
EVENT      → adquisición, expansión, inauguración, inversión, contrato
```

**Formato entrada:**
```
BYD y Geely pujan por planta COMPAS en Aguascalientes con capacidad de 230,000 vehículos
```

**Output Pioneer:**
```json
{
  "entities": [
    {"text": "BYD", "label": "COMPANY"},
    {"text": "Geely", "label": "COMPANY"},
    {"text": "COMPAS", "label": "COMPANY"},
    {"text": "Aguascalientes", "label": "LOCATION"},
    {"text": "230,000 vehículos", "label": "METRIC"},
    {"text": "adquisición", "label": "EVENT"}
  ]
}
```

**Template determinístico para construir queries:**
```python
def build_query_from_entities(entities: list[dict]) -> str:
    companies = [e["text"] for e in entities if e["label"] == "COMPANY"][:2]
    locations = [e["text"] for e in entities if e["label"] == "LOCATION"][:1]
    sectors   = [e["text"] for e in entities if e["label"] == "SECTOR"][:1]
    events    = [e["text"] for e in entities if e["label"] == "EVENT"][:1]

    parts = companies + locations + sectors + events
    return " ".join(parts[:5]) + f" {datetime.now().year}"
    # → "BYD Geely Aguascalientes adquisición 2026"
```

**Datos de entrenamiento:**
- ~50–100 titulares de noticias CRE México etiquetados manualmente con las 5 categorías
- Se pueden etiquetar en 2–3 horas dado el dominio acotado

---

## 6. Comparación de estrategias

| Estrategia | Esfuerzo | Reducción rate limit | Costo operativo | Calidad |
|---|---|---|---|---|
| **A. Solo Pioneer evaluador** | Bajo | ↓ 40–50% | ↓ 30% | ≈ igual |
| **B. Pioneer evaluador + planner híbrido** | Medio | ↓ 75–80% | ↓ 55% | Ligeramente menor en planner |
| **C. Reemplazar analyst con modelo más barato** | Bajo | ↓ 20% | ↓ 60% | Menor calidad de redacción |
| **D. B + caching de evaluaciones similares** | Medio | ↓ 85–90% | ↓ 65% | ≈ igual |

**Recomendación: Estrategia B** como target, comenzando con **Estrategia A** como primer paso validado.

---

## 7. Hoja de ruta de implementación

### Fase 1 — Pioneer Evaluador (1–2 días)
1. Ejecutar 50 runs del agente actual y capturar todos los inputs/outputs del evaluador
2. Limpiar y formatear el dataset en el esquema de Pioneer
3. Fine-tunear `cre-coverage-evaluator` en Pioneer
4. Crear `nodes/evaluator_pioneer.py` como reemplazo
5. A/B test: comparar `Evaluation.is_sufficient` de Pioneer vs OpenAI en 20 casos
6. Si accuracy ≥ 90%, reemplazar en producción

### Fase 2 — Pioneer Planner (2–3 días)
1. Etiquetar 100 titulares CRE México con entidades
2. Fine-tunear `cre-headline-entity-extractor`
3. Crear función `build_query_from_entities()` con templates
4. Crear `nodes/planner_pioneer.py`
5. Validar: comparar diversidad y relevancia de queries generados vs actuales
6. Si calidad ≥ 85% (evaluación manual), reemplazar en producción

### Fase 3 — Optimizaciones adicionales (opcional)
- Caching de evaluaciones: si el mismo topic_set fue evaluado antes, reusar resultado
- Paralelización: ejecutar pioneer_evaluate y pioneer_extract en paralelo cuando sea posible
- Monitoreo de drift: detectar cuando el modelo empieza a fallar y reentrenar

---

## 8. Estructura de archivos propuesta

```
nodes/
├── planner.py              # Actual (OpenAI) — se mantiene como fallback
├── planner_pioneer.py      # Nuevo: Pioneer entity extraction + template
├── evaluator.py            # Actual (OpenAI) — se mantiene como fallback
├── evaluator_pioneer.py    # Nuevo: Pioneer clasificación binaria + multi-label
├── analyst.py              # Sin cambios — permanece con gpt-5
├── explorer.py             # Sin cambios — Tavily
├── searcher.py             # Sin cambios — Tavily
└── extractor.py            # Sin cambios — Tavily

pioneer_client.py           # Cliente Pioneer reutilizable (auth, retry, timeout)
```

**Flag de feature en `.env` para activar/desactivar Pioneer:**
```env
USE_PIONEER_EVALUATOR=true
USE_PIONEER_PLANNER=false    # false hasta validar en Fase 2
PIONEER_API_KEY=pk-...
PIONEER_EVALUATOR_MODEL_ID=cre-coverage-evaluator
PIONEER_PLANNER_MODEL_ID=cre-headline-entity-extractor
```

---

## 9. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Pioneer accuracy < 90% en evaluador | Media | Mantener OpenAI como fallback con flag |
| Taxonomía fija de CRE no cubre nuevo objetivo | Alta | Diseñar taxonomía extensible; re-entrenar si se añaden sectores |
| Latencia de Pioneer API > esperada | Baja | Timeout de 2s + fallback a OpenAI |
| Queries del planner híbrido menos creativos | Media | Aceptable: en dominios acotados, precisión > creatividad |
| Dataset de entrenamiento insuficiente | Alta | Comenzar con 50 ejemplos; iterar con más si performance es baja |

---

## 10. Conclusión

| Nodo | Decisión | Justificación |
|---|---|---|
| `evaluator.py` | **Reemplazar con Pioneer** | Clasificación binaria + multi-label sobre texto corto. Caso de uso ideal para GLiNER. Ahorra 1-2 llamadas OpenAI por run. |
| `planner.py` | **Reemplazar con Pioneer + templates** | Entity extraction de titulares es perfecta para GLiNER. La construcción de queries via templates es determinista. Ahorra 1 llamada OpenAI por run. |
| `analyst.py` | **Mantener OpenAI gpt-5** | Generación de texto narrativo. GLiNER no puede hacerlo. Es la única tarea que justifica un LLM generativo. |
| `explorer.py` | Sin cambios (Tavily) | |
| `searcher.py` | Sin cambios (Tavily) | |
| `extractor.py` | Sin cambios (Tavily) | |

**El evaluador es el primer paso recomendado** por su alto ROI: es la tarea más clara para GLiNER, corre 1-2 veces por ejecución (amplificando el ahorro con el loop), y su reemplazo reduce directamente el riesgo de rate limiting en la fase crítica del pipeline donde el agente decide si necesita más búsquedas.
