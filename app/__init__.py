from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail

# Initialize Flask extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    with app.app_context():
        # Import models
        from .models.user import User
        from .models.room import Room
        from .models.booking import Booking
        from .models.review import Review
        from .models.wishlist import Wishlist
        from .models.notification import Notification
        from .models.room_image import RoomImage
        
        # Create database tables for our data models
        db.create_all()
        
        try:
            # --- SEED ADMIN & ROOMS ---
            # 1. Create a Built-in Admin User if none exists
            admin_email = 'admin@hotel.com'
            if not User.query.filter_by(email=admin_email).first():
                hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
                admin_user = User(name='Hotel Admin', email=admin_email, password_hash=hashed_pw, role='admin')
                db.session.add(admin_user)
                db.session.commit()
                print("Built-in Admin created (Email: admin@hotel.com | Password: admin123)")

            # 2. Add sample Rooms with images if the database is empty
            if Room.query.count() == 0:
                sample_rooms = [
                    Room(type='Deluxe Ocean View', price=250.00, status='available', 
                         features='WiFi,AC,TV,Ocean View,Minibar',
                         total_rooms=10, blocked_rooms=1,
                         image_url='https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800&auto=format&fit=crop'),
                    Room(type='Premium Suite', price=400.00, status='available', 
                         features='WiFi,AC,TV,Private Pool,Garden',
                         total_rooms=5, blocked_rooms=0,
                         image_url='https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&auto=format&fit=crop'),
                    Room(type='Cozy Single', price=120.00, status='available', 
                         features='WiFi,AC,TV,Work Desk',
                         total_rooms=15, blocked_rooms=2,
                         image_url='https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&auto=format&fit=crop'),
                    Room(type='Family Penthouse', price=650.00, status='available', 
                         features='WiFi,AC,TV,Kitchenette,Balcony',
                         total_rooms=3, blocked_rooms=0,
                         image_url='https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800&auto=format&fit=crop')
                ]
                db.session.bulk_save_objects(sample_rooms)
                db.session.commit()
                
                # Add secondary images for the gallery
                rooms = Room.query.all()
                for r in rooms:
                    secondary_imgs = [
                        RoomImage(room_id=r.id, image_url='https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800&auto=format&fit=crop'),
                        RoomImage(room_id=r.id, image_url='https://images.unsplash.com/photo-1598928636135-d146006ff4be?w=800&auto=format&fit=crop')
                    ]
                    db.session.add_all(secondary_imgs)
                db.session.commit()
                print("Sample rooms and images successfully loaded into the database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error during seeding: {e}")
            # Do NOT exit, allow the app to start even if seeding failed
        
        # Register blueprints
        from .routes.main import main
        from .routes.auth import auth
        from .routes.admin import admin
        
        app.register_blueprint(main)
        app.register_blueprint(auth, url_prefix='/auth')
        app.register_blueprint(admin, url_prefix='/admin')
        
        # FIX: Dispose of the engine to prevent shared connections across Gunicorn worker forks.
        # This forces each worker to create its own fresh, safe SSL connection.
        db.engine.dispose()
        
        return app
