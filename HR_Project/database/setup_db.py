"""
setup_db.py
===========
Creates and seeds the local SQLite database for the JSO HR Intelligence Agent.
Run this file once to initialize the database.

Usage:
    python database/setup_db.py
"""

import sqlite3
import os
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "jso_hr.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
SEED_PATH = os.path.join(os.path.dirname(__file__), "seed_data.sql")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # allows dict-like row access
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_sql_file(conn: sqlite3.Connection, filepath: str) -> None:
    """Reads and executes a .sql file against the given connection."""
    with open(filepath, "r") as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
    print(f"  ✅ Executed: {os.path.basename(filepath)}")


def _is_db_empty(conn: sqlite3.Connection) -> bool:
    try:
        count = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        return count == 0
    except sqlite3.Error:
        return True


def seed_with_faker(
    conn: sqlite3.Connection,
    num_candidates: int = 30,
    num_jobs: int = 8,
    num_hr: int = 4,
) -> None:
    """
    Seeds the database with realistic fake data using Faker.
    """
    try:
        from faker import Faker
    except ImportError as e:
        raise ImportError("faker not installed. Run: pip install faker") from e

    fake = Faker()
    cursor = conn.cursor()

    locations = [
        "London", "New York", "San Francisco", "Bangalore", "Mumbai",
        "Berlin", "Toronto", "Singapore", "Sydney", "Amsterdam",
    ]
    roles = [
        "Frontend Developer", "Backend Developer", "Full Stack Engineer",
        "Data Scientist", "DevOps Engineer", "QA Engineer",
    ]
    job_titles = [
        "Senior Frontend Engineer", "React Developer", "Backend Engineer",
        "Full Stack Developer", "Data Analyst", "DevOps Specialist",
    ]
    skills_pool = [
        "React", "JavaScript", "TypeScript", "Node.js", "Python",
        "Django", "Flask", "FastAPI", "SQL", "PostgreSQL",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP",
        "HTML", "CSS", "Tailwind", "Redux", "Next.js",
    ]
    specializations = ["tech", "finance", "marketing", "product", "design"]
    job_types = ["full_time", "part_time", "contract", "remote"]
    availability_options = ["immediate", "2_weeks", "1_month"]
    profile_status_options = ["active", "active", "active", "inactive"]

    # HR consultants
    hr_ids = []
    for _ in range(num_hr):
        cursor.execute(
            """
            INSERT INTO hr_consultants (full_name, email, company, specialization)
            VALUES (?, ?, ?, ?)
            """,
            (
                fake.name(),
                fake.unique.email(),
                fake.company(),
                random.choice(specializations),
            ),
        )
        hr_ids.append(cursor.lastrowid)

    # Candidates
    candidate_rows = []
    for _ in range(num_candidates):
        exp_years = random.randint(0, 12)
        expected_salary = random.randrange(40000, 160000, 5000)
        cursor.execute(
            """
            INSERT INTO candidates (
                full_name, email, phone, location, experience_years,
                current_role, current_company, expected_salary, currency,
                availability, profile_status, risk_score, github_url,
                github_score, linkedin_url, portfolio_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fake.name(),
                fake.unique.email(),
                fake.phone_number(),
                random.choice(locations),
                exp_years,
                random.choice(roles),
                fake.company(),
                expected_salary,
                "USD",
                random.choice(availability_options),
                random.choice(profile_status_options),
                random.randint(0, 35),
                f"https://github.com/{fake.user_name()}",
                round(random.uniform(2.5, 9.5), 1),
                f"https://linkedin.com/in/{fake.user_name()}",
                fake.url(),
            ),
        )
        candidate_rows.append({"id": cursor.lastrowid, "exp": exp_years})

    # Skills + CVs
    for cand in candidate_rows:
        num_skills = random.randint(3, 8)
        chosen_skills = random.sample(skills_pool, k=num_skills)

        for skill in chosen_skills:
            yrs = max(1, min(cand["exp"], random.randint(1, 8)))
            if yrs <= 1:
                prof = "beginner"
            elif yrs <= 3:
                prof = "intermediate"
            elif yrs <= 5:
                prof = "advanced"
            else:
                prof = "expert"
            cursor.execute(
                """
                INSERT INTO skills (candidate_id, skill_name, proficiency_level, years_of_experience)
                VALUES (?, ?, ?, ?)
                """,
                (cand["id"], skill, prof, yrs),
            )

        cv_text = (
            f"{fake.name()} is a {random.choice(roles)} with {cand['exp']} years of experience. "
            f"Skills: {', '.join(chosen_skills)}. "
            "Projects include web apps, APIs, and cloud deployments."
        )
        cursor.execute(
            """
            INSERT INTO cvs (candidate_id, raw_text, file_url)
            VALUES (?, ?, ?)
            """,
            (cand["id"], cv_text, fake.url()),
        )

    # Job descriptions
    job_ids = []
    for _ in range(num_jobs):
        req_skills = random.sample(skills_pool, k=5)
        nice_skills = random.sample(skills_pool, k=3)
        exp_req = random.randint(0, 7)
        salary_min = random.randrange(45000, 120000, 5000)
        salary_max = salary_min + random.randrange(15000, 60000, 5000)
        description = (
            f"We are looking for a {random.choice(job_titles)}. "
            "Responsibilities include building features and collaborating with teams. "
            f"Required skills: {', '.join(req_skills)}. "
            f"Nice to have: {', '.join(nice_skills)}."
        )
        cursor.execute(
            """
            INSERT INTO job_descriptions (
                title, company, location, job_type, experience_required,
                salary_min, salary_max, currency, description,
                required_skills, nice_to_have_skills, status, posted_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                random.choice(job_titles),
                fake.company(),
                random.choice(locations),
                random.choice(job_types),
                exp_req,
                salary_min,
                salary_max,
                "USD",
                description,
                ", ".join(req_skills),
                ", ".join(nice_skills),
                "open",
                random.choice(hr_ids),
            ),
        )
        job_ids.append(cursor.lastrowid)

    # Applications
    for job_id in job_ids:
        applied_candidates = random.sample(
            candidate_rows, k=random.randint(4, min(10, len(candidate_rows)))
        )
        for cand in applied_candidates:
            cursor.execute(
                """
                INSERT INTO applications (candidate_id, job_id, status, match_score, hr_notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    cand["id"],
                    job_id,
                    random.choice(["pending", "reviewed", "shortlisted", "rejected"]),
                    round(random.uniform(0.2, 0.95), 2),
                    fake.sentence(nb_words=8),
                ),
            )

    conn.commit()
    print("  Seeded database with Faker data.")


def setup_database(reset: bool = False, use_faker: bool | None = None) -> None:
    """
    Initializes the database.
    If reset=True, drops the existing DB and recreates it fresh.
    """
    if use_faker is None:
        use_faker = os.getenv("USE_FAKER_SEED", "false").lower() in ("1", "true", "yes")

    if reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing database.")

    if os.path.exists(DB_PATH) and not reset:
        conn = get_connection()
        if _is_db_empty(conn):
            print("Database exists but is empty. Seeding with Faker data...")
            seed_with_faker(conn)
            conn.close()
            return
        conn.close()
        print(f"Database already exists at: {DB_PATH}")
        print("Use setup_database(reset=True) to recreate.")
        return

    print("Setting up JSO HR Intelligence Database...")
    conn = get_connection()

    try:
        print("Running schema...")
        run_sql_file(conn, SCHEMA_PATH)

        if use_faker:
            print("Seeding with Faker data...")
            seed_with_faker(conn)
        else:
            print("Running seed data...")
            run_sql_file(conn, SEED_PATH)

        # Quick verification
        cursor = conn.cursor()
        tables = ["candidates", "skills", "cvs", "job_descriptions", "applications", "hr_consultants"]
        print("Database verification:")
        for table in tables:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table:<25} -> {count} rows")

        print(f"Database ready at: {DB_PATH}")

    except Exception as e:
        conn.rollback()
        print(f"Error during setup: {e}")
        raise
    finally:
        conn.close()


def get_table_schema(table_name: str) -> str:
    """Returns the CREATE TABLE statement for a given table (useful for agent context)."""
    conn = get_connection()
    cursor = conn.cursor()
    result = cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    conn.close()
    return result[0] if result else f"Table '{table_name}' not found."


def get_full_schema_context() -> str:
    """
    Returns the full schema as a string for injecting into Claude's context.
    This tells the agent what tables and columns exist.
    """
    conn = get_connection()
    cursor = conn.cursor()
    tables = cursor.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()

    schema_text = "DATABASE SCHEMA (SQLite):\n\n"
    for table in tables:
        schema_text += f"{table['sql']};\n\n"
    return schema_text


if __name__ == "__main__":
    setup_database(reset=True)
