import json
import os
import re
import base64
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .. import config
from . import normalizer_service

PRIMARY_GEMINI_MODEL = "gemini-3-flash-preview"
FALLBACK_GEMINI_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash"
]

class GeminiServiceError(Exception):
    """Custom exception for Gemini AI service errors with safe, user-friendly messages."""
    pass

def sanitize_api_error(text: str) -> str:
    """
    Strips Google Gemini API keys, query parameter tokens, and credential strings
    from error messages, URLs, and exceptions to prevent credential leakage.
    """
    if not text:
        return ""
    s = str(text)
    for k in getattr(config, "GEMINI_API_KEYS", []) or []:
        if k and len(k) > 5:
            s = s.replace(k, "[REDACTED_API_KEY]")
    single_key = getattr(config, "GEMINI_API_KEY", "")
    if single_key and len(single_key) > 5:
        s = s.replace(single_key, "[REDACTED_API_KEY]")
    # Redact any Google API key pattern (AIzaSy...)
    s = re.sub(r'AIza[0-9A-Za-z\-_]{20,}', '[REDACTED_API_KEY]', s)
    # Redact any key=... query parameters
    s = re.sub(r'([?&]key=)[^&\s]+', r'\1[REDACTED_API_KEY]', s)
    # Redact x-goog-api-key headers
    s = re.sub(r'(x-goog-api-key[\'"]?\s*[:=]\s*[\'"]?)[^\s,\'"}\]]+', r'\1[REDACTED_API_KEY]', s, flags=re.IGNORECASE)
    return s

def get_friendly_error_message(status_code: int = None, raw_error: str = "") -> str:
    """
    Translates raw API errors into concise, user-friendly messages
    without revealing internal endpoints, tokens, or stack traces.
    """
    err_str = (raw_error or "").lower()
    
    if status_code == 429 or "quota" in err_str or "rate limit" in err_str or "resource_exhausted" in err_str:
        return "AI analysis service is temporarily busy due to rate limits or quota. Please try again shortly."
    
    if status_code in [401, 403] or "api key" in err_str or "permission_denied" in err_str or "unauthenticated" in err_str:
        return "AI service authentication error. Please verify the API key configuration."
        
    if status_code == 400 or "invalid_argument" in err_str:
        if "api key" in err_str:
            return "AI service authentication error. Please verify the API key configuration."
        return "The uploaded document could not be processed by the AI service. Please verify the file format."
        
    if status_code in [500, 502, 503, 504] or "overloaded" in err_str or "unavailable" in err_str:
        return "AI analysis service is temporarily overloaded. Please try again in a few moments."
        
    if "timeout" in err_str or "timed out" in err_str:
        return "AI analysis service timed out while processing your CV. Please try again."
        
    if "connection" in err_str or "network" in err_str or "max retries" in err_str:
        return "Unable to connect to AI analysis service. Please check your network connection."
        
    return "AI resume analysis is temporarily unavailable. Please try again shortly."

def get_resilient_session():
    """Returns a requests Session with automatic retries on transient connection or server errors."""
    session = requests.Session()
    retry_strategy = Retry(
        total=2,
        backoff_factor=1.0,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def analyze_resume_with_gemini(raw_text: str, job_roles: list, file_path: str = None) -> dict:
    """
    Sends candidate resume (with visual Multimodal PDF inspection if available, or raw text)
    and target job roles to Google Gemini in a SINGLE unified API prompt.
    Returns structured JSON with summary, profile details, skills, and multi-role gap analysis.
    """
    if not config.GEMINI_API_KEY:
        raise GeminiServiceError("Gemini AI API key is not configured. Please set GEMINI_API_KEY in your .env file.")

    roles_context = "\n".join([
        f"- Role Code: '{r['jobrole_code']}', Title: '{r['jobrole_name']}', Description: '{r.get('description', '')}'"
        for r in job_roles
    ])

    system_instruction = (
        "You are an expert AI Job Matchmaker and Career Analyst. "
        "Analyze the provided candidate resume against all specified target job roles. "
        "Evaluate the candidate against EVERY role provided in the list.\n\n"
        "1. CAREER LEVEL DETECTION & ADAPTIVE SCORING RUBRIC:\n"
        "Detect whether the candidate is an 'intern_fresher' (intern seeker, student, undergraduate, or 0-1 years of experience) "
        "or an 'experienced' professional (1+ years of industry/production experience).\n"
        "Apply the appropriate scoring rubric based on career stage:\n"
        "A. For 'intern_fresher' candidates (Internships & Entry-Level):\n"
        "   Do NOT penalize for lack of corporate/industry tenure. Instead, evaluate their practical projects, coursework, and coding ability:\n"
        "   - Core Technical Skills & Coursework (60% weight): Relevant languages, frameworks, fundamentals. (core_skills: 0-60)\n"
        "   - Practical Projects, Portfolio & Hackathons (20% weight): Hands-on software projects, GitHub repos, coursework projects, hackathons. (experience_or_projects: 0-20)\n"
        "   - Academic Degree Foundation (15% weight): Degree relevance, university coursework, academic standing. (education: 0-15)\n"
        "   - Tools & Engineering Practices (5% weight): Git, collaboration, basic testing, problem solving. (tools_practices: 0-5)\n\n"
        "B. For 'experienced' candidates (Mid / Senior / Industry Professionals):\n"
        "   - Core Technical Skills (50% weight): Direct overlap of production technologies. (core_skills: 0-50)\n"
        "   - Industry Experience Relevance & Seniority (25% weight): Years of production experience, scale, architecture. (experience_or_projects: 0-25)\n"
        "   - Academic & Domain Foundation (15% weight): Degree and theoretical domain background. (education: 0-15)\n"
        "   - Engineering Practices & Tools (10% weight): CI/CD, Agile, testing, cloud infrastructure. (tools_practices: 0-10)\n\n"
        "2. TYPO CORRECTION & STANDARDIZATION:\n"
        "- Automatically correct common typos, casing, and abbreviations in degrees (e.g., 'BS.c in Computer science' -> 'B.Sc. in Computer Science', 'bsc' -> 'B.Sc.', 'B.tech' -> 'B.Tech.', 'msc' -> 'M.Sc.').\n"
        "- Capitalize proper nouns in education and field of study.\n"
        "- Standardize all extracted technical skills into canonical industry names (e.g. 'pythn' -> 'Python', 'reactjs' -> 'React').\n\n"
        "3. OUTPUT REQUIREMENTS:\n"
        "For each role, provide:\n"
        "- match_percentage (integer 0-100)\n"
        "- score_breakdown: object with integer scores for core_skills, experience_or_projects, experience (alias), education, tools_practices, and max_weights\n"
        "- score_explanation: 1-2 sentence concise plain-language rationale explaining why this score was given, explicitly noting the candidate's career level (e.g. highlighting projects for interns or tenure for experienced candidates).\n"
        "- compatibility_summary: 1 sentence high-level summary of fit.\n"
        "- matched_skills: array of candidate's skills matching this role.\n"
        "- missing_skills: array of objects with 'name' and 'priority' ('high', 'medium', or 'low') representing skill gaps.\n\n"
        "Also extract candidate_level ('intern_fresher' or 'experienced'), candidate_level_label ('Intern / Fresher Applicant' or 'Experienced Professional'), "
        "personal details, profile score (0-100), concise professional summary (2-3 sentences), "
        "total years of experience (float), brief experience text, education details, and all canonical skills as a clean array.\n"
        "Return strictly valid JSON with no markdown formatting or backticks."
    )

    parts = []
    has_pdf_inline = False

    # Check if plain text was already cleanly extracted
    has_clean_text = bool(raw_text and len(raw_text.strip()) >= 50)

    # If text is missing or extremely short (e.g. scanned image PDF), attach inline PDF data
    if not has_clean_text and file_path and os.path.exists(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        if ext == ".pdf" and file_size < 15 * 1024 * 1024:
            try:
                with open(file_path, "rb") as f:
                    pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
                parts.append({
                    "inlineData": {
                        "mimeType": "application/pdf",
                        "data": pdf_b64
                    }
                })
                has_pdf_inline = True
            except Exception as e:
                print(f"Warning: Could not base64 encode PDF for multimodal vision: {e}")

    if has_pdf_inline:
        doc_intro = (
            "Candidate Resume Document: The visual PDF document is attached above as visual data.\n"
            "Please visually inspect BOTH the text content AND any graphical images, certification badges (e.g. AWS, Cisco, GCP, PMP), "
            "visual skill charts, or text embedded within graphics/banners."
        )
    else:
        doc_intro = f"Candidate Resume Text:\n\"\"\"\n{raw_text[:12000] if raw_text else 'No selectable text available.'}\n\"\"\""

    prompt = f"""
{doc_intro}

Target Job Roles to Evaluate:
{roles_context}

Expected JSON Schema:
{{
  "candidate_level": "intern_fresher",
  "candidate_level_label": "Intern / Fresher Applicant",
  "rubric_applied": "intern_fresher",
  "summary": "Concise 2-3 sentence resume summary",
  "profile_score": 85,
  "personal_info": {{
    "name": "Full Name",
    "role": "Current Job Title / Role",
    "location": "City, Country",
    "email": "Email Address",
    "phone": "Phone Number",
    "linkedin": "LinkedIn URL or handle",
    "github": "GitHub URL or handle",
    "portfolio": "Website / Portfolio URL"
  }},
  "experience": {{
    "years": 0.5,
    "summary": "Brief 1-2 sentence description of experience or project depth"
  }},
  "education": {{
    "degree": "B.Sc. in Computer Science",
    "institute": "University / College Name",
    "duration": "e.g. 2023 - Present",
    "graduation_year": "e.g. Expected Graduation: 2027"
  }},
  "skills": ["Python", "JavaScript", "SQL", "React", "Git"],
  "all_job_analyses": [
    {{
      "jobrole_code": "se",
      "job_title": "Software Engineer",
      "match_percentage": 85,
      "score_breakdown": {{
        "core_skills": 50,
        "experience_or_projects": 18,
        "experience": 18,
        "education": 14,
        "tools_practices": 4,
        "max_weights": {{
          "core_skills": 60,
          "experience_or_projects": 20,
          "education": 15,
          "tools_practices": 5
        }}
      }},
      "score_explanation": "Score 85%: Matched core programming skills...",
      "compatibility_summary": "High compatibility with full-stack development...",
      "role_description": "Role overview...",
      "matched_skills": ["Java", "Python", "SQL", "Node.js", "JavaScript"],
      "missing_skills": [
        {{ "name": "Docker / Kubernetes", "priority": "high" }},
        {{ "name": "AWS / Cloud Services", "priority": "high" }},
        {{ "name": "CI/CD Pipelines", "priority": "medium" }}
      ]
    }}
  ]
}}
"""

    parts.append({"text": f"{system_instruction}\n\n{prompt}"})

    payload = {
        "contents": [
            {
                "parts": parts
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        }
    }

    session = get_resilient_session()
    api_keys = getattr(config, "GEMINI_API_KEYS", []) or [config.GEMINI_API_KEY]
    models_to_try = [PRIMARY_GEMINI_MODEL] + [m for m in FALLBACK_GEMINI_MODELS if m != PRIMARY_GEMINI_MODEL]

    last_raw_error = None
    last_status_code = None
    response = None
    success = False

    for current_key in api_keys:
        if not current_key:
            continue
        for model_name in models_to_try:
            # Send API key via header instead of in URL query string to prevent credential exposure
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            req_headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": current_key
            }
            try:
                print(f"[GeminiService] Requesting analysis via model: {model_name}...")
                resp = session.post(
                    url,
                    json=payload,
                    headers=req_headers,
                    timeout=(6, 25)
                )

                if resp.status_code == 200:
                    print(f"[GeminiService] Analysis succeeded with model: {model_name}")
                    response = resp
                    success = True
                    break

                last_status_code = resp.status_code
                error_msg = resp.text
                try:
                    err_obj = resp.json()
                    error_msg = err_obj.get("error", {}).get("message", resp.text)
                except Exception:
                    pass

                clean_error_msg = sanitize_api_error(error_msg)
                print(f"[GeminiService] Model {model_name} returned HTTP {resp.status_code}: {clean_error_msg}")
                last_raw_error = f"Model {model_name} HTTP {resp.status_code}: {clean_error_msg}"

                if resp.status_code in [404, 429, 500, 502, 503, 504]:
                    continue
                else:
                    continue

            except requests.exceptions.Timeout:
                print(f"[GeminiService] Model {model_name} timed out after 25s. Attempting fallback...")
                last_raw_error = f"Model {model_name} timed out."
                continue
            except requests.exceptions.RequestException as ce:
                clean_ce = sanitize_api_error(str(ce))
                print(f"[GeminiService] Model {model_name} request error: {clean_ce}")
                last_raw_error = f"Request error on {model_name}: {clean_ce}"
                continue
            except Exception as ex:
                clean_ex = sanitize_api_error(str(ex))
                print(f"[GeminiService] Model {model_name} unexpected error: {clean_ex}")
                last_raw_error = f"Unexpected error on {model_name}: {clean_ex}"
                continue

        if success:
            break

    if not success or not response or response.status_code != 200:
        friendly_msg = get_friendly_error_message(last_status_code, last_raw_error)
        print(f"[GeminiService] All Gemini models/keys exhausted ({sanitize_api_error(last_raw_error)}).")
        raise GeminiServiceError(friendly_msg)

    try:
        result = response.json()
        candidates = result.get("candidates", [])
        if not candidates:
            print("[GeminiService] Gemini API returned no candidates.")
            raise GeminiServiceError("AI service was unable to evaluate this resume. Please check your document and try again.")

        content_parts = candidates[0].get("content", {}).get("parts", [])
        text_content = ""
        for p in content_parts:
            if not p.get("thought", False) and "text" in p:
                text_content += p["text"]

        if not text_content and content_parts:
            text_content = content_parts[0].get("text", "")

        # Clean possible markdown artifacts
        text_content = re.sub(r"^```json\s*", "", text_content.strip())
        text_content = re.sub(r"```$", "", text_content.strip())

        parsed_data = json.loads(text_content)
    except json.JSONDecodeError as jde:
        print(f"[GeminiService] Failed to extract JSON from Gemini response: {jde}")
        raise GeminiServiceError("AI service returned an invalid response format. Please try again.")
    except GeminiServiceError:
        raise
    except Exception as e:
        clean_err = sanitize_api_error(str(e))
        print(f"[GeminiService] Error processing Gemini response: {clean_err}")
        raise GeminiServiceError("Failed to parse AI evaluation response. Please try again.")

    # Apply deterministic degree typo and title-casing normalization
    if "education" in parsed_data and isinstance(parsed_data["education"], dict):
        raw_deg = parsed_data["education"].get("degree", "")
        parsed_data["education"]["degree"] = normalizer_service.normalize_degree(raw_deg)
        inst = (parsed_data["education"].get("institute") or parsed_data["education"].get("institution") or "").strip()
        parsed_data["education"]["institute"] = inst
        parsed_data["education"]["institution"] = inst

    # Apply canonical skill normalization
    if "skills" in parsed_data and isinstance(parsed_data["skills"], list):
        parsed_data["skills"] = normalizer_service.normalize_skills_list(parsed_data["skills"])

    # Normalize candidate level labels
    cand_level = parsed_data.get("candidate_level", "experienced")
    if cand_level not in ["intern_fresher", "experienced"]:
        exp_yrs = float(parsed_data.get("experience", {}).get("years", 0.0))
        cand_level = "intern_fresher" if exp_yrs <= 1.0 else "experienced"
    
    parsed_data["candidate_level"] = cand_level
    parsed_data["candidate_level_label"] = "Intern / Fresher Applicant" if cand_level == "intern_fresher" else "Experienced Professional"

    # Normalize skills in all job analyses
    for job in parsed_data.get("all_job_analyses", []):
        if "matched_skills" in job and isinstance(job["matched_skills"], list):
            job["matched_skills"] = normalizer_service.normalize_skills_list(job["matched_skills"])
        sb = job.get("score_breakdown", {})
        if "experience_or_projects" in sb and "experience" not in sb:
            sb["experience"] = sb["experience_or_projects"]
        elif "experience" in sb and "experience_or_projects" not in sb:
            sb["experience_or_projects"] = sb["experience"]

    # Ensure candidate_name and personal_info are synchronized
    if "personal_info" in parsed_data and isinstance(parsed_data["personal_info"], dict):
        p_name = parsed_data["personal_info"].get("name")
        if p_name and not parsed_data.get("candidate_name"):
            parsed_data["candidate_name"] = p_name
    elif parsed_data.get("candidate_name"):
        if not isinstance(parsed_data.get("personal_info"), dict):
            parsed_data["personal_info"] = {}
        parsed_data["personal_info"]["name"] = parsed_data["candidate_name"]

    return parsed_data


