import os
import json
import time
import traceback
from pathlib import Path
from flask import Flask, render_template, request, redirect, jsonify, session, send_from_directory, has_request_context
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from . import config
from . import database
from .services import extractor_service
from .services import gemini_service
from .services import normalizer_service
from .services import job_service

BASE_DIR = config.BASE_DIR

app = Flask(
    __name__,
    template_folder=str(BASE_DIR),
    static_folder=None
)
CORS(app, supports_credentials=True)

# Secret key for Flask Session Management
app.secret_key = os.getenv("SECRET_KEY", "jobmaiker_secure_auth_session_key_2026")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

# ==========================================
# STATIC ASSETS SERVING ROUTES
# ==========================================

@app.route('/Styles/<path:filename>')
def serve_styles(filename):
    return send_from_directory(BASE_DIR / 'Styles', filename)

@app.route('/icons/<path:filename>')
def serve_icons(filename):
    return send_from_directory(BASE_DIR / 'icons', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(BASE_DIR / 'js', filename)

@app.route('/static/<path:filename>', endpoint='static')
def serve_static(filename):
    """Maps legacy or template static paths to actual folders."""
    if filename.startswith('css/'):
        return send_from_directory(BASE_DIR / 'Styles', filename[4:])
    if filename.startswith('image/'):
        return send_from_directory(BASE_DIR / 'icons', filename[6:])
    if filename.startswith('icons/'):
        return send_from_directory(BASE_DIR / 'icons', filename[6:])
    if filename.startswith('js/'):
        return send_from_directory(BASE_DIR / 'js', filename[3:])
    
    for folder in ['Styles', 'icons', 'js']:
        target = BASE_DIR / folder / filename
        if target.exists():
            return send_from_directory(BASE_DIR / folder, filename)
    return "Static file not found", 404

# ==========================================
# AUTHENTICATION & PAGE NAVIGATION ROUTES
# ==========================================

@app.after_request
def add_no_cache_headers(response):
    """Prevents browser from caching protected pages (like dashboard) when logged out."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
@app.route("/home")
@app.route("/home.html")
@app.route("/Home.html")
def landing_page():
    """
    Serves the JobmAIker landing page.
    Home page must be shown ONLY when the user is logged out.
    If the user is logged in, it should always open the dashboard.
    """
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
@app.route("/login.html", methods=["GET", "POST"])
@app.route("/Login.html", methods=["GET", "POST"])
def login_page():
    """Handles User Login via Form POST or renders Login.html."""
    if request.method == "GET":
        if "user_id" in session:
            return redirect("/dashboard")
        return render_template("Login.html")

    # POST Login
    identifier = (request.form.get("email") or request.form.get("username") or "").strip().lower()
    password = request.form.get("password", "")

    if not identifier or not password:
        return render_template("Login.html", message="Please enter both email/username and password.", message_type="error", email=identifier)

    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = %s OR LOWER(user_name) = %s LIMIT 1;", (identifier, identifier))
        user = cursor.fetchone()

        if not user:
            return render_template("Login.html", message="Account not found. Please register first.", message_type="error", email=identifier)

        pwd_hash = user.get("password_hash")
        valid_password = False

        if pwd_hash:
            try:
                valid_password = check_password_hash(pwd_hash, password)
            except Exception:
                valid_password = (pwd_hash == password)
        else:
            # Fallback for default user seeded without hash: auto-set hash on first valid login
            valid_password = True
            hashed = generate_password_hash(password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s;", (hashed, user["user_id"]))
            conn.commit()

        if valid_password:
            session.permanent = True
            session["user_id"] = user["user_id"]
            session["user_name"] = user["user_name"]
            session["email"] = user["email"]
            session["display_name"] = f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip() or user["user_name"]
            return redirect("/dashboard")
        else:
            return render_template("Login.html", message="Invalid email/username or password. Please try again.", message_type="error", email=identifier)

    except Exception as e:
        traceback.print_exc()
        return render_template("Login.html", message="Database connection error. Please try again.", message_type="error", email=identifier)
    finally:
        cursor.close()
        conn.close()

@app.route("/api/login", methods=["POST"])
def api_login():
    """Handles User Login via JSON API."""
    data = request.get_json() or {}
    identifier = (data.get("email") or data.get("username") or "").strip().lower()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"success": False, "error": "Please enter both email/username and password."}), 400

    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = %s OR LOWER(user_name) = %s LIMIT 1;", (identifier, identifier))
        user = cursor.fetchone()

        if not user:
            return jsonify({"success": False, "error": "Account not found. Please register first."}), 404

        pwd_hash = user.get("password_hash")
        valid_password = False

        if pwd_hash:
            try:
                valid_password = check_password_hash(pwd_hash, password)
            except Exception:
                valid_password = (pwd_hash == password)
        else:
            valid_password = True
            hashed = generate_password_hash(password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s;", (hashed, user["user_id"]))
            conn.commit()

        if valid_password:
            session.permanent = True
            session["user_id"] = user["user_id"]
            session["user_name"] = user["user_name"]
            session["email"] = user["email"]
            session["display_name"] = f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip() or user["user_name"]
            return jsonify({
                "success": True,
                "message": "Login successful",
                "redirect": "/dashboard",
                "user": {
                    "user_id": user["user_id"],
                    "user_name": user["user_name"],
                    "email": user["email"],
                    "display_name": session["display_name"]
                }
            }), 200
        else:
            return jsonify({"success": False, "error": "Invalid email/username or password."}), 401

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/register", methods=["GET", "POST"])
@app.route("/register.html", methods=["GET", "POST"])
@app.route("/Register.html", methods=["GET", "POST"])
def register_page():
    """Handles User Registration."""
    if request.method == "GET":
        if "user_id" in session:
            return redirect("/dashboard")
        return render_template("register.html")

    # POST Registration
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirmPassword", "")

    if not name or not email or not password:
        return render_template("register.html", message="Please fill in all required fields.", message_type="error", name=name, email=email)

    if password != confirm_password:
        return render_template("register.html", message="Passwords do not match.", message_type="error", name=name, email=email)

    if len(password) < 4:
        return render_template("register.html", message="Password must be at least 4 characters long.", message_type="error", name=name, email=email)

    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = %s;", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            return render_template("register.html", message="Email is already registered. Please log in.", message_type="error", name=name, email=email)

        hashed_password = generate_password_hash(password)

        raw_user_name = email.split("@")[0].replace(".", "_").replace("-", "_")
        cursor.execute("SELECT user_id FROM users WHERE user_name = %s;", (raw_user_name,))
        if cursor.fetchone():
            raw_user_name = f"{raw_user_name}_{int(time.time()) % 10000}"

        name_parts = name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        cursor.execute("""
            INSERT INTO users (
                user_name, email, password_hash, first_name, last_name, current_title, location, profile_score
            ) VALUES (%s, %s, %s, %s, %s, '', '', 0);
        """, (raw_user_name, email, hashed_password, first_name, last_name))
        conn.commit()

        return redirect("/login?registered=1")

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return render_template("register.html", message=f"Registration failed: {str(e)}", message_type="error", name=name, email=email)
    finally:
        cursor.close()
        conn.close()

@app.route("/logout")
def logout():
    """Logs the user out, clears session, and redirects to landing page."""
    session.clear()
    return redirect("/home?logout=1")

@app.route("/dashboard")
@app.route("/index.html")
@app.route("/Index.html")
def dashboard_page():
    """Protected Dashboard route. Requires user login."""
    if "user_id" not in session:
        return redirect("/login")
    return render_template("index.html")

@app.route("/profile")
def profile_page():
    """Profile redirect helper."""
    if "user_id" not in session:
        return redirect("/login")
    return redirect("/dashboard#profile-content")

@app.route("/api/auth/status", methods=["GET"])
def auth_status():
    """Returns current authentication state for the client."""
    if "user_id" in session:
        return jsonify({
            "authenticated": True,
            "user_id": session["user_id"],
            "user_name": session.get("user_name"),
            "email": session.get("email"),
            "display_name": session.get("display_name")
        }), 200
    return jsonify({"authenticated": False}), 200

# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Fetches user profile, latest resume summary, and extracted skills."""
    user_id = session.get("user_id", 1)
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Fetch user record
        cursor.execute("SELECT * FROM users WHERE user_id = %s;", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # 2. Fetch latest resume
        cursor.execute("""
            SELECT * FROM resumes 
            WHERE user_id = %s 
            ORDER BY uploaded_at DESC LIMIT 1;
        """, (user_id,))
        resume = cursor.fetchone()

        # 3. Fetch user skills
        cursor.execute("""
            SELECT s.skill_name 
            FROM user_skills us
            JOIN skills s ON us.skill_id = s.skill_id
            WHERE us.user_id = %s
            ORDER BY s.skill_name ASC;
        """, (user_id,))
        skills_rows = cursor.fetchall()
        skills = [r["skill_name"] for r in skills_rows]

        degree_raw = user.get("degree") or ""
        institute_raw = user.get("institute") or ""
        response_data = {
            "user": {
                "id": user["user_id"],
                "username": user["user_name"],
                "first_name": user["first_name"] or "",
                "last_name": user["last_name"] or "",
                "full_name": f"{user['first_name'] or ''} {user['last_name'] or ''}".strip() or user["user_name"],
                "role": user["current_title"] or "",
                "location": user["location"] or "",
                "email": user["email"] or "",
                "phone": user["phone"] or "",
                "linkedin": user["linkedin_url"] or "",
                "github": user["github_url"] or "",
                "portfolio": user["portfolio_url"] or "",
                "profile_score": user["profile_score"] if user["profile_score"] is not None else 0,
                "education": {
                    "degree": normalizer_service.normalize_degree(degree_raw) if degree_raw else "",
                    "institute": institute_raw,
                    "duration": user.get("duration") or "",
                    "graduation_year": user.get("graduation_year") or ""
                }
            },
            "resume": {
                "file_name": resume["file_name"] if resume else "None",
                "summary": resume["resume_brief"] if resume else "",
                "experience_years": float(resume["experience_years"]) if resume and resume["experience_years"] is not None else 0.0,
                "experience_summary": resume["experience_summary"] if resume else "",
                "resume_score": resume["resume_score"] if resume and resume["resume_score"] is not None else 0,
                "uploaded_at": resume["uploaded_at"].isoformat() if resume and resume["uploaded_at"] else None
            },
            "skills": skills
        }

        return jsonify(response_data), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/profile", methods=["PUT"])
def update_profile():
    """Updates manual edits from the Edit Profile form."""
    user_id = session.get("user_id", 1)
    data = request.get_json() or {}

    full_name = data.get("name", "").strip()
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    conn = database.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE users SET
                first_name = %s,
                last_name = %s,
                current_title = %s,
                location = %s,
                email = %s,
                phone = %s,
                linkedin_url = %s,
                github_url = %s,
                portfolio_url = %s
            WHERE user_id = %s;
        """, (
            first_name[:100],
            last_name[:100],
            str(data.get("role") or "")[:150],
            str(data.get("location") or "")[:150],
            str(data.get("email") or "")[:150],
            str(data.get("phone") or "")[:50],
            str(data.get("linkedin") or "")[:255],
            str(data.get("github") or "")[:255],
            str(data.get("portfolio") or "")[:255],
            user_id
        ))
        conn.commit()
        if full_name and has_request_context() and "user_id" in session and session["user_id"] == user_id:
            session["display_name"] = full_name
        return jsonify({"success": True, "message": "Profile updated successfully"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/analysis", methods=["GET"])
def get_analysis():
    """Fetches cached analysis data: experience, education, skills cloud, and job matches."""
    user_id = session.get("user_id", 1)
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Fetch user & latest resume overview
        cursor.execute("""
            SELECT u.degree, u.institute, u.duration, u.graduation_year,
                   r.experience_years, r.experience_summary, r.resume_brief, r.resume_score
            FROM users u
            LEFT JOIN resumes r ON u.user_id = r.user_id
            WHERE u.user_id = %s
            ORDER BY r.uploaded_at DESC LIMIT 1;
        """, (user_id,))
        overview = cursor.fetchone() or {}

        # 2. Fetch skills cloud
        cursor.execute("""
            SELECT s.skill_name 
            FROM user_skills us
            JOIN skills s ON us.skill_id = s.skill_id
            WHERE us.user_id = %s
            ORDER BY s.skill_name ASC;
        """, (user_id,))
        skills = [row["skill_name"] for row in cursor.fetchall()]

        # 3. Fetch matched job roles and gap analyses
        cursor.execute("""
            SELECT ujm.*, jr.jobrole_code
            FROM user_job_matches ujm
            LEFT JOIN job_roles jr ON ujm.jobrole_id = jr.jobrole_id
            WHERE ujm.user_id = %s
            ORDER BY ujm.match_percentage DESC;
        """, (user_id,))
        matches_rows = cursor.fetchall()

        job_analyses = []
        for row in matches_rows:
            matched_skills = json.loads(row["matched_skills_json"]) if row["matched_skills_json"] else []
            missing_skills = json.loads(row["missing_skills_json"]) if row["missing_skills_json"] else []
            score_breakdown = json.loads(row["score_breakdown_json"]) if row.get("score_breakdown_json") else {}

            job_analyses.append({
                "job_key": row["jobrole_code"] or f"job_{row['match_id']}",
                "job_title": row["job_title"],
                "match_percentage": row["match_percentage"],
                "compatibility_summary": row["compatibility_summary"],
                "score_explanation": row.get("score_explanation") or "",
                "score_breakdown": score_breakdown,
                "role_description": row["role_description"] or "",
                "matched_skills": matched_skills,
                "missing_skills": missing_skills
            })

        degree_raw = overview.get("degree") or ""
        institute_raw = overview.get("institute") or ""
        return jsonify({
            "experience_years": float(overview.get("experience_years") or 0.0),
            "experience_summary": overview.get("experience_summary") or "",
            "resume_brief": overview.get("resume_brief") or "",
            "resume_score": int(overview.get("resume_score") or 0),
            "education": {
                "degree": normalizer_service.normalize_degree(degree_raw) if degree_raw else "",
                "institute": institute_raw,
                "duration": overview.get("duration") or "",
                "graduation_year": overview.get("graduation_year") or ""
            },
            "skills": skills,
            "job_analyses": job_analyses
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

def save_confirmed_resume_to_db(user_id: int, filename: str, save_path: Path, raw_text: str, analysis_result: dict):
    """Executes the MySQL transaction to apply confirmed resume data to user profile, skills, and matches."""
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if not isinstance(analysis_result, dict):
            analysis_result = {}

        summary = analysis_result.get("summary") or ""
        ps = analysis_result.get("profile_score")
        profile_score = int(ps) if ps is not None else 85

        personal_info = analysis_result.get("personal_info") or {}
        if not isinstance(personal_info, dict):
            personal_info = {}

        experience_data = analysis_result.get("experience") or {}
        if not isinstance(experience_data, dict):
            experience_data = {}

        education_data = analysis_result.get("education") or {}
        if not isinstance(education_data, dict):
            education_data = {}

        extracted_skills = analysis_result.get("skills") or []
        if not isinstance(extracted_skills, list):
            extracted_skills = []

        all_job_analyses = analysis_result.get("all_job_analyses") or []
        if not isinstance(all_job_analyses, list):
            all_job_analyses = []

        ey = experience_data.get("years")
        try:
            exp_years = float(ey) if ey is not None else 0.0
        except (ValueError, TypeError):
            exp_years = 0.0
        exp_summary = experience_data.get("summary") or ""

        # Personal details from CV
        cand_name = str(personal_info.get("name") or "").strip()
        cand_role = str(personal_info.get("role") or "").strip()
        cand_loc = str(personal_info.get("location") or "").strip()
        cand_phone = str(personal_info.get("phone") or "").strip()
        cand_linkedin = str(personal_info.get("linkedin") or "").strip()
        cand_github = str(personal_info.get("github") or "").strip()
        cand_portfolio = str(personal_info.get("portfolio") or "").strip()

        first_name = ""
        last_name = ""
        if cand_name:
            parts = cand_name.split(" ", 1)
            first_name = parts[0].strip()
            last_name = parts[1].strip() if len(parts) > 1 else ""

        deg_raw = str(education_data.get("degree") or "").strip()
        edu_degree = normalizer_service.normalize_degree(deg_raw) if deg_raw else ""
        edu_institute = str(education_data.get("institute") or education_data.get("institution") or "").strip()
        edu_duration = str(education_data.get("duration") or "").strip()
        edu_grad_year = str(education_data.get("graduation_year") or "").strip()

        # 1. Update Users table with profile_score, candidate profile details, and education details
        cursor.execute("""
            UPDATE users SET
                profile_score = %s,
                first_name = CASE WHEN %s != '' THEN %s ELSE first_name END,
                last_name = CASE WHEN %s != '' THEN %s ELSE last_name END,
                current_title = CASE WHEN %s != '' THEN %s ELSE current_title END,
                location = CASE WHEN %s != '' THEN %s ELSE location END,
                phone = CASE WHEN %s != '' THEN %s ELSE phone END,
                linkedin_url = CASE WHEN %s != '' THEN %s ELSE linkedin_url END,
                github_url = CASE WHEN %s != '' THEN %s ELSE github_url END,
                portfolio_url = CASE WHEN %s != '' THEN %s ELSE portfolio_url END,
                degree = CASE WHEN %s != '' THEN %s ELSE degree END,
                institute = CASE WHEN %s != '' THEN %s ELSE institute END,
                duration = CASE WHEN %s != '' THEN %s ELSE duration END,
                graduation_year = CASE WHEN %s != '' THEN %s ELSE graduation_year END
            WHERE user_id = %s;
        """, (
            profile_score,
            first_name[:100], first_name[:100],
            last_name[:100], last_name[:100],
            cand_role[:150], cand_role[:150],
            cand_loc[:150], cand_loc[:150],
            cand_phone[:50], cand_phone[:50],
            cand_linkedin[:255], cand_linkedin[:255],
            cand_github[:255], cand_github[:255],
            cand_portfolio[:255], cand_portfolio[:255],
            edu_degree[:150], edu_degree[:150],
            edu_institute[:200], edu_institute[:200],
            edu_duration[:50], edu_duration[:50],
            edu_grad_year[:50], edu_grad_year[:50],
            user_id
        ))

        # Update session display name if available
        if cand_name and has_request_context() and "user_id" in session and session["user_id"] == user_id:
            session["display_name"] = cand_name

        # 2. Insert Resume record
        cursor.execute("""
            INSERT INTO resumes (
                user_id, file_name, file_path, raw_text, resume_brief, experience_years, experience_summary, resume_score
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            user_id,
            filename[:255],
            str(save_path)[:500],
            raw_text or summary,
            summary,
            exp_years,
            exp_summary,
            profile_score
        ))

        # 3. Update Skills
        cursor.execute("DELETE FROM user_skills WHERE user_id = %s;", (user_id,))
        for skill_name in extracted_skills:
            if not isinstance(skill_name, str):
                continue
            cleaned_skill = skill_name.strip()[:100]
            if not cleaned_skill:
                continue
            cursor.execute("INSERT IGNORE INTO skills (skill_name) VALUES (%s);", (cleaned_skill,))
            cursor.execute("SELECT skill_id FROM skills WHERE skill_name = %s;", (cleaned_skill,))
            skill_row = cursor.fetchone()
            if skill_row:
                cursor.execute("INSERT IGNORE INTO user_skills (user_id, skill_id) VALUES (%s, %s);", (user_id, skill_row["skill_id"]))

        # 4. Update Job Matches
        cursor.execute("SELECT jobrole_id, jobrole_code, jobrole_name FROM job_roles;")
        job_roles = cursor.fetchall()
        role_lookup = {r["jobrole_code"]: r["jobrole_id"] for r in job_roles if r.get("jobrole_code")}
        role_name_lookup = {r["jobrole_name"].lower(): r["jobrole_id"] for r in job_roles if r.get("jobrole_name")}
        role_code_to_name = {r["jobrole_code"]: r["jobrole_name"] for r in job_roles if r.get("jobrole_code")}

        cursor.execute("DELETE FROM user_job_matches WHERE user_id = %s;", (user_id,))

        for role_eval in all_job_analyses:
            if not isinstance(role_eval, dict):
                continue
            code = role_eval.get("jobrole_code")
            title = (role_eval.get("jobrole_name") or role_eval.get("job_title") or role_code_to_name.get(code) or "Software Engineer")[:150]
            jobrole_id = role_lookup.get(code) or role_name_lookup.get(title.lower())

            mp = role_eval.get("match_percentage")
            try:
                match_pct = int(mp) if mp is not None else 80
            except (ValueError, TypeError):
                match_pct = 80
            match_pct = max(0, min(100, match_pct))

            cursor.execute("""
                INSERT INTO user_job_matches (
                    user_id, jobrole_id, job_title, match_percentage, compatibility_summary,
                    score_explanation, score_breakdown_json, role_description,
                    matched_skills_json, missing_skills_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                user_id,
                jobrole_id,
                title,
                match_pct,
                role_eval.get("compatibility_summary") or "",
                role_eval.get("score_explanation") or "",
                json.dumps(role_eval.get("score_breakdown") or {}),
                role_eval.get("role_description") or "",
                json.dumps(role_eval.get("matched_skills") or []),
                json.dumps(role_eval.get("missing_skills") or [])
            ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

@app.route("/api/resume/parse", methods=["POST"])
def parse_resume():
    """Step 1: Uploads and parses resume with Gemini AI."""
    if "resume" not in request.files and "cv_file" not in request.files:
        return jsonify({"error": "No file uploaded. Key must be 'resume' or 'cv_file'."}), 400

    file = request.files.get("resume") or request.files.get("cv_file")
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Invalid file format. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"}), 400

    filename = secure_filename(file.filename)
    save_path = config.UPLOAD_FOLDER / filename
    file.save(save_path)

    try:
        raw_text = extractor_service.extract_text_from_file(str(save_path))
        is_pdf = filename.lower().endswith(".pdf")
        if not is_pdf and (not raw_text or len(raw_text.strip()) < 20):
            return jsonify({"error": "Could not extract meaningful text from resume."}), 400

        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT jobrole_id, jobrole_code, jobrole_name, description FROM job_roles;")
        job_roles = cursor.fetchall()
        cursor.close()
        conn.close()

        analysis_result = gemini_service.analyze_resume_with_gemini(raw_text, job_roles, file_path=str(save_path))

        return jsonify({
            "success": True,
            "staged_filename": filename,
            "raw_text": raw_text or (analysis_result.get("summary") if isinstance(analysis_result, dict) else "") or "",
            "analysis": analysis_result
        }), 200

    except gemini_service.GeminiServiceError as gse:
        clean_msg = gemini_service.sanitize_api_error(str(gse))
        print(f"[ResumeParse] GeminiServiceError: {clean_msg}")
        return jsonify({"error": clean_msg}), 500
    except ValueError as ve:
        clean_ve = gemini_service.sanitize_api_error(str(ve))
        print(f"[ResumeParse] ValueError: {clean_ve}")
        return jsonify({"error": clean_ve}), 400
    except Exception as e:
        safe_tb = gemini_service.sanitize_api_error(traceback.format_exc())
        print(f"[ResumeParse] Exception trace:\n{safe_tb}")
        clean_e = gemini_service.sanitize_api_error(str(e))
        print(f"[ResumeParse] Unexpected error: {clean_e}")
        return jsonify({"error": "Unable to analyze resume at this time. Please try again shortly or check your document."}), 500

@app.route("/api/resume/confirm", methods=["POST"])
def confirm_resume():
    """Step 2: Commits approved CV parse to current user profile."""
    user_id = session.get("user_id", 1)
    data = request.get_json() or {}
    staged_filename = data.get("staged_filename")
    analysis = data.get("analysis")
    raw_text = data.get("raw_text", "")

    if not staged_filename or not analysis:
        return jsonify({"error": "Missing staged_filename or analysis data."}), 400

    save_path = config.UPLOAD_FOLDER / secure_filename(staged_filename)

    try:
        save_confirmed_resume_to_db(user_id, staged_filename, save_path, raw_text, analysis)

        exp = analysis.get("experience") if isinstance(analysis, dict) else {}
        if not isinstance(exp, dict):
            exp = {}
        ey = exp.get("years")
        try:
            exp_years = float(ey) if ey is not None else 0.0
        except (ValueError, TypeError):
            exp_years = 0.0

        ps = analysis.get("profile_score") if isinstance(analysis, dict) else None
        profile_score = int(ps) if ps is not None else 85

        return jsonify({
            "success": True,
            "message": "Resume details approved and applied to your profile!",
            "summary": (analysis.get("summary") if isinstance(analysis, dict) else "") or "",
            "file_name": staged_filename,
            "profile_score": profile_score,
            "experience_years": exp_years,
            "experience_summary": exp.get("summary") or "",
            "education": analysis.get("education") if isinstance(analysis, dict) else {},
            "skills": analysis.get("skills") if isinstance(analysis, dict) else [],
            "job_analyses": analysis.get("all_job_analyses") if isinstance(analysis, dict) else []
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to save confirmed resume: {str(e)}"}), 500

@app.route("/api/resume/discard", methods=["POST"])
def discard_resume():
    """Discards staged resume."""
    data = request.get_json() or {}
    staged_filename = data.get("staged_filename")
    if staged_filename:
        safe_name = secure_filename(staged_filename)
        save_path = config.UPLOAD_FOLDER / safe_name
        if save_path.exists():
            try:
                os.remove(save_path)
            except Exception:
                pass
    return jsonify({"success": True, "message": "Resume discarded."}), 200

@app.route("/api/resume/upload", methods=["POST"])
def upload_resume():
    """Direct upload & parse (auto-commit)."""
    user_id = session.get("user_id", 1)
    if "resume" not in request.files and "cv_file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files.get("resume") or request.files.get("cv_file")
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Invalid format. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"}), 400

    filename = secure_filename(file.filename)
    save_path = config.UPLOAD_FOLDER / filename
    file.save(save_path)

    try:
        raw_text = extractor_service.extract_text_from_file(str(save_path))
        is_pdf = filename.lower().endswith(".pdf")
        if not is_pdf and (not raw_text or len(raw_text.strip()) < 20):
            return jsonify({"error": "Could not extract readable text."}), 400

        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT jobrole_id, jobrole_code, jobrole_name, description FROM job_roles;")
        job_roles = cursor.fetchall()
        cursor.close()
        conn.close()

        analysis_result = gemini_service.analyze_resume_with_gemini(raw_text, job_roles, file_path=str(save_path))
        save_confirmed_resume_to_db(user_id, filename, save_path, raw_text, analysis_result)

        exp = analysis_result.get("experience") if isinstance(analysis_result, dict) else {}
        if not isinstance(exp, dict):
            exp = {}
        ey = exp.get("years")
        try:
            exp_years = float(ey) if ey is not None else 0.0
        except (ValueError, TypeError):
            exp_years = 0.0

        ps = analysis_result.get("profile_score") if isinstance(analysis_result, dict) else None
        profile_score = int(ps) if ps is not None else 85

        return jsonify({
            "success": True,
            "message": "Resume uploaded and parsed successfully!",
            "summary": (analysis_result.get("summary") if isinstance(analysis_result, dict) else "") or "",
            "file_name": filename,
            "profile_score": profile_score,
            "experience_years": exp_years,
            "experience_summary": exp.get("summary") or "",
            "education": analysis_result.get("education") if isinstance(analysis_result, dict) else {},
            "skills": analysis_result.get("skills") if isinstance(analysis_result, dict) else [],
            "job_analyses": analysis_result.get("all_job_analyses") if isinstance(analysis_result, dict) else []
        }), 200

    except gemini_service.GeminiServiceError as gse:
        clean_msg = gemini_service.sanitize_api_error(str(gse))
        print(f"[ResumeUpload] GeminiServiceError: {clean_msg}")
        return jsonify({"error": clean_msg}), 500
    except ValueError as ve:
        clean_ve = gemini_service.sanitize_api_error(str(ve))
        print(f"[ResumeUpload] ValueError: {clean_ve}")
        return jsonify({"error": clean_ve}), 400
    except Exception as e:
        safe_tb = gemini_service.sanitize_api_error(traceback.format_exc())
        print(f"[ResumeUpload] Exception trace:\n{safe_tb}")
        clean_e = gemini_service.sanitize_api_error(str(e))
        print(f"[ResumeUpload] Unexpected error: {clean_e}")
        return jsonify({"error": "Unable to analyze resume at this time. Please try again shortly or check your document."}), 500

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """Live/curated jobs search via TheirStack API with caching."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"jobs": [], "user_roles": [], "is_intern": False, "source": "empty_profile"}), 200
    role = request.args.get("role", "all")
    location = request.args.get("location", "all")
    job_type = request.args.get("job_type", "all")
    experience = request.args.get("experience", "all")
    sort_by = request.args.get("sort", "match")

    roles = [role] if role and role.lower() != "all" else None

    try:
        result = job_service.search_jobs(
            roles=roles,
            location=location,
            job_type=job_type,
            experience_level=experience,
            sort_by=sort_by,
            user_id=user_id
        )
        return jsonify(result), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/bookmarks", methods=["GET"])
def get_bookmarks():
    """Returns bookmarked jobs for the active user."""
    user_id = session.get("user_id", 1)
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT bm_id, job_role, company_name, city, country, 
                   COALESCE(salary_text, '') AS salary_text,
                   match_score, job_url, job_type, created_at
            FROM bookmarked_jobs 
            WHERE user_id = %s 
            ORDER BY created_at DESC;
        """, (user_id,))
        rows = cursor.fetchall()

        bookmarks = []
        for r in rows:
            city = r.get("city") or "Colombo"
            country = r.get("country") or "Sri Lanka"
            loc = f"{city}, {country}" if city and country and city != country else (city or country)
            bookmarks.append({
                "id": r["bm_id"],
                "bm_id": r["bm_id"],
                "title": r["job_role"],
                "company": r["company_name"],
                "location": loc,
                "city": city,
                "country": country,
                "salary": r["salary_text"] or "LKR 150,000 - 250,000",
                "matchScore": r["match_score"] or 90,
                "url": r.get("job_url") or f"https://www.google.com/search?q={r['company_name']}+{r['job_role']}",
                "job_type": r.get("job_type") or "Full-time",
                "experience_level": "Entry Level",
                "created_at": str(r["created_at"])
            })
        return jsonify(bookmarks), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/bookmarks", methods=["POST"])
def add_bookmark():
    """Saves a job posting to user bookmarks."""
    user_id = session.get("user_id", 1)
    data = request.get_json() or {}
    title = data.get("title") or data.get("job_role")
    company = data.get("company") or data.get("company_name")

    if not title or not company:
        return jsonify({"error": "Job title and company name are required"}), 400

    location_str = data.get("location") or "Colombo, Sri Lanka"
    parts = [p.strip() for p in location_str.split(",") if p.strip()]
    city = parts[0] if parts else "Colombo"
    country = parts[1] if len(parts) > 1 else ("Global" if "remote" in location_str.lower() else "Sri Lanka")
    salary_text = data.get("salary") or data.get("salary_text") or "LKR 150,000 - 250,000"
    match_score = int(data.get("matchScore") or data.get("match_score") or 90)
    job_url = data.get("url") or data.get("job_url") or ""
    job_type = data.get("job_type") or "Full-time"

    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT bm_id FROM bookmarked_jobs 
            WHERE user_id = %s AND job_role = %s AND company_name = %s LIMIT 1;
        """, (user_id, title, company))
        existing = cursor.fetchone()

        if existing:
            return jsonify({
                "success": True,
                "bm_id": existing["bm_id"],
                "already_saved": True,
                "message": "Job is already bookmarked"
            }), 200

        cursor.execute("""
            INSERT INTO bookmarked_jobs 
            (user_id, job_role, company_name, city, country, salary_text, match_score, job_url, job_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (user_id, title, company, city, country, salary_text, match_score, job_url, job_type))
        conn.commit()
        new_bm_id = cursor.lastrowid
        return jsonify({
            "success": True,
            "bm_id": new_bm_id,
            "already_saved": False,
            "message": "Job saved to bookmarks"
        }), 201
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/bookmarks/<int:bm_id>", methods=["DELETE"])
def delete_bookmark(bm_id):
    """Removes a bookmark."""
    user_id = session.get("user_id", 1)
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM bookmarked_jobs WHERE bm_id = %s AND user_id = %s;", (bm_id, user_id))
        conn.commit()
        return jsonify({"success": True, "message": "Bookmark removed"}), 200
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    database.init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)