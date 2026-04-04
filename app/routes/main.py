from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, make_response
from app.models.room import Room
from app.models.booking import Booking
from app.models.user import User
from app.models.review import Review
from app import db, mail
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy.exc import ObjectNotExecutableError, IntegrityError, OperationalError
from sqlalchemy import or_, and_, desc
from flask_mail import Message
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from app.models.wishlist import Wishlist
from app.models.notification import Notification
from app.models.room_image import RoomImage

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # Advanced Recommendations logic
    recommendations = []
    recommended_title = "Featured Rooms"
    recommended_desc = "Carefully selected for your ultimate comfort"
    
    if current_user.is_authenticated and current_user.role != 'admin':
        # 1. Budget-based recommendations
        past_bookings = Booking.query.filter_by(user_id=current_user.id).all()
        if past_bookings:
            avg_past_price = sum(b.room.price for b in past_bookings) / len(past_bookings)
            # Find rooms within +/- 20% of their usual budget
            recommendations = Room.query.filter(
                Room.price.between(avg_past_price * 0.8, avg_past_price * 1.2),
                Room.status == 'available'
            ).limit(3).all()
            
            if recommendations:
                recommended_title = "Personalized for You"
                recommended_desc = "Rooms that match your preferred comfort and budget"
        
        # 2. If no budget match, recommend highly rated rooms of types they like
        if not recommendations and past_bookings:
            liked_types = [b.room.type for b in past_bookings]
            recommendations = Room.query.filter(Room.type.in_(liked_types))\
                                  .order_by(desc(Room.price)).limit(3).all()

    # Fallback: Top Rated Rooms
    if not recommendations:
        all_rooms = Room.query.all()
        # Sort by avg_rating in memory if needed, or just take top price for luxury feel
        recommendations = sorted(all_rooms, key=lambda x: x.avg_rating, reverse=True)[:3]
        
    return render_template('index.html', rooms=recommendations, recommended_title=recommended_title, recommended_desc=recommended_desc)

@main.route('/rooms')
def rooms():
    # Advanced Search & Filter
    query = Room.query

    # Search (by type or features)
    search_query = request.args.get('search', '').strip()
    if search_query:
        query = query.filter(
            or_(
                Room.type.ilike(f'%{search_query}%'),
                Room.features.ilike(f'%{search_query}%')
            )
        )

    # Filters
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    room_type = request.args.get('type')
    
    if min_price:
        query = query.filter(Room.price >= float(min_price))
    if max_price:
        query = query.filter(Room.price <= float(max_price))
    if room_type and room_type != 'All':
        query = query.filter(Room.type == room_type)

    # Smart Availability Filter (Date-based)
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    if check_in and check_out:
        try:
            start_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            end_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            
            if start_date < end_date:
                # Find all rooms and filter them by their dynamic availability
                filtered_rooms = []
                for room in query.all():
                    if room.get_availability_count(start_date, end_date) > 0:
                        filtered_rooms.append(room)
                return render_template('rooms.html', rooms=filtered_rooms, check_in=check_in, check_out=check_out)
        except ValueError:
            pass # Ignore invalid dates for general listing
            
    # Sorting
    sort_by = request.args.get('sort')
    if sort_by == 'price_asc':
        query = query.order_by(Room.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Room.price.desc())
        
    all_rooms = query.all()
    return render_template('rooms.html', rooms=all_rooms)

@main.route('/api/booked_dates/<int:room_id>')
def get_booked_dates(room_id):
    # Returns dates that are already booked for Flatpickr disabled dates
    bookings = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status.in_(['Pending', 'Confirmed', 'Checked-in'])
    ).all()
    
    booked_dates = []
    for b in bookings:
        delta = b.check_out - b.check_in
        for i in range(delta.days):
            day = b.check_in + timedelta(days=i)
            booked_dates.append(day.strftime('%Y-%m-%d'))
            
    return jsonify(booked_dates)

@main.route('/wishlist/toggle/<int:room_id>', methods=['POST'])
@login_required
def toggle_wishlist(room_id):
    wish_item = Wishlist.query.filter_by(user_id=current_user.id, room_id=room_id).first()
    if wish_item:
        db.session.delete(wish_item)
        db.session.commit()
        return jsonify({'status': 'removed'})
    else:
        new_wish = Wishlist(user_id=current_user.id, room_id=room_id)
        db.session.add(new_wish)
        db.session.commit()
        return jsonify({'status': 'added'})

@main.route('/wishlist')
@login_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=current_user.id).all()
    rooms = [item.room for item in items]
    return render_template('wishlist.html', rooms=rooms)
@main.route('/notifications/unread_count')
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@main.route('/notifications/mark_all_read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({Notification.is_read: True})
    db.session.commit()
    return jsonify({'status': 'success'})

@main.route('/book/<int:room_id>', methods=['GET', 'POST'])
@login_required
def book(room_id):
    if current_user.role == 'admin':
        flash('Admins cannot book rooms.', 'warning')
        return redirect(url_for('main.rooms'))
        
    room = Room.query.get_or_404(room_id)
    if room.status == 'maintenance':
        flash('This room is currently under maintenance.', 'danger')
        return redirect(url_for('main.rooms'))
        
    if request.method == 'POST':
        check_in_str = request.form.get('check_in')
        check_out_str = request.form.get('check_out')
        
        try:
            check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('main.book', room_id=room.id))

        if check_in_date >= check_out_date:
            flash('Check-out date must be after check-in date.', 'danger')
            return redirect(url_for('main.book', room_id=room.id))
            
        if check_in_date < datetime.today().date():
            flash('Cannot book in the past.', 'danger')
            return redirect(url_for('main.book', room_id=room.id))

        # Dynamic Pricing Logic & Total Calculation
        total_price = 0.0
        current_date = check_in_date
        while current_date < check_out_date:
            daily_price = room.price
            # Weekend surge (+20% on Saturdays and Sundays)
            if current_date.weekday() >= 5: 
                daily_price *= 1.20
            total_price += daily_price
            current_date += timedelta(days=1)
            
        total_price = round(total_price, 2)

        # Critical Backend Upgrade: Concurrent Booking Protection using row-level locking
        try:
            # Lock the room row for updates
            locked_room = Room.query.with_for_update().get(room_id)
            
            # Re-check overlap inside lock using the new inventory logic
            available_count = locked_room.get_availability_count(check_in_date, check_out_date)

            if available_count <= 0:
                flash(f'Sorry! This room type is now sold out for these dates.', 'danger')
                return redirect(url_for('main.book', room_id=room.id))
                
            # Insert Confirmed booking
            new_booking = Booking(
                user_id=current_user.id,
                room_id=locked_room.id,
                check_in=check_in_date,
                check_out=check_out_date,
                total_price=total_price,
                status='Confirmed',
                payment_status='Paid'
            )
            db.session.add(new_booking)
            
            # Create Notification
            notif = Notification(user_id=current_user.id, message=f"Booking confirmed for {locked_room.type} room from {check_in_date} to {check_out_date}!")
            db.session.add(notif)
            
            db.session.commit()
            
            flash('Booking successful! Your stay is confirmed.', 'success')
            return redirect(url_for('main.history'))
            
        except OperationalError:
            db.session.rollback()
            flash('Server busy due to high demand. Please try again.', 'danger')
            return redirect(url_for('main.book', room_id=room.id))

    return render_template('booking.html', room=room)

@main.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))
        
    if booking.payment_status == 'Paid':
        flash('Booking is already paid.', 'info')
        return redirect(url_for('main.history'))

    if request.method == 'POST':
        booking.payment_status = 'Paid'
        booking.status = 'Confirmed'
        
        # Create Notification
        notif = Notification(user_id=current_user.id, message=f"Payment successful! Your booking #{booking.id} is confirmed.")
        db.session.add(notif)
        
        db.session.commit()
        
        # Send Email Notification
        try:
            msg = Message("Booking Confirmed - Grand Horizon",
                          recipients=[current_user.email])
            msg.body = f"Hello {current_user.name},\n\nYour booking (ID: {booking.id}) for the {booking.room.type} room from {booking.check_in} to {booking.check_out} is confirmed!\n\nTotal Paid: ₹{booking.total_price}\n\nThank you for choosing Grand Horizon."
            mail.send(msg)
        except Exception as e:
            # Silently fail if email is not configured but logic executes
            print(f"Failed to send email: {e}")
            
        flash('Payment successful! Your booking is confirmed.', 'success')
        return redirect(url_for('main.history'))
        
    return render_template('payment.html', booking=booking)

@main.route('/history')
@login_required
def history():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('history.html', bookings=bookings)

@main.route('/rate/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def rate_stay(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure this booking belongs to the current user and is Checked-out
    if booking.user_id != current_user.id or booking.status != 'Checked-out':
        flash('You can only rate rooms after you have checked out.', 'danger')
        return redirect(url_for('main.history'))
    
    if request.method == 'POST':
        rating = int(request.form.get('rating', 5))
        comment = request.form.get('comment', '')
        
        # Check if review already exists
        existing_review = Review.query.filter_by(user_id=current_user.id, room_id=booking.room.id).first()
        if existing_review:
            flash('You have already reviewed this stay.', 'info')
            return redirect(url_for('main.history'))
            
        review = Review(user_id=current_user.id, room_id=booking.room.id, rating=rating, comment=comment)
        db.session.add(review)
        
        # Create a notification for the user
        notif = Notification(user_id=current_user.id, message=f"Thank you for reviewing your stay at the {booking.room.type} room!")
        db.session.add(notif)
        
        db.session.commit()
        flash('Thank you for your review!', 'success')
        return redirect(url_for('main.history'))
        
    return render_template('rate.html', booking=booking)

@main.route('/invoice/<int:booking_id>')
@login_required
def generate_invoice(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and current_user.role != 'admin':
        return redirect(url_for('main.index'))
        
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 24)
    p.drawString(100, 700, "Grand Horizon Hotel - Invoice")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 650, f"Booking ID: {booking.id}")
    p.drawString(100, 630, f"Date Issued: {datetime.now().strftime('%Y-%m-%d')}")
    p.drawString(100, 600, f"Customer: {booking.user.name}")
    p.drawString(100, 580, f"Email: {booking.user.email}")
    
    p.drawString(100, 540, "Room Details:")
    p.drawString(120, 520, f"Type: {booking.room.type}")
    p.drawString(120, 500, f"Check-in: {booking.check_in}")
    p.drawString(120, 480, f"Check-out: {booking.check_out}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 440, f"Total Amount Paid: ₹{booking.total_price}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{booking.id}.pdf'
    return response

@main.route('/notifications/read/all', methods=['POST'])
@login_required
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({Notification.is_read: True})
    db.session.commit()
    return jsonify({'status': 'success'})

@main.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('Thank you for your message! Our team will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html')
