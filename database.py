import sqlite3
import os
import json
from config import Config

from typing import Any, Sequence

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(Config.DATABASE_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def query_db(query: str, args: Sequence[Any] | tuple[Any, ...] = (), one: bool = False) -> Any:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    finally:
        conn.close()

def execute_db(query: str, args: Sequence[Any] | tuple[Any, ...] = (), commit: bool = True) -> Any:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        if commit:
            conn.commit()
        last_id = cur.lastrowid
        return last_id
    finally:
        conn.close()

def init_db(drop_all=False):
    conn = get_db_connection()
    cur = conn.cursor()

    if drop_all:
        tables = [
            'favorites', 'reviews', 'order_items', 'orders', 'couriers',
            'promo_codes', 'payment_methods', 'addresses', 'cart_items',
            'modifier_options', 'modifier_groups', 'menu_items',
            'menu_categories', 'cuisines', 'restaurants', 'users'
        ]
        for t in tables:
            cur.execute(f"DROP TABLE IF EXISTS {t}")
        conn.commit()

    cur.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        phone TEXT,
        role TEXT DEFAULT 'customer', -- 'customer', 'restaurant', 'courier', 'admin'
        avatar_url TEXT,
        loyalty_points INTEGER DEFAULT 250,
        member_tier TEXT DEFAULT 'Gold VIP', -- 'Bronze', 'Silver', 'Gold VIP', 'Platinum'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        cuisine TEXT NOT NULL,
        rating REAL DEFAULT NULL,
        review_count INTEGER DEFAULT 0,
        delivery_time_min INTEGER DEFAULT 20,
        delivery_time_max INTEGER DEFAULT 35,
        delivery_fee REAL DEFAULT 2.99,
        min_order REAL DEFAULT 15.00,
        price_level TEXT DEFAULT '$$', -- '$', '$$', '$$$', '$$$$'
        image_url TEXT NOT NULL,
        logo_url TEXT,
        address TEXT NOT NULL,
        lat REAL DEFAULT 40.7128,
        lng REAL DEFAULT -74.0060,
        is_open INTEGER DEFAULT 1,
        is_busy INTEGER DEFAULT 0,
        is_featured INTEGER DEFAULT 0,
        tags TEXT, -- JSON array string
        description TEXT,
        phone TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS cuisines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        icon TEXT NOT NULL,
        image_url TEXT NOT NULL,
        restaurant_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS menu_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        restaurant_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        image_url TEXT NOT NULL,
        is_vegetarian INTEGER DEFAULT 0,
        is_vegan INTEGER DEFAULT 0,
        is_gluten_free INTEGER DEFAULT 0,
        is_spicy INTEGER DEFAULT 0,
        is_popular INTEGER DEFAULT 0,
        is_available INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES menu_categories (id) ON DELETE CASCADE,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS modifier_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu_item_id INTEGER NOT NULL,
        name TEXT NOT NULL, -- e.g. "Choose Size", "Spice Level", "Add-ons"
        min_selection INTEGER DEFAULT 0,
        max_selection INTEGER DEFAULT 1,
        is_required INTEGER DEFAULT 0,
        FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS modifier_options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modifier_group_id INTEGER NOT NULL,
        name TEXT NOT NULL, -- e.g. "Regular 10\"", "Large 14\"", "Extra Truffle Glaze"
        price_delta REAL DEFAULT 0.00,
        is_default INTEGER DEFAULT 0,
        stock_quantity INTEGER DEFAULT 50, -- Daily stock available for this size/option
        FOREIGN KEY (modifier_group_id) REFERENCES modifier_groups (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        user_id INTEGER,
        menu_item_id INTEGER NOT NULL,
        restaurant_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        special_instructions TEXT,
        selected_modifiers_json TEXT, -- JSON array of selected modifiers
        item_total REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE CASCADE,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        label TEXT NOT NULL, -- "Home", "Work", "Other"
        street TEXT NOT NULL,
        apartment TEXT,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        zip_code TEXT NOT NULL,
        instructions TEXT,
        is_default INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL, -- "card", "upi", "netbanking", "wallet", "cod"
        card_brand TEXT, -- "Visa", "Mastercard", "Amex", "RuPay", "ApplePay"
        last4 TEXT,
        exp_month TEXT,
        exp_year TEXT,
        upi_id TEXT, -- e.g. "alex@okaxis"
        bank_name TEXT, -- e.g. "HDFC Bank"
        is_default INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS promo_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_type TEXT NOT NULL, -- "percent", "fixed"
        discount_value REAL NOT NULL,
        min_spend REAL DEFAULT 0.0,
        max_discount REAL DEFAULT 50.0,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        expires_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS couriers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        vehicle_type TEXT DEFAULT 'Motorcycle',
        vehicle_plate TEXT DEFAULT 'NYC-7892',
        rating REAL DEFAULT NULL,
        total_trips INTEGER DEFAULT 0,
        is_online INTEGER DEFAULT 1,
        current_lat REAL DEFAULT 40.7128,
        current_lng REAL DEFAULT -74.0060,
        avatar_url TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL,
        restaurant_id INTEGER NOT NULL,
        courier_id INTEGER,
        status TEXT DEFAULT 'placed', -- 'placed', 'confirmed', 'preparing', 'ready', 'picked_up', 'on_the_way', 'delivered', 'cancelled'
        subtotal REAL NOT NULL,
        delivery_fee REAL DEFAULT 0.0,
        service_fee REAL DEFAULT 0.0,
        tax REAL DEFAULT 0.0,
        tip REAL DEFAULT 0.0,
        discount REAL DEFAULT 0.0,
        total REAL NOT NULL,
        promo_code TEXT,
        delivery_address_json TEXT NOT NULL,
        delivery_instructions TEXT,
        payment_method TEXT NOT NULL,
        delivery_type TEXT DEFAULT 'delivery', -- 'delivery', 'pickup'
        estimated_delivery_time TEXT,
        courier_lat REAL,
        courier_lng REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE,
        FOREIGN KEY (courier_id) REFERENCES couriers (id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        menu_item_id INTEGER,
        name TEXT NOT NULL,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        modifiers_summary TEXT,
        total_price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
        FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        restaurant_id INTEGER,
        menu_item_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE,
        FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE CASCADE
    );
    ''')

    conn.commit()
    conn.close()
    ensure_schema_migrations()

def ensure_schema_migrations():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(restaurants)")
        cols = [r['name'] if isinstance(r, sqlite3.Row) else r[1] for r in cur.fetchall()]
        if 'lat' not in cols:
            cur.execute("ALTER TABLE restaurants ADD COLUMN lat REAL DEFAULT 40.7128")
        if 'lng' not in cols:
            cur.execute("ALTER TABLE restaurants ADD COLUMN lng REAL DEFAULT -74.0060")

        cur.execute("PRAGMA table_info(modifier_options)")
        mod_cols = [r['name'] if isinstance(r, sqlite3.Row) else r[1] for r in cur.fetchall()]
        if 'stock_quantity' not in mod_cols:
            cur.execute("ALTER TABLE modifier_options ADD COLUMN stock_quantity INTEGER DEFAULT 50")

        conn.commit()
    except Exception as e:
        print("Migration note:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
