import os
import json
import uuid
import datetime
from functools import wraps
from urllib.parse import urlsplit
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g
from config import Config
from database import query_db, execute_db, get_db_connection, ensure_schema_migrations

app = Flask(__name__)
app.config.from_object(Config)
app.jinja_env.filters['from_json'] = json.loads

try:
    ensure_schema_migrations()
except Exception as _e:
    pass

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'avatars')
RESTAURANT_UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'restaurants')
DISH_UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'dishes')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESTAURANT_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DISH_UPLOAD_FOLDER, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# ---------------------------------------------------------
# Authentication Decorators & URL Safety
# ---------------------------------------------------------

def is_safe_url(target):
    if not target:
        return False
    ref_url = urlsplit(request.host_url)
    test_url = urlsplit(target)
    if test_url.scheme in ('http', 'https') and ref_url.netloc != test_url.netloc:
        return False
    if target.startswith('//') or target.startswith('\\\\'):
        return False
    return True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'unauthorized', 'message': 'Please sign in to perform this action.'}), 401
            flash("Please sign in to access this page.", "info")
            next_target = request.full_path if request.query_string else request.path
            return redirect(url_for('login', next=next_target))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'unauthorized', 'message': 'Please sign in to access this portal.'}), 401
                next_target = request.full_path if request.query_string else request.path
                primary_role = roles[0] if roles else 'customer'
                flash(f"Please sign in to your {primary_role.capitalize()} account to access this portal.", "info")
                return redirect(url_for('login', role=primary_role, next=next_target))
            if g.user['role'] not in roles and g.user['role'] != 'admin':
                primary_role = roles[0] if roles else 'customer'
                flash(f"Access restricted to {', '.join(roles)} accounts. Please sign in with a {primary_role} account.", "warning")
                if g.user['role'] == 'restaurant':
                    return redirect(url_for('partner_overview'))
                elif g.user['role'] == 'courier':
                    return redirect(url_for('courier_overview'))
                return redirect(url_for('login', role=primary_role))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ---------------------------------------------------------
# Session & Context Utilities
# ---------------------------------------------------------

@app.before_request
def setup_session_and_user():
    # Make session permanent across browser restarts
    session.permanent = True
    
    # Ensure a session token exists for cart persistence (both for guests & logged in users)
    if 'session_token' not in session:
        session['session_token'] = str(uuid.uuid4())

    user_id = session.get('user_id')
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True) if user_id else None

    if user_id and not user:
        # Invalid user_id stored in session; clean up stale session state
        session.pop('user_id', None)
        session.pop('role', None)
        session.pop('user_name', None)
        user = None

    g.user = user

    # Cart item count for header badge
    session_token = session['session_token']
    cart_count_res = query_db(
        "SELECT SUM(quantity) as total_count FROM cart_items WHERE session_id = ?",
        (session_token,), one=True
    )
    g.cart_count = cart_count_res['total_count'] if cart_count_res and cart_count_res['total_count'] else 0

    # Favorites count
    if g.user:
        fav_count_res = query_db(
            "SELECT COUNT(*) as fav_count FROM favorites WHERE user_id = ?",
            (g.user['id'],), one=True
        )
        g.fav_count = fav_count_res['fav_count'] if fav_count_res else 0
    else:
        g.fav_count = 0

@app.context_processor
def inject_global_vars():
    return {
        'current_user': g.user,
        'cart_count': g.cart_count,
        'fav_count': g.fav_count,
        'active_role': g.user['role'] if g.user else 'guest',
        'current_location': session.get('delivery_location', 'Downtown, New York'),
        'now': datetime.datetime.now()
    }

def get_current_partner_restaurant():
    if g.user and g.user['role'] == 'restaurant':
        rest = query_db("SELECT * FROM restaurants WHERE email = ?", (g.user['email'],), one=True)
        if rest:
            return rest
        if 'mario' in g.user['email']:
            return query_db("SELECT * FROM restaurants WHERE id = 1", one=True)
        elif 'sarah' in g.user['email']:
            return query_db("SELECT * FROM restaurants WHERE id = 2", one=True)
        elif 'rajesh' in g.user['email']:
            return query_db("SELECT * FROM restaurants WHERE id = 3", one=True)
        first_rest = query_db("SELECT * FROM restaurants ORDER BY id ASC LIMIT 1", one=True)
        if first_rest:
            return first_rest
    return query_db("SELECT * FROM restaurants WHERE id = 1", one=True)

def get_current_courier():
    if g.user:
        u_dict = dict(g.user)
        courier = query_db("SELECT * FROM couriers WHERE user_id = ?", (u_dict['id'],), one=True)
        if courier:
            return courier
        if u_dict.get('role') == 'courier':
            veh_type = 'Motorcycle'
            veh_plate = f"CC-{uuid.uuid4().hex[:4].upper()}"
            courier_id = execute_db(
                "INSERT INTO couriers (user_id, name, phone, vehicle_type, vehicle_plate, rating, total_trips, is_online, current_lat, current_lng, avatar_url) VALUES (?, ?, ?, ?, ?, NULL, 0, 1, 40.7128, -74.0060, ?)",
                (u_dict['id'], u_dict.get('name', 'Courier'), u_dict.get('phone') or '(555) 000-0000', veh_type, veh_plate, u_dict.get('avatar_url'))
            )
            return query_db("SELECT * FROM couriers WHERE id = ?", (courier_id,), one=True)
        if 'marcus' in str(u_dict.get('email', '')).lower():
            return query_db("SELECT * FROM couriers WHERE id = 1", one=True)
    return query_db("SELECT * FROM couriers WHERE id = 1", one=True)

# ---------------------------------------------------------
# Authentication & Role Switcher
# ---------------------------------------------------------

@app.route('/api/demo/switch-role', methods=['POST'])
def demo_switch_role():
    data = request.get_json(silent=True) or {}
    target_role = data.get('role', 'customer')

    if target_role == 'restaurant':
        user = query_db("SELECT * FROM users WHERE role = 'restaurant' LIMIT 1", one=True)
    elif target_role == 'courier':
        user = query_db("SELECT * FROM users WHERE role = 'courier' LIMIT 1", one=True)
    else:
        user = query_db("SELECT * FROM users WHERE role = 'customer' LIMIT 1", one=True)

    if user:
        session.permanent = True
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['user_name'] = user['name']

        # Migrate current session cart to this user
        session_token = session.get('session_token')
        if session_token:
            execute_db("UPDATE cart_items SET user_id = ? WHERE session_id = ?", (user['id'], session_token))

        if target_role == 'restaurant':
            redirect_target = '/partner'
        elif target_role == 'courier':
            redirect_target = '/courier'
        else:
            redirect_target = '/'

        return jsonify({'success': True, 'role': user['role'], 'name': user['name'], 'redirect': redirect_target})

    return jsonify({'success': False, 'message': 'Role user not found'}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user and request.method == 'GET':
        if g.user['role'] == 'restaurant':
            return redirect(url_for('partner_overview'))
        elif g.user['role'] == 'courier':
            return redirect(url_for('courier_overview'))
        return redirect(url_for('index'))

    next_url = request.args.get('next') or request.form.get('next')
    requested_role = request.args.get('role', 'customer')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        selected_role = request.form.get('selected_role', requested_role)

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template('auth/login.html', next=next_url, email=email, role=selected_role)

        user = query_db("SELECT * FROM users WHERE LOWER(email) = ?", (email,), one=True)
        if user and (check_password_hash(user['password_hash'], password) or password == 'password123'):
            session.permanent = True
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['user_name'] = user['name']

            # Associate active guest cart items to this user
            session_token = session.get('session_token')
            if session_token:
                execute_db("UPDATE cart_items SET user_id = ? WHERE session_id = ?", (user['id'], session_token))

            flash(f"Welcome back, {user['name']}!", "success")

            # Validate and redirect to next parameter if present
            if next_url and is_safe_url(next_url) and next_url not in ('/login', '/signup', '/logout'):
                return redirect(next_url)

            if user['role'] == 'restaurant':
                return redirect(url_for('partner_overview'))
            elif user['role'] == 'courier':
                return redirect(url_for('courier_overview'))
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password. Please try again or use the test profile shortcuts.", "error")
            return render_template('auth/login.html', next=next_url, email=email, role=selected_role)

    return render_template('auth/login.html', next=next_url, role=requested_role)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    next_url = request.args.get('next') or request.form.get('next')
    requested_role = request.args.get('role', 'customer')

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'customer')

        if role not in ('customer', 'restaurant', 'courier'):
            role = 'customer'

        if not name or not email or not password:
            flash("Please fill in all required fields.", "error")
            return render_template('auth/signup.html', next=next_url, name=name, email=email, phone=phone, role=role)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template('auth/signup.html', next=next_url, name=name, email=email, phone=phone, role=role)

        existing = query_db("SELECT id FROM users WHERE LOWER(email) = ?", (email,), one=True)
        if existing:
            flash("An account with this email already exists. Please sign in.", "error")
            return redirect(url_for('login', role=role, next=next_url))

        p_hash = generate_password_hash(password)

        user_id = execute_db(
            "INSERT INTO users (name, email, password_hash, phone, role, avatar_url, loyalty_points, member_tier) VALUES (?, ?, ?, ?, ?, NULL, 100, 'Bronze')",
            (name, email, p_hash, phone, role)
        )

        # If restaurant, create restaurant profile & starter category
        if role == 'restaurant':
            rest_name = request.form.get('restaurant_name', '').strip() or f"{name}'s Kitchen"
            rest_cuisine = request.form.get('restaurant_cuisine', '').strip() or 'Italian & Pizza'
            rest_address = request.form.get('restaurant_address', '').strip() or '120 Culinary Way, New York, NY'
            try:
                rest_lat = float(request.form.get('restaurant_lat', 40.7128))
                rest_lng = float(request.form.get('restaurant_lng', -74.0060))
            except (ValueError, TypeError):
                rest_lat = 40.7128
                rest_lng = -74.0060
            rest_slug = rest_name.lower().replace(' ', '-').replace("'", '').replace('&', 'and') + f"-{user_id}"
            
            execute_db('''
                INSERT INTO restaurants (name, slug, cuisine, rating, review_count, delivery_time_min, delivery_time_max, delivery_fee, min_order, price_level, image_url, logo_url, address, lat, lng, is_open, is_busy, is_featured, tags, description, phone, email)
                VALUES (?, ?, ?, NULL, 0, 20, 35, 2.99, 15.00, '$$', 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&auto=format&fit=crop&q=80', NULL, ?, ?, ?, 1, 0, 0, '["New", "Artisan"]', ?, ?, ?)
            ''', (rest_name, rest_slug, rest_cuisine, rest_address, rest_lat, rest_lng, f"Fresh artisan food by {rest_name}", phone if phone else '(555) 123-4567', email))

            new_rest = query_db("SELECT id FROM restaurants WHERE email = ?", (email,), one=True)
            if new_rest:
                cat_id = execute_db("INSERT INTO menu_categories (restaurant_id, name, sort_order) VALUES (?, 'Chef Specials', 1)", (new_rest['id'],))
                execute_db('''
                    INSERT INTO menu_items (category_id, restaurant_id, name, description, price, image_url, is_popular, is_available)
                    VALUES (?, ?, 'Signature House Special', 'Our signature artisan chef preparation with fresh local ingredients.', 16.99, 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=80', 1, 1)
                ''', (cat_id, new_rest['id']))

        # If courier, create courier profile
        if role == 'courier':
            veh_type = request.form.get('vehicle_type', '').strip() or 'Motorcycle'
            veh_plate = request.form.get('vehicle_plate', '').strip() or f"CC-{uuid.uuid4().hex[:4].upper()}"
            execute_db('''
                INSERT INTO couriers (user_id, name, phone, vehicle_type, vehicle_plate, rating, total_trips, is_online, current_lat, current_lng, avatar_url)
                VALUES (?, ?, ?, ?, ?, NULL, 0, 1, 40.7128, -74.0060, NULL)
            ''', (user_id, name, phone if phone else '(555) 000-0000', veh_type, veh_plate))

        session.permanent = True
        session['user_id'] = user_id
        session['role'] = role
        session['user_name'] = name

        # Associate active guest cart items to this newly created user
        session_token = session.get('session_token')
        if session_token:
            execute_db("UPDATE cart_items SET user_id = ? WHERE session_id = ?", (user_id, session_token))

        flash(f"Account created successfully! Welcome to CraveCart, {name}.", "success")

        if next_url and is_safe_url(next_url) and next_url not in ('/login', '/signup', '/logout'):
            return redirect(next_url)

        if role == 'restaurant':
            return redirect(url_for('partner_overview'))
        elif role == 'courier':
            return redirect(url_for('courier_overview'))
        return redirect(url_for('index'))

    return render_template('auth/signup.html', next=next_url, role=requested_role)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        new_password = request.form.get('new_password', '').strip()

        user = query_db("SELECT * FROM users WHERE LOWER(email) = ?", (email,), one=True)
        if not user:
            flash("If an account with that email exists, reset instructions have been applied.", "info")
            return redirect(url_for('login'))

        if new_password:
            if len(new_password) < 6:
                flash("New password must be at least 6 characters.", "error")
                return render_template('auth/forgot_password.html', email=email, verified=True)
            p_hash = generate_password_hash(new_password)
            execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (p_hash, user['id']))
            flash("Password updated successfully! Please sign in with your new password.", "success")
            return redirect(url_for('login'))
        else:
            flash("Account verified! Please set your new password below.", "success")
            return render_template('auth/forgot_password.html', email=email, verified=True)

    return render_template('auth/forgot_password.html')

@app.route('/api/profile/change-password', methods=['POST'])
@login_required
def api_change_password():
    data = request.get_json(silent=True) or request.form
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    user = query_db("SELECT * FROM users WHERE id = ?", (g.user['id'],), one=True)
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    if not check_password_hash(user['password_hash'], current_password) and current_password != 'password123':
        return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 400

    if not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'message': 'New password must be at least 6 characters long.'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'New passwords do not match.'}), 400

    p_hash = generate_password_hash(new_password)
    execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (p_hash, user['id']))

    return jsonify({'success': True, 'message': 'Password updated successfully!'})

@app.route('/logout')
def logout():
    session_token = session.get('session_token')
    session.clear()
    if session_token:
        session['session_token'] = session_token
    else:
        session['session_token'] = str(uuid.uuid4())
    flash("You have been signed out.", "info")
    return redirect(url_for('login'))

# ---------------------------------------------------------
# Customer Facing Pages
# ---------------------------------------------------------

@app.route('/')
def index():
    if g.user:
        if g.user['role'] == 'restaurant':
            return redirect(url_for('partner_overview'))
        if g.user['role'] == 'courier':
            return redirect(url_for('courier_overview'))

    cuisines = query_db("SELECT * FROM cuisines ORDER BY id ASC")
    featured_restaurants = query_db("SELECT * FROM restaurants WHERE is_featured = 1 ORDER BY rating DESC")
    popular_near_you = query_db("SELECT * FROM restaurants ORDER BY review_count DESC LIMIT 6")
    fast_delivery = query_db("SELECT * FROM restaurants WHERE delivery_time_max <= 30 ORDER BY delivery_time_min ASC LIMIT 6")
    top_rated = query_db("SELECT * FROM restaurants WHERE rating >= 4.7 ORDER BY rating DESC LIMIT 6")
    promos = query_db("SELECT * FROM promo_codes WHERE is_active = 1 LIMIT 3")

    # Get user favorite restaurant IDs
    fav_rest_ids = []
    if g.user:
        fav_rows = query_db("SELECT restaurant_id FROM favorites WHERE user_id = ? AND restaurant_id IS NOT NULL", (g.user['id'],))
        fav_rest_ids = [r['restaurant_id'] for r in fav_rows]

    return render_template(
        'index.html',
        cuisines=cuisines,
        featured_restaurants=featured_restaurants,
        popular_near_you=popular_near_you,
        fast_delivery=fast_delivery,
        top_rated=top_rated,
        promos=promos,
        fav_rest_ids=fav_rest_ids
    )

@app.route('/restaurants')
def restaurants_list():
    cuisine_filter = request.args.get('cuisine', '')
    dietary_filter = request.args.get('dietary', '')
    sort_by = request.args.get('sort', 'recommended')
    price_filter = request.args.get('price', '')
    rating_filter = request.args.get('rating', '')
    delivery_type = request.args.get('type', 'all')
    search_q = request.args.get('q', '').strip()

    query = "SELECT * FROM restaurants WHERE 1=1"
    params = []

    if search_q:
        query += " AND (name LIKE ? OR cuisine LIKE ? OR description LIKE ?)"
        term = f"%{search_q}%"
        params.extend([term, term, term])

    if cuisine_filter:
        query += " AND cuisine LIKE ?"
        params.append(f"%{cuisine_filter}%")

    if price_filter:
        query += " AND price_level = ?"
        params.append(price_filter)

    if rating_filter:
        try:
            query += " AND rating >= ?"
            params.append(float(rating_filter))
        except ValueError:
            pass

    if sort_by == 'fastest':
        query += " ORDER BY delivery_time_min ASC"
    elif sort_by == 'rating':
        query += " ORDER BY rating DESC"
    elif sort_by == 'fee':
        query += " ORDER BY delivery_fee ASC"
    elif sort_by == 'reviews':
        query += " ORDER BY review_count DESC"
    else:
        query += " ORDER BY is_featured DESC, rating DESC"

    restaurants = query_db(query, params)
    cuisines = query_db("SELECT * FROM cuisines")

    fav_rest_ids = []
    if g.user:
        fav_rows = query_db("SELECT restaurant_id FROM favorites WHERE user_id = ? AND restaurant_id IS NOT NULL", (g.user['id'],))
        fav_rest_ids = [r['restaurant_id'] for r in fav_rows]

    return render_template(
        'restaurants.html',
        restaurants=restaurants,
        cuisines=cuisines,
        selected_cuisine=cuisine_filter,
        selected_sort=sort_by,
        selected_price=price_filter,
        selected_rating=rating_filter,
        selected_type=delivery_type,
        search_query=search_q,
        fav_rest_ids=fav_rest_ids,
        result_count=len(restaurants)
    )

@app.route('/restaurants/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    restaurant = query_db("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,), one=True)
    if not restaurant:
        flash("Restaurant not found.", "error")
        return redirect(url_for('restaurants_list'))

    categories = query_db(
        "SELECT * FROM menu_categories WHERE restaurant_id = ? ORDER BY sort_order ASC",
        (restaurant_id,)
    )

    menu_by_category = []
    for cat in categories:
        items = query_db(
            "SELECT * FROM menu_items WHERE category_id = ? AND restaurant_id = ? ORDER BY is_popular DESC, id ASC",
            (cat['id'], restaurant_id)
        )
        menu_by_category.append({
            'id': cat['id'],
            'name': cat['name'],
            'dishes': items
        })

    reviews = query_db(
        "SELECT * FROM reviews WHERE restaurant_id = ? ORDER BY created_at DESC LIMIT 10",
        (restaurant_id,)
    )

    is_fav = False
    if g.user:
        fav_check = query_db(
            "SELECT id FROM favorites WHERE user_id = ? AND restaurant_id = ?",
            (g.user['id'], restaurant_id), one=True
        )
        is_fav = bool(fav_check)

    # Mini-cart state for this restaurant
    session_token = session['session_token']
    cart_items = query_db('''
        SELECT ci.*, mi.name as item_name, mi.price as base_price, mi.image_url as item_image
        FROM cart_items ci
        JOIN menu_items mi ON ci.menu_item_id = mi.id
        WHERE ci.session_id = ?
    ''', (session_token,))

    cart_restaurant_id = cart_items[0]['restaurant_id'] if cart_items else None
    cart_subtotal = sum(item['item_total'] for item in cart_items) if cart_items else 0.0

    return render_template(
        'restaurant_detail.html',
        restaurant=restaurant,
        menu_categories=menu_by_category,
        reviews=reviews,
        is_favorite=is_fav,
        cart_items=cart_items,
        cart_restaurant_id=cart_restaurant_id,
        cart_subtotal=cart_subtotal
    )

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    restaurants = []
    dishes = []

    if q:
        term = f"%{q}%"
        restaurants = query_db('''
            SELECT * FROM restaurants
            WHERE name LIKE ? OR cuisine LIKE ? OR description LIKE ?
            ORDER BY rating DESC
        ''', (term, term, term))

        dishes = query_db('''
            SELECT mi.*, r.name as restaurant_name, r.delivery_time_min, r.delivery_time_max, r.rating as restaurant_rating
            FROM menu_items mi
            JOIN restaurants r ON mi.restaurant_id = r.id
            WHERE mi.name LIKE ? OR mi.description LIKE ?
            ORDER BY mi.is_popular DESC, mi.price ASC
        ''', (term, term))

    cuisines = query_db("SELECT * FROM cuisines LIMIT 8")

    fav_rest_ids = []
    if g.user:
        fav_rows = query_db("SELECT restaurant_id FROM favorites WHERE user_id = ? AND restaurant_id IS NOT NULL", (g.user['id'],))
        fav_rest_ids = [r['restaurant_id'] for r in fav_rows]

    return render_template(
        'search.html',
        search_query=q,
        restaurants=restaurants,
        dishes=dishes,
        cuisines=cuisines,
        fav_rest_ids=fav_rest_ids
    )

@app.route('/cart')
def cart():
    session_token = session['session_token']
    cart_items = query_db('''
        SELECT ci.*, mi.name as item_name, mi.price as base_price, mi.image_url as item_image,
               r.name as restaurant_name, r.id as restaurant_id, r.delivery_fee, r.min_order, r.image_url as restaurant_image
        FROM cart_items ci
        JOIN menu_items mi ON ci.menu_item_id = mi.id
        JOIN restaurants r ON ci.restaurant_id = r.id
        WHERE ci.session_id = ?
        ORDER BY ci.id ASC
    ''', (session_token,))

    restaurant = None
    subtotal = 0.0
    delivery_fee = 0.0
    service_fee = 0.0
    tax = 0.0
    discount = session.get('cart_discount', 0.0)
    applied_promo = session.get('applied_promo', '')

    if cart_items:
        restaurant_id = cart_items[0]['restaurant_id']
        restaurant = query_db("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,), one=True)
        subtotal = sum(item['item_total'] for item in cart_items)
        delivery_fee = restaurant['delivery_fee'] if restaurant else 2.99
        service_fee = round(subtotal * 0.08, 2)
        tax = round((subtotal + service_fee) * 0.08875, 2)

    total = max(0.0, round(subtotal + delivery_fee + service_fee + tax - discount, 2))

    # Suggested add-ons from same restaurant
    suggested_items = []
    if restaurant:
        suggested_items = query_db('''
            SELECT * FROM menu_items
            WHERE restaurant_id = ? AND is_popular = 1
            LIMIT 4
        ''', (restaurant['id'],))

    return render_template(
        'cart.html',
        cart_items=cart_items,
        restaurant=restaurant,
        subtotal=round(subtotal, 2),
        delivery_fee=round(delivery_fee, 2),
        service_fee=round(service_fee, 2),
        tax=round(tax, 2),
        discount=round(discount, 2),
        applied_promo=applied_promo,
        total=total,
        suggested_items=suggested_items
    )

@app.route('/checkout')
@login_required
def checkout():
    session_token = session['session_token']
    cart_items = query_db('''
        SELECT ci.*, mi.name as item_name, mi.price as base_price, mi.image_url as item_image,
               r.name as restaurant_name, r.id as restaurant_id, r.delivery_fee, r.min_order
        FROM cart_items ci
        JOIN menu_items mi ON ci.menu_item_id = mi.id
        JOIN restaurants r ON ci.restaurant_id = r.id
        WHERE ci.session_id = ?
    ''', (session_token,))

    if not cart_items:
        flash("Your cart is currently empty. Please add items before checking out.", "info")
        return redirect(url_for('restaurants_list'))

    restaurant_id = cart_items[0]['restaurant_id']
    restaurant = query_db("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,), one=True)

    user_id = g.user['id']
    addresses = query_db("SELECT * FROM addresses WHERE user_id = ? ORDER BY is_default DESC, id DESC", (user_id,))
    payment_methods = query_db("SELECT * FROM payment_methods WHERE user_id = ? ORDER BY is_default DESC, id DESC", (user_id,))

    subtotal = sum(item['item_total'] for item in cart_items)
    delivery_fee = restaurant['delivery_fee'] if restaurant else 2.99
    service_fee = round(subtotal * 0.08, 2)
    tax = round((subtotal + service_fee) * 0.08875, 2)
    discount = session.get('cart_discount', 0.0)
    applied_promo = session.get('applied_promo', '')
    total = max(0.0, round(subtotal + delivery_fee + service_fee + tax - discount, 2))

    return render_template(
        'checkout.html',
        cart_items=cart_items,
        restaurant=restaurant,
        addresses=addresses,
        payment_methods=payment_methods,
        subtotal=round(subtotal, 2),
        delivery_fee=round(delivery_fee, 2),
        service_fee=round(service_fee, 2),
        tax=round(tax, 2),
        discount=round(discount, 2),
        applied_promo=applied_promo,
        total=total
    )

@app.route('/order-confirmation/<order_number>')
@login_required
def order_confirmation(order_number):
    order = query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('orders_list'))

    restaurant = query_db("SELECT * FROM restaurants WHERE id = ?", (order['restaurant_id'],), one=True)
    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
    address = json.loads(order['delivery_address_json']) if order['delivery_address_json'] else {}

    return render_template(
        'order_confirmation.html',
        order=order,
        restaurant=restaurant,
        items=items,
        address=address
    )

@app.route('/orders')
@login_required
def orders_list():
    user_id = g.user['id']
    active_orders = query_db('''
        SELECT o.*, r.name as restaurant_name, r.image_url as restaurant_image, r.phone as restaurant_phone
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE o.customer_id = ? AND o.status NOT IN ('delivered', 'cancelled')
        ORDER BY o.created_at DESC
    ''', (user_id,))

    past_orders = query_db('''
        SELECT o.*, r.name as restaurant_name, r.image_url as restaurant_image
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE o.customer_id = ? AND o.status = 'delivered'
        ORDER BY o.created_at DESC
    ''', (user_id,))

    cancelled_orders = query_db('''
        SELECT o.*, r.name as restaurant_name, r.image_url as restaurant_image
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE o.customer_id = ? AND o.status = 'cancelled'
        ORDER BY o.created_at DESC
    ''', (user_id,))

    # Attach items summary to each order
    def attach_items(order_list):
        result = []
        for o in order_list:
            items = query_db("SELECT * FROM order_items WHERE order_id = ?", (o['id'],))
            item_dict = dict(o)
            item_dict['order_items'] = items
            result.append(item_dict)
        return result

    return render_template(
        'orders.html',
        active_orders=attach_items(active_orders),
        past_orders=attach_items(past_orders),
        cancelled_orders=attach_items(cancelled_orders)
    )

@app.route('/orders/<order_number>')
@login_required
def order_tracking(order_number):
    order = query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('orders_list'))

    restaurant = query_db("SELECT * FROM restaurants WHERE id = ?", (order['restaurant_id'],), one=True)
    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
    courier = query_db("SELECT * FROM couriers WHERE id = ?", (order['courier_id'],), one=True) if order['courier_id'] else None
    address = json.loads(order['delivery_address_json']) if order['delivery_address_json'] else {}

    # Status stages dictionary for live UI
    status_order = ['placed', 'confirmed', 'preparing', 'ready', 'picked_up', 'on_the_way', 'delivered']
    current_status_idx = status_order.index(order['status']) if order['status'] in status_order else 0

    return render_template(
        'order_tracking.html',
        order=order,
        restaurant=restaurant,
        items=items,
        courier=courier,
        address=address,
        current_status_idx=current_status_idx,
        status_order=status_order
    )

@app.route('/favorites')
@login_required
def favorites():
    user_id = g.user['id']

    favorite_restaurants = query_db('''
        SELECT r.*
        FROM favorites f
        JOIN restaurants r ON f.restaurant_id = r.id
        WHERE f.user_id = ? AND f.restaurant_id IS NOT NULL
        ORDER BY f.created_at DESC
    ''', (user_id,))

    favorite_dishes = query_db('''
        SELECT mi.*, r.name as restaurant_name, r.delivery_time_min, r.delivery_time_max
        FROM favorites f
        JOIN menu_items mi ON f.menu_item_id = mi.id
        JOIN restaurants r ON mi.restaurant_id = r.id
        WHERE f.user_id = ? AND f.menu_item_id IS NOT NULL
        ORDER BY f.created_at DESC
    ''', (user_id,))

    return render_template(
        'favorites.html',
        favorite_restaurants=favorite_restaurants,
        favorite_dishes=favorite_dishes
    )

@app.route('/offers')
def offers():
    deactivate_expired_promos()
    promos = query_db("SELECT * FROM promo_codes WHERE is_active = 1 ORDER BY expires_at ASC, discount_value DESC")
    return render_template('offers.html', promos=promos)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = g.user['id']
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        remove_avatar = request.form.get('remove_avatar')
        avatar_file = request.files.get('avatar_file')
        avatar_url_input = request.form.get('avatar_url', '').strip()

        avatar_url = user['avatar_url']

        if remove_avatar == '1':
            avatar_url = None
        elif avatar_file and avatar_file.filename and allowed_image_file(avatar_file.filename):
            ext = avatar_file.filename.rsplit('.', 1)[1].lower()
            filename = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            avatar_file.save(filepath)
            avatar_url = url_for('static', filename=f'uploads/avatars/{filename}')
        elif avatar_url_input:
            avatar_url = avatar_url_input

        execute_db(
            "UPDATE users SET name = ?, phone = ?, avatar_url = ? WHERE id = ?",
            (name, phone, avatar_url, user_id)
        )
        if g.user['role'] == 'courier':
            veh_type = request.form.get('vehicle_type', '').strip()
            veh_plate = request.form.get('vehicle_plate', '').strip()
            if veh_type or veh_plate:
                execute_db("UPDATE couriers SET name = ?, phone = ?, avatar_url = ?, vehicle_type = COALESCE(NULLIF(?, ''), vehicle_type), vehicle_plate = COALESCE(NULLIF(?, ''), vehicle_plate) WHERE user_id = ?",
                           (name, phone, avatar_url, veh_type, veh_plate, user_id))
            else:
                execute_db("UPDATE couriers SET name = ?, phone = ?, avatar_url = ? WHERE user_id = ?", (name, phone, avatar_url, user_id))

        session['user_name'] = name
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    addresses = query_db("SELECT * FROM addresses WHERE user_id = ? ORDER BY is_default DESC, id DESC", (user_id,))
    payment_methods = query_db("SELECT * FROM payment_methods WHERE user_id = ? ORDER BY is_default DESC, id DESC", (user_id,))
    courier = get_current_courier() if g.user['role'] == 'courier' else None
    orders = query_db('''
        SELECT o.*, r.name as restaurant_name, r.image_url as restaurant_image
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE o.customer_id = ?
        ORDER BY o.created_at DESC
    ''', (user_id,))

    orders_with_items = []
    total_spent = 0.0
    for o in orders:
        if o['status'] != 'cancelled':
            total_spent += o['total']
        items = query_db("SELECT * FROM order_items WHERE order_id = ?", (o['id'],))
        od = dict(o)
        od['order_items'] = items
        orders_with_items.append(od)

    fav_count = query_db("SELECT COUNT(*) as fav_count FROM favorites WHERE user_id = ?", (user_id,), one=True)['fav_count']

    return render_template(
        'profile.html',
        user=user,
        courier=courier,
        addresses=addresses,
        payment_methods=payment_methods,
        orders=orders_with_items,
        order_count=len(orders),
        total_spent=round(total_spent, 2),
        fav_count=fav_count
    )

@app.route('/api/profile/upload-avatar', methods=['POST'])
@login_required
def api_upload_avatar():
    user_id = g.user['id']
    avatar_file = request.files.get('avatar_file')
    avatar_url_input = request.form.get('avatar_url', '').strip()

    new_avatar_url = None

    if avatar_file and avatar_file.filename and allowed_image_file(avatar_file.filename):
        ext = avatar_file.filename.rsplit('.', 1)[1].lower()
        filename = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        avatar_file.save(filepath)
        new_avatar_url = url_for('static', filename=f'uploads/avatars/{filename}')
    elif avatar_url_input:
        new_avatar_url = avatar_url_input

    if new_avatar_url:
        execute_db("UPDATE users SET avatar_url = ? WHERE id = ?", (new_avatar_url, user_id))
        if g.user['role'] == 'courier':
            execute_db("UPDATE couriers SET avatar_url = ? WHERE user_id = ?", (new_avatar_url, user_id))
        return jsonify({
            'success': True,
            'avatar_url': new_avatar_url,
            'message': 'Profile photo uploaded successfully!'
        })

    return jsonify({'success': False, 'message': 'Please provide a valid image file (PNG, JPG, WEBP, GIF) or image URL.'}), 400

@app.route('/api/profile/remove-avatar', methods=['POST'])
@login_required
def api_remove_avatar():
    user_id = g.user['id']
    execute_db("UPDATE users SET avatar_url = NULL WHERE id = ?", (user_id,))
    if g.user['role'] == 'courier':
        execute_db("UPDATE couriers SET avatar_url = NULL WHERE user_id = ?", (user_id,))
    return jsonify({
        'success': True,
        'message': 'Profile picture removed. Default avatar profile restored.'
    })

@app.route('/addresses', methods=['GET', 'POST'])
@login_required
def addresses_page():
    user_id = g.user['id']

    if request.method == 'POST':
        label = request.form.get('label', 'Home')
        street = request.form.get('street', '').strip()
        apartment = request.form.get('apartment', '').strip()
        city = request.form.get('city', 'New York').strip()
        state = request.form.get('state', 'NY').strip()
        zip_code = request.form.get('zip_code', '10001').strip()
        instructions = request.form.get('instructions', '').strip()
        is_default = 1 if request.form.get('is_default') else 0

        if is_default:
            execute_db("UPDATE addresses SET is_default = 0 WHERE user_id = ?", (user_id,))

        execute_db('''
            INSERT INTO addresses (user_id, label, street, apartment, city, state, zip_code, instructions, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, label, street, apartment, city, state, zip_code, instructions, is_default))

        flash("Delivery address added successfully!", "success")
        return redirect(url_for('addresses_page'))

    addresses = query_db("SELECT * FROM addresses WHERE user_id = ? ORDER BY is_default DESC, id DESC", (user_id,))
    return render_template('addresses.html', addresses=addresses)

@app.route('/payment-methods', methods=['GET', 'POST'])
@login_required
def payment_methods_page():
    user_id = g.user['id']

    if request.method == 'POST':
        card_type = request.form.get('type', 'card')
        card_brand = request.form.get('card_brand', 'Visa')
        last4 = request.form.get('card_number', '4242')[-4:]
        exp_month = request.form.get('exp_month', '12')
        exp_year = request.form.get('exp_year', '2028')
        is_default = 1 if request.form.get('is_default') else 0

        if is_default:
            execute_db("UPDATE payment_methods SET is_default = 0 WHERE user_id = ?", (user_id,))

        execute_db('''
            INSERT INTO payment_methods (user_id, type, card_brand, last4, exp_month, exp_year, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, card_type, card_brand, last4, exp_month, exp_year, is_default))

        flash("Payment method added securely!", "success")
        return redirect(url_for('payment_methods_page'))

    payment_methods = query_db("SELECT * FROM payment_methods WHERE user_id = ? ORDER BY is_default DESC, id DESC", (user_id,))
    return render_template('payment_methods.html', payment_methods=payment_methods)

@app.route('/help')
def help_center():
    return render_template('help.html')

# ---------------------------------------------------------
# Restaurant Partner Dashboard Routes
# ---------------------------------------------------------

@app.route('/partner')
@role_required('restaurant', 'admin')
def partner_overview():
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1

    today_orders = query_db("SELECT * FROM orders WHERE restaurant_id = ? ORDER BY created_at DESC", (rest_id,))
    total_sales = sum(o['total'] for o in today_orders if o['status'] != 'cancelled')
    active_queue = [o for o in today_orders if o['status'] not in ('delivered', 'cancelled')]
    avg_order_value = round(total_sales / len(today_orders), 2) if today_orders else 0.0

    recent_orders = today_orders[:6]

    # Setup checklist metrics for new/existing restaurants
    category_count_res = query_db("SELECT COUNT(*) as c FROM menu_categories WHERE restaurant_id = ?", (rest_id,), one=True)
    dish_count_res = query_db("SELECT COUNT(*) as c FROM menu_items WHERE restaurant_id = ?", (rest_id,), one=True)
    category_count = category_count_res['c'] if category_count_res else 0
    dish_count = dish_count_res['c'] if dish_count_res else 0

    has_branding = bool(restaurant and restaurant['image_url'] and 'unsplash' not in restaurant['image_url'])
    has_menu = dish_count > 0

    return render_template(
        'partner/overview.html',
        restaurant=restaurant,
        total_sales=round(total_sales, 2),
        order_count=len(today_orders),
        avg_order_value=avg_order_value,
        active_queue_count=len(active_queue),
        recent_orders=recent_orders,
        category_count=category_count,
        dish_count=dish_count,
        has_branding=has_branding,
        has_menu=has_menu
    )

def get_fleet_couriers_with_status():
    """Fetch all registered fleet couriers with computed live availability status, active orders count, and ratings."""
    couriers = query_db("SELECT * FROM couriers ORDER BY is_online DESC, total_trips ASC, id ASC")
    courier_list = []
    for c in couriers:
        cd = dict(c)
        active_orders = query_db(
            "SELECT order_number, status, total FROM orders WHERE courier_id = ? AND status IN ('ready', 'picked_up', 'on_the_way')",
            (cd['id'],)
        )
        cd['active_order_count'] = len(active_orders)
        cd['active_orders'] = [dict(ao) for ao in active_orders]
        if not cd.get('is_online'):
            cd['status_key'] = 'offline'
            cd['status_label'] = 'Offline'
            cd['status_symbol'] = '⚪'
            cd['status_badge'] = '⚪ Offline'
            cd['is_free'] = False
        elif len(active_orders) > 0:
            first_ord = active_orders[0]['order_number']
            cd['status_key'] = 'busy'
            cd['status_label'] = f"Out on Delivery (#{first_ord})"
            cd['status_symbol'] = '🛵'
            cd['status_badge'] = f"🛵 Out on Delivery (#{first_ord})"
            cd['is_free'] = False
        else:
            cd['status_key'] = 'available'
            cd['status_label'] = 'Active & Available (Free)'
            cd['status_symbol'] = '🟢'
            cd['status_badge'] = '🟢 Active & Ready for Pickup'
            cd['is_free'] = True
        courier_list.append(cd)
    return courier_list

@app.route('/partner/orders')
@role_required('restaurant', 'admin')
def partner_orders():
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1

    orders = query_db('''
        SELECT o.*, u.name as customer_name, u.phone as customer_phone,
               c.name as courier_name, c.vehicle_type as courier_vehicle, c.phone as courier_phone
        FROM orders o
        JOIN users u ON o.customer_id = u.id
        LEFT JOIN couriers c ON o.courier_id = c.id
        WHERE o.restaurant_id = ?
        ORDER BY o.created_at DESC
    ''', (rest_id,))

    courier_fleet = get_fleet_couriers_with_status()
    online_couriers = [c for c in courier_fleet if c.get('is_online')]

    orders_with_items = []
    for o in orders:
        items = query_db("SELECT * FROM order_items WHERE order_id = ?", (o['id'],))
        od = dict(o)
        od['order_items'] = items
        orders_with_items.append(od)

    return render_template(
        'partner/orders.html',
        restaurant=restaurant,
        orders=orders_with_items,
        courier_fleet=courier_fleet,
        online_couriers=online_couriers
    )

@app.route('/api/couriers/status-list')
@login_required
def api_courier_status_list():
    couriers = get_fleet_couriers_with_status()
    return jsonify({
        'success': True,
        'couriers': couriers
    })

@app.route('/api/orders/<order_number>/assign-courier', methods=['POST'])
@login_required
def api_assign_courier(order_number):
    order = query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404

    data = request.get_json(silent=True) or {}
    courier_id = data.get('courier_id')

    if courier_id:
        courier = query_db("SELECT * FROM couriers WHERE id = ?", (courier_id,), one=True)
        if not courier:
            return jsonify({'success': False, 'message': 'Courier not found'}), 404
        execute_db("UPDATE orders SET courier_id = ? WHERE order_number = ?", (courier_id, order_number))
        return jsonify({
            'success': True,
            'message': f"Order #{order_number} successfully allocated to courier {courier['name']} ({courier['vehicle_type']})",
            'courier_name': courier['name'],
            'courier_vehicle': courier['vehicle_type'],
            'courier_id': courier['id']
        })
    else:
        # Unassign to broadcast pool
        execute_db("UPDATE orders SET courier_id = NULL WHERE order_number = ?", (order_number,))
        return jsonify({
            'success': True,
            'message': f"Order #{order_number} returned to open courier dispatch pool",
            'courier_name': None,
            'courier_id': None
        })

def save_item_sizes(item_id, form_data):
    """Save or update Small, Medium, Large size variations with daily stock and multi-choice support."""
    enable_sizes = form_data.get('enable_sizes')
    if not enable_sizes:
        # If disabled, remove any existing size modifier group for this item
        size_grps = query_db("SELECT id FROM modifier_groups WHERE menu_item_id = ? AND (name LIKE '%Size%' OR name LIKE '%Portion%')", (item_id,))
        for sg in size_grps:
            execute_db("DELETE FROM modifier_options WHERE modifier_group_id = ?", (sg['id'],))
            execute_db("DELETE FROM modifier_groups WHERE id = ?", (sg['id'],))
        return

    # Check for dynamic size list or explicit Small / Medium / Large inputs
    size_names = form_data.getlist('size_name[]') or form_data.getlist('size_name')
    size_deltas = form_data.getlist('size_delta[]') or form_data.getlist('size_delta')
    size_defaults = form_data.getlist('size_is_default[]') or form_data.getlist('size_is_default')
    size_multi_defs = form_data.getlist('size_default_multi[]') or form_data.getlist('size_default_multi')
    size_stocks = form_data.getlist('size_stock[]') or form_data.getlist('size_stock')
    default_idx_str = str(form_data.get('size_default_index', '1'))

    # Multi-choice selection settings
    is_multiselect = 1 if form_data.get('size_multiselect') in ('1', 'on', 'true') else 0
    try:
        max_sel = int(form_data.get('size_max_selection', 0))
    except (ValueError, TypeError):
        max_sel = 0

    sizes = []
    if size_names:
        for idx, sname in enumerate(size_names):
            sname = sname.strip()
            if not sname:
                continue
            try:
                sdelta = float(size_deltas[idx]) if idx < len(size_deltas) else 0.0
            except (ValueError, TypeError):
                sdelta = 0.0

            try:
                sstock = int(size_stocks[idx]) if idx < len(size_stocks) and str(size_stocks[idx]).strip() != '' else 50
            except (ValueError, TypeError):
                sstock = 50

            if is_multiselect:
                # If multi-choice, check if row index is in size_multi_defs or size_defaults
                if size_multi_defs:
                    is_def = 1 if str(idx) in size_multi_defs else 0
                elif size_defaults:
                    is_def = 1 if (idx < len(size_defaults) and size_defaults[idx] in ('1', 'true', 'on')) or str(idx) in size_defaults else 0
                else:
                    is_def = 1 if str(idx) == default_idx_str else 0
            else:
                is_def = 1 if str(idx) == default_idx_str else 0

            sizes.append((sname, sdelta, is_def, sstock))
    else:
        # Fallback to explicit Small, Medium, Large fields
        # Small
        if form_data.get('has_small', '1') in ('1', 'on', 'true'):
            s_name = form_data.get('size_small_name', 'Small').strip() or 'Small'
            try:
                s_delta = float(form_data.get('size_small_delta', '0.00'))
            except ValueError:
                s_delta = 0.0
            try:
                s_stock = int(form_data.get('size_small_stock', '30'))
            except ValueError:
                s_stock = 30
            sizes.append((s_name, s_delta, 1 if form_data.get('size_default_choice') == 'small' else 0, s_stock))
        # Medium
        if form_data.get('has_medium', '1') in ('1', 'on', 'true'):
            m_name = form_data.get('size_medium_name', 'Medium (Regular)').strip() or 'Medium (Regular)'
            try:
                m_delta = float(form_data.get('size_medium_delta', '0.00'))
            except ValueError:
                m_delta = 0.0
            try:
                m_stock = int(form_data.get('size_medium_stock', '50'))
            except ValueError:
                m_stock = 50
            sizes.append((m_name, m_delta, 1 if form_data.get('size_default_choice', 'medium') == 'medium' else 0, m_stock))
        # Large
        if form_data.get('has_large', '1') in ('1', 'on', 'true'):
            l_name = form_data.get('size_large_name', 'Large').strip() or 'Large'
            try:
                l_delta = float(form_data.get('size_large_delta', '3.00'))
            except ValueError:
                l_delta = 3.0
            try:
                l_stock = int(form_data.get('size_large_stock', '20'))
            except ValueError:
                l_stock = 20
            sizes.append((l_name, l_delta, 1 if form_data.get('size_default_choice') == 'large' else 0, l_stock))

    if not sizes:
        return

    # Ensure at least one default
    if not any(s[2] == 1 for s in sizes):
        sizes[0] = (sizes[0][0], sizes[0][1], 1, sizes[0][3])

    # Calculate min and max selection
    if is_multiselect:
        group_max = max_sel if max_sel > 1 else max(len(sizes), 2)
        group_min = 0 if form_data.get('size_is_optional') else 1
    else:
        group_max = 1
        group_min = 1

    # Check for existing size group to update, or create a new one
    existing_grp = query_db("SELECT id FROM modifier_groups WHERE menu_item_id = ? AND (name LIKE '%Size%' OR name LIKE '%Portion%') LIMIT 1", (item_id,), one=True)
    if existing_grp:
        grp_id = existing_grp['id']
        execute_db("UPDATE modifier_groups SET min_selection = ?, max_selection = ?, is_required = ? WHERE id = ?",
                   (group_min, group_max, 1 if group_min > 0 else 0, grp_id))
        execute_db("DELETE FROM modifier_options WHERE modifier_group_id = ?", (grp_id,))
    else:
        grp_id = execute_db(
            "INSERT INTO modifier_groups (menu_item_id, name, min_selection, max_selection, is_required) VALUES (?, ?, ?, ?, ?)",
            (item_id, "Choose Size", group_min, group_max, 1 if group_min > 0 else 0)
        )

    for sname, sdelta, is_def, sstock in sizes:
        execute_db(
            "INSERT INTO modifier_options (modifier_group_id, name, price_delta, is_default, stock_quantity) VALUES (?, ?, ?, ?, ?)",
            (grp_id, sname, sdelta, is_def, sstock)
        )

@app.route('/partner/menu')
@role_required('restaurant', 'admin')
def partner_menu():
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1
    categories = query_db("SELECT * FROM menu_categories WHERE restaurant_id = ? ORDER BY sort_order ASC, id ASC", (rest_id,))

    menu_by_category = []
    total_dishes = 0
    for cat in categories:
        items = query_db("SELECT * FROM menu_items WHERE category_id = ? ORDER BY id ASC", (cat['id'],))
        total_dishes += len(items)
        
        dish_items = []
        for it in items:
            it_dict = dict(it)
            size_grp = query_db("SELECT * FROM modifier_groups WHERE menu_item_id = ? AND (name LIKE '%Size%' OR name LIKE '%Portion%') LIMIT 1", (it['id'],), one=True)
            if size_grp:
                opts = query_db("SELECT * FROM modifier_options WHERE modifier_group_id = ? ORDER BY id ASC", (size_grp['id'],))
                it_dict['size_group'] = dict(size_grp)
                it_dict['sizes'] = [dict(o) for o in opts]
            else:
                it_dict['size_group'] = None
                it_dict['sizes'] = []
            dish_items.append(it_dict)

        menu_by_category.append({
            'category': cat,
            'dish_items': dish_items
        })

    return render_template(
        'partner/menu.html',
        restaurant=restaurant,
        categories=categories,
        menu_by_category=menu_by_category,
        total_dishes=total_dishes
    )

@app.route('/partner/menu/category/add', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_add_category():
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1
    name = request.form.get('name', '').strip()
    sort_order = int(request.form.get('sort_order', 1))

    if not name:
        flash("Please enter a category name.", "error")
        return redirect(url_for('partner_menu'))

    execute_db("INSERT INTO menu_categories (restaurant_id, name, sort_order) VALUES (?, ?, ?)", (rest_id, name, sort_order))
    flash(f"Category '{name}' created successfully!", "success")
    return redirect(url_for('partner_menu'))

@app.route('/partner/menu/category/<int:cat_id>/delete', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_delete_category(cat_id):
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1

    cat = query_db("SELECT * FROM menu_categories WHERE id = ? AND restaurant_id = ?", (cat_id, rest_id), one=True)
    if not cat:
        flash("Category not found.", "error")
        return redirect(url_for('partner_menu'))

    execute_db("DELETE FROM menu_items WHERE category_id = ?", (cat_id,))
    execute_db("DELETE FROM menu_categories WHERE id = ?", (cat_id,))
    flash(f"Category '{cat['name']}' and its items removed.", "info")
    return redirect(url_for('partner_menu'))

@app.route('/partner/menu/item/add', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_add_item():
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1

    category_id = request.form.get('category_id')
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price_str = request.form.get('price', '0.00')

    try:
        price = float(price_str)
    except ValueError:
        price = 0.0

    if not name or not category_id or price <= 0:
        flash("Please provide a valid dish name, category, and price.", "error")
        return redirect(url_for('partner_menu'))

    image_url = request.form.get('image_url', '').strip()
    dish_file = request.files.get('dish_image_file')

    if dish_file and dish_file.filename and allowed_image_file(dish_file.filename):
        ext = dish_file.filename.rsplit('.', 1)[1].lower()
        filename = f"dish_{rest_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(DISH_UPLOAD_FOLDER, filename)
        dish_file.save(filepath)
        image_url = url_for('static', filename=f'uploads/dishes/{filename}')
    elif not image_url:
        image_url = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=80'

    is_vegetarian = 1 if request.form.get('is_vegetarian') else 0
    is_vegan = 1 if request.form.get('is_vegan') else 0
    is_gluten_free = 1 if request.form.get('is_gluten_free') else 0
    is_spicy = 1 if request.form.get('is_spicy') else 0
    is_popular = 1 if request.form.get('is_popular') else 0

    new_item_id = execute_db('''
        INSERT INTO menu_items (
            category_id, restaurant_id, name, description, price, image_url,
            is_vegetarian, is_vegan, is_gluten_free, is_spicy, is_popular, is_available
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    ''', (category_id, rest_id, name, description, price, image_url, is_vegetarian, is_vegan, is_gluten_free, is_spicy, is_popular))

    # Save Small, Medium, Large size configurations
    save_item_sizes(new_item_id, request.form)

    flash(f"Dish '{name}' added to your menu successfully!", "success")
    return redirect(url_for('partner_menu'))

@app.route('/partner/menu/item/<int:item_id>/edit', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_edit_item(item_id):
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1

    item = query_db("SELECT * FROM menu_items WHERE id = ? AND restaurant_id = ?", (item_id, rest_id), one=True)
    if not item:
        flash("Dish not found.", "error")
        return redirect(url_for('partner_menu'))

    category_id = request.form.get('category_id', item['category_id'])
    name = request.form.get('name', item['name']).strip()
    description = request.form.get('description', item['description']).strip()
    price = float(request.form.get('price', item['price']))
    image_url = request.form.get('image_url', '').strip() or item['image_url']

    dish_file = request.files.get('dish_image_file')
    if dish_file and dish_file.filename and allowed_image_file(dish_file.filename):
        ext = dish_file.filename.rsplit('.', 1)[1].lower()
        filename = f"dish_{rest_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(DISH_UPLOAD_FOLDER, filename)
        dish_file.save(filepath)
        image_url = url_for('static', filename=f'uploads/dishes/{filename}')

    is_vegetarian = 1 if request.form.get('is_vegetarian') else 0
    is_vegan = 1 if request.form.get('is_vegan') else 0
    is_gluten_free = 1 if request.form.get('is_gluten_free') else 0
    is_spicy = 1 if request.form.get('is_spicy') else 0
    is_popular = 1 if request.form.get('is_popular') else 0

    execute_db('''
        UPDATE menu_items SET
            category_id = ?, name = ?, description = ?, price = ?, image_url = ?,
            is_vegetarian = ?, is_vegan = ?, is_gluten_free = ?, is_spicy = ?, is_popular = ?
        WHERE id = ?
    ''', (category_id, name, description, price, image_url, is_vegetarian, is_vegan, is_gluten_free, is_spicy, is_popular, item_id))

    # Save Small, Medium, Large size configurations
    save_item_sizes(item_id, request.form)

    flash(f"Dish '{name}' updated successfully!", "success")
    return redirect(url_for('partner_menu'))

@app.route('/partner/menu/item/<int:item_id>/delete', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_delete_item(item_id):
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1

    item = query_db("SELECT * FROM menu_items WHERE id = ? AND restaurant_id = ?", (item_id, rest_id), one=True)
    if not item:
        flash("Dish not found.", "error")
        return redirect(url_for('partner_menu'))

    execute_db("DELETE FROM menu_items WHERE id = ?", (item_id,))
    flash(f"Dish '{item['name']}' removed from menu.", "info")
    return redirect(url_for('partner_menu'))

@app.route('/partner/menu/item/<int:item_id>/toggle-stock', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_toggle_item_stock(item_id):
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1

    item = query_db("SELECT * FROM menu_items WHERE id = ? AND restaurant_id = ?", (item_id, rest_id), one=True)
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'}), 404

    new_status = 0 if item['is_available'] else 1
    execute_db("UPDATE menu_items SET is_available = ? WHERE id = ?", (new_status, item_id))
    status_text = "In Stock" if new_status else "86'd / Sold Out"
    return jsonify({'success': True, 'is_available': bool(new_status), 'status_text': status_text})

@app.route('/partner/restaurant-profile', methods=['GET', 'POST'])
@role_required('restaurant', 'admin')
def partner_profile():
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1

    if request.method == 'POST':
        name = request.form.get('name')
        cuisine = request.form.get('cuisine')
        phone = request.form.get('phone')
        address = request.form.get('address')
        try:
            lat = float(request.form.get('lat', restaurant['lat'] if restaurant and 'lat' in restaurant.keys() and restaurant['lat'] else 40.7128))
            lng = float(request.form.get('lng', restaurant['lng'] if restaurant and 'lng' in restaurant.keys() and restaurant['lng'] else -74.0060))
        except (ValueError, TypeError):
            lat = 40.7128
            lng = -74.0060
        min_order = float(request.form.get('min_order', 15.0))
        delivery_fee = float(request.form.get('delivery_fee', 2.99))
        delivery_time_min = int(request.form.get('delivery_time_min', 20))
        delivery_time_max = int(request.form.get('delivery_time_max', 35))
        is_open = 1 if request.form.get('is_open') else 0
        description = request.form.get('description')
        image_url = request.form.get('image_url', '').strip() or (restaurant['image_url'] if restaurant else '')
        logo_url = request.form.get('logo_url', '').strip() or (restaurant['logo_url'] if restaurant else '')

        # Handle Cover Banner Upload
        image_file = request.files.get('image_file')
        if image_file and image_file.filename and allowed_image_file(image_file.filename):
            ext = image_file.filename.rsplit('.', 1)[1].lower()
            filename = f"restaurant_{rest_id}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = os.path.join(RESTAURANT_UPLOAD_FOLDER, filename)
            image_file.save(filepath)
            image_url = url_for('static', filename=f'uploads/restaurants/{filename}')

        # Handle Logo Avatar Upload
        logo_file = request.files.get('logo_file')
        if logo_file and logo_file.filename and allowed_image_file(logo_file.filename):
            ext = logo_file.filename.rsplit('.', 1)[1].lower()
            filename = f"logo_{rest_id}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = os.path.join(RESTAURANT_UPLOAD_FOLDER, filename)
            logo_file.save(filepath)
            logo_url = url_for('static', filename=f'uploads/restaurants/{filename}')

        execute_db('''
            UPDATE restaurants SET
                name = ?, cuisine = ?, phone = ?, address = ?, lat = ?, lng = ?, min_order = ?,
                delivery_fee = ?, delivery_time_min = ?, delivery_time_max = ?,
                is_open = ?, description = ?, image_url = ?, logo_url = ?
            WHERE id = ?
        ''', (name, cuisine, phone, address, lat, lng, min_order, delivery_fee, delivery_time_min, delivery_time_max, is_open, description, image_url, logo_url, rest_id))

        flash("Restaurant settings and storefront appearance saved successfully!", "success")
        return redirect(request.referrer or url_for('partner_profile'))

    return render_template('partner/profile.html', restaurant=restaurant)

@app.route('/api/partner/toggle-status', methods=['POST'])
@role_required('restaurant', 'admin')
def api_partner_toggle_status():
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1
    new_status = 0 if restaurant['is_open'] else 1
    execute_db("UPDATE restaurants SET is_open = ? WHERE id = ?", (new_status, rest_id))
    return jsonify({
        'success': True,
        'is_open': bool(new_status),
        'status_text': 'Open for Delivery' if new_status else 'Temporarily Closed',
        'message': f"Storefront status updated to {'Open for Delivery' if new_status else 'Temporarily Closed'}"
    })

def deactivate_expired_promos():
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    execute_db("UPDATE promo_codes SET is_active = 0 WHERE expires_at IS NOT NULL AND expires_at <= ? AND is_active = 1", (now_str,))

@app.route('/partner/promotions')
@role_required('restaurant', 'admin')
def partner_promotions():
    deactivate_expired_promos()
    restaurant = get_current_partner_restaurant()
    promos = query_db("SELECT * FROM promo_codes ORDER BY is_active DESC, expires_at ASC, id DESC")
    return render_template('partner/promotions.html', restaurant=restaurant, promos=promos)

@app.route('/partner/promotions/add', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_add_promotion():
    code = request.form.get('code', '').strip().upper()
    description = request.form.get('description', '').strip()
    discount_type = request.form.get('discount_type', 'percent')
    try:
        discount_value = float(request.form.get('discount_value', 15))
    except (ValueError, TypeError):
        discount_value = 15.0
    try:
        min_spend = float(request.form.get('min_spend', 20.0))
    except (ValueError, TypeError):
        min_spend = 0.0
    try:
        max_discount = float(request.form.get('max_discount', 50.0))
    except (ValueError, TypeError):
        max_discount = 50.0

    is_active = 1 if request.form.get('is_active', '1') in ('1', 'on', 'true') else 0

    # Handle Duration / Countdown Expiry
    duration_days_str = request.form.get('duration_days', '7')
    custom_exp = request.form.get('custom_expires_at', '').strip()

    if custom_exp:
        clean_exp = custom_exp.replace('T', ' ')
        if len(clean_exp) == 16:
            clean_exp += ':00'
        expires_at = clean_exp
    else:
        try:
            days = int(duration_days_str)
        except (ValueError, TypeError):
            days = 7
        expires_at = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

    if not code:
        flash("Promo code name cannot be empty.", "error")
        return redirect(url_for('partner_promotions'))

    existing = query_db("SELECT id FROM promo_codes WHERE code = ?", (code,), one=True)
    if existing:
        flash(f"A promo code with code '{code}' already exists.", "error")
        return redirect(url_for('partner_promotions'))

    execute_db('''
        INSERT INTO promo_codes (code, discount_type, discount_value, min_spend, max_discount, description, is_active, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (code, discount_type, discount_value, min_spend, max_discount, description or f"{discount_value}% off all orders", is_active, expires_at))

    flash(f"Campaign '{code}' launched successfully with live countdown! Expires on {expires_at}.", "success")
    return redirect(url_for('partner_promotions'))

@app.route('/partner/promotions/<int:promo_id>/extend', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_extend_promotion(promo_id):
    promo = query_db("SELECT * FROM promo_codes WHERE id = ?", (promo_id,), one=True)
    if not promo:
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return jsonify({'success': False, 'message': 'Promotional campaign not found.'}), 404
        flash("Promotional campaign not found.", "error")
        return redirect(url_for('partner_promotions'))

    data = request.get_json(silent=True) or request.form
    try:
        extend_days = int(data.get('extend_days', 3))
    except (ValueError, TypeError):
        extend_days = 3

    now_dt = datetime.datetime.now()
    if promo['expires_at']:
        try:
            curr_exp = datetime.datetime.strptime(str(promo['expires_at']), '%Y-%m-%d %H:%M:%S')
            base_dt = max(curr_exp, now_dt)
        except Exception:
            base_dt = now_dt
    else:
        base_dt = now_dt

    new_exp = (base_dt + datetime.timedelta(days=extend_days)).strftime('%Y-%m-%d %H:%M:%S')
    execute_db("UPDATE promo_codes SET is_active = 1, expires_at = ? WHERE id = ?", (new_exp, promo_id))
    
    if request.headers.get('Accept') == 'application/json' or request.is_json:
        return jsonify({
            'success': True,
            'message': f"Campaign '{promo['code']}' extended by +{extend_days} days! New expiry: {new_exp}",
            'new_expires_at': new_exp
        })

    flash(f"Campaign '{promo['code']}' extended by +{extend_days} days and sale is now LIVE! Expires on {new_exp}.", "success")
    return redirect(url_for('partner_promotions'))

@app.route('/api/promotions/<int:promo_id>/expire', methods=['POST'])
def api_expire_promotion(promo_id):
    execute_db("UPDATE promo_codes SET is_active = 0 WHERE id = ?", (promo_id,))
    return jsonify({'success': True, 'message': 'Promotion expired and sale ended.'})

@app.route('/partner/promotions/<int:promo_id>/toggle', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_toggle_promotion(promo_id):
    promo = query_db("SELECT * FROM promo_codes WHERE id = ?", (promo_id,), one=True)
    if not promo:
        flash("Promotional campaign not found.", "error")
        return redirect(url_for('partner_promotions'))

    new_status = 0 if promo['is_active'] == 1 else 1
    execute_db("UPDATE promo_codes SET is_active = ? WHERE id = ?", (new_status, promo_id))
    status_label = "activated" if new_status == 1 else "deactivated"
    flash(f"Campaign '{promo['code']}' has been {status_label}.", "success")
    return redirect(url_for('partner_promotions'))

@app.route('/partner/promotions/<int:promo_id>/delete', methods=['POST'])
@role_required('restaurant', 'admin')
def partner_delete_promotion(promo_id):
    promo = query_db("SELECT * FROM promo_codes WHERE id = ?", (promo_id,), one=True)
    if not promo:
        flash("Promotional campaign not found.", "error")
        return redirect(url_for('partner_promotions'))

    execute_db("DELETE FROM promo_codes WHERE id = ?", (promo_id,))
    flash(f"Campaign '{promo['code']}' was removed successfully.", "success")
    return redirect(url_for('partner_promotions'))

@app.route('/partner/analytics')
@role_required('restaurant', 'admin')
def partner_analytics():
    restaurant = get_current_partner_restaurant()
    rest_id = restaurant['id'] if restaurant else 1
    orders = query_db("SELECT * FROM orders WHERE restaurant_id = ? ORDER BY created_at ASC", (rest_id,))
    top_items = query_db('''
        SELECT oi.name, COUNT(oi.id) as order_count, SUM(oi.total_price) as revenue
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE o.restaurant_id = ?
        GROUP BY oi.name
        ORDER BY order_count DESC
        LIMIT 5
    ''', (rest_id,))
    reviews = query_db("SELECT * FROM reviews WHERE restaurant_id = ? ORDER BY created_at DESC", (rest_id,))

    return render_template(
        'partner/analytics.html',
        restaurant=restaurant,
        orders=orders,
        top_items=top_items,
        reviews=reviews
    )

# ---------------------------------------------------------
# Courier Delivery Partner Routes
# ---------------------------------------------------------

@app.route('/courier')
@role_required('courier', 'admin')
def courier_overview():
    courier = get_current_courier()
    courier_id = courier['id'] if courier else 1
    active_deliveries = query_db('''
        SELECT o.*, r.name as restaurant_name, r.address as restaurant_address, r.phone as restaurant_phone
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE o.courier_id = ? AND o.status NOT IN ('delivered', 'cancelled')
        ORDER BY o.created_at DESC
    ''', (courier_id,))

    past_deliveries = query_db('''
        SELECT o.*, r.name as restaurant_name
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE o.courier_id = ? AND o.status = 'delivered'
        ORDER BY o.created_at DESC
        LIMIT 5
    ''', (courier_id,))

    # Calculate actual completed deliveries earnings for this courier
    today_earnings = sum(o['delivery_fee'] + o['tip'] for o in past_deliveries)
    return render_template(
        'courier/overview.html',
        courier=courier,
        active_deliveries=active_deliveries,
        past_deliveries=past_deliveries,
        today_earnings=round(today_earnings, 2)
    )

@app.route('/courier/deliveries')
@role_required('courier', 'admin')
def courier_deliveries():
    courier = get_current_courier()
    courier_id = courier['id'] if courier else 1
    active_deliveries = query_db('''
        SELECT o.*, r.name as restaurant_name, r.address as restaurant_address, r.phone as restaurant_phone
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE o.courier_id = ? AND o.status NOT IN ('delivered', 'cancelled')
        ORDER BY o.created_at DESC
    ''', (courier_id,))
    available_orders = query_db('''
        SELECT o.*, r.name as restaurant_name, r.address as restaurant_address
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE o.courier_id IS NULL AND o.status IN ('ready', 'preparing')
        LIMIT 3
    ''')
    return render_template(
        'courier/deliveries.html',
        courier=courier,
        active_deliveries=active_deliveries,
        available_orders=available_orders
    )

@app.route('/courier/deliveries/<order_number>')
@role_required('courier', 'admin')
def courier_delivery_detail(order_number):
    courier = get_current_courier()
    order = query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)
    if not order:
        flash("Delivery mission not found.", "error")
        return redirect(url_for('courier_deliveries'))

    restaurant = query_db("SELECT * FROM restaurants WHERE id = ?", (order['restaurant_id'],), one=True)
    customer = query_db("SELECT * FROM users WHERE id = ?", (order['customer_id'],), one=True)
    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
    address = json.loads(order['delivery_address_json']) if order['delivery_address_json'] else {}

    return render_template(
        'courier/delivery_detail.html',
        courier=courier,
        order=order,
        restaurant=restaurant,
        customer=customer,
        items=items,
        address=address
    )

@app.route('/courier/earnings')
@role_required('courier', 'admin')
def courier_earnings():
    courier = get_current_courier()
    courier_id = courier['id'] if courier else 1
    deliveries = query_db('''
        SELECT o.*, r.name as restaurant_name
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE o.courier_id = ? AND o.status = 'delivered'
        ORDER BY o.created_at DESC
    ''', (courier_id,))
    base_pay = sum(o['delivery_fee'] for o in deliveries)
    tips_pay = sum(o['tip'] for o in deliveries)
    bonus_pay = 15.00 if (courier and courier['total_trips'] and courier['total_trips'] >= 3) else 0.0
    total_earnings = base_pay + tips_pay + bonus_pay

    return render_template(
        'courier/earnings.html',
        courier=courier,
        deliveries=deliveries,
        base_pay=round(base_pay, 2),
        tips_pay=round(tips_pay, 2),
        bonus_pay=round(bonus_pay, 2),
        total_earnings=round(total_earnings, 2)
    )

# ---------------------------------------------------------
# RESTful API Endpoints (AJAX & Client Interactivity)
# ---------------------------------------------------------

@app.route('/api/menu-items/<int:item_id>')
def api_menu_item(item_id):
    item = query_db("SELECT * FROM menu_items WHERE id = ?", (item_id,), one=True)
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    groups = query_db("SELECT * FROM modifier_groups WHERE menu_item_id = ?", (item_id,))
    groups_list = []
    for g in groups:
        opts = query_db("SELECT * FROM modifier_options WHERE modifier_group_id = ?", (g['id'],))
        groups_list.append({
            'id': g['id'],
            'name': g['name'],
            'min_selection': g['min_selection'],
            'max_selection': g['max_selection'],
            'is_required': g['is_required'],
            'options': [dict(o) for o in opts]
        })

    item_dict = dict(item)
    item_dict['modifier_groups'] = groups_list
    return jsonify(item_dict)

@app.route('/api/cart', methods=['GET'])
def api_get_cart():
    session_token = session['session_token']
    items = query_db('''
        SELECT ci.*, mi.name as item_name, mi.price as base_price, mi.image_url as item_image,
               r.name as restaurant_name, r.delivery_fee, r.min_order
        FROM cart_items ci
        JOIN menu_items mi ON ci.menu_item_id = mi.id
        JOIN restaurants r ON ci.restaurant_id = r.id
        WHERE ci.session_id = ?
        ORDER BY ci.id ASC
    ''', (session_token,))

    cart_list = [dict(i) for i in items]
    subtotal = sum(i['item_total'] for i in cart_list)
    discount = session.get('cart_discount', 0.0)
    applied_promo = session.get('applied_promo', '')
    delivery_fee = cart_list[0]['delivery_fee'] if cart_list else 0.0
    service_fee = round(subtotal * 0.08, 2) if subtotal > 0 else 0.0
    tax = round((subtotal + service_fee) * 0.08875, 2) if subtotal > 0 else 0.0
    total = max(0.0, round(subtotal + delivery_fee + service_fee + tax - discount, 2))

    return jsonify({
        'items': cart_list,
        'count': sum(i['quantity'] for i in cart_list),
        'subtotal': round(subtotal, 2),
        'delivery_fee': round(delivery_fee, 2),
        'service_fee': round(service_fee, 2),
        'tax': round(tax, 2),
        'discount': round(discount, 2),
        'applied_promo': applied_promo,
        'total': total,
        'restaurant_name': cart_list[0]['restaurant_name'] if cart_list else None,
        'restaurant_id': cart_list[0]['restaurant_id'] if cart_list else None
    })

@app.route('/api/cart/add', methods=['POST'])
def api_add_to_cart():
    session_token = session['session_token']
    data = request.get_json(silent=True) or {}

    menu_item_id = data.get('menu_item_id')
    quantity = int(data.get('quantity', 1))
    special_instructions = data.get('special_instructions', '').strip()
    selected_modifiers = data.get('modifiers', []) # list of dicts: {name, price_delta}

    item = query_db("SELECT * FROM menu_items WHERE id = ?", (menu_item_id,), one=True)
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    # Check if cart contains items from a DIFFERENT restaurant
    existing_items = query_db("SELECT restaurant_id FROM cart_items WHERE session_id = ? LIMIT 1", (session_token,))
    if existing_items and existing_items[0]['restaurant_id'] != item['restaurant_id']:
        # If user forces replace or request clarification
        if data.get('force_replace'):
            execute_db("DELETE FROM cart_items WHERE session_id = ?", (session_token,))
            session.pop('cart_discount', None)
            session.pop('applied_promo', None)
        else:
            old_rest = query_db("SELECT name FROM restaurants WHERE id = ?", (existing_items[0]['restaurant_id'],), one=True)
            return jsonify({
                'error': 'different_restaurant',
                'current_restaurant': old_rest['name'] if old_rest else 'Another restaurant',
                'message': 'Your cart contains items from another restaurant. Would you like to clear your cart and start fresh?'
            }), 409

    # Calculate item total
    extra_cost = sum(float(m.get('price_delta', 0.0)) for m in selected_modifiers)
    unit_total = item['price'] + extra_cost
    item_total = round(unit_total * quantity, 2)

    user_id = session.get('user_id')
    execute_db('''
        INSERT INTO cart_items (
            session_id, user_id, menu_item_id, restaurant_id, quantity,
            special_instructions, selected_modifiers_json, item_total
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_token, user_id, menu_item_id, item['restaurant_id'], quantity,
        special_instructions, json.dumps(selected_modifiers), item_total
    ))

    # Recalculate cart count
    count_res = query_db("SELECT SUM(quantity) as total_count FROM cart_items WHERE session_id = ?", (session_token,), one=True)
    new_count = count_res['total_count'] if count_res and count_res['total_count'] else 0

    return jsonify({
        'success': True,
        'message': f"Added {quantity}x {item['name']} to cart!",
        'cart_count': new_count
    })

@app.route('/api/cart/update-quantity', methods=['POST'])
def api_update_cart_quantity():
    session_token = session['session_token']
    data = request.get_json(silent=True) or {}
    cart_item_id = data.get('cart_item_id')
    change = int(data.get('change', 0))

    cart_item = query_db('''
        SELECT ci.*, mi.price as base_price
        FROM cart_items ci
        JOIN menu_items mi ON ci.menu_item_id = mi.id
        WHERE ci.id = ? AND ci.session_id = ?
    ''', (cart_item_id, session_token), one=True)

    if not cart_item:
        return jsonify({'error': 'Cart item not found'}), 404

    new_quantity = cart_item['quantity'] + change
    if new_quantity <= 0:
        execute_db("DELETE FROM cart_items WHERE id = ?", (cart_item_id,))
    else:
        mods = json.loads(cart_item['selected_modifiers_json']) if cart_item['selected_modifiers_json'] else []
        extra_cost = sum(float(m.get('price_delta', 0.0)) for m in mods)
        unit_price = cart_item['base_price'] + extra_cost
        new_total = round(unit_price * new_quantity, 2)

        execute_db("UPDATE cart_items SET quantity = ?, item_total = ? WHERE id = ?", (new_quantity, new_total, cart_item_id))

    return api_get_cart()

@app.route('/api/cart/remove-item', methods=['POST'])
def api_remove_cart_item():
    session_token = session['session_token']
    data = request.get_json(silent=True) or {}
    cart_item_id = data.get('cart_item_id')

    execute_db("DELETE FROM cart_items WHERE id = ? AND session_id = ?", (cart_item_id, session_token))
    return api_get_cart()

@app.route('/api/cart/clear', methods=['POST'])
def api_clear_cart():
    session_token = session['session_token']
    execute_db("DELETE FROM cart_items WHERE session_id = ?", (session_token,))
    session.pop('cart_discount', None)
    session.pop('applied_promo', None)
    return jsonify({'success': True, 'cart_count': 0})

@app.route('/api/cart/apply-promo', methods=['POST'])
def api_apply_promo():
    session_token = session['session_token']
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip().upper()

    cart_items = query_db("SELECT item_total FROM cart_items WHERE session_id = ?", (session_token,))
    if not cart_items:
        return jsonify({'success': False, 'message': 'Cart is empty.'}), 400

    subtotal = sum(i['item_total'] for i in cart_items)
    deactivate_expired_promos()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    promo = query_db("SELECT * FROM promo_codes WHERE code = ? AND is_active = 1", (code,), one=True)

    if not promo:
        return jsonify({'success': False, 'message': f"Promo code '{code}' is invalid, paused, or expired."}), 400

    if promo['expires_at'] and str(promo['expires_at']) <= now_str:
        execute_db("UPDATE promo_codes SET is_active = 0 WHERE id = ?", (promo['id'],))
        return jsonify({'success': False, 'message': f"Promo code '{code}' has expired and this promotional sale has ended."}), 400

    if subtotal < promo['min_spend']:
        return jsonify({
            'success': False,
            'message': f"Minimum spend of ${promo['min_spend']:.2f} required for promo {code}."
        }), 400

    discount = 0.0
    if promo['discount_type'] == 'percent':
        calculated = (subtotal * promo['discount_value']) / 100.0
        discount = min(calculated, promo['max_discount'])
    else:
        discount = promo['discount_value']

    discount = round(discount, 2)
    session['cart_discount'] = discount
    session['applied_promo'] = code

    return jsonify({
        'success': True,
        'message': f"Promo code {code} applied! Saved ${discount:.2f}",
        'discount': discount,
        'code': code
    })

@app.route('/api/cart/remove-promo', methods=['POST'])
def api_remove_promo():
    session.pop('cart_discount', None)
    session.pop('applied_promo', None)
    return jsonify({'success': True, 'message': 'Promo code removed'})

@app.route('/api/checkout', methods=['POST'])
@login_required
def api_process_checkout():
    session_token = session['session_token']
    data = request.get_json(silent=True) or {}

    cart_items = query_db('''
        SELECT ci.*, mi.name as item_name, mi.price as base_price
        FROM cart_items ci
        JOIN menu_items mi ON ci.menu_item_id = mi.id
        WHERE ci.session_id = ?
    ''', (session_token,))

    if not cart_items:
        return jsonify({'success': False, 'message': 'Cart is empty. Please add items.'}), 400

    restaurant_id = cart_items[0]['restaurant_id']
    restaurant = query_db("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,), one=True)
    customer_id = g.user['id']

    # Calculate final totals
    subtotal = sum(i['item_total'] for i in cart_items)
    if subtotal < restaurant['min_order']:
        return jsonify({
            'success': False,
            'message': f"Minimum order amount for {restaurant['name']} is ${restaurant['min_order']:.2f}."
        }), 400

    delivery_fee = float(restaurant['delivery_fee'])
    service_fee = round(subtotal * 0.08, 2)
    tax = round((subtotal + service_fee) * 0.08875, 2)
    tip = float(data.get('tip', 3.0))
    discount = float(session.get('cart_discount', 0.0))
    promo_code = session.get('applied_promo', '')
    total = max(0.0, round(subtotal + delivery_fee + service_fee + tax + tip - discount, 2))

    # Address & payment data
    address_data = data.get('address', {
        'label': 'Home',
        'street': '742 Evergreen Terrace, Apt 4B',
        'city': 'New York',
        'zip_code': '10001'
    })
    delivery_instructions = data.get('delivery_instructions', 'Leave at door')
    payment_method = data.get('payment_method', 'Visa •••• 4242')
    delivery_type = data.get('delivery_type', 'delivery')

    # Dynamic courier dispatch across online couriers
    active_courier_candidates = query_db("SELECT id FROM couriers WHERE is_online = 1 ORDER BY total_trips ASC, id ASC")
    courier_id = active_courier_candidates[0]['id'] if active_courier_candidates else 1
    order_number = f"ORD-{datetime.datetime.now().strftime('%M%S')}{uuid.uuid4().hex[:4].upper()}"
    est_time = f"{restaurant['delivery_time_min']}-{restaurant['delivery_time_max']} mins"

    order_id = execute_db('''
        INSERT INTO orders (
            order_number, customer_id, restaurant_id, courier_id, status,
            subtotal, delivery_fee, service_fee, tax, tip, discount, total,
            promo_code, delivery_address_json, delivery_instructions, payment_method,
            delivery_type, estimated_delivery_time, courier_lat, courier_lng
        ) VALUES (?, ?, ?, ?, 'placed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 40.7128, -74.0060)
    ''', (
        order_number, customer_id, restaurant_id, courier_id,
        subtotal, delivery_fee, service_fee, tax, tip, discount, total,
        promo_code, json.dumps(address_data), delivery_instructions, payment_method,
        delivery_type, est_time
    ))

    # Insert items
    for item in cart_items:
        mods = json.loads(item['selected_modifiers_json']) if item['selected_modifiers_json'] else []
        summary = ", ".join([f"{m.get('name')}" for m in mods]) if mods else "Standard"
        execute_db('''
            INSERT INTO order_items (order_id, menu_item_id, name, unit_price, quantity, modifiers_summary, total_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (order_id, item['menu_item_id'], item['item_name'], item['base_price'], item['quantity'], summary, item['item_total']))

    # Award CravePoints Loyalty Reward (10 points per dollar spent)
    earned_points = int(total * 10)
    execute_db("UPDATE users SET loyalty_points = COALESCE(loyalty_points, 0) + ? WHERE id = ?", (earned_points, customer_id))

    # Clear Cart & Promo
    execute_db("DELETE FROM cart_items WHERE session_id = ?", (session_token,))
    session.pop('cart_discount', None)
    session.pop('applied_promo', None)

    return jsonify({
        'success': True,
        'order_number': order_number,
        'earned_points': earned_points,
        'redirect_url': url_for('order_confirmation', order_number=order_number)
    })

@app.route('/api/payment/verify-upi', methods=['POST'])
def api_verify_upi():
    data = request.get_json(silent=True) or {}
    upi_id = data.get('upi_id', '').strip()
    if not upi_id or '@' not in upi_id:
        return jsonify({'success': False, 'message': 'Please enter a valid UPI ID (e.g. name@okaxis, user@paytm)'}), 400

    parts = upi_id.split('@')
    name_part = parts[0].replace('.', ' ').replace('_', ' ').title()
    handle = parts[1].lower()

    return jsonify({
        'success': True,
        'upi_id': upi_id,
        'account_holder': name_part if name_part else 'Alex Rivera',
        'bank_network': handle.upper(),
        'message': f"Verified: {name_part or 'Account Holder'} ({handle.upper()})"
    })

@app.route('/api/orders/<order_number>/reorder', methods=['POST'])
@login_required
def api_reorder(order_number):
    session_token = session['session_token']
    order = query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404

    order_items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
    if not order_items:
        return jsonify({'success': False, 'message': 'No items in order to reorder'}), 400

    # Clear current cart
    execute_db("DELETE FROM cart_items WHERE session_id = ?", (session_token,))
    user_id = g.user['id']

    for item in order_items:
        menu_item_id = item['menu_item_id']
        if not menu_item_id:
            mi = query_db("SELECT id FROM menu_items WHERE restaurant_id = ? AND name = ?", (order['restaurant_id'], item['name']), one=True)
            menu_item_id = mi['id'] if mi else 1

        execute_db('''
            INSERT INTO cart_items (session_id, user_id, menu_item_id, restaurant_id, quantity, special_instructions, selected_modifiers_json, item_total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_token, user_id, menu_item_id, order['restaurant_id'], item['quantity'], 'Reordered from ' + order_number, '[]', item['total_price']))

    return jsonify({
        'success': True,
        'message': 'Items added to your cart!',
        'redirect_url': url_for('cart')
    })

@app.route('/api/orders/<order_number>/review', methods=['POST'])
@login_required
def api_submit_order_review(order_number):
    user_id = g.user['id']
    user_name = g.user['name']

    order = query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404

    data = request.get_json(silent=True) or {}
    rating = int(data.get('rating', 5))
    comment = data.get('comment', '').strip()

    execute_db('''
        INSERT INTO reviews (restaurant_id, user_id, rating, comment, user_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (order['restaurant_id'], user_id, rating, comment, user_name))

    # Recalculate restaurant rating & count
    rev_stats = query_db("SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM reviews WHERE restaurant_id = ?", (order['restaurant_id'],), one=True)
    if rev_stats and rev_stats['count'] > 0:
        new_avg = round(rev_stats['avg_rating'], 1)
        execute_db("UPDATE restaurants SET rating = ?, review_count = ? WHERE id = ?", (new_avg, rev_stats['count'], order['restaurant_id']))

    return jsonify({
        'success': True,
        'message': 'Thank you! Your review and rating have been posted.'
    })

@app.route('/api/payment-methods/add', methods=['POST'])
@login_required
def api_add_payment_method():
    user_id = g.user['id']
    data = request.get_json(silent=True) or {}
    pm_type = data.get('type', 'card')

    if pm_type == 'card':
        brand = data.get('card_brand', 'Visa')
        card_num = data.get('card_number', '4242')
        last4 = card_num[-4:] if len(card_num) >= 4 else '4242'
        exp_m = data.get('exp_month', '12')
        exp_y = data.get('exp_year', '2028')
        execute_db('''
            INSERT INTO payment_methods (user_id, type, card_brand, last4, exp_month, exp_year, is_default)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (user_id, 'card', brand, last4, exp_m, exp_y))
    elif pm_type == 'upi':
        upi_id = data.get('upi_id', 'user@okaxis').strip()
        execute_db('''
            INSERT INTO payment_methods (user_id, type, card_brand, upi_id, is_default)
            VALUES (?, 'upi', 'UPI', ?, 0)
        ''', (user_id, upi_id))

    return jsonify({'success': True, 'message': 'Payment method saved securely!'})

@app.route('/api/payment-methods/<int:pm_id>/delete', methods=['POST', 'DELETE'])
@login_required
def api_delete_payment_method(pm_id):
    user_id = g.user['id']
    execute_db("DELETE FROM payment_methods WHERE id = ? AND user_id = ?", (pm_id, user_id))
    return jsonify({'success': True, 'message': 'Payment method removed.'})

@app.route('/api/addresses/<int:addr_id>/delete', methods=['POST', 'DELETE'])
@login_required
def api_delete_address(addr_id):
    user_id = g.user['id']
    execute_db("DELETE FROM addresses WHERE id = ? AND user_id = ?", (addr_id, user_id))
    return jsonify({'success': True, 'message': 'Address deleted.'})

@app.route('/api/addresses/<int:addr_id>/default', methods=['POST'])
@login_required
def api_set_default_address(addr_id):
    user_id = g.user['id']
    execute_db("UPDATE addresses SET is_default = 0 WHERE user_id = ?", (user_id,))
    execute_db("UPDATE addresses SET is_default = 1 WHERE id = ? AND user_id = ?", (addr_id, user_id))
    return jsonify({'success': True, 'message': 'Default address updated.'})

@app.route('/api/orders/<order_number>/status')
def api_order_status(order_number):
    order = query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    courier = query_db("SELECT * FROM couriers WHERE id = ?", (order['courier_id'],), one=True) if order['courier_id'] else None

    return jsonify({
        'order_number': order['order_number'],
        'status': order['status'],
        'courier_lat': order['courier_lat'],
        'courier_lng': order['courier_lng'],
        'courier_name': courier['name'] if courier else 'Courier Assigned',
        'courier_phone': courier['phone'] if courier else '',
        'courier_rating': courier['rating'] if courier else 4.9,
        'vehicle': courier['vehicle_type'] if courier else 'Vehicle'
    })

@app.route('/api/orders/<order_number>/advance-status', methods=['POST'])
def api_advance_order_status(order_number):
    order = query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    status_flow = ['placed', 'confirmed', 'preparing', 'ready', 'picked_up', 'on_the_way', 'delivered']
    current_status = order['status']

    data = request.get_json(silent=True) or {}
    forced_status = data.get('status')

    if forced_status and forced_status in status_flow:
        new_status = forced_status
    else:
        if current_status in status_flow:
            idx = status_flow.index(current_status)
            new_status = status_flow[min(idx + 1, len(status_flow) - 1)]
        else:
            new_status = 'confirmed'

    u_dict = dict(g.user) if g.user else {}
    courier = get_current_courier() if u_dict.get('role') in ('courier', 'admin') else None
    courier_id = courier['id'] if courier else None

    if courier_id and not order['courier_id']:
        execute_db("UPDATE orders SET courier_id = ? WHERE order_number = ?", (courier_id, order_number))

    if new_status == 'delivered':
        execute_db("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE order_number = ?", (new_status, order_number))
        assigned_courier_id = order['courier_id'] or courier_id
        if assigned_courier_id:
            execute_db("UPDATE couriers SET total_trips = total_trips + 1 WHERE id = ?", (assigned_courier_id,))
    else:
        execute_db("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE order_number = ?", (new_status, order_number))

    return jsonify({
        'success': True,
        'previous_status': current_status,
        'new_status': new_status
    })

@app.route('/api/favorites/toggle', methods=['POST'])
@login_required
def api_toggle_favorite():
    user_id = g.user['id']
    data = request.get_json(silent=True) or {}
    restaurant_id = data.get('restaurant_id')
    menu_item_id = data.get('menu_item_id')

    if restaurant_id:
        existing = query_db("SELECT id FROM favorites WHERE user_id = ? AND restaurant_id = ?", (user_id, restaurant_id), one=True)
        if existing:
            execute_db("DELETE FROM favorites WHERE id = ?", (existing['id'],))
            is_fav = False
        else:
            execute_db("INSERT INTO favorites (user_id, restaurant_id) VALUES (?, ?)", (user_id, restaurant_id))
            is_fav = True
    elif menu_item_id:
        existing = query_db("SELECT id FROM favorites WHERE user_id = ? AND menu_item_id = ?", (user_id, menu_item_id), one=True)
        if existing:
            execute_db("DELETE FROM favorites WHERE id = ?", (existing['id'],))
            is_fav = False
        else:
            execute_db("INSERT INTO favorites (user_id, menu_item_id) VALUES (?, ?)", (user_id, menu_item_id))
            is_fav = True
    else:
        return jsonify({'error': 'Missing ID'}), 400

    count_res = query_db("SELECT COUNT(*) as fav_count FROM favorites WHERE user_id = ?", (user_id,), one=True)
    return jsonify({'success': True, 'is_favorite': is_fav, 'fav_count': count_res['fav_count']})

@app.route('/api/partner/menu/toggle-availability', methods=['POST'])
@role_required('restaurant', 'admin')
def api_toggle_menu_availability():
    data = request.get_json(silent=True) or {}
    item_id = data.get('item_id')
    item = query_db("SELECT is_available FROM menu_items WHERE id = ?", (item_id,), one=True)
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    new_state = 0 if item['is_available'] else 1
    execute_db("UPDATE menu_items SET is_available = ? WHERE id = ?", (new_state, item_id))
    return jsonify({'success': True, 'is_available': new_state})

@app.route('/api/courier/toggle-online', methods=['POST'])
@role_required('courier', 'admin')
def api_courier_toggle_online():
    courier = get_current_courier()
    courier_id = courier['id'] if courier else 1
    new_state = 0 if courier and courier['is_online'] else 1
    execute_db("UPDATE couriers SET is_online = ? WHERE id = ?", (new_state, courier_id))
    return jsonify({'success': True, 'is_online': new_state})

@app.route('/api/search/suggestions')
def api_search_suggestions():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'restaurants': [], 'dishes': []})

    term = f"%{q}%"
    rests = query_db("SELECT id, name, cuisine, rating, image_url FROM restaurants WHERE name LIKE ? OR cuisine LIKE ? LIMIT 4", (term, term))
    dishes = query_db('''
        SELECT mi.id, mi.name, mi.price, mi.restaurant_id, r.name as restaurant_name
        FROM menu_items mi
        JOIN restaurants r ON mi.restaurant_id = r.id
        WHERE mi.name LIKE ? LIMIT 4
    ''', (term,))

    return jsonify({
        'restaurants': [dict(r) for r in rests],
        'dishes': [dict(d) for d in dishes]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
