from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = 'green-parking-secret-key'

# Database file
DATABASE = 'green_parking.db'

# Initialize database with all tables
def init_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Users table with green features
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            carbon_saved REAL DEFAULT 0,
            green_points INTEGER DEFAULT 0,
            badges TEXT DEFAULT ''
        )
    ''')
    
    # Parking lots with eco features
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parking_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            pincode TEXT NOT NULL,
            price REAL NOT NULL,
            max_spots INTEGER NOT NULL,
            eco_rating INTEGER DEFAULT 3,
            has_solar INTEGER DEFAULT 0,
            has_ev_charging INTEGER DEFAULT 0,
            has_recycling INTEGER DEFAULT 0,
            has_bike_spots INTEGER DEFAULT 0
        )
    ''')
    
    # Parking spots with types
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parking_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            status TEXT DEFAULT 'A',
            spot_type TEXT DEFAULT 'car',
            FOREIGN KEY (lot_id) REFERENCES parking_lots (id)
        )
    ''')
    
    # Reservations with green tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            parking_timestamp DATETIME,
            leaving_timestamp DATETIME,
            cost REAL,
            carbon_saved REAL DEFAULT 0,
            green_points_earned INTEGER DEFAULT 0,
            FOREIGN KEY (spot_id) REFERENCES parking_spots (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Eco tips table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eco_tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tip_text TEXT NOT NULL,
            category TEXT NOT NULL
        )
    ''')
    
    # Create admin user
    cursor.execute('SELECT * FROM users WHERE username = "admin"')
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, email) 
            VALUES ("admin", "admin123", "admin@greenparking.com")
        ''')
    
    # Add sample eco tips
    cursor.execute('SELECT COUNT(*) FROM eco_tips')
    if cursor.fetchone()[0] == 0:
        tips = [
            ("Turn off your engine while waiting to reduce emissions!", "driving"),
            ("Consider carpooling to earn bonus green points!", "social"),
            ("Use bike parking when possible - it's carbon-free!", "transport"),
            ("Choose parking lots with solar panels for clean energy!", "energy"),
            ("Recycle your waste in eco-friendly parking lots!", "waste"),
            ("Park closer to your destination to reduce walking impact!", "efficiency")
        ]
        cursor.executemany('INSERT INTO eco_tips (tip_text, category) VALUES (?, ?)', tips)
    
    conn.commit()
    conn.close()

# Get random eco tip
def get_random_eco_tip():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT tip_text FROM eco_tips ORDER BY RANDOM() LIMIT 1')
    tip = cursor.fetchone()
    conn.close()
    return tip[0] if tip else "Be eco-friendly today!"

# Calculate carbon savings (simple calculation)
def calculate_carbon_savings(parking_duration_hours, lot_eco_rating):
    # Base carbon saved: 0.5kg per hour of efficient parking
    # Bonus for eco-friendly lots
    base_savings = parking_duration_hours * 0.5
    eco_bonus = (lot_eco_rating - 3) * 0.2  # Extra savings for 4-5 star lots
    return round(base_savings + eco_bonus, 2)

# Calculate green points
def calculate_green_points(parking_duration_hours, spot_type, lot_eco_rating):
    base_points = int(parking_duration_hours * 10)
    
    # Bonus for bike parking
    if spot_type == 'bike':
        base_points += 50
    elif spot_type == 'ev':
        base_points += 30
    
    # Bonus for eco-friendly lots
    base_points += (lot_eco_rating - 3) * 10
    
    return base_points

# Check and award badges
def check_badges(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT carbon_saved, green_points FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        conn.close()
        return
    
    carbon_saved, green_points = user_data
    badges = []
    
    # Carbon-based badges
    if carbon_saved >= 100:
        badges.append("Carbon Champion")
    elif carbon_saved >= 50:
        badges.append("Eco Warrior")
    elif carbon_saved >= 10:
        badges.append("Green Starter")
    
    # Points-based badges
    if green_points >= 1000:
        badges.append("Green Master")
    elif green_points >= 500:
        badges.append("Eco Expert")
    
    badge_string = ",".join(badges)
    cursor.execute('UPDATE users SET badges = ? WHERE id = ?', (badge_string, user_id))
    conn.commit()
    conn.close()

# Home page
@app.route('/')
def home():
    return redirect('/login')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = (username == 'admin')
            
            if username == 'admin':
                return redirect('/admin')
            else:
                return redirect('/user')
        else:
            flash('Invalid username or password!')
    
    return render_template('login.html')

# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (username, password, email) 
                VALUES (?, ?, ?)
            ''', (username, password, email))
            conn.commit()
            flash('Registration successful! Please login.')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('Username already exists!')
        finally:
            conn.close()
    
    return render_template('register.html')

# Admin Dashboard
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get all parking lots
    cursor.execute('SELECT * FROM parking_lots')
    lots = cursor.fetchall()
    
    # Get all users except admin
    cursor.execute('SELECT * FROM users WHERE username != "admin"')
    users = cursor.fetchall()
    
    # Get parking statistics
    cursor.execute('SELECT COUNT(*) FROM parking_spots WHERE status = "O"')
    occupied_spots = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM parking_spots WHERE status = "A"')
    available_spots = cursor.fetchone()[0]
    
    # Get total carbon saved by all users
    cursor.execute('SELECT SUM(carbon_saved) FROM users')
    total_carbon = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         lots=lots, 
                         users=users, 
                         occupied_spots=occupied_spots,
                         available_spots=available_spots,
                         total_carbon=total_carbon)

# Add parking lot (Admin)
@app.route('/add_lot', methods=['GET', 'POST'])
def add_lot():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect('/login')
    
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pincode = request.form['pincode']
        price = float(request.form['price'])
        max_spots = int(request.form['max_spots'])
        eco_rating = int(request.form['eco_rating'])
        has_solar = 1 if 'has_solar' in request.form else 0
        has_ev_charging = 1 if 'has_ev_charging' in request.form else 0
        has_recycling = 1 if 'has_recycling' in request.form else 0
        has_bike_spots = 1 if 'has_bike_spots' in request.form else 0
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Insert parking lot
        cursor.execute('''
            INSERT INTO parking_lots 
            (name, address, pincode, price, max_spots, eco_rating, 
             has_solar, has_ev_charging, has_recycling, has_bike_spots)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, address, pincode, price, max_spots, eco_rating,
              has_solar, has_ev_charging, has_recycling, has_bike_spots))
        
        lot_id = cursor.lastrowid
        
        # Auto-create parking spots
        car_spots = max_spots - (10 if has_bike_spots else 0)  # Reserve 10 for bikes if enabled
        
        # Create car spots
        for i in range(car_spots):
            cursor.execute('INSERT INTO parking_spots (lot_id, spot_type) VALUES (?, "car")', (lot_id,))
        
        # Create bike spots if enabled
        if has_bike_spots:
            for i in range(10):
                cursor.execute('INSERT INTO parking_spots (lot_id, spot_type) VALUES (?, "bike")', (lot_id,))
        
        conn.commit()
        conn.close()
        
        flash('Parking lot added successfully!')
        return redirect('/admin')
    
    return render_template('add_lot.html')

# Delete parking lot (Admin)
@app.route('/delete_lot/<int:lot_id>')
def delete_lot(lot_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if all spots are empty
    cursor.execute('SELECT COUNT(*) FROM parking_spots WHERE lot_id = ? AND status = "O"', (lot_id,))
    occupied_count = cursor.fetchone()[0]
    
    if occupied_count > 0:
        flash('Cannot delete parking lot with occupied spots!')
    else:
        # Delete spots first, then lot
        cursor.execute('DELETE FROM parking_spots WHERE lot_id = ?', (lot_id,))
        cursor.execute('DELETE FROM parking_lots WHERE id = ?', (lot_id,))
        conn.commit()
        flash('Parking lot deleted successfully!')
    
    conn.close()
    return redirect('/admin')

# User Dashboard
@app.route('/user')
def user_dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get user's green stats
    cursor.execute('SELECT carbon_saved, green_points, badges FROM users WHERE id = ?', (session['user_id'],))
    user_stats = cursor.fetchone()
    
    # Get available parking lots
    cursor.execute('''
        SELECT pl.*, COUNT(ps.id) as available_spots
        FROM parking_lots pl
        LEFT JOIN parking_spots ps ON pl.id = ps.lot_id AND ps.status = 'A'
        GROUP BY pl.id
    ''')
    lots = cursor.fetchall()
    
    # Get user's current reservations
    cursor.execute('''
        SELECT r.*, pl.name, ps.spot_type
        FROM reservations r
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.user_id = ? AND r.leaving_timestamp IS NULL
    ''', (session['user_id'],))
    current_reservations = cursor.fetchall()
    
    # Get user's parking history
    cursor.execute('''
        SELECT r.*, pl.name, ps.spot_type
        FROM reservations r
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.user_id = ? AND r.leaving_timestamp IS NOT NULL
        ORDER BY r.leaving_timestamp DESC
        LIMIT 5
    ''', (session['user_id'],))
    history = cursor.fetchall()
    
    conn.close()
    
    # Get random eco tip
    eco_tip = get_random_eco_tip()
    
    return render_template('user_dashboard.html', 
                         user_stats=user_stats,
                         lots=lots,
                         current_reservations=current_reservations,
                         history=history,
                         eco_tip=eco_tip)

# Book parking spot
@app.route('/book_spot/<int:lot_id>')
def book_spot(lot_id):
    if 'user_id' not in session or session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Find first available spot
    cursor.execute('SELECT * FROM parking_spots WHERE lot_id = ? AND status = "A" LIMIT 1', (lot_id,))
    spot = cursor.fetchone()
    
    if spot:
        # Book the spot
        cursor.execute('UPDATE parking_spots SET status = "O" WHERE id = ?', (spot[0],))
        
        # Create reservation
        cursor.execute('''
            INSERT INTO reservations (spot_id, user_id, parking_timestamp)
            VALUES (?, ?, ?)
        ''', (spot[0], session['user_id'], datetime.now()))
        
        conn.commit()
        flash('Parking spot booked successfully!')
    else:
        flash('No available spots in this parking lot!')
    
    conn.close()
    return redirect('/user')

# Check out from parking spot
@app.route('/checkout/<int:reservation_id>')
def checkout(reservation_id):
    if 'user_id' not in session or session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get reservation details
    cursor.execute('''
        SELECT r.*, pl.price, pl.eco_rating, ps.spot_type
        FROM reservations r
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.id = ? AND r.user_id = ?
    ''', (reservation_id, session['user_id']))
    
    reservation = cursor.fetchone()
    
    if reservation:
        # Calculate parking duration
        parking_start = datetime.strptime(reservation[3], '%Y-%m-%d %H:%M:%S.%f')
        parking_end = datetime.now()
        duration = (parking_end - parking_start).total_seconds() / 3600  # hours
        
        # Calculate cost
        cost = duration * reservation[6]  # price per hour
        
        # Calculate green benefits
        carbon_saved = calculate_carbon_savings(duration, reservation[7])
        green_points = calculate_green_points(duration, reservation[8], reservation[7])
        
        # Update reservation
        cursor.execute('''
            UPDATE reservations 
            SET leaving_timestamp = ?, cost = ?, carbon_saved = ?, green_points_earned = ?
            WHERE id = ?
        ''', (parking_end, cost, carbon_saved, green_points, reservation_id))
        
        # Update parking spot status
        cursor.execute('UPDATE parking_spots SET status = "A" WHERE id = ?', (reservation[1],))
        
        # Update user's green stats
        cursor.execute('''
            UPDATE users 
            SET carbon_saved = carbon_saved + ?, green_points = green_points + ?
            WHERE id = ?
        ''', (carbon_saved, green_points, session['user_id']))
        
        conn.commit()
        conn.close()
        
        # Check for new badges
        check_badges(session['user_id'])
        
        flash(f'Checked out successfully! You earned {green_points} green points and saved {carbon_saved}kg CO2!')
    else:
        flash('Invalid reservation!')
        conn.close()
    
    return redirect('/user')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect('/login')

# Run the app
if __name__ == '__main__':
    init_database()
    app.run(debug=True)