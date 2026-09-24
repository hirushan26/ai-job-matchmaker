import mysql.connector
from werkzeug.security import generate_password_hash
from . import config

def get_db_connection(include_db=True):
    """Establishes and returns a connection to MySQL."""
    conn_params = {
        "host": config.DB_HOST,
        "port": config.DB_PORT,
        "user": config.DB_USER,
        "password": config.DB_PASSWORD,
    }
    if include_db:
        conn_params["database"] = config.DB_NAME
    
    return mysql.connector.connect(**conn_params)

def init_db():
    """Initializes the database, creates tables, and seeds initial data."""
    # 1. Ensure database exists
    conn_no_db = get_db_connection(include_db=False)
    cursor_no_db = conn_no_db.cursor()
    cursor_no_db.execute(f"CREATE DATABASE IF NOT EXISTS {config.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cursor_no_db.close()
    conn_no_db.close()

    # 2. Connect to the database and create tables
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            user_name VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            gender VARCHAR(20),
            current_title VARCHAR(150),
            location VARCHAR(150),
            phone VARCHAR(50),
            linkedin_url VARCHAR(255),
            github_url VARCHAR(255),
            portfolio_url VARCHAR(255),
            degree VARCHAR(150),
            institute VARCHAR(200),
            duration VARCHAR(50),
            graduation_year VARCHAR(50),
            profile_score INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
    """)

    # Resumes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            resume_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            raw_text LONGTEXT,
            resume_brief TEXT,
            experience_years DECIMAL(4, 1) DEFAULT 0.0,
            experience_summary TEXT,
            resume_score INT DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
    """)

    # Skills catalog table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            skill_id INT AUTO_INCREMENT PRIMARY KEY,
            skill_name VARCHAR(100) NOT NULL UNIQUE
        );
    """)

    # User skills junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_skills (
            user_id INT NOT NULL,
            skill_id INT NOT NULL,
            PRIMARY KEY (user_id, skill_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
        );
    """)

    # Job roles catalog table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_roles (
            jobrole_id INT AUTO_INCREMENT PRIMARY KEY,
            jobrole_code VARCHAR(50) UNIQUE,
            jobrole_name VARCHAR(150) NOT NULL,
            description TEXT
        );
    """)

    # User job matches with gap analysis and score breakdown
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_job_matches (
            match_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            jobrole_id INT NULL,
            job_title VARCHAR(150) NOT NULL,
            match_percentage INT NOT NULL,
            compatibility_summary TEXT,
            score_explanation TEXT,
            score_breakdown_json JSON,
            role_description TEXT,
            matched_skills_json JSON,
            missing_skills_json JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (jobrole_id) REFERENCES job_roles(jobrole_id) ON DELETE SET NULL
        );
    """)

    # Bookmarked jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarked_jobs (
            bm_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            job_role VARCHAR(150) NOT NULL,
            company_name VARCHAR(150) NOT NULL,
            city VARCHAR(100),
            country VARCHAR(100),
            floor_salary DECIMAL(10, 2),
            ceiling_salary DECIMAL(10, 2),
            salary_text VARCHAR(100),
            match_score INT,
            job_url VARCHAR(500) DEFAULT NULL,
            job_type VARCHAR(50) DEFAULT 'Full-time',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
    """)

    # Ensure password_hash exists in users
    try:
        cursor.execute("SHOW COLUMNS FROM users LIKE 'password_hash';")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL;")
    except Exception as e:
        print(f"Notice on users password_hash column: {e}")

    # Ensure job_url and job_type exist if bookmarked_jobs already existed
    try:
        cursor.execute("SHOW COLUMNS FROM bookmarked_jobs LIKE 'job_url';")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE bookmarked_jobs ADD COLUMN job_url VARCHAR(500) DEFAULT NULL;")
        cursor.execute("SHOW COLUMNS FROM bookmarked_jobs LIKE 'job_type';")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE bookmarked_jobs ADD COLUMN job_type VARCHAR(50) DEFAULT 'Full-time';")
    except Exception as e:
        print(f"Warning adding columns to bookmarked_jobs: {e}")

    conn.commit()

    # 3. Seed Initial Job Roles if table is empty
    cursor.execute("SELECT COUNT(*) FROM job_roles;")
    if cursor.fetchone()[0] == 0:
        initial_roles = [
            ("se", "Software Engineer", "Designs, develops, and maintains software applications using modern programming languages and clean architecture."),
            ("qa", "Quality Assurance Engineer", "Ensures product quality via automated testing, test pipelines, bug tracking, and manual test execution."),
            ("fs", "Full Stack Developer", "Builds end-to-end web applications combining responsive frontend interfaces with robust backend APIs and databases."),
            ("devops", "DevOps Engineer", "Automates CI/CD pipelines, container orchestration, cloud infrastructure, and monitoring systems."),
            ("da", "Data Analyst", "Extracts insights from large datasets using SQL, Python, statistical methods, and dashboard visualization tools.")
        ]
        cursor.executemany(
            "INSERT INTO job_roles (jobrole_code, jobrole_name, description) VALUES (%s, %s, %s);",
            initial_roles
        )
        conn.commit()

    # 4. Seed Default User if not exists
    cursor.execute("SELECT user_id FROM users WHERE user_id = 1;")
    user1 = cursor.fetchone()
    default_pwd_hash = generate_password_hash("123456")
    if not user1:
        cursor.execute("""
            INSERT INTO users (
                user_id, user_name, email, password_hash, first_name, last_name, gender, current_title,
                location, phone, linkedin_url, github_url, portfolio_url,
                degree, institute, duration, graduation_year, profile_score
            ) VALUES (
                1, 'hirushan', 'hirushan@gmail.com', %s, 'Hirushan', 'Nimnada', 'Male', '',
                '', '', '', '', '',
                '', '', '', '', 0
            );
        """, (default_pwd_hash,))
        conn.commit()
    else:
        # If user 1 exists but doesn't have password_hash, set default '123456'
        try:
            cursor.execute("SELECT password_hash FROM users WHERE user_id = 1;")
            p_row = cursor.fetchone()
            if p_row and not p_row[0]:
                cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = 1;", (default_pwd_hash,))
                conn.commit()
        except Exception:
            pass

    cursor.close()
    conn.close()
    print("Database initialized successfully.")