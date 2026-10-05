"""
Automated Test Suite for Oasis Real-Time Chat Application
Tests authentication, database operations, emoji parsing, and HTTP endpoints.
"""
import os
import json
import sqlite3
import pytest
from app import app, init_db, parse_emojis, db_connection
from werkzeug.security import check_password_hash

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        yield client

def test_database_tables_exist():
    """Verify that users, rooms, and messages tables exist."""
    init_db()
    with db_connection() as db:
        tables = [
            row['name'] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert 'users' in tables
        assert 'rooms' in tables
        assert 'messages' in tables

        # Verify seeded default rooms
        room_names = [row['name'] for row in db.execute("SELECT name FROM rooms").fetchall()]
        assert 'General' in room_names
        assert 'Tech Talk' in room_names
        assert 'Random' in room_names

def test_emoji_shortcode_parser():
    """Verify that emoji shortcodes convert to expected Unicode characters."""
    assert parse_emojis("Hello :smile: :heart:!") == "Hello 😄 ❤️!"
    assert parse_emojis("Good job :thumbsup: :fire:") == "Good job 👍 🔥"
    assert parse_emojis("Deploy :rocket: party :tada:") == "Deploy 🚀 party 🎉"
    assert parse_emojis("Score :100: coffee :coffee:") == "Score 💯 coffee ☕"
    # Unmatched shortcode remains unchanged
    assert parse_emojis(":unknown_emoji_code:") == ":unknown_emoji_code:"
    # Plain text remains unchanged
    assert parse_emojis("Just normal text 123") == "Just normal text 123"

def test_user_registration_and_hashing(client):
    """Test user registration and verify password is cryptographically hashed in SQLite."""
    test_user = "test_alice"
    test_pass = "supersecret123"

    # Clean up test user if exists from previous run
    with db_connection() as db:
        db.execute("DELETE FROM users WHERE username = ?", (test_user,))

    # Register
    res = client.post('/api/register', json={
        'username': test_user,
        'password': test_pass
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    assert data['user']['username'] == test_user

    # Verify directly in SQLite that plaintext password is NOT stored
    with db_connection() as db:
        user_row = db.execute("SELECT * FROM users WHERE username = ?", (test_user,)).fetchone()
        assert user_row is not None
        assert user_row['password_hash'] != test_pass
        assert check_password_hash(user_row['password_hash'], test_pass) is True

def test_duplicate_user_registration(client):
    """Test that duplicate usernames are rejected."""
    test_user = "test_alice"
    res = client.post('/api/register', json={
        'username': test_user,
        'password': 'anotherpassword'
    })
    assert res.status_code == 409
    data = res.get_json()
    assert data['success'] is False

def test_user_login(client):
    """Test successful login and invalid password rejection."""
    # Invalid password
    res_fail = client.post('/api/login', json={
        'username': 'test_alice',
        'password': 'wrongpassword'
    })
    assert res_fail.status_code == 401

    # Valid password
    res_ok = client.post('/api/login', json={
        'username': 'test_alice',
        'password': 'supersecret123'
    })
    assert res_ok.status_code == 200
    data = res_ok.get_json()
    assert data['success'] is True

    # Check /api/me with session
    res_me = client.get('/api/me')
    assert res_me.status_code == 200
    assert res_me.get_json()['user']['username'] == 'test_alice'

def test_rooms_api(client):
    """Test getting rooms list while authenticated."""
    # Authenticate client
    client.post('/api/login', json={
        'username': 'test_alice',
        'password': 'supersecret123'
    })

    res = client.get('/api/rooms')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    room_names = [r['name'] for r in data['rooms']]
    assert 'General' in room_names

    # Clean up any previous test room
    with db_connection() as db:
        db.execute("DELETE FROM rooms WHERE name = 'API Test Room'")

    # Test creating new room via POST /api/rooms
    post_res = client.post('/api/rooms', json={
        'name': 'API Test Room',
        'description': 'Created via REST API'
    })
    assert post_res.status_code == 201
    assert post_res.get_json()['success'] is True
    assert post_res.get_json()['room']['name'] == 'API Test Room'

def test_index_route(client):
    """Test index route renders HTML."""
    res = client.get('/')
    assert res.status_code == 200
    assert b'Chatty' in res.data
    assert b'id="app-container"' in res.data

def test_socketio_communication():
    """Test WebSocket connection, join_room, send_message, history, and disconnect."""
    from app import socketio

    # Clean up test users if they exist from previous runs
    with db_connection() as db:
        db.execute("DELETE FROM users WHERE username IN ('socket_alice', 'socket_bob')")

    # Create two test users and authenticate sessions
    with app.test_client() as c1:
        c1.post('/api/register', json={'username': 'socket_alice', 'password': 'password123'})
        s1 = socketio.test_client(app, flask_test_client=c1)
        assert s1.is_connected()

        # Alice joins General room
        s1.emit('join_room', {'room': 'General'})
        received = s1.get_received()
        events = [msg['name'] for msg in received]
        assert 'room_history' in events
        assert 'receive_message' in events  # Alice joined announcement

        # Verify system message for join
        join_msg = [m['args'][0] for m in received if m['name'] == 'receive_message'][0]
        assert join_msg['is_system'] is True
        assert 'socket_alice has joined the room' in join_msg['message']
        assert join_msg['timestamp'] is not None

        with app.test_client() as c2:
            c2.post('/api/register', json={'username': 'socket_bob', 'password': 'password123'})
            s2 = socketio.test_client(app, flask_test_client=c2)
            assert s2.is_connected()

            s2.emit('join_room', {'room': 'General'})
            s2_received = s2.get_received()

            # Alice receives Bob's join system message
            alice_new = s1.get_received()
            bob_join_for_alice = [m['args'][0] for m in alice_new if m['name'] == 'receive_message'][0]
            assert 'socket_bob has joined the room' in bob_join_for_alice['message']

            # Alice sends a message with emoji shortcode
            s1.emit('send_message', {'room': 'General', 'message': 'Hello Bob! :smile: :heart:'})

            # Bob receives Alice's message with parsed emojis and timestamp
            bob_msgs = s2.get_received()
            chat_msg = [m['args'][0] for m in bob_msgs if m['name'] == 'receive_message' and not m['args'][0]['is_system']][0]
            assert chat_msg['username'] == 'socket_alice'
            assert chat_msg['message'] == 'Hello Bob! 😄 ❤️'
            assert chat_msg['timestamp'] is not None

            # Verify message stored in SQLite
            with db_connection() as db:
                stored = db.execute("SELECT * FROM messages WHERE id = ?", (chat_msg['id'],)).fetchone()
                assert stored is not None
                assert stored['content'] == 'Hello Bob! 😄 ❤️'

            # Bob disconnects: Alice should receive disconnect notification
            s2.disconnect()
            after_disconnect = s1.get_received()
            disc_msgs = [m['args'][0] for m in after_disconnect if m['name'] == 'receive_message' and m['args'][0]['is_system']]
            assert any('socket_bob has disconnected' in m['message'] for m in disc_msgs)

        s1.disconnect()

