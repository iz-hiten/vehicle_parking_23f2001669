# database.py - Green Parking App Database Setup
# This file handles all database operations for our parking app

import sqlite3
from datetime import datetime
import os

# Database file name
DATABASE_NAME = 'green_parking.db'

def create_database():
    """
    Creates the database and all tables needed for the Green Parking App
    This function runs when the app starts for the first time
    """
    print("Creating database...")
    
    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Create users table - stores all user information
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
    print("✅ Users table created")
    
    # Create parking_lots table - stores parking lot information
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
    print("✅ Parking lots table created")
    
    # Create parking_spots table - stores individual parking spots
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parking_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            spot_number TEXT NOT NULL,
            status TEXT DEFAULT 'A',
            spot_type TEXT DEFAULT 'car',
            FOREIGN KEY (lot_id) REFERENCES parking_lots (id)
        )
    ''')
    print("✅ Parking spots table created")
    
    # Create reservations table - stores booking information
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
    print("✅ Reservations table created")
    
    # Create eco_tips table - stores environmental tips
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eco_tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tip_text TEXT NOT NULL,
            category TEXT NOT NULL
        )
    ''')
    print("✅ Eco tips table created")
    
    conn.commit()
    conn.close()
    print("✅ Database created successfully!")

def create_admin_user():
    """
    Creates the admin user if it doesn't exist
    Admin can access all features of the app
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Check if admin already exists
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone():
        print("✅ Admin user already exists")
        conn.close()
        return
    
    # Create admin user
    cursor.execute('''
        INSERT INTO users (username, password, email, green_points, badges) 
        VALUES (?, ?, ?, ?, ?)
    ''', ('admin', 'admin123', 'admin@greenparking.com', 1000, 'Super Admin,Eco Champion'))
    
    conn.commit()
    conn.close()
    print("✅ Admin user created successfully!")

def add_sample_eco_tips():
    """
    Adds sample eco-friendly tips to the database
    These tips will be shown to users on their dashboard
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Sample eco tips
    eco_tips = [
        ('Walk or bike short distances instead of driving to reduce carbon footprint!', 'transport'),
        ('Choose parking spots with solar panels to support renewable energy!', 'energy'),
        ('Carpool with friends to reduce emissions and earn bonus green points!', 'transport'),
        ('Always use recycling bins available in eco-friendly parking lots!', 'waste'),
        ('Turn off your engine while waiting to reduce air pollution!', 'air'),
        ('Plant a tree with your earned green points to offset carbon emissions!', 'nature'),
        ('Use public transport when possible to reduce overall vehicle emissions!', 'transport'),
        ('Choose electric or hybrid vehicles for a cleaner environment!', 'vehicle'),
        ('Park in shaded areas to reduce air conditioning usage!', 'energy'),
        ('Support businesses that use renewable energy sources!', 'energy')
    ]
    
    # Add tips to database (only if they don't exist)
    for tip_text, category in eco_tips:
        cursor.execute('SELECT * FROM eco_tips WHERE tip_text = ?', (tip_text,))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO eco_tips (tip_text, category) VALUES (?, ?)', (tip_text, category))
    
    conn.commit()
    conn.close()
    print("✅ Sample eco tips added successfully!")

def add_sample_parking_lots():
    """
    Adds sample parking lots for testing
    This helps beginners test the app without creating lots manually
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Check if parking lots already exist
    cursor.execute('SELECT COUNT(*) FROM parking_lots')
    if cursor.fetchone()[0] > 0:
        print("✅ Sample parking lots already exist")
        conn.close()
        return
    
    # Sample parking lots
    sample_lots = [
        ('Green Valley Mall', '123 Eco Street, Green City', '12345', 5.0, 50, 5, 1, 1, 1),
        ('Solar Park Plaza', '456 Solar Avenue, Eco Town', '67890', 3.5, 30, 4, 1, 0, 1),
        ('EV Charging Hub', '789 Electric Road, Future City', '11111', 7.0, 25, 5, 1, 1, 0),
        ('Bike Friendly Lot', '321 Cycle Lane, Green Village', '22222', 2.0, 40, 3, 0, 0, 1),
        ('Eco Business Center', '654 Sustainable Street, Clean City', '33333', 6.0, 60, 4, 1, 1, 1)
    ]
    
    for lot_data in sample_lots:
        name, address, pincode, price, max_spots, eco_rating, has_solar, has_ev, has_recycling = lot_data
        
        # Insert parking lot
        cursor.execute('''
            INSERT INTO parking_lots (name, address, pincode, price, max_spots, eco_rating, 
                                    has_solar, has_ev_charging, has_recycling) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, address, pincode, price, max_spots, eco_rating, has_solar, has_ev, has_recycling))
        
        lot_id = cursor.lastrowid
        
        # Create parking spots for each lot
        for spot_num in range(1, max_spots + 1):
            # Assign spot types: 10% bikes, 20% EVs, 70% cars
            if spot_num <= max_spots * 0.1:
                spot_type = 'bike'
            elif spot_num <= max_spots * 0.3:
                spot_type = 'ev'
            else:
                spot_type = 'car'
            
            cursor.execute('''
                INSERT INTO parking_spots (lot_id, spot_number, spot_type) 
                VALUES (?, ?, ?)
            ''', (lot_id, spot_num, spot_type))
    
    conn.commit()
    conn.close()
    print("✅ Sample parking lots created successfully!")

def get_database_stats():
    """
    Returns basic statistics about the database
    Useful for checking if everything is working
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Get counts from each table
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM parking_lots')
    lot_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM parking_spots')
    spot_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM reservations')
    reservation_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM eco_tips')
    tip_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'users': user_count,
        'parking_lots': lot_count,
        'parking_spots': spot_count,
        'reservations': reservation_count,
        'eco_tips': tip_count
    }

def reset_database():
    """
    Deletes the database file and creates a fresh one
    WARNING: This will delete all data!
    """
    if os.path.exists(DATABASE_NAME):
        os.remove(DATABASE_NAME)
        print("🗑️ Old database deleted")
    
    initialize_database()

def initialize_database():
    """
    Complete database initialization
    This function sets up everything needed for the app
    """
    print("🚀 Initializing Green Parking Database...")
    
    # Create all tables
    create_database()
    
    # Create admin user
    create_admin_user()
    
    # Add sample data
    add_sample_eco_tips()
    add_sample_parking_lots()
    
    # Show database statistics
    stats = get_database_stats()
    print("\n📊 Database Statistics:")
    print(f"   Users: {stats['users']}")
    print(f"   Parking Lots: {stats['parking_lots']}")
    print(f"   Parking Spots: {stats['parking_spots']}")
    print(f"   Reservations: {stats['reservations']}")
    print(f"   Eco Tips: {stats['eco_tips']}")
    
    print("\n🎉 Database initialization complete!")
    print("📝 Admin Login: username=admin, password=admin123")

def check_database_health():
    """
    Checks if the database is working properly
    Returns True if everything is OK
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Test each table
        cursor.execute('SELECT 1 FROM users LIMIT 1')
        cursor.execute('SELECT 1 FROM parking_lots LIMIT 1')
        cursor.execute('SELECT 1 FROM parking_spots LIMIT 1')
        cursor.execute('SELECT 1 FROM reservations LIMIT 1')
        cursor.execute('SELECT 1 FROM eco_tips LIMIT 1')
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return False

# Helper functions for common database operations
def get_user_by_username(username):
    """Get user information by username"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_available_spots(lot_id):
    """Get count of available spots in a parking lot"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM parking_spots WHERE lot_id = ? AND status = "A"', (lot_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_user_green_stats(user_id):
    """Get user's green statistics"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT carbon_saved, green_points, badges FROM users WHERE id = ?', (user_id,))
    stats = cursor.fetchone()
    conn.close()
    return stats

# Run this when the file is executed directly
if __name__ == '__main__':
    print("🌱 Green Parking Database Setup")
    print("=" * 40)
    
    choice = input("Choose an option:\n1. Initialize database\n2. Reset database\n3. Check database health\n4. Show statistics\nEnter choice (1-4): ")
    
    if choice == '1':
        initialize_database()
    elif choice == '2':
        confirm = input("⚠️ This will delete all data! Are you sure? (yes/no): ")
        if confirm.lower() == 'yes':
            reset_database()
        else:
            print("❌ Operation cancelled")
    elif choice == '3':
        if check_database_health():
            print("✅ Database is healthy!")
        else:
            print("❌ Database has issues!")
    elif choice == '4':
        if os.path.exists(DATABASE_NAME):
            stats = get_database_stats()
            print("\n📊 Database Statistics:")
            for table, count in stats.items():
                print(f"   {table.capitalize()}: {count}")
        else:
            print("❌ Database doesn't exist yet!")
    else:
        print("❌ Invalid choice!")