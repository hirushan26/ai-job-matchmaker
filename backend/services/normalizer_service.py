import re

# Canonical skill mappings for common typos and aliases
CANONICAL_SKILL_MAP = {
    "pythn": "Python",
    "python3": "Python",
    "js": "JavaScript",
    "javascrip": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "reactjs": "React",
    "react.js": "React",
    "react native": "React Native",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "postgre": "PostgreSQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Microsoft Azure",
    "docker": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "ci/cd": "CI/CD",
    "html": "HTML",
    "html5": "HTML5",
    "css": "CSS",
    "css3": "CSS3",
    "c++": "C++",
    "c#": "C#",
    "golang": "Go",
    "graphql": "GraphQL",
    "rest": "REST APIs",
    "restful": "REST APIs",
    "git": "Git",
    "github": "GitHub",
    "jira": "Jira",
    "agile": "Agile / Scrum",
    "scrum": "Agile / Scrum"
}

def normalize_degree(degree_raw: str) -> str:
    """
    Standardizes degree abbreviations, fixes common typos, and capitalizes field of study.
    Example: 'BS.c in Computer science' -> 'B.Sc. in Computer Science'
             'bsc (hons) computer science' -> 'B.Sc. (Hons) in Computer Science'
             'Bachelor of Science (Computer Science)' -> 'B.Sc. in Computer Science'
    """
    if not degree_raw or not isinstance(degree_raw, str):
        return degree_raw or ""
    
    text = degree_raw.strip()
    
    # Standardize B.Sc. variations
    text = re.sub(r'(?i)\bbachelor\s+of\s+science\b', 'B.Sc.', text)
    text = re.sub(r'(?i)\bb\.?s\.?c\b\.?', 'B.Sc.', text)
    text = re.sub(r'(?i)\bbsc\b\.?', 'B.Sc.', text)
    text = re.sub(r'(?i)\bb\.?s\b(?!\s+(?:in\s+)?(?:engineering|developer))', 'B.Sc.', text)
    
    # Standardize B.Tech / B.Eng / M.Sc
    text = re.sub(r'(?i)\bbachelor\s+of\s+technology\b', 'B.Tech.', text)
    text = re.sub(r'(?i)\bb\.?tech\b\.?', 'B.Tech.', text)
    text = re.sub(r'(?i)\bbachelor\s+of\s+engineering\b', 'B.Eng.', text)
    text = re.sub(r'(?i)\bb\.?eng\b\.?', 'B.Eng.', text)
    text = re.sub(r'(?i)\bb\.?e\b\.?', 'B.E.', text)
    text = re.sub(r'(?i)\bmaster\s+of\s+science\b', 'M.Sc.', text)
    text = re.sub(r'(?i)\bm\.?s\.?c\b\.?', 'M.Sc.', text)
    text = re.sub(r'(?i)\bmsc\b\.?', 'M.Sc.', text)
    text = re.sub(r'(?i)\bmaster\s+of\s+engineering\b', 'M.Eng.', text)
    text = re.sub(r'(?i)\bm\.?tech\b\.?', 'M.Tech.', text)
    text = re.sub(r'(?i)\bmtech\b\.?', 'M.Tech.', text)
    text = re.sub(r'(?i)\bm\.?b\.?a\b\.?', 'M.B.A.', text)
    
    # Fix double dots
    text = re.sub(r'\.{2,}', '.', text)
    
    # Honours
    text = re.sub(r'(?i)\(?\bhons\.?\b\)?', '(Hons)', text)
    
    # Parentheses around field of study: e.g. (Computer Science) -> in Computer Science
    text = re.sub(r'\(\s*(?!Hons\b)(?:in\s+)?([A-Za-z\s]+)\s*\)', r'in \1', text)
    
    # Capitalize proper words
    lowercase_words = {'in', 'of', 'and', 'with', 'for', 'at', 'on'}
    tokens = [t for t in text.split(' ') if t]
    formatted = []
    for i, tok in enumerate(tokens):
        if '.' in tok or tok in {'(Hons)', 'IT', 'AI', 'ML', 'CS', 'SE', 'B.Sc.', 'B.Tech.', 'B.Eng.', 'M.Sc.', 'M.Eng.', 'M.Tech.', 'M.B.A.'}:
            formatted.append(tok)
        elif tok.lower() in lowercase_words and i != 0:
            formatted.append(tok.lower())
        else:
            parts = tok.split('-')
            formatted.append('-'.join(p.capitalize() for p in parts))
    result = ' '.join(formatted).strip()
    
    # Ensure 'in' is inserted if missing (e.g. B.Sc. Computer Science -> B.Sc. in Computer Science)
    result = re.sub(r'(B\.Sc\.|B\.Tech\.|B\.Eng\.|M\.Sc\.|M\.Tech\.)\s+in\s+\(Hons\)', r'\1 (Hons)', result)
    result = re.sub(r'^(B\.Sc\.|B\.Tech\.|B\.Eng\.|M\.Sc\.|M\.Tech\.)\s+(?!in\b|\(Hons\))', r'\1 in ', result)
    result = re.sub(r'\(Hons\)\s+(?!in\b)', '(Hons) in ', result)
    result = re.sub(r'\s+in\s+in\b', ' in', result)
    result = re.sub(r'\s+', ' ', result).strip()
    return result

def normalize_skill(skill_raw: str) -> str:
    """
    Normalizes a single skill name to its canonical industry standard.
    Example: 'pythn' -> 'Python', 'reactjs' -> 'React'
    """
    if not skill_raw or not isinstance(skill_raw, str):
        return skill_raw or ""
    
    clean = skill_raw.strip()
    key = clean.lower()
    
    if key in CANONICAL_SKILL_MAP:
        return CANONICAL_SKILL_MAP[key]
    
    # Otherwise return cleanly capitalized skill
    if len(clean) <= 4 and clean.isupper():
        return clean  # e.g. AWS, SQL, GCP, CSS, HTML
    
    # Capitalize standard words (e.g., 'machine learning' -> 'Machine Learning')
    return " ".join(w.capitalize() for w in clean.split(" "))

def normalize_skills_list(skills: list) -> list:
    """Normalizes and deduplicates a list of extracted skills."""
    if not skills or not isinstance(skills, list):
        return []
    
    seen = set()
    normalized = []
    for s in skills:
        norm = normalize_skill(str(s))
        if norm and norm.lower() not in seen:
            seen.add(norm.lower())
            normalized.append(norm)
    return normalized
