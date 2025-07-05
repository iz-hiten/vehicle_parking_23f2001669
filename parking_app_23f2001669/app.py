from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = 'green-parking-secret-key-2024'

DATABASE = 'green_parking.db'


@app.template_filter('strptime')
def strptime_filter(s, fmt):
    return datetime.strptime(s, fmt)

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
            badges TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Parking lots table with eco features
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
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Parking spots table with types
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parking_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            spot_number INTEGER NOT NULL,
            status TEXT DEFAULT 'A',
            spot_type TEXT DEFAULT 'car',
            FOREIGN KEY (lot_id) REFERENCES parking_lots (id)
        )
    ''')
    
    # Reservations table with green tracking
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
            INSERT INTO users (username, password, email, green_points, badges) 
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', 'admin123', 'admin@greenparking.com', 1000, 'Super Admin,Eco Champion'))
    
    # Add sample eco tips
    sample_tips = [
        ('Walk or bike short distances instead of driving to reduce carbon footprint!', 'transport'),
        ('Choose parking spots with solar panels to support renewable energy!', 'energy'),
        ('Carpool with friends to reduce emissions and earn bonus green points!', 'transport'),
        ('Always use recycling bins available in eco-friendly parking lots!', 'waste'),
        ('Turn off your engine while waiting to reduce air pollution!', 'air'),
        ('Plant a tree with your earned green points to offset carbon emissions!', 'nature')
    ]
    
    for tip in sample_tips:
        cursor.execute('SELECT * FROM eco_tips WHERE tip_text = ?', (tip[0],))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO eco_tips (tip_text, category) VALUES (?, ?)', tip)
    
    conn.commit()
    conn.close()

def get_random_eco_tip():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT tip_text FROM eco_tips ORDER BY RANDOM() LIMIT 1')
    tip = cursor.fetchone()
    conn.close()
    return tip[0] if tip else "Save the planet with green parking!"

def calculate_carbon_saved(duration_minutes):
    # Simple calculation: 0.1 kg CO2 saved per hour of efficient parking
    return round((duration_minutes / 60) * 0.1, 2)

def calculate_green_points(carbon_saved, spot_type):
    base_points = int(carbon_saved * 10)
    if spot_type == 'bike':
        base_points *= 2  # Double points for bike parking
    elif spot_type == 'ev':
        base_points *= 1.5  # 50% bonus for EV parking
    return base_points

def award_badge(user_id, green_points):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT badges FROM users WHERE id = ?', (user_id,))
    current_badges = cursor.fetchone()[0]
    
    new_badges = []
    if green_points >= 100 and 'Eco Warrior' not in current_badges:
        new_badges.append('Eco Warrior')
    if green_points >= 500 and 'Green Champion' not in current_badges:
        new_badges.append('Green Champion')
    if green_points >= 1000 and 'Carbon Saver' not in current_badges:
        new_badges.append('Carbon Saver')
    
    if new_badges:
        updated_badges = current_badges + ',' + ','.join(new_badges) if current_badges else ','.join(new_badges)
        cursor.execute('UPDATE users SET badges = ? WHERE id = ?', (updated_badges, user_id))
        conn.commit()
    
    conn.close()
    return new_badges

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

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
            session['green_points'] = user[5]
            
            if username == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password!')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                          (username, password, email))
            conn.commit()
            flash('Registration successful! Welcome to Green Parking!')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get all parking lots
    cursor.execute('SELECT * FROM parking_lots')
    lots = cursor.fetchall()
    
    # Get all users
    cursor.execute('SELECT * FROM users WHERE username != "admin"')
    users = cursor.fetchall()
    
    # Get parking statistics
    cursor.execute('SELECT COUNT(*) FROM parking_spots WHERE status = "O"')
    occupied_spots = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM parking_spots WHERE status = "A"')
    available_spots = cursor.fetchone()[0]
    
    # Get total carbon saved
    cursor.execute('SELECT SUM(carbon_saved) FROM users')
    total_carbon_saved = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         lots=lots, 
                         users=users, 
                         occupied_spots=occupied_spots,
                         available_spots=available_spots,
                         total_carbon_saved=total_carbon_saved)

@app.route('/add_parking_lot', methods=['GET', 'POST'])
def add_parking_lot():
    if 'user_id' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    
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
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Insert parking lot
        cursor.execute('''
            INSERT INTO parking_lots (name, address, pincode, price, max_spots, eco_rating, 
                                    has_solar, has_ev_charging, has_recycling) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, address, pincode, price, max_spots, eco_rating, has_solar, has_ev_charging, has_recycling))
        
        lot_id = cursor.lastrowid
        
        # Create parking spots automatically
        for i in range(1, max_spots + 1):
            # First 10% spots for bikes, 20% for EVs, rest for cars
            if i <= max_spots * 0.1:
                spot_type = 'bike'
            elif i <= max_spots * 0.3:
                spot_type = 'ev'
            else:
                spot_type = 'car'
            
            cursor.execute('INSERT INTO parking_spots (lot_id, spot_number, spot_type) VALUES (?, ?, ?)',
                          (lot_id, i, spot_type))
        
        conn.commit()
        conn.close()
        
        flash('Parking lot created successfully with eco-friendly features!')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_parking_lot.html')

@app.route('/edit_parking_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_parking_lot(lot_id):
    if 'user_id' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pincode = request.form['pincode']
        price = float(request.form['price'])
        eco_rating = int(request.form['eco_rating'])
        has_solar = 1 if 'has_solar' in request.form else 0
        has_ev_charging = 1 if 'has_ev_charging' in request.form else 0
        has_recycling = 1 if 'has_recycling' in request.form else 0
        
        cursor.execute('''
            UPDATE parking_lots 
            SET name=?, address=?, pincode=?, price=?, eco_rating=?, 
                has_solar=?, has_ev_charging=?, has_recycling=?
            WHERE id=?
        ''', (name, address, pincode, price, eco_rating, has_solar, has_ev_charging, has_recycling, lot_id))
        
        conn.commit()
        conn.close()
        
        flash('Parking lot updated successfully!')
        return redirect(url_for('admin_dashboard'))
    
    cursor.execute('SELECT * FROM parking_lots WHERE id = ?', (lot_id,))
    lot = cursor.fetchone()
    conn.close()
    
    return render_template('edit_parking_lot.html', lot=lot)

@app.route('/delete_parking_lot/<int:lot_id>')
def delete_parking_lot(lot_id):
    if 'user_id' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if all spots are available
    cursor.execute('SELECT COUNT(*) FROM parking_spots WHERE lot_id = ? AND status = "O"', (lot_id,))
    occupied_spots = cursor.fetchone()[0]
    
    if occupied_spots > 0:
        flash('Cannot delete parking lot! Some spots are still occupied.')
    else:
        cursor.execute('DELETE FROM parking_spots WHERE lot_id = ?', (lot_id,))
        cursor.execute('DELETE FROM parking_lots WHERE id = ?', (lot_id,))
        conn.commit()
        flash('Parking lot deleted successfully!')
    
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/user')
def user_dashboard():
    if 'user_id' not in session or session['username'] == 'admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get user info
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    # Get available parking lots
    cursor.execute('SELECT * FROM parking_lots')
    lots = cursor.fetchall()
    
    # Get user's current reservations
    cursor.execute('''
        SELECT r.*, pl.name as lot_name, ps.spot_number, ps.spot_type
        FROM reservations r
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.user_id = ? AND r.leaving_timestamp IS NULL
    ''', (session['user_id'],))
    current_reservations = cursor.fetchall()
    
    # Get user's parking history
    cursor.execute('''
        SELECT r.*, pl.name as lot_name, ps.spot_number, ps.spot_type
        FROM reservations r
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.user_id = ? AND r.leaving_timestamp IS NOT NULL
        ORDER BY r.leaving_timestamp DESC LIMIT 5
    ''', (session['user_id'],))
    history = cursor.fetchall()
    
    conn.close()
    
    eco_tip = get_random_eco_tip()
    
    return render_template('user_dashboard.html', 
                         user=user, 
                         lots=lots, 
                         current_reservations=current_reservations,
                         history=history,
                         eco_tip=eco_tip)

@app.route('/book_parking/<int:lot_id>')
def book_parking(lot_id):
    if 'user_id' not in session or session['username'] == 'admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if user already has an active reservation
    cursor.execute('''
        SELECT COUNT(*) FROM reservations 
        WHERE user_id = ? AND leaving_timestamp IS NULL
    ''', (session['user_id'],))
    
    if cursor.fetchone()[0] > 0:
        flash('You already have an active parking reservation!')
        return redirect(url_for('user_dashboard'))
    
    # Find first available spot
    cursor.execute('''
        SELECT * FROM parking_spots 
        WHERE lot_id = ? AND status = "A" 
        ORDER BY spot_type DESC, spot_number ASC LIMIT 1
    ''', (lot_id,))
    
    spot = cursor.fetchone()
    
    if not spot:
        flash('No available spots in this parking lot!')
        return redirect(url_for('user_dashboard'))
    
    # Book the spot
    cursor.execute('''
        INSERT INTO reservations (spot_id, user_id, parking_timestamp) 
        VALUES (?, ?, ?)
    ''', (spot[0], session['user_id'], datetime.now()))
    
    cursor.execute('UPDATE parking_spots SET status = "O" WHERE id = ?', (spot[0],))
    
    conn.commit()
    conn.close()
    
    flash(f'Parking spot #{spot[2]} booked successfully! Go green!')
    return redirect(url_for('user_dashboard'))

@app.route('/checkout/<int:reservation_id>')
def checkout(reservation_id):
    if 'user_id' not in session or session['username'] == 'admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get reservation details
    cursor.execute('''
        SELECT r.*, ps.spot_type, pl.price 
        FROM reservations r
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.id = ? AND r.user_id = ?
    ''', (reservation_id, session['user_id']))
    
    reservation = cursor.fetchone()
    
    if not reservation:
        flash('Invalid reservation!')
        return redirect(url_for('user_dashboard'))
    
    # Calculate duration, cost, and green benefits
    parking_time = datetime.strptime(reservation[3], '%Y-%m-%d %H:%M:%S.%f')
    leaving_time = datetime.now()
    duration = leaving_time - parking_time
    duration_minutes = duration.total_seconds() / 60
    
    cost = (duration_minutes / 60) * float(reservation[6])  # hourly rate
    carbon_saved = calculate_carbon_saved(duration_minutes)
    green_points = calculate_green_points(carbon_saved, reservation[7])
    
    # Update reservation
    cursor.execute('''
        UPDATE reservations 
        SET leaving_timestamp = ?, cost = ?, carbon_saved = ?, green_points_earned = ?
        WHERE id = ?
    ''', (leaving_time, cost, carbon_saved, green_points, reservation_id))
    
    # Update spot status
    cursor.execute('UPDATE parking_spots SET status = "A" WHERE id = ?', (reservation[1],))
    
    # Update user's green stats
    cursor.execute('''
        UPDATE users 
        SET carbon_saved = carbon_saved + ?, green_points = green_points + ?
        WHERE id = ?
    ''', (carbon_saved, green_points, session['user_id']))
    
    conn.commit()
    conn.close()
    
    # Award badges
    new_badges = award_badge(session['user_id'], session['green_points'] + green_points)
    session['green_points'] += green_points
    
    badge_message = f' You earned new badges: {", ".join(new_badges)}!' if new_badges else ''
    
    flash(f'Checkout successful! You saved {carbon_saved}kg CO2 and earned {green_points} green points!{badge_message}')
    return redirect(url_for('user_dashboard'))

@app.route('/api/parking_stats')
def parking_stats():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT pl.name, COUNT(ps.id) as total_spots,
               SUM(CASE WHEN ps.status = 'O' THEN 1 ELSE 0 END) as occupied_spots
        FROM parking_lots pl
        LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
        GROUP BY pl.id, pl.name
    ''')
    
    stats = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'name': stat[0],
        'total_spots': stat[1],
        'occupied_spots': stat[2],
        'available_spots': stat[1] - stat[2]
    } for stat in stats])

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out. Thank you for choosing Green Parking!')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_database()
    app.run(debug=True)