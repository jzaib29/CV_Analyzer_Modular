import json
import os
import streamlit as st
from groq import Groq
from pypdf import PdfReader
from docx import Document

# 1. Page Configuration
st.set_page_config(page_title="AI Resume Analyzer", layout="wide")
st.title("CV Reviewer & Quality Evaluator")

# 2. Setup Groq Client
api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)
if not api_key:
    api_key = st.sidebar.text_input("Enter Groq API Key", type="password")

if not api_key:
    st.info("Please provide a Groq API Key via environment variables, Streamlit secrets, or the sidebar input.")
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

# 4. LLM Analysis Function
def analyze_cv_with_groq(cv_text: str) -> dict:
    prompt = f"""
Act as a professional recruiter.
Analyze the candidate's CV text provided below. 
Evaluate it strictly across 4 dimensions:
1. Structure: Clear logical sections (Summary, Experience, Education, Skills).
2. Continuity: Chronological career flow, absence of unexplained gaps, logical progression.
3. Design & Formatting Clarity: Readability, consistent bulleting, concise headers as reflected in text hierarchy.
4. Language & Beautification: Professional tone, action verbs, strong metrics, absence of repetitive phrasing.

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
  }}
}}

Resume Content:
\"\"\"{cv_text}\"\"\"
"""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You are an expert technical recruiter and resume evaluator. Always respond with raw JSON without markdown markers."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    return json.loads(response.choices[0].message.content)

# 5. UI Layout & Execution
uploaded_file = st.file_uploader(
    "Upload CV (PDF, DOCX, TXT)", 
    type=["pdf", "docx", "doc", "txt"]
)

if uploaded_file and st.button("Evaluate CV"):
    with st.spinner("Extracting content..."):
        cv_text = extract_text_from_file(uploaded_file)
        
    if not cv_text:
        st.error("No readable text found. If using an image-only PDF, standard OCR is required.")
        st.stop()

    with st.spinner("Analyzing structure, continuity, and design with Groq..."):
        try:
            result = analyze_cv_with_groq(cv_text)
            
            # Display Metric Breakdown
            st.subheader("Evaluation Results")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Overall Score", f"{result.get('overall_score', 0)} / 10")
            col2.metric("Structure", f"{result.get('structure_score', 0)} / 10")
            col3.metric("Continuity", f"{result.get('continuity_score', 0)} / 10")
            col4.metric("Design", f"{result.get('design_score', 0)} / 10")
            col5.metric("Language", f"{result.get('language_score', 0)} / 10")

            # Display Detailed Insights
            feedback = result.get("feedback", {})
            st.divider()
            
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("**Key Strengths**")
                for s in feedback.get("strengths", []):
                    st.write(f"- {s}")
                    
                st.markdown("**Areas for Improvement**")
                for w in feedback.get("weaknesses", []):
                    st.write(f"- {w}")

            with c_right:
                st.markdown("**Actionable Recommendations**")
                for rec in feedback.get("actionable_recommendations", []):
                    st.write(f"- {rec}")
                    
        except Exception as e:
            st.error(f"Error evaluating document: {str(e)}")
