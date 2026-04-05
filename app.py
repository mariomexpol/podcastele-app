import streamlit as st
import requests
import io
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="PodcastELE Pro - Gemini Edition", layout="wide", page_icon="🎙️")

# --- FUNCIONES DE SOPORTE ---
def limpiar_texto(texto):
    return texto.replace('\\_', '_').replace('\\', '')

def generar_docx_podcast(texto_ia, escuela, profe, tema, nivel, logo_file=None):
    doc = Document()
    section = doc.sections[0]
    header = section.header
    htxt = header.paragraphs[0]
    
    if logo_file:
        try:
            run_logo = htxt.add_run()
            run_logo.add_picture(logo_file, width=Inches(1.2))
            htxt.alignment = WD_ALIGN_PARAGRAPH.LEFT
        except: pass
    
    info_h = header.add_paragraph(f"{escuela}\nMaterial de Apoyo - Nivel {nivel}\nProf. {profe}")
    info_h.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph() 
    titulo = doc.add_heading(f"GUION Y EJERCICIOS: {tema.upper()}", 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    lineas = limpiar_texto(texto_ia).split('\n')
    for linea in lineas:
        l = linea.strip()
        if not l: continue
        
        títulos_clave = ["#", "GUION", "SCRIPT", "VOCABULARIO", "EJERCICIOS", "SOLUCIONARIO", "NOTAS", "GLOSARIO"]
        if any(keyword in l.upper() for keyword in títulos_clave) and len(l) < 100:
            if "SOLUCIONARIO" in l.upper(): doc.add_page_break()
            level = 1 if l.startswith('#') else 2
            doc.add_heading(l.replace('#', '').strip(), level=level)
            continue

        p = doc.add_paragraph()
        if l.startswith('- '):
            p.style = 'List Bullet'
            l = l[2:]
            
        partes = l.split('**')
        for i, parte in enumerate(partes):
            run = p.add_run(parte)
            if i % 2 == 1:
                run.bold = True
                run.font.color.rgb = RGBColor(200, 146, 74)
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- BARRA LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2991/2991201.png", width=100)
    st.header("⚙️ Configuración")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    logo_subido = st.file_uploader("Logo de tu escuela/podcast", type=["png", "jpg"])
    nombre_escuela = st.text_input("Nombre del Proyecto", "PodcastELE")
    nombre_profe = st.text_input("Autor/Profesor", "Mario")
    idioma_apoyo = st.selectbox("Traducciones de apoyo", ["Ninguno (100% Español)", "Inglés", "Polaco", "Francés"])

# --- INTERFAZ PRINCIPAL ---
st.title("🎙️ PodcastELE Pro: Generador de Guiones")
st.caption("Crea cuentos inmersivos para tus alumnos y exporta el material pedagógico a Word.")

col1, col2 = st.columns([2, 1])

with col1:
    tema_input = st.text_area("Tema o idea del cuento", placeholder="Ej: Una detective que resuelve misterios...")
    instrucciones_extra = st.text_input("Instrucciones adicionales", placeholder="Ej: Incluir modismos...")

with col2:
    nivel_mcer = st.selectbox("Nivel MCER", ["A1", "A2", "B1", "B2", "C1", "C2"])
    duracion = st.select_slider("Duración", options=["3 min", "5 min", "10 min", "15 min"], value="5 min")
    genero = st.selectbox("Género", ["Misterio", "Romance", "Histórico", "Fábula", "Humor"])

# --- LÓGICA DE GENERACIÓN ---
if st.button("✨ Generar Guion y Material Pedagógico"):
    if not api_key or not tema_input:
        st.warning("⚠️ Por favor, introduce la API Key y el tema del cuento.")
    else:
        try:
            with st.spinner("Conectando con Gemini y redactando..."):
                url_models = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
                res_models = requests.get(url_models).json()
                
                modelos_disponibles = [m["name"] for m in res_models.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
                
                modelo_final = "models/gemini-1.5-pro"
                if modelo_final not in modelos_disponibles:
                    if "models/gemini-1.5-flash" in modelos_disponibles:
                        modelo_final = "models/gemini-1.5-flash"
                    elif modelos_disponibles:
                        modelo_final = modelos_disponibles[0]
                    else:
                        st.error("No se encontraron modelos. Revisa tu clave.")
                        st.stop()

                soporte = f"Usa el {idioma_apoyo} para traducir palabras difíciles." if idioma_apoyo != "Ninguno (100% Español)" else "Todo el material debe ser 100% en español."
                
                prompt = (
                    f"Actúa como guionista y profesor de ELE. Crea material para podcast.\n"
                    f"PROYECTO: {nombre_escuela}. NIVEL: {nivel_mcer}. TEMA: {tema_input}. GÉNERO: {genero}.\n"
                    f"ESTRUCTURA:\n1. # TITULO\n2. # GUION: Cuento de {duracion}.\n3. # GLOSARIO: 10 términos con traducción al {idioma_apoyo}.\n"
                    f"4. # EJERCICIOS: Comprensión y gramática.\n5. # SOLUCIONARIO\n6. # NOTAS DEL NARRADOR.\n"
                    f"{soporte}\n{instrucciones_extra}\nFirma: {nombre_profe}."
                )

                url_gen = f"https://generativelanguage.googleapis.com/v1beta/{modelo_final}:generateContent?key={api_key.strip()}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                res_gen = requests.post(url_gen, json=payload)
                
                if res_gen.status_code == 200:
                    st.session_state['material_podcast'] = res_gen.json()["candidates"][0]["content"]["parts"][0]["text"]
                    st.success(f"¡Contenido generado con {modelo_final}!")
                else:
                    st.error(f"Error ({res_gen.status_code}): {res_gen.text}")

        except Exception as e:
            st.error(f"Error de ejecución: {e}")

# --- VISUALIZACIÓN ---
if 'material_podcast' in st.session_state:
    st.divider()
    docx_bytes = generar_docx_podcast(st.session_state['material_podcast'], nombre_escuela, nombre_profe, tema_input, nivel_mcer, logo_file=logo_subido)
    
    st.download_button(label="📥 Descargar Guion (Word)", data=docx_bytes, file_name=f"Podcast_{tema_input[:20]}.docx")
    st.markdown("### 📝 Vista previa")
    st.markdown(st.session_state['material_podcast'])
