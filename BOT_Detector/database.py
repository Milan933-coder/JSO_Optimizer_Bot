"""
database.py — Sentinel-JSO Dummy Database (Faker-powered)
Generates a large realistic dataset:
  - 60 HR users  (mix of normal, suspicious, high-risk)
  - 140 Job Seekers (mix of normal, suspicious, high-risk, bot clusters)
  - 800+ activity logs
  - 500+ job applications
  - 200+ job posts (some with phishing)
  - 15 account clusters (bot networks)
"""

import sqlite3
import json
import os
import random
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DB_PATH = "sentinel_jso.db"

# ── Realistic scam/phishing content pools ─────────────────────────────────────
SCAM_JOB_TITLES = [
    "Urgent Crypto Trader Needed", "Work From Home $5000/wk",
    "Easy Money Remote Job", "Immediate Hire – No Experience",
    "Online Data Entry $200/hr", "Mystery Shopper Wanted",
    "Pyramid Sales Representative", "Bitcoin Investment Advisor",
]
SCAM_DESCRIPTIONS = [
    "Click here to apply now: bit.ly/get-rich-{n}",
    "Send your CV to earn.fast@scam{n}.ru immediately",
    "Apply via t.me/jobscam_{n}_bot — urgent!",
    "Visit http://totallylegit{n}.xyz to register",
    "WhatsApp +1-555-{n:04d} for instant job offer",
]
LEGIT_JOB_TITLES = [
    "Senior Software Engineer", "Product Manager", "Data Analyst",
    "UX Designer", "DevOps Engineer", "Marketing Manager",
    "Backend Developer", "QA Engineer", "Scrum Master",
    "Full Stack Developer", "Data Scientist", "Cloud Architect",
    "Mobile Developer", "Frontend Engineer", "Business Analyst",
]
ACTIONS = ["apply_job", "login", "view_profile", "upload_cv",
           "message_recruiter", "save_job", "scrape_content", "post_job"]
SHARED_IPS = [fake.ipv4() for _ in range(8)]
SHARED_DEVICES = [f"DEV_{fake.lexify('????').upper()}" for _ in range(10)]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY,
            name            TEXT,
            email           TEXT,
            role            TEXT,
            company         TEXT,
            location        TEXT,
            joined_date     TEXT,
            linkedin_url    TEXT,
            github_url      TEXT,
            risk_score      REAL DEFAULT 0.0,
            risk_level      TEXT DEFAULT 'Normal',
            flagged         INTEGER DEFAULT 0,
            flag_reason     TEXT
        );

        CREATE TABLE IF NOT EXISTS activity_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER,
            action          TEXT,
            timestamp       TEXT,
            ip_address      TEXT,
            device_id       TEXT,
            metadata        TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS job_applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            seeker_id       INTEGER,
            job_title       TEXT,
            company         TEXT,
            applied_at      TEXT,
            status          TEXT
        );

        CREATE TABLE IF NOT EXISTS job_posts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            hr_id           INTEGER,
            title           TEXT,
            description     TEXT,
            posted_at       TEXT,
            contains_phishing INTEGER DEFAULT 0,
            scam_score      REAL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS account_clusters (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_id      TEXT,
            user_id         INTEGER,
            shared_ip       TEXT,
            shared_device   TEXT
        );
    """)
    conn.commit()


# ── Risk profile helpers ──────────────────────────────────────────────────────

def normal_profile():
    score = round(random.uniform(0.02, 0.38), 3)
    return score, "Normal", 0, None

def suspicious_profile():
    score = round(random.uniform(0.41, 0.68), 3)
    reasons = [
        "Multiple logins from different countries in 24h",
        "Unusual posting frequency detected",
        "Profile data inconsistencies found",
        "Rapid job application bursts detected",
        "Unverified LinkedIn profile",
    ]
    return score, "Suspicious", 1, random.choice(reasons)

def high_risk_profile():
    score = round(random.uniform(0.71, 0.99), 3)
    reasons = [
        f"{random.randint(80,200)} job applications in {random.randint(3,8)} minutes; bot-like behavior",
        f"Phishing links in {random.randint(2,6)} job posts; shared device with {random.randint(4,10)} accounts",
        f"Coordinated bot network; {random.randint(10,25)} accounts with shared IP",
        f"Automated scraping detected; bot probability {round(random.uniform(0.88,0.99),2)}",
        "Duplicate resume embeddings across 8 accounts; same device fingerprint",
    ]
    return score, "High Risk", 1, random.choice(reasons)

def pick_risk():
    """70% normal, 18% suspicious, 12% high-risk"""
    r = random.random()
    if r < 0.70:
        return normal_profile()
    elif r < 0.88:
        return suspicious_profile()
    else:
        return high_risk_profile()


# ── User generators ───────────────────────────────────────────────────────────

def generate_hrs(start_id=1, count=60):
    users = []
    for i in range(count):
        uid     = start_id + i
        name    = fake.name()
        email   = fake.company_email()
        company = fake.company()
        loc     = f"{fake.city()}, {fake.country()}"
        joined  = fake.date_between(start_date="-3y", end_date="today").isoformat()
        linkedin = f"linkedin.com/in/{fake.user_name()}"
        score, level, flagged, reason = pick_risk()
        users.append((uid, name, email, "HR", company, loc, joined,
                      linkedin, None, score, level, flagged, reason))
    return users


def generate_seekers(start_id=200, count=140):
    users = []
    for i in range(count):
        uid     = start_id + i
        name    = fake.name()
        email   = fake.email()
        loc     = f"{fake.city()}, {fake.country()}"
        joined  = fake.date_between(start_date="-3y", end_date="today").isoformat()
        linkedin = f"linkedin.com/in/{fake.user_name()}" if random.random() > 0.2 else None
        github   = f"github.com/{fake.user_name()}"      if random.random() > 0.3 else None
        score, level, flagged, reason = pick_risk()
        users.append((uid, name, email, "JobSeeker", None, loc, joined,
                      linkedin, github, score, level, flagged, reason))
    return users


# ── Activity log generators ───────────────────────────────────────────────────

def generate_logs_for_user(user_id, risk_level, role):
    logs = []
    n_logs = {
        "Normal":    random.randint(2, 8),
        "Suspicious": random.randint(8, 18),
        "High Risk": random.randint(20, 50),
    }[risk_level]

    for _ in range(n_logs):
        if risk_level == "High Risk" and random.random() < 0.5:
            action = random.choice(["apply_job", "scrape_content", "apply_job", "apply_job"])
            ip     = random.choice(SHARED_IPS)
            device = random.choice(SHARED_DEVICES)
            meta   = json.dumps({"speed": "bulk", "bot_prob": round(random.uniform(0.85, 0.99), 2)})
        elif risk_level == "Suspicious" and random.random() < 0.4:
            action = random.choice(["login", "login", "view_profile"])
            ip     = fake.ipv4()
            device = fake.lexify("DEV_????").upper()
            meta   = json.dumps({"country": fake.country(), "anomaly": "multi-region"})
        else:
            action = random.choice(ACTIONS)
            ip     = fake.ipv4()
            device = fake.lexify("DEV_????").upper()
            meta   = json.dumps({"job_id": random.randint(1, 200)})

        ts = fake.date_time_between(
            start_date="-1y", end_date="now"
        ).isoformat(sep=" ", timespec="seconds")
        logs.append((user_id, action, ts, ip, device, meta))

    return logs


# ── Job application generators ────────────────────────────────────────────────

def generate_applications_for_seeker(seeker_id, risk_level):
    from datetime import timedelta, datetime
    apps = []
    n = {
        "Normal":    random.randint(1, 5),
        "Suspicious": random.randint(5, 20),
        "High Risk": random.randint(80, 200),
    }[risk_level]

    base_time = fake.date_time_between(start_date="-6m", end_date="now")
    statuses  = ["pending", "reviewed", "accepted", "rejected", "flagged"]
    weights = {
        "Normal":    [0.4, 0.3, 0.2, 0.1, 0.0],
        "Suspicious": [0.3, 0.2, 0.1, 0.2, 0.2],
        "High Risk":  [0.0, 0.0, 0.0, 0.2, 0.8],
    }

    for i in range(n):
        title   = random.choice(LEGIT_JOB_TITLES)
        company = fake.company()
        if risk_level == "High Risk":
            ts = (base_time + timedelta(seconds=i * random.randint(5, 15))).isoformat(
                sep=" ", timespec="seconds"
            )
        else:
            ts = fake.date_time_between(
                start_date="-6m", end_date="now"
            ).isoformat(sep=" ", timespec="seconds")

        status = random.choices(statuses, weights=weights[risk_level])[0]
        apps.append((seeker_id, title, company, ts, status))

    return apps


# ── Job post generators ───────────────────────────────────────────────────────

def generate_posts_for_hr(hr_id, risk_level):
    posts = []
    n = {
        "Normal":    random.randint(1, 4),
        "Suspicious": random.randint(3, 8),
        "High Risk": random.randint(5, 12),
    }[risk_level]

    for i in range(n):
        is_scam = (
            (risk_level == "High Risk"   and random.random() < 0.7) or
            (risk_level == "Suspicious"  and random.random() < 0.25)
        )

        if is_scam:
            title  = random.choice(SCAM_JOB_TITLES)
            desc   = random.choice(SCAM_DESCRIPTIONS).format(n=random.randint(100, 999))
            scam_s = round(random.uniform(0.72, 0.99), 3)
            phish  = 1
        else:
            title  = random.choice(LEGIT_JOB_TITLES)
            desc   = fake.paragraph(nb_sentences=3)
            scam_s = round(random.uniform(0.0, 0.15), 3)
            phish  = 0

        ts = fake.date_time_between(
            start_date="-1y", end_date="now"
        ).isoformat(sep=" ", timespec="seconds")
        posts.append((hr_id, title, desc, ts, phish, scam_s))

    return posts


# ── Bot cluster generators ────────────────────────────────────────────────────

def generate_clusters(high_risk_ids):
    """Assign high-risk users into 15 overlapping bot clusters."""
    clusters = []
    cluster_count = 15
    ids = list(high_risk_ids)
    random.shuffle(ids)

    for c in range(cluster_count):
        cluster_id = f"C{c+1:02d}"
        shared_ip  = random.choice(SHARED_IPS)
        shared_dev = random.choice(SHARED_DEVICES)
        size = random.randint(3, min(10, len(ids)))
        members = random.sample(ids, size)
        for uid in members:
            clusters.append((cluster_id, uid, shared_ip, shared_dev))

    return clusters


# ── Main init ─────────────────────────────────────────────────────────────────

def init_db():
    conn = get_connection()
    create_tables(conn)
    c = conn.cursor()

    print("Generating users with Faker...")
    hrs     = generate_hrs(start_id=1,   count=60)
    seekers = generate_seekers(start_id=200, count=140)
    all_users = hrs + seekers

    c.executemany("""
        INSERT OR IGNORE INTO users
        (id,name,email,role,company,location,joined_date,linkedin_url,
         github_url,risk_score,risk_level,flagged,flag_reason)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, all_users)
    print(f"  {len(hrs)} HR users, {len(seekers)} job seekers")

    print("Generating activity logs...")
    all_logs = []
    for u in all_users:
        uid, risk_level, role = u[0], u[10], u[3]
        all_logs.extend(generate_logs_for_user(uid, risk_level, role))

    c.executemany("""
        INSERT INTO activity_logs (user_id,action,timestamp,ip_address,device_id,metadata)
        VALUES (?,?,?,?,?,?)
    """, all_logs)
    print(f"  {len(all_logs)} activity logs")

    print("Generating job applications...")
    all_apps = []
    for u in seekers:
        uid, risk_level = u[0], u[10]
        all_apps.extend(generate_applications_for_seeker(uid, risk_level))

    c.executemany("""
        INSERT INTO job_applications (seeker_id,job_title,company,applied_at,status)
        VALUES (?,?,?,?,?)
    """, all_apps)
    print(f"  {len(all_apps)} job applications")

    print("Generating job posts...")
    all_posts = []
    for u in hrs:
        uid, risk_level = u[0], u[10]
        all_posts.extend(generate_posts_for_hr(uid, risk_level))

    c.executemany("""
        INSERT INTO job_posts (hr_id,title,description,posted_at,contains_phishing,scam_score)
        VALUES (?,?,?,?,?,?)
    """, all_posts)
    print(f"  {len(all_posts)} job posts")

    print("Generating bot clusters...")
    high_risk_ids = [u[0] for u in all_users if u[10] == "High Risk"]
    clusters = generate_clusters(high_risk_ids)
    c.executemany("""
        INSERT INTO account_clusters (cluster_id,user_id,shared_ip,shared_device)
        VALUES (?,?,?,?)
    """, clusters)
    print(f"  {len(clusters)} cluster memberships across 15 clusters")

    conn.commit()
    conn.close()

    print(f"\nDatabase ready at '{DB_PATH}'")
    print(f"  Total users      : {len(all_users)}")
    print(f"  Activity logs    : {len(all_logs)}")
    print(f"  Job applications : {len(all_apps)}")
    print(f"  Job posts        : {len(all_posts)}")
    print(f"  Cluster records  : {len(clusters)}")


# ── Query helpers (unchanged API — app.py calls these) ────────────────────────

def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY risk_score DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_by_id(user_id: int):
    conn = get_connection()
    user     = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    logs     = conn.execute(
        "SELECT * FROM activity_logs WHERE user_id=? ORDER BY timestamp DESC", (user_id,)
    ).fetchall()
    apps     = conn.execute(
        "SELECT * FROM job_applications WHERE seeker_id=? ORDER BY applied_at DESC", (user_id,)
    ).fetchall()
    posts    = conn.execute(
        "SELECT * FROM job_posts WHERE hr_id=? ORDER BY posted_at DESC", (user_id,)
    ).fetchall()
    clusters = conn.execute(
        "SELECT * FROM account_clusters WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    if not user:
        return None
    return {
        "user":     dict(user),
        "logs":     [dict(r) for r in logs],
        "apps":     [dict(r) for r in apps],
        "posts":    [dict(r) for r in posts],
        "clusters": [dict(r) for r in clusters],
    }


def get_flagged_users():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM users WHERE flagged=1 ORDER BY risk_score DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_connection()
    total      = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    flagged    = conn.execute("SELECT COUNT(*) FROM users WHERE flagged=1").fetchone()[0]
    high_risk  = conn.execute("SELECT COUNT(*) FROM users WHERE risk_level='High Risk'").fetchone()[0]
    suspicious = conn.execute("SELECT COUNT(*) FROM users WHERE risk_level='Suspicious'").fetchone()[0]
    phishing   = conn.execute("SELECT COUNT(*) FROM job_posts WHERE contains_phishing=1").fetchone()[0]
    total_apps = conn.execute("SELECT COUNT(*) FROM job_applications").fetchone()[0]
    total_logs = conn.execute("SELECT COUNT(*) FROM activity_logs").fetchone()[0]
    clusters   = conn.execute(
        "SELECT COUNT(DISTINCT cluster_id) FROM account_clusters"
    ).fetchone()[0]
    conn.close()
    return {
        "total": total, "flagged": flagged, "high_risk": high_risk,
        "suspicious": suspicious, "phishing_posts": phishing,
        "total_applications": total_apps, "total_logs": total_logs,
        "bot_clusters": clusters,
    }


if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
