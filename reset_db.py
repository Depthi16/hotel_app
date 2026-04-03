import pymysql
from config import Config

# Extract DB connection info from URI
# 'mysql+pymysql://root:root%40123@localhost/hotel_db'
uri = Config.SQLALCHEMY_DATABASE_URI
parts = uri.split('://')[1].split('@')
user_pass = parts[0].split(':')
user = user_pass[0]
password = user_pass[1].replace('%40', '@')
host_db = parts[1].split('/')
host = host_db[0]
db_name = host_db[1]

print(f"Connecting to {db_name} on {host}...")
connection = pymysql.connect(
    host=host,
    user=user,
    password=password,
    database=db_name
)

try:
    with connection.cursor() as cursor:
        print("Dropping 'rooms' table to clear schema mismatch...")
        # We need to disable foreign key checks if there are references
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("DROP TABLE IF EXISTS rooms;")
        cursor.execute("DROP TABLE IF EXISTS bookings;")
        cursor.execute("DROP TABLE IF EXISTS reviews;")
        cursor.execute("DROP TABLE IF EXISTS wishlist;")
        cursor.execute("DROP TABLE IF EXISTS notifications;")
        cursor.execute("DROP TABLE IF EXISTS room_images;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    connection.commit()
    print("Tables dropped successfully.")
finally:
    connection.close()

from app import create_app, db
app = create_app()
with app.app_context():
    print("Recreating tables and seeding...")
    db.create_all()
    print("Done! Database is now fresh and compatible with the new models.")
