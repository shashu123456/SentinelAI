import sys
import os
sys.path.insert(0, '.')

# Force a writable database path
os.environ['SESSION_STORE_DB'] = os.path.join(os.getcwd(), "sessions_test.db")

from app.core.execution.session_store import SessionStore

# Test create and get
store = SessionStore(os.environ['SESSION_STORE_DB'])

# Create session
session = store.create_session(
    session_id="store-test-session",
    agent_id="test-agent",
    target_path="/tmp/test",
    config={"timeout": 30.0},
)

print(f"Created session: {session.session_id}")
print(f"Session status: {session.status}")
print(f"Session created_at: {session.created_at}")
print(f"Session updated_at: {session.updated_at}")

# Retrieve session
retrieved = store.get_session("store-test-session")
print(f"Retrieved session: {retrieved.session_id if retrieved else None}")

if retrieved:
    print(f"Retrieved status: {retrieved.status}")
    print(f"Retrieved updated_at: {retrieved.updated_at}")
else:
    print("FAILED: Retrieved is None!")

# List sessions
sessions = store.list_sessions()
print(f"List sessions count: {len(sessions)}")

# Delete session
deleted = store.delete_session("store-test-session")
print(f"Deleted: {deleted}")

# Verify delete
after_delete = store.get_session("store-test-session")
print(f"After delete: {after_delete}")

print("\n--- All basic tests completed ---")
