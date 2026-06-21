from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
import os
from flask_login import login_required, current_user
from models import db, ParkingLot, ParkingSpot, ParkingReservation, User, IST, SavedPaymentMethod
from datetime import datetime
from sqlalchemy import func
from utils.helpers import normalize_phone_number, validate_vehicle_format, normalize_vehicle_number, validate_email_domain
from jobs import trigger_csv_export

user = Blueprint('user', __name__)

@user.route('/dashboard')
@login_required
def dashboard():
    # Get user's active reservations
    active_reservations = ParkingReservation.query.filter_by(user_id=current_user.id, active=True).all()
    
    reservation_details = []
    for res in active_reservations:
        spot = ParkingSpot.query.get(res.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
        
        # Calculate the current cost for active reservations
        now = datetime.now(IST)
        duration = (now - res.parking_timestamp.replace(tzinfo=IST)).total_seconds() / 3600
        current_cost = lot.price * duration

        reservation_details.append({
            'reservation_id': res.id,
            'lot_name': lot.name,
            'spot_number': spot.spot_number,
            'parking_time': res.parking_timestamp,
            'hourly_rate': lot.price,
            'payment_status': res.payment_status,
            'parking_cost': round(current_cost, 2) if lot.price > 0 else 0
        })
    
    # Get user's recent reservations (both active and inactive)
    recent_reservations = ParkingReservation.query.filter_by(user_id=current_user.id).order_by(ParkingReservation.parking_timestamp.desc()).limit(5).all()
    
    past_reservation_details = []
    for res in recent_reservations:
        spot = ParkingSpot.query.get(res.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
        
        # Calculate duration in hours
        duration = (res.leaving_timestamp - res.parking_timestamp).total_seconds() / 3600 if res.leaving_timestamp else 0
        
        # For completed reservations without a cost, calculate it
        cost = res.parking_cost
        if not res.active and not cost and res.leaving_timestamp:
            cost = lot.price * duration
        
        past_reservation_details.append({
            'reservation_id': res.id,
            'lot_name': lot.name,
            'spot_number': spot.spot_number,
            'lot_location': lot.prime_location_name,
            'vehicle_no': res.vehicle_no,
            'parking_time': res.parking_timestamp,
            'leaving_time': res.leaving_timestamp,
            'duration': round(duration, 2) if res.leaving_timestamp else 0,
            'cost': round(cost, 2) if cost else cost,
            'is_active': res.active,
            'payment_status': res.payment_status
        })
    
    # Get summary data for charts
    total_reservations = ParkingReservation.query.filter_by(user_id=current_user.id).count()
    active_count = len(active_reservations)
    past_count = ParkingReservation.query.filter_by(user_id=current_user.id, active=False).count()
    
    # Get total spent on parking
    total_spent = db.session.query(func.sum(ParkingReservation.parking_cost)).filter_by(user_id=current_user.id, active=False).scalar() or 0
    
    # Round total spent to two decimal places
    total_spent = round(float(total_spent), 2)
    
    return render_template(
        'user/dashboard.html',
        active_reservations=reservation_details,
        past_reservations=past_reservation_details,
        total_reservations=total_reservations,
        active_count=active_count,
        past_count=past_count,
        total_spent=total_spent
    )

@user.route('/search-parking')
@login_required
def search_parking():
    search_term = request.args.get('location', '')
    
    if not search_term:
        flash('Please enter a location or pin code to search.', 'warning')
        return redirect(url_for('user.dashboard'))
    
    # Search for parking lots by location name or pin code
    lots = ParkingLot.query.filter(
        db.or_(
            ParkingLot.prime_location_name.ilike(f'%{search_term}%'),
            ParkingLot.address.ilike(f'%{search_term}%'),
            ParkingLot.pin_code == search_term
        )
    ).all()
    
    return render_template('user/search_results.html', lots=lots, search_term=search_term)

@user.route('/book-spot', methods=['GET', 'POST'])
@login_required
def book_spot():
    if request.method == 'POST':
        lot_id = request.form.get('lot_id')
        vehicle_no = request.form.get('vehicle_no', '')
        spot_id = request.form.get('spot_id', None)  # New parameter for spot selection
        
        if not lot_id:
            flash('Please select a parking lot.', 'danger')
            return redirect(url_for('user.book_spot'))
            
        if not vehicle_no:
            flash('Please enter a vehicle number.', 'danger')
            return redirect(url_for('user.book_spot'))
        
        # Validate and normalize vehicle number
        is_valid, normalized_vehicle_no = validate_vehicle_format(vehicle_no)
        if not is_valid:
            flash('Vehicle number must be in the format AB12CD3456 (2 letters, 2 numbers, 2 letters, 4 numbers).', 'danger')
            return redirect(url_for('user.book_spot'))
        
        try:
            # Check if vehicle is already parked somewhere else (case insensitive)
            all_active_reservations = ParkingReservation.query.filter_by(active=True).all()
            for reservation in all_active_reservations:
                if normalize_vehicle_number(reservation.vehicle_no) == normalized_vehicle_no:
                    # Check if it's by another user
                    if reservation.user_id != current_user.id:
                        flash('This vehicle is already parked by another user. It cannot be used until it is released.', 'danger')
                        return redirect(url_for('user.book_spot'))
                    # Check if it's by the current user
                    else:
                        flash('This vehicle is already parked in another spot. Please release that spot first.', 'danger')
                        return redirect(url_for('user.book_spot'))
            
            # If spot_id is provided, use that specific spot, otherwise find the first available spot
            if spot_id:
                selected_spot = ParkingSpot.query.get(spot_id)
                if not selected_spot or selected_spot.lot_id != int(lot_id) or selected_spot.status != 'A':
                    flash('The selected spot is no longer available.', 'danger')
                    return redirect(url_for('user.book_spot'))
                available_spot = selected_spot
            else:
                # Find the first available spot in the selected lot
                available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
            
            if not available_spot:
                flash('No available spots in the selected parking lot.', 'danger')
                return redirect(url_for('user.book_spot'))
            
            # Create a new reservation with normalized vehicle number
            new_reservation = ParkingReservation(
                user_id=current_user.id,
                spot_id=available_spot.id,
                vehicle_no=normalized_vehicle_no,
                parking_timestamp=datetime.now(IST),
                active=True
            )
            
            # Update spot status to occupied
            available_spot.status = 'O'
            
            # Update user's vehicle number if it's not set or different (case insensitive)
            if not current_user.vehicle_no or normalize_vehicle_number(current_user.vehicle_no) != normalized_vehicle_no:
                # Check if this vehicle number is already registered to another user (case insensitive)
                all_users = User.query.filter(User.id != current_user.id).all()
                for user in all_users:
                    if user.vehicle_no and normalize_vehicle_number(user.vehicle_no) == normalized_vehicle_no:
                        flash('This vehicle number is already registered to another user. Please use a different vehicle number.', 'danger')
                        return redirect(url_for('user.book_spot'))
                
                current_user.vehicle_no = normalized_vehicle_no
                
            # Add and commit in two steps to catch any potential errors
            db.session.add(new_reservation)
            db.session.flush()  # Flush to get the ID without committing
            
            db.session.commit()  # Final commit if all is well
            
            lot = ParkingLot.query.get(lot_id)
            flash(f'Spot #{available_spot.spot_number} in {lot.name} booked successfully.', 'success')
        except Exception as e:
            # Log the error
            print(f"Error during booking: {str(e)}")
            db.session.rollback()
            flash('An error occurred during booking. Please try again.', 'danger')
            
        return redirect(url_for('user.dashboard'))
    
    # Get all parking lots with available spots
    available_lots = db.session.query(ParkingLot).join(ParkingSpot).filter(ParkingSpot.status == 'A').group_by(ParkingLot.id).all()
    
    # Get current time for template
    current_time = datetime.now(IST)
    
    return render_template('user/book_spot.html', available_lots=available_lots, current_time=current_time)

@user.route('/release-spot/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def release_spot(reservation_id):
    reservation = ParkingReservation.query.get_or_404(reservation_id)
    
    # Ensure the reservation belongs to the current user
    if reservation.user_id != current_user.id:
        flash('You do not have permission to access this reservation.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        # Mark the reservation as inactive
        reservation.active = False
        reservation.leaving_timestamp = datetime.now(IST)
        
        # Calculate parking duration in hours
        duration = (reservation.leaving_timestamp - reservation.parking_timestamp.replace(tzinfo=IST)).total_seconds() / 3600
        
        # Get the spot and lot information
        spot = ParkingSpot.query.get(reservation.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
        
        # Calculate parking cost - ensure it's not null or 0 when there should be a cost
        if lot.price > 0 and duration > 0:
            reservation.parking_cost = lot.price * duration
        else:
            # Even for free parking, set a 0 value instead of null
            reservation.parking_cost = 0.0
            
        # Set initial payment status
        if reservation.parking_cost > 0:
            reservation.payment_status = 'PENDING'
        else:
            reservation.payment_status = 'PAID'  # Free parking is considered paid
        
        # Update spot status to available
        spot.status = 'A'
        
        db.session.commit()
        
        # Format the cost message appropriately
        if reservation.parking_cost > 0:
            flash(f'Parking spot released. Cost: ${reservation.parking_cost:.2f}', 'success')
        else:
            flash('Parking spot released. No charge for this reservation.', 'success')
        return redirect(url_for('user.dashboard'))
    
    # Get the spot and lot information for display
    spot = ParkingSpot.query.get(reservation.spot_id)
    lot = ParkingLot.query.get(spot.lot_id)
    
    # Calculate current duration and estimated cost
    now = datetime.now(IST)
    duration = (now - reservation.parking_timestamp.replace(tzinfo=IST)).total_seconds() / 3600
    estimated_cost = lot.price * duration
    
    return render_template(
        'user/release_spot.html',
        reservation=reservation,
        spot=spot,
        lot=lot,
        now=now,
        duration=duration,
        estimated_cost=estimated_cost,
        current_user=current_user
    )

@user.route('/view-history')
@login_required
def view_history():
    reservations = ParkingReservation.query.filter_by(user_id=current_user.id, active=False).order_by(ParkingReservation.leaving_timestamp.desc()).all()
    
    history = []
    for res in reservations:
        spot = ParkingSpot.query.get(res.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
        
        # Calculate duration in hours
        duration = (res.leaving_timestamp - res.parking_timestamp).total_seconds() / 3600
        
        # Calculate cost if it's not already set
        cost = res.parking_cost
        if cost is None or cost == 0:
            # Only calculate a new cost if the lot has a price
            if lot.price > 0:
                cost = lot.price * duration
            else:
                cost = 0
                
        history.append({
            'lot_name': lot.name,
            'spot_number': spot.spot_number,
            'parking_time': res.parking_timestamp,
            'leaving_time': res.leaving_timestamp,
            'duration': round(duration, 2),
            'cost': round(cost, 2) if cost is not None else 0,
            'vehicle_no': res.vehicle_no
        })
    
    return render_template('user/view_history.html', history=history)

@user.route('/api/user-stats')
@login_required
def user_stats_api():
    # Get counts for active and past reservations
    active_count = ParkingReservation.query.filter_by(user_id=current_user.id, active=True).count()
    past_count = ParkingReservation.query.filter_by(user_id=current_user.id, active=False).count()
    
    # Get total spent on parking
    total_spent = db.session.query(func.sum(ParkingReservation.parking_cost)).filter_by(user_id=current_user.id, active=False).scalar() or 0
    
    # Get monthly spending data
    monthly_spending = {}
    
    # This is a simplified approach - for a real app you'd want to use SQL functions to extract month/year
    past_reservations = ParkingReservation.query.filter_by(user_id=current_user.id, active=False).all()
    
    for res in past_reservations:
        month_year = res.leaving_timestamp.strftime("%B %Y")
        if month_year in monthly_spending:
            monthly_spending[month_year] += res.parking_cost
        else:
            monthly_spending[month_year] = res.parking_cost
    
    # Convert to list of dictionaries for easier chart rendering
    monthly_data = [{"month": k, "amount": v} for k, v in monthly_spending.items()]
    
    return jsonify({
        "active_reservations": active_count,
        "past_reservations": past_count,
        "total_spent": round(total_spent, 2),
        "monthly_spending": monthly_data
    })

@user.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        pin_code = request.form.get('pin_code', '')
        vehicle_no = request.form.get('vehicle_no', '')
        
        # Validate email domain
        is_valid_domain, domain_message = validate_email_domain(email)
        if not is_valid_domain:
            flash(domain_message, 'danger')
            return redirect(url_for('user.edit_profile'))
        
        # Check if username is already taken by another user
        existing_user = User.query.filter(User.username == username, User.id != current_user.id).first()
        if existing_user:
            flash('Username already taken. Please choose another one.', 'danger')
            return redirect(url_for('user.edit_profile'))
            
        # Check if email is already taken by another user
        existing_email = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_email:
            flash('Email already registered. Please use another email.', 'danger')
            return redirect(url_for('user.edit_profile'))
        
        # Check if phone number is already taken by another user using normalized comparison
        if phone:
            normalized_phone = normalize_phone_number(phone)
            if normalized_phone:
                # Get all users and compare normalized phone numbers
                users = User.query.filter(User.id != current_user.id).all()
                for user in users:
                    if user.phone and normalize_phone_number(user.phone) == normalized_phone:
                        flash('Phone number already registered. Please use a different phone number.', 'danger')
                        return redirect(url_for('user.edit_profile'))
        
        # Validate and normalize vehicle number
        normalized_vehicle_no = None
        if vehicle_no:
            is_valid, normalized_vehicle_no = validate_vehicle_format(vehicle_no)
            if not is_valid:
                flash('Vehicle number must be in the format AB12CD3456 (2 letters, 2 numbers, 2 letters, 4 numbers).', 'danger')
                return redirect(url_for('user.edit_profile'))
                
            # Skip further checks if the vehicle number hasn't changed (case-insensitive)
            if current_user.vehicle_no and normalize_vehicle_number(current_user.vehicle_no) == normalized_vehicle_no:
                normalized_vehicle_no = current_user.vehicle_no  # Keep the existing one
            else:
                # Check if vehicle is registered to another user (case insensitive)
                all_users = User.query.filter(User.id != current_user.id).all()
                for user in all_users:
                    if user.vehicle_no and normalize_vehicle_number(user.vehicle_no) == normalized_vehicle_no:
                        flash('Vehicle number already registered. Please use a different vehicle number.', 'danger')
                        return redirect(url_for('user.edit_profile'))
                
                # Check if vehicle is parked by another user (case insensitive)
                all_active_reservations = ParkingReservation.query.filter_by(active=True).all()
                for reservation in all_active_reservations:
                    if (normalize_vehicle_number(reservation.vehicle_no) == normalized_vehicle_no and 
                        reservation.user_id != current_user.id):
                        flash('This vehicle is currently parked by another user. It cannot be added to your profile until it is released.', 'danger')
                        return redirect(url_for('user.edit_profile'))
        
        try:
            # Update user profile
            current_user.username = username
            current_user.email = email
            
            # Update phone if User model has phone field
            has_phone_attr = hasattr(User, 'phone')
            if has_phone_attr:
                current_user.phone = phone
            
            # Update address, pin code, and vehicle number
            current_user.address = address
            current_user.pin_code = pin_code
            current_user.vehicle_no = normalized_vehicle_no
            
            db.session.commit()
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('user.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile. Please try again.', 'danger')
            return redirect(url_for('user.edit_profile'))
    
    # Check if User model has phone field
    has_phone_attr = hasattr(User, 'phone')
    phone_value = getattr(current_user, 'phone', '') if has_phone_attr else ''
    
    return render_template(
        'user/edit_profile.html', 
        user=current_user,
        has_phone_attr=has_phone_attr,
        phone_value=phone_value
    )

@user.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Verify current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('user.edit_profile'))
    
    # Check if new passwords match
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('user.edit_profile'))
    
    # Update password
    from werkzeug.security import generate_password_hash
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    flash('Your password has been updated successfully!', 'success')
    return redirect(url_for('user.dashboard'))

@user.route('/summary')
@login_required
def summary():
    # Get all past reservations
    past_reservations = ParkingReservation.query.filter_by(user_id=current_user.id, active=False).order_by(ParkingReservation.leaving_timestamp).all()
    
    # 1. Monthly usage count
    monthly_usage = {}
    
    # 2. Usage by parking lot
    usage_by_lot = {}
    
    # 3. Monthly spending
    monthly_spending = {}
    
    # 4. Time spent by lot (in hours)
    time_by_lot = {}
    
    for res in past_reservations:
        # Get the month-year string
        month_year = res.leaving_timestamp.strftime("%b %Y")
        
        # Get the lot name
        spot = ParkingSpot.query.get(res.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
        lot_name = lot.name
        
        # Calculate duration in hours
        duration = (res.leaving_timestamp - res.parking_timestamp).total_seconds() / 3600
        
        # Calculate cost if not already set
        cost = res.parking_cost
        if cost is None:
            # Calculate based on lot price and duration
            cost = lot.price * duration
        
        # Update monthly usage count
        if month_year in monthly_usage:
            monthly_usage[month_year] += 1
        else:
            monthly_usage[month_year] = 1
            
        # Update usage by lot
        if lot_name in usage_by_lot:
            usage_by_lot[lot_name] += 1
        else:
            usage_by_lot[lot_name] = 1
            
        # Update monthly spending
        if month_year in monthly_spending:
            monthly_spending[month_year] += cost
        else:
            monthly_spending[month_year] = cost
            
        # Update time spent by lot
        if lot_name in time_by_lot:
            time_by_lot[lot_name] += duration
        else:
            time_by_lot[lot_name] = duration
    
    # Sort monthly data chronologically
    sorted_months = sorted(monthly_usage.keys(), key=lambda x: datetime.strptime(x, "%b %Y"))
    
    # Prepare data for charts
    monthly_usage_labels = sorted_months
    monthly_usage_data = [monthly_usage[month] for month in sorted_months]
    
    lot_names = list(usage_by_lot.keys())
    lot_usage_data = [usage_by_lot[lot] for lot in lot_names]
    
    monthly_spending_data = [round(monthly_spending.get(month, 0), 2) for month in sorted_months]
    
    time_by_lot_data = [round(time_by_lot[lot], 2) for lot in lot_names]
    
    # Get total stats
    total_reservations = len(past_reservations)
    total_spent = round(sum(res.parking_cost or 0 for res in past_reservations), 2)
    total_hours = round(sum((res.leaving_timestamp - res.parking_timestamp).total_seconds() / 3600 for res in past_reservations), 2)
    most_visited_lot = max(usage_by_lot.items(), key=lambda x: x[1])[0] if usage_by_lot else "None"
    
    return render_template(
        'user/summary.html',
        monthly_usage_labels=monthly_usage_labels,
        monthly_usage_data=monthly_usage_data,
        lot_names=lot_names,
        lot_usage_data=lot_usage_data,
        monthly_spending_data=monthly_spending_data,
        time_by_lot_data=time_by_lot_data,
        total_reservations=total_reservations,
        total_spent=total_spent,
        total_hours=total_hours,
        most_visited_lot=most_visited_lot
    )

@user.route('/book-form/<int:lot_id>')
@login_required
def book_form(lot_id):
    # Get the parking lot
    lot = ParkingLot.query.get_or_404(lot_id)
    
    # Find all available spots in the lot
    available_spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').order_by(ParkingSpot.spot_number).all()
    
    if not available_spots:
        flash('No available spots in the selected parking lot.', 'danger')
        return redirect(url_for('user.search_parking'))
    
    # Current timestamp
    now = datetime.now(IST)
    
    return render_template(
        'user/book_form.html',
        lot=lot,
        available_spots=available_spots,
        now=now,
        current_user=current_user
    )

@user.route('/confirm-booking', methods=['POST'])
@login_required
def confirm_booking():
    spot_id = request.form.get('spot_id')
    vehicle_no = request.form.get('vehicle_no')
    
    # Validate data
    if not spot_id or not vehicle_no:
        flash('Missing required information.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    # Validate and normalize vehicle number
    is_valid, normalized_vehicle_no = validate_vehicle_format(vehicle_no)
    if not is_valid:
        flash('Vehicle number must be in the format AB12CD3456 (2 letters, 2 numbers, 2 letters, 4 numbers).', 'danger')
        return redirect(url_for('user.dashboard'))
    
    # Get the spot
    spot = ParkingSpot.query.get_or_404(spot_id)
    
    # Check if spot is still available
    if spot.status != 'A':
        flash('Sorry, this spot has been booked by someone else.', 'danger')
        return redirect(url_for('user.search_parking'))
    
    try:
        # Check if vehicle is already parked somewhere (case insensitive)
        all_active_reservations = ParkingReservation.query.filter_by(active=True).all()
        for reservation in all_active_reservations:
            if normalize_vehicle_number(reservation.vehicle_no) == normalized_vehicle_no:
                # Check if it's by another user
                if reservation.user_id != current_user.id:
                    flash('This vehicle is already parked by another user. It cannot be used until it is released.', 'danger')
                    return redirect(url_for('user.dashboard'))
                # If it's by current user
                else:
                    flash('This vehicle is already parked in another spot. Please release that spot first.', 'danger')
                    return redirect(url_for('user.dashboard'))
                
        # Check if vehicle belongs to another user (case insensitive)
        current_user_vehicle_normalized = normalize_vehicle_number(current_user.vehicle_no) if current_user.vehicle_no else None
        if current_user_vehicle_normalized != normalized_vehicle_no:
            all_users = User.query.filter(User.id != current_user.id).all()
            for user in all_users:
                if user.vehicle_no and normalize_vehicle_number(user.vehicle_no) == normalized_vehicle_no:
                    flash('This vehicle number is registered to another user. Please use your own vehicle.', 'danger')
                    return redirect(url_for('user.dashboard'))
                
        # Create a new reservation with normalized vehicle number
        new_reservation = ParkingReservation(
            user_id=current_user.id,
            spot_id=spot.id,
            vehicle_no=normalized_vehicle_no,
            parking_timestamp=datetime.now(IST),
            active=True
        )
        
        # Update user's vehicle number if it's not set or different
        if not current_user.vehicle_no or current_user_vehicle_normalized != normalized_vehicle_no:
            current_user.vehicle_no = normalized_vehicle_no
        
        # Update spot status to occupied
        spot.status = 'O'
        
        db.session.add(new_reservation)
        db.session.commit()
        
        lot = ParkingLot.query.get(spot.lot_id)
        flash(f'Spot #{spot.spot_number} in {lot.name} booked successfully.', 'success')
    except Exception as e:
        # Log the error
        print(f"Error during booking: {str(e)}")
        db.session.rollback()
        flash('An error occurred during booking. Please try again.', 'danger')
    
    return redirect(url_for('user.dashboard'))

@user.route('/api/available-spots/<int:lot_id>')
@login_required
def available_spots_api(lot_id):
    """
    API endpoint to get available spots for a parking lot.
    Returns a JSON response with available spots.
    """
    print(f"API endpoint called for lot_id: {lot_id}")
    
    # Find all available spots in the lot
    available_spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').order_by(ParkingSpot.spot_number).all()
    
    # Convert to a list of dictionaries
    spots_data = []
    for spot in available_spots:
        spots_data.append({
            'id': spot.id,
            'spot_number': spot.spot_number,
            'status': spot.status
        })
    
    print(f"Found {len(spots_data)} available spots")
    
    return jsonify({
        'success': True,
        'lot_id': lot_id,
        'spots': spots_data,
        'count': len(spots_data)
    })

@user.route('/export-csv', methods=['GET', 'POST'])
@login_required
def export_csv():
    """Export parking data as CSV"""
    if request.method == 'POST':
        # Trigger the CSV export job
        export_path = trigger_csv_export(current_app._get_current_object(), current_user.id)
        
        if export_path:
            flash('Your CSV export is being prepared. You will receive an email when it is ready.', 'success')
        else:
            flash('Failed to generate CSV export. Please try again.', 'danger')
            
        return redirect(url_for('user.dashboard'))
        
    return render_template('user/export_csv.html')

@user.route('/download-monthly-report', methods=['GET', 'POST'])
@login_required
def download_monthly_report():
    """Download monthly activity report in user's preferred format"""
    if request.method == 'POST':
        # Get user's preferred report format
        report_format = getattr(current_user, 'report_format', 'html')
        
        # Override with form selection if provided
        if request.form.get('report_format'):
            report_format = request.form.get('report_format')
        
        # Get report period (current month or previous month)
        report_period = request.form.get('report_period', 'current')
        
        try:
            from services.report_service import ReportService
            report_service = ReportService(current_app._get_current_object())
            
            if report_period == 'previous':
                # Generate previous month report
                report_path = report_service.generate_monthly_activity_report(current_user, report_format)
            else:
                # Generate current month report
                report_path = report_service.generate_current_month_report(current_user, report_format)
            
            if report_path and os.path.exists(report_path):
                # Return the file for download
                filename = os.path.basename(report_path)
                
                if report_format.lower() == 'pdf':
                    return send_file(
                        report_path,
                        as_attachment=True,
                        download_name=filename,
                        mimetype='application/pdf'
                    )
                else:
                    return send_file(
                        report_path,
                        as_attachment=True,
                        download_name=filename,
                        mimetype='text/html'
                    )
            else:
                flash('Failed to generate report. Please try again.', 'danger')
                
        except Exception as e:
            current_app.logger.error(f"Error generating monthly report: {str(e)}")
            flash('An error occurred while generating your report. Please try again.', 'danger')
            
        return redirect(url_for('user.dashboard'))
        
    # Get current and previous month names for the template
    from datetime import datetime
    current_date = datetime.now()
    
    # Current month
    current_month = current_date.strftime('%B %Y')
    
    # Previous month
    if current_date.month == 1:
        previous_month = f"December {current_date.year - 1}"
    else:
        prev_date = current_date.replace(month=current_date.month - 1)
        previous_month = prev_date.strftime('%B %Y')
    
    return render_template('user/download_monthly_report.html', 
                         current_month=current_month, 
                         previous_month=previous_month)

@user.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    """User preferences page"""
    if request.method == 'POST':
        # Get form data
        notification_preference = request.form.get('notification_preference', 'email')
        gchat_email = request.form.get('gchat_email', '')
        reminder_time = request.form.get('reminder_time', '18:00')
        report_format = request.form.get('report_format', 'html')
        
        # Check if reminder time has changed
        reminder_time_changed = current_user.reminder_time != reminder_time
        
        # Update user preferences
        current_user.notification_preference = notification_preference
        current_user.gchat_email = gchat_email
        current_user.reminder_time = reminder_time
        current_user.report_format = report_format
        
        # If reminder time changed, reset the last reminder date so user can receive reminders at new time
        if reminder_time_changed:
            current_user.last_reminder_date = None
        
        try:
            db.session.commit()
            
            # Send confirmation email
            try:
                from services.email_service import EmailService
                email_service = EmailService(current_app)
                
                subject = "Preferences Updated - Parking Management System"
                html_content = f"""
                <html>
                    <head>
                        <style>
                            body {{
                                font-family: 'Segoe UI', Arial, sans-serif;
                                line-height: 1.6;
                                color: #333;
                                max-width: 600px;
                                margin: 0 auto;
                                padding: 20px;
                            }}
                            .container {{
                                background-color: #f9f9f9;
                                border-radius: 8px;
                                overflow: hidden;
                                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                            }}
                            .header {{
                                background-color: #28a745;
                                color: white;
                                padding: 20px;
                                text-align: center;
                            }}
                            .content {{
                                padding: 20px;
                                background-color: white;
                            }}
                            .preference-item {{
                                margin: 10px 0;
                                padding: 10px;
                                background-color: #f8f9fa;
                                border-radius: 4px;
                            }}
                            .reminder-notice {{
                                background-color: #fff3cd;
                                border: 1px solid #ffeaa7;
                                border-radius: 4px;
                                padding: 15px;
                                margin: 15px 0;
                                color: #856404;
                            }}
                            .footer {{
                                background-color: #f5f5f5;
                                padding: 15px;
                                text-align: center;
                                font-size: 12px;
                                color: #666;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>Preferences Updated Successfully!</h1>
                                <p>Your parking preferences have been updated</p>
                            </div>
                            <div class="content">
                                <p>Hello {current_user.full_name or current_user.username},</p>
                                <p>Your parking preferences have been successfully updated. Here are your current settings:</p>
                                
                                <div class="preference-item">
                                    <strong>Notification Preference:</strong> {notification_preference.title()}
                                </div>
                                <div class="preference-item">
                                    <strong>Daily Reminder Time:</strong> {reminder_time}
                                </div>
                                <div class="preference-item">
                                    <strong>Monthly Report Format:</strong> {report_format.upper()}
                                </div>
                                {f'<div class="preference-item"><strong>Google Chat Email:</strong> {gchat_email}</div>' if gchat_email else ''}
                                
                                {f'<div class="reminder-notice"><strong>🕐 Reminder Time Changed!</strong><br>Your daily reminder time has been updated to {reminder_time}. You will now receive reminders at this new time every day.</div>' if reminder_time_changed else ''}
                                
                                <p>These preferences will be used for:</p>
                                <ul>
                                    <li>Daily parking reminders</li>
                                    <li>Monthly activity reports</li>
                                    <li>Important notifications</li>
                                </ul>
                                
                                <p>If you didn't make these changes, please contact support immediately.</p>
                            </div>
                            <div class="footer">
                                <p>Thank you for using our Parking Management System!</p>
                                <p>This email was sent to {current_user.email}</p>
                            </div>
                        </div>
                    </body>
                </html>
                """
                
                email_service.send_email(current_user.email, subject, html_content)
                
                current_app.logger.info(f"Confirmation email sent successfully to {current_user.email} for preferences update")
                
                if reminder_time_changed:
                    flash('Your preferences have been updated successfully! A confirmation email has been sent. You will now receive daily reminders at ' + reminder_time + '.', 'success')
                else:
                    flash('Your preferences have been updated successfully and a confirmation email has been sent.', 'success')
                
            except Exception as email_error:
                # Log the email error but don't fail the preferences update
                current_app.logger.error(f"Failed to send confirmation email to {current_user.email}: {str(email_error)}")
                current_app.logger.error(f"Email error type: {type(email_error).__name__}")
                print(f"Failed to send confirmation email: {email_error}")
                flash('Your preferences have been updated successfully, but the confirmation email could not be sent.', 'success')
                
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your preferences. Please try again.', 'danger')
            
        return redirect(url_for('user.preferences'))
        
    return render_template('user/preferences.html')

@user.route('/payment/<int:reservation_id>', methods=['GET'])
@login_required
def payment(reservation_id):
    """Display payment form for a reservation"""
    # Get reservation details
    reservation = ParkingReservation.query.get_or_404(reservation_id)
    
    # Make sure the reservation belongs to the user
    if reservation.user_id != current_user.id:
        flash('You are not authorized to view this payment.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    # Get spot and lot information
    spot = ParkingSpot.query.get(reservation.spot_id)
    lot = ParkingLot.query.get(spot.lot_id)
    
    # Current time for duration calculations
    now = datetime.now(IST)
    
    # Ensure parking_timestamp is timezone-aware by attaching IST timezone
    parking_time = reservation.parking_timestamp
    if parking_time.tzinfo is None:
        parking_time = parking_time.replace(tzinfo=IST)
    
    # Ensure leaving_timestamp is timezone-aware
    release_time = reservation.leaving_timestamp
    if release_time and release_time.tzinfo is None:
        release_time = release_time.replace(tzinfo=IST)
    
    # Calculate actual parking duration in hours
    if release_time:
        # If the reservation has been released, use the release time
        duration = (release_time - parking_time).total_seconds() / 3600
    else:
        # Otherwise, calculate based on current time
        duration = (now - parking_time).total_seconds() / 3600
    
    # Calculate the correct amount based on current duration
    calculated_amount = lot.price * duration
    
    # Use the calculated amount or the stored amount, whichever is greater
    # This ensures we show the most up-to-date cost
    stored_amount = reservation.parking_cost or 0
    amount = max(calculated_amount, stored_amount)
    
    # Format amount to two decimal places
    amount = "{:.2f}".format(amount)
    
    # Get user's saved payment methods
    saved_methods = SavedPaymentMethod.query.filter_by(user_id=current_user.id).all()
    
    # Check if user has a default payment method
    has_default_method = any(method.is_default for method in saved_methods)
    
    # Create a more detailed reservation object for the template
    reservation_details = {
        'lot_name': lot.name,
        'spot_number': spot.spot_number,
        'parking_time': parking_time,
        'release_time': release_time,
        'vehicle_no': reservation.vehicle_no,
        'reservation_id': reservation.id,
        'duration_hours': round(duration, 2),
        'hourly_rate': lot.price
    }
    
    return render_template('user/payment.html', 
                          reservation_id=reservation_id,
                          amount=amount,
                          success=False,
                          saved_methods=saved_methods,
                          has_default_method=has_default_method,
                          reservation=reservation_details,
                          now=now)

@user.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    """Process a payment (dummy implementation)"""
    # Get form data
    reservation_id = request.form.get('reservation_id')
    amount = request.form.get('amount')
    payment_method = request.form.get('payment_method', 'card')
    save_payment = request.form.get('save_payment') == '1'
    
    # Debug: Log all form data to help identify issues
    current_app.logger.info(f"Payment form data: {request.form}")
    
    # Check if using a saved payment method
    saved_method_id = request.form.get('saved_method_id')
    
    try:
        if saved_method_id:
            # Get the saved payment method
            saved_method = SavedPaymentMethod.query.get(saved_method_id)
            if saved_method and saved_method.user_id == current_user.id:
                payment_method = saved_method.payment_type
                # Update last used timestamp
                saved_method.last_used = datetime.now(IST)
                db.session.commit()
                
                # Log payment with saved method
                current_app.logger.info(f"Payment attempt using saved {payment_method} for reservation {reservation_id} | Amount: ${amount}")
            else:
                flash('Invalid payment method.', 'danger')
                return redirect(url_for('user.payment', reservation_id=reservation_id))
        else:
            # Process based on payment method type
            if payment_method == 'card':
                # Get and clean card details
                card_number = request.form.get('card_number', '')
                if card_number:
                    card_number = card_number.replace(" ", "")
                expiry_date = request.form.get('expiry_date', '')
                name_on_card = request.form.get('name_on_card', '')
                cvv = request.form.get('cvv', '')
                
                # Validate card details
                if not card_number or len(card_number) < 13:
                    current_app.logger.error(f"Invalid card number: {card_number}")
                    flash('Please enter a valid card number.', 'danger')
                    return redirect(url_for('user.payment', reservation_id=reservation_id))
                
                if not expiry_date or '/' not in expiry_date:
                    current_app.logger.error(f"Invalid expiry date: {expiry_date}")
                    flash('Please enter a valid expiry date (MM/YY).', 'danger')
                    return redirect(url_for('user.payment', reservation_id=reservation_id))
                
                if not cvv or len(cvv) < 3:
                    current_app.logger.error("Invalid CVV")
                    flash('Please enter a valid CVV.', 'danger')
                    return redirect(url_for('user.payment', reservation_id=reservation_id))
                
                if not name_on_card:
                    current_app.logger.error("Missing card holder name")
                    flash('Please enter the name on the card.', 'danger')
                    return redirect(url_for('user.payment', reservation_id=reservation_id))
                
                # Log payment attempt (but don't store sensitive data in production)
                current_app.logger.info(f"Card payment attempt for reservation {reservation_id} | Amount: ${amount}")
                
                # Save the payment method if requested
                if save_payment and card_number:
                    try:
                        # Determine card type based on first digit
                        card_type = 'Unknown'
                        if card_number.startswith('4'):
                            card_type = 'Visa'
                        elif card_number.startswith('5'):
                            card_type = 'Mastercard'
                        elif card_number.startswith('3'):
                            card_type = 'Amex'
                        elif card_number.startswith('6'):
                            card_type = 'Discover'
                        
                        # Check if this card is already saved (by last 4 digits)
                        last_four = card_number[-4:] if len(card_number) >= 4 else card_number
                        existing_card = SavedPaymentMethod.query.filter_by(
                            user_id=current_user.id, 
                            payment_type='card',
                            card_last_four=last_four
                        ).first()
                        
                        if existing_card:
                            # Update existing card
                            existing_card.card_holder_name = name_on_card
                            existing_card.card_expiry = expiry_date
                            existing_card.last_used = datetime.now(IST)
                            
                            db.session.commit()
                            flash('Payment method updated.', 'success')
                        else:
                            # Create new payment method
                            new_method = SavedPaymentMethod(
                                user_id=current_user.id,
                                payment_type='card',
                                card_last_four=last_four,
                                card_type=card_type,
                                card_holder_name=name_on_card,
                                card_expiry=expiry_date,
                                created_at=datetime.now(IST),
                                last_used=datetime.now(IST)
                            )
                            
                            # If this is the first payment method, set it as default
                            if SavedPaymentMethod.query.filter_by(user_id=current_user.id).count() == 0:
                                new_method.is_default = True
                            
                            db.session.add(new_method)
                            db.session.commit()
                            flash('Payment method saved for future use.', 'success')
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error saving payment method: {str(e)}")
                        flash('Could not save payment method.', 'warning')
            
            elif payment_method == 'upi':
                upi_id = request.form.get('upi_id', '')
                
                # Validate UPI ID
                if not upi_id or '@' not in upi_id:
                    current_app.logger.error(f"Invalid UPI ID: {upi_id}")
                    flash('Please enter a valid UPI ID.', 'danger')
                    return redirect(url_for('user.payment', reservation_id=reservation_id))
                
                # Log payment attempt
                current_app.logger.info(f"UPI payment attempt for reservation {reservation_id} | Amount: ${amount}")
                
                # Save the UPI ID if requested
                if save_payment and upi_id:
                    try:
                        # Check if this UPI ID is already saved
                        existing_upi = SavedPaymentMethod.query.filter_by(
                            user_id=current_user.id,
                            payment_type='upi',
                            upi_id=upi_id
                        ).first()
                        
                        if existing_upi:
                            # Update last used timestamp
                            existing_upi.last_used = datetime.now(IST)
                            db.session.commit()
                            flash('Payment method updated.', 'success')
                        else:
                            # Create new payment method
                            new_method = SavedPaymentMethod(
                                user_id=current_user.id,
                                payment_type='upi',
                                upi_id=upi_id,
                                created_at=datetime.now(IST),
                                last_used=datetime.now(IST)
                            )
                            
                            # If this is the first payment method, set it as default
                            if SavedPaymentMethod.query.filter_by(user_id=current_user.id).count() == 0:
                                new_method.is_default = True
                            
                            db.session.add(new_method)
                            db.session.commit()
                            flash('UPI ID saved for future use.', 'success')
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error saving UPI ID: {str(e)}")
                        flash('Could not save UPI ID.', 'warning')
        
        # Generate a fake transaction ID
        import random
        import string
        transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        
        # Update reservation payment status
        try:
            reservation = ParkingReservation.query.get(reservation_id)
            if reservation:
                # If the reservation is still active, mark it as inactive and release the spot
                if reservation.active:
                    # Get the spot and mark it as available
                    spot = ParkingSpot.query.get(reservation.spot_id)
                    if spot:
                        spot.status = 'A'  # 'A' means available

                    # Set leaving timestamp if not already set
                    if not reservation.leaving_timestamp:
                        reservation.leaving_timestamp = datetime.now(IST)
                    
                    # Mark reservation as inactive
                    reservation.active = False
                    
                    # Log the automatic release
                    current_app.logger.info(f"Spot automatically released after payment for reservation {reservation_id}")
                
                # Update payment status
                reservation.payment_status = 'PAID'
                reservation.payment_date = datetime.now(IST)
                reservation.payment_method = payment_method
                reservation.transaction_id = transaction_id
                
                # If parking_cost is not set or is zero but amount is higher, update it
                if (not reservation.parking_cost or reservation.parking_cost == 0) and float(amount) > 0:
                    reservation.parking_cost = float(amount)
                
                db.session.commit()
                
                # Log successful payment
                current_app.logger.info(f"Payment successful for reservation {reservation_id} | Transaction ID: {transaction_id}")
                
                if reservation.active:
                    flash('Payment was successful! You can now complete your parking session.', 'success')
                else:
                    flash('Payment was successful! Your parking session is now complete.', 'success')
            else:
                current_app.logger.error(f"Reservation {reservation_id} not found during payment processing")
                flash('Reservation not found.', 'danger')
                return redirect(url_for('user.dashboard'))
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing payment: {str(e)}")
            flash('An error occurred while processing your payment. Please try again.', 'danger')
            return redirect(url_for('user.payment', reservation_id=reservation_id))
        
        # Display success page
        return render_template('user/payment.html',
                            success=True,
                            amount=amount,
                            transaction_id=transaction_id)
                            
    except Exception as e:
        # Catch any unexpected errors
        current_app.logger.error(f"Unexpected error in payment processing: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'danger')
        return redirect(url_for('user.payment', reservation_id=reservation_id))

@user.route('/test-payment-form', methods=['GET', 'POST'])
@login_required
def test_payment_form():
    """A simple test form to debug CSRF issues"""
    if request.method == 'POST':
        # Just print the form data and return success
        current_app.logger.info(f"Test form data: {request.form}")
        return render_template('user/payment.html', success=True, amount="10.00", transaction_id="TEST123")
    
    # Display the test form
    return render_template('user/payment.html', amount="10.00", reservation_id="0", success=False)

@user.route('/payment-methods', methods=['GET', 'POST'])
@login_required
def payment_methods():
    """Manage saved payment methods"""
    if request.method == 'POST':
        action = request.form.get('action')
        method_id = request.form.get('method_id')
        
        # Delete a payment method
        if action == 'delete' and method_id:
            try:
                method = SavedPaymentMethod.query.get(method_id)
                if method and method.user_id == current_user.id:
                    db.session.delete(method)
                    db.session.commit()
                    flash('Payment method deleted successfully.', 'success')
                else:
                    flash('Invalid payment method.', 'danger')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error deleting payment method: {str(e)}")
                flash('An error occurred while deleting the payment method.', 'danger')
        
        # Set a payment method as default
        elif action == 'set_default' and method_id:
            try:
                # First, unset all existing defaults
                SavedPaymentMethod.query.filter_by(user_id=current_user.id, is_default=True).update({SavedPaymentMethod.is_default: False})
                
                # Then set the selected one as default
                method = SavedPaymentMethod.query.get(method_id)
                if method and method.user_id == current_user.id:
                    method.is_default = True
                    db.session.commit()
                    flash('Default payment method updated.', 'success')
                else:
                    db.session.rollback()
                    flash('Invalid payment method.', 'danger')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error setting default payment method: {str(e)}")
                flash('An error occurred while updating the default payment method.', 'danger')
        
        # Add a new payment method
        elif action == 'add':
            payment_type = request.form.get('payment_type')
            
            if payment_type == 'card':
                # Add card details
                card_number = request.form.get('card_number', '').replace(' ', '')
                card_holder = request.form.get('card_holder', '')
                expiry_date = request.form.get('expiry_date', '')
                
                try:
                    # Determine card type
                    card_type = 'Unknown'
                    if card_number.startswith('4'):
                        card_type = 'Visa'
                    elif card_number.startswith('5'):
                        card_type = 'Mastercard'
                    elif card_number.startswith('3'):
                        card_type = 'Amex'
                    elif card_number.startswith('6'):
                        card_type = 'Discover'
                    
                    # Store only last 4 digits
                    last_four = card_number[-4:] if len(card_number) >= 4 else card_number
                    
                    # Check for duplicate
                    existing = SavedPaymentMethod.query.filter_by(
                        user_id=current_user.id,
                        payment_type='card',
                        card_last_four=last_four
                    ).first()
                    
                    if existing:
                        flash('This card is already saved.', 'warning')
                    else:
                        new_method = SavedPaymentMethod(
                            user_id=current_user.id,
                            payment_type='card',
                            card_last_four=last_four,
                            card_type=card_type,
                            card_holder_name=card_holder,
                            card_expiry=expiry_date,
                            created_at=datetime.now(IST)
                        )
                        
                        # If first method, set as default
                        if SavedPaymentMethod.query.filter_by(user_id=current_user.id).count() == 0:
                            new_method.is_default = True
                        
                        db.session.add(new_method)
                        db.session.commit()
                        flash('Card added successfully.', 'success')
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error adding card: {str(e)}")
                    flash('An error occurred while adding the card.', 'danger')
            
            elif payment_type == 'upi':
                # Add UPI details
                upi_id = request.form.get('upi_id', '')
                
                try:
                    # Check for duplicate
                    existing = SavedPaymentMethod.query.filter_by(
                        user_id=current_user.id,
                        payment_type='upi',
                        upi_id=upi_id
                    ).first()
                    
                    if existing:
                        flash('This UPI ID is already saved.', 'warning')
                    else:
                        new_method = SavedPaymentMethod(
                            user_id=current_user.id,
                            payment_type='upi',
                            upi_id=upi_id,
                            created_at=datetime.now(IST)
                        )
                        
                        # If first method, set as default
                        if SavedPaymentMethod.query.filter_by(user_id=current_user.id).count() == 0:
                            new_method.is_default = True
                        
                        db.session.add(new_method)
                        db.session.commit()
                        flash('UPI ID added successfully.', 'success')
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error adding UPI ID: {str(e)}")
                    flash('An error occurred while adding the UPI ID.', 'danger')
    
    # Get all saved payment methods
    saved_methods = SavedPaymentMethod.query.filter_by(user_id=current_user.id).order_by(SavedPaymentMethod.is_default.desc()).all()
    
    return render_template('user/payment_methods.html', saved_methods=saved_methods)