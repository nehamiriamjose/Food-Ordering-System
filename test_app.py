import os
import unittest
import json
from config import Config

# Isolate database for tests so cravecart.db is NEVER modified by test runs
TEST_DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test_cravecart.db')
Config.DATABASE_PATH = TEST_DB_PATH

from app import app
from database import init_db, query_db, execute_db
from seed_data import seed_database
from werkzeug.security import check_password_hash

class CraveCartFullStackTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Config.DATABASE_PATH = TEST_DB_PATH
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        seed_database(drop_all=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def setUp(self):
        Config.DATABASE_PATH = TEST_DB_PATH
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        self.client = app.test_client()
        seed_database(drop_all=True)

    def login_as(self, email="alex@cravecart.demo", password="password123"):
        return self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def test_unauthenticated_root_redirects_to_login(self):
        # When unauthenticated visitor opens the website root, they land on /login
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))

    def test_guest_public_routes_render_ok(self):
        # Verify unauthenticated guest can view public pages, auth, and help
        routes = [
            '/restaurants',
            '/restaurants/1',
            '/search?q=pizza',
            '/cart',
            '/offers',
            '/login',
            '/signup',
            '/forgot-password',
            '/help'
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200, f"Public route {route} failed with status {response.status_code}")

    def test_unauthenticated_protected_customer_routes_redirect_to_login(self):
        # Unauthenticated users accessing customer-specific pages redirect to /login
        protected_routes = [
            '/checkout',
            '/orders',
            '/favorites',
            '/profile',
            '/addresses',
            '/payment-methods'
        ]
        for route in protected_routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 302, f"Route {route} did not redirect unauthenticated guest")
                self.assertIn('/login', response.headers.get('Location', ''))

    def test_authenticated_customer_routes_render_ok(self):
        # Log in as Alex Rivera
        login_res = self.login_as("alex@cravecart.demo", "password123")
        self.assertEqual(login_res.status_code, 200)

        # Add item to cart first so /checkout renders 200 OK
        self.client.post('/api/cart/add', json={
            'menu_item_id': 1,
            'quantity': 1,
            'modifiers': []
        })

        routes = [
            '/',
            '/restaurants',
            '/restaurants/1',
            '/cart',
            '/checkout',
            '/orders',
            '/favorites',
            '/profile',
            '/addresses',
            '/payment-methods'
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200, f"Authenticated route {route} failed")

    def test_login_success_and_invalid_credentials(self):
        # 1. Failed login with wrong password
        fail_res = self.client.post('/login', data={
            'email': 'alex@cravecart.demo',
            'password': 'wrongpassword'
        })
        self.assertEqual(fail_res.status_code, 200)
        self.assertIn(b"Invalid email or password", fail_res.data)

        # 2. Successful login
        success_res = self.client.post('/login', data={
            'email': 'alex@cravecart.demo',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(success_res.status_code, 200)
        self.assertIn(b"Welcome back", success_res.data)

        # 3. Next URL parameter redirection
        with self.client.session_transaction() as sess:
            sess.clear()

        next_res = self.client.post('/login?next=%2Fprofile', data={
            'email': 'alex@cravecart.demo',
            'password': 'password123'
        })
        self.assertEqual(next_res.status_code, 302)
        self.assertIn('/profile', next_res.headers.get('Location', ''))

    def test_strict_role_login_validation(self):
        # Customer cannot sign in via Restaurant or Courier tabs
        res_rest = self.client.post('/login', data={
            'email': 'alex@cravecart.demo',
            'password': 'password123',
            'selected_role': 'restaurant'
        })
        self.assertEqual(res_rest.status_code, 200)
        self.assertIn(b"is registered as a Customer account and cannot sign into the Restaurant", res_rest.data)

        res_cour = self.client.post('/login', data={
            'email': 'alex@cravecart.demo',
            'password': 'password123',
            'selected_role': 'courier'
        })
        self.assertEqual(res_cour.status_code, 200)
        self.assertIn(b"is registered as a Customer account and cannot sign into the Courier", res_cour.data)

        # Restaurant cannot sign in via Customer tab
        res_cust = self.client.post('/login', data={
            'email': 'mario@emberandcrust.demo',
            'password': 'password123',
            'selected_role': 'customer'
        })
        self.assertEqual(res_cust.status_code, 200)
        self.assertIn(b"is registered as a Restaurant Partner account", res_cust.data)

        # Courier cannot sign in via Customer tab
        res_cour_as_cust = self.client.post('/login', data={
            'email': 'marcus@courier.demo',
            'password': 'password123',
            'selected_role': 'customer'
        })
        self.assertEqual(res_cour_as_cust.status_code, 200)
        self.assertIn(b"is registered as a Courier Partner account", res_cour_as_cust.data)

    def test_customer_blocked_from_partner_and_courier_portals(self):
        # Log in as Customer
        self.login_as('alex@cravecart.demo', 'password123')
        
        # Accessing /partner redirects customer back to /
        resp_partner = self.client.get('/partner')
        self.assertEqual(resp_partner.status_code, 302)
        self.assertEqual(resp_partner.headers.get('Location', ''), '/')

        # Accessing /courier redirects customer back to /
        resp_courier = self.client.get('/courier')
        self.assertEqual(resp_courier.status_code, 302)
        self.assertEqual(resp_courier.headers.get('Location', ''), '/')

    def test_signup_flow(self):
        # Sign up a new customer account
        res = self.client.post('/signup', data={
            'name': 'Taylor Swift',
            'email': 'taylor@example.com',
            'phone': '(555) 123-4567',
            'password': 'taylorpassword',
            'role': 'customer'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Account created successfully", res.data)

        # Verify user exists in database with hashed password
        user = query_db("SELECT * FROM users WHERE email = 'taylor@example.com'", one=True)
        self.assertIsNotNone(user)
        self.assertEqual(user['name'], 'Taylor Swift')
        self.assertTrue(check_password_hash(user['password_hash'], 'taylorpassword'))

        # Duplicate email registration rejected
        dup_res = self.client.post('/signup', data={
            'name': 'Taylor Clone',
            'email': 'taylor@example.com',
            'password': 'taylorpassword'
        }, follow_redirects=True)
        self.assertEqual(dup_res.status_code, 200)
        self.assertIn(b"already exists", dup_res.data)

    def test_logout_clears_session(self):
        self.login_as("alex@cravecart.demo", "password123")
        
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b"You have been signed out", logout_res.data)

        # Attempt to access profile after logout -> must redirect
        prof_res = self.client.get('/profile')
        self.assertEqual(prof_res.status_code, 302)

    def test_role_based_access_control(self):
        # 1. Customer trying to access Partner dashboard -> redirected/blocked
        self.login_as("alex@cravecart.demo", "password123")
        partner_res = self.client.get('/partner')
        self.assertEqual(partner_res.status_code, 302)

        # 2. Restaurant partner can access Partner dashboard
        self.login_as("mario@emberandcrust.demo", "password123")
        partner_ok = self.client.get('/partner')
        self.assertEqual(partner_ok.status_code, 200)

        partner_orders_ok = self.client.get('/partner/orders')
        self.assertEqual(partner_orders_ok.status_code, 200)

        # 3. Courier partner can access Courier dashboard
        self.login_as("marcus@courier.demo", "password123")
        courier_ok = self.client.get('/courier')
        self.assertEqual(courier_ok.status_code, 200)

    def test_change_password_api(self):
        self.login_as("alex@cravecart.demo", "password123")

        # Wrong current password
        bad_res = self.client.post('/api/profile/change-password', json={
            'current_password': 'wrongpassword',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        self.assertEqual(bad_res.status_code, 400)
        self.assertFalse(bad_res.get_json()['success'])

        # Successful password change
        good_res = self.client.post('/api/profile/change-password', json={
            'current_password': 'password123',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        self.assertEqual(good_res.status_code, 200)
        self.assertTrue(good_res.get_json()['success'])

        # Verify new password in DB
        user = query_db("SELECT * FROM users WHERE email = 'alex@cravecart.demo'", one=True)
        self.assertTrue(check_password_hash(user['password_hash'], 'newpassword123'))

    def test_forgot_password_reset(self):
        # 1. Verify email
        verify_res = self.client.post('/forgot-password', data={
            'email': 'alex@cravecart.demo'
        })
        self.assertEqual(verify_res.status_code, 200)

        # 2. Set new password
        reset_res = self.client.post('/forgot-password', data={
            'email': 'alex@cravecart.demo',
            'new_password': 'resetalexpass456'
        }, follow_redirects=True)
        self.assertEqual(reset_res.status_code, 200)
        self.assertIn(b"Password updated successfully", reset_res.data)

        # Verify DB
        user = query_db("SELECT * FROM users WHERE email = 'alex@cravecart.demo'", one=True)
        self.assertTrue(check_password_hash(user['password_hash'], 'resetalexpass456'))

    def test_guest_cart_linked_to_user_on_login(self):
        # 1. Guest adds item to cart
        self.client.post('/api/cart/add', json={
            'menu_item_id': 1,
            'quantity': 2,
            'modifiers': []
        })

        # 2. Guest logs in
        self.login_as("alex@cravecart.demo", "password123")

        # 3. Verify cart items still exist and are linked
        cart_res = self.client.get('/api/cart')
        c_data = cart_res.get_json()
        self.assertEqual(c_data['count'], 2)

    def test_checkout_and_order_tracking(self):
        self.login_as("alex@cravecart.demo", "password123")
        
        self.client.post('/api/cart/add', json={
            'menu_item_id': 1,
            'quantity': 1,
            'modifiers': []
        })

        checkout_res = self.client.post('/api/checkout', json={
            'tip': 4.00,
            'delivery_instructions': 'Leave at front desk',
            'payment_method': 'Visa •••• 4242'
        })
        self.assertEqual(checkout_res.status_code, 200)
        ch_data = checkout_res.get_json()
        self.assertTrue(ch_data['success'])
        order_num = ch_data['order_number']

        adv_res = self.client.post(f'/api/orders/{order_num}/advance-status')
        self.assertEqual(adv_res.status_code, 200)
        self.assertEqual(adv_res.get_json()['new_status'], 'confirmed')

    def test_multi_role_login_redirects(self):
        # 1. Customer login redirects to /
        res_cust = self.client.post('/login', data={
            'email': 'alex@cravecart.demo',
            'password': 'password123'
        })
        self.assertEqual(res_cust.status_code, 302)
        self.assertEqual(res_cust.headers.get('Location'), '/')

        with self.client.session_transaction() as sess:
            sess.clear()

        # 2. Restaurant partner login redirects to /partner
        res_rest = self.client.post('/login', data={
            'email': 'mario@emberandcrust.demo',
            'password': 'password123'
        })
        self.assertEqual(res_rest.status_code, 302)
        self.assertEqual(res_rest.headers.get('Location'), '/partner')

        with self.client.session_transaction() as sess:
            sess.clear()

        # 3. Courier partner login redirects to /courier
        res_cour = self.client.post('/login', data={
            'email': 'marcus@courier.demo',
            'password': 'password123'
        })
        self.assertEqual(res_cour.status_code, 302)
        self.assertEqual(res_cour.headers.get('Location'), '/courier')

    def test_restaurant_partner_signup_creates_kitchen(self):
        res = self.client.post('/signup', data={
            'name': 'Chef Antonio',
            'email': 'antonio@trattoria.demo',
            'phone': '(555) 888-9999',
            'password': 'antoniopassword',
            'role': 'restaurant',
            'restaurant_name': 'Trattoria Bella Napoli',
            'restaurant_cuisine': 'Italian & Pizza',
            'restaurant_address': '77 Little Italy St, New York, NY'
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/partner')

        # Verify restaurant was created in DB
        rest = query_db("SELECT * FROM restaurants WHERE email = 'antonio@trattoria.demo'", one=True)
        self.assertIsNotNone(rest)
        self.assertEqual(rest['name'], 'Trattoria Bella Napoli')
        self.assertEqual(rest['cuisine'], 'Italian & Pizza')

    def test_courier_partner_signup_creates_fleet_profile(self):
        res = self.client.post('/signup', data={
            'name': 'Sam Rider',
            'email': 'sam@speedy.demo',
            'phone': '(555) 777-6666',
            'password': 'sampassword',
            'role': 'courier',
            'vehicle_type': 'Electric Cargo E-Bike',
            'vehicle_plate': 'E-CARGO-88'
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/courier')

        # Verify courier profile was created in DB
        cour = query_db("SELECT * FROM couriers WHERE phone = '(555) 777-6666'", one=True)
        self.assertIsNotNone(cour)
        self.assertEqual(cour['name'], 'Sam Rider')
        self.assertEqual(cour['vehicle_type'], 'Electric Cargo E-Bike')
        self.assertEqual(cour['vehicle_plate'], 'E-CARGO-88')

    def test_new_user_signup_has_no_avatar_and_renders_placeholder(self):
        # Sign up user 'Don'
        res = self.client.post('/signup', data={
            'name': 'Don',
            'email': 'don@example.com',
            'password': 'password123',
            'role': 'customer'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check DB: avatar_url must be None/empty (no stock photo)
        user = query_db("SELECT * FROM users WHERE email = 'don@example.com'", one=True)
        self.assertIsNotNone(user)
        self.assertIsNone(user['avatar_url'])

        # Check profile page render: contains initial placeholder 'D'
        prof_res = self.client.get('/profile')
        self.assertEqual(prof_res.status_code, 200)
        self.assertIn(b"user-avatar-placeholder", prof_res.data)
        self.assertIn(b">D<", prof_res.data)

    def test_avatar_upload_and_removal_api(self):
        import io
        self.login_as("alex@cravecart.demo", "password123")

        # 1. Upload mock avatar image
        fake_image = (io.BytesIO(b"fake-image-bytes-png-data"), "test_avatar.png")
        upload_res = self.client.post('/api/profile/upload-avatar', data={
            'avatar_file': fake_image
        }, content_type='multipart/form-data')
        
        self.assertEqual(upload_res.status_code, 200)
        data = upload_res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('uploads/avatars', data['avatar_url'])

        # Verify DB updated
        user = query_db("SELECT * FROM users WHERE email = 'alex@cravecart.demo'", one=True)
        self.assertIsNotNone(user['avatar_url'])

        # 2. Remove avatar
        remove_res = self.client.post('/api/profile/remove-avatar')
        self.assertEqual(remove_res.status_code, 200)
        rem_data = remove_res.get_json()
        self.assertTrue(rem_data['success'])

    def test_restaurant_signup_with_map_location(self):
        # Register a new restaurant with custom map coordinates
        signup_res = self.client.post('/signup', data={
            'name': 'Chef Antonio',
            'email': 'antonio@pastanapoletana.demo',
            'phone': '(555) 777-8899',
            'password': 'password123',
            'role': 'restaurant',
            'restaurant_name': 'Trattoria Napoletana',
            'restaurant_cuisine': 'Italian & Pizza',
            'restaurant_address': '842 7th Ave, New York, NY',
            'restaurant_lat': '40.761500',
            'restaurant_lng': '-73.982300'
        }, follow_redirects=True)
        self.assertEqual(signup_res.status_code, 200)

        # Check DB record
        rest = query_db("SELECT * FROM restaurants WHERE email = 'antonio@pastanapoletana.demo'", one=True)
        self.assertIsNotNone(rest)
        self.assertEqual(rest['name'], 'Trattoria Napoletana')
        self.assertAlmostEqual(rest['lat'], 40.761500, places=4)
        self.assertAlmostEqual(rest['lng'], -73.982300, places=4)
        self.assertEqual(rest['address'], '842 7th Ave, New York, NY')

    def test_restaurant_partner_add_dish_and_edit_flow(self):
        import io
        # 1. Log in as Mario Rossi (Restaurant Partner)
        self.login_as("mario@emberandcrust.demo", "password123")

        # 2. Add a new dish with image upload and dietary details
        mock_dish_image = (io.BytesIO(b"fake-dish-jpeg-data"), "truffle_gnocchi.jpg")
        add_res = self.client.post('/partner/menu/item/add', data={
            'category_id': 1,
            'name': 'Artisan Truffle Gnocchi',
            'description': 'Handmade potato gnocchi with black summer truffle emulsion and aged parmesan.',
            'price': '22.50',
            'is_vegetarian': '1',
            'is_popular': '1',
            'dish_image_file': mock_dish_image
        }, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        # 3. Verify dish in DB
        dish = query_db("SELECT * FROM menu_items WHERE name = 'Artisan Truffle Gnocchi'", one=True)
        self.assertIsNotNone(dish)
        self.assertEqual(dish['price'], 22.50)
        self.assertEqual(dish['is_vegetarian'], 1)
        self.assertEqual(dish['is_popular'], 1)
        self.assertIn('uploads/dishes', dish['image_url'])

        # 4. Toggle stock
        toggle_res = self.client.post(f'/partner/menu/item/{dish["id"]}/toggle-stock')
        self.assertEqual(toggle_res.status_code, 200)
        t_data = toggle_res.get_json()
        self.assertTrue(t_data['success'])
        self.assertFalse(t_data['is_available'])

    def test_restaurant_partner_update_map_location(self):
        self.login_as("mario@emberandcrust.demo", "password123")

        # Update profile and map pin coordinates
        prof_res = self.client.post('/partner/restaurant-profile', data={
            'name': 'Ember & Crust Wood-Fired Pizza',
            'cuisine': 'Artisan Wood-Fired Pizza',
            'phone': '(555) 345-6789',
            'address': '450 Lexington Ave, New York, NY',
            'lat': '40.752800',
            'lng': '-73.975400',
            'min_order': '15.00',
            'delivery_fee': '2.99',
            'delivery_time_min': '20',
            'delivery_time_max': '35',
            'is_open': '1',
            'description': 'Award-winning sourdough artisan pizzas.'
        }, follow_redirects=True)
        self.assertEqual(prof_res.status_code, 200)

        rest = query_db("SELECT * FROM restaurants WHERE id = 1", one=True)
        self.assertAlmostEqual(rest['lat'], 40.752800, places=4)
        self.assertAlmostEqual(rest['lng'], -73.975400, places=4)
        self.assertEqual(rest['address'], '450 Lexington Ave, New York, NY')

    def test_restaurant_partner_promotions_management_and_customer_redemption(self):
        # 1. Partner logs in and views promotions studio
        self.login_as("mario@emberandcrust.demo", "password123")
        promo_page_res = self.client.get('/partner/promotions')
        self.assertEqual(promo_page_res.status_code, 200)
        self.assertIn(b"Promotions & Deals Studio", promo_page_res.data)

        # 2. Partner creates a new promotional campaign
        create_res = self.client.post('/partner/promotions/add', data={
            'code': 'SUMMER25',
            'description': 'Summer festival 25% discount on all orders',
            'discount_type': 'percent',
            'discount_value': '25.0',
            'min_spend': '20.0',
            'max_discount': '15.0',
            'is_active': '1'
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)

        # 3. Verify in database
        promo = query_db("SELECT * FROM promo_codes WHERE code = 'SUMMER25'", one=True)
        self.assertIsNotNone(promo)
        self.assertEqual(promo['discount_value'], 25.0)
        self.assertEqual(promo['is_active'], 1)

        # 4. Toggle promotion status (active -> inactive)
        toggle_res = self.client.post(f'/partner/promotions/{promo["id"]}/toggle', follow_redirects=True)
        self.assertEqual(toggle_res.status_code, 200)
        promo_off = query_db("SELECT * FROM promo_codes WHERE id = ?", (promo['id'],), one=True)
        self.assertEqual(promo_off['is_active'], 0)

        # 5. Toggle back to active
        self.client.post(f'/partner/promotions/{promo["id"]}/toggle', follow_redirects=True)
        promo_on = query_db("SELECT * FROM promo_codes WHERE id = ?", (promo['id'],), one=True)
        self.assertEqual(promo_on['is_active'], 1)

        # 6. Customer logs in and applies the newly created promo code at checkout
        self.login_as("alex@cravecart.demo", "password123")
        self.client.post('/api/cart/add', json={
            'menu_item_id': 1, # Price ~ $18.50 x 2 = $37.00
            'quantity': 2,
            'modifiers': []
        })

        apply_res = self.client.post('/api/cart/apply-promo', json={'code': 'SUMMER25'})
        self.assertEqual(apply_res.status_code, 200)
        a_data = apply_res.get_json()
        self.assertTrue(a_data['success'])
        self.assertIn("SUMMER25", a_data['message'])
        self.assertGreater(a_data['discount'], 0)

        # 7. Partner deletes the promo code
        self.login_as("mario@emberandcrust.demo", "password123")
        del_res = self.client.post(f'/partner/promotions/{promo["id"]}/delete', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        deleted = query_db("SELECT * FROM promo_codes WHERE id = ?", (promo['id'],), one=True)
        self.assertIsNone(deleted)

    def test_promotion_countdown_duration_auto_expire_and_extend(self):
        import datetime
        # 1. Partner logs in and creates a promo with a 3-day duration countdown
        self.login_as("mario@emberandcrust.demo", "password123")
        create_res = self.client.post('/partner/promotions/add', data={
            'code': 'TIMED30',
            'description': '3-Day Flash 30% Off',
            'discount_type': 'percent',
            'discount_value': '30.0',
            'min_spend': '15.0',
            'max_discount': '20.0',
            'duration_days': '3',
            'is_active': '1'
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)

        promo = query_db("SELECT * FROM promo_codes WHERE code = 'TIMED30'", one=True)
        self.assertIsNotNone(promo)
        self.assertIsNotNone(promo['expires_at'])
        self.assertEqual(promo['is_active'], 1)

        # 2. Simulate countdown reaching zero (set expires_at in the past)
        past_time = (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        execute_db("UPDATE promo_codes SET expires_at = ? WHERE id = ?", (past_time, promo['id']))

        # 3. Customer tries to apply expired promo code -> rejected
        self.login_as("alex@cravecart.demo", "password123")
        self.client.post('/api/cart/add', json={'menu_item_id': 1, 'quantity': 2, 'modifiers': []})
        apply_res = self.client.post('/api/cart/apply-promo', json={'code': 'TIMED30'})
        self.assertEqual(apply_res.status_code, 400)
        self.assertIn("expired", apply_res.get_json()['message'].lower())

        # 4. Verify promo is automatically marked inactive
        promo_after = query_db("SELECT is_active FROM promo_codes WHERE id = ?", (promo['id'],), one=True)
        self.assertEqual(promo_after['is_active'], 0)

        # 5. Partner extends the promotion by +7 days
        self.login_as("mario@emberandcrust.demo", "password123")
        extend_res = self.client.post(f'/partner/promotions/{promo["id"]}/extend', data={'extend_days': 7}, follow_redirects=True)
        self.assertEqual(extend_res.status_code, 200)

        promo_extended = query_db("SELECT * FROM promo_codes WHERE id = ?", (promo['id'],), one=True)
        self.assertEqual(promo_extended['is_active'], 1)
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.assertGreater(str(promo_extended['expires_at']), now_str)

        # 6. Customer can now apply the extended active promo code
        self.login_as("alex@cravecart.demo", "password123")
        reapply_res = self.client.post('/api/cart/apply-promo', json={'code': 'TIMED30'})
        self.assertEqual(reapply_res.status_code, 200)
        self.assertTrue(reapply_res.get_json()['success'])

    def test_courier_delivery_mission_controller_and_route_map(self):
        # 1. Courier logs in
        self.login_as("marcus@courier.demo", "password123")

        # 2. View courier mission controller for active order ORD-78901
        res = self.client.get('/courier/deliveries/ORD-78901')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Mission Controller #ORD-78901", res.data)
        self.assertIn(b"courierRouteMap", res.data)
        self.assertIn(b"Turn-by-Turn GPS", res.data)

    def test_restaurant_partner_dish_size_variations_and_cart_ordering(self):
        # 1. Restaurant Partner logs in
        self.login_as("mario@emberandcrust.demo", "password123")

        # 2. Add a new dish with Small, Medium, Large size options
        add_res = self.client.post('/partner/menu/item/add', data={
            'category_id': 1,
            'name': 'Gourmet Quattro Formaggi',
            'description': 'Four artisanal cheeses with honeycomb drizzle and fresh thyme.',
            'price': '18.00',
            'enable_sizes': '1',
            'size_name[]': ['Small (10")', 'Medium (12")', 'Large (14")'],
            'size_delta[]': ['-3.00', '0.00', '4.50'],
            'size_default_index': '1'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        # 3. Verify dish and size modifier group in database
        dish = query_db("SELECT * FROM menu_items WHERE name = 'Gourmet Quattro Formaggi'", one=True)
        self.assertIsNotNone(dish)
        self.assertEqual(dish['price'], 18.00)

        size_grp = query_db("SELECT * FROM modifier_groups WHERE menu_item_id = ? AND name = 'Choose Size'", (dish['id'],), one=True)
        self.assertIsNotNone(size_grp)

        size_opts = query_db("SELECT * FROM modifier_options WHERE modifier_group_id = ? ORDER BY id ASC", (size_grp['id'],))
        self.assertEqual(len(size_opts), 3)
        self.assertEqual(size_opts[0]['name'], 'Small (10")')
        self.assertEqual(size_opts[0]['price_delta'], -3.00)
        self.assertEqual(size_opts[1]['name'], 'Medium (12")')
        self.assertEqual(size_opts[1]['is_default'], 1)
        self.assertEqual(size_opts[2]['name'], 'Large (14")')
        self.assertEqual(size_opts[2]['price_delta'], 4.50)

        # 4. Fetch via API
        api_res = self.client.get(f"/api/menu-items/{dish['id']}")
        self.assertEqual(api_res.status_code, 200)
        api_data = api_res.get_json()
        self.assertEqual(len(api_data['modifier_groups']), 1)
        self.assertEqual(len(api_data['modifier_groups'][0]['options']), 3)

        # 5. Customer logs in and orders the Large size
        self.login_as("alex@cravecart.demo", "password123")
        cart_add_res = self.client.post('/api/cart/add', json={
            'menu_item_id': dish['id'],
            'quantity': 2,
            'modifiers': [{'name': 'Large (14")', 'price_delta': 4.50}]
        })
        self.assertEqual(cart_add_res.status_code, 200)
        cart_data = cart_add_res.get_json()
        self.assertTrue(cart_data['success'])

        # Verify cart item total: (18.00 + 4.50) * 2 = 45.00
        cart_res = self.client.get('/api/cart')
        cart_info = cart_res.get_json()
        large_item = next((i for i in cart_info['items'] if i['menu_item_id'] == dish['id']), None)
        self.assertIsNotNone(large_item)
        self.assertEqual(large_item['item_total'], 45.00)

        # 6. Partner edits the dish to update sizes
        self.login_as("mario@emberandcrust.demo", "password123")
        edit_res = self.client.post(f"/partner/menu/item/{dish['id']}/edit", data={
            'category_id': 1,
            'name': 'Gourmet Quattro Formaggi Supremo',
            'description': 'Updated description with extra truffle oil.',
            'price': '19.00',
            'enable_sizes': '1',
            'size_name[]': ['Small (10")', 'Medium (12")', 'Large (14")', 'Extra Large (16")'],
            'size_delta[]': ['-2.50', '0.00', '4.00', '7.00'],
            'size_default_index': '2'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)

        # Verify updated dish and 4 sizes
        updated_dish = query_db("SELECT * FROM menu_items WHERE id = ?", (dish['id'],), one=True)
        self.assertEqual(updated_dish['name'], 'Gourmet Quattro Formaggi Supremo')
        self.assertEqual(updated_dish['price'], 19.00)

        updated_opts = query_db("SELECT * FROM modifier_options WHERE modifier_group_id = ? ORDER BY id ASC", (size_grp['id'],))
        self.assertEqual(len(updated_opts), 4)
        self.assertEqual(updated_opts[3]['name'], 'Extra Large (16")')
        self.assertEqual(updated_opts[3]['price_delta'], 7.00)

    def test_partner_dish_multiselect_sizes_and_daily_stock(self):
        # 1. Partner logs in
        self.login_as("mario@emberandcrust.demo", "password123")

        # 2. Add dish with Multi-Choice size selection and specific Daily Stock per size
        add_res = self.client.post('/partner/menu/item/add', data={
            'category_id': 1,
            'name': 'Artisan Flight Sampler',
            'description': 'Choose multiple portion sizes to sample or share.',
            'price': '12.00',
            'enable_sizes': '1',
            'size_multiselect': '1',
            'size_name[]': ['Small Tasting (8oz)', 'Regular Bowl (12oz)', 'Party Share (16oz)'],
            'size_delta[]': ['-2.00', '0.00', '4.00'],
            'size_stock[]': ['15', '35', '10'],
            'size_default_index': '1'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        # 3. Verify in database
        dish = query_db("SELECT * FROM menu_items WHERE name = 'Artisan Flight Sampler'", one=True)
        self.assertIsNotNone(dish)

        grp = query_db("SELECT * FROM modifier_groups WHERE menu_item_id = ?", (dish['id'],), one=True)
        self.assertIsNotNone(grp)
        self.assertGreater(grp['max_selection'], 1)  # Multi-choice allows > 1

        opts = query_db("SELECT * FROM modifier_options WHERE modifier_group_id = ? ORDER BY id ASC", (grp['id'],))
        self.assertEqual(len(opts), 3)
        self.assertEqual(opts[0]['name'], 'Small Tasting (8oz)')
        self.assertEqual(opts[0]['stock_quantity'], 15)
        self.assertEqual(opts[1]['name'], 'Regular Bowl (12oz)')
        self.assertEqual(opts[1]['stock_quantity'], 35)
        self.assertEqual(opts[2]['name'], 'Party Share (16oz)')
        self.assertEqual(opts[2]['stock_quantity'], 10)

        # 4. Verify API response includes stock_quantity and multi-choice max_selection
        api_res = self.client.get(f"/api/menu-items/{dish['id']}")
        self.assertEqual(api_res.status_code, 200)
        api_json = api_res.get_json()
        self.assertGreater(api_json['modifier_groups'][0]['max_selection'], 1)
        self.assertEqual(api_json['modifier_groups'][0]['options'][0]['stock_quantity'], 15)
        self.assertEqual(api_json['modifier_groups'][0]['options'][2]['stock_quantity'], 10)

        # 5. Customer orders with multiple size choices selected simultaneously
        self.login_as("alex@cravecart.demo", "password123")
        cart_add_res = self.client.post('/api/cart/add', json={
            'menu_item_id': dish['id'],
            'quantity': 1,
            'modifiers': [
                {'name': 'Small Tasting (8oz)', 'price_delta': -2.00},
                {'name': 'Party Share (16oz)', 'price_delta': 4.00}
            ]
        })
        self.assertEqual(cart_add_res.status_code, 200)
        self.assertTrue(cart_add_res.get_json()['success'])

        # Verify Cart calculation: (12.00 - 2.00 + 4.00) * 1 = 14.00
        cart_res = self.client.get('/api/cart')
        cart_data = cart_res.get_json()
        item_in_cart = next((i for i in cart_data['items'] if i['menu_item_id'] == dish['id']), None)
        self.assertIsNotNone(item_in_cart)
        self.assertEqual(item_in_cart['item_total'], 14.00)

    def test_new_courier_registration_dashboard_and_mission_lifecycle(self):
        # 1. Sign up brand new courier 'Minu'
        signup_res = self.client.post('/signup', data={
            'name': 'Minu',
            'email': 'minu@courier.demo',
            'phone': '(555) 345-6789',
            'password': 'password123',
            'role': 'courier',
            'vehicle_type': 'Motorcycle',
            'vehicle_plate': 'NY-MINU1'
        }, follow_redirects=True)
        self.assertEqual(signup_res.status_code, 200)

        # 2. View courier overview dashboard
        overview_res = self.client.get('/courier')
        self.assertEqual(overview_res.status_code, 200)
        # Should display Minu's name, not Marcus
        self.assertIn(b"Good afternoon, Minu", overview_res.data)
        self.assertNotIn(b"Marcus", overview_res.data)
        # Today's earnings should start at $0.00 for a fresh courier with 0 trips
        self.assertIn(b"$0.00", overview_res.data)

        # 3. Create a test order placed by a customer (unassigned, courier_id = NULL)
        cust = query_db("SELECT id FROM users WHERE role = 'customer' LIMIT 1", one=True)
        order_id = execute_db('''
            INSERT INTO orders (order_number, customer_id, restaurant_id, courier_id, status, subtotal, tax, delivery_fee, tip, discount, total, payment_method, delivery_address_json)
            VALUES ('ORD-MINU-01', ?, 1, NULL, 'ready', 25.00, 2.00, 3.50, 4.00, 0.00, 34.50, 'Credit Card', '{"street": "456 Broadway", "city": "New York"}')
        ''', (cust['id'],))

        # 4. View deliveries queue: Unassigned order must NOT appear in Minu's deliveries queue
        queue_res = self.client.get('/courier/deliveries')
        self.assertEqual(queue_res.status_code, 200)
        self.assertNotIn(b"ORD-MINU-01", queue_res.data)

        # 5. If unassigned courier attempts to advance status before being assigned -> 403 Forbidden
        unauth_pick = self.client.post('/api/orders/ORD-MINU-01/advance-status', json={'status': 'picked_up'})
        self.assertEqual(unauth_pick.status_code, 403)

        # 6. Restaurant Partner logs in and assigns ORD-MINU-01 specifically to Minu
        minu_courier = query_db("SELECT * FROM couriers WHERE name = 'Minu'", one=True)
        self.login_as("mario@emberandcrust.demo", "password123")
        assign_res = self.client.post('/api/orders/ORD-MINU-01/assign-courier', json={'courier_id': minu_courier['id']})
        self.assertEqual(assign_res.status_code, 200)

        # 7. Minu logs back in: Now ORD-MINU-01 appears in Minu's assigned queue
        self.login_as("minu@courier.demo", "password123")
        queue_res2 = self.client.get('/courier/deliveries')
        self.assertEqual(queue_res2.status_code, 200)
        self.assertIn(b"ORD-MINU-01", queue_res2.data)

        # 8. Advance status: Accept & Pick up -> On the way -> Delivered
        pick_res = self.client.post('/api/orders/ORD-MINU-01/advance-status', json={'status': 'picked_up'})
        self.assertEqual(pick_res.status_code, 200)
        self.assertTrue(pick_res.get_json()['success'])

        dep_res = self.client.post('/api/orders/ORD-MINU-01/advance-status', json={'status': 'on_the_way'})
        self.assertEqual(dep_res.status_code, 200)

        deliv_res = self.client.post('/api/orders/ORD-MINU-01/advance-status', json={'status': 'delivered'})
        self.assertEqual(deliv_res.status_code, 200)

        # 9. Check trip count increment and earnings update
        minu_courier_after = query_db("SELECT * FROM couriers WHERE id = ?", (minu_courier['id'],), one=True)
        self.assertEqual(minu_courier_after['total_trips'], 1)

        overview_after = self.client.get('/courier')
        self.assertEqual(overview_after.status_code, 200)
        # Payout for this trip: $3.50 delivery fee + $4.00 tip = $7.50
        self.assertIn(b"$7.50", overview_after.data)

        # 10. Update vehicle profile via dedicated /courier/profile
        courier_prof_get = self.client.get('/courier/profile')
        self.assertEqual(courier_prof_get.status_code, 200)
        self.assertIn(b"Vehicle & Courier Profile", courier_prof_get.data)

        courier_prof_post = self.client.post('/courier/profile', data={
            'name': 'Minu Fast Rider',
            'phone': '(555) 999-8888',
            'vehicle_type': 'Bicycle',
            'vehicle_plate': 'BIKE-09'
        }, follow_redirects=True)
        self.assertEqual(courier_prof_post.status_code, 200)

        minu_courier_updated = query_db("SELECT * FROM couriers WHERE id = ?", (minu_courier['id'],), one=True)
        self.assertEqual(minu_courier_updated['name'], 'Minu Fast Rider')
        self.assertEqual(minu_courier_updated['vehicle_type'], 'Bicycle')
        self.assertEqual(minu_courier_updated['vehicle_plate'], 'BIKE-09')

    def test_delivery_allocation_and_automatic_courier_freeing(self):
        # 1. Log in as Restaurant Partner (Chef Mario Rossi - Ember & Crust)
        self.login_as("mario@emberandcrust.demo", "password123")

        # 2. Check fleet status list API
        fleet_res = self.client.get('/api/couriers/status-list')
        self.assertEqual(fleet_res.status_code, 200)
        fleet_data = fleet_res.get_json()
        self.assertTrue(fleet_data['success'])
        self.assertGreater(len(fleet_data['couriers']), 0)

        # 3. Create a new test order in 'ready' status and pick an initially free online courier
        cust = query_db("SELECT id FROM users WHERE role = 'customer' LIMIT 1", one=True)
        free_courier = next((c for c in fleet_data['couriers'] if c['is_free']), None)
        if not free_courier:
            # If all are busy, mark existing orders as delivered first
            execute_db("UPDATE orders SET status = 'delivered' WHERE status IN ('ready', 'picked_up', 'on_the_way')")
            fleet_res = self.client.get('/api/couriers/status-list')
            fleet_data = fleet_res.get_json()
            free_courier = fleet_data['couriers'][0]
        
        target_courier = free_courier
        
        execute_db('''
            INSERT INTO orders (order_number, customer_id, restaurant_id, courier_id, status, subtotal, tax, delivery_fee, tip, total, payment_method, delivery_address_json)
            VALUES ('ORD-ALLOC-99', ?, 1, NULL, 'ready', 30.00, 2.50, 4.00, 5.00, 41.50, 'Credit Card', '{"street": "123 Main St"}')
        ''', (cust['id'],))

        # 4. Allocate courier to order using API
        assign_res = self.client.post('/api/orders/ORD-ALLOC-99/assign-courier', json={
            'courier_id': target_courier['id']
        })
        self.assertEqual(assign_res.status_code, 200)
        self.assertTrue(assign_res.get_json()['success'])
        self.assertEqual(assign_res.get_json()['courier_name'], target_courier['name'])

        # Verify courier is now busy with this active order
        fleet_res2 = self.client.get('/api/couriers/status-list')
        busy_courier = next(c for c in fleet_res2.get_json()['couriers'] if c['id'] == target_courier['id'])
        self.assertEqual(busy_courier['status_key'], 'busy')
        self.assertIn('ORD-ALLOC-99', busy_courier['status_label'])
        self.assertFalse(busy_courier['is_free'])

        # 5. Advance order to delivered
        self.client.post('/api/orders/ORD-ALLOC-99/advance-status', json={'status': 'picked_up'})
        self.client.post('/api/orders/ORD-ALLOC-99/advance-status', json={'status': 'on_the_way'})
        deliv_res = self.client.post('/api/orders/ORD-ALLOC-99/advance-status', json={'status': 'delivered'})
        self.assertEqual(deliv_res.status_code, 200)

        # 6. Verify courier is now freed up automatically (🟢 Active & Available)
        fleet_res3 = self.client.get('/api/couriers/status-list')
        freed_courier = next(c for c in fleet_res3.get_json()['couriers'] if c['id'] == target_courier['id'])
        self.assertEqual(freed_courier['status_key'], 'available')
        self.assertTrue(freed_courier['is_free'])
        self.assertEqual(freed_courier['status_symbol'], '🟢')

    def test_customer_order_goes_to_kitchen_unassigned_and_courier_access_controlled(self):
        # 1. Customer logs in and places an order
        self.login_as("alex@cravecart.demo", "password123")
        self.client.post('/api/cart/add', json={
            'menu_item_id': 1,
            'quantity': 1,
            'modifiers': []
        })
        checkout_res = self.client.post('/api/checkout', json={
            'tip': 5.00,
            'delivery_instructions': 'Ring doorbell on 2nd floor'
        })
        self.assertEqual(checkout_res.status_code, 200)
        ord_num = checkout_res.get_json()['order_number']

        # 2. Verify order in DB: courier_id MUST be NULL upon checkout
        ord_db = query_db("SELECT * FROM orders WHERE order_number = ?", (ord_num,), one=True)
        self.assertIsNotNone(ord_db)
        self.assertIsNone(ord_db['courier_id'])
        self.assertEqual(ord_db['status'], 'placed')

        # 3. Log in as Courier Marcus: the order must NOT appear in Marcus's active deliveries
        self.login_as("marcus@courier.demo", "password123")
        cour_res = self.client.get('/courier/deliveries')
        self.assertEqual(cour_res.status_code, 200)
        self.assertNotIn(ord_num.encode(), cour_res.data)

        # Marcus attempts to accept or advance the unassigned order -> 403 Forbidden
        unauth_adv = self.client.post(f'/api/orders/{ord_num}/advance-status', json={'status': 'picked_up'})
        self.assertEqual(unauth_adv.status_code, 403)

        # 4. Log in as Restaurant Partner: order appears in kitchen order board
        self.login_as("mario@emberandcrust.demo", "password123")
        kitchen_res = self.client.get('/partner/orders')
        self.assertEqual(kitchen_res.status_code, 200)
        self.assertIn(ord_num.encode(), kitchen_res.data)

        # Restaurant prepares the order: placed -> confirmed -> preparing -> ready
        self.client.post(f'/api/orders/{ord_num}/advance-status', json={'status': 'confirmed'})
        self.client.post(f'/api/orders/{ord_num}/advance-status', json={'status': 'preparing'})
        self.client.post(f'/api/orders/{ord_num}/advance-status', json={'status': 'ready'})

        # 5. Restaurant explicitly assigns Marcus (courier_id = 1)
        marcus_courier = query_db("SELECT id FROM couriers WHERE name LIKE 'Marcus%'", one=True)
        assign_res = self.client.post(f'/api/orders/{ord_num}/assign-courier', json={'courier_id': marcus_courier['id']})
        self.assertEqual(assign_res.status_code, 200)
        self.assertTrue(assign_res.get_json()['success'])

        # 6. Log back in as Marcus: order is now in Marcus's deliveries queue with action buttons
        self.login_as("marcus@courier.demo", "password123")
        cour_res_assigned = self.client.get('/courier/deliveries')
        self.assertEqual(cour_res_assigned.status_code, 200)
        self.assertIn(ord_num.encode(), cour_res_assigned.data)
        self.assertIn(b"Accept Mission", cour_res_assigned.data)

        # 7. Marcus completes the delivery lifecycle: picked_up -> on_the_way -> delivered
        p_res = self.client.post(f'/api/orders/{ord_num}/advance-status', json={'status': 'picked_up'})
        self.assertEqual(p_res.status_code, 200)

        w_res = self.client.post(f'/api/orders/{ord_num}/advance-status', json={'status': 'on_the_way'})
        self.assertEqual(w_res.status_code, 200)

        d_res = self.client.post(f'/api/orders/{ord_num}/advance-status', json={'status': 'delivered'})
        self.assertEqual(d_res.status_code, 200)

        # Verify order in DB has final status 'delivered' and courier_id set
        final_db = query_db("SELECT * FROM orders WHERE order_number = ?", (ord_num,), one=True)
        self.assertEqual(final_db['status'], 'delivered')
        self.assertEqual(final_db['courier_id'], marcus_courier['id'])

    def test_order_creation_tracking_mark_delivered_and_history(self):
        """Verify full customer lifecycle: place order -> see in history as active -> track -> mark delivered -> see in history as delivered -> review."""
        # 1. Customer Alex logs in
        self.login_as("alex@cravecart.demo", "password123")
        alex_user = query_db("SELECT id FROM users WHERE email = 'alex@cravecart.demo'", one=True)

        # 2. Add dish to cart and place order
        item = query_db("SELECT * FROM menu_items WHERE id = 1", one=True)
        self.client.post('/api/cart/add', json={'item_id': item['id'], 'quantity': 2, 'modifiers': []})

        place_res = self.client.post('/api/checkout', json={
            'delivery_type': 'delivery',
            'payment_method': 'Visa •••• 4242',
            'tip': 4.0
        })
        self.assertEqual(place_res.status_code, 200)
        p_data = place_res.get_json()
        self.assertTrue(p_data['success'])
        ord_num = p_data['order_number']

        # 3. Verify order exists in DB with status 'placed'
        ord_db = query_db("SELECT * FROM orders WHERE order_number = ?", (ord_num,), one=True)
        self.assertIsNotNone(ord_db)
        self.assertEqual(ord_db['status'], 'placed')
        self.assertEqual(ord_db['customer_id'], alex_user['id'])

        # 4. View /orders history page -> order should be present in active deliveries
        orders_page_res = self.client.get('/orders')
        self.assertEqual(orders_page_res.status_code, 200)
        self.assertIn(ord_num.encode(), orders_page_res.data)
        self.assertIn(b"Active Deliveries", orders_page_res.data)
        self.assertIn(b"I Have Received My Order", orders_page_res.data)

        # 5. View /orders/<ord_num> tracking page
        tracking_res = self.client.get(f'/orders/{ord_num}')
        self.assertEqual(tracking_res.status_code, 200)
        self.assertIn(ord_num.encode(), tracking_res.data)
        self.assertIn(b"Food Arrived at Your Location?", tracking_res.data)

        # 6. Customer marks the order as received / delivered
        mark_res = self.client.post(f'/api/orders/{ord_num}/mark-delivered')
        self.assertEqual(mark_res.status_code, 200)
        m_data = mark_res.get_json()
        self.assertTrue(m_data['success'])
        self.assertEqual(m_data['status'], 'delivered')

        # 7. Check database: order is now 'delivered'
        updated_ord = query_db("SELECT * FROM orders WHERE order_number = ?", (ord_num,), one=True)
        self.assertEqual(updated_ord['status'], 'delivered')

        # 8. View /orders page again -> order should now be displayed under Delivered Orders History
        orders_after_res = self.client.get('/orders')
        self.assertEqual(orders_after_res.status_code, 200)
        self.assertIn(ord_num.encode(), orders_after_res.data)
        self.assertIn(b"Delivered Orders History", orders_after_res.data)
        self.assertIn(b"Order Delivered", orders_after_res.data)

        # 9. Customer submits a review on the delivered order
        rev_res = self.client.post(f'/api/orders/{ord_num}/review', json={
            'rating': 5,
            'comment': 'Delicious hot pizza delivered fast! 10/10'
        })
        self.assertEqual(rev_res.status_code, 200)
        self.assertTrue(rev_res.get_json()['success'])

        rev_db = query_db("SELECT * FROM reviews WHERE user_id = ? AND comment LIKE '%10/10%'", (alex_user['id'],), one=True)
        self.assertIsNotNone(rev_db)
        self.assertEqual(rev_db['rating'], 5)

if __name__ == '__main__':
    unittest.main()



