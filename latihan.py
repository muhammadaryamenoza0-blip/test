from flask import Flask, request, render_template_string, redirect, url_for, session, send_from_directory
import json
import os
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # App tetap berjalan walau python-dotenv belum terpasang.
    pass

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

# File untuk menyimpan data user
USERS_FILE = os.path.join(DATA_DIR, "users_data.json")
PERSONAL_PAGES_FILE = os.path.join(DATA_DIR, "personal_pages.json")

# Folder untuk menyimpan gambar, lagu, dan video
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'mp4', 'webm', 'avi', 'mov', 'mkv', 'flv', 'm4v', 'wmv'}

# Buat folder uploads jika belum ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # Max 100MB per file (upgraded from 16MB)

def allowed_file(filename):
    """Cek apakah file adalah gambar atau lagu"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Tentukan tipe file: image, audio, atau video"""
    audio_ext = {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac'}
    video_ext = {'mp4', 'webm', 'avi', 'mov', 'mkv', 'flv', 'm4v', 'wmv'}
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in video_ext:
        return 'video'
    elif ext in audio_ext:
        return 'audio'
    else:
        return 'image'

def get_audio_mime_type(filename):
    """Tentukan MIME type berdasarkan ekstensi audio"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    mime_types = {
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'm4a': 'audio/mp4',
        'flac': 'audio/flac',
        'aac': 'audio/aac'
    }
    return mime_types.get(ext, 'audio/mpeg')

def get_video_mime_type(filename):
    """Tentukan MIME type berdasarkan ekstensi video"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    mime_types = {
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
        'mkv': 'video/x-matroska',
        'flv': 'video/x-flv',
        'm4v': 'video/x-m4v',
        'wmv': 'video/x-ms-wmv'
    }
    return mime_types.get(ext, 'video/mp4')

# Default users (akan digunakan jika file tidak ada)
DEFAULT_USERS = {
    "admin": {"password": "1234", "msg": "Selamat datang, Admin. Dunia aman di tanganmu.", "role": "admin", "bg_color": "#000000", "text_color": "#ffffff", "theme": "dark"},
    "arya": {"password": "4321", "msg": "Halo User. Hidup memang absurd, tapi jalan terus.", "role": "user", "bg_color": "#000000", "text_color": "#ffffff", "theme": "dark"},
    "guest": {"password": "0000", "msg": "Selamat datang, tamu yang terhormat. Janganlah engkau terlalu banyak berfikir tentang hal yang tak perlu.", "role": "user", "bg_color": "#000000", "text_color": "#ffffff", "theme": "dark"},
    "friend": {"password": "1111", "msg": "halo teman semoga kau selalu sehat dan mendapatkan apa yang kau inginkan", "role": "user", "bg_color": "#000000", "text_color": "#ffffff", "theme": "dark"},
    "ma biche": {"password": "151225", "msg": "je t'aime,ma biche", "role": "user", "bg_color": "#000000", "text_color": "#ffffff", "theme": "dark"}
}

def load_users():
    """Memuat user data dari file JSON"""
    global USERS, PENDING_USERS, ADMIN_PANEL_ENABLED
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                data = json.load(f)
                USERS = data.get("users", DEFAULT_USERS)
                PENDING_USERS = data.get("pending_users", {})
                ADMIN_PANEL_ENABLED = data.get("admin_panel_enabled", True)
        except:
            USERS = DEFAULT_USERS.copy()
            PENDING_USERS = {}
            ADMIN_PANEL_ENABLED = True
    else:
        USERS = DEFAULT_USERS.copy()
        PENDING_USERS = {}
        ADMIN_PANEL_ENABLED = True

def save_users():
    """Menyimpan user data ke file JSON"""
    data = {
        "users": USERS,
        "pending_users": PENDING_USERS,
        "admin_panel_enabled": ADMIN_PANEL_ENABLED
    }
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_personal_pages():
    """Memuat personal page data dari file JSON"""
    global PERSONAL_PAGES
    if os.path.exists(PERSONAL_PAGES_FILE):
        try:
            with open(PERSONAL_PAGES_FILE, 'r') as f:
                PERSONAL_PAGES = json.load(f)
        except:
            PERSONAL_PAGES = {}
    else:
        PERSONAL_PAGES = {}

def save_personal_pages():
    """Menyimpan personal page data ke file JSON"""
    with open(PERSONAL_PAGES_FILE, 'w') as f:
        json.dump(PERSONAL_PAGES, f, indent=2)

def get_user_personal_page(username):
    """Dapatkan data personal page user, buat default jika belum ada"""
    if username not in PERSONAL_PAGES:
        PERSONAL_PAGES[username] = {
            "title": f"Personal Page - {username}",
            "description": "Selamat datang di halaman personal saya!",
            "bg_color": "#1a1a2e",
            "text_color": "#ffffff",
            "images": [],
            "audio": [],
            "video": [],
            "background_image": None
        }
        save_personal_pages()
    # Ensure audio array exists for backward compatibility
    if "audio" not in PERSONAL_PAGES[username]:
        PERSONAL_PAGES[username]["audio"] = []
    # Ensure video array exists for backward compatibility
    if "video" not in PERSONAL_PAGES[username]:
        PERSONAL_PAGES[username]["video"] = []
    return PERSONAL_PAGES[username]

# Load users saat aplikasi dimulai
load_users()
load_personal_pages()

USERS = USERS if USERS else DEFAULT_USERS.copy()
PENDING_USERS = PENDING_USERS if PENDING_USERS else {}
ADMIN_PANEL_ENABLED = ADMIN_PANEL_ENABLED if 'ADMIN_PANEL_ENABLED' in globals() else True

REGISTER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Register</title>
    <style>
        body {
            margin: 0;
            height: 100vh;
            background: url('{{ url_for("static", filename="bg.png") }}');
            background-size: cover;
            background-position: center;
            font-family: Arial, sans-serif;
        }
        .box {
            background: rgba(0,0,0,0.65);
            color: white;
            padding: 30px;
            width: 320px;
            margin: auto;
            margin-top: 8%;
            border-radius: 10px;
            text-align: center;
        }
        input, button {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
            border: none;
        }
        button {
            background: #00c6ff;
            cursor: pointer;
        }
        button:hover {
            background: #00a8d4;
        }
        .msg {
            color: #ffdd57;
            font-size: 12px;
            margin-top: 10px;
        }
        .login-link {
            margin-top: 15px;
        }
        .login-link a {
            color: #00c6ff;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="box">
        <h2>Register</h2>
        {% if error %}
            <p style="color: #ff4444;">{{ error }}</p>
        {% endif %}
        <form method="post">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <input name="confirm_password" type="password" placeholder="Confirm Password" required>
            <button>Register</button>
        </form>
        <p class="msg">Akun Anda akan menunggu persetujuan admin</p>
        <div class="login-link">
            Sudah punya akun? <a href="/login">Login</a>
        </div>
    </div>
</body>
</html>
"""

ADMIN_PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel</title>
    <style>
        body {
            margin: 0;
            height: 100vh;
            background: url('{{ url_for("static", filename="bg.jpg") }}');
            background-size: cover;
            background-position: center;
            font-family: Arial, sans-serif;
        }
        .container {
            background: rgba(0,0,0,0.85);
            color: white;
            padding: 20px;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 2px solid #00c6ff;
        }
        .navbar h1 {
            margin: 0;
        }
        .navbar a {
            color: white;
            background: #00c6ff;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .navbar a:hover {
            background: #00a8d4;
        }
        .menu {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .menu button {
            background: #333;
            color: white;
            border: 2px solid #00c6ff;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .menu button:hover {
            background: #00c6ff;
            color: black;
        }
        .menu button.active {
            background: #00c6ff;
            color: black;
        }
        .content {
            flex: 1;
            overflow-y: auto;
        }
        .request-card {
            background: rgba(0,0,0,0.6);
            border: 1px solid #00c6ff;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
        }
        .request-card h3 {
            margin-top: 0;
            color: #00c6ff;
        }
        .request-card .actions {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .request-card button {
            padding: 8px 15px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }
        .approve {
            background: #00c600;
            color: white;
        }
        .approve:hover {
            background: #00a800;
        }
        .reject {
            background: #c60000;
            color: white;
        }
        .reject:hover {
            background: #a80000;
        }
        .no-requests {
            color: #888;
            text-align: center;
            padding: 50px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="navbar">
            <div style="display: flex; align-items: center; gap: 15px;">
                <h1 style="margin: 0;">⚙️ Admin Panel</h1>
                <form method="post" style="margin: 0; display: inline;">
                    <input type="hidden" name="action" value="toggle_admin">
                    <button type="submit" title="{% if admin_panel_enabled %}Tutup Admin Panel{% else %}Buka Admin Panel{% endif %}" style="padding: 8px 12px; background: {% if admin_panel_enabled %}#00c600{% else %}#c60000{% endif %}; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; transition: 0.3s;">
                        {% if admin_panel_enabled %}🔓{% else %}🔒{% endif %}
                    </button>
                </form>
            </div>
            <a href="/logout">Logout</a>
        </div>
        
        <div class="menu">
            <button class="menu-btn active" onclick="showSection('pending')">📋 Permintaan Pendaftaran</button>
            <button class="menu-btn" onclick="showSection('users')">👥 Daftar Pengguna</button>
            <button class="menu-btn" onclick="showSection('home')">🏠 Home</button>
        </div>
        
        <div class="content">
            {% if not admin_panel_enabled %}
            <div style="background: rgba(198,0,0,0.3); border: 2px solid #ff4444; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                <p style="color: #ff4444; margin: 0; font-weight: bold;">⚠️ ADMIN PANEL SEDANG DITUTUP</p>
                <p style="margin: 5px 0 0 0; color: #ffdd57;">Fitur moderasi tidak tersedia untuk pengguna reguler</p>
            </div>
            {% endif %}
            <div id="pending" class="section" style="display: block;">
                <h2>Permintaan Pendaftaran Menunggu</h2>
                {% if pending_users %}
                    {% for username, data in pending_users.items() %}
                        <div class="request-card">
                            <h3>{{ username }}</h3>
                            <p>Status: <span style="color: #ffdd57;">Menunggu Persetujuan</span></p>
                            <div class="actions">
                                <form method="post" style="display: inline;">
                                    <input type="hidden" name="action" value="approve">
                                    <input type="hidden" name="username" value="{{ username }}">
                                    <button type="submit" class="approve">✓ Setujui</button>
                                </form>
                                <form method="post" style="display: inline;">
                                    <input type="hidden" name="action" value="reject">
                                    <input type="hidden" name="username" value="{{ username }}">
                                    <button type="submit" class="reject">✗ Tolak</button>
                                </form>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="no-requests">Tidak ada permintaan pendaftaran yang menunggu</div>
                {% endif %}
            </div>
            
            <div id="users" class="section" style="display: none;">
                <h2>Daftar Pengguna</h2>
                {% for username, data in users.items() %}
                    <div class="request-card">
                        <h3>{{ username }}</h3>
                        <p>Role: <span style="color: #00c6ff;">{{ data.role }}</span></p>
                        <div class="actions">
                            {% if data.role == "user" %}
                                <form method="post" style="display: inline;">
                                    <input type="hidden" name="action" value="make_admin">
                                    <input type="hidden" name="username" value="{{ username }}">
                                    <button type="submit" style="padding: 8px 15px; background: #ffaa00; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">👑 Jadikan Admin</button>
                                </form>
                            {% elif data.role == "admin" and username != session.get('user') %}
                                <form method="post" style="display: inline;">
                                    <input type="hidden" name="action" value="remove_admin">
                                    <input type="hidden" name="username" value="{{ username }}">
                                    <button type="submit" style="padding: 8px 15px; background: #c60000; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">👤 Hapus Admin</button>
                                </form>
                            {% endif %}
                        </div>
                    </div>
                {% endfor %}
            </div>
            
            <div id="home" class="section" style="display: none;">
                <h2>Dashboard Admin</h2>
                <div class="request-card">
                    <h3>📊 Statistik</h3>
                    <p>Total Pengguna: {{ user_count }}</p>
                    <p>Permintaan Menunggu: {{ pending_count }}</p>
                </div>
                <div class="request-card">
                    <h3>🔐 Kontrol Admin Panel</h3>
                    <p>Status Admin Panel: 
                        <span style="color: {% if admin_panel_enabled %}#00c600{% else %}#ff4444{% endif %};">
                            {% if admin_panel_enabled %}✓ AKTIF{% else %}✗ NONAKTIF{% endif %}
                        </span>
                    </p>
                    <form method="post" style="margin-top: 10px;">
                        <input type="hidden" name="action" value="toggle_admin">
                        <button type="submit" style="width: auto; padding: 8px 15px; background: {% if admin_panel_enabled %}#c60000{% else %}#00c600{% endif %}; color: white; border: none; border-radius: 5px; cursor: pointer;">
                            {% if admin_panel_enabled %}🔒 Tutup Admin Panel{% else %}🔓 Buka Admin Panel{% endif %}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function showSection(id) {
            // Hide all sections
            document.querySelectorAll('.section').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.menu-btn').forEach(btn => btn.classList.remove('active'));
            
            // Show selected section
            document.getElementById(id).style.display = 'block';
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
"""

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <style>
        body {
            margin: 0;
            height: 100vh;
            background: url('{{ url_for("static", filename="bg.png") }}');
            background-size: cover;
            background-position: center;
            font-family: Arial, sans-serif;
        }
        .box {
            background: rgba(0,0,0,0.65);
            color: white;
            padding: 30px;
            width: 320px;
            margin: auto;
            margin-top: 12%;
            border-radius: 10px;
            text-align: center;
        }
        input, button {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
            border: none;
        }
        button {
            background: #00c6ff;
            cursor: pointer;
        }
        .bottom-text {
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            color: white;
            font-size: 24px;
            text-align: center;
            background: transparent;
            padding: 0;
            z-index: 10;
        }
        .bottom-text h2 {
            background: transparent;
            margin: 0;
            padding: 0;
        }
        .bottom-text a {
            text-decoration: none;
        }
        .bottom-text button {
            background: transparent !important;
            color: white !important;
            border: 1px solid white !important;
            padding: 10px 20px !important;
            width: auto !important;
        }
    </style>
</head>
<body>
    {% if user == "ma biche" %}
        <div class="bottom-text">
            <h2>{{ msg }}</h2>
            <a href="/logout"><button>Logout</button></a>
        </div>
    {% else %}
        <div class="box">
            {% if msg %}
                <h2>{{ msg }}</h2>
                <a href="/logout"><button>Logout</button></a>
            {% else %}
                <h2>Login</h2>
                <form method="post">
                    <input name="username" placeholder="Username">
                    <input name="password" type="password" placeholder="Password">
                    <button>Login</button>
                </form>
                <p style="margin-top: 15px;">Belum punya akun? <a href="/register" style="color: #00c6ff;">Daftar</a></p>
            {% endif %}
        </div>
    {% endif %}
</body>
</html>
"""

HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Home</title>
    <style>
        body {
            margin: 0;
            height: 100vh;
            background: url('{{ url_for("static", filename="bg.png") }}');
            background-size: cover;
            background-position: center;
            background-color: {{ bg_color }};
            font-family: Arial, sans-serif;
        }
        .navbar {
            background: rgba(0,0,0,0.7);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .navbar h2 {
            color: {{ text_color }};
            margin: 0;
        }
        .navbar-buttons {
            display: flex;
            gap: 10px;
        }
        .navbar a {
            color: white;
            text-decoration: none;
            background: #00c6ff;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
        .navbar a:hover {
            background: #00a8d4;
        }
        .content {
            color: {{ text_color }};
            text-align: center;
            padding: 50px 20px;
        }
        .content h1 {
            font-size: 48px;
            margin-bottom: 20px;
            color: {{ text_color }};
        }
        .content p {
            font-size: 20px;
            max-width: 600px;
            margin: 0 auto;
            color: {{ text_color }};
        }
        .links {
            margin-top: 50px;
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .links a {
            color: white;
            text-decoration: none;
            background: rgba(0,0,0,0.6);
            padding: 15px 30px;
            border-radius: 5px;
            border: 2px solid #00c6ff;
            font-size: 16px;
            transition: 0.3s;
        }
        .links a:hover {
            background: #00c6ff;
            color: black;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>Welcome, {{ user }}!</h2>
        <div class="navbar-buttons">
            {% if is_admin %}
                <a href="/admin">⚙️ Admin Panel</a>
            {% endif %}
            <a href="/personal-page">🎨 Personal Page</a>
            <a href="/edit-profile">✏️ Edit Profile</a>
            <a href="/logout">Logout</a>
        </div>
    </div>
    <div class="content">
        <h1>Home</h1>
        <p>{{ msg }}</p>
        <div class="links">
            <a href="https://www.instagram.com/muhammadaryamenoza/" target="_blank">My Instagram</a>
            <a href="https://www.instagram.com" target="_blank">Instagram</a>
            <a href="https://mail.google.com" target="_blank">Gmail</a>
        </div>
    </div>
</body>
</html>
"""

EDIT_PROFILE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Edit Profile</title>
    <style>
        body {
            margin: 0;
            height: 100vh;
            background: url('{{ url_for("static", filename="bg.png") }}');
            background-size: cover;
            background-position: center;
            font-family: Arial, sans-serif;
        }
        .container {
            background: rgba(0,0,0,0.85);
            color: white;
            padding: 30px;
            width: 90%;
            max-width: 600px;
            margin: 20px auto;
            border-radius: 10px;
        }
        .container h2 {
            color: #00c6ff;
            margin-top: 0;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #00c6ff;
        }
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #00c6ff;
            border-radius: 5px;
            background: rgba(0,0,0,0.5);
            color: white;
            font-family: Arial, sans-serif;
            box-sizing: border-box;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }
        .form-group input::placeholder,
        .form-group textarea::placeholder {
            color: #888;
        }
        .color-preview {
            display: inline-block;
            width: 50px;
            height: 50px;
            border: 2px solid white;
            border-radius: 5px;
            margin-left: 10px;
        }
        .preview {
            background: rgba(0,0,0,0.6);
            padding: 20px;
            border-radius: 5px;
            margin-top: 20px;
            border: 2px solid #00c6ff;
        }
        .preview h3 {
            color: #00c6ff;
        }
        .preview-text {
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .button-group button,
        .button-group a {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            text-decoration: none;
            text-align: center;
        }
        .button-group button {
            background: #00c600;
            color: white;
        }
        .button-group button:hover {
            background: #00a800;
        }
        .button-group a {
            background: #666;
            color: white;
        }
        .button-group a:hover {
            background: #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>✏️ Edit Profile</h2>
        <form method="post">
            <div class="form-group">
                <label for="msg">Pesan di Home Page:</label>
                <textarea name="msg" id="msg" placeholder="Tulis pesan Anda..." required>{{ msg }}</textarea>
            </div>
            
            <div class="form-group">
                <label for="bg_color">Warna Background:</label>
                <input type="color" name="bg_color" id="bg_color" value="{{ bg_color }}">
                <span class="color-preview" id="bg_preview" style="background: {{ bg_color }};"></span>
            </div>
            
            <div class="form-group">
                <label for="text_color">Warna Text:</label>
                <input type="color" name="text_color" id="text_color" value="{{ text_color }}">
                <span class="color-preview" id="text_preview" style="background: {{ text_color }};"></span>
            </div>
            
            <div class="preview">
                <h3>Preview:</h3>
                <div class="preview-text" id="preview" style="background-color: {{ bg_color }}; color: {{ text_color }};">
                    {{ msg }}
                </div>
            </div>
            
            <div class="button-group">
                <button type="submit">💾 Simpan Perubahan</button>
                <a href="/home">Batal</a>
            </div>
        </form>
    </div>
    
    <script>
        // Update preview saat user mengetik
        document.getElementById('msg').addEventListener('input', updatePreview);
        document.getElementById('bg_color').addEventListener('change', updatePreview);
        document.getElementById('text_color').addEventListener('change', updatePreview);
        
        function updatePreview() {
            const msg = document.getElementById('msg').value;
            const bgColor = document.getElementById('bg_color').value;
            const textColor = document.getElementById('text_color').value;
            
            const preview = document.getElementById('preview');
            preview.style.backgroundColor = bgColor;
            preview.style.color = textColor;
            preview.textContent = msg;
            
            document.getElementById('bg_preview').style.background = bgColor;
            document.getElementById('text_preview').style.background = textColor;
        }
    </script>
</body>
</html>
"""

PUBLIC_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Public Home</title>
    <style>
        body {
            margin: 0;
            height: 100vh;
            background: url('{{ url_for("static", filename="bg.png") }}');
            background-size: cover;
            background-position: center;
            font-family: Arial, sans-serif;
        }
        .navbar {
            background: rgba(0,0,0,0.7);
            padding: 20px;
            text-align: right;
        }
        .navbar h2 {
            color: white;
            margin: 0 0 10px 0;
        }
        .navbar a {
            color: white;
            text-decoration: none;
            background: #00c6ff;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-left: 10px;
        }
        .navbar a:hover {
            background: #00a8d4;
        }
        .content {
            color: white;
            text-align: center;
            padding: 50px 20px;
        }
        .content h1 {
            font-size: 48px;
            margin-bottom: 20px;
        }
        .content p {
            font-size: 20px;
            max-width: 600px;
            margin: 0 auto;
        }
        .links {
            margin-top: 50px;
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .links a {
            color: white;
            text-decoration: none;
            background: rgba(0,0,0,0.6);
            padding: 15px 30px;
            border-radius: 5px;
            border: 2px solid #00c6ff;
            font-size: 16px;
            transition: 0.3s;
        }
        .links a:hover {
            background: #00c6ff;
            color: black;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>Welcome to My Site!</h2>
        <div style="display: flex; gap: 10px;">
            <a href="/register">📝 Register</a>
            <a href="/login">🔐 Login</a>
        </div>
    </div>
    <div class="content">
        <h1>Welcome</h1>
        <p>Access my social media and contact accounts</p>
        <div class="links">
            <a href="https://www.instagram.com/muhammadaryamenoza/" target="_blank">My Instagram</a>
            <a href="https://www.instagram.com" target="_blank">Instagram</a>
            <a href="https://mail.google.com" target="_blank">Gmail</a>
        </div>
    </div>
</body>
</html>
"""

PERSONAL_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            background: url('{{ url_for("static", filename="bg.png") }}');
            background-size: cover;
            background-attachment: fixed;
            background-color: {{ bg_color }};
            font-family: Arial, sans-serif;
            {% if background_image %}
            background-image: url('/uploads/{{ background_image }}') !important;
            background-attachment: fixed;
            background-position: center;
            background-repeat: no-repeat;
            {% endif %}
        }
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.4);
            pointer-events: none;
            z-index: -1;
        }
        .navbar {
            background: rgba(0,0,0,0.8);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        .navbar h2 {
            color: {{ text_color }};
            margin: 0;
        }
        .search-form {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .search-form input {
            padding: 10px 15px;
            border: 2px solid #00c6ff;
            border-radius: 5px;
            background: rgba(0,0,0,0.5);
            color: white;
            min-width: 200px;
        }
        .search-form input::placeholder {
            color: #888;
        }
        .search-form input:focus {
            outline: none;
            border-color: #00ff00;
            box-shadow: 0 0 10px rgba(0,255,0,0.3);
        }
        .search-form button {
            padding: 10px 20px;
            background: #00c6ff;
            color: black;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        .search-form button:hover {
            background: #00a8d4;
        }
        .navbar-buttons {
            display: flex;
            gap: 10px;
        }
        .navbar a {
            color: white;
            text-decoration: none;
            background: #00c6ff;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
        .navbar a:hover {
            background: #00a8d4;
        }
        .container {
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            background: rgba(0,0,0,0.7);
            border-radius: 10px;
            color: {{ text_color }};
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 36px;
            margin: 0 0 10px 0;
            color: {{ text_color }};
        }
        .header p {
            font-size: 18px;
            margin: 0;
            color: {{ text_color }};
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .gallery-item {
            background: rgba(0,0,0,0.5);
            border-radius: 8px;
            overflow: hidden;
            border: 2px solid #00c6ff;
            position: relative;
        }
        .gallery-item img {
            width: 100%;
            height: 250px;
            object-fit: cover;
            display: block;
        }
        .gallery-item .delete-btn {
            position: absolute;
            top: 5px;
            right: 5px;
            background: #c60000;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
        .gallery-item .delete-btn:hover {
            background: #a80000;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🎨 Personal Page</h2>
        <form method="get" action="/view-user" class="search-form">
            <input type="text" name="username" placeholder="Cari user..." required>
            <button type="submit">🔍 Cari</button>
        </form>
        <div class="navbar-buttons">
            <a href="/edit-personal-page">✏️ Edit</a>
            <a href="/home">🏠 Home</a>
            <a href="/logout">Logout</a>
        </div>
    </div>
    
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
            <p>{{ description }}</p>
        </div>
        
        <div class="gallery">
            {% if images %}
                {% for image in images %}
                    <div class="gallery-item">
                        <img src="/uploads/{{ image.filename }}" alt="Image">
                        {% if current_user == owner or is_admin %}
                        <form method="post" style="display: inline;" action="/delete-image">
                            <input type="hidden" name="image" value="{{ image.filename }}">
                            <button type="submit" class="delete-btn">🗑️ Hapus</button>
                        </form>
                        {% endif %}
                    </div>
                {% endfor %}
            {% else %}
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #888;">
                    <p>Belum ada gambar. Klik Edit untuk menambahkan!</p>
                </div>
            {% endif %}
        </div>

        {% if audio %}
        <h2 style="color: {{ text_color }}; margin-top: 40px;">🎵 Lagu</h2>
        <div style="display: flex; flex-direction: column; gap: 15px;">
            {% for track in audio %}
                <div style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; border: 2px solid #00c6ff; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div style="flex: 1; min-width: 200px;">
                        <p style="margin: 0 0 8px 0; color: {{ text_color }}; font-weight: bold;">🎵 {{ track.filename.split('_')[-1] }}</p>
                        <audio style="width: 100%; max-width: 400px;" controls preload="metadata">
                            <source src="/uploads/{{ track.filename }}">
                            Browser Anda tidak mendukung audio. <a href="/uploads/{{ track.filename }}">Download lagu</a>
                        </audio>
                    </div>
                    {% if current_user == owner or is_admin %}
                    <form method="post" style="display: inline;" action="/delete-image">
                        <input type="hidden" name="image" value="{{ track.filename }}">
                        <button type="submit" class="delete-btn">🗑️ Hapus</button>
                    </form>
                    {% endif %}
                </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if video %}
        <h2 style="color: {{ text_color }}; margin-top: 40px;">🎬 Video</h2>
        <div style="display: flex; flex-direction: column; gap: 15px;">
            {% for vid in video %}
                <div style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; border: 2px solid #00c6ff; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div style="flex: 1; min-width: 250px;">
                        <p style="margin: 0 0 8px 0; color: {{ text_color }}; font-weight: bold;">🎬 {{ vid.filename.split('_')[-1] }}</p>
                        <video style="width: 100%; max-width: 500px; border-radius: 5px;" controls preload="metadata">
                            <source src="/uploads/{{ vid.filename }}">
                            Browser Anda tidak mendukung video. <a href="/uploads/{{ vid.filename }}">Download video</a>
                        </video>
                    </div>
                    {% if current_user == owner or is_admin %}
                    <form method="post" style="display: inline;" action="/delete-image">
                        <input type="hidden" name="image" value="{{ vid.filename }}">
                        <button type="submit" class="delete-btn">🗑️ Hapus</button>
                    </form>
                    {% endif %}
                </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

EDIT_PERSONAL_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Edit Personal Page</title>
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            background: url('{{ url_for("static", filename="bg.png") }}');
            background-size: cover;
            background-color: #1a1a2e;
            font-family: Arial, sans-serif;
        }
        .container {
            background: rgba(0,0,0,0.85);
            color: white;
            padding: 30px;
            width: 90%;
            max-width: 600px;
            margin: 20px auto;
            border-radius: 10px;
        }
        .container h2 {
            color: #00c6ff;
            margin-top: 0;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #00c6ff;
        }
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #00c6ff;
            border-radius: 5px;
            background: rgba(0,0,0,0.5);
            color: white;
            font-family: Arial, sans-serif;
            box-sizing: border-box;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }
        .form-group input::placeholder,
        .form-group textarea::placeholder {
            color: #888;
        }
        .upload-area {
            border: 2px dashed #00c6ff;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
            cursor: pointer;
            background: rgba(0,0,0,0.3);
            margin: 20px 0;
        }
        .upload-area:hover {
            background: rgba(0,198,255,0.1);
        }
        .upload-area input[type="file"] {
            display: none;
        }
        .color-preview {
            display: inline-block;
            width: 50px;
            height: 50px;
            border: 2px solid white;
            border-radius: 5px;
            margin-left: 10px;
        }
        .preview {
            background: rgba(0,0,0,0.6);
            padding: 20px;
            border-radius: 5px;
            margin-top: 20px;
            border: 2px solid #00c6ff;
        }
        .preview h3 {
            color: #00c6ff;
        }
        .preview-text {
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .button-group button,
        .button-group a {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            text-decoration: none;
            text-align: center;
        }
        .button-group button {
            background: #00c600;
            color: white;
        }
        .button-group button:hover {
            background: #00a800;
        }
        .button-group a {
            background: #666;
            color: white;
        }
        .button-group a:hover {
            background: #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>✏️ Edit Personal Page</h2>
        
        <form method="post" enctype="multipart/form-data">
            <div class="form-group">
                <label for="title">Judul Halaman:</label>
                <input type="text" name="title" id="title" value="{{ title }}" required>
            </div>
            
            <div class="form-group">
                <label for="description">Deskripsi:</label>
                <textarea name="description" id="description" placeholder="Tulis deskripsi halaman Anda..." required>{{ description }}</textarea>
            </div>
            
            <div class="form-group">
                <label for="bg_color">Warna Background:</label>
                <input type="color" name="bg_color" id="bg_color" value="{{ bg_color }}">
                <span class="color-preview" id="bg_preview" style="background: {{ bg_color }};"></span>
            </div>
            
            <div class="form-group">
                <label for="text_color">Warna Text:</label>
                <input type="color" name="text_color" id="text_color" value="{{ text_color }}">
                <span class="color-preview" id="text_preview" style="background: {{ text_color }};"></span>
            </div>
            
            <div class="form-group">
                <label>Upload Gambar, Lagu, atau Video:</label>
                <div class="upload-area" id="uploadArea" onclick="document.getElementById('image_file').click();">
                    <p>📸/🎵/🎬 Klik untuk memilih file atau drag & drop di sini</p>
                    <input type="file" id="image_file" name="image" accept="image/*,audio/*,video/*">
                </div>
                <div id="uploadStatus" style="margin-top: 10px;"></div>
            </div>
            
            <div class="form-group">
                <label>Atau Pilih dari Gallery:</label>
                <a href="/image-gallery" style="display: inline-block; background: #00c6ff; color: black; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: bold;">🖼️ Buka Galeri</a>
            </div>
            
            <div class="preview">
                <h3>Preview:</h3>
                <div class="preview-text" id="preview" style="background-color: {{ bg_color }}; color: {{ text_color }};">
                    <strong>{{ title }}</strong><br>
                    {{ description }}
                </div>
            </div>
            
            <div class="button-group">
                <button type="submit">💾 Simpan Perubahan</button>
                <a href="/personal-page">Batal</a>
            </div>
        </form>
    </div>
    
    <script>
        document.getElementById('title').addEventListener('input', updatePreview);
        document.getElementById('description').addEventListener('input', updatePreview);
        document.getElementById('bg_color').addEventListener('change', updatePreview);
        document.getElementById('text_color').addEventListener('change', updatePreview);
        
        function updatePreview() {
            const title = document.getElementById('title').value;
            const description = document.getElementById('description').value;
            const bgColor = document.getElementById('bg_color').value;
            const textColor = document.getElementById('text_color').value;
            
            const preview = document.getElementById('preview');
            preview.style.backgroundColor = bgColor;
            preview.style.color = textColor;
            preview.innerHTML = '<strong>' + title + '</strong><br>' + description;
            
            document.getElementById('bg_preview').style.background = bgColor;
            document.getElementById('text_preview').style.background = textColor;
        }
        
        document.getElementById('image_file').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const uploadArea = document.getElementById('uploadArea');
            const uploadStatus = document.getElementById('uploadStatus');
            
            // Show loading
            uploadArea.innerHTML = '⏳ Mengupload file...';
            uploadArea.style.opacity = '0.5';
            uploadStatus.innerHTML = '';
            
            // Create FormData
            const formData = new FormData();
            formData.append('image', file);
            
            // Upload via AJAX
            fetch('/upload-image-instant', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
                .then(data => {
                if (data.success) {
                    uploadArea.innerHTML = '✅ ' + (data.message || 'File berhasil diupload!') + '<br><small>' + file.name + '</small>';
                    uploadArea.style.opacity = '1';
                    uploadStatus.innerHTML = '<div style="padding: 10px; background: rgba(0, 198, 0, 0.3); color: #00c600; border: 1px solid #00c600; border-radius: 5px; text-align: center;">✅ ' + data.message + '</div>';
                    // Reset file input
                    e.target.value = '';
                    setTimeout(() => {
                        uploadArea.innerHTML = '📸/🎵/🎬 Klik untuk memilih file atau drag & drop di sini';
                        uploadStatus.innerHTML = '';
                    }, 3000);
                } else {
                    throw new Error(data.error);
                }
            })
            .catch(error => {
                uploadArea.innerHTML = '📸/🎵/🎬 Klik untuk memilih file atau drag & drop di sini';
                uploadArea.style.opacity = '1';
                uploadStatus.innerHTML = '<div style="padding: 10px; background: rgba(198, 0, 0, 0.3); color: #ff4444; border: 1px solid #ff4444; border-radius: 5px; text-align: center;">❌ Upload gagal: ' + error.message + '</div>';
                e.target.value = '';
            });
        });
        
        // Drag and drop
        const uploadArea = document.getElementById('uploadArea');
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.background = 'rgba(0,198,255,0.2)';
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.background = 'rgba(0,0,0,0.3)';
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.background = 'rgba(0,0,0,0.3)';
            const files = e.dataTransfer.files;
            if (files.length) {
                document.getElementById('image_file').files = files;
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                document.getElementById('image_file').dispatchEvent(event);
            }
        });
    </script>
</body>
</html>
"""

IMAGE_GALLERY_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Image Gallery</title>
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            background: url('{{ url_for("static", filename="bg.png") }}');
            background-size: cover;
            background-color: #1a1a2e;
            font-family: Arial, sans-serif;
        }
        .navbar {
            background: rgba(0,0,0,0.8);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .navbar h2 {
            color: white;
            margin: 0;
        }
        .navbar a {
            color: white;
            text-decoration: none;
            background: #00c6ff;
            padding: 10px 20px;
            border-radius: 5px;
        }
        .navbar a:hover {
            background: #00a8d4;
        }
        .container {
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
        }
        .container h2 {
            color: white;
            text-align: center;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }
        .gallery-item {
            background: rgba(0,0,0,0.7);
            border-radius: 8px;
            overflow: hidden;
            border: 2px solid #00c6ff;
            cursor: pointer;
            transition: 0.3s;
            position: relative;
        }
        .gallery-item:hover {
            border-color: #00ff00;
            box-shadow: 0 0 10px rgba(0,255,0,0.3);
        }
        .gallery-item img {
            width: 100%;
            height: 250px;
            object-fit: cover;
            display: block;
        }
        .gallery-item-info {
            padding: 10px;
            color: white;
            font-size: 12px;
        }
        .gallery-item-info p {
            margin: 5px 0;
        }
        .set-bg-btn {
            position: absolute;
            bottom: 10px;
            left: 10px;
            right: 10px;
            background: #00c600;
            color: white;
            border: none;
            padding: 8px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }
        .set-bg-btn:hover {
            background: #00a800;
        }
        .no-images {
            color: white;
            text-align: center;
            padding: 40px;
            font-size: 18px;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🖼️ Gallery (Images & Music)</h2>
        <a href="/edit-personal-page">← Back</a>
    </div>
    
    <div class="container">
        <h2>Galeri Anda - Pilih Background atau Kelola File</h2>
        <div class="gallery">
            {% if images %}
                <h3 style="color: white; grid-column: 1 / -1;">📸 Gambar</h3>
                {% for image in images %}
                    <div class="gallery-item">
                        <img src="/uploads/{{ image.filename }}" alt="Image">
                        <div class="gallery-item-info">
                            <p>Uploaded by you</p>
                            <p>Visibility: <strong>{{ image.visibility }}</strong></p>
                        </div>
                        <div style="display: flex; gap: 8px; width: 100%; flex-wrap: wrap;">
                            <form method="post" style="flex: 1; min-width: 120px;" action="/set-background">
                                <input type="hidden" name="image" value="{{ image.filename }}">
                                <button type="submit" class="set-bg-btn" style="width: 100%;">🎨 Background</button>
                            </form>
                            <form method="post" style="flex: 1; min-width: 120px;" action="/toggle-visibility">
                                <input type="hidden" name="image" value="{{ image.filename }}">
                                <button type="submit" class="set-bg-btn" style="width: 100%;">🔁 Visibility</button>
                            </form>
                        </div>
                    </div>
                {% endfor %}
            {% endif %}
            
            {% if audio %}
                <h3 style="color: white; grid-column: 1 / -1;">🎵 Lagu</h3>
                {% for track in audio %}
                    <div style="grid-column: 1 / -1; background: rgba(0,0,0,0.7); padding: 15px; border: 2px solid #00c6ff; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <div style="flex: 1; min-width: 200px;">
                            <p style="margin: 0 0 8px 0; color: white; font-weight: bold;">🎵 {{ track.filename.split('_')[-1] }}</p>
                            <p style="margin: 5px 0; color: #aaa; font-size: 12px;">Visibility: <strong>{{ track.visibility }}</strong></p>
                        </div>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <form method="post" style="display: inline;" action="/toggle-visibility">
                                <input type="hidden" name="image" value="{{ track.filename }}">
                                <button type="submit" style="padding: 8px 12px; background: #00c600; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">🔁 Toggle</button>
                            </form>
                            <form method="post" style="display: inline;" action="/delete-image">
                                <input type="hidden" name="image" value="{{ track.filename }}">
                                <button type="submit" style="padding: 8px 12px; background: #c60000; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">🗑️ Delete</button>
                            </form>
                        </div>
                    </div>
                {% endfor %}
            {% endif %}

            {% if video %}
                <h3 style="color: white; grid-column: 1 / -1;">🎬 Video</h3>
                {% for vid in video %}
                    <div style="grid-column: 1 / -1; background: rgba(0,0,0,0.7); padding: 15px; border: 2px solid #00c6ff; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <div style="flex: 1; min-width: 250px;">
                            <p style="margin: 0 0 8px 0; color: white; font-weight: bold;">🎬 {{ vid.filename.split('_')[-1] }}</p>
                            <p style="margin: 5px 0; color: #aaa; font-size: 12px;">Visibility: <strong>{{ vid.visibility }}</strong></p>
                        </div>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <form method="post" style="display: inline;" action="/toggle-visibility">
                                <input type="hidden" name="image" value="{{ vid.filename }}">
                                <button type="submit" style="padding: 8px 12px; background: #00c600; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">🔁 Toggle</button>
                            </form>
                            <form method="post" style="display: inline;" action="/delete-image">
                                <input type="hidden" name="image" value="{{ vid.filename }}">
                                <button type="submit" style="padding: 8px 12px; background: #c60000; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">🗑️ Delete</button>
                            </form>
                        </div>
                    </div>
                {% endfor %}
            {% endif %}
            
            {% if not images and not audio and not video %}
                <div class="no-images">Belum ada file di galeri</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

@app.route("/public")
def public():
    return render_template_string(PUBLIC_HTML)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files but allow owner, admin, or if image/audio is public."""
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    # Find owner and visibility by scanning PERSONAL_PAGES (both images and audio)
    owner = None
    visibility = None
    file_type = None
    
    for uname, pdata in PERSONAL_PAGES.items():
        # Search in images
        for img in pdata.get("images", []):
            if isinstance(img, dict) and img.get("filename") == filename:
                owner = uname
                visibility = img.get("visibility", "private")
                file_type = "image"
                break
            if isinstance(img, str) and img == filename:
                owner = uname
                visibility = "private"
                file_type = "image"
                break
        
        # Search in audio
        if not owner:
            for track in pdata.get("audio", []):
                if isinstance(track, dict) and track.get("filename") == filename:
                    owner = uname
                    visibility = track.get("visibility", "private")
                    file_type = "audio"
                    break
                if isinstance(track, str) and track == filename:
                    owner = uname
                    visibility = "private"
                    file_type = "audio"
                    break
        
        if owner:
            break

    if not owner:
        return "Not found", 404

    # Allow if requester is owner, or file is public, or requester is admin
    if user == owner or visibility == "public" or USERS.get(user, {}).get("role") == "admin":
        # For audio files, set correct MIME type
        if file_type == "audio":
            mime_type = get_audio_mime_type(filename)
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype=mime_type)
        
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    return "Forbidden", 403

@app.route('/upload-image-instant', methods=['POST'])
def upload_image_instant():
    """Handle instant image or audio upload via AJAX"""
    user = session.get("user")
    if not user:
        return {"error": "Not authenticated"}, 401
    
    if 'image' not in request.files:
        return {"error": "No file provided"}, 400
    
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return {"error": "Invalid file"}, 400
    
    page_data = get_user_personal_page(user)
    file_type = get_file_type(file.filename)
    
    if file_type == 'audio':
        # Store in audio array
        total_files = len(page_data.get('audio', []))
        filename = secure_filename(f"{user}_{total_files}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        if "audio" not in page_data:
            page_data["audio"] = []
        page_data["audio"].append({"filename": filename, "visibility": "private"})
        message = "Lagu berhasil diupload!"
    elif file_type == 'video':
        # Store in video array
        total_files = len(page_data.get('video', []))
        filename = secure_filename(f"{user}_{total_files}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        if "video" not in page_data:
            page_data["video"] = []
        page_data["video"].append({"filename": filename, "visibility": "private"})
        message = "Video berhasil diupload!"
    else:
        # Store in images array (existing behavior)
        total_files = len(page_data.get('images', []))
        filename = secure_filename(f"{user}_{total_files}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        if "images" not in page_data:
            page_data["images"] = []
        page_data["images"].append({"filename": filename, "visibility": "private"})
        message = "Gambar berhasil diupload!"
    
    PERSONAL_PAGES[user] = page_data
    save_personal_pages()
    
    return {"success": True, "filename": filename, "message": message, "type": file_type}

@app.route("/home")
def home():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    user_data = USERS.get(user, {})
    msg = user_data.get("msg", "Welcome!")
    bg_color = user_data.get("bg_color", "#000000")
    text_color = user_data.get("text_color", "#ffffff")
    is_admin = user_data.get("role") == "admin"
    return render_template_string(HOME_HTML, user=user, msg=msg, bg_color=bg_color, text_color=text_color, is_admin=is_admin)

@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        msg = request.form.get("msg", "")
        bg_color = request.form.get("bg_color", "#000000")
        text_color = request.form.get("text_color", "#ffffff")
        
        # Update user data
        if user in USERS:
            USERS[user]["msg"] = msg
            USERS[user]["bg_color"] = bg_color
            USERS[user]["text_color"] = text_color
            save_users()  # Simpan perubahan ke file
        
        return redirect(url_for("home"))
    
    user_data = USERS.get(user, {})
    msg = user_data.get("msg", "")
    bg_color = user_data.get("bg_color", "#000000")
    text_color = user_data.get("text_color", "#ffffff")
    
    return render_template_string(EDIT_PROFILE_HTML, msg=msg, bg_color=bg_color, text_color=text_color)

@app.route("/")
def index():
    user = session.get("user")
    if user:
        return redirect(url_for("home"))
    else:
        return redirect(url_for("public"))

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        cp = request.form.get("confirm_password", "")
        
        if not u or not p or not cp:
            error = "Semua field harus diisi"
        elif len(u) < 3:
            error = "Username harus minimal 3 karakter"
        elif len(p) < 3:
            error = "Password harus minimal 3 karakter"
        elif p != cp:
            error = "Password tidak cocok"
        elif u in USERS:
            error = "Username sudah terdaftar"
        elif u in PENDING_USERS:
            error = "Username sudah dalam antrian persetujuan"
        else:
            PENDING_USERS[u] = {"password": p}
            save_users()  # Simpan perubahan ke file
            return redirect(url_for("register_success"))
    
    return render_template_string(REGISTER_HTML, error=error)

@app.route("/register-success")
def register_success():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Registrasi Berhasil</title>
        <style>
            body {
                margin: 0;
                height: 100vh;
                background: url('""" + url_for("static", filename="bg.png") + """');
                background-size: cover;
                font-family: Arial, sans-serif;
            }
            .box {
                background: rgba(0,0,0,0.65);
                color: white;
                padding: 30px;
                width: 320px;
                margin: auto;
                margin-top: 15%;
                border-radius: 10px;
                text-align: center;
            }
            a {
                display: inline-block;
                background: #00c6ff;
                color: black;
                padding: 10px 20px;
                margin-top: 20px;
                text-decoration: none;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>✓ Registrasi Berhasil!</h2>
            <p>Akun Anda telah terdaftar dan menunggu persetujuan admin.</p>
            <p>Silakan tunggu hingga admin menyetujui akun Anda.</p>
            <a href="/login">Kembali ke Login</a>
        </div>
    </body>
    </html>
    """

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    global ADMIN_PANEL_ENABLED
    user = session.get("user")
    if not user or USERS.get(user, {}).get("role") != "admin":
        return redirect(url_for("login"))
    
    if request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username")
        
        if action == "toggle_admin":
            ADMIN_PANEL_ENABLED = not ADMIN_PANEL_ENABLED
            save_users()
            return redirect(url_for("admin_panel"))
        elif action == "approve" and username in PENDING_USERS:
            USERS[username] = {
                "password": PENDING_USERS[username]["password"],
                "msg": f"Selamat datang, {username}!",
                "role": "user",
                "bg_color": "#000000",
                "text_color": "#ffffff",
                "theme": "dark"
            }
            del PENDING_USERS[username]
            save_users()  # Simpan perubahan ke file
        elif action == "reject" and username in PENDING_USERS:
            del PENDING_USERS[username]
            save_users()  # Simpan perubahan ke file
        elif action == "make_admin" and username in USERS:
            USERS[username]["role"] = "admin"
            save_users()  # Simpan perubahan ke file
        elif action == "remove_admin" and username in USERS and username != user:
            USERS[username]["role"] = "user"
            save_users()  # Simpan perubahan ke file
        
        return redirect(url_for("admin_panel"))
    
    return render_template_string(
        ADMIN_PANEL_HTML,
        pending_users=PENDING_USERS if ADMIN_PANEL_ENABLED else {},
        users=USERS,
        user_count=len(USERS),
        pending_count=len(PENDING_USERS) if ADMIN_PANEL_ENABLED else 0,
        admin_panel_enabled=ADMIN_PANEL_ENABLED
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")

        if u in USERS and USERS[u]["password"] == p:
            session["user"] = u
            print(f"DEBUG: Session set for user {u}")
            # Redirect based on user type
            if u == "guest":
                return redirect("https://www.instagram.com/muhammadaryamenoza/")
            else:
                return redirect(url_for("home"))
        else:
            print(f"DEBUG: Login failed for user {u}")

    user = session.get("user")
    return render_template_string(HTML, msg=USERS.get(user, {}).get("msg") if user else None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("public"))

@app.route("/personal-page")
def personal_page():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    page_data = get_user_personal_page(user)
    audio_list = page_data.get("audio", [])
    video_list = page_data.get("video", [])
    print(f"DEBUG: personal_page for user={user}, audio_list={audio_list}, video_list={video_list}")
    return render_template_string(
        PERSONAL_PAGE_HTML,
        title=page_data.get("title", ""),
        description=page_data.get("description", ""),
        bg_color=page_data.get("bg_color", "#1a1a2e"),
        text_color=page_data.get("text_color", "#ffffff"),
        images=page_data.get("images", []),
        audio=audio_list,
        video=video_list,
        background_image=page_data.get("background_image", None),
        owner=user,
        current_user=user,
        is_admin=(USERS.get(user, {}).get("role") == "admin")
    )

@app.route("/view-user")
def view_user():
    """Melihat personal page user lain"""
    search_username = request.args.get("username", "").strip()
    current_user = session.get("user")

    if not current_user:
        return redirect(url_for("login"))

    # Cari pada USERS (bukan hanya PERSONAL_PAGES), karena personal page dibuat
    # secara lazy. Jika user ada di USERS, pastikan personal page dibuat lalu tampilkan.
    if not search_username or search_username not in USERS:
        # User tidak ditemukan
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>User Tidak Ditemukan</title>
            <style>
                body {
                    margin: 0;
                    height: 100vh;
                    background: url('""" + url_for("static", filename="bg.png") + """');
                    background-size: cover;
                    font-family: Arial, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .box {
                    background: rgba(0,0,0,0.85);
                    color: white;
                    padding: 40px;
                    width: 400px;
                    border-radius: 10px;
                    text-align: center;
                    border: 2px solid #c60000;
                }
                .box h2 {
                    color: #ff4444;
                    margin-top: 0;
                }
                .box p {
                    font-size: 16px;
                    margin: 15px 0;
                }
                a {
                    display: inline-block;
                    background: #00c6ff;
                    color: black;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                }
                a:hover {
                    background: #00a8d4;
                }
            </style>
        </head>
        <body>
            <div class="box">
                <h2>❌ User Tidak Ditemukan</h2>
                <p>Username '<strong>""" + search_username + """</strong>' tidak ditemukan.</p>
                <a href="/personal-page">← Kembali</a>
            </div>
        </body>
        </html>
        """)

    # Pastikan ada data personal page untuk user yang dicari
    page_data = get_user_personal_page(search_username)

    # Determine which images/background to expose
    images = []
    for img in page_data.get("images", []):
        # img is a dict {filename, visibility}
        if search_username == current_user or img.get("visibility") == "public" or USERS.get(current_user, {}).get("role") == "admin":
            images.append(img)

    # Determine which audio to expose
    audio = []
    for track in page_data.get("audio", []):
        if search_username == current_user or track.get("visibility") == "public" or USERS.get(current_user, {}).get("role") == "admin":
            audio.append(track)

    # Determine which video to expose
    video = []
    for vid in page_data.get("video", []):
        if search_username == current_user or vid.get("visibility") == "public" or USERS.get(current_user, {}).get("role") == "admin":
            video.append(vid)

    # background image should be shown only if owner or public or admin
    bg = page_data.get("background_image", None)
    background_image = None
    if bg:
        # find bg in images list to check visibility
        found = None
        for img in page_data.get("images", []):
            if img.get("filename") == bg:
                found = img
                break
        if found and (search_username == current_user or found.get("visibility") == "public" or USERS.get(current_user, {}).get("role") == "admin"):
            background_image = bg

    return render_template_string(
        PERSONAL_PAGE_HTML,
        title=page_data.get("title", ""),
        description=page_data.get("description", ""),
        bg_color=page_data.get("bg_color", "#1a1a2e"),
        text_color=page_data.get("text_color", "#ffffff"),
        images=images,
        audio=audio,
        video=video,
        background_image=background_image,
        owner=search_username,
        current_user=current_user,
        is_admin=(USERS.get(current_user, {}).get("role") == "admin")
    )

@app.route("/edit-personal-page", methods=["GET", "POST"])
def edit_personal_page():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    page_data = get_user_personal_page(user)
    
    if request.method == "POST":
        # Update text data only (image upload sudah via AJAX)
        title = request.form.get("title", "")
        description = request.form.get("description", "")
        bg_color = request.form.get("bg_color", "#1a1a2e")
        text_color = request.form.get("text_color", "#ffffff")
        
        page_data["title"] = title
        page_data["description"] = description
        page_data["bg_color"] = bg_color
        page_data["text_color"] = text_color
        
        PERSONAL_PAGES[user] = page_data
        save_personal_pages()
        return redirect(url_for("personal_page"))
    
    return render_template_string(
        EDIT_PERSONAL_PAGE_HTML,
        title=page_data.get("title", ""),
        description=page_data.get("description", ""),
        bg_color=page_data.get("bg_color", "#1a1a2e"),
        text_color=page_data.get("text_color", "#ffffff")
    )

@app.route("/delete-image", methods=["POST"])
def delete_image():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    filename = request.form.get("image", "")
    page_data = get_user_personal_page(user)

    # Check and remove from images
    new_images = []
    removed = False
    for img in page_data.get("images", []):
        if isinstance(img, dict) and img.get("filename") == filename:
            removed = True
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            continue
        if isinstance(img, str) and img == filename:
            removed = True
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            continue
        new_images.append(img)

    if removed:
        page_data["images"] = new_images

    # Check and remove from audio
    new_audio = []
    for track in page_data.get("audio", []):
        if isinstance(track, dict) and track.get("filename") == filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            continue
        if isinstance(track, str) and track == filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            continue
        new_audio.append(track)

    if page_data.get("audio", []) != new_audio:
        page_data["audio"] = new_audio

    # Check and remove from video
    new_video = []
    for vid in page_data.get("video", []):
        if isinstance(vid, dict) and vid.get("filename") == filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            continue
        if isinstance(vid, str) and vid == filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            continue
        new_video.append(vid)

    if page_data.get("video", []) != new_video:
        page_data["video"] = new_video

    if removed or page_data.get("audio", []) != new_audio or page_data.get("video", []) != new_video:
        PERSONAL_PAGES[user] = page_data
        save_personal_pages()
    
    return redirect(url_for("personal_page"))

@app.route("/image-gallery")
def image_gallery():
    """Menampilkan galeri gambar, lagu, dan video user"""
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    # Show only current user's images, audio, and video (uploads are private)
    page_data = get_user_personal_page(user)
    images = page_data.get("images", [])
    audio = page_data.get("audio", [])
    video = page_data.get("video", [])

    return render_template_string(IMAGE_GALLERY_HTML, images=images, audio=audio, video=video)

@app.route("/set-background", methods=["POST"])
def set_background():
    """Set gambar sebagai background personal page user"""
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    image = request.form.get("image", "")
    page_data = get_user_personal_page(user)
    # Only allow setting an image that the current user actually uploaded
    found = False
    for img in page_data.get("images", []):
        if isinstance(img, dict) and img.get("filename") == image:
            found = True
            break
        if isinstance(img, str) and img == image:
            found = True
            break
    if found:
        page_data["background_image"] = image
        PERSONAL_PAGES[user] = page_data
        save_personal_pages()
    
    return redirect(url_for("edit_personal_page"))


@app.route("/toggle-visibility", methods=["POST"])
def toggle_visibility():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    filename = request.form.get("image", "")
    page_data = get_user_personal_page(user)
    changed = False
    
    # Check images
    for img in page_data.get("images", []):
        if isinstance(img, dict) and img.get("filename") == filename:
            img["visibility"] = "public" if img.get("visibility") == "private" else "private"
            changed = True
            break
    
    # Check audio if not found in images
    if not changed:
        for track in page_data.get("audio", []):
            if isinstance(track, dict) and track.get("filename") == filename:
                track["visibility"] = "public" if track.get("visibility") == "private" else "private"
                changed = True
                break
    
    if changed:
        PERSONAL_PAGES[user] = page_data
        save_personal_pages()

    return redirect(url_for("image_gallery"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)

