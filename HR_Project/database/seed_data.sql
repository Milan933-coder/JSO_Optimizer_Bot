-- ============================================================
-- JSO HR Intelligence Agent - Seed Data
-- ============================================================

-- HR Consultants
INSERT INTO hr_consultants (full_name, email, company, specialization) VALUES
('Sarah Mitchell', 'sarah.m@jso.com', 'JSO Platform', 'tech'),
('James Rodriguez', 'james.r@jso.com', 'JSO Platform', 'finance'),
('Priya Sharma', 'priya.s@jso.com', 'JSO Platform', 'tech');

-- Candidates
INSERT INTO candidates (full_name, email, phone, location, experience_years, current_role, current_company, expected_salary, availability, github_url, github_score, risk_score) VALUES
('Arjun Mehta',       'arjun.m@gmail.com',    '+91-9876543210', 'Mumbai',    6, 'Senior React Developer',    'TechCorp',       95000,  'immediate', 'https://github.com/arjunmehta',    8.7, 5),
('Emily Carter',      'emily.c@gmail.com',     '+1-4155552671',  'New York',  4, 'Frontend Developer',        'StartupXYZ',     85000,  '2_weeks',   'https://github.com/emilycarter',   7.2, 3),
('Rahul Singh',       'rahul.s@gmail.com',     '+91-9123456789', 'Bangalore', 7, 'Full Stack Engineer',       'Infosys',        110000, '1_month',   'https://github.com/rahulsingh',    9.1, 2),
('Sofia Fernandez',   'sofia.f@outlook.com',   '+34-612345678',  'Madrid',    3, 'React Developer',           'Agency Digital', 70000,  'immediate', 'https://github.com/sofiafernandez', 6.5, 8),
('Kevin Zhang',       'kevin.z@yahoo.com',     '+1-6502221234',  'San Jose',  8, 'Senior Full Stack Dev',     'Google',         150000, '1_month',   'https://github.com/kevinzhang',    9.5, 1),
('Amara Osei',        'amara.o@gmail.com',     '+233-244123456', 'Accra',     2, 'Junior Developer',          'Freelance',      45000,  'immediate', 'https://github.com/amaraosei',     5.8, 12),
('Lena Müller',       'lena.m@gmail.com',      '+49-15123456789','Berlin',    5, 'Python Backend Developer',  'SAP',            90000,  '2_weeks',   'https://github.com/lenamuller',    8.2, 4),
('Omar Hassan',       'omar.h@gmail.com',      '+20-1012345678', 'Cairo',     4, 'Node.js Developer',         'Freelance',      60000,  'immediate', 'https://github.com/omarhassan',    7.0, 15),
('Priya Nair',        'priya.n@gmail.com',     '+91-9988776655', 'Chennai',   6, 'Data Engineer',             'Wipro',          88000,  '2_weeks',   'https://github.com/priyanair',     8.9, 3),
('Jake Thompson',     'jake.t@gmail.com',      '+1-3125551234',  'Chicago',   1, 'Junior Frontend Dev',       'Agency Web',     55000,  'immediate', 'https://github.com/jakethompson',  4.5, 20),
('Mei Lin',           'mei.l@gmail.com',       '+86-13812345678','Shanghai',  9, 'Tech Lead',                 'Alibaba',        180000, '1_month',   'https://github.com/meilin',        9.8, 1),
('Carlos Vega',       'carlos.v@gmail.com',    '+52-5512345678', 'Mexico City',3,'Backend Developer',         'FinTech MX',     65000,  'immediate', 'https://github.com/carlosvega',    7.5, 6),
('Aisha Patel',       'aisha.p@gmail.com',     '+44-7700123456', 'London',    5, 'DevOps Engineer',           'Barclays',       100000, '2_weeks',   'https://github.com/aishapatel',    8.4, 2),
('David Kim',         'david.k@gmail.com',     '+82-1012345678', 'Seoul',     7, 'ML Engineer',               'Samsung',        130000, '1_month',   'https://github.com/davidkim',      9.3, 3),
('Nina Volkov',       'nina.v@gmail.com',      '+7-9161234567',  'Moscow',    4, 'QA Automation Engineer',    'Yandex',         75000,  'immediate', 'https://github.com/ninavolkov',    7.8, 5);

-- Skills
INSERT INTO skills (candidate_id, skill_name, proficiency_level, years_of_experience) VALUES
-- Arjun Mehta (id=1)
(1, 'React',        'expert',        6), (1, 'TypeScript',  'advanced',      5),
(1, 'Node.js',      'advanced',      4), (1, 'PostgreSQL',  'intermediate',  3),
(1, 'AWS',          'intermediate',  2), (1, 'Docker',      'beginner',      1),
-- Emily Carter (id=2)
(2, 'React',        'advanced',      4), (2, 'CSS',         'expert',        4),
(2, 'JavaScript',   'advanced',      4), (2, 'Figma',       'intermediate',  2),
(2, 'Vue.js',       'beginner',      1),
-- Rahul Singh (id=3)
(3, 'React',        'expert',        5), (3, 'Node.js',     'expert',        6),
(3, 'MongoDB',      'advanced',      5), (3, 'AWS',         'advanced',      4),
(3, 'Docker',       'advanced',      3), (3, 'Kubernetes',  'intermediate',  2),
-- Sofia Fernandez (id=4)
(4, 'React',        'intermediate',  3), (4, 'JavaScript',  'advanced',      3),
(4, 'HTML/CSS',     'expert',        3),
-- Kevin Zhang (id=5)
(5, 'React',        'expert',        7), (5, 'Node.js',     'expert',        8),
(5, 'Python',       'advanced',      5), (5, 'Kubernetes',  'expert',        4),
(5, 'AWS',          'expert',        6), (5, 'Docker',      'expert',        5),
(5, 'PostgreSQL',   'advanced',      4), (5, 'Redis',       'advanced',      3),
-- Amara Osei (id=6)
(6, 'JavaScript',   'intermediate',  2), (6, 'React',       'beginner',      1),
(6, 'HTML/CSS',     'intermediate',  2),
-- Lena Müller (id=7)
(7, 'Python',       'expert',        5), (7, 'Django',      'advanced',      4),
(7, 'PostgreSQL',   'advanced',      4), (7, 'REST APIs',   'advanced',      4),
(7, 'Docker',       'intermediate',  2), (7, 'AWS',         'beginner',      1),
-- Omar Hassan (id=8)
(8, 'Node.js',      'advanced',      4), (8, 'Express.js',  'advanced',      4),
(8, 'MongoDB',      'intermediate',  3), (8, 'REST APIs',   'advanced',      3),
-- Priya Nair (id=9)
(9, 'Python',       'expert',        6), (9, 'Apache Spark','advanced',      4),
(9, 'AWS',          'advanced',      4), (9, 'SQL',         'expert',        6),
(9, 'Airflow',      'intermediate',  2), (9, 'Kafka',       'intermediate',  2),
-- Jake Thompson (id=10)
(10,'JavaScript',   'intermediate',  1), (10,'React',       'beginner',      1),
(10,'HTML/CSS',     'advanced',      1),
-- Mei Lin (id=11)
(11,'React',        'expert',        8), (11,'Node.js',     'expert',        9),
(11,'Python',       'expert',        7), (11,'AWS',         'expert',        8),
(11,'Kubernetes',   'expert',        5), (11,'System Design','expert',       6),
-- Carlos Vega (id=12)
(12,'Node.js',      'advanced',      3), (12,'Python',      'intermediate',  2),
(12,'MongoDB',      'advanced',      3), (12,'REST APIs',   'advanced',      3),
-- Aisha Patel (id=13)
(13,'DevOps',       'expert',        5), (13,'AWS',         'expert',        4),
(13,'Docker',       'expert',        4), (13,'Kubernetes',  'advanced',      3),
(13,'CI/CD',        'expert',        4), (13,'Terraform',   'advanced',      3),
-- David Kim (id=14)
(14,'Python',       'expert',        7), (14,'TensorFlow',  'advanced',      4),
(14,'PyTorch',      'advanced',      3), (14,'SQL',         'advanced',      5),
(14,'AWS SageMaker','intermediate',  2), (14,'MLflow',      'intermediate',  2),
-- Nina Volkov (id=15)
(15,'Selenium',     'expert',        4), (15,'Python',      'advanced',      3),
(15,'JavaScript',   'intermediate',  3), (15,'Cypress',     'advanced',      3),
(15,'Jest',         'advanced',      2);

-- CVs (raw text for semantic search)
INSERT INTO cvs (candidate_id, raw_text) VALUES
(1, 'Arjun Mehta - Senior React Developer with 6 years of experience. Expert in React, TypeScript, and Node.js. Built scalable frontend architectures for fintech and e-commerce platforms at TechCorp. Strong understanding of performance optimization, state management with Redux and Zustand. Experience with AWS deployment, REST APIs, and PostgreSQL databases. Led a team of 3 frontend developers. Delivered 12 production applications. Open source contributor with 200+ GitHub stars.'),

(2, 'Emily Carter - Frontend Developer with 4 years of experience specializing in React and pixel-perfect UI implementation. Expert in CSS animations, responsive design, and accessibility standards. Worked with StartupXYZ to redesign their core product. Proficient in Figma to code workflows. Experienced with Vue.js and modern JavaScript. Strong communication skills, worked directly with design teams.'),

(3, 'Rahul Singh - Full Stack Engineer with 7 years of experience. Expert in React, Node.js, and MongoDB. Senior engineer at Infosys delivering enterprise-grade applications. Architected microservices systems on AWS. Deep experience with Docker and Kubernetes for container orchestration. Database optimization expert. Mentored junior developers. Delivered projects for banking, insurance, and healthcare sectors.'),

(4, 'Sofia Fernandez - React Developer with 3 years experience. Frontend specialist with strong HTML, CSS, and JavaScript foundations. Built multiple web applications for digital agencies across Europe. Intermediate React skills with hooks and context API. Looking to grow into full stack development.'),

(5, 'Kevin Zhang - Senior Full Stack Developer with 8 years at Google. Expert across the entire stack: React, Node.js, Python, PostgreSQL, and Redis. Kubernetes and AWS expert. Led platform migrations for Google internal tools. Designed systems serving millions of users. Open source maintainer with 2000+ GitHub stars. Architecture and system design specialist.'),

(6, 'Amara Osei - Junior Developer with 2 years experience. Self-taught JavaScript and React developer. Built 3 personal portfolio projects. Recently completed online bootcamp. Eager to learn and grow. Available for junior or internship positions.'),

(7, 'Lena Müller - Python Backend Developer with 5 years at SAP. Django and REST API specialist. Designed and maintained large-scale data processing pipelines. PostgreSQL database design expert. Docker containerization experience. AWS beginner. Python testing with pytest. Team player with good documentation habits.'),

(8, 'Omar Hassan - Node.js Developer with 4 years freelance experience. Built multiple REST APIs for clients across MENA region. Express.js and MongoDB expert. Experience with real-time applications using Socket.io. Self-motivated remote worker.'),

(9, 'Priya Nair - Data Engineer with 6 years at Wipro. Python and SQL expert. Built ETL pipelines using Apache Spark and Airflow. AWS data infrastructure including S3, Redshift, and Glue. Kafka stream processing experience. Delivered data solutions for retail and telecom clients.'),

(10,'Jake Thompson - Junior Frontend Developer with 1 year experience. HTML, CSS, and basic JavaScript knowledge. Completed React tutorials. Looking for first full-time role. Fast learner with a passion for UI design.'),

(11,'Mei Lin - Tech Lead with 9 years at Alibaba. Led teams of 12 engineers. Full stack expert: React, Node.js, Python. AWS and Kubernetes at massive scale. System design and architecture specialist. Authored internal engineering blogs. Mentored 20+ engineers. Deep experience in distributed systems, caching, and high-availability architecture.'),

(12,'Carlos Vega - Backend Developer with 3 years in FinTech. Node.js and Python for financial APIs. MongoDB database design. REST API development. Experience with payment integrations and compliance requirements. Bilingual English and Spanish.'),

(13,'Aisha Patel - DevOps Engineer with 5 years at Barclays. AWS certified solutions architect. Docker and Kubernetes expert. CI/CD pipeline design with Jenkins and GitHub Actions. Terraform infrastructure as code. Security-focused cloud deployments. Reduced deployment time by 60% at Barclays.'),

(14,'David Kim - Machine Learning Engineer with 7 years at Samsung AI Lab. TensorFlow and PyTorch specialist. Deployed production ML models for computer vision and NLP. AWS SageMaker for model deployment. MLflow for experiment tracking. SQL and data pipeline experience. Published 3 research papers.'),

(15,'Nina Volkov - QA Automation Engineer with 4 years at Yandex. Selenium and Cypress testing frameworks expert. Python and JavaScript for test automation. Built comprehensive test suites for e-commerce platform. Jest unit testing. Reduced bug escape rate by 40%. Strong analytical and debugging skills.');

-- Job Descriptions
INSERT INTO job_descriptions (title, company, location, job_type, experience_required, salary_min, salary_max, description, required_skills, nice_to_have_skills, posted_by) VALUES
('Senior React Developer', 'FinTech Solutions', 'Remote', 'full_time', 5,
 90000, 130000,
 'We are looking for a Senior React Developer to lead the frontend development of our trading platform. You will architect scalable React applications, work closely with backend teams, and mentor junior developers. Must have strong TypeScript skills and experience with financial applications. Knowledge of state management patterns is essential. You will be building real-time dashboards handling live market data.',
 'React,TypeScript,Node.js,PostgreSQL,AWS', 'Docker,Redux,WebSockets', 1),

('Full Stack Engineer', 'E-Commerce Giant', 'New York', 'full_time', 4,
 100000, 140000,
 'Join our engineering team to build the next generation of our e-commerce platform. You will work on both frontend React components and backend Node.js services. Experience with MongoDB or PostgreSQL required. Must be comfortable with AWS infrastructure and Docker containers. Agile team environment with strong code review culture.',
 'React,Node.js,MongoDB,AWS,Docker', 'Kubernetes,Redis,TypeScript', 1),

('Python Backend Developer', 'Data Analytics Corp', 'Berlin', 'full_time', 3,
 80000, 110000,
 'Seeking a Python Backend Developer to build robust data processing APIs. You will design REST APIs using Django or FastAPI, manage PostgreSQL databases, and integrate with various data sources. Docker experience required. AWS knowledge helpful. Strong understanding of data structures and algorithms expected.',
 'Python,Django,PostgreSQL,REST APIs,Docker', 'AWS,FastAPI,Redis', 2),

('DevOps Engineer', 'Cloud Startup', 'London', 'full_time', 4,
 95000, 130000,
 'We need a DevOps Engineer to manage our growing cloud infrastructure. AWS certification preferred. Must have strong Kubernetes and Docker skills. CI/CD pipeline design experience essential. Terraform for infrastructure as code. Security-conscious approach to cloud deployments. Experience with monitoring tools like Datadog or Prometheus.',
 'AWS,Docker,Kubernetes,CI/CD,Terraform', 'Datadog,Prometheus,Python', 1),

('Machine Learning Engineer', 'AI Research Lab', 'Remote', 'full_time', 5,
 120000, 170000,
 'Seeking an ML Engineer to develop and deploy production machine learning models. TensorFlow or PyTorch required. Experience with NLP or computer vision preferred. AWS SageMaker or similar cloud ML platform experience. Strong Python and SQL skills. Ability to work with large datasets and optimize model performance for production.',
 'Python,TensorFlow,PyTorch,SQL,AWS', 'MLflow,Spark,Docker', 2);

-- Applications
INSERT INTO applications (candidate_id, job_id, status, match_score, hr_notes) VALUES
(1, 1, 'shortlisted',  0.94, 'Excellent React skills, strong TypeScript background. Invite for technical interview.'),
(2, 1, 'reviewed',     0.72, 'Good frontend skills but missing TypeScript depth. Consider for junior role.'),
(3, 1, 'shortlisted',  0.88, 'Full stack profile, very strong overall. Check Node.js depth.'),
(5, 1, 'shortlisted',  0.96, 'Outstanding profile. Top candidate. Schedule ASAP.'),
(4, 1, 'rejected',     0.51, 'Not enough experience for senior role. Reapply in 2 years.'),
(3, 2, 'shortlisted',  0.91, 'Perfect fit for full stack role. Strong MongoDB experience.'),
(5, 2, 'reviewed',     0.89, 'Overqualified but interested. Discuss salary expectations.'),
(8, 2, 'pending',      0.78, NULL),
(12,2, 'pending',      0.74, NULL),
(7, 3, 'shortlisted',  0.92, 'Ideal Python backend profile. Strong Django and PostgreSQL.'),
(9, 3, 'reviewed',     0.65, 'Data engineering background, not pure backend. But Python is strong.'),
(12,3, 'pending',      0.71, NULL),
(13,4, 'shortlisted',  0.97, 'Perfect DevOps match. AWS certified, Terraform expert.'),
(3, 4, 'reviewed',     0.62, 'Has Docker/Kubernetes but lacks DevOps focus.'),
(14,5, 'shortlisted',  0.95, 'Top ML engineer. Published researcher. Strong candidate.'),
(11,5, 'reviewed',     0.83, 'Tech lead background, ML is secondary. Discuss role fit.');
