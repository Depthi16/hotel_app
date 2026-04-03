from app import db
from datetime import datetime

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Confirmed, Checked-in, Checked-out, Cancelled
    payment_status = db.Column(db.String(20), default='Unpaid') # Unpaid, Paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
