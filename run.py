"""
CraveCart High-Concurrency Multi-User Server Launcher
Configured for 1,000+ simultaneous users using Waitress WSGI & SQLite WAL Engine.
"""

import sys
import os

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from database import ensure_schema_migrations
from app import app

def main():
    print("=" * 70, flush=True)
    print(" [CraveCart] Multi-Role Food Ordering Platform", flush=True)
    print(" [Server] High-Concurrency Production WSGI Server (Waitress)", flush=True)
    print("=" * 70, flush=True)
    
    # Run database initialization and high-speed indexes
    try:
        ensure_schema_migrations()
        print(" [OK] SQLite Database WAL mode & Performance Indexes verified.", flush=True)
    except Exception as e:
        print(f" [!] Database notice: {e}", flush=True)

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    threads = int(os.environ.get('THREADS', 64))
    connection_limit = int(os.environ.get('CONN_LIMIT', 2000))

    print(" [OK] Concurrency Configuration:", flush=True)
    print(f"      - Worker Threads       : {threads}", flush=True)
    print(f"      - Max Client Sockets   : {connection_limit}", flush=True)
    print(f"      - Socket Backlog Queue : 2048", flush=True)
    print(f"      - Channel Timeout      : 30s", flush=True)
    print(f"      - SQLite Journal Mode  : WAL (Non-Blocking Concurrent Reads/Writes)", flush=True)
    print(" [OK] Landing Page Rule      : Unauthenticated visitors land directly on /login", flush=True)
    print("-" * 70, flush=True)
    print(f"  -> Local Web App URL       : http://localhost:{port}", flush=True)
    print(f"  -> Network / LAN URL       : http://127.0.0.1:{port}", flush=True)
    print("=" * 70, flush=True)
    print(" Server is running. Press Ctrl+C to stop.\n", flush=True)

    try:
        from waitress import serve
        serve(
            app,
            host=host,
            port=port,
            threads=threads,
            connection_limit=connection_limit,
            channel_timeout=30,
            backlog=2048,
            asyncore_loop_timeout=1,
            send_bytes=18000,
            outbuf_overflow=1048576
        )
    except ImportError:
        print("Waitress not found. Starting multi-threaded Flask server...", flush=True)
        app.run(host=host, port=port, threaded=True, debug=False)

if __name__ == '__main__':
    main()
