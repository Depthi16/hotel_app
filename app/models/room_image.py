from app import db

class RoomImage(db.Model):
    __tablename__ = 'room_images'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    
    room = db.relationship('Room', backref='images')
