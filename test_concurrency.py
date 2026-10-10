import sys
import os
import time
import concurrent.futures

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app import app
from database import get_db_connection

def simulate_guest_landing(user_idx):
    """Simulate user opening the website root URL."""
    with app.test_client() as client:
        start = time.time()
        resp = client.get('/')
        duration = time.time() - start
        is_redirect_to_login = (resp.status_code == 302 and '/login' in resp.headers.get('Location', ''))
        return {
            'user_idx': user_idx,
            'type': 'guest_landing',
            'status': resp.status_code,
            'success': is_redirect_to_login,
            'duration_ms': duration * 1000
        }

def simulate_active_user(user_idx):
    """Simulate an active user browsing, searching, and viewing dishes."""
    with app.test_client() as client:
        start = time.time()
        # 1. Browse restaurants
        r1 = client.get('/restaurants')
        # 2. View restaurant detail
        r2 = client.get('/restaurants/1')
        # 3. Search query
        r3 = client.get('/search?q=pizza')
        # 4. View cart
        r4 = client.get('/cart')
        duration = time.time() - start
        success = (r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200 and r4.status_code == 200)
        return {
            'user_idx': user_idx,
            'type': 'active_browser',
            'status': r1.status_code,
            'success': success,
            'duration_ms': duration * 1000
        }

def simulate_concurrent_auth_and_cart(user_idx):
    """Simulate concurrent users adding items to cart and authenticating."""
    with app.test_client() as client:
        start = time.time()
        # Add item to unique guest cart
        add_res = client.post('/api/cart/add', json={
            'menu_item_id': 1 + (user_idx % 8),
            'quantity': 1,
            'modifiers': []
        })
        cart_res = client.get('/api/cart')
        duration = time.time() - start
        success = (add_res.status_code == 200 and cart_res.status_code == 200)
        return {
            'user_idx': user_idx,
            'type': 'cart_action',
            'status': add_res.status_code,
            'success': success,
            'duration_ms': duration * 1000
        }

def run_benchmark(total_users=1000, max_workers=50):
    print("=" * 70)
    print(f" [>] Running {total_users} Concurrent User Load Benchmark (Workers: {max_workers})")
    print("=" * 70)

    # Test 1: 1,000 Concurrent Guest Landings (Verify / -> /login redirect)
    print(f"\n[Test 1/3] Simulating {total_users} concurrent visitors opening the site...")
    start_time = time.time()
    results_landing = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(simulate_guest_landing, i) for i in range(total_users)]
        for f in concurrent.futures.as_completed(futures):
            results_landing.append(f.result())
    total_time = time.time() - start_time
    success_count = sum(1 for r in results_landing if r['success'])
    avg_latency = sum(r['duration_ms'] for r in results_landing) / len(results_landing)
    print(f" [PASS] Completed {total_users} landing requests in {total_time:.2f}s")
    print(f" [PASS] Success Rate (Redirect to /login): {success_count}/{total_users} ({success_count/total_users*100:.1f}%)")
    print(f" [PASS] Average Latency: {avg_latency:.2f} ms")
    print(f" [PASS] Throughput: {total_users/total_time:.1f} requests/sec")
    assert success_count == total_users, f"Expected 100% success, got {success_count}/{total_users}"

    # Test 2: 1,000 Concurrent Active Browsing Sessions
    print(f"\n[Test 2/3] Simulating {total_users} concurrent multi-page browsing sessions (4,000 total HTTP queries)...")
    start_time = time.time()
    results_browsing = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(simulate_active_user, i) for i in range(total_users)]
        for f in concurrent.futures.as_completed(futures):
            results_browsing.append(f.result())
    total_time = time.time() - start_time
    success_count = sum(1 for r in results_browsing if r['success'])
    avg_latency = sum(r['duration_ms'] for r in results_browsing) / len(results_browsing)
    print(f" [PASS] Completed {total_users * 4} HTTP operations across {total_users} concurrent users in {total_time:.2f}s")
    print(f" [PASS] Success Rate: {success_count}/{total_users} ({success_count/total_users*100:.1f}%)")
    print(f" [PASS] Average Session Latency (4 pages): {avg_latency:.2f} ms")
    print(f" [PASS] Throughput: {(total_users * 4)/total_time:.1f} requests/sec")
    assert success_count == total_users, f"Expected 100% success, got {success_count}/{total_users}"

    # Test 3: 1,000 Concurrent Database Writes / Cart Sessions
    print(f"\n[Test 3/3] Simulating {total_users} concurrent cart additions (SQLite WAL concurrent write & read)...")
    start_time = time.time()
    results_cart = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(simulate_concurrent_auth_and_cart, i) for i in range(total_users)]
        for f in concurrent.futures.as_completed(futures):
            results_cart.append(f.result())
    total_time = time.time() - start_time
    success_count = sum(1 for r in results_cart if r['success'])
    avg_latency = sum(r['duration_ms'] for r in results_cart) / len(results_cart)
    print(f" [PASS] Completed {total_users * 2} cart write/read operations in {total_time:.2f}s")
    print(f" [PASS] Success Rate (0 database locks): {success_count}/{total_users} ({success_count/total_users*100:.1f}%)")
    print(f" [PASS] Average Latency: {avg_latency:.2f} ms")
    print(f" [PASS] Throughput: {(total_users * 2)/total_time:.1f} requests/sec")
    assert success_count == total_users, f"Expected 100% success, got {success_count}/{total_users}"

    print("\n" + "=" * 70)
    print(" [SUCCESS] ALL 1,000 CONCURRENT USER BENCHMARKS PASSED (100% SUCCESS RATE)!")
    print("=" * 70)

if __name__ == '__main__':
    run_benchmark(total_users=1000, max_workers=50)
