from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    full_name = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    pin_code = db.Column(db.String(20), nullable=True)
    vehicle_no = db.Column(db.String(20), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    
    # Notification preferences
    notification_preference = db.Column(db.String(20), default='email')  # email, gchat, sms
    gchat_email = db.Column(db.String(120), nullable=True)
    reminder_time = db.Column(db.String(5), default='18:00')  # 24-hour format HH:MM
    
    # Report preferences
    report_format = db.Column(db.String(10), default='html')  # html or pdf
    
    # One-to-many relationship with ParkingReservation
    reservations = db.relationship('ParkingReservation', backref='user', lazy=True, cascade="all, delete-orphan")
    
    # One-to-many relationship with SavedPaymentMethod
    payment_methods = db.relationship('SavedPaymentMethod', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, username, email, password, is_admin=False, phone=None, full_name=None, address=None, pin_code=None, vehicle_no=None):
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.is_admin = is_admin
        self.phone = phone
        self.full_name = full_name
        self.address = address
        self.pin_code = pin_code
        self.vehicle_no = vehicle_no
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def active_reservations(self):
        return len([r for r in self.reservations if r.active])
    
    @property
    def total_bookings(self):
        return len(self.reservations)
    
    @property
    def total_spent(self):
        return sum(r.parking_cost or 0 for r in self.reservations if not r.active)
    
    def __repr__(self):
        return f'<User {self.username}>'


class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prime_location_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(IST))
    
    # One-to-many relationship with ParkingSpot
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True, cascade="all, delete-orphan")
    
    @property
    def available_spots(self):
        return len([spot for spot in self.spots if spot.status == 'A'])
        
    def __repr__(self):
        return f'<ParkingLot {self.name}>'


class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    spot_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(1), nullable=False, default='A')  # 'A' for Available, 'O' for Occupied
    created_at = db.Column(db.DateTime, default=datetime.now(IST))
    
    # One-to-many relationship with ParkingReservation
    reservations = db.relationship('ParkingReservation', backref='spot', lazy=True)
    
    @property
    def current_reservation(self):
        # Find the active reservation for this spot
        return ParkingReservation.query.filter_by(spot_id=self.id, active=True).first()
        
    def __repr__(self):
        return f'<ParkingSpot {self.spot_number} in Lot {self.lot_id}>'


class ParkingReservation(db.Model):
    __tablename__ = 'parking_reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    vehicle_no = db.Column(db.String(20), nullable=True)
    parking_timestamp = db.Column(db.DateTime, default=datetime.now(IST))
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)
    active = db.Column(db.Boolean, default=True)
    
    # Payment information
    payment_status = db.Column(db.String(20), default='PENDING')  # PENDING, PAID, FAILED
    payment_date = db.Column(db.DateTime, nullable=True)
    payment_method = db.Column(db.String(20), nullable=True)  # credit-card, paypal, etc.
    transaction_id = db.Column(db.String(50), nullable=True)
    
    @property
    def duration(self):
        # Calculate duration, using current time if still active
        end_time = self.leaving_timestamp or datetime.now(IST)
        start_time = self.parking_timestamp
        
        # Ensure both are timezone aware for subtraction
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=IST)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=IST)
            
        diff_seconds = (end_time - start_time).total_seconds()
        
        hours = int(diff_seconds // 3600)
        minutes = int((diff_seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
            
    def __repr__(self):
        return f'<ParkingReservation {self.id}>'


class SavedPaymentMethod(db.Model):
    __tablename__ = 'saved_payment_methods'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Payment method type
    payment_type = db.Column(db.String(20), nullable=False)  # 'card', 'upi', etc.
    
    # Masked card details (for security, only store last 4 digits)
    card_last_four = db.Column(db.String(4), nullable=True)
    card_type = db.Column(db.String(20), nullable=True)  # 'visa', 'mastercard', etc.
    card_holder_name = db.Column(db.String(100), nullable=True)
    card_expiry = db.Column(db.String(5), nullable=True)  # MM/YY format
    
    # UPI details
    upi_id = db.Column(db.String(50), nullable=True)
    
    # Common fields
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(IST))
    last_used = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        if self.payment_type == 'card':
            return f'<Card ending in {self.card_last_four}>'
        elif self.payment_type == 'upi':
            return f'<UPI ID: {self.upi_id}>'
        else:
            return f'<PaymentMethod {self.id}>'
