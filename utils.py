import PyPDF2
import docx
import re


def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception:
        return ""
    return text


def extract_text_from_docx(docx_file):
    text = ""
    try:
        doc = docx.Document(docx_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception:
        return ""
    return text


def extract_text_from_txt(txt_file):
    try:
        return txt_file.getvalue().decode("utf-8")
    except Exception:
        return ""


def extract_resume_text(uploaded_file):
    if uploaded_file.type == "application/pdf":
        return extract_text_from_pdf(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(uploaded_file)
    elif uploaded_file.type == "text/plain":
        return extract_text_from_txt(uploaded_file)
    return ""


def extract_candidate_name(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        return "Candidate"

    ignore_words = {
        "resume", "curriculum vitae", "cv", "profile", "summary",
        "education", "skills", "experience", "projects", "contact"
    }

    for line in lines[:8]:
        low = line.lower()

        if any(word in low for word in ignore_words):
            continue

        if "@" in line:
            continue
        if len(line) > 40:
            continue
        if sum(ch.isdigit() for ch in line) > 2:
            continue

        words = line.split()

        if 2 <= len(words) <= 4:
            clean_words = []
            valid = True

            for word in words:
                clean = re.sub(r"[^A-Za-z]", "", word)
                if not clean:
                    valid = False
                    break
                clean_words.append(clean.capitalize())

            if valid:
                return " ".join(clean_words)

    return "Candidate"


def parse_skills_from_text(text):
    skill_map = {
        "python": ["python"],
        "java": ["java"],
        "javascript": ["javascript", "js"],
        "react": ["react", "reactjs", "react.js"],
        "node.js": ["node.js", "nodejs", "node js"],
        "sql": ["sql", "structured query language"],
        "mongodb": ["mongodb", "mongo"],
        "mysql": ["mysql"],
        "aws": ["aws", "amazon web services"],
        "docker": ["docker"],
        "kubernetes": ["kubernetes", "k8s"],
        "machine learning": ["machine learning", "ml"],
        "deep learning": ["deep learning", "dl"],
        "nlp": ["nlp", "natural language processing"],
        "tensorflow": ["tensorflow", "tensor flow"],
        "pandas": ["pandas"],
        "streamlit": ["streamlit"],
        "git": ["git", "github", "gitlab"],
        "linux": ["linux"],
        "communication": ["communication", "communication skills"],
        "leadership": ["leadership", "team lead", "leading"],
        "rest api": ["rest api", "restful api", "api development", "apis"],
        "spring boot": ["spring boot", "springboot"]
    }

    text_lower = text.lower()
    found_skills = []

    for skill, variants in skill_map.items():
        if any(variant in text_lower for variant in variants):
            found_skills.append(skill)

    return found_skills


def estimate_experience_years(text):
    text_lower = text.lower()
    matches = re.findall(r'(\d+)\+?\s*(?:years|yrs|year)', text_lower)
    if matches:
        return max(int(x) for x in matches)

    if "intern" in text_lower:
        return 1
    if "project" in text_lower:
        return 1
    return 0


def extract_education(text):
    text_lower = text.lower()
    education_keywords = [
        "b.tech", "btech", "b.e", "be", "m.tech", "mtech",
        "b.sc", "bsc", "m.sc", "msc", "bca", "mca",
        "degree", "college", "university"
    ]

    found = [item for item in education_keywords if item in text_lower]
    if found:
        return "Education details found in resume"
    return "Not clearly identified"


def build_candidate_profile(resume_text):
    skills = parse_skills_from_text(resume_text)
    experience_years = estimate_experience_years(resume_text)
    education = extract_education(resume_text)
    candidate_name = extract_candidate_name(resume_text)

    return {
        "name": candidate_name,
        "skills": [skill.title() for skill in skills],
        "experience_years": experience_years,
        "education": education,
        "summary": resume_text[:2000]
    }