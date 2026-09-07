import json
import os
import streamlit as st
from groq import Groq
from pypdf import PdfReader
from docx import Document

# 1. Page Configuration
st.set_page_config(page_title="CV Quality & Line Reviewer", layout="wide")

# Subtle styling palette (Slate, Emerald, Amber, Indigo)
st.markdown("""
<style>
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-val {
        font-size: 28px;
        font-weight: 700;
        color: #1e293b;
    }
    .metric-lbl {
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
    }
    .section-box {
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .box-green {
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        color: #14532d;
    }
    .box-amber {
        background-color: #fffbeb;
        border-left: 4px solid #d97706;
        color: #78350f;
    }
    .box-indigo {
        background-color: #eef2ff;
        border-left: 4px solid #4f46e5;
        color: #1e1b4b;
    }
    .diff-container {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .diff-original {
        background-color: #fef2f2;
        color: #991b1b;
        padding: 8px 12px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 13px;
        margin-bottom: 6px;
    }
    .diff-replacement {
        background-color: #f0fdf4;
        color: #166534;
        padding: 8px 12px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

st.title("CV Reviewer & Line-by-Line Editor")

# 2. Setup Groq Client
api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)
if not api_key:
    api_key = st.sidebar.text_input("Enter Groq API Key", type="password")

if not api_key:
    st.info("Please provide your Groq API Key via environment variables, Streamlit secrets, or sidebar.")
    st.stop()

client = Groq(api_key=api_key)

# 3. Document Extraction Helper
def extract_text_from_file(uploaded_file) -> str:
    filename = uploaded_file.name.lower()
    text = ""
    if filename.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    elif filename.endswith((".docx", ".doc")):
        doc = Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif filename.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8", errors="ignore")
    return text.strip()

# 4. LLM Analysis Function with In-line Extraction
def analyze_cv_with_groq(cv_text: str) -> dict:
    prompt = f"""
Analyze the candidate's CV text provided below. 
Evaluate structure, continuity, formatting clarity, and professional language.

In addition to category scores and broad feedback, extract specific fragments or bullet points from the text that need improvement. For each fragment, identify the precise flaw and supply a production-ready, improved version.

Provide your response STRICTLY as valid JSON matching this schema:
{{
  "overall_score": <float between 0 and 10>,
  "structure_score": <float between 0 and 10>,
  "continuity_score": <float between 0 and 10>,
  "design_score": <float between 0 and 10>,
  "language_score": <float between 0 and 10>,
  "feedback": {{
    "strengths": ["...", "..."],
    "weaknesses": ["...", "..."],
    "actionable_recommendations": ["...", "..."]
  }},
  "targeted_improvements": [
    {{
      "original_text": "Exact or near-exact quote from the CV",
      "issue": "Specific diagnosis (e.g., passive phrasing, missing quantified metrics, ambiguous timeline)",
      "suggested_replacement": "Rewritten, high-impact replacement"
    }}
  ]
}}

Resume Content:
\"\"\"{cv_text}\"\"\"
"""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You are a senior executive recruiter and resume proofreader. Return strictly valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    return json.loads(response.choices[0].message.content)

# 5. UI Layout & Execution
uploaded_file = st.file_uploader(
    "Upload CV (PDF, DOCX, TXT)", 
    type=["pdf", "docx", "doc", "txt"]
)

if uploaded_file and st.button("Evaluate CV"):
    with st.spinner("Parsing document..."):
        cv_text = extract_text_from_file(uploaded_file)
        
    if not cv_text:
        st.error("No extractable text found in file. Please ensure the document is not a scanned image.")
        st.stop()

    with st.spinner("Evaluating with openai/gpt-oss-120b..."):
        try:
            result = analyze_cv_with_groq(cv_text)
            
            # --- Metrics Dashboard ---
            st.markdown("### Evaluation Scores")
            m_cols = st.columns(5)
            scores = [
                ("Overall Score", result.get("overall_score", 0)),
                ("Structure", result.get("structure_score", 0)),
                ("Continuity", result.get("continuity_score", 0)),
                ("Design / Hierarchy", result.get("design_score", 0)),
                ("Language & Polish", result.get("language_score", 0))
            ]
            for col, (label, val) in zip(m_cols, scores):
                with col:
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <div class="metric-val">{val}<span style="font-size:16px; color:#94a3b8;">/10</span></div>
                            <div class="metric-lbl">{label}</div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )

            st.write("")
            
            # --- Summary Insights ---
            feedback = result.get("feedback", {})
            col_s, col_w, col_r = st.columns(3)
            
            with col_s:
                st.markdown("#### Strengths")
                for item in feedback.get("strengths", []):
                    st.markdown(f'<div class="section-box box-green">{item}</div>', unsafe_allow_html=True)
                    
            with col_w:
                st.markdown("#### Areas to Watch")
                for item in feedback.get("weaknesses", []):
                    st.markdown(f'<div class="section-box box-amber">{item}</div>', unsafe_allow_html=True)
                    
            with col_r:
                st.markdown("#### Key Priorities")
                for item in feedback.get("actionable_recommendations", []):
                    st.markdown(f'<div class="section-box box-indigo">{item}</div>', unsafe_allow_html=True)

            st.divider()

            # --- Targeted Line-by-Line Changes ---
            st.markdown("### Targeted Corrections & Replacements")
            st.caption("Directly swap the highlighted source phrases with the recommended versions.")
            
            targeted = result.get("targeted_improvements", [])
            if targeted:
                for idx, imp in enumerate(targeted):
                    orig = imp.get("original_text", "")
                    issue = imp.get("issue", "")
                    replacement = imp.get("suggested_replacement", "")
                    
                    st.markdown(f"""
                    <div class="diff-container">
                        <div style="font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 6px;">
                            #{idx + 1} — Diagnosis: <span style="color: #0f172a;">{issue}</span>
                        </div>
                        <div class="diff-original"><b>Current:</b> {orig}</div>
                        <div class="diff-replacement"><b>Suggested:</b> {replacement}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No localized syntax or bullet-level flaws flagged for replacement.")
                    
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")
