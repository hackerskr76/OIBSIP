import pytest
from app import app, socketio, db_connection

def test_full_multidevice_workflow():
    """
    Simulates two devices (Device 1 and Device 2) interacting across:
    1. Simultaneous sessions
    2. Room creation via HTTP REST and WebSocket
    3. Cross-device real-time event broadcasting
    4. Room join and message exchange
    5. Room list synchronization
    """
    dev1_client = app.test_client()
    dev2_client = app.test_client()

    with db_connection() as db:
        db.execute("DELETE FROM users WHERE username IN ('dev1_user', 'dev2_user')")
        db.execute("DELETE FROM rooms WHERE name IN ('DeviceSyncRoom1', 'DeviceSyncRoom2')")

    # 1. Register users on both devices
    r1 = dev1_client.post('/api/register', json={'username': 'dev1_user', 'password': 'password123'})
    assert r1.status_code == 201

    r2 = dev2_client.post('/api/register', json={'username': 'dev2_user', 'password': 'password123'})
    assert r2.status_code == 201

    # 2. Connect WebSockets for both devices
    s1 = socketio.test_client(app, flask_test_client=dev1_client)
    s2 = socketio.test_client(app, flask_test_client=dev2_client)

    assert s1.is_connected()
    assert s2.is_connected()

    # Flush connect welcome events
    s1.get_received()
    s2.get_received()

    # 3. Device 1 creates a new room via HTTP POST /api/rooms
    create_res = dev1_client.post('/api/rooms', json={
        'name': 'DeviceSyncRoom1',
        'description': 'Created by Device 1'
    })
    assert create_res.status_code == 201
    room1_data = create_res.get_json()['room']
    assert room1_data['name'] == 'DeviceSyncRoom1'

    # 4. Device 2 MUST receive 'new_room_created' event in real-time
    dev2_events = s2.get_received()
    room_created_events = [m for m in dev2_events if m['name'] == 'new_room_created']
    assert len(room_created_events) > 0, "Device 2 did not receive new_room_created event!"
    assert room_created_events[0]['args'][0]['name'] == 'DeviceSyncRoom1'

    # Device 1 also receives 'new_room_created'
    dev1_events = s1.get_received()
    assert any(m['name'] == 'new_room_created' and m['args'][0]['name'] == 'DeviceSyncRoom1' for m in dev1_events)

    # 5. Device 1 joins 'DeviceSyncRoom1'
    s1.emit('join_room', {'room': 'DeviceSyncRoom1'})
    s1.get_received()

    # 6. Device 2 joins 'DeviceSyncRoom1'
    s2.emit('join_room', {'room': 'DeviceSyncRoom1'})
    s2_join_events = s2.get_received()
    assert any(m['name'] == 'room_history' for m in s2_join_events)

    # Device 1 gets notification that Device 2 joined
    s1_join_alerts = s1.get_received()
    assert any('dev2_user has joined the room' in str(m) for m in s1_join_alerts)

    # 7. Device 1 sends message
    s1.emit('send_message', {'room': 'DeviceSyncRoom1', 'message': 'Hello from Device 1! :fire:'})

    # Device 2 receives the message
    s2_msgs = s2.get_received()
    chat_events = [m['args'][0] for m in s2_msgs if m['name'] == 'receive_message' and not m['args'][0]['is_system']]
    assert len(chat_events) == 1
    assert chat_events[0]['message'] == 'Hello from Device 1! 🔥'
    assert chat_events[0]['username'] == 'dev1_user'

    # 8. Device 2 creates a second room via WebSocket 'create_room'
    s2.emit('create_room', {'name': 'DeviceSyncRoom2', 'description': 'Created by Device 2 via Socket'})
    s2_sock_events = s2.get_received()
    assert any(m['name'] == 'room_created_success' for m in s2_sock_events)

    # Device 1 receives 'new_room_created' for Room 2
    s1_sock_events = s1.get_received()
    assert any(m['name'] == 'new_room_created' and m['args'][0]['name'] == 'DeviceSyncRoom2' for m in s1_sock_events)

    # 9. Verify REST endpoint /api/rooms returns both rooms for both devices
    list_res1 = dev1_client.get('/api/rooms')
    list_res2 = dev2_client.get('/api/rooms')
    assert list_res1.status_code == 200
    assert list_res2.status_code == 200
    names1 = [r['name'] for r in list_res1.get_json()['rooms']]
    names2 = [r['name'] for r in list_res2.get_json()['rooms']]
    assert 'DeviceSyncRoom1' in names1 and 'DeviceSyncRoom2' in names1
    assert 'DeviceSyncRoom1' in names2 and 'DeviceSyncRoom2' in names2

    s1.disconnect()
    s2.disconnect()
