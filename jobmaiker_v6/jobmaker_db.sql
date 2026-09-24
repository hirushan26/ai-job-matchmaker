-- ==========================================================
-- JobMaker Database Schema & Initial Seeds
-- Database: jobmaker_db
-- System: MySQL (XAMPP) / Google Gemini AI Matchmaking Engine
-- ==========================================================

CREATE DATABASE IF NOT EXISTS `jobmaker_db` 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `jobmaker_db`;

-- 1. Users Table

CREATE TABLE `users` (
    `user_id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_name` VARCHAR(100) NOT NULL UNIQUE,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NULL,
    `first_name` VARCHAR(100),
    `last_name` VARCHAR(100),
    `gender` VARCHAR(20),
    `current_title` VARCHAR(150),
    `location` VARCHAR(150),
    `phone` VARCHAR(50),
    `linkedin_url` VARCHAR(255),
    `github_url` VARCHAR(255),
    `portfolio_url` VARCHAR(255),
    `degree` VARCHAR(150),
    `institute` VARCHAR(200),
    `duration` VARCHAR(50),
    `graduation_year` VARCHAR(50),
    `profile_score` INT DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Resumes Table
CREATE TABLE `resumes` (
    `resume_id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `file_name` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `raw_text` LONGTEXT,
    `resume_brief` TEXT,
    `experience_years` DECIMAL(4, 1) DEFAULT 0.0,
    `experience_summary` TEXT,
    `resume_score` INT DEFAULT 0,
    `uploaded_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Skills Catalog Table (Normalized canonical skills)
CREATE TABLE `skills` (
    `skill_id` INT AUTO_INCREMENT PRIMARY KEY,
    `skill_name` VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. User Skills Junction Table (Many-to-Many relationship)
CREATE TABLE `user_skills` (
    `user_id` INT NOT NULL,
    `skill_id` INT NOT NULL,
    PRIMARY KEY (`user_id`, `skill_id`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE,
    FOREIGN KEY (`skill_id`) REFERENCES `skills`(`skill_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Standard Job Roles Catalog Table
CREATE TABLE `job_roles` (
    `jobrole_id` INT AUTO_INCREMENT PRIMARY KEY,
    `jobrole_code` VARCHAR(50) UNIQUE,
    `jobrole_name` VARCHAR(150) NOT NULL,
    `description` TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. User Job Matches Table (Cached AI multi-role gap analysis results)
CREATE TABLE `user_job_matches` (
    `match_id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `jobrole_id` INT NULL,
    `job_title` VARCHAR(150) NOT NULL,
    `match_percentage` INT NOT NULL,
    `compatibility_summary` TEXT,
    `role_description` TEXT,
    `score_breakdown_json` JSON,
    `score_explanation` TEXT,
    `matched_skills_json` JSON,
    `missing_skills_json` JSON,
    `calculated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE,
    FOREIGN KEY (`jobrole_id`) REFERENCES `job_roles`(`jobrole_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Bookmarked Jobs Table
CREATE TABLE `bookmarked_jobs` (
    `bookmark_id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `job_title` VARCHAR(150) NOT NULL,
    `company` VARCHAR(150),
    `location` VARCHAR(150),
    `salary` VARCHAR(100),
    `match_score` INT DEFAULT 0,
    `bookmarked_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



-- Seed Target Job Roles
INSERT INTO `job_roles` (`jobrole_code`, `jobrole_name`, `description`) VALUES
('se', 'Software Engineer', 'Designs, develops, and maintains software applications using modern programming languages and clean architecture.'),
('qa', 'Quality Assurance Engineer', 'Ensures product quality via automated testing, test pipelines, bug tracking, and manual test execution.'),
('fs', 'Full Stack Developer', 'Builds end-to-end web applications combining responsive frontend interfaces with robust backend APIs and databases.'),
('devops', 'DevOps Engineer', 'Automates CI/CD pipelines, container orchestration, cloud infrastructure, and monitoring systems.'),
('da', 'Data Analyst', 'Extracts insights from large datasets using SQL, Python, statistical methods, and dashboard visualization tools.')
ON DUPLICATE KEY UPDATE `jobrole_name`=VALUES(`jobrole_name`);

-- Seed Default Candidate (Clean fresh state)
INSERT INTO `users` (
    `user_id`, `user_name`, `email`, `first_name`, `last_name`, 
    `gender`, `current_title`, `location`, `phone`, `linkedin_url`, 
    `github_url`, `portfolio_url`, `degree`, `institute`, `duration`, 
    `graduation_year`, `profile_score`
) VALUES (
    1, 'hirushan', 'hirushan@gmail.com', 'Hirushan', 'Nimnada',
    'Male', '', '', '',
    '', '', '',
    '', '', '',
    '', 0
) ON DUPLICATE KEY UPDATE `first_name`=VALUES(`first_name`), `profile_score`=VALUES(`profile_score`);
