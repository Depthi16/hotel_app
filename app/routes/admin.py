from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import db, bcrypt
from app.models.room import Room
from app.models.booking import Booking
from app.models.user import User
from flask_login import login_required, current_user, login_user
from functools import wraps

admin = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'staff']:
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Only full Admins can perform this action.', 'danger')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.role in ['admin', 'staff']:
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and is an admin/staff
        if user and user.role in ['admin', 'staff'] and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
        else:
            flash('Admin access denied. Please check your credentials.', 'danger')
            
    return render_template('admin/login.html')

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_bookings = Booking.query.count()
    available_rooms = Room.query.filter_by(status='available').count()
    
    # Calculate total revenue from Confirmed and Checked-out bookings
    valid_bookings = Booking.query.filter(Booking.status.in_(['Confirmed', 'Checked-in', 'Checked-out'])).all()
    total_revenue = sum(b.total_price for b in valid_bookings)
    
    # --- Advanced Analytics Data ---
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # 1. Monthly Bookings (Last 6 Months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_stats = db.session.query(
        func.date_format(Booking.created_at, '%b').label('month'),
        func.count(Booking.id).label('count'),
        func.sum(Booking.total_price).label('revenue')
    ).filter(Booking.created_at >= six_months_ago)\
     .group_by('month').order_by(func.min(Booking.created_at)).all()
    
    line_labels = [s[0] for s in monthly_stats]
    line_data_bookings = [s[1] for s in monthly_stats]
    line_data_revenue = [float(s[2]) if s[2] else 0 for s in monthly_stats]
    
    # 2. Most Booked Room Types (Pie Chart)
    room_popularity = db.session.query(
        Room.type, func.count(Booking.id)
    ).join(Booking).group_by(Room.type).all()
    
    pie_labels = [r[0] for r in room_popularity]
    pie_data = [r[1] for r in room_popularity]

    # Booking trends by status (kept for legacy or extra info)
    status_counts = db.session.query(Booking.status, func.count(Booking.id)).group_by(Booking.status).all()
    status_labels = [s[0] for s in status_counts]
    status_data = [s[1] for s in status_counts]
    
    return render_template('admin/dashboard.html', 
                          total_bookings=total_bookings,
                          available_rooms=available_rooms,
                          total_revenue=total_revenue,
                          line_labels=line_labels,
                          line_data_bookings=line_data_bookings,
                          line_data_revenue=line_data_revenue,
                          pie_labels=pie_labels,
                          pie_data=pie_data,
                          status_labels=status_labels,
                          status_data=status_data)

@admin.route('/rooms', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_rooms():
    if request.method == 'POST':
        if current_user.role == 'receptionist':
            flash('Receptionists cannot add new rooms.', 'danger')
            return redirect(url_for('admin.manage_rooms'))
            
        room_type = request.form.get('type')
        price = request.form.get('price')
        status = request.form.get('status', 'available')
        image_url = request.form.get('image_url')
        total_rooms = request.form.get('total_rooms', 1)
        blocked_rooms = request.form.get('blocked_rooms', 0)
        
        new_room = Room(
            type=room_type, 
            price=float(price), 
            status=status, 
            image_url=image_url,
            total_rooms=int(total_rooms),
            blocked_rooms=int(blocked_rooms)
        )
        db.session.add(new_room)
        db.session.commit()
        flash('Room type added successfully with inventory!', 'success')
        return redirect(url_for('admin.manage_rooms'))
        
    rooms = Room.query.all()
    return render_template('admin/manage_rooms.html', rooms=rooms)

@admin.route('/room/toggle_maintenance/<int:room_id>')
@login_required
@admin_required
def toggle_maintenance(room_id):
    room = Room.query.get_or_404(room_id)
    if room.status == 'maintenance':
        room.status = 'available'
        flash(f'Room {room.id} is now available.', 'success')
    else:
        active = Booking.query.filter(Booking.room_id==room_id, Booking.status.in_(['Pending', 'Confirmed', 'Checked-in'])).first()
        if active:
            flash('Cannot place an occupied room into maintenance.', 'danger')
        else:
            room.status = 'maintenance'
            flash(f'Room {room.id} placed into maintenance.', 'warning')
    db.session.commit()
    return redirect(url_for('admin.manage_rooms'))

@admin.route('/room/delete/<int:room_id>')
@login_required
@super_admin_required
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    active_bookings = Booking.query.filter(Booking.room_id==room_id, Booking.status.in_(['Pending', 'Confirmed', 'Checked-in'])).first()
    if active_bookings:
        flash('Cannot delete room with active bookings.', 'danger')
        return redirect(url_for('admin.manage_rooms'))
        
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted successfully', 'success')
    return redirect(url_for('admin.manage_rooms'))

@admin.route('/room/edit/<int:room_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_room(room_id):
    if current_user.role == 'receptionist':
        flash('Receptionists cannot edit rooms.', 'danger')
        return redirect(url_for('admin.manage_rooms'))
        
    room = Room.query.get_or_404(room_id)
    
    if request.method == 'POST':
        room.type = request.form.get('type')
        room.price = float(request.form.get('price'))
        room.total_rooms = int(request.form.get('total_rooms'))
        room.blocked_rooms = int(request.form.get('blocked_rooms'))
        room.image_url = request.form.get('image_url')
        
        db.session.commit()
        flash(f'Room {room.type} updated successfully!', 'success')
        return redirect(url_for('admin.manage_rooms'))
        
    return render_template('admin/edit_room.html', room=room)

@admin.route('/bookings')
@login_required
@admin_required
def manage_bookings():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/manage_bookings.html', bookings=bookings)

@admin.route('/booking/update/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def update_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    new_status = request.form.get('status')
    
    if new_status in ['Pending', 'Confirmed', 'Checked-in', 'Checked-out', 'Cancelled']:
        booking.status = new_status
        db.session.commit()
        flash(f'Booking #{booking.id} status updated to {new_status}.', 'success')
        
    return redirect(url_for('admin.manage_bookings'))

@admin.route('/reviews')
@login_required
@admin_required
def manage_reviews():
    from app.models.review import Review
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/manage_reviews.html', reviews=reviews)

@admin.route('/review/delete/<int:review_id>')
@login_required
@super_admin_required
def delete_review(review_id):
    from app.models.review import Review
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully.', 'success')
    return redirect(url_for('admin.manage_reviews'))
