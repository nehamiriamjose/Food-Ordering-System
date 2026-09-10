import datetime
import json
import sqlite3
from database import get_db_connection, init_db
from werkzeug.security import generate_password_hash

def seed_database(drop_all=True):
    init_db(drop_all=drop_all)
    conn = get_db_connection()
    cur = conn.cursor()

    if drop_all:
        # Clear existing data
        tables = [
            'favorites', 'reviews', 'order_items', 'orders', 'couriers',
            'promo_codes', 'payment_methods', 'addresses', 'cart_items',
            'modifier_options', 'modifier_groups', 'menu_items',
            'menu_categories', 'cuisines', 'restaurants', 'users'
        ]
        for table in tables:
            cur.execute(f"DELETE FROM {table}")
            cur.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")

    # 1. Users
    password_hash = generate_password_hash("password123")
    users = [
        ("Alex Rivera", "alex@cravecart.demo", password_hash, "(555) 234-5678", "customer", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80", 620, "Gold VIP"),
        ("Chef Mario Rossi", "mario@emberandcrust.demo", password_hash, "(555) 345-6789", "restaurant", "https://images.unsplash.com/photo-1577219491135-ce391730fb2c?w=150&auto=format&fit=crop&q=80", 120, "Silver"),
        ("Marcus Vance", "marcus@courier.demo", password_hash, "(555) 876-5432", "courier", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80", 350, "Gold VIP"),
        ("Sarah Jenkins", "sarah@bowltheory.demo", password_hash, "(555) 456-7890", "restaurant", "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80", 80, "Bronze"),
        ("Rajesh Kumar", "rajesh@tandoorihouse.demo", password_hash, "(555) 567-8901", "restaurant", "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80", 210, "Silver")
    ]
    cur.executemany(
        "INSERT INTO users (name, email, password_hash, phone, role, avatar_url, loyalty_points, member_tier) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        users
    )

    # 2. Couriers
    couriers = [
        (3, "Marcus Vance", "(555) 876-5432", "Honda CB500X Motorcycle", "NYC-7892", 4.9, 542, 1, 40.7135, -74.0042, "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80"),
        (None, "Elena Rostova", "(555) 987-6543", "Trek Electric Cargo E-Bike", "E-774", 4.8, 389, 1, 40.7180, -73.9980, "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80"),
        (None, "David Chen", "(555) 432-1098", "Toyota Prius Hybrid", "NY-9821K", 4.9, 815, 1, 40.7250, -74.0020, "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80")
    ]
    cur.executemany(
        "INSERT INTO couriers (user_id, name, phone, vehicle_type, vehicle_plate, rating, total_trips, is_online, current_lat, current_lng, avatar_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        couriers
    )

    # 3. Cuisines
    cuisines = [
        ("Drinks & Beverages", "drinks", "🥤", "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=300&auto=format&fit=crop&q=80", 16),
        ("Pizza", "pizza", "🍕", "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=300&auto=format&fit=crop&q=80", 12),
        ("Burgers", "burgers", "🍔", "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=300&auto=format&fit=crop&q=80", 15),
        ("Sushi & Japanese", "sushi", "🍣", "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=300&auto=format&fit=crop&q=80", 8),
        ("Indian", "indian", "🍛", "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=300&auto=format&fit=crop&q=80", 9),
        ("Mexican & Tacos", "mexican", "🌮", "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=300&auto=format&fit=crop&q=80", 11),
        ("Healthy & Bowls", "healthy", "🥗", "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=300&auto=format&fit=crop&q=80", 14),
        ("Desserts & Bakery", "desserts", "🍰", "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=300&auto=format&fit=crop&q=80", 10),
        ("Asian & Noodles", "asian", "🍜", "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=300&auto=format&fit=crop&q=80", 13),
        ("Coffee & Breakfast", "coffee", "☕", "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=300&auto=format&fit=crop&q=80", 7)
    ]
    cur.executemany(
        "INSERT INTO cuisines (name, slug, icon, image_url, restaurant_count) VALUES (?, ?, ?, ?, ?)",
        cuisines
    )

    # 4. Restaurants
    restaurants_data = [
        (
            "Ember & Crust", "ember-and-crust", "Pizza", 4.8, 384, 25, 35, 2.99, 15.00, "$$",
            "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1590846406792-0adc7f938f1d?w=150&auto=format&fit=crop&q=80",
            "428 Bedford Ave, Williamsburg, NY", 1, 0, 1,
            json.dumps(["Wood-Fired", "Artisanal", "Vegetarian-Friendly", "Free Dip"]),
            "Authentic Neapolitan wood-fired sourdough pizzas crafted with 72-hour fermented dough, San Marzano tomatoes, and creamy fior di latte.",
            "(555) 234-9988", "orders@emberandcrust.demo"
        ),
        (
            "Bowl Theory", "bowl-theory", "Healthy & Bowls", 4.7, 290, 20, 30, 1.99, 12.00, "$$",
            "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=150&auto=format&fit=crop&q=80",
            "150 Greene St, SoHo, NY", 1, 0, 1,
            json.dumps(["Organic", "Gluten-Free", "Superfoods", "High Protein"]),
            "Chef-designed nourishing grain bowls, wild salmon, fresh avocado, and cold-pressed botanical dressings made from scratch daily.",
            "(555) 345-8877", "hello@bowltheory.demo"
        ),
        (
            "Tandoori House", "tandoori-house", "Indian", 4.9, 512, 30, 40, 3.49, 18.00, "$$",
            "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?w=150&auto=format&fit=crop&q=80",
            "78 1st Avenue, East Village, NY", 1, 0, 1,
            json.dumps(["Authentic", "Clay Oven", "Halal", "Family Feast"]),
            "Generations-old slow-cooked curries, charcoal tandoori meats, pillowy garlic naans, and fragrant saffron basmati biryanis.",
            "(555) 456-7766", "spices@tandoorihouse.demo"
        ),
        (
            "Seoul Bites", "seoul-bites", "Asian & Noodles", 4.6, 215, 25, 35, 2.49, 15.00, "$$",
            "https://images.unsplash.com/photo-1535140728325-a4d3707eee61?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=150&auto=format&fit=crop&q=80",
            "34 W 32nd St, Koreatown, NY", 1, 0, 1,
            json.dumps(["Double Fried", "Spicy Gochujang", "Street Food", "Bao Buns"]),
            "Crispy double-fried Korean fried chicken tossed in house garlic-soy or sweet fiery gochujang, paired with kimchi fries and fluffy bao.",
            "(555) 567-6655", "info@seoulbites.demo"
        ),
        (
            "The Green Fork", "the-green-fork", "Healthy & Bowls", 4.8, 189, 15, 25, 1.49, 10.00, "$$",
            "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=150&auto=format&fit=crop&q=80",
            "215 Flatbush Ave, Brooklyn, NY", 1, 0, 0,
            json.dumps(["Farm-to-Table", "Vegan", "Eco-Packaging", "Quick Delivery"]),
            "Locally sourced organic leafy salads, warm grain bowls, plant-based wraps, and revitalizing immunity wellness shots.",
            "(555) 678-5544", "order@thegreenfork.demo"
        ),
        (
            "Sweet District", "sweet-district", "Desserts & Bakery", 4.7, 340, 20, 30, 2.99, 12.00, "$",
            "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=150&auto=format&fit=crop&q=80",
            "89 Mulberry St, Little Italy, NY", 1, 0, 0,
            json.dumps(["Molten Center", "French Pastries", "Belgian Chocolate", "Artisan Coffee"]),
            "Decadent warm chocolate lava cakes, handcrafted French macarons, Belgian buttermilk waffles, and silky micro-roast lattes.",
            "(555) 789-4433", "treats@sweetdistrict.demo"
        ),
        (
            "Burger Craft", "burger-craft", "Burgers", 4.8, 470, 20, 30, 2.49, 14.00, "$$",
            "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1550547660-d9450f859349?w=150&auto=format&fit=crop&q=80",
            "520 8th Ave, Midtown, NY", 1, 0, 1,
            json.dumps(["Smashed Patties", "Brioche Buns", "Truffle Fries", "Craft Shakes"]),
            "100% Certified Angus prime beef smash burgers with crispy lacy edges, melted aged cheddar, secret smoky sauce on toasted brioche.",
            "(555) 890-3322", "grill@burgercraft.demo"
        ),
        (
            "Dragon Wok", "dragon-wok", "Asian & Noodles", 4.6, 310, 25, 35, 3.99, 16.00, "$$",
            "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=150&auto=format&fit=crop&q=80",
            "18 Mott St, Chinatown, NY", 1, 0, 0,
            json.dumps(["Wok Hei", "Dim Sum", "Szechuan Peppercorn", "Dumplings"]),
            "Sizzling wok-tossed noodles, crispy Peking duck, steaming soup dumplings, and fiery Szechuan chili specialties.",
            "(555) 901-2211", "service@dragonwok.demo"
        ),
        (
            "Taqueria Sol", "taqueria-sol", "Mexican & Tacos", 4.9, 425, 15, 25, 1.99, 12.00, "$",
            "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?w=150&auto=format&fit=crop&q=80",
            "312 Bleecker St, West Village, NY", 1, 0, 1,
            json.dumps(["Handmade Tortillas", "Al Pastor", "Birria Tacos", "Fresh Guac"]),
            "Authentic handmade heirloom corn tortillas filled with citrus-marinated Al Pastor, slow-braised Birria with rich consommé dip, and smashed hass avocado.",
            "(555) 012-1100", "hola@taqueriasol.demo"
        ),
        (
            "Dolce & Pasta", "dolce-and-pasta", "Italian", 4.8, 275, 30, 45, 3.99, 20.00, "$$$",
            "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1621996346565-e3d5d6281691?w=150&auto=format&fit=crop&q=80",
            "145 Spring St, SoHo, NY", 1, 0, 0,
            json.dumps(["Handmade Pasta", "Truffle Gnocchi", "Parmigiano Reggiano", "Wine Pairing"]),
            "Fresh pasta extruded daily in-house: silky tagliatelle Bolognese, wild truffle mushroom gnocchi, and authentic mascarpone tiramisu.",
            "(555) 123-0099", "ciao@dolcepasta.demo"
        )
    ]

    for rest in restaurants_data:
        cur.execute('''
            INSERT INTO restaurants (
                name, slug, cuisine, rating, review_count, delivery_time_min, delivery_time_max,
                delivery_fee, min_order, price_level, image_url, logo_url, address,
                is_open, is_busy, is_featured, tags, description, phone, email
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', rest)

    # 5. Menu Categories and Menu Items
    # Mapping of restaurants to categories and dishes
    menu_structure = [
        # Ember & Crust (Rest ID 1)
        {
            "rest_id": 1,
            "categories": [
                {
                    "name": "Popular Pizzas",
                    "items": [
                        {
                            "name": "Truffle Mushroom Pizza",
                            "desc": "Roasted cremini & wild forest mushrooms, fresh fior di latte mozzarella, aromatic white truffle oil, and thyme.",
                            "price": 16.50,
                            "image": "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Choose Size", "req": 1, "options": [("Regular 10\" (6 Slices)", 0.0, 1), ("Large 14\" (8 Slices)", 4.50, 0), ("Family 18\" (12 Slices)", 8.50, 0)]},
                                {"name": "Crust Style", "req": 1, "options": [("Neapolitan Sourdough", 0.0, 1), ("Thin & Crispy Roman", 0.0, 0), ("Cheese Stuffed Crust", 2.50, 0), ("Gluten-Free Cauliflower Crust", 3.00, 0)]},
                                {"name": "Extra Toppings", "req": 0, "max": 4, "options": [("Extra Truffle Drizzle", 1.50, 0), ("Fresh Creamy Burrata Ball", 3.50, 0), ("Caramelized Balsamic Onions", 1.25, 0), ("Prosciutto di Parma", 3.00, 0)]}
                            ]
                        },
                        {
                            "name": "Margherita D.O.P.",
                            "desc": "San Marzano tomato sauce, fresh buffalo mozzarella, hand-torn sweet basil, and extra virgin olive oil.",
                            "price": 14.50,
                            "image": "https://images.unsplash.com/photo-1604382355076-af4b0eb60143?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Choose Size", "req": 1, "options": [("Regular 10\"", 0.0, 1), ("Large 14\"", 4.00, 0)]},
                                {"name": "Add Extra Cheese", "req": 0, "options": [("Double Buffalo Mozzarella", 2.50, 0), ("Aged Parmesan Flakes", 1.50, 0)]}
                            ]
                        },
                        {
                            "name": "Spicy Diavola & Hot Honey",
                            "desc": "Calabrian spicy soppressata, smoked provolone, chili-infused organic wildflower hot honey drizzle.",
                            "price": 17.50,
                            "image": "https://images.unsplash.com/photo-1534308983496-4fabb1a015ee?w=500&auto=format&fit=crop&q=80",
                            "is_spicy": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Choose Size", "req": 1, "options": [("Regular 10\"", 0.0, 1), ("Large 14\"", 4.50, 0)]},
                                {"name": "Heat Level", "req": 1, "options": [("Mild Kick", 0.0, 0), ("Traditional Hot", 0.0, 1), ("Extra Fiery Calabrian Pepper", 1.0, 0)]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Starters & Dips",
                    "items": [
                        {
                            "name": "Crispy Truffle Polenta Bites",
                            "desc": "Golden crusted polenta cakes dusted with parmesan, served with roasted garlic aioli.",
                            "price": 8.50,
                            "image": "https://images.unsplash.com/photo-1541529086526-db283c563270?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 0,
                            "modifiers": []
                        },
                        {
                            "name": "Burrata Caprese Board",
                            "desc": "Heirloom cherry tomatoes, aged balsamic reduction, basil pesto, warm wood-fired focaccia.",
                            "price": 12.95,
                            "image": "https://images.unsplash.com/photo-1592417817098-8f3d6910985b?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 0,
                            "modifiers": []
                        }
                    ]
                },
                {
                    "name": "Artisan Drinks & Refreshers",
                    "items": [
                        {
                            "name": "Sparkling Lemon Basil Spritz",
                            "desc": "Freshly squeezed Meyer lemon juice, sparkling mineral water, muddled organic sweet basil, and a dash of raw agave.",
                            "price": 4.95,
                            "image": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Sweetness Level", "req": 1, "options": [("Normal Sweetness", 0.0, 1), ("Less Sweet (50%)", 0.0, 0), ("Unsweetened", 0.0, 0)]},
                                {"name": "Ice Level", "req": 1, "options": [("Regular Ice", 0.0, 1), ("Less Ice", 0.0, 0), ("No Ice", 0.0, 0)]}
                            ]
                        },
                        {
                            "name": "San Pellegrino Blood Orange",
                            "desc": "Crisp sparkling Italian citrus soda (330ml can).",
                            "price": 3.50,
                            "image": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 0,
                            "modifiers": []
                        },
                        {
                            "name": "Iced Espresso Tonic",
                            "desc": "Double shot of single-origin espresso poured over premium tonic water with fresh orange twist.",
                            "price": 5.25,
                            "image": "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                }
            ]
        },
        # Bowl Theory (Rest ID 2)
        {
            "rest_id": 2,
            "categories": [
                {
                    "name": "Signature Grain Bowls",
                    "items": [
                        {
                            "name": "Miso Salmon Bowl",
                            "desc": "Pan-seared wild salmon, warm jasmine brown rice, organic edamame, shaved cucumber, pickled ginger, and sweet miso glaze.",
                            "price": 18.75,
                            "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop&q=80",
                            "is_gf": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Base Selection", "req": 1, "options": [("Jasmine Brown Rice", 0.0, 1), ("Tri-Color Quinoa", 1.0, 0), ("Cauliflower Rice", 1.50, 0), ("Organic Mixed Greens", 0.0, 0)]},
                                {"name": "Dressing", "req": 1, "options": [("Sweet Miso Glaze", 0.0, 1), ("Spicy Ginger Ponzu", 0.0, 0), ("Tahini Goddess", 0.0, 0)]},
                                {"name": "Boosters", "req": 0, "options": [("Extra Avocado Half", 2.00, 0), ("Soft Boiled Onsen Egg", 1.50, 0), ("Double Salmon Portion", 5.50, 0)]}
                            ]
                        },
                        {
                            "name": "Avocado Crunch Power Bowl",
                            "desc": "Hass avocado, roasted sweet potatoes, charred broccoli, baby kale, toasted pumpkin seeds, green goddess dressing.",
                            "price": 14.50,
                            "image": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500&auto=format&fit=crop&q=80",
                            "is_vegan": 1, "is_gf": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Add Plant Protein", "req": 0, "options": [("Organic Crispy Tofu", 3.00, 0), ("Grilled Herb Chicken", 4.50, 0)]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Cold Pressed Juices",
                    "items": [
                        {
                            "name": "Green Glow Juice",
                            "desc": "Kale, green apple, cucumber, celery, lemon, and fresh ginger.",
                            "price": 6.95,
                            "image": "https://images.unsplash.com/photo-1613478223719-2ab802602423?w=500&auto=format&fit=crop&q=80",
                            "is_vegan": 1, "is_gf": 1, "is_pop": 0,
                            "modifiers": []
                        }
                    ]
                }
            ]
        },
        # Tandoori House (Rest ID 3)
        {
            "rest_id": 3,
            "categories": [
                {
                    "name": "Clay Oven & Wraps",
                    "items": [
                        {
                            "name": "Paneer Tikka Wrap",
                            "desc": "Grilled cottage cheese cubes marinated in yogurt & aromatics, bell peppers, mint chutney in freshly rolled flatbread.",
                            "price": 12.50,
                            "image": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Spice Level", "req": 1, "options": [("Mild & Creamy", 0.0, 0), ("Medium Masala", 0.0, 1), ("Desi Hot Spice", 0.0, 0)]},
                                {"name": "Bread Selection", "req": 1, "options": [("Butter Naan Wrap", 0.0, 1), ("Garlic Naan Wrap", 1.0, 0), ("Whole Wheat Roti", 0.0, 0)]},
                                {"name": "Add Side", "req": 0, "options": [("Masala Spiced Fries", 3.50, 0), ("Cucumber Raita Cup", 1.95, 0)]}
                            ]
                        },
                        {
                            "name": "Butter Chicken Deluxe (Murgh Makhani)",
                            "desc": "Tender tandoor-roasted chicken in a rich, velvety tomato butter and fenugreek cream gravy.",
                            "price": 17.95,
                            "image": "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?w=500&auto=format&fit=crop&q=80",
                            "is_pop": 1,
                            "modifiers": [
                                {"name": "Includes Rice/Bread", "req": 1, "options": [("Saffron Basmati Rice", 0.0, 1), ("Garlic Butter Naan", 1.0, 0), ("Both Rice & Naan", 2.50, 0)]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Breads & Biryanis",
                    "items": [
                        {
                            "name": "Dum Hyderabadi Biryani",
                            "desc": "Fragrant aged basmati rice layered with spiced meat, saffron, caramelized onions and served with mirchi ka salan & raita.",
                            "price": 16.50,
                            "image": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=500&auto=format&fit=crop&q=80",
                            "is_spicy": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Choice of Protein", "req": 1, "options": [("Tender Chicken", 0.0, 1), ("Slow Cooked Lamb (+ $2.50)", 2.50, 0), ("Vegetable & Paneer", 0.0, 0)]}
                            ]
                        },
                        {
                            "name": "Garlic Coriander Naan",
                            "desc": "Tandoor baked flatbread brushed with crushed garlic, cilantro and pure ghee.",
                            "price": 3.75,
                            "image": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                },
                {
                    "name": "Traditional Drinks & Lassi",
                    "items": [
                        {
                            "name": "Royal Saffron Mango Lassi",
                            "desc": "Thick creamy yogurt blended with Alphonso mango pulp, saffron strands, green cardamom, and crushed pistachios.",
                            "price": 5.50,
                            "image": "https://images.unsplash.com/photo-1546173159-315724a31696?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Sweetness Level", "req": 1, "options": [("Normal Sweet", 0.0, 1), ("Less Sweet", 0.0, 0)]},
                                {"name": "Garnish", "req": 0, "options": [("Extra Pistachio & Almond Flakes", 0.75, 0), ("Rose Syrup Drizzle", 0.50, 0)]}
                            ]
                        },
                        {
                            "name": "Masala Chai (Clay Pot)",
                            "desc": "Freshly brewed Assam CTC black tea with crushed ginger, whole green cardamom, cinnamon, and whole milk.",
                            "price": 3.95,
                            "image": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                }
            ]
        },
        # Seoul Bites (Rest ID 4)
        {
            "rest_id": 4,
            "categories": [
                {
                    "name": "Korean Fried Chicken",
                    "items": [
                        {
                            "name": "Gochujang Crispy Wings (8 Pcs)",
                            "desc": "Double fried ultra-crunchy chicken wings glazed in sweet & spicy gochujang chili sauce, sesame seeds, pickled radish.",
                            "price": 15.95,
                            "image": "https://images.unsplash.com/photo-1527477321007-e75bf854807c?w=500&auto=format&fit=crop&q=80",
                            "is_spicy": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Glaze Flavor", "req": 1, "options": [("Sweet Gochujang Chili", 0.0, 1), ("Soy Garlic Ginger", 0.0, 0), ("Honey Butter Snow", 0.50, 0), ("Half & Half", 1.00, 0)]},
                                {"name": "Side Dip", "req": 0, "options": [("Kimchi Ranch Dip", 1.25, 0), ("Extra Pickled Daikon Radish", 1.00, 0)]}
                            ]
                        },
                        {
                            "name": "Bulgogi Beef Bao Buns (3 Pcs)",
                            "desc": "Steamed lotus buns stuffed with sweet soy-marinated beef ribeye, scallion salad, and spicy mayo.",
                            "price": 13.50,
                            "image": "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=500&auto=format&fit=crop&q=80",
                            "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                },
                {
                    "name": "Boba, Teas & Coolers",
                    "items": [
                        {
                            "name": "Brown Sugar Boba Milk",
                            "desc": "Slow-cooked warm brown sugar tapioca pearls, fresh whole milk, and house caramelized tiger stripe drizzle.",
                            "price": 6.25,
                            "image": "https://images.unsplash.com/photo-1558857563-b371b5636034?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Sweetness Level", "req": 1, "options": [("100% Regular Sweet", 0.0, 1), ("70% Less Sweet", 0.0, 0), ("30% Mild Sweet", 0.0, 0)]},
                                {"name": "Ice Level", "req": 1, "options": [("Regular Ice", 0.0, 1), ("Less Ice", 0.0, 0), ("No Ice", 0.0, 0)]},
                                {"name": "Toppings", "req": 0, "options": [("Extra Boba Pearls", 0.75, 0), ("Cheese Foam Cap", 1.25, 0), ("Grass Jelly", 0.75, 0)]}
                            ]
                        },
                        {
                            "name": "Sparkling Yuzu Citron Soda",
                            "desc": "Korean honey yuzu marmalade shaken with sparkling soda water, fresh mint sprig, and lemon slice.",
                            "price": 4.95,
                            "image": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                }
            ]
        },
        # The Green Fork (Rest ID 5)
        {
            "rest_id": 5,
            "categories": [
                {
                    "name": "Signature Salads & Wraps",
                    "items": [
                        {
                            "name": "Superfood Kale Caesar",
                            "desc": "Baby kale, shredded romaine, crispy chickpeas croutons, shaved parmesan, hemp seeds, creamy vegan cashew caesar dressing.",
                            "price": 13.95,
                            "image": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Add Protein", "req": 0, "options": [("Grilled Lemon Herb Chicken", 4.50, 0), ("Smoked Organic Tofu", 3.00, 0), ("Wild Salmon Fillet", 6.00, 0)]}
                            ]
                        },
                        {
                            "name": "Rainbow Falafel Wrap",
                            "desc": "Housemade crunchy herb falafel, beetroot hummus, cucumber, pickled cabbage, tahini sauce in spinach tortilla.",
                            "price": 11.95,
                            "image": "https://images.unsplash.com/photo-1529042410759-befb1204b468?w=500&auto=format&fit=crop&q=80",
                            "is_vegan": 1, "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                }
            ]
        },
        # Sweet District (Rest ID 6)
        {
            "rest_id": 6,
            "categories": [
                {
                    "name": "Warm Molten Cakes & Waffles",
                    "items": [
                        {
                            "name": "Chocolate Lava Cake",
                            "desc": "Warm dark Valrhona chocolate cake with an oozing molten center, served with Madagascan vanilla bean ice cream.",
                            "price": 7.25,
                            "image": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Ice Cream Flavor", "req": 1, "options": [("Madagascan Vanilla Bean", 0.0, 1), ("Salted Butter Caramel", 1.0, 0), ("Sicilian Pistachio", 1.50, 0)]},
                                {"name": "Toppings", "req": 0, "options": [("Warm Nutella Drizzle", 1.25, 0), ("Fresh Raspberries & Strawberries", 1.75, 0)]}
                            ]
                        },
                        {
                            "name": "Belgian Liege Pearl Sugar Waffle",
                            "desc": "Caramelized pearl sugar brioche waffle topped with sliced banana, strawberries, and Belgian chocolate drizzle.",
                            "price": 8.95,
                            "image": "https://images.unsplash.com/photo-1562376552-0d160a2f238d?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                }
            ]
        },
        # Burger Craft (Rest ID 7)
        {
            "rest_id": 7,
            "categories": [
                {
                    "name": "Craft Burgers",
                    "items": [
                        {
                            "name": "Crispy Chicken Burger",
                            "desc": "Golden buttermilk fried chicken thigh, creamy purple cabbage slaw, dill pickles, and house secret sauce on toasted brioche.",
                            "price": 13.95,
                            "image": "https://images.unsplash.com/photo-1625813506062-0aeb1d7a094b?w=500&auto=format&fit=crop&q=80",
                            "is_pop": 1,
                            "modifiers": [
                                {"name": "Spice Level", "req": 1, "options": [("Original Classic", 0.0, 1), ("Nashville Hot & Spicy", 0.0, 0), ("Inferno Reaper Hot", 1.0, 0)]},
                                {"name": "Cheese Options", "req": 0, "options": [("Aged Yellow Cheddar", 1.0, 0), ("Smoked Gouda", 1.50, 0)]},
                                {"name": "Add Extras", "req": 0, "options": [("Applewood Smoked Bacon", 2.00, 0), ("Fried Sunny Side Egg", 1.50, 0), ("Avocado Slices", 1.75, 0)]}
                            ]
                        },
                        {
                            "name": "The Double Smashed Truffle Burger",
                            "desc": "Two 100% Angus smash patties, Swiss gruyere cheese, sautéed balsamic onions, truffle mayo on glossy brioche.",
                            "price": 15.50,
                            "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500&auto=format&fit=crop&q=80",
                            "is_pop": 1,
                            "modifiers": [
                                {"name": "Patty Count", "req": 1, "options": [("Double Patty (Standard)", 0.0, 1), ("Triple Patty (+ $3.00)", 3.00, 0)]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Sides & Loaded Fries",
                    "items": [
                        {
                            "name": "Parmesan Truffle Fries",
                            "desc": "Crispy hand-cut russet fries tossed in white truffle oil, rosemary sea salt, and microplaned aged parmesan.",
                            "price": 6.95,
                            "image": "https://images.unsplash.com/photo-1576107232684-1279f3908594?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                }
            ]
        },
        # Dragon Wok (Rest ID 8)
        {
            "rest_id": 8,
            "categories": [
                {
                    "name": "Wok Specials & Dumplings",
                    "items": [
                        {
                            "name": "Shanghai Steamed Soup Dumplings (6 Pcs)",
                            "desc": "Delicate handmade soup dumplings filled with seasoned pork and piping hot rich broth, served with black vinegar and ginger.",
                            "price": 11.50,
                            "image": "https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?w=500&auto=format&fit=crop&q=80",
                            "is_pop": 1,
                            "modifiers": []
                        },
                        {
                            "name": "Dan Dan Szechuan Noodles",
                            "desc": "Springy wheat noodles in spicy chili-sesame broth, minced pork, crushed peanuts, bok choy, and fragrant chili crisp.",
                            "price": 14.50,
                            "image": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=500&auto=format&fit=crop&q=80",
                            "is_spicy": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Heat Level", "req": 1, "options": [("Mild Numbing", 0.0, 0), ("Standard Szechuan Fire", 0.0, 1), ("Extreme Ghost Chili", 1.0, 0)]}
                            ]
                        }
                    ]
                }
            ]
        },
        # Taqueria Sol (Rest ID 9)
        {
            "rest_id": 9,
            "categories": [
                {
                    "name": "Street Tacos & Quesadillas",
                    "items": [
                        {
                            "name": "Birria Quesatacos (3 Tacos)",
                            "desc": "Slow-braised beef birria folded into corn tortillas with melted Oaxaca cheese, cilantro, onions, and rich dipping consommé.",
                            "price": 14.95,
                            "image": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=500&auto=format&fit=crop&q=80",
                            "is_pop": 1,
                            "modifiers": [
                                {"name": "Tortilla Choice", "req": 1, "options": [("Crispy Corn (Authentic)", 0.0, 1), ("Soft Flour Tortillas", 0.0, 0)]},
                                {"name": "Add-ons", "req": 0, "options": [("Extra Consommé Cup", 2.00, 0), ("Fresh Smashed Guacamole", 2.50, 0)]}
                            ]
                        },
                        {
                            "name": "Al Pastor Street Tacos (3 Tacos)",
                            "desc": "Spit-roasted pork marinated in achiote & citrus, topped with charred pineapple chunks, cilantro, and roasted salsa verde.",
                            "price": 12.50,
                            "image": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?w=500&auto=format&fit=crop&q=80",
                            "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                }
            ]
        },
        # Dolce & Pasta (Rest ID 10)
        {
            "rest_id": 10,
            "categories": [
                {
                    "name": "Handcrafted Pastas",
                    "items": [
                        {
                            "name": "Wild Truffle & Mushroom Gnocchi",
                            "desc": "Pillowy potato gnocchi tossed in brown butter truffle cream sauce, roasted chanterelles, and 24-month Parmigiano Reggiano.",
                            "price": 19.50,
                            "image": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=500&auto=format&fit=crop&q=80",
                            "is_veg": 1, "is_pop": 1,
                            "modifiers": [
                                {"name": "Extra Topping", "req": 0, "options": [("Fresh Shaved Truffle", 4.00, 0), ("Crispy Pancetta Bits", 2.50, 0)]}
                            ]
                        },
                        {
                            "name": "Tagliatelle al Ragu Bolognese",
                            "desc": "Hand-rolled egg ribbon pasta coated with slow-simmered beef, veal, and pancetta ragu with a splash of Chianti.",
                            "price": 18.50,
                            "image": "https://images.unsplash.com/photo-1621996346565-e3d5d6281691?w=500&auto=format&fit=crop&q=80",
                            "is_pop": 1,
                            "modifiers": []
                        }
                    ]
                }
            ]
        }
    ]

    for menu in menu_structure:
        rest_id = menu["rest_id"]
        for cat_idx, cat in enumerate(menu["categories"]):
            cur.execute("INSERT INTO menu_categories (restaurant_id, name, sort_order) VALUES (?, ?, ?)", (rest_id, cat["name"], cat_idx))
            cat_id = cur.lastrowid
            for item in cat["items"]:
                cur.execute('''
                    INSERT INTO menu_items (
                        category_id, restaurant_id, name, description, price, image_url,
                        is_vegetarian, is_vegan, is_gluten_free, is_spicy, is_popular, is_available
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    cat_id, rest_id, item["name"], item["desc"], item["price"], item["image"],
                    item.get("is_veg", 0), item.get("is_vegan", 0), item.get("is_gf", 0),
                    item.get("is_spicy", 0), item.get("is_pop", 0)
                ))
                item_id = cur.lastrowid

                # Modifiers
                for mod_grp in item.get("modifiers", []):
                    cur.execute('''
                        INSERT INTO modifier_groups (menu_item_id, name, min_selection, max_selection, is_required)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (item_id, mod_grp["name"], 1 if mod_grp.get("req", 0) else 0, mod_grp.get("max", 1), mod_grp.get("req", 0)))
                    grp_id = cur.lastrowid
                    for opt_name, price_delta, is_def in mod_grp["options"]:
                        cur.execute('''
                            INSERT INTO modifier_options (modifier_group_id, name, price_delta, is_default)
                            VALUES (?, ?, ?, ?)
                        ''', (grp_id, opt_name, price_delta, is_def))

    # 6. Promo Codes
    now_dt = datetime.datetime.now()
    promos = [
        ("WELCOME50", "percent", 50.0, 20.0, 15.0, "50% off on your first order up to $15", (now_dt + datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')),
        ("CRAVE20", "percent", 20.0, 25.0, 10.0, "20% off all orders over $25", (now_dt + datetime.timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')),
        ("FREESHIP", "fixed", 4.0, 15.0, 4.0, "Free delivery on gourmet favorites over $15", (now_dt + datetime.timedelta(days=1, hours=12)).strftime('%Y-%m-%d %H:%M:%S')),
        ("TASTY10", "fixed", 10.0, 35.0, 10.0, "$10 off on feast orders above $35", (now_dt + datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')),
        ("FEAST15", "percent", 15.0, 30.0, 12.0, "15% off weekend family meals over $30", (now_dt + datetime.timedelta(days=2, hours=6)).strftime('%Y-%m-%d %H:%M:%S')),
        ("CHEER5", "fixed", 5.0, 20.0, 5.0, "$5 instant discount for loyal craving members", (now_dt + datetime.timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'))
    ]
    cur.executemany(
        "INSERT INTO promo_codes (code, discount_type, discount_value, min_spend, max_discount, description, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        promos
    )

    # 7. Customer Addresses & Payment Methods
    cur.execute('''
        INSERT INTO addresses (user_id, label, street, apartment, city, state, zip_code, instructions, is_default)
        VALUES (1, 'Home', '742 Evergreen Terrace', 'Apt 4B', 'New York', 'NY', '10001', 'Ring bell #4B, leave on delivery bench by elevator', 1),
               (1, 'Work', '100 Innovation Way', 'Suite 800', 'New York', 'NY', '10010', 'Leave at reception desk with security badge verification', 0)
    ''')

    cur.execute('''
        INSERT INTO payment_methods (user_id, type, card_brand, last4, exp_month, exp_year, upi_id, bank_name, is_default)
        VALUES (1, 'card', 'Visa', '4242', '12', '2028', NULL, NULL, 1),
               (1, 'card', 'Mastercard', '8899', '08', '2027', NULL, NULL, 0),
               (1, 'upi', 'UPI', NULL, NULL, NULL, 'alex@okaxis', 'Google Pay', 0),
               (1, 'upi', 'UPI', NULL, NULL, NULL, 'alex.rivera@paytm', 'Paytm UPI', 0),
               (1, 'netbanking', 'NetBanking', NULL, NULL, NULL, NULL, 'HDFC Bank', 0),
               (1, 'wallet', 'ApplePay', NULL, NULL, NULL, NULL, 'Apple Pay', 0)
    ''')

    # 8. Sample Active & Past Orders
    # Active live order
    active_address = {
        "label": "Home",
        "street": "742 Evergreen Terrace, Apt 4B",
        "city": "New York",
        "zip_code": "10001"
    }
    cur.execute('''
        INSERT INTO orders (
            order_number, customer_id, restaurant_id, courier_id, status, subtotal,
            delivery_fee, service_fee, tax, tip, discount, total, promo_code,
            delivery_address_json, delivery_instructions, payment_method, delivery_type,
            estimated_delivery_time, courier_lat, courier_lng, created_at
        ) VALUES (
            'ORD-78901', 1, 1, 1, 'on_the_way', 31.00,
            2.99, 2.50, 2.75, 4.00, 10.00, 33.24, 'WELCOME50',
            ?, 'Please ring bell #4B and leave at door', 'Visa •••• 4242', 'delivery',
            '18 mins (8:45 PM)', 40.7135, -74.0042, datetime('now', '-15 minutes')
        )
    ''', (json.dumps(active_address),))
    order_id_1 = cur.lastrowid

    cur.execute('''
        INSERT INTO order_items (order_id, menu_item_id, name, unit_price, quantity, modifiers_summary, total_price)
        VALUES (?, 1, 'Truffle Mushroom Pizza', 16.50, 1, 'Large 14\" (+ $4.50), Neapolitan Sourdough, Extra Truffle Drizzle (+ $1.50)', 22.50),
               (?, 5, 'Crispy Truffle Polenta Bites', 8.50, 1, 'Standard portion', 8.50)
    ''', (order_id_1, order_id_1))

    # Past Completed Orders
    cur.execute('''
        INSERT INTO orders (
            order_number, customer_id, restaurant_id, courier_id, status, subtotal,
            delivery_fee, service_fee, tax, tip, discount, total, promo_code,
            delivery_address_json, delivery_instructions, payment_method, delivery_type,
            estimated_delivery_time, courier_lat, courier_lng, created_at
        ) VALUES (
            'ORD-65421', 1, 2, 2, 'delivered', 25.70,
            1.99, 2.00, 2.30, 3.00, 0.00, 34.99, '',
            ?, 'Leave with doorman', 'Apple Pay', 'delivery',
            'Delivered', 40.7180, -73.9980, datetime('now', '-2 days')
        )
    ''', (json.dumps(active_address),))
    order_id_2 = cur.lastrowid

    cur.execute('''
        INSERT INTO order_items (order_id, menu_item_id, name, unit_price, quantity, modifiers_summary, total_price)
        VALUES (?, 8, 'Miso Salmon Bowl', 18.75, 1, 'Tri-Color Quinoa (+ $1.00), Sweet Miso Glaze', 19.75),
               (?, 10, 'Green Glow Juice', 6.95, 1, 'Cold pressed 12oz', 6.95)
    ''', (order_id_2, order_id_2))

    # Another past order from Tandoori House
    cur.execute('''
        INSERT INTO orders (
            order_number, customer_id, restaurant_id, courier_id, status, subtotal,
            delivery_fee, service_fee, tax, tip, discount, total, promo_code,
            delivery_address_json, delivery_instructions, payment_method, delivery_type,
            estimated_delivery_time, courier_lat, courier_lng, created_at
        ) VALUES (
            'ORD-54312', 1, 3, 3, 'delivered', 34.45,
            3.49, 2.50, 3.10, 5.00, 5.00, 43.54, 'CHEER5',
            ?, 'Hand to me', 'Visa •••• 4242', 'delivery',
            'Delivered', 40.7250, -74.0020, datetime('now', '-5 days')
        )
    ''', (json.dumps(active_address),))
    order_id_3 = cur.lastrowid

    cur.execute('''
        INSERT INTO order_items (order_id, menu_item_id, name, unit_price, quantity, modifiers_summary, total_price)
        VALUES (?, 11, 'Paneer Tikka Wrap', 12.50, 1, 'Garlic Naan Wrap (+ $1.00), Medium Masala', 13.50),
               (?, 12, 'Butter Chicken Deluxe', 17.95, 1, 'Both Rice & Naan (+ $2.50)', 20.45)
    ''', (order_id_3, order_id_3))

    # 9. Favorites
    cur.execute('''
        INSERT INTO favorites (user_id, restaurant_id, menu_item_id)
        VALUES (1, 1, NULL),
               (1, 2, NULL),
               (1, 7, NULL),
               (1, NULL, 1),
               (1, NULL, 8)
    ''')

    # 10. Reviews
    reviews_data = [
        (1, 1, 5, "Best artisanal pizza in the city! The crust had amazing leopard spotting and the truffle aroma was intoxicating.", "Alex Rivera"),
        (1, 2, 5, "Super fresh ingredients and delivered scorching hot in under 25 minutes. 10/10!", "Jessica Meyer"),
        (2, 1, 5, "The miso salmon bowl is my weekly holy grail. So healthy yet packed with umami flavor.", "Alex Rivera"),
        (3, 1, 5, "Authentic clay oven flavor and the butter chicken sauce is rich and heavenly.", "David Thorne"),
        (7, 2, 5, "The smashed patties have the crispiest lacy edges. The truffle fries are unmatched.", "Michael Scott")
    ]
    cur.executemany(
        "INSERT INTO reviews (restaurant_id, user_id, rating, comment, user_name) VALUES (?, ?, ?, ?, ?)",
        reviews_data
    )

    conn.commit()
    conn.close()
    print("CraveCart database successfully seeded with realistic restaurants, dishes, modifiers, promos, orders & accounts!")

def seed_if_empty():
    init_db(drop_all=False)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM restaurants")
    count = cur.fetchone()[0]
    conn.close()
    if count == 0:
        seed_database(drop_all=False)

if __name__ == "__main__":
    seed_database()
