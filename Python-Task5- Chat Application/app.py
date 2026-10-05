#!/usr/bin/env python3
"""
Real-Time Chat Application Server
Tech Stack: Flask, Flask-SocketIO (WebSockets), SQLite3, Werkzeug Security
"""

import os
import sys
import re
import sqlite3
import datetime
import contextlib

# Ensure Windows terminals with cp1252 do not crash on UTF-8 / emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    g
)
from flask_socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room,
    disconnect
)
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'chat.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'oasis-chat-dev-secret-key-3b89fa7e21')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize SocketIO with support for cross-origin if needed and thread/websocket mode
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    manage_session=False,
    async_mode=None  # Automatically picks simple-websocket, eventlet, or threading
)

# In-memory tracking for active sessions & rooms
# active_sessions: sid -> {'user_id': int, 'username': str, 'room': str or None}
active_sessions = {}
# room_members: room_name -> set(username)
room_members = {}

# ---------------------------------------------------------------------------
# Comprehensive Emoji Shortcode Map & Parser
# ---------------------------------------------------------------------------
EMOJI_MAP = {
    ':smile:': '😄',
    ':smiley:': '😃',
    ':grinning:': '😀',
    ':blush:': '😊',
    ':heart_eyes:': '😍',
    ':kissing_heart:': '😘',
    ':relaxed:': '☺️',
    ':heart:': '❤️',
    ':thumbsup:': '👍',
    ':+1:': '👍',
    ':thumbsdown:': '👎',
    ':-1:': '👎',
    ':fire:': '🔥',
    ':laughing:': '😆',
    ':joy:': '😂',
    ':rofl:': '🤣',
    ':rocket:': '🚀',
    ':tada:': '🎉',
    ':party:': '🥳',
    ':thinking:': '🤔',
    ':wave:': '👋',
    ':clap:': '👏',
    ':100:': '💯',
    ':sparkles:': '✨',
    ':check:': '✅',
    ':white_check_mark:': '✅',
    ':cat:': '🐱',
    ':dog:': '🐶',
    ':coffee:': '☕',
    ':sunglasses:': '😎',
    ':eyes:': '👀',
    ':star:': '⭐',
    ':pray:': '🙏',
    ':warning:': '⚠️',
    ':cry:': '😢',
    ':sob:': '😭',
    ':wink:': '😉',
    ':cool:': '🆒',
    ':ok:': '👌',
    ':ok_hand:': '👌',
    ':skull:': '💀',
    ':zap:': '⚡',
    ':bulb:': '💡',
    ':lock:': '🔒',
    ':unlock:': '🔓',
    ':ghost:': '👻',
    ':crown:': '👑',
    ':gem:': '💎',
    ':money:': '💰',
    ':muscle:': '💪',
    ':pizza:': '🍕',
    ':beer:': '🍺',
    ':salute:': '🫡',
    ':nerd:': '🤓',
    ':rolling_eyes:': '🙄',
    ':shrug:': '🤷',
    ':facepalm:': '🤦'
}

def parse_emojis(text: str) -> str:
    """Replaces emoji shortcodes (e.g., :smile:, :heart:) with their Unicode characters."""
    if not text:
        return text
    # Pattern to match shortcodes: :code:
    pattern = re.compile(r':([a-zA-Z0-9_\+\-]+):')
    def _repl(match):
        code = match.group(0)
        return EMOJI_MAP.get(code, code)
    return pattern.sub(_repl, text)

# ---------------------------------------------------------------------------
# Database Management
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def db_connection():
    """
    Context manager providing a clean, thread-safe SQLite connection.
    Enforces foreign keys, enables dictionary-like row access, and automatically
    handles commits and rollbacks.
    """
    conn = sqlite3.connect(DATABASE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes tables (users, rooms, messages) and seeds default rooms if needed."""
    with db_connection() as db:
        # 1. Users table
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # 2. Rooms table
        db.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL COLLATE NOCASE,
                description TEXT,
                created_by TEXT DEFAULT 'System',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # 3. Messages table
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # Performance Indexes
        db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_rooms_name ON rooms(name);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room_id, id);")

        # Seed initial default rooms if empty
        room_count = db.execute("SELECT COUNT(*) as count FROM rooms").fetchone()['count']
        if room_count == 0:
            default_rooms = [
                ('General', 'Welcome to the main channel! General chats for all members.', 'System'),
                ('Tech Talk', 'Architecture, Python, WebSockets, and developer chatter.', 'System'),
                ('Random', 'Memes, random discussions, and watercooler breaks.', 'System')
            ]
            db.executemany(
                "INSERT INTO rooms (name, description, created_by) VALUES (?, ?, ?);",
                default_rooms
            )
            print("[DB] Initialized database and seeded default rooms: General, Tech Talk, Random.")

        # Ensure demo accounts alice and bob exist with password123
        demo_pass_hash = generate_password_hash('password123')
        for demo_name in ['alice', 'bob']:
            existing_user = db.execute("SELECT id FROM users WHERE username = ? COLLATE NOCASE", (demo_name,)).fetchone()
            if not existing_user:
                db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (demo_name, demo_pass_hash))
                print(f"[DB] Created demo user '{demo_name}' (password: password123)")

# Ensure DB is created on load
init_db()

# ---------------------------------------------------------------------------
# Authentication & HTTP Routes
# ---------------------------------------------------------------------------
def get_session_user():
    """
    Validates current session against the SQLite database.
    If the session is invalid or the user was deleted, cleans up the ghost session.
    """
    user_id = session.get('user_id')
    if not user_id:
        return None
    try:
        with db_connection() as db:
            user = db.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
            if user:
                return {'id': user['id'], 'username': user['username']}
    except Exception:
        pass
    # Stale/invalid session found - clear it so user gets fresh login screen
    session.pop('user_id', None)
    session.pop('username', None)
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_session_user()
        if not current_user:
            if request.is_json:
                return jsonify({'error': 'Unauthorized', 'message': 'Please log in to continue.'}), 401
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Main route serving index.html. Contains both Auth and Chat interfaces."""
    current_user = get_session_user()
    return render_template('index.html', current_user=current_user)

@app.route('/api/register', methods=['POST'])
def register():
    """Registers a new user and establishes a session upon success."""
    data = request.get_json(silent=True) or request.form
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    # Input validation
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required.'}), 400

    if not re.match(r'^[a-zA-Z0-9_\-]{3,20}$', username):
        return jsonify({
            'success': False,
            'error': 'Username must be 3-20 characters long and contain only letters, numbers, hyphens, and underscores.'
        }), 400

    if len(password) < 4:
        return jsonify({'success': False, 'error': 'Password must be at least 4 characters.'}), 400

    password_hash = generate_password_hash(password)

    try:
        with db_connection() as db:
            existing = db.execute("SELECT id FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
            if existing:
                return jsonify({'success': False, 'error': f'Username "{username}" is already taken. Please choose another or sign in.'}), 409

            cursor = db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            user_id = cursor.lastrowid

            # Set user session
            session['user_id'] = user_id
            session['username'] = username

            return jsonify({
                'success': True,
                'message': 'Registration successful.',
                'user': {'id': user_id, 'username': username}
            }), 201

    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Username already exists.'}), 409
    except Exception as e:
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticates credentials against stored password hashes with helpful diagnostic feedback."""
    data = request.get_json(silent=True) or request.form
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required.'}), 400

    with db_connection() as db:
        user = db.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
        if not user:
            return jsonify({
                'success': False,
                'not_found': True,
                'error': f'Account "{username}" not found. Please click "Create Account" above to register.'
            }), 404

        if not check_password_hash(user['password_hash'], password):
            return jsonify({'success': False, 'error': f'Incorrect password for "{user["username"]}". Please try again.'}), 401

        session['user_id'] = user['id']
        session['username'] = user['username']

        return jsonify({
            'success': True,
            'message': 'Login successful.',
            'user': {'id': user['id'], 'username': user['username']}
        }), 200

@app.route('/api/logout', methods=['GET', 'POST'])
def logout():
    """Logs the user out and clears the session."""
    session.clear()
    if request.is_json:
        return jsonify({'success': True, 'message': 'Logged out successfully.'})
    return redirect(url_for('index'))

@app.route('/api/me')
def me():
    """Returns the currently authenticated user or 401."""
    current_user = get_session_user()
    if current_user:
        return jsonify({
            'authenticated': True,
            'user': current_user
        })
    return jsonify({'authenticated': False, 'user': None}), 401

@app.route('/api/rooms', methods=['GET'])
@login_required
def get_rooms():
    """Retrieves all available chat rooms with metadata and recent activity."""
    with db_connection() as db:
        rooms = db.execute("""
            SELECT r.id, r.name, r.description, r.created_by, r.created_at,
                   COUNT(m.id) as message_count
            FROM rooms r
            LEFT JOIN messages m ON r.id = m.room_id
            GROUP BY r.id
            ORDER BY r.name ASC
        """).fetchall()

        result = []
        for r in rooms:
            name = r['name']
            active_count = len(room_members.get(name, set()))
            result.append({
                'id': r['id'],
                'name': name,
                'description': r['description'] or '',
                'created_by': r['created_by'],
                'created_at': r['created_at'],
                'message_count': r['message_count'],
                'active_users': active_count
            })
        return jsonify({'success': True, 'rooms': result})

@app.route('/api/rooms', methods=['POST'])
@login_required
def create_room_api():
    """HTTP REST endpoint to create a chat room and broadcast to all connected clients."""
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    desc = (data.get('description') or '').strip()

    if not re.match(r'^[a-zA-Z0-9_\- ]{2,30}$', name):
        return jsonify({
            'success': False,
            'error': 'Room name must be 2-30 characters (letters, numbers, spaces, hyphens, underscores).'
        }), 400

    if len(desc) > 120:
        desc = desc[:120]

    username = session['username']

    try:
        with db_connection() as db:
            existing = db.execute("SELECT id FROM rooms WHERE name = ?", (name,)).fetchone()
            if existing:
                return jsonify({'success': False, 'error': f'A room named "{name}" already exists.'}), 409

            cur = db.execute("""
                INSERT INTO rooms (name, description, created_by)
                VALUES (?, ?, ?)
            """, (name, desc, username))
            room_id = cur.lastrowid

        new_room = {
            'id': room_id,
            'name': name,
            'description': desc,
            'created_by': username,
            'message_count': 0,
            'active_users': 0
        }

        # Real-time WebSocket broadcast to all connected users
        socketio.emit('new_room_created', new_room)

        return jsonify({
            'success': True,
            'message': f'Room "{name}" created successfully!',
            'room': new_room
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500

@app.route('/api/rooms/<path:room_name>/messages', methods=['GET'])
@login_required
def get_room_messages(room_name):
    """Fetches recent message history for a given room name."""
    with db_connection() as db:
        room = db.execute("SELECT id, name, description FROM rooms WHERE name = ?", (room_name,)).fetchone()
        if not room:
            return jsonify({'success': False, 'error': f'Room "{room_name}" not found.'}), 404

        rows = db.execute("""
            SELECT id, room_id, user_id, username, content, timestamp, created_at
            FROM messages
            WHERE room_id = ?
            ORDER BY id ASC
            LIMIT 100
        """, (room['id'],)).fetchall()

        messages = [
            {
                'id': row['id'],
                'room': room['name'],
                'user_id': row['user_id'],
                'username': row['username'],
                'message': row['content'],
                'timestamp': row['timestamp'],
                'is_system': False
            }
            for row in rows
        ]
        return jsonify({
            'success': True,
            'room': room['name'],
            'description': room['description'] or '',
            'messages': messages
        })

@app.route('/api/rooms/<path:room_name>/messages', methods=['POST'])
@login_required
def send_room_message_api(room_name):
    """HTTP REST fallback to send a message to a room and broadcast in real-time."""
    data = request.get_json(silent=True) or request.form
    raw_message = (data.get('message') or '').strip()

    if not raw_message:
        return jsonify({'success': False, 'error': 'Message cannot be empty.'}), 400

    if len(raw_message) > 2000:
        return jsonify({'success': False, 'error': 'Message exceeds 2000 character limit.'}), 400

    username = session['username']
    user_id = session['user_id']
    parsed_message = parse_emojis(raw_message)
    now_ts = datetime.datetime.now().strftime('%H:%M')

    try:
        with db_connection() as db:
            room = db.execute("SELECT id, name FROM rooms WHERE name = ?", (room_name,)).fetchone()
            if not room:
                return jsonify({'success': False, 'error': f'Room "{room_name}" not found.'}), 404

            cur = db.execute("""
                INSERT INTO messages (room_id, user_id, username, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (room['id'], user_id, username, parsed_message, now_ts))
            msg_id = cur.lastrowid

        message_data = {
            'id': msg_id,
            'room': room['name'],
            'user_id': user_id,
            'username': username,
            'message': parsed_message,
            'timestamp': now_ts,
            'is_system': False
        }

        # Broadcast via WebSocket to all connected room members
        socketio.emit('receive_message', message_data, to=room['name'])

        return jsonify({'success': True, 'message_data': message_data}), 201

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# WebSocket Real-Time Event Handlers (Flask-SocketIO)
# ---------------------------------------------------------------------------
@socketio.on('connect')
def handle_connect(auth=None):
    """
    Verifies user session on WebSocket connection establishment.
    Supports both HTTP session cookie and explicit client auth payload fallback.
    """
    current_user = get_session_user()

    # Fallback to auth payload if session cookie was not attached by the browser/socket transport
    if not current_user and isinstance(auth, dict):
        auth_user_id = auth.get('user_id')
        auth_username = auth.get('username')
        if auth_user_id and auth_username:
            try:
                with db_connection() as db:
                    user = db.execute(
                        "SELECT id, username FROM users WHERE id = ? AND username = ? COLLATE NOCASE",
                        (auth_user_id, auth_username)
                    ).fetchone()
                    if user:
                        current_user = {'id': user['id'], 'username': user['username']}
                        session['user_id'] = user['id']
                        session['username'] = user['username']
            except Exception as e:
                print(f"[Socket] Auth lookup error: {e}")

    if not current_user:
        # Reject unauthenticated socket connections
        print(f"[Socket] Unauthorized connection rejected from SID: {request.sid}")
        return False

    user_id = current_user['id']
    username = current_user['username']
    active_sessions[request.sid] = {
        'user_id': user_id,
        'username': username,
        'room': None
    }
    print(f"[Socket] User connected: {username} (SID: {request.sid})")
    emit('connected', {
        'message': f'Welcome, {username}! Connected to real-time server.',
        'username': username
    })

@socketio.on('join_room')
def handle_join_room(data):
    """
    Handles a user joining a chat room.
    Leaves the previous room, loads SQLite message history,
    broadcasts system notification, and updates member list.
    """
    client_info = active_sessions.get(request.sid)
    if not client_info:
        user_id = session.get('user_id')
        username = session.get('username')
        if user_id and username:
            active_sessions[request.sid] = {
                'user_id': user_id,
                'username': username,
                'room': None
            }
            client_info = active_sessions[request.sid]
        else:
            emit('error', {'message': 'Session expired or unauthenticated. Please re-login.'})
            return

    username = client_info['username']
    user_id = client_info['user_id']
    room_name = (data.get('room') or '').strip()

    if not room_name:
        emit('error', {'message': 'Room name cannot be empty.'})
        return

    # Verify room exists in database
    with db_connection() as db:
        room = db.execute("SELECT id, name, description FROM rooms WHERE name = ?", (room_name,)).fetchone()
        if not room:
            emit('error', {'message': f'Room "{room_name}" does not exist.'})
            return
        room_id = room['id']
        room_desc = room['description'] or ''

    # Leave previous room if the user was in one
    old_room = client_info.get('room')
    if old_room and old_room != room_name:
        leave_room(old_room)
        if old_room in room_members:
            room_members[old_room].discard(username)
            # Broadcast departure notice to previous room
            leave_ts = datetime.datetime.now().strftime('%H:%M')
            emit('receive_message', {
                'id': None,
                'room': old_room,
                'username': 'System',
                'message': f'{username} has left the room.',
                'timestamp': leave_ts,
                'is_system': True
            }, to=old_room)
            emit('room_users', {
                'room': old_room,
                'users': sorted(list(room_members[old_room]))
            }, to=old_room)

    # Join the new room
    join_room(room_name)
    client_info['room'] = room_name

    if room_name not in room_members:
        room_members[room_name] = set()
    room_members[room_name].add(username)

    # Query message history for this room (ordered chronologically)
    with db_connection() as db:
        rows = db.execute("""
            SELECT id, room_id, user_id, username, content, timestamp, created_at
            FROM messages
            WHERE room_id = ?
            ORDER BY id ASC
            LIMIT 100
        """, (room_id,)).fetchall()

        history = [
            {
                'id': row['id'],
                'room': room_name,
                'user_id': row['user_id'],
                'username': row['username'],
                'message': row['content'],
                'timestamp': row['timestamp'],
                'is_system': False
            }
            for row in rows
        ]

    # Emit historical messages specifically to the joined client
    emit('room_history', {
        'room': room_name,
        'description': room_desc,
        'messages': history
    }, to=request.sid)

    # Broadcast system message to all users in the room
    now_ts = datetime.datetime.now().strftime('%H:%M')
    emit('receive_message', {
        'id': None,
        'room': room_name,
        'username': 'System',
        'message': f'{username} has joined the room.',
        'timestamp': now_ts,
        'is_system': True
    }, to=room_name)

    # Broadcast active members list to room
    emit('room_users', {
        'room': room_name,
        'users': sorted(list(room_members[room_name]))
    }, to=room_name)

    print(f"[Room] {username} joined '{room_name}' (Active members: {len(room_members[room_name])})")

@socketio.on('leave_room')
def handle_leave_room(data):
    """Handles an explicit room exit from the client."""
    client_info = active_sessions.get(request.sid)
    if not client_info:
        return

    username = client_info['username']
    room_name = (data.get('room') or '').strip()

    if room_name and room_name in room_members:
        leave_room(room_name)
        room_members[room_name].discard(username)
        client_info['room'] = None

        now_ts = datetime.datetime.now().strftime('%H:%M')
        emit('receive_message', {
            'id': None,
            'room': room_name,
            'username': 'System',
            'message': f'{username} has left the room.',
            'timestamp': now_ts,
            'is_system': True
        }, to=room_name)
        emit('room_users', {
            'room': room_name,
            'users': sorted(list(room_members[room_name]))
        }, to=room_name)

@socketio.on('send_message')
def handle_send_message(data):
    """
    Receives incoming chat message, parses emojis, stores message in SQLite,
    and broadcasts to all connected clients in the designated room.
    """
    client_info = active_sessions.get(request.sid)
    if not client_info:
        user_id = session.get('user_id')
        username = session.get('username')
        if user_id and username:
            active_sessions[request.sid] = {
                'user_id': user_id,
                'username': username,
                'room': None
            }
            client_info = active_sessions[request.sid]
        else:
            emit('error', {'message': 'Session expired. Please log in again.'})
            return

    username = client_info['username']
    user_id = client_info['user_id']
    room_name = (data.get('room') or '').strip()
    raw_message = (data.get('message') or '').strip()

    if not room_name or not raw_message:
        return

    if len(raw_message) > 2000:
        emit('error', {'message': 'Message is too long. Maximum length is 2000 characters.'})
        return

    # Parse emoji shortcodes to Unicode (e.g., :smile: -> 😄, :heart: -> ❤️)
    parsed_message = parse_emojis(raw_message)
    now_ts = datetime.datetime.now().strftime('%H:%M')

    # Store in SQLite database
    try:
        with db_connection() as db:
            room = db.execute("SELECT id FROM rooms WHERE name = ?", (room_name,)).fetchone()
            if not room:
                emit('error', {'message': f'Room "{room_name}" not found.'})
                return
            room_id = room['id']

            cur = db.execute("""
                INSERT INTO messages (room_id, user_id, username, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (room_id, user_id, username, parsed_message, now_ts))
            msg_id = cur.lastrowid

        # Broadcast bidirectional message to room
        emit('receive_message', {
            'id': msg_id,
            'room': room_name,
            'user_id': user_id,
            'username': username,
            'message': parsed_message,
            'timestamp': now_ts,
            'is_system': False
        }, to=room_name)

    except Exception as e:
        emit('error', {'message': f'Failed to deliver message: {str(e)}'})

@socketio.on('create_room')
def handle_create_room(data):
    """Creates a new named room in SQLite and broadcasts room creation to all clients."""
    client_info = active_sessions.get(request.sid)
    if not client_info:
        user_id = session.get('user_id')
        username = session.get('username')
        if user_id and username:
            active_sessions[request.sid] = {
                'user_id': user_id,
                'username': username,
                'room': None
            }
            client_info = active_sessions[request.sid]
        else:
            emit('error', {'message': 'You must be logged in to create a room.'})
            return

    username = client_info['username']
    name = (data.get('name') or '').strip()
    desc = (data.get('description') or '').strip()

    # Room name validation: 2-30 characters, letters, numbers, spaces, hyphens
    if not re.match(r'^[a-zA-Z0-9_\- ]{2,30}$', name):
        emit('error', {
            'message': 'Room name must be 2-30 characters (letters, numbers, spaces, hyphens, underscores).'
        })
        return

    if len(desc) > 120:
        desc = desc[:120]

    try:
        with db_connection() as db:
            existing = db.execute("SELECT id FROM rooms WHERE name = ?", (name,)).fetchone()
            if existing:
                emit('error', {'message': f'A room named "{name}" already exists.'})
                return

            cur = db.execute("""
                INSERT INTO rooms (name, description, created_by)
                VALUES (?, ?, ?)
            """, (name, desc, username))
            room_id = cur.lastrowid

        new_room = {
            'id': room_id,
            'name': name,
            'description': desc,
            'created_by': username,
            'message_count': 0,
            'active_users': 0
        }

        # Notify ALL connected clients across all transports
        socketio.emit('new_room_created', new_room)

        emit('room_created_success', {
            'name': name,
            'message': f'Room "{name}" successfully created!'
        })

    except Exception as e:
        emit('error', {'message': f'Error creating room: {str(e)}'})

@socketio.on('typing')
def handle_typing(data):
    """Broadcasts a typing indicator to members of the room."""
    client_info = active_sessions.get(request.sid)
    if not client_info:
        return
    room_name = (data.get('room') or '').strip()
    is_typing = bool(data.get('is_typing', False))
    if room_name:
        emit('user_typing', {
            'username': client_info['username'],
            'is_typing': is_typing
        }, to=room_name, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    """
    Graceful disconnection handling:
    Cleans up active session, removes user from room tracking,
    and broadcasts a system message indicating departure.
    """
    client_info = active_sessions.pop(request.sid, None)
    if not client_info:
        return

    username = client_info.get('username')
    room_name = client_info.get('room')

    print(f"[Socket] User disconnected: {username} (SID: {request.sid})")

    if room_name and room_name in room_members:
        room_members[room_name].discard(username)
        now_ts = datetime.datetime.now().strftime('%H:%M')

        # Broadcast departure notification to the room
        emit('receive_message', {
            'id': None,
            'room': room_name,
            'username': 'System',
            'message': f'{username} has disconnected.',
            'timestamp': now_ts,
            'is_system': True
        }, to=room_name)

        # Broadcast updated participant list
        emit('room_users', {
            'room': room_name,
            'users': sorted(list(room_members[room_name]))
        }, to=room_name)

# ---------------------------------------------------------------------------
# Network Helper & Application Entry Point
# ---------------------------------------------------------------------------
def get_local_ip():
    """
    Detects the machine's primary local network IPv4 address (e.g., 192.168.1.X)
    so mobile devices on the same Wi-Fi network can connect directly.
    """
    import socket
    try:
        # Connect dummy UDP socket to public DNS to determine active local network interface
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return '127.0.0.1'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    lan_ip = get_local_ip()

    print("=" * 65)
    print(" [*] CHATTY REAL-TIME APPLICATION (WEB EDITION)")
    print(f" [Local]   http://127.0.0.1:{port}")
    print(f" [Network] http://{lan_ip}:{port}")
    print(" [Socket]  WebSocket transport enabled (Flask-SocketIO)")
    print(" [DB]      Database: SQLite3 (chat.db)")
    print(f" [Host]    Bound to {host}:{port}")
    print("=" * 65)

    socketio.run(app, host=host, port=port, debug=True, allow_unsafe_werkzeug=True)


