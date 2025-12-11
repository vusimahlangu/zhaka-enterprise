from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import jwt
import hashlib
import random
import string
import os
from functools import wraps

app = Flask(__name__, static_folder='../frontend')
CORS(app)

app.config['SECRET_KEY'] = 'zion-apostolic-swaziland-secret-2025'
app.config['JWT_SECRET'] = 'zion-apostolic-jwt-secret-2025'

# ============ DATABASE SETUP ============
DB_PATH = 'zion_apostolic_swaziland.db'

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # CHURCH INFO TABLE
    c.execute('''
        CREATE TABLE IF NOT EXISTS church_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT "Zion Apostolic Swaziland Church of South Africa",
            npo_number TEXT DEFAULT "2023/757388/08",
            motto TEXT DEFAULT "Building Faith, Unity, and the Future of Our Youth",
            contact_phone TEXT DEFAULT "072 276 7670",
            contact_email TEXT DEFAULT "youth@zionchurch.org.za",
            headquarters TEXT DEFAULT "All National Branches, South Africa",
            founded_year INTEGER DEFAULT 1985,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default church info
    c.execute('''
        INSERT OR IGNORE INTO church_info (name, npo_number, motto) 
        VALUES (?, ?, ?)
    ''', (
        "Zion Apostolic Swaziland Church of South Africa",
        "2023/757388/08",
        "Building Faith, Unity, and the Future of Our Youth"
    ))
    
    # USERS TABLE (Extended)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            id_number TEXT UNIQUE NOT NULL,
            date_of_birth DATE NOT NULL,
            gender TEXT NOT NULL,
            marital_status TEXT,
            
            -- Contact Information
            address TEXT,
            city TEXT,
            province TEXT,
            postal_code TEXT,
            
            -- Church Information
            membership_number TEXT UNIQUE,
            membership_date DATE DEFAULT CURRENT_DATE,
            membership_status TEXT DEFAULT 'active',
            membership_fee_paid BOOLEAN DEFAULT 0,
            last_fee_payment DATE,
            branch_name TEXT,  -- Local branch name
            
            -- Spiritual Information
            baptism_date DATE,
            baptism_location TEXT,
            previous_church TEXT,
            spiritual_gifts TEXT,
            ministries TEXT,
            department TEXT,
            
            -- App Settings
            push_token TEXT,
            notification_enabled BOOLEAN DEFAULT 1,
            two_factor_enabled BOOLEAN DEFAULT 0,
            profile_photo TEXT,
            
            -- Referral System
            referral_code TEXT UNIQUE,
            referred_by TEXT,
            total_referrals INTEGER DEFAULT 0,
            referral_earnings DECIMAL(10,2) DEFAULT 0,
            
            -- System
            role TEXT DEFAULT 'member',
            status TEXT DEFAULT 'active',
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # BRANCHES TABLE
    c.execute('''
        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_code TEXT UNIQUE,
            branch_name TEXT NOT NULL,
            province TEXT NOT NULL,
            city TEXT NOT NULL,
            address TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            established_date DATE,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default branches (9 provinces)
    provinces = [
        ('EC', 'Eastern Cape', 'Gqeberha'),
        ('FS', 'Free State', 'Bloemfontein'),
        ('GP', 'Gauteng', 'Johannesburg'),
        ('KZN', 'KwaZulu-Natal', 'Durban'),
        ('LP', 'Limpopo', 'Polokwane'),
        ('MP', 'Mpumalanga', 'Mbombela'),
        ('NW', 'North West', 'Mahikeng'),
        ('NC', 'Northern Cape', 'Kimberley'),
        ('WC', 'Western Cape', 'Cape Town')
    ]
    
    for i, (code, province, city) in enumerate(provinces, 1):
        c.execute('''
            INSERT OR IGNORE INTO branches (branch_code, branch_name, province, city)
            VALUES (?, ?, ?, ?)
        ''', (
            f'ZAS-{code}',
            f'Zion Apostolic Swaziland Church - {province}',
            province,
            city
        ))
    
    # SERVICES TABLE
    c.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_type TEXT NOT NULL,  -- sunday_morning, sunday_evening, wednesday, friday, special
            service_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME,
            title TEXT,
            preacher TEXT,
            bible_reading TEXT,
            branch_id INTEGER,
            expected_attendance INTEGER,
            actual_attendance INTEGER,
            notes TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(id)
        )
    ''')
    
    # YOUTH FOUNDATION PROGRAMS
    c.execute('''
        CREATE TABLE IF NOT EXISTS youth_programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_type TEXT NOT NULL,  -- choir, sports, education, camp, outreach
            program_name TEXT NOT NULL,
            description TEXT,
            start_date DATE,
            end_date DATE,
            location TEXT,
            coordinator TEXT,
            budget DECIMAL(10,2),
            status TEXT DEFAULT 'planned',
            participants_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default youth programs from the Constitution
    programs = [
        ('choir', 'Church Choir Competition', 'Annual inter-provincial choir competition', '2025-07-20', '2025-07-20', 'Church Headquarters', 'Music Ministry', 50000.00),
        ('camp', 'National Youth Holiday Trip to Durban', 'Annual youth gathering from all 9 provinces', '2025-12-15', '2025-12-22', 'Durban', 'Youth President', 150000.00),
        ('sports', 'Sports Development Program', 'Youth sports tournaments and training', '2025-06-01', '2025-08-31', 'Various Locations', 'Sports Ministry', 30000.00),
        ('education', 'Educational Tours & School Support', 'School visits and educational support programs', '2025-02-01', '2025-11-30', 'All Provinces', 'Education Ministry', 75000.00),
        ('outreach', 'Community Outreach Program', 'Poverty alleviation and community support', '2025-01-01', '2025-12-31', 'Nationwide', 'Outreach Ministry', 100000.00)
    ]
    
    for program in programs:
        c.execute('''
            INSERT OR IGNORE INTO youth_programs 
            (program_type, program_name, description, start_date, end_date, location, coordinator, budget)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', program)
    
    # UNIFORM MANAGEMENT (from Constitution)
    c.execute('''
        CREATE TABLE IF NOT EXISTS uniforms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uniform_type TEXT NOT NULL,  -- male_leader, female_leader, male_member, female_member, youth_male, youth_female
            description TEXT NOT NULL,
            items TEXT NOT NULL,  -- JSON array of items
            approved_colors TEXT,
            emblem_required BOOLEAN DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert uniform standards from Constitution
    uniforms = [
        ('male_leader', 'Male Church Leaders', 'White trousers, blue shirt, white jacket, blue band, church emblem', 'White, Blue, Navy Blue', 1, 'For Arch-Bishop, Bishop, Presidents, Ministers'),
        ('female_leader', 'Female Church Leaders', 'White skirt, blue top, blue neck band, white band, head cover, church emblem', 'White, Blue', 1, 'For female leaders'),
        ('male_member', 'Male Members', 'White trousers, blue shirt, white jacket, blue band', 'White, Blue', 1, 'Regular male members'),
        ('female_member', 'Female Members', 'White skirt, blue top, blue neck band, white band, head cover', 'White, Blue', 1, 'Regular female members'),
        ('youth_male', 'Youth Male', 'White trousers, blue shirt, white jacket, blue band', 'White, Blue', 1, 'Youth members (16-35 years)'),
        ('youth_female', 'Youth Female', 'White dress, blue band, head cover', 'White, Blue', 1, 'Youth members (16-35 years)')
    ]
    
    for uniform in uniforms:
        c.execute('''
            INSERT OR IGNORE INTO uniforms (uniform_type, description, items, approved_colors, emblem_required, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', uniform)
    
    # [Rest of the tables remain the same...]
    # CONTINUE WITH PREVIOUS TABLES: attendance, donations, prayer_requests, etc.
    
    # ATTENDANCE TABLE
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_id INTEGER,
            service_type TEXT,
            service_date DATE,
            check_in_time TIMESTAMP,
            check_out_time TIMESTAMP,
            temperature REAL,
            attended_via TEXT DEFAULT 'in_person',
            notes TEXT,
            recorded_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    ''')
    
    # DONATIONS & TITHES
    c.execute('''
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER,
            donation_type TEXT,
            amount DECIMAL(10,2) NOT NULL,
            currency TEXT DEFAULT 'ZAR',
            payment_method TEXT,
            reference_number TEXT UNIQUE,
            transaction_id TEXT,
            status TEXT DEFAULT 'pending',
            donation_date DATE DEFAULT CURRENT_DATE,
            receipt_issued BOOLEAN DEFAULT 0,
            receipt_number TEXT,
            purpose TEXT,  -- tithe, offering, building, youth_foundation, general
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (donor_id) REFERENCES users(id)
        )
    ''')
    
    # Continue with other tables...
    
    conn.commit()
    conn.close()
    print("✅ Zion Apostolic Swaziland Church database initialized")

init_database()

# ============ HELPER FUNCTIONS ============
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
;1R    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def generate_token(user_id, role):
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            current_user = data['user_id']
            current_role = data['role']
        except:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user, current_role, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(current_user, current_role, *args, **kwargs):
        if current_role not in ['admin', 'super_admin', 'minister']:
            return jsonify({'error': 'Admin access required'}), 403
        return f(current_user, current_role, *args, **kwargs)
    return decorated

# ============ CHURCH INFO ENDPOINTS ============
@app.route('/api/church/info', methods=['GET'])
def church_info():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT * FROM church_info LIMIT 1')
    church = c.fetchone()
    
    c.execute('SELECT COUNT(*) as total_branches FROM branches WHERE status = "active"')
    branches = c.fetchone()
    
    c.execute('SELECT province, COUNT(*) as count FROM branches GROUP BY province')
    by_province = c.fetchall()
    
    conn.close()
    
    if church:
        return jsonify({
            'church': dict(church),
            'statistics': {
                'total_branches': branches['total_branches'],
                'branches_by_province': [dict(row) for row in by_province]
            }
        })
    else:
        return jsonify({
            'name': 'Zion Apostolic Swaziland Church of South Africa',
            'npo_number': '2023/757388/08',
            'motto': 'Building Faith, Unity, and the Future of Our Youth',
            'contact': '072 276 7670 (Youth President)',
# Initialize git
git init
git add .
git commit -m "Complete Zion Apostolic Church System v2.0"

# Connect to your GitHub
git remote add origin https://github.com/vusimahlangu/Zion-Apostolic-Swaziland-Church-of-South-Africa.git
git branch -M main
git push -u origin main

pwd
# Should show: /c/Users/YourUsername/Zion-Church-New (or similar)
git init
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
env.bak/
venv.bak/

# Database
*.db
*.sqlite3

# Environment variables
.env
.env.local

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# Node modules
node_modules/
npm-debug.log*

# Temporary files
*.tmp
*.temp

# Logs
*.log

# Virtual environment
myenv/
