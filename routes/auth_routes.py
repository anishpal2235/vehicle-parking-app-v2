from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db, ParkingReservation
from werkzeug.security import generate_password_hash
from utils.helpers import normalize_phone_number, validate_vehicle_format, normalize_vehicle_number, validate_email_domain

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # If user exists and is admin, or if credentials are invalid, show generic error
        if not user or not user.check_password(password) or user.is_admin:
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        return redirect(url_for('user.dashboard'))
        
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        address = request.form.get('address')
        pin_code = request.form.get('pin_code')
        phone = request.form.get('phone')
        vehicle_no = request.form.get('vehicle_no')
        
        # Validate email domain
        is_valid_domain, domain_message = validate_email_domain(email)
        if not is_valid_domain:
            flash(domain_message, 'danger')
            return redirect(url_for('auth.register'))
        
        # Use full name as username instead of email
        username = full_name
        
        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if username already exists
        user = User.query.filter_by(username=username).first()
        if user:
            # If username is taken, append a unique identifier
            username = f"{full_name}_{email.split('@')[0]}"
        
        # Check if phone number already exists using normalized comparison
        if phone:
            normalized_phone = normalize_phone_number(phone)
            if normalized_phone:
                # Get all users and compare normalized phone numbers
                users = User.query.all()
                for user in users:
                    if user.phone and normalize_phone_number(user.phone) == normalized_phone:
                        flash('Phone number already registered. Please use a different phone number.', 'danger')
                        return redirect(url_for('auth.register'))
        
        # Check vehicle number format and normalize
        normalized_vehicle_no = None
        if vehicle_no:
            is_valid, normalized_vehicle_no = validate_vehicle_format(vehicle_no)
            if not is_valid:
                flash('Vehicle number must be in the format AB12CD3456 (2 letters, 2 numbers, 2 letters, 4 numbers).', 'danger')
                return redirect(url_for('auth.register'))
            
            # First check if vehicle number is assigned to another user (case insensitive)
            all_users = User.query.all()
            for user in all_users:
                if user.vehicle_no and normalize_vehicle_number(user.vehicle_no) == normalized_vehicle_no:
                    flash('Vehicle number already registered. Please use a different vehicle number.', 'danger')
                    return redirect(url_for('auth.register'))
            
            # Then check if the vehicle is currently parked (in an active reservation)
            all_active_reservations = ParkingReservation.query.filter_by(active=True).all()
            for reservation in all_active_reservations:
                if normalize_vehicle_number(reservation.vehicle_no) == normalized_vehicle_no:
                    flash('This vehicle is currently parked. It cannot be registered until it is released.', 'danger')
                    return redirect(url_for('auth.register'))
        
        new_user = User(
            username=username, 
            email=email, 
            password=password,
            full_name=full_name,
            address=address,
            pin_code=pin_code,
            phone=phone,
            vehicle_no=normalized_vehicle_no  # Use the normalized version
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('auth.register'))
        
    return render_template('auth/register.html')

@auth.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate email domain
        is_valid_domain, domain_message = validate_email_domain(email)
        if not is_valid_domain:
            flash(domain_message, 'danger')
            return redirect(url_for('auth.admin_login'))
        
        user = User.query.filter_by(email=email, is_admin=True).first()
        
        if not user or not user.check_password(password):
            flash('Invalid admin credentials.', 'danger')
            return redirect(url_for('auth.admin_login'))
        
        login_user(user)
        return redirect(url_for('admin.dashboard'))
        
    return render_template('auth/admin_login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))