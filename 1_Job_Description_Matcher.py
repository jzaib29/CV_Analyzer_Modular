import json
import os
import streamlit as st
from groq import Groq
from utils import extract_text_from_file

# Page Config
st.set_page_config(page_title="CV vs Job Description Matcher", layout="wide")

# Subtle styling palette consistent with main app
st.markdown("""
<style>
    .match-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 18px;
        text-align: center;
        margin-bottom: 18px;
    }
    .match-score {
        font-size: 36px;
        font-weight: 700;
        color: #0f172a;
    }
    .pill-green {
        display: inline-block;
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 600;
        margin: 3px;
    }
    .pill-red {
        display: inline-block;
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 600;
        margin: 3px;
    }
    .action-box {
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
        color: #14532d;
    }
</style>
""", unsafe_allow_html=True)

st.title("Target Job Matcher & Gap Analysis")
st.caption("Benchmark candidate CV content directly against specific job specifications.")

# Setup Groq Client
api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)
if not api_key:
    api_key = st.sidebar.text_input("Enter Groq API Key", type="password")

if not api_key:
    st.info("Please provide a Groq API Key via environment variables, Streamlit secrets, or sidebar.")
    st.stop()

client = Groq(api_key=api_key)

# LLM Comparison Function
def match_cv_to_jd(cv_text: str, jd_text: str) -> dict:
    prompt = f"""
Compare the candidate's CV against the provided Job Description (JD).
Evaluate relevancy, skill coverage, keyword alignment, and experience gaps.

Provide your response STRICTLY as valid JSON matching this schema:
{{
  "match_score": <float between 0 and 10>,
  "alignment_summary": "Brief 2-sentence overview of candidate fit",
  "matched_skills": ["skill 1", "skill 2"],
  "missing_critical_skills": ["missing skill 1", "missing skill 2"],
  "experience_gap_analysis": ["point 1", "point 2"],
  "tailoring_recommendations": [
    {{
      "target_section": "e.g., Summary or Experience",
      "action": "Concrete advice to adjust the resume to reflect required competencies"
    }}
  ]
}}

Job Description:
\"\"\"{jd_text}\"\"\"

Candidate CV:
\"\"\"{cv_text}\"\"\"
"""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You are an executive hiring manager and ATS optimization specialist. Return strictly valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    return json.loads(response.choices[0].message.content)

# Inputs Section
col_cv, col_jd = st.columns(2)

with col_cv:
    st.subheader("1. Candidate CV (Required)")
    cv_file = st.file_uploader("Upload CV", type=["pdf", "docx", "doc", "txt"], key="cv_input")

with col_jd:
    st.subheader("2. Target Job Description (Optional)")
    jd_tab1, jd_tab2 = st.tabs(["Upload Document", "Paste Text"])
    with jd_tab1:
        jd_file = st.file_uploader("Upload JD", type=["pdf", "docx", "doc", "txt"], key="jd_file_input")
    with jd_tab2:
        jd_pasted_text = st.text_area("Or paste JD text here", height=140, placeholder="Paste JD requirements, responsibilities, and qualifications...")

# Run Analysis
if st.button("Analyze Match"):
    if not cv_file:
        st.error("Please upload a candidate CV to proceed.")
        st.stop()

    cv_text = extract_text_from_file(cv_file)
    if not cv_text:
        st.error("Could not extract readable text from the CV.")
        st.stop()

    # Determine JD input
    jd_text = ""
    if jd_file:
        jd_text = extract_text_from_file(jd_file)
    elif jd_pasted_text.strip():
        jd_text = jd_pasted_text.strip()

    if not jd_text:
        st.warning("No Job Description provided. You can either upload a JD document or paste the job posting to run a gap analysis.")
        st.stop()

    with st.spinner("Evaluating match alignment with openai/gpt-oss-120b..."):
        try:
            results = match_cv_to_jd(cv_text, jd_text)

            # Match Score Display
            score = results.get("match_score", 0)
            summary = results.get("alignment_summary", "")
            
            st.markdown(f"""
            <div class="match-card">
                <div class="match-score">{score} <span style="font-size: 18px; color: #64748b;">/ 10</span></div>
                <div style="font-size: 14px; font-weight: 600; color: #475569; margin-bottom: 6px;">Target Role Compatibility</div>
                <div style="font-size: 14px; color: #334155; max-width: 700px; margin: 0 auto;">{summary}</div>
            </div>
            """, unsafe_allow_html=True)

            # Skills Gap Comparison
            col_matched, col_missing = st.columns(2)
            with col_matched:
                st.markdown("#### Matched Competencies & Keywords")
                matched = results.get("matched_skills", [])
                if matched:
                    st.markdown("".join([f'<span class="pill-green">{s}</span>' for s in matched]), unsafe_allow_html=True)
                else:
                    st.write("No direct keyword matches identified.")

            with col_missing:
                st.markdown("#### Missing or Underrepresented Requirements")
                missing = results.get("missing_critical_skills", [])
                if missing:
                    st.markdown("".join([f'<span class="pill-red">{s}</span>' for s in missing]), unsafe_allow_html=True)
                else:
                    st.write("No critical skill gaps identified.")

            st.divider()

            # Tailoring Recommendations
            st.markdown("#### Recommended Resume Adjustments")
            recs = results.get("tailoring_recommendations", [])
            for r in recs:
                sec = r.get("target_section", "General")
                act = r.get("action", "")
                st.markdown(f"""
                <div class="action-box">
                    <strong>Focus Section:</strong> {sec}<br>
                    <span>{act}</span>
                </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error executing JD comparison: {str(e)}")