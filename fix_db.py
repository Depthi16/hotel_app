from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os

# Manual setup to avoid create_app() which runs validation logic
app = Flask(__name__)
# URL encoded password root@123 -> root%40123
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root%40123@localhost/hotel_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        print("Updating database schema...")
        
        # SQL to add columns if they don't exist
        
        # 1. Total Rooms
        try:
            db.session.execute(text("ALTER TABLE rooms ADD COLUMN total_rooms INTEGER DEFAULT 1"))
            db.session.commit()
            print("Successfully added 'total_rooms' column.")
        except Exception as e:
            db.session.rollback()
            print(f"Total_rooms column check: {e}")

        # 2. Blocked Rooms
        try:
            db.session.execute(text("ALTER TABLE rooms ADD COLUMN blocked_rooms INTEGER DEFAULT 0"))
            db.session.commit()
            print("Successfully added 'blocked_rooms' column.")
        except Exception as e:
            db.session.rollback()
            print(f"Blocked_rooms column check: {e}")

        print("Database schema is now synchronized.")
        
    except Exception as e:
        print(f"Critical error during migration: {e}")

print("Done.")
