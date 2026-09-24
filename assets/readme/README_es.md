<p align="right">
  <a href="../../README.md">English</a> · <a href="README_zh.md">中文</a> · <a href="README_ja.md">日本語</a> · <b>Español</b>
</p>

<p align="center">
  <img src="../catchme-logo.png" width="360" alt="CatchMe Logo"/>
</p>

<h1 align="center">CatchMe: captura toda tu huella digital</h1>

<p align="center">
  <b>Para que tus agentes te entiendan mejor: ligero, sin vectores y potente.</b>
</p>

<p align="center">
  <a href="../../LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue?style=flat" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-%E2%89%A53.11-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey?style=flat" alt="Platform">
  <a href="https://hkuds.github.io/CatchMe"><img src="https://img.shields.io/badge/Blog-online-orange?style=flat" alt="Blog"></a>
  <img src="https://img.shields.io/badge/Report-coming%20soon-lightgrey?style=flat" alt="Report">
  <br>
  <a href="../../COMMUNICATION.md"><img src="https://img.shields.io/badge/Feishu-Group-E9DBFC?style=flat-square&logo=feishu&logoColor=white" alt="Feishu"></a>
  <a href="../../COMMUNICATION.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat-square&logo=wechat&logoColor=white" alt="WeChat"></a>
  <a href="https://discord.gg/2vDYc2w5"><img src="https://img.shields.io/badge/Discord-Join-7289DA?style=flat-square&logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <a href="#-caracter%C3%ADsticas-principales">Funciones</a> &nbsp;·&nbsp;
  <a href="#-arquitectura-de-catchme">Cómo funciona</a> &nbsp;·&nbsp;
  <a href="#-configuraci%C3%B3n-del-llm">LLM</a> &nbsp;·&nbsp;
  <a href="#-primeros-pasos">Inicio</a> &nbsp;·&nbsp;
  <a href="#-coste-y-eficiencia">Coste</a> &nbsp;·&nbsp;
  <a href="#-comunidad">Comunidad</a>
</p>

<p align="center"><i>« <b>Haz lo tuyo. CatchMe captura el resto — almacenado en local para privacidad y seguridad.</b> »</i></p>

<p align="center">
  <img src="../terminal_demo.svg" alt="Demo de terminal CatchMe"/>
</p>

**🦞 Hace que tus agentes sean de verdad personales**. CatchMe se distribuye como skill compatible con agentes CLI (OpenClaw, NanoBot, Claude, Cursor, etc.). Puedes ejecutar CatchMe independientemente; tus agentes consultan la memoria solo con comandos CLI.

## 🎯 Enriquece tu contexto digital personal

<table width="100%">
  <tr>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_coding.png" height="150" alt="Programación"/><br>
      <h3>💻 Asistente de programación personal</h3>
      <b><i>«¿En qué estaba programando hoy en Claude Code?»</i></b><br><br>
      <div align="left">
        • Reproducción de sesiones de código<br>
        • Recuerda los archivos que editaste<br>
        • Rastrea lo que escribiste
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_research.png" height="150" alt="Investigación"/><br>
      <h3>🔍 Investigación profunda personal</h3>
      <b><i>«¿Qué leía ayer sobre IA?»</i></b><br><br>
      <div align="left">
        • Web/PDF vistos<br>
        • Consultas de búsqueda escritas<br>
        • Lectura rastreada
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_files.png" height="150" alt="Archivos"/><br>
      <h3>📁 Gestor de archivos personal</h3>
      <b><i>«¿Qué archivos cambié hoy?»</i></b><br><br>
      <div align="left">
        • Cambios de archivos rastreados<br>
        • Documentos consultados<br>
        • Revisiones de ediciones
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_digital_life.png" height="150" alt="Vida digital"/><br>
      <h3>🧩 Panorama de tu vida digital</h3>
      <b><i>«¿Cómo pasé la tarde?»</i></b><br><br>
      <div align="left">
        • Uso de apps rastreado<br>
        • Flujos de trabajo reproducibles<br>
        • Actividades recuperables
      </div>
    </td>
  </tr>
</table>

## ✨ Características principales

### 📹 Captura de eventos siempre activa
- **Grabación impulsada por eventos**: sin temporizador ni retrasos: captura al instante las acciones del ratón con anotación en cruz.
- **Contexto amplio**: cinco grabadores rastrean ventanas, teclado, portapapeles, notificaciones y archivos en torno a las acciones del ratón.

### 🌲 Jerarquía de memoria inteligente
- **Organización automática**: los flujos crudos se estructuran en cinco niveles: día → sesión → aplicación → ubicación → acción.
- **Resúmenes inteligentes**: resúmenes LLM en cada nivel, convirtiendo registros en árboles de conocimiento buscables.

### 🔍 Recuperación basada en árbol
- **Sin complejidad vectorial**: omite embeddings y VDB: el sistema usa razonamiento basado en árbol para la navegación.
- **Búsqueda de arriba abajo**: el LLM lee resúmenes, elige ramas relevantes y profundiza hasta la evidencia.

### 🤖 Integración con agentes sin configuración
- **Un solo archivo**: coloca un archivo de skill en cualquier agente de IA para integrarlo al instante.
- **Acceso inmediato**: consultas al historial de pantalla por CLI sin configuración extra.

### 🪶 Ultraligero y centrado en la privacidad
- **Huella mínima**: ~0,2 GB de RAM en ejecución con SQLite + FTS5 eficiente.
- **Local y sin conexión**: todos los datos permanecen en tu máquina; modo totalmente offline con Ollama / vLLM / LM Studio.

### 🖥️ Interfaz web rica
- **Exploración visual**: líneas de tiempo interactivas, navegación por árbol de memoria y monitorización del sistema en tiempo real.
- **Conversación natural**: chatea con toda tu huella digital en lenguaje natural.

<p align="center">
  <img src="../web.png" width="100%" alt="Panel web CatchMe"/>
</p>


## 💡 Arquitectura de CatchMe

CatchMe transforma la actividad digital en memoria estructurada y buscable en tres etapas concurrentes:

### 🔄 Grabar → Organizar → Razonar: del caos digital a memoria consultable

**Captura**. Seis grabadores en segundo plano monitorizan ventana activa, pulsaciones, ratón, capturas, portapapeles y notificaciones.

**Índice**. Los eventos se organizan en un árbol de actividad jerárquico: día → sesión → aplicación → ubicación → acción. Cada nodo recibe resúmenes generados por LLM. Recuperación rápida y significativa sin embeddings vectoriales.

**Recuperación**. Haces una pregunta. El LLM recorre el árbol de memoria de arriba abajo, selecciona nodos relevantes e inspecciona datos brutos (capturas, pulsaciones). Luego sintetiza una respuesta precisa.

<p align="center">
  <img src="../catchme-pipe.png" width="680" alt="Pipeline CatchMe: captura → indexación → recuperación"/>
</p>

### 🌲 Árbol de actividad jerárquico
El árbol de actividad es el núcleo de memoria de CatchMe. Ofrece vistas estructuradas y multinivel de tu vida digital: resúmenes de alto nivel o detalle fino.

<p align="center">
  <img src="../fig1_activity_tree.png" width="800" alt="Estructura del árbol de actividad"/>
</p>

### 🔍 Recuperación inteligente en el árbol
CatchMe omite la búsqueda vectorial clásica. En su lugar, el LLM navega directamente tu árbol de actividad. Permite razonamiento complejo entre días y reunión precisa de evidencias del historial bruto.

<p align="center">
  <img src="../fig2_retrieval.png" width="800" alt="Proceso de recuperación basado en árbol"/>
</p>

**📖 Más información**: diseño detallado y profundización técnica en nuestro [blog](https://hkuds.github.io/CatchMe).

## 🧠 Configuración del LLM

### **❗️ Aviso de privacidad de datos**
• **Almacenamiento 100 % local**: todos los datos brutos (capturas, pulsaciones, árboles de actividad) permanecen en `~/data/` y no salen de tu máquina.

• **Opciones priorizando offline**: LLM locales (Ollama, vLLM, LM Studio) permiten operación totalmente offline sin dependencia de la nube.

• **⚠️ Precaución con proveedores en la nube**: si se usan, las API en la nube resumirán tu actividad diaria. **Los endpoints no confiables pueden exponer datos privados** — revisa con cuidado las políticas de datos de tu proveedor.

### **📋 Requisitos**
• **Multimodal**: tu modelo debe admitir texto + imágenes.

• **Ventana de contexto**: asegúrate de que supere los límites de `max_tokens` en `config.json`.

• **Control de costes**: para *controlar costes de forma estricta*, establece límites con `llm.max_calls` o aumenta `filter.mouse_cluster_gap` para reducir la frecuencia de resúmenes.

CatchMe necesita un LLM para resúmenes en segundo plano y recuperación inteligente. Usa **catchme init** (en <a href="#-primeros-pasos">Primeros pasos</a>) para **configuración guiada** o sigue la **configuración manual** más abajo.

Ejemplo de API en la nube:

```json
{
    "llm": {
        "provider": "openrouter",
        "api_key": "sk-or-...",
        "api_url": null,
        "model": "google/gemini-3-flash-preview"
    }
}
```

Ejemplo local / sin conexión:

```json
{
    "llm": {
        "provider": "ollama",
        "api_key": null,
        "api_url": null,
        "model": "gemma3:4b"
    }
}
```

<details>
<summary><b>Proveedores LLM admitidos</b></summary>

| Proveedor                  | Nombre en config         | URL API por defecto                                     | Obtener clave                                                        |
| ------------------------- | ------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------- |
| **OpenRouter** (gateway)  | `openrouter`             | `https://openrouter.ai/api/v1`                          | [openrouter.ai/keys](https://openrouter.ai/keys)                     |
| **Requesty** (gateway)    | `requesty`               | `https://router.requesty.ai/v1`                         | [app.requesty.ai/api-keys](https://app.requesty.ai/api-keys)         |
| **AiHubMix** (gateway)    | `aihubmix`               | `https://aihubmix.com/v1`                               | [aihubmix.com](https://aihubmix.com)                                 |
| **SiliconFlow** (gateway) | `siliconflow`            | `https://api.siliconflow.cn/v1`                         | [cloud.siliconflow.cn](https://cloud.siliconflow.cn)                 |
| **OpenAI**                | `openai`                 | `https://api.openai.com/v1`                             | [platform.openai.com](https://platform.openai.com/api-keys)          |
| **Anthropic**             | `anthropic`              | `https://api.anthropic.com/v1`                          | [console.anthropic.com](https://console.anthropic.com)               |
| **DeepSeek**              | `deepseek`               | `https://api.deepseek.com/v1`                           | [platform.deepseek.com](https://platform.deepseek.com/api_keys)      |
| **Gemini**                | `gemini`                 | `https://generativelanguage.googleapis.com/v1beta`      | [aistudio.google.com](https://aistudio.google.com/apikey)            |
| **Groq**                  | `groq`                   | `https://api.groq.com/openai/v1`                        | [console.groq.com](https://console.groq.com/keys)                    |
| **Mistral**               | `mistral`                | `https://api.mistral.ai/v1`                             | [console.mistral.ai](https://console.mistral.ai)                     |
| **Moonshot / Kimi**       | `moonshot`               | `https://api.moonshot.ai/v1`                            | [platform.moonshot.cn](https://platform.moonshot.cn)                 |
| **MiniMax**               | `minimax`                | `https://api.minimax.io/v1`                             | [platform.minimaxi.com](https://platform.minimaxi.com)               |
| **Zhipu AI (GLM)**        | `zhipu`                  | `https://open.bigmodel.cn/api/paas/v4`                  | [open.bigmodel.cn](https://open.bigmodel.cn)                         |
| **DashScope (Qwen)**      | `dashscope`              | `https://dashscope.aliyuncs.com/compatible-mode/v1`     | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) |
| **VolcEngine**            | `volcengine`             | `https://ark.cn-beijing.volces.com/api/v3`              | [console.volcengine.com](https://console.volcengine.com)             |
| **VolcEngine Coding**     | `volcengine_coding_plan` | `https://ark.cn-beijing.volces.com/api/coding/v3`       | [console.volcengine.com](https://console.volcengine.com)             |
| **BytePlus**              | `byteplus`               | `https://ark.ap-southeast.bytepluses.com/api/v3`        | [console.byteplus.com](https://console.byteplus.com)                 |
| **BytePlus Coding**       | `byteplus_coding_plan`   | `https://ark.ap-southeast.bytepluses.com/api/coding/v3` | [console.byteplus.com](https://console.byteplus.com)                 |
| **Ollama** (local)        | `ollama`                 | `http://localhost:11434/v1`                             | —                                                                    |
| **vLLM** (local)          | `vllm`                   | `http://localhost:8000/v1`                              | —                                                                    |
| **LM Studio** (local)     | `lmstudio`               | `http://localhost:1234/v1`                              | —                                                                    |

> Cualquier endpoint compatible con OpenAI funciona: establece `api_url` y `api_key` directamente.

</details>

<details>
<summary><b>Todos los parámetros de configuración</b></summary>

| Sección       | Parámetro                  | Por defecto | Descripción                                         |
| ------------- | -------------------------- | ----------- | --------------------------------------------------- |
| **web**       | `host`                     | `127.0.0.1` | Dirección de enlace del panel                       |
|               | `port`                     | `8765`      | Puerto del panel                                    |
| **llm**       | `provider`                 | —           | Nombre del proveedor LLM (ver tabla)                |
|               | `api_key`                  | —           | Clave API del proveedor                             |
|               | `api_url`                  | *(auto)*    | Endpoint personalizado; si se omite, se asigna por proveedor |
|               | `model`                    | —           | Nombre del modelo (depende del proveedor)           |
|               | `max_calls`                | `0`         | Máx. llamadas LLM por ciclo (`0` = ilimitado; límite para costes) |
|               | `max_images_per_cluster`   | `5`         | Máx. capturas por clúster de eventos                |
| **filter**    | `window_min_dwell`         | `3.0`       | Tiempo mín. en ventana (s) antes de grabar          |
|               | `keyboard_cluster_gap`     | `3.0`       | Intervalo de agrupación del teclado (s)            |
|               | `mouse_cluster_gap`        | `3.0`       | Intervalo para fusionar eventos de ratón (s); **valores mayores reducen resúmenes LLM** |
| **summarize** | `language`                 | `en`        | Idioma de salida del resumen (`en`, `zh`, etc.)     |
|               | `max_tokens_l0`–`l3`       | `1200`      | Máx. tokens por nivel del árbol (L0=acción … L3=sesión) |
|               | `temperature`              | `0.4`       | Temperatura del LLM para resúmenes                   |
|               | `max_workers`              | `2`         | Workers de resumen concurrentes                     |
|               | `debounce_sec`             | `3.0`       | Debounce antes de disparar el resumen               |
|               | `save_interval_sec`        | `5.0`       | Intervalo de guardado automático del árbol          |
| **retrieve**  | `max_prompt_chars`         | `42000`     | Máx. caracteres en el prompt de recuperación       |
|               | `max_iterations`           | `15`        | Máx. iteraciones de recorrido del árbol             |
|               | `max_file_chars`           | `8000`      | Máx. caracteres de archivos extraídos               |
|               | `max_select_nodes`         | `7`         | Máx. nodos seleccionados por iteración              |
|               | `max_tokens_step`          | `4096`      | Máx. tokens por paso de recuperación                |
|               | `max_tokens_answer`        | `8192`      | Máx. tokens para la respuesta final                 |
|               | `temperature_select`       | `0.3`       | Temperatura para selección de nodos                 |
|               | `temperature_answer`       | `0.5`       | Temperatura para generación de respuesta            |
|               | `temperature_time_resolve` | `0.1`       | Temperatura para resolución temporal                |
|               | `max_tokens_time_resolve`  | `1000`      | Máx. tokens para resolución temporal                |

</details>

## 🚀 Primeros pasos

### 📦 Instalación

```bash
git clone https://github.com/HKUDS/catchme.git && cd catchme

conda create -n catchme python=3.11 -y && conda activate catchme

pip install -e .
```

> **macOS** — concede *Accesibilidad*, *Monitorización de entrada* y *Grabación de pantalla* en Ajustes del sistema → Privacidad y seguridad  
> **Windows** — ejecuta como administrador para la monitorización global de entrada

### ⚡ Init

```bash
catchme init                  # configuración interactiva: proveedor, clave API, modelo
```

### 🔥 Ejecución

```bash
catchme awake                 # iniciar grabación
catchme web                   # visualizar y chatear

# o por CLI
catchme ask -- "¿Qué he hecho hoy?"
```

<details>
<summary><b>Referencia CLI</b></summary>

| Comando                     | Descripción                                            |
| --------------------------- | ------------------------------------------------------ |
| `catchme awake`             | Inicia el demonio de grabación                         |
| `catchme web [-p PORT]`     | Lanza el panel web (por defecto `http://127.0.0.1:8765`) |
| `catchme ask -- "pregunta"` | Consulta tu actividad en lenguaje natural              |
| `catchme cost`              | Muestra uso de tokens LLM (últimos 10 min / hoy / total) |
| `catchme disk`              | Desglose de almacenamiento y recuento de eventos       |
| `catchme ram`               | Uso de memoria de procesos en ejecución                |
| `catchme init`              | Configuración interactiva: proveedor, clave y modelo   |

</details>


## 🦞 CatchMe hace que tus agentes sean de verdad personales
CatchMe se distribuye como skill compatible con agentes CLI (OpenClaw, NanoBot, Claude, Cursor, etc.).

**🪶 Integración con agentes:**  
Ejecuta CatchMe tú mismo. Tus agentes consultan la memoria solo con comandos CLI.

```bash
# 1. Inicia CatchMe tú
catchme awake

# 2. Da el skill ligero a tu agente
cp CATCHME-light.md ~/.cursor/skills/catchme/SKILL.md
```

**Opción B — Skill completo** (el agente gestiona todo el ciclo de vida de CatchMe):

```bash
cp CATCHME-full.md ~/.cursor/skills/catchme/SKILL.md
```

### 🔧 Integrar en tu flujo actual

```python
from catchme import CatchMe
from catchme.pipelines.retrieve import retrieve

# 1. Búsqueda en una línea — búsqueda rápida por palabras clave en toda la actividad
with CatchMe() as mem:
    for e in mem.search("meeting notes"):
        print(e.timestamp, e.data)

# 2. Recuperación con LLM — preguntas en lenguaje natural sobre tu historial de pantalla
for step in retrieve("What was I working on this morning?"):
    if step["type"] == "answer":
        print(step["content"])
```

## 📊 Coste y eficiencia

*Benchmark: **2 horas de uso intensivo y continuo en MacBook Air M4**.*


| Métrica                                          | Valor                                                                           |
| ----------------------------------------------- | ------------------------------------------------------------------------------- |
| **RAM en ejecución**                            | ~0,2 GB                                                                    |
| **Uso de disco**                                | ~200 MB                                                                        |
| **Rendimiento de tokens**                       | entrada ~6 M, salida ~0,7 M                                                    |
| **Coste LLM** — `qwen-3.5-plus`                 | ~0,42 $ vía [Aliyun DashScope](https://home.console.aliyun.com/home/dashboard/) |
| **Coste LLM** — `gemini-3-flash-preview`        | ~5,00 $ vía [OpenRouter](https://openrouter.ai/models)                     |
| **Velocidad de recuperación completa** (depende de la pregunta) | 5–20 s por consulta con `gemini-3-flash-preview`                                |


## 🚀 Hoja de ruta
CatchMe evoluciona con la comunidad. Próximas funciones:

**Grabación multi-dispositivo**. Captura y unifica actividades GUI en todas tus máquinas mediante sincronización LAN.

**Agrupación dinámica**. Algoritmos adaptativos que reflejan mejor tus patrones y flujos de trabajo, reduciendo costes innecesarios.

**Mejor uso de datos**. Más información a partir de capturas y metadatos, más allá de los pipelines actuales de procesamiento.

> 🌟 **Da una estrella al repo** para seguir las novedades — tu interés nos impulsa.

Agradecemos cualquier contribución: comentarios, informes de errores, ideas o pull requests. Consulta [CONTRIBUTING.md](../../CONTRIBUTING.md).

## 🤝 Comunidad

### ¡Agradecimientos!

CatchMe se inspira en estos proyectos de código abierto:

| Proyecto                                                         | Inspiración                                           |
| --------------------------------------------------------------- | ----------------------------------------------------- |
| [ActivityWatch](https://github.com/ActivityWatch/activitywatch) | Pionero en seguimiento de actividad open source       |
| [Screenpipe](https://github.com/mediar-ai/screenpipe)           | Infraestructura de grabación de pantalla para agentes IA |
| [Windrecorder](https://github.com/Antonoko/Windrecorder)        | Grabación y búsqueda personal en Windows             |
| [OpenRecall](https://github.com/openrecall/openrecall)          | Alternativa open source a Windows Recall             |
| [Selfspy](https://github.com/selfspy/selfspy)                   | Registro de actividad estilo daemon clásico           |
| [PageIndex](https://github.com/HKUDS/PageIndex)                 | Recuperación documental en árbol sin embeddings      |
| [MineContext](https://github.com/volcengine/MineContext)        | Socio de IA consciente del contexto y captura de pantalla |


### 🏛️ Ecosistema

CatchMe forma parte del ecosistema de agentes **[HKUDS](https://github.com/HKUDS)** — la capa de infraestructura para agentes de IA personales:

<table>
  <tr>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/nanobot"><b>NanoBot</b></a><br>
      <sub>Asistente de IA personal ultraligero</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/CLI-Anything"><b>CLI-Anything</b></a><br>
      <sub>Hacer que todo el software sea nativo para agentes</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/ClawWork"><b>ClawWork</b></a><br>
      <sub>De asistente de IA a compañero de trabajo IA</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/ClawTeam"><b>ClawTeam</b></a><br>
      <sub>Inteligencia de enjambre de agentes para automatización de equipos</sub>
    </td>
  </tr>
</table>
<br>
<p align="center">
  Gracias por visitar ✨ <b>CatchMe</b>
</p>
<p align="center">
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.catchme" alt="visitors"/>
</p>
