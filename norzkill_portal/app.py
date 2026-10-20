from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'norzagaray_secret_key'

DATABASE = 'portal.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            company TEXT,
            barangay TEXT,
            skills TEXT,
            phone TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            posted_by TEXT,
            title TEXT,
            description TEXT,
            barangay TEXT,
            phone TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            commenter TEXT,
            comment TEXT,
            parent_id INTEGER
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
    
    conn.commit()
    conn.close()

TRANSLATIONS = {
    'en': {
        'hi': 'Hi',
        'messages': 'Messages',
        'notifs': 'Notifications',
        'logout': 'Logout',
        'post_job': 'Post an Ad / Job Need',
        'job_title': 'Job Title / Skill Needed',
        'job_details': 'Job Details & Description',
        'barangay': 'Barangay',
        'publish': 'Publish Ad',
        'community_feed': 'Community Feed',
        'registered_users': 'Registered Users',
        'skills': 'Skills',
        'send_msg': 'Send Message',
        'recipient': 'Recipient',
        'select_user': '-- Select User --',
        'type_msg': 'Type message...',
        'send': 'Send',
        'inbox': 'Inbox',
        'no_msg': 'No messages yet.',
        'notifications': 'Notifications',
        'no_notif': 'No notifications yet.',
        'no_comments': 'No comments yet.',
        'comment_placeholder': 'Write a comment...',
        'comment_btn': 'Comment',
        'reply_placeholder': 'Write a reply...',
        'reply_btn': 'Reply',
        'no_posts': 'No posts available yet.',
        'no_users': 'No registered users.',
        'tab_emp_posts': '📌 Posts for Employer',
        'tab_employee_posts': '📌 Posts for Employee',
        'tab_create': '✍️ Post an Ad',
        'tab_workers': '👷‍♂️ Registered Workers',
        'tab_companies': '🏢 Registered Companies',
        'workers_title': 'List of Registered Workers / Job Seekers',
        'companies_title': 'List of Registered Companies',
        'no_workers': 'No registered workers yet.',
        'no_companies': 'No registered companies yet.',
        'menu_title': 'Menu'
    },
    'tl': {
        'hi': 'Hi',
        'messages': 'Messages',
        'notifs': 'Notifications',
        'logout': 'Logout',
        'post_job': 'Post an Ad / Job Need',
        'job_title': 'Job Title / Skill Needed',
        'job_details': 'Job Details & Description',
        'barangay': 'Barangay',
        'publish': 'Publish Ad',
        'community_feed': 'Community Feed',
        'registered_users': 'Registered Users',
        'skills': 'Skills',
        'send_msg': 'Send Message',
        'recipient': 'Recipient',
        'select_user': '-- Select User --',
        'type_msg': 'Type message...',
        'send': 'Send',
        'inbox': 'Inbox',
        'no_msg': 'No messages yet.',
        'notifications': 'Notifications',
        'no_notif': 'No notifications yet.',
        'no_comments': 'No comments yet.',
        'comment_placeholder': 'Write a comment...',
        'comment_btn': 'Comment',
        'reply_placeholder': 'Write a reply...',
        'reply_btn': 'Reply',
        'no_posts': 'No posts available yet.',
        'no_users': 'No registered users.',
        'tab_emp_posts': '📌 Posts for Employer',
        'tab_employee_posts': '📌 Posts for Employee',
        'tab_create': '✍️ Post an Ad',
        'tab_workers': '👷‍♂️ Registered Workers',
        'tab_companies': '🏢 Registered Companies',
        'workers_title': 'List of Registered Workers / Job Seekers',
        'companies_title': 'List of Registered Companies',
        'no_workers': 'No registered workers yet.',
        'no_companies': 'No registered companies yet.',
        'menu_title': 'Menu'
    }
}

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in ['en', 'tl']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    current_user = session['user']

    if current_user == 'admin':
        return redirect(url_for('admin'))

    role = session.get('role', 'employer')
    lang = session.get('lang', 'tl')
    t = TRANSLATIONS[lang]
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Lahat ng database queries ay ginawang standard Python lists/dicts para ligtas sa JSON
    cursor.execute("SELECT username, role, company, barangay, skills, phone FROM users WHERE username != 'admin'")
    users_list = [[row[0], row[1], row[2], row[3], row[4], row[5]] for row in cursor.fetchall()]
    
    cursor.execute("SELECT sender, receiver, message FROM messages WHERE receiver = ? OR sender = ? ORDER BY id DESC", (current_user, current_user))
    messages = [[row[0], row[1], row[2]] for row in cursor.fetchall()]
    
    cursor.execute("SELECT message, post_id FROM notifications WHERE username = ? ORDER BY id DESC", (current_user,))
    notifications = [{'message': row[0], 'post_id': row[1]} for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('index.html', 
                           users_list=users_list, 
                           user=current_user,
                           role=role,
                           messages=messages, 
                           notifications=notifications,
                           current_lang=lang,
                           t=t)

@app.route('/admin')
def admin():
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    
    cursor.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = cursor.fetchall()
    
    conn.close()
    return render_template('admin.html', users=users, posts=posts)

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
        fullname = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']
        
        company = request.form.get('company', '') if role == 'employee' else ''
        barangay = request.form.get('barangay', '') if role == 'employer' else ''
        skills = request.form.get('skills', '') if role == 'employer' else ''
        phone = request.form.get('phone', '') if role == 'employer' else ''
        
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password, role, company, barangay, skills, phone) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fullname, password, role, company, barangay, skills, phone))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error="Full name already exists. Please check your inputs.")
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        fullname = request.form['username'].strip()
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?) AND password = ?", (fullname, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user'] = user['username']
            session['role'] = user['role']
            session['lang'] = 'tl'
            if user['username'] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid Full Name or Password. Please try again.")
            
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
    posted_by = session['user']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT phone FROM users WHERE username = ?", (posted_by,))
    user_record = cursor.fetchone()
    phone = user_record['phone'] if user_record and user_record['phone'] else ''
    
    cursor.execute("INSERT INTO posts (posted_by, title, description, barangay, phone) VALUES (?, ?, ?, ?, ?)",
                   (posted_by, title, description, barangay, phone))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    comment = request.form['comment']
    commenter = session['user']
    parent_id = request.form.get('parent_id')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO comments (post_id, commenter, comment, parent_id) VALUES (?, ?, ?, ?)",
                   (post_id, commenter, comment, parent_id if parent_id else None))
    
    if parent_id:
        cursor.execute("SELECT commenter FROM comments WHERE id = ?", (parent_id,))
        parent_comment = cursor.fetchone()
        if parent_comment and parent_comment['commenter'] != commenter:
            notif_msg = f"{commenter} replied to your comment."
            cursor.execute("INSERT INTO notifications (username, message, post_id) VALUES (?, ?, ?)",
                           (parent_comment['commenter'], notif_msg, post_id))
    else:
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
        return redirect(url_for('login'))
        
    sender = session['user']
    receiver = request.form['receiver']
    message = request.form['message']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)", (sender, receiver, message))
    notif_msg = f"New message from {sender}."
    cursor.execute("INSERT INTO notifications (username, message, post_id) VALUES (?, ?, ?)", (receiver, notif_msg, None))
    conn.commit()
    conn.close()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
        
    return redirect(url_for('index'))

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
        cursor.execute("SELECT * FROM comments WHERE post_id = ? AND parent_id IS NULL ORDER BY id ASC", (post_dict['id'],))
        comments_raw = cursor.fetchall()
        
        comments = []
        for c in comments_raw:
            c_dict = dict(c)
            cursor.execute("SELECT * FROM comments WHERE parent_id = ? ORDER BY id ASC", (c_dict['id'],))
            replies_raw = cursor.fetchall()
            c_dict['replies'] = [dict(r) for r in replies_raw]
            comments.append(c_dict)
            
        post_dict['comments'] = comments
        posts.append(post_dict)
    
    cursor.execute("SELECT sender, receiver, message FROM messages WHERE receiver = ? OR sender = ? ORDER BY id DESC", (current_user, current_user))
    messages = [{'sender': r[0], 'receiver': r[1], 'message': r[2]} for r in cursor.fetchall()]
    
    cursor.execute("SELECT message, post_id FROM notifications WHERE username = ? ORDER BY id DESC", (current_user,))
    notifications = [{'message': r[0], 'post_id': r[1]} for r in cursor.fetchall()]
    
    conn.close()
    return jsonify({
        'posts': posts, 
        'messages': messages, 
        'notifications': notifications
    })

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
