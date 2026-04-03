from app import db

class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='available') # available, booked, maintenance
    image_url = db.Column(db.String(255), nullable=True)
    features = db.Column(db.String(255), nullable=True) # e.g. "WiFi,AC,TV"
    total_rooms = db.Column(db.Integer, default=1)
    blocked_rooms = db.Column(db.Integer, default=0)
    
    bookings = db.relationship('Booking', backref='room', lazy=True)
    reviews = db.relationship('Review', backref='room', lazy=True)
    
    def get_availability_count(self, check_in, check_out):
        # Calculate availability for a given date range
        # Available = total - blocked - overlapping bookings
        from app.models.booking import Booking
        from datetime import datetime
        
        # Ensure we have date objects
        if isinstance(check_in, str) and check_in.strip():
            check_in = datetime.strptime(check_in, '%Y-%m-%d').date()
        if isinstance(check_out, str) and check_out.strip():
            check_out = datetime.strptime(check_out, '%Y-%m-%d').date()
            
        from datetime import date, datetime
        if not check_in or not check_out or not isinstance(check_in, (date, datetime)) or not isinstance(check_out, (date, datetime)):
            return max(0, self.total_rooms - self.blocked_rooms)
            
        overlapping_bookings = Booking.query.filter(
            Booking.room_id == self.id,
            Booking.status.in_(['Confirmed', 'Checked-in']),
            Booking.check_in < check_out,
            Booking.check_out > check_in
        ).count()
        
        return max(0, self.total_rooms - self.blocked_rooms - overlapping_bookings)

    @property
    def avg_rating(self):
        if not self.reviews:
            return 0
        return sum(r.rating for r in self.reviews) / len(self.reviews)
