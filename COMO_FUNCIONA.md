# Cómo funciona el Agente de Noticias CRE México

Este documento explica en detalle la arquitectura, el flujo de datos y la lógica interna del agente autónomo de noticias para el sector inmobiliario comercial (CRE) de México.

---

## Visión general

El agente es un sistema de inteligencia artificial construido sobre **LangGraph** que recopila, filtra, evalúa y sintetiza noticias del sector CRE de México de forma completamente autónoma. A diferencia de un buscador convencional, este agente **razona** sobre lo que encuentra y decide por sí solo qué investigar más a fondo.

El proceso comienza con un objetivo de alto nivel en lenguaje natural (por ejemplo, *"Noticias de parques industriales, oficinas corporativas y logística en México"*) y termina produciendo un digest estructurado con artículos, datos concretos y fuentes verificables.

---

## Tecnologías utilizadas

| Componente | Tecnología | Rol |
|---|---|---|
| Orquestación del agente | LangGraph | Define el grafo de nodos y el flujo de ejecución |
| Modelos de lenguaje | OpenAI GPT (via LangChain) | Planificación, evaluación y redacción del reporte |
| Búsqueda y extracción web | Tavily API | Busca noticias reales y extrae contenido completo de URLs |
| Modelos de datos | Pydantic | Valida y estructura el estado y las salidas del agente |
| Conversión de reportes | python-docx | Genera archivos Word, Markdown y texto plano |

---

## Arquitectura: El grafo de nodos

El agente se implementa como un **grafo dirigido** donde cada nodo realiza una tarea específica. El estado del agente (`GraphState`) fluye entre nodos y se va enriqueciendo en cada paso.

```
START
  │
  ▼
┌─────────────┐
│  explorador │  ← Búsqueda amplia y rápida para ver el panorama
└──────┬──────┘
       │
       ▼
┌─────────────┐
│planificador │  ← LLM analiza titulares reales y elige qué investigar
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   buscador  │  ← Búsquedas profundas por tema en medios mexicanos
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  extractor  │  ← Obtiene el contenido completo de cada artículo
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  evaluador  │  ← LLM decide si la cobertura es suficiente
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
  NO      SÍ
   │       │
   │       ▼
   │  ┌─────────────┐
   │  │   analista  │  ← LLM redacta el digest final estructurado
   │  └──────┬──────┘
   │         │
   └─────────┘ (vuelve a buscador si falta cobertura)
              │
              ▼
            END  →  reporte.json
```

---

## Estado compartido (`GraphState`)

Todos los nodos comparten un estado común definido en `models.py`. Este estado se actualiza de forma incremental a lo largo del flujo:

```python
class GraphState(TypedDict):
    objective: str           # Objetivo en lenguaje natural (entrada del usuario)
    start_date: str          # Fecha inicio del periodo de búsqueda (YYYY-MM-DD)
    end_date: str            # Fecha fin del periodo de búsqueda (YYYY-MM-DD)
    exploration_results: list[dict]  # Titulares y snippets del explorador
    topics: list[str]        # Queries de búsqueda elegidos por el planificador
    planning_reasoning: str  # Justificación del planificador
    raw_content: list[dict]  # Artículos completos recopilados
    evaluation: Evaluation   # Resultado de la evaluación de cobertura
    search_iterations: int   # Contador de iteraciones de búsqueda
    digest: NewsDigest       # Salida final: el reporte estructurado
```

---

## Los 6 nodos en detalle

### 1. `explorador` — Reconocimiento inicial

**Archivo:** `nodes/explorer.py`

El explorador realiza una búsqueda **amplia pero superficial** usando la API de Tavily. No filtra por dominio; su objetivo es descubrir qué está pasando en el sector durante el periodo indicado.

- Construye un query combinando el objetivo del usuario con el rango de fechas.
- Recupera hasta 10 resultados (títulos + snippets de ~500 caracteres).
- No extrae el contenido completo — eso lo hace el extractor más adelante.
- Los resultados alimentan al planificador para que tome decisiones informadas.

**Por qué existe:** Sin esta exploración previa, el planificador tendría que adivinar qué buscar. Con los titulares reales, el agente sabe qué eventos son noticia esta semana.

---

### 2. `planificador` — Selección inteligente de temas

**Archivo:** `nodes/planner.py`
**Modelo:** GPT (temperatura 0, salida estructurada `SearchPlan`)

El planificador recibe los titulares del explorador y usa un LLM para decidir qué temas merecen investigación profunda.

- Genera entre 3 y 5 queries de búsqueda específicos (máximo ~60 caracteres cada uno).
- Prioriza noticias con datos concretos: montos en USD, m², empresas específicas.
- Produce un campo `reasoning` explicando por qué eligió esos temas.

**Ejemplo de output:**
```
topics:
  - "Nearshoring parques industriales Monterrey 2026"
  - "Vacancia oficinas Reforma CDMX Q1 2026"
  - "Amazon centro distribución Guadalajara"
reasoning: "Los titulares muestran tres tendencias claras: ..."
```

---

### 3. `buscador` — Búsqueda profunda y focalizada

**Archivo:** `nodes/searcher.py`

Por cada topic generado por el planificador, el buscador realiza una búsqueda **profunda y filtrada** en medios mexicanos especializados.

- Restringe las búsquedas a dominios de medios mexicanos de CRE (ver lista abajo).
- Aplica el filtro de fechas para garantizar vigencia.
- Recupera hasta 5 artículos por topic con título, URL, snippet y fecha de publicación.

**Dominios incluidos (`MEXICO_DOMAINS`):**
```
eleconomista.com.mx, elfinanciero.com.mx, expansion.mx, forbes.com.mx,
inmobiliare.com, realestatemarket.com.mx, obrasweb.mx, centrourbano.com,
mexicoindustry.com, solili.mx, oem.com.mx/elsoldemexico
```

El resultado se acumula en `raw_content` como una lista de `{topic, sources[]}`.

---

### 4. `extractor` — Extracción de contenido completo

**Archivo:** `nodes/extractor.py`

El buscador solo devuelve snippets. El extractor llama a `tavily.extract()` con las URLs descubiertas para obtener el **texto completo** de cada artículo (hasta 3,000 caracteres por fuente).

- Reemplaza el contenido parcial por el texto completo del artículo.
- Descarta automáticamente las URLs que fallan en la extracción.
- Los errores se manejan con `try/except` para no detener el flujo completo.

Esto es lo que permite al analista final escribir artículos con datos concretos y citas reales, en lugar de basarse en fragmentos.

---

### 5. `evaluador` — Control de calidad con criterios rigurosos

**Archivo:** `nodes/evaluator.py`
**Modelo:** GPT (temperatura 0, salida estructurada `Evaluation`)

El evaluador actúa como un **editor senior** que decide si el material recopilado es suficiente para publicar o si se necesita más investigación.

Analiza:
1. **Cobertura temática:** ¿Hay al menos un tema por sub-sector mencionado en el objetivo?
2. **Calidad de datos:** ¿Hay cifras concretas (m², USD, porcentajes, tasas de vacancia)?
3. **Diversidad de fuentes:** ¿Hay al menos 2 fuentes distintas por tema?
4. **Vigencia:** ¿Las fuentes están dentro del rango de fechas solicitado?

**Criterios de suficiencia:**
- SUFICIENTE: ≥ 3 temas sólidos con datos concretos y ≥ 2 fuentes cada uno.
- INSUFICIENTE: < 3 temas sólidos, o un sub-sector sin cobertura, o mayoría de fuentes fuera de rango.

Si la cobertura es insuficiente, el evaluador devuelve `missing_topics` con queries adicionales a buscar. El límite máximo de iteraciones es **2** (`MAX_SEARCH_ITERATIONS`), tras el cual se pasa al analista de todas formas.

**La función `should_search_more`** implementa la arista condicional del grafo:
- Devuelve `"buscador"` → si falta cobertura y quedan iteraciones.
- Devuelve `"analista"` → si la cobertura es suficiente o se agotaron las iteraciones.

---

### 6. `analista` — Redacción del reporte final

**Archivo:** `nodes/analyst.py`
**Modelo:** GPT-5 (temperatura 0, salida estructurada `NewsDigest`)

El analista recibe todo el contenido recopilado y genera el **digest final estructurado**. Por cada tema relevante produce:

- **Título:** Descriptivo del evento o tendencia.
- **Artículo:** 100-150 palabras con datos concretos (cifras, empresas, ubicaciones).
- **Fuentes:** Lista de URLs de los artículos utilizados.

El output es un objeto `NewsDigest` validado por Pydantic, que se serializa a `reporte.json`.

---

## Flujo de datos completo

```
Usuario define:
  objective = "Noticias CRE México: industrial, oficinas, logística"
  start_date = "2026-02-07"
  end_date   = "2026-02-16"
         │
         ▼
  explorador → 10 titulares + snippets
         │
         ▼
  planificador (LLM) → ["Nearshoring Monterrey", "Oficinas CDMX", "Logística Bajío"]
         │
         ▼
  buscador → 3 topics × 5 artículos = ~15 artículos con snippets
         │
         ▼
  extractor → 15 artículos con contenido completo (~3,000 chars c/u)
         │
         ▼
  evaluador (LLM) → ¿Suficiente? NO → missing_topics = ["FIBRA industrial 2026"]
         │
         ▼ (iteración 2)
  buscador → 4 artículos adicionales
         │
         ▼
  extractor → contenido completo
         │
         ▼
  evaluador (LLM) → ¿Suficiente? SÍ
         │
         ▼
  analista (LLM) → NewsDigest con 4-5 secciones estructuradas
         │
         ▼
  reporte.json  →  converter.py  →  reporte.md / reporte.docx / reporte.txt
```

---

## Conversión de reportes (`converter.py`)

Una vez generado `reporte.json`, el converter permite exportarlo a distintos formatos:

```bash
# Markdown (por defecto)
python converter.py reporte.json

# Texto plano
python converter.py reporte.json --format txt

# Word (.docx)
python converter.py reporte.json --format docx

# Todos los formatos a la vez
python converter.py reporte.json --all
```

Los archivos se guardan en la carpeta `reportes/` con el nombre `reporte_YYYY-MM-DD_YYYY-MM-DD.{ext}`.

---

## Modelos de datos (Pydantic)

```
GraphState          ← Estado interno del grafo (TypedDict)
  ├── SearchPlan    ← Output del planificador (topics + reasoning)
  ├── Evaluation    ← Output del evaluador (is_sufficient + missing_topics)
  └── ReportOutput  ← Archivo JSON final con metadatos
        └── NewsDigest
              └── TopicSection[]  ← title + article + sources[]
```

---

## Configuración y variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
OPENAI_API_KEY=sk-...          # Requerido
TAVILY_API_KEY=tvly-...        # Requerido
```

El límite de iteraciones de búsqueda se controla directamente en `models.py`:

```python
MAX_SEARCH_ITERATIONS = 2
```

---

## El directorio `news_bot` — Entorno virtual (venv)

Al ejecutar `python -m venv news_bot`, Python crea un **entorno virtual aislado** dentro de la carpeta `news_bot/`. Este directorio **no es código del agente** — es la infraestructura que mantiene las dependencias del proyecto separadas del Python del sistema.

### Estructura interna

```
news_bot/
├── bin/              # Ejecutables: python, pip, pytest, activadores del venv
├── lib/
│   └── python3.9/
│       └── site-packages/   # Todas las librerías instaladas
├── include/          # Headers C (para extensiones compiladas como lxml)
└── pyvenv.cfg        # Metadatos del venv (versión Python, origen)
```

### Dependencias instaladas — Estado

| Paquete | Versión instalada | Estado |
|---|---|---|
| tavily-python | 0.7.22 | ✅ |
| python-dotenv | 1.2.1 | ✅ |
| langchain-openai | 0.3.35 | ✅ |
| langgraph | 0.6.11 | ✅ |
| requests | 2.32.5 | ✅ |
| beautifulsoup4 | 4.14.3 | ✅ |
| lxml | 6.0.2 | ✅ |
| tqdm | 4.67.3 | ✅ |
| python-docx | 1.2.0 | ✅ |
| pytest | 8.4.2 | ✅ |
| pytest-mock | 3.15.1 | ✅ |

Todas las dependencias se instalaron correctamente.

### Problema de compatibilidad: Python 3.9 vs 3.10+

**El venv usa Python 3.9.6**, pero el código emplea la sintaxis de union types `X | None` introducida en **Python 3.10** (PEP 604). Esto provoca un error al intentar ejecutar el agente:

```
TypeError: unsupported operand type(s) for |: 'ModelMetaclass' and 'NoneType'
  File "models.py", line 79, in GraphState
    evaluation: Evaluation | None
```

Los archivos afectados son:

| Archivo | Línea | Sintaxis problemática |
|---|---|---|
| `models.py` | 79 | `evaluation: Evaluation \| None` |
| `models.py` | 80 | `digest: NewsDigest \| None` |
| `agent.py` | 86 | `-> NewsDigest \| None:` |
| `converter.py` | 154 | `output_path: str \| None = None` |

**Solución:** reemplazar `X | None` por `Optional[X]` importando `Optional` de `typing`, o usar Python 3.10+.

```python
# Python 3.9 compatible
from typing import Optional
evaluation: Optional[Evaluation]

# Python 3.10+ (sintaxis actual del código)
evaluation: Evaluation | None
```

Adicionalmente, existe una advertencia de SSL al importar `urllib3`:
```
NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+,
currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'
```
Esto no bloquea la ejecución pero puede causar problemas con conexiones HTTPS en algunos casos.

---

## Instalación y ejecución

```bash
# 1. Crear entorno virtual
python -m venv news_bot
source news_bot/bin/activate        # macOS/Linux
.\news_bot\Scripts\Activate.ps1     # Windows PowerShell

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env   # y editar con tus API keys

# 4. Ejecutar el agente
python agent.py

# 5. (Opcional) Convertir el reporte JSON
python converter.py reporte.json --all
```

---

## Tests

```bash
pytest                          # Suite completa
pytest tests/unit/              # Solo tests unitarios por nodo
pytest tests/integration/       # Test del flujo completo
pytest --cov=nodes --cov=agent  # Con cobertura de código
```

Los tests unitarios mockean las llamadas externas (Tavily, OpenAI) para que corran sin API keys.
