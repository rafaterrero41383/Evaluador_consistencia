# app.py
import os
import tempfile
import time
import streamlit as st
from docx import Document
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd

# --- Configuración inicial ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
st.set_page_config(page_title="Evaluador de Consistencia HDU ↔ DTM (BIAN)", layout="wide")

# --- CSS (idéntico al original) ---
st.markdown("""
<style>
    .st-emotion-cache-16txtl3, #MainMenu { display: none; }
    .st-emotion-cache-z5fcl4 { padding-top: 2rem; }

    .chat-message { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px; }
    .user-message { flex-direction: row-reverse; }
    .avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
    .message-bubble { padding: 14px 18px; border-radius: 18px; max-width: 85%; word-wrap: break-word; line-height: 1.4; }
    .user-bubble { background-color: #e3f2fd; border: 1px solid #bbdefb; }
    .assistant-bubble { background-color: #f1f0f0; border: 1px solid #ddd; }

    .st-emotion-cache-1jicfl2 {
        flex: 1 1 0%;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# --- Estado global ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processing_triggered" not in st.session_state:
    st.session_state.processing_triggered = False
if "uploaded_hdu" not in st.session_state:
    st.session_state.uploaded_hdu = None
if "uploaded_dtm" not in st.session_state:
    st.session_state.uploaded_dtm = None

# --- Avatares ---
assistant_avatar = "https://cdn-icons-png.flaticon.com/512/4712/4712109.png"
user_avatar = "https://cdn-icons-png.flaticon.com/512/1077/1077012.png"

# --- Encabezado ---
st.markdown("<h1 style='text-align: center;'>🤖 Evaluador de Consistencia HDU ↔ DTM</h1>", unsafe_allow_html=True)

# --- Botón de reinicio ---
if st.button("🔄 Reiniciar aplicación"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- Carga de archivos ---
col1, col2 = st.columns(2)

with col1:
    hdu_file = st.file_uploader("1️⃣ Adjunta tu archivo HDU (.xlsx)", type=["xlsx"])
    if hdu_file and "uploaded_hdu_flag" not in st.session_state:
        try:
            excel_data = pd.read_excel(hdu_file, sheet_name=None)
            hdu_text = ""
            for sheet_name, df in excel_data.items():
                hdu_text += f"\n\n=== Hoja: {sheet_name} ===\n"
                hdu_text += df.fillna("").astype(str).to_string(index=False)
            st.session_state.uploaded_hdu = {"name": hdu_file.name, "content": hdu_text}
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"📊 HDU `{hdu_file.name}` cargada correctamente desde Excel."
            })
            st.session_state.uploaded_hdu_flag = True
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Error al leer el archivo Excel: {e}")

with col2:
    dtm_file = st.file_uploader("2️⃣ Adjunta tu archivo DTM (.docx)", type=["docx"])
    if dtm_file and "uploaded_dtm_flag" not in st.session_state:
        try:
            doc = Document(dtm_file)
            dtm_text = "\n".join([p.text for p in doc.paragraphs])
            st.session_state.uploaded_dtm = {"name": dtm_file.name, "content": dtm_text}
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"📘 DTM `{dtm_file.name}` cargado correctamente."
            })
            st.session_state.uploaded_dtm_flag = True
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Error al leer el DTM: {e}")

# --- Contenedor del chat ---
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        avatar = user_avatar if msg["role"] == "user" else assistant_avatar
        bubble_class = "user-bubble" if msg["role"] == "user" else "assistant-bubble"
        message_class = "user-message" if msg["role"] == "user" else "assistant-message"
        st.markdown(
            f'<div class="chat-message {message_class}">'
            f'<img src="{avatar}" class="avatar">'
            f'<div class="message-bubble {bubble_class}">{msg["content"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

# --- Lógica de procesamiento ---
if st.session_state.processing_triggered:
    with st.spinner("Evaluando consistencia HDU ↔ DTM... por favor, espera."):
        time.sleep(2)

        hdu_text = st.session_state.uploaded_hdu["content"]
        dtm_text = st.session_state.uploaded_dtm["content"]

        # Prompt principal
        prompt = f"""
Eres un auditor técnico experto en arquitectura BIAN y documentación ágil.
Evalúa la consistencia entre una Historia de Usuario Detallada (HDU) y un Diseño Técnico de Microservicio (DTM)
usando la siguiente rúbrica basada en 25 puntos de control.

Cada punto se califica del 0 al 4, ponderación igual. Muestra la tabla Markdown con columnas:
| # | Punto de control | Puntaje (0–4) | Evidencia breve | Incongruencia | Recomendación |

Calcula:
- Total sobre 100
- Porcentaje de consistencia
- Clasificación (Alta / Media-Alta / Media / Baja)
- Top 5 incongruencias más críticas con breve descripción y recomendación

Usa español claro y formato Markdown. 
No uses JSON ni texto fuera del formato solicitado.

Entradas:
DTM:
\"\"\"
{dtm_text}
\"\"\"

HDU:
\"\"\"
{hdu_text}
\"\"\"
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un auditor técnico que compara HDU y DTM usando 25 puntos de control BIAN."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            result = response.choices[0].message.content.strip()

            # Mostrar resultado
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"📋 **Evaluación generada:**\n\n{result}"
            })

            # Guardar para descarga
            with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmpfile:
                tmpfile.write(result.encode("utf-8"))
                tmpfile.seek(0)
                st.session_state.generated_md = tmpfile.read()

        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Error: {e}"})

        st.session_state.processing_triggered = False
        st.rerun()

# --- Botón de descarga ---
if "generated_md" in st.session_state and st.session_state.generated_md:
    st.download_button(
        "⬇️ Descargar Reporte (.md)",
        st.session_state.generated_md,
        "evaluacion_consistencia.md",
        "text/markdown"
    )
    del st.session_state.generated_md

# --- Chat Input ---
if prompt := st.chat_input("Escribe tu mensaje o pide evaluar la consistencia..."):
    if not st.session_state.uploaded_hdu or not st.session_state.uploaded_dtm:
        st.toast("⚠️ Por favor, carga primero los archivos HDU (.xlsx) y DTM (.docx).", icon="⚠️")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.processing_triggered = True
        st.rerun()
