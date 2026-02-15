from flask import Flask, render_template, request, redirect, session, flash, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import uuid

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'virus-word-2026-redblack-hack'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'zip', 'rar', 'exe', 'msi'}

def init_db():
    conn = sqlite3.connect('virus.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, 
        username TEXT UNIQUE NOT NULL, 
        password TEXT NOT NULL, 
        is_admin INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        avatar TEXT,
        file_path TEXT NOT NULL,
        downloads INTEGER DEFAULT 0,
        upload_date TEXT,
        uploader TEXT
    )''')
    
    # Создаём админа
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        pwd_hash = generate_password_hash('Mark123458790')
        c.execute("INSERT INTO users (username, password, is_admin, created_at) VALUES (?, ?, 1, ?)", 
                 ('admin', pwd_hash, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_games(search=''):
    conn = sqlite3.connect('virus.db')
    c = conn.cursor()
    if search:
        c.execute("SELECT * FROM games WHERE title LIKE ? OR description LIKE ? ORDER BY upload_date DESC LIMIT 50", 
                 (f'%{search}%', f'%{search}%'))
    else:
        c.execute("SELECT * FROM games ORDER BY upload_date DESC")
    games = c.fetchall()
    conn.close()
    return games

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/games')
def api_games():
    search = request.args.get('q', '')
    games = get_games(search)
    return jsonify([{
        'id': g[0], 'title': g[1], 'desc': g[2], 'avatar': g[3], 
        'file': g[4], 'downloads': g[5], 'date': g[6], 'uploader': g[7]
    } for g in games])

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    conn = sqlite3.connect('virus.db')
    c = conn.cursor()
    c.execute("SELECT id, username, password, is_admin FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['is_admin'] = bool(user[3])
        return jsonify({'success': True, 'username': user[1], 'is_admin': bool(user[3])})
    return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 401

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if len(username) < 3 or len(password) < 4:
        return jsonify({'success': False, 'error': 'Логин >3, пароль >4 символов'}), 400
    
    conn = sqlite3.connect('virus.db')
    c = conn.cursor()
    try:
        pwd_hash = generate_password_hash(password)
        c.execute("INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)", 
                 (username, pwd_hash, datetime.now().isoformat()))
        conn.commit()
        return jsonify({'success': True, 'message': 'Регистрация успешна'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Логин уже занят'}), 400
    finally:
        conn.close()

@app.route('/api/auth/logout')
def api_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/admin/upload', methods=['POST'])
def admin_upload():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Только админ'}), 403
    
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    if not title or not description or len(title) > 100:
        return jsonify({'success': False, 'error': 'Неверные данные'}), 400
    
    avatar_file = request.files.get('avatar')
    game_file = request.files.get('game_file')
    
    if not game_file or not allowed_file(game_file.filename):
        return jsonify({'success': False, 'error': 'Выберите корректный файл игры'}), 400
    
    conn = sqlite3.connect('virus.db')
    c = conn.cursor()
    
    # Сохраняем аватар
    avatar_path = None
    if avatar_file and allowed_file(avatar_file.filename):
        ext = avatar_file.filename.rsplit('.', 1)[1].lower()
        avatar_path = f"avatar_{uuid.uuid4().hex[:8]}.{ext}"
        avatar_file.save(os.path.join(UPLOAD_FOLDER, avatar_path))
    
    # Сохраняем игру
    ext = game_file.filename.rsplit('.', 1)[1].lower()
    game_filename = f"game_{uuid.uuid4().hex[:8]}.{ext}"
    game_file.save(os.path.join(UPLOAD_FOLDER, game_filename))
    
    # Сохраняем в БД
    c.execute("""INSERT INTO games (title, description, avatar, file_path, upload_date, uploader) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
             (title, description, avatar_path, game_filename, 
              datetime.now().strftime('%Y-%m-%d %H:%M'), session['username']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/download/<int:game_id>')
def api_download(game_id):
    conn = sqlite3.connect('virus.db')
    c = conn.cursor()
    c.execute("SELECT file_path FROM games WHERE id=?", (game_id,))
    result = c.fetchone()
    
    if result:
        c.execute("UPDATE games SET downloads = downloads + 1 WHERE id=?", (game_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'file': result[0]})
    conn.close()
    return jsonify({'success': False}), 404

@app.route('/download/<int:game_id>')
def download(game_id):
    conn = sqlite3.connect('virus.db')
    c = conn.cursor()
    c.execute("SELECT file_path FROM games WHERE id=?", (game_id,))
    result = c.fetchone()
    
    if result:
        c.execute("UPDATE games SET downloads = downloads + 1 WHERE id=?", (game_id,))
        conn.commit()
        conn.close()
        return send_from_directory(UPLOAD_FOLDER, result[0], as_attachment=True)
    return 'Игра не найдена', 404

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
