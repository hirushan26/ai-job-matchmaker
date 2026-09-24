# JobMaker - AI-Powered Job & Resume Matching Platform

JobMaker is an end-to-end intelligent career platform that parses resumes, evaluates candidate qualifications using Google Gemini AI, performs multi-role gap analysis, and matches candidates with live tech jobs and internships (via RapidAPI JSearch and curated local feeds).

---

## Features

- **Gemini AI Resume Parsing & Evaluation**: Extracts education, projects, technical skills, soft skills, and experience directly from uploaded PDF or Word resumes (`.pdf`, `.docx`).
- **Multi-Role Compatibility & Gap Analysis**: Computes matchmaking percentages across standard target tech roles (Software Engineer, Quality Assurance, Full Stack, DevOps, Data Analyst) highlighting matched skills, missing skills, and career improvement roadmaps.
- **Live Tech Job Search**: Integrates with RapidAPI JSearch for real-time local (Sri Lanka) and global remote tech jobs, internships, and vacancies with 24-hour intelligent disk caching.
- **Curated Tech Job Feed**: Embedded verified fallback opportunities ensuring continuous availability even without active search API queries.
- **Candidate Profile & Bookmarking**: Candidate dashboard for updating personal details, managing verified skill tags, and saving target jobs.
- **Secure Authentication & Session Management**: Built-in hashed password authentication, session management, and MySQL relational persistence.

---

## Tech Stack

- **Backend**: Python 3.10+, Flask, Flask-CORS, PyPDF, python-docx, mysql-connector-python, python-dotenv
- **Frontend**: HTML5, Responsive CSS3, Vanilla JavaScript (ES6+ modular fetch API)
- **Database**: MySQL (compatible with XAMPP MySQL / standalone MySQL Server 8.0+)
- **External AI & APIs**: Google Gemini AI (Multimodal `gemini-1.5-flash` / `gemini-2.0-flash`), RapidAPI JSearch

---

## Project Structure

```
├── backend/
│   ├── cache/                  # Runtime 24h jobs cache
│   ├── data/
│   │   └── curated_jobs.json   # Curated tech jobs dataset
│   ├── services/
│   │   ├── extractor_service.py   # PDF and DOCX text extraction
│   │   ├── gemini_service.py      # Google Gemini AI prompts & parsing
│   │   ├── job_service.py         # RapidAPI JSearch integration & caching
│   │   └── normalizer_service.py  # Canonical skill alias normalization
│   ├── app.py                  # Flask routes, API endpoints, static handlers
│   ├── config.py               # Environment configuration & secret loader
│   ├── database.py             # MySQL connection, schema initialization & seeds
│   └── requirements.txt        # Backend dependencies
├── icons/                      # Application icons, graphics, and images
├── js/                         # Frontend scripts (api.js, analysis.js, jobs.js, etc.)
├── Styles/                     # Frontend stylesheets (home.css, profile.css, etc.)
├── uploads/                    # User resume upload destination (sample files included)
├── .env.example                # Configuration template for environment variables
├── .gitignore                  # Git ignore rules for keys, bytecode, venv, and uploads
├── home.html                   # Landing page
├── index.html                  # Jobs & matching dashboard
├── Login.html                  # User login page
├── register.html               # Registration page
├── jobmaker_db.sql             # SQL database schema and seeds
├── requirements.txt            # Root dependencies mirror
└── run.py                      # Application launcher script
```

---

## Getting Started

### 1. Prerequisites
- **Python 3.10+** installed
- **MySQL Server** (e.g. via [XAMPP](https://www.apachefriends.org/) or standalone MySQL)
- **Google Gemini API Key** (Free tier available at [Google AI Studio](https://aistudio.google.com/))
- **RapidAPI Key** (Free tier available at [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch))

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 3. Create and Activate a Virtual Environment
**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy the `.env.example` file to create your local `.env`:

**Windows:**
```powershell
copy .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

Open `.env` and fill in your keys and database credentials:
```env
# Google Gemini AI API Key
GEMINI_API_KEY=your_gemini_api_key_here

# RapidAPI Key for live job search
RAPIDAPI_KEY=your_rapidapi_key_here

# Flask Session Key
SECRET_KEY=change_this_to_a_secure_random_string_2026

# MySQL Configuration (Default for XAMPP is root with no password)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=jobmaker_db
```

### 6. Set Up the Database
Ensure your MySQL server is running (e.g., start MySQL in the XAMPP Control Panel).
You can either:
- Let `run.py` automatically create the database and seed tables on first launch, OR
- Import `jobmaker_db.sql` into phpMyAdmin / MySQL CLI.

### 7. Run the Application
```bash
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## Security & API Keys

- Sensitive keys, credentials, and passwords are never hardcoded in source files.
- All secrets are managed using environment variables loaded via `.env` (which is excluded from Git via `.gitignore`).
- When contributing or deploying, always configure secrets through environment variables or a local `.env` file.
