from pypdf import PdfReader
from docx import Document

def extract_text_from_file(uploaded_file) -> str:
    """Extracts plain text from PDF, DOCX, DOC, or TXT file uploads."""
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