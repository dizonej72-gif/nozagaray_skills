from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'norzagaray_secret_key_12345')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'portal.db')

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT,
                gender TEXT,
                company TEXT,
                position TEXT,
                barangay TEXT,
                address TEXT,
                skills TEXT,
                phone TEXT,
                gmail TEXT,
                proof TEXT,
                status TEXT DEFAULT 'approved'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                posted_by TEXT,
                title TEXT,
                description TEXT,
                barangay TEXT,
                salary_option TEXT,
                salary_amount TEXT,
                rate_type TEXT,
                work_type TEXT,
                phone TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                commenter TEXT,
                comment TEXT,
                parent_id INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                receiver TEXT,
                message TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                message TEXT,
                post_id INTEGER
            )
        ''')
        
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (username, password, role, status) 
                VALUES ('admin', 'admin123', 'admin', 'approved')
            ''')

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Init Error: {e}")

init_db()

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    current_user = session['user']
    if current_user == 'admin':
        return redirect(url_for('admin'))

    role = session.get('role', 'worker')
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT username, role, full_name, gender, company, position, barangay, address, skills, phone, gmail FROM users WHERE username != 'admin' AND status = 'approved'")
        users_list = [[row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]] for row in cursor.fetchall()]
        
        cursor.execute("SELECT sender, receiver, message FROM messages WHERE receiver = ? OR sender = ? ORDER BY id DESC", (current_user, current_user))
        messages = [{'sender': row[0], 'receiver': row[1], 'message': row[2]} for row in cursor.fetchall()]
        
        cursor.execute("SELECT message, post_id FROM notifications WHERE username = ? ORDER BY id DESC", (current_user,))
        notifications = [{'message': row[0], 'post_id': row[1]} for row in cursor.fetchall()]
        
        conn.close()
    except Exception as e:
        print(f"Index Error: {e}")
        users_list, messages, notifications = [], [], []

    return render_template('index.html', 
                           users_list=users_list, 
                           user=current_user,
                           role=role,
                           messages=messages, 
                           notifications=notifications)

@app.route('/admin')
def admin():
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY id DESC")
    users = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return render_template('admin.html', users=users, posts=posts)

@app.route('/admin/approve_user/<int:user_id>', methods=['POST'])
def admin_approve_user(user_id):
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'approved' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/delete_post/<int:post_id>', methods=['POST'])
def admin_delete_post(post_id):
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    cursor.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    cursor.execute("DELETE FROM notifications WHERE post_id = ?", (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    if user_row:
        username = user_row['username']
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        cursor.execute("DELETE FROM posts WHERE posted_by = ?", (username,))
        cursor.execute("DELETE FROM comments WHERE commenter = ?", (username,))
        cursor.execute("DELETE FROM messages WHERE sender = ? OR receiver = ?", (username, username))
        cursor.execute("DELETE FROM notifications WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        gender = request.form.get('gender', 'Male')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'worker')
        barangay = request.form.get('barangay', '')
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        gmail = request.form.get('email', '')
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        skills_list = [request.form.get('skills', '')]
        other_skills = request.form.getlist('other_skills[]')
        if other_skills:
            skills_list.extend([s.strip() for s in other_skills if s.strip()])
        skills_str = ", ".join([s for s in skills_list if s])

        proof_filename = ''
        
        if role == 'worker':
            company, position = '', ''
            status = 'approved'
        else:
            skills_str = ''
            barangay, address = '', ''
            company = request.form.get('company', '')
            position = request.form.get('position', '')
            status = 'pending'
            if 'proof' in request.files:
                file = request.files['proof']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{username}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    proof_filename = filename

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password, role, full_name, gender, company, position, barangay, address, skills, phone, gmail, proof, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, password, role, full_name, gender, company, position, barangay, address, skills_str, phone, gmail, proof_filename, status))
            conn.commit()
            conn.close()
            if status == 'pending':
                return render_template('login.html', success="Registration successful! Pending Admin Approval.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error="Username already exists. Please choose another.")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?) AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            if user['status'] != 'approved':
                return render_template('login.html', error="Your account is pending admin approval.")
            session['user'] = user['username']
            session['role'] = user['role']
            if user['username'] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials or account not found.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add_post', methods=['POST'])
def add_post():
    if 'user' not in session:
        return redirect(url_for('login'))
    title = request.form['title']
    description = request.form['description']
    barangay = request.form['barangay']
    salary_option = request.form.get('salary_option', 'amount')
    salary_amount = request.form.get('salary_amount', '')
    rate_type = request.form.get('rate_type', 'Daily')
    work_type = request.form.get('work_type', 'Full-time')
    posted_by = session['user']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT phone FROM users WHERE username = ?", (posted_by,))
    user_record = cursor.fetchone()
    phone = user_record['phone'] if user_record and user_record['phone'] else ''
    
    cursor.execute("""
        INSERT INTO posts (posted_by, title, description, barangay, salary_option, salary_amount, rate_type, work_type, phone) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (posted_by, title, description, barangay, salary_option, salary_amount, rate_type, work_type, phone))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    comment = request.form['comment']
    parent_id = request.form.get('parent_id', 0)
    commenter = session['user']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO comments (post_id, commenter, comment, parent_id) VALUES (?, ?, ?, ?)",
                   (post_id, commenter, comment, parent_id))
    
    cursor.execute("SELECT posted_by FROM posts WHERE id = ?", (post_id,))
    post_owner = cursor.fetchone()
    if post_owner and post_owner['posted_by'] != commenter:
        notif_msg = f"{commenter} commented on your post."
        cursor.execute("INSERT INTO notifications (username, message, post_id) VALUES (?, ?, ?)",
                       (post_owner['posted_by'], notif_msg, post_id))
    conn.commit()
    conn.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(url_for('index'))

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    sender = session['user']
    data = request.get_json() if request.is_json else request.form
    receiver = data.get('receiver', '')
    message = data.get('message', '')

    if not receiver or not message:
        return jsonify({'error': 'Empty message'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)", 
                   (sender, receiver, message))
    
    notif_msg = f"New message from {sender}."
    cursor.execute("INSERT INTO notifications (username, message, post_id) VALUES (?, ?, ?)", (receiver, notif_msg, None))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/updates')
def api_updates():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    current_user = session['user']
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT posts.*, users.role as poster_role 
        FROM posts 
        LEFT JOIN users ON posts.posted_by = users.username 
        ORDER BY posts.id DESC
    """)
    posts_raw = cursor.fetchall()
    posts = []
    for p in posts_raw:
        post_dict = dict(p)
        cursor.execute("SELECT * FROM comments WHERE post_id = ? ORDER BY id ASC", (post_dict['id'],))
        post_dict['comments'] = [dict(c) for c in cursor.fetchall()]
        posts.append(post_dict)
    
    cursor.execute("SELECT sender, receiver, message FROM messages WHERE receiver = ? OR sender = ? ORDER BY id DESC", (current_user, current_user))
    messages = [{'sender': r[0], 'receiver': r[1], 'message': r[2]} for r in cursor.fetchall()]
    
    cursor.execute("SELECT id, message, post_id FROM notifications WHERE username = ? ORDER BY id DESC", (current_user,))
    notifications = [{'id': r[0], 'message': r[1], 'post_id': r[2]} for r in cursor.fetchall()]
    
    conn.close()
    return jsonify({
        'posts': posts, 
        'messages': messages, 
        'notifications': notifications
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
