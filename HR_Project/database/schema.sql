-- ============================================================
-- JSO HR Intelligence Agent - Database Schema
-- ============================================================

-- Candidates Table
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    location TEXT,
    experience_years INTEGER DEFAULT 0,
    current_role TEXT,
    current_company TEXT,
    expected_salary INTEGER,
    currency TEXT DEFAULT 'USD',
    availability TEXT DEFAULT 'immediate', -- immediate, 2_weeks, 1_month
    profile_status TEXT DEFAULT 'active',  -- active, inactive, banned, flagged
    risk_score INTEGER DEFAULT 0,          -- 0-100, higher = riskier
    github_url TEXT,
    github_score REAL DEFAULT 0.0,         -- 0-10 rating
    linkedin_url TEXT,
    portfolio_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Skills Table
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    skill_name TEXT NOT NULL,
    proficiency_level TEXT DEFAULT 'intermediate', -- beginner, intermediate, advanced, expert
    years_of_experience INTEGER DEFAULT 1,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

-- CVs Table (stores raw CV text for embedding)
CREATE TABLE IF NOT EXISTS cvs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER UNIQUE NOT NULL,
    raw_text TEXT NOT NULL,
    file_url TEXT,
    embedding TEXT,  -- JSON-serialized embedding vector
    last_parsed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

-- Job Descriptions Table
CREATE TABLE IF NOT EXISTS job_descriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    job_type TEXT DEFAULT 'full_time', -- full_time, part_time, contract, remote
    experience_required INTEGER DEFAULT 0,
    salary_min INTEGER,
    salary_max INTEGER,
    currency TEXT DEFAULT 'USD',
    description TEXT NOT NULL,
    required_skills TEXT,  -- comma-separated
    nice_to_have_skills TEXT,
    embedding TEXT,  -- JSON-serialized embedding vector
    status TEXT DEFAULT 'open', -- open, closed, paused
    posted_by INTEGER,  -- HR consultant ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (posted_by) REFERENCES hr_consultants(id)
);

-- HR Consultants Table
CREATE TABLE IF NOT EXISTS hr_consultants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    company TEXT,
    specialization TEXT,  -- tech, finance, marketing, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Applications Table
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, reviewed, shortlisted, rejected, hired
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    match_score REAL DEFAULT 0.0,  -- cosine similarity score 0-1
    hr_notes TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (job_id) REFERENCES job_descriptions(id)
);

-- Query History Table (tracks HR agent queries for learning)
CREATE TABLE IF NOT EXISTS query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hr_id INTEGER,
    natural_language_query TEXT NOT NULL,
    generated_sql TEXT,
    query_type TEXT,  -- sql, semantic, hybrid
    result_count INTEGER DEFAULT 0,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hr_id) REFERENCES hr_consultants(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_candidates_location ON candidates(location);
CREATE INDEX IF NOT EXISTS idx_candidates_experience ON candidates(experience_years);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(profile_status);
CREATE INDEX IF NOT EXISTS idx_skills_candidate ON skills(candidate_id);
CREATE INDEX IF NOT EXISTS idx_applications_candidate ON applications(candidate_id);
CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
