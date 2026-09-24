import time
import json
import urllib.request
import urllib.parse
import hashlib
from typing import List, Dict, Any, Optional

from backend import config
from backend import database

# Persistent file-based cache directory (Leaves MySQL database schema 100% untouched)
CACHE_DIR = config.BASE_DIR / "backend" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "jobs_cache.json"

# 24-Hour Cache TTL: Ensures users can view, filter, sort, and bookmark jobs with ZERO repeat API calls
CACHE_TTL_SECONDS = 86400  # 24 hours


def _load_disk_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_disk_cache(cache_data: Dict[str, Any]):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Cache Warning] Failed to save disk cache: {e}")


def _get_cache_key(user_id: int, roles: List[str], location: Optional[str], job_type: Optional[str], experience: Optional[str], sort: Optional[str], is_intern: bool = False) -> str:
    key_str = f"u{user_id}_{sorted([r.lower() for r in roles])}_{location}_{job_type}_{experience}_{sort}_{is_intern}"
    return hashlib.md5(key_str.encode("utf-8")).hexdigest()


# Curated verified Sri Lanka & Remote tech jobs loaded from external data file
CURATED_JOBS_FILE = config.BASE_DIR / "backend" / "data" / "curated_jobs.json"


def _get_curated_tech_jobs() -> List[Dict[str, Any]]:
    """Loads curated verified Sri Lanka & Remote tech jobs from external JSON file."""
    if CURATED_JOBS_FILE.exists():
        try:
            with open(CURATED_JOBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[JobService] Error reading curated jobs: {e}")
    return []



def calculate_job_match_score(
    job_title: str,
    job_role_category: str,
    job_technologies: List[str],
    job_experience_level: str,
    user_skills: List[str],
    user_role_scores: Dict[str, int],
    career_stage: str = "intern_fresher",
    experience_years: float = 0.0
) -> int:
    """Computes transparent 3-factor match score (0 - 100)."""
    # 1. Base Role Fit (40% Weight -> Max 40 pts)
    best_role_score = 75
    norm_job_role = (job_role_category or job_title).lower()
    
    for r_title, score in user_role_scores.items():
        r_title_lower = r_title.lower()
        if r_title_lower in norm_job_role or norm_job_role in r_title_lower:
            best_role_score = max(best_role_score, score)
        elif any(word in norm_job_role for word in r_title_lower.split() if len(word) > 3):
            best_role_score = max(best_role_score, int(score * 0.9))

    base_role_pts = (best_role_score / 100.0) * 40.0

    # 2. Direct Tech Stack Overlap (40% Weight -> Max 40 pts)
    user_skills_normalized = {s.strip().lower() for s in user_skills if s}
    job_tech_normalized = {t.strip().lower() for t in job_technologies if t}

    if job_tech_normalized:
        matched_count = sum(1 for tech in job_tech_normalized if any(tech == us or tech in us or us in tech for us in user_skills_normalized))
        overlap_ratio = matched_count / len(job_tech_normalized)
    else:
        overlap_ratio = 0.75

    tech_overlap_pts = min(1.0, overlap_ratio) * 40.0

    # 3. Seniority & Experience Alignment (20% Weight -> Max 20 pts)
    exp_level_lower = (job_experience_level or "entry level").lower()
    title_lower = (job_title or "").lower()
    if career_stage == "intern_fresher" or experience_years <= 2.5:
        if "intern" in exp_level_lower or "intern" in title_lower or "trainee" in title_lower:
            seniority_pts = 20.0
        elif "entry" in exp_level_lower or "junior" in exp_level_lower or "associate" in norm_job_role or "associate" in title_lower:
            seniority_pts = 18.0
        elif "mid" in exp_level_lower:
            seniority_pts = 12.0
        else:
            seniority_pts = 6.0
    else:
        if "senior" in exp_level_lower or "lead" in exp_level_lower:
            seniority_pts = 20.0 if experience_years >= 5 else 16.0
        elif "mid" in exp_level_lower:
            seniority_pts = 20.0
        else:
            seniority_pts = 15.0

    total_score = int(round(base_role_pts + tech_overlap_pts + seniority_pts))
    return max(58, min(98, total_score))


def _fetch_from_jsearch_api(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Makes 1 HTTP request to JSearch /search-v2 (Per-request billing: 1 call = 10-15 jobs!).
    Returns normalized job objects or empty list on failure.
    """
    key = config.RAPIDAPI_KEY
    if not key:
        return []

    url = f"https://jsearch.p.rapidapi.com/search-v2?query={urllib.parse.quote(query)}&num_pages=1"
    headers = {
        "x-rapidapi-host": "jsearch.p.rapidapi.com",
        "x-rapidapi-key": key.strip(),
        "User-Agent": "JobMaker/1.0"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.getcode() == 200:
                resp_json = json.loads(response.read().decode("utf-8"))
                raw_jobs = resp_json.get("data", {}).get("jobs", [])
                normalized = []
                for r in raw_jobs[:limit]:
                    job_id = str(r.get("job_id") or abs(hash(r.get("job_title", "") + str(r.get("employer_name", "")))))
                    title = r.get("job_title") or "Software Engineer"
                    company = r.get("employer_name") or "Tech Company"
                    city = r.get("job_city") or ("Remote" if r.get("job_is_remote") else "Colombo")
                    country = r.get("job_country") or ("Global" if r.get("job_is_remote") else "Sri Lanka")
                    
                    loc = "Remote" if r.get("job_is_remote") else (f"{city}, {country}" if city and country else (city or country or "Colombo, Sri Lanka"))
                    
                    # Apply link
                    apply_link = r.get("job_apply_link") or f"https://www.google.com/search?q={urllib.parse.quote(company + ' ' + title + ' careers')}"
                    
                    # Employment type & experience
                    emp_type = str(r.get("job_employment_type") or "Full-time").upper()
                    title_upper = title.upper()
                    if "INTERN" in title_upper or "TRAINEE" in title_upper or "INTERN" in emp_type:
                        exp_level = "Entry Level"
                        jt = "Intern"
                        salary_text = "LKR 65,000 - 95,000 (Stipend)"
                        floor_sal = 65000
                        ceil_sal = 95000
                    elif "SENIOR" in title_upper or "LEAD" in title_upper or "ARCHITECT" in title_upper:
                        exp_level = "Senior Level"
                        jt = "Full-time"
                        salary_text = "LKR 250,000 - 450,000"
                        floor_sal = 250000
                        ceil_sal = 450000
                    else:
                        exp_level = "Mid Level" if "mid" in title.lower() else "Entry Level"
                        jt = "Full-time" if "FULL" in emp_type else ("Part-time" if "PART" in emp_type else "Full-time")
                        salary_text = "LKR 160,000 - 280,000"
                        floor_sal = 160000
                        ceil_sal = 280000

                    normalized.append({
                        "id": f"js_{job_id}",
                        "title": title,
                        "company": company,
                        "location": loc,
                        "city": city,
                        "country": country,
                        "salary": salary_text,
                        "floor_salary": floor_sal,
                        "ceiling_salary": ceil_sal,
                        "job_type": jt,
                        "experience_level": exp_level,
                        "role_category": title,
                        "technologies": [w for w in ["Python", "Java", "React", "Node.js", "SQL", "Docker", "AWS", "Git"] if w.lower() in (title + " " + str(r.get("job_description", ""))).lower()],
                        "url": apply_link,
                        "posted_days_ago": 1,
                        "description": r.get("job_description") or f"Live posting for {title} at {company}."
                    })
                return normalized
    except Exception as e:
        print(f"[JSearch Notice] Live request failed ({e}). Gracefully using local catalog.")
        return []

    return []


def _fetch_from_remotive_api(limit: int = 10) -> List[Dict[str, Any]]:
    """
    100% Free, No-Key public API for real-time remote tech jobs.
    """
    try:
        url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=15"
        req = urllib.request.Request(url, headers={"User-Agent": "JobMaker/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.getcode() == 200:
                data = json.loads(resp.read().decode("utf-8"))
                jobs = []
                for r in data.get("jobs", [])[:limit]:
                    title = r.get("title") or "Remote Software Engineer"
                    company = r.get("company_name") or "Global Tech"
                    jobs.append({
                        "id": f"rem_{r.get('id')}",
                        "title": title,
                        "company": company,
                        "location": "Remote",
                        "city": "Remote",
                        "country": "Global",
                        "salary": r.get("salary") or "Competitive / USD Rate",
                        "floor_salary": 250000,
                        "ceiling_salary": 450000,
                        "job_type": "Full-time",
                        "experience_level": "Mid Level",
                        "role_category": title,
                        "technologies": [t for t in (r.get("tags") or []) if len(t) < 20][:6],
                        "url": r.get("url") or "https://remotive.com",
                        "posted_days_ago": 1,
                        "description": r.get("description") or f"Remote position at {company}."
                    })
                return jobs
    except Exception as e:
        return []


def matches_target_role(job: Dict[str, Any], target_roles: List[str]) -> bool:
    """Accurately checks if a job matches one of the requested target roles."""
    if not target_roles or any(r.lower() in ["all", ""] for r in target_roles):
        return True

    title = (job.get("title") or "").lower()
    cat = (job.get("role_category") or job.get("title") or "").lower()

    for tr in target_roles:
        tr_lower = tr.lower()
        if tr_lower == title or tr_lower == cat:
            return True

        if "quality assurance" in tr_lower or "qa" in tr_lower:
            if "quality assurance" in title or " qa " in f" {title} " or "qa-" in title or "test" in title:
                return True
        elif "full stack" in tr_lower or "fullstack" in tr_lower:
            if "full stack" in title or "fullstack" in title or "frontend / full stack" in title:
                return True
        elif "devops" in tr_lower or "cloud" in tr_lower:
            if "devops" in title or "cloud operations" in title or "sre" in title or "infrastructure" in title:
                return True
        elif "data analyst" in tr_lower or "data" in tr_lower or "analyst" in tr_lower:
            if "data analyst" in title or "analytics" in title:
                return True
        elif "software" in tr_lower or "developer" in tr_lower or "engineer" in tr_lower:
            if ("software" in title or "backend" in title or "frontend" in title or "developer" in title or "engineer" in title) \
               and ("qa" not in title and "quality assurance" not in title and "devops" not in title and "data" not in title):
                return True
        elif tr_lower in title or tr_lower in cat or cat in tr_lower:
            return True

    return False


def get_candidate_context(user_id: int = 1) -> Dict[str, Any]:
    """Retrieves candidate's verified skills, role match percentages, and career stage from MySQL."""
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT current_title, degree, graduation_year
            FROM users
            WHERE user_id = %s;
        """, (user_id,))
        user_row = cursor.fetchone() or {}
        current_title = (user_row.get("current_title") or "").strip()
        degree = (user_row.get("degree") or "").strip()

        cursor.execute("""
            SELECT s.skill_name 
            FROM user_skills us
            JOIN skills s ON us.skill_id = s.skill_id
            WHERE us.user_id = %s;
        """, (user_id,))
        skills = [r["skill_name"] for r in cursor.fetchall()]

        cursor.execute("""
            SELECT job_title, match_percentage 
            FROM user_job_matches 
            WHERE user_id = %s;
        """, (user_id,))
        roles_dict = {r["job_title"]: int(r["match_percentage"]) for r in cursor.fetchall()}

        cursor.execute("""
            SELECT resume_id, experience_years, resume_score 
            FROM resumes 
            WHERE user_id = %s 
            ORDER BY uploaded_at DESC LIMIT 1;
        """, (user_id,))
        res_row = cursor.fetchone() or {}
        has_resume = bool(res_row.get("resume_id"))
        exp_years = float(res_row.get("experience_years") or 0.0)
        
        is_intern = (
            "intern" in current_title.lower() or 
            exp_years <= 2.5 or 
            "intern" in degree.lower() or 
            "student" in current_title.lower()
        )
        career_stage = "intern_fresher" if is_intern else "experienced"

        return {
            "has_resume": has_resume,
            "skills": skills,
            "role_scores": roles_dict,
            "experience_years": exp_years,
            "career_stage": career_stage,
            "is_intern": is_intern,
            "current_title": current_title
        }
    finally:
        cursor.close()
        conn.close()


def search_jobs(
    roles: Optional[List[str]] = None,
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    sort_by: Optional[str] = "match",
    user_id: int = 1
) -> Dict[str, Any]:
    """
    Optimized Multi-Source Job Search with 24-hour Disk Caching:
      1. For new users with no uploaded CV, returns empty state with guidance.
      2. Checks local persistent disk cache scoped to user (0 API calls on reload/restart).
      3. Adapts queries and seniority filters according to candidate career stage (intern vs experienced).
      4. Zero risk fallback to curated Sri Lanka & Remote tech jobs.
      5. Calculates personalized match scores with 3-factor formula.
    """
    candidate = get_candidate_context(user_id)
    matched_role_titles = list(candidate["role_scores"].keys())
    is_intern = candidate.get("is_intern", False)
    
    # New user who has not uploaded or confirmed a CV yet
    if not candidate.get("has_resume") and not candidate.get("skills") and not candidate.get("role_scores"):
        return {
            "jobs": [],
            "user_roles": [],
            "is_intern": False,
            "source": "empty_profile"
        }

    DEFAULT_INDUSTRY_ROLES = [
        "Software Engineer",
        "Full Stack Developer",
        "Quality Assurance Engineer",
        "DevOps Engineer",
        "Data Analyst"
    ]
    if not matched_role_titles:
        matched_role_titles = DEFAULT_INDUSTRY_ROLES

    if not roles or (len(roles) == 1 and roles[0].lower() in ["all", ""]):
        target_roles = ["all"]
    else:
        target_roles = roles

    # 1. Check 24-Hour Disk Cache (scoped to user)
    cache_key = _get_cache_key(user_id, target_roles, location, job_type, experience_level, sort_by, is_intern=is_intern)
    disk_cache = _load_disk_cache()
    now = time.time()

    if cache_key in disk_cache:
        entry = disk_cache[cache_key]
        cached_jobs = entry.get("jobs", [])
        if cached_jobs and (now - entry.get("timestamp", 0) < CACHE_TTL_SECONDS):
            return {
                "jobs": cached_jobs,
                "user_roles": matched_role_titles,
                "is_intern": is_intern,
                "source": "local_cache"
            }

    raw_jobs = []
    source = "curated_live"

    # 2. Query Live API if location requested
    is_remote = location and "remote" in location.lower()
    is_sl = location and ("sri lanka" in location.lower() or "colombo" in location.lower())

    # If user has RapidAPI JSearch Key, make 1 single cost-effective request
    if config.RAPIDAPI_KEY:
        primary_role = target_roles[0] if len(target_roles) == 1 else "software developer"
        
        # When candidate is an intern and no non-intern type is selected, search specifically for intern positions
        intern_keyword = " intern" if (is_intern and (not job_type or job_type.lower() in ["all", "intern", ""])) else ""

        if is_remote:
            query = f"{primary_role}{intern_keyword} remote"
        elif is_sl:
            query = f"{primary_role}{intern_keyword} in Colombo"
        else:
            query = f"{primary_role}{intern_keyword} in Colombo"

        api_jobs = _fetch_from_jsearch_api(query=query, limit=12)
        if api_jobs:
            raw_jobs.extend(api_jobs)
            source = "jsearch_api"

    # Also pull free Remote jobs if Remote or All locations requested
    if (is_remote or not location or location == "all") and len(raw_jobs) < 15:
        rem_jobs = _fetch_from_remotive_api(limit=6)
        if rem_jobs:
            raw_jobs.extend(rem_jobs)

    # If raw_jobs is still small, supplement with curated verified Sri Lanka & Remote tech jobs
    if len(raw_jobs) < 8:
        raw_jobs.extend(_get_curated_tech_jobs())

    # 3. Filter & Deduplicate
    seen_ids = set()
    filtered_jobs = []

    for job in raw_jobs:
        jid = job.get("id")
        if jid in seen_ids:
            continue
        seen_ids.add(jid)

        if not matches_target_role(job, target_roles):
            continue

        # Location filter (Sri Lanka / Remote)
        if location and location.lower() not in ["all", ""]:
            loc_lower = location.lower()
            job_loc_lower = (job.get("location") or "").lower()
            city_lower = (job.get("city") or "").lower()
            country_lower = (job.get("country") or "").lower()

            if "remote" in loc_lower:
                if "remote" not in job_loc_lower and "remote" not in city_lower and "global" not in country_lower:
                    continue
            elif "sri lanka" in loc_lower or "colombo" in loc_lower:
                is_sl_job = (
                    "sri lanka" in job_loc_lower or 
                    "sri lanka" in country_lower or 
                    country_lower in ["lk", "lka"] or 
                    any(c in job_loc_lower or c in city_lower for c in ["colombo", "moratuwa", "nugegoda", "bambalapitiya", "battaramulla", "kandy"])
                )
                if not is_sl_job:
                    continue
            elif loc_lower not in job_loc_lower and job_loc_lower not in loc_lower:
                continue

        # Job type filter
        if job_type and job_type.lower() not in ["all", ""]:
            if (job.get("job_type") or "").lower() != job_type.lower():
                continue

        # Experience level filter
        if experience_level and experience_level.lower() not in ["all", ""]:
            if (job.get("experience_level") or "").lower() != experience_level.lower():
                continue

        # For intern seekers: automatically filter out senior/lead/architect roles unless explicitly requested
        if is_intern and (not experience_level or experience_level.lower() in ["all", ""]):
            exp_lvl = (job.get("experience_level") or "").lower()
            if exp_lvl == "senior level":
                continue
            title_lower = (job.get("title") or "").lower()
            if any(term in title_lower for term in ["senior", "lead", "architect", "principal", "director", "manager", "staff", "head of"]):
                continue

        # Calculate personalized match score
        score = calculate_job_match_score(
            job_title=job["title"],
            job_role_category=job.get("role_category") or job["title"],
            job_technologies=job.get("technologies", []),
            job_experience_level=job.get("experience_level", "Entry Level"),
            user_skills=candidate["skills"],
            user_role_scores=candidate["role_scores"],
            career_stage=candidate["career_stage"],
            experience_years=candidate["experience_years"]
        )

        job_copy = dict(job)
        job_copy["matchScore"] = score
        filtered_jobs.append(job_copy)

    # 4. Sort
    if sort_by == "match":
        filtered_jobs.sort(key=lambda j: j.get("matchScore", 0), reverse=True)
    elif sort_by == "newest":
        filtered_jobs.sort(key=lambda j: j.get("posted_days_ago", 999))
    elif sort_by == "salary-high":
        filtered_jobs.sort(key=lambda j: j.get("ceiling_salary", 0), reverse=True)

    # 5. Persist to 24-Hour Disk Cache (only cache non-empty results)
    if filtered_jobs:
        disk_cache[cache_key] = {
            "timestamp": now,
            "jobs": filtered_jobs
        }
        _save_disk_cache(disk_cache)

    return {
        "jobs": filtered_jobs,
        "user_roles": matched_role_titles,
        "is_intern": is_intern,
        "source": source
    }
