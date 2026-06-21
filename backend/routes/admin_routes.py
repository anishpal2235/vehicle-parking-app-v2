from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, ParkingLot, ParkingSpot, User, ParkingReservation, IST
from sqlalchemy import func
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

admin = Blueprint('admin', __name__)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    parking_lots = ParkingLot.query.all()
    total_spots = ParkingSpot.query.count()
    available_spots = ParkingSpot.query.filter_by(status='A').count()
    occupied_spots = ParkingSpot.query.filter_by(status='O').count()
    total_users = User.query.filter_by(is_admin=False).count()
    
    # Get recent reservations
    recent_reservations = ParkingReservation.query.order_by(ParkingReservation.parking_timestamp.desc()).limit(5).all()
    
    # Get revenue data for the last 7 days
    revenue_data = []
    revenue_labels = []
    
    for i in range(6, -1, -1):
        date = datetime.now(IST) - timedelta(days=i)
        start_of_day = datetime(date.year, date.month, date.day, tzinfo=IST)
        end_of_day = start_of_day + timedelta(days=1)
        
        daily_revenue = db.session.query(func.sum(ParkingReservation.parking_cost))\
            .filter(ParkingReservation.parking_timestamp >= start_of_day)\
            .filter(ParkingReservation.parking_timestamp < end_of_day)\
            .scalar() or 0
            
        revenue_data.append(round(float(daily_revenue), 2))
        revenue_labels.append(start_of_day.strftime('%Y-%m-%d'))
    
    # Get total revenue
    total_revenue = db.session.query(func.sum(ParkingReservation.parking_cost))\
        .filter(ParkingReservation.parking_cost.isnot(None))\
        .scalar() or 0
    
    # Round the total revenue to 2 decimal places
    total_revenue = round(float(total_revenue), 2)
    
    # Get active reservations count
    active_reservations = ParkingReservation.query.filter_by(active=True).count()
    
    # Get data for charts
    lot_data = []
    for lot in parking_lots:
        total_lot_spots = len(lot.spots)
        available_lot_spots = sum(1 for spot in lot.spots if spot.status == 'A')
        occupied_lot_spots = sum(1 for spot in lot.spots if spot.status == 'O')
        
        lot_data.append({
            'name': lot.name,
            'total': total_lot_spots,
            'available': available_lot_spots,
            'occupied': occupied_lot_spots
        })
    
    return render_template(
        'admin/dashboard.html', 
        parking_lots=parking_lots,
        total_spots=total_spots,
        available_spots=available_spots,
        occupied_spots=occupied_spots,
        total_users=total_users,
        lot_data=lot_data,
        recent_reservations=recent_reservations,
        revenue_labels=revenue_labels,
        revenue_data=revenue_data,
        total_revenue=total_revenue,
        active_reservations=active_reservations
    )

@admin.route('/parking-lots')
@login_required
@admin_required
def parking_lots():
    lots = ParkingLot.query.all()
    return render_template('admin/parking_lots.html', parking_lots=lots)

@admin.route('/create-parking-lot', methods=['GET', 'POST'])
@login_required
@admin_required
def create_parking_lot():
    if request.method == 'POST':
        name = request.form.get('name')
        prime_location_name = request.form.get('prime_location_name')
        price = float(request.form.get('price'))
        address = request.form.get('address')
        pin_code = request.form.get('pin_code')
        max_spots = int(request.form.get('max_spots'))
        
        new_lot = ParkingLot(
            name=name,
            prime_location_name=prime_location_name,
            price=price,
            address=address,
            pin_code=pin_code,
            maximum_number_of_spots=max_spots
        )
        
        db.session.add(new_lot)
        db.session.commit()
        
        # Create parking spots for this lot
        for i in range(1, max_spots + 1):
            spot = ParkingSpot(lot_id=new_lot.id, spot_number=i, status='A')
            db.session.add(spot)
        
        db.session.commit()
        flash(f'Parking lot "{name}" created successfully with {max_spots} spots.', 'success')
        return redirect(url_for('admin.parking_lots'))
        
    return render_template('admin/create_parking_lot.html')

@admin.route('/edit-parking-lot/<int:lot_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    
    if request.method == 'POST':
        lot.name = request.form.get('name')
        lot.prime_location_name = request.form.get('prime_location_name')
        lot.price = float(request.form.get('price'))
        lot.address = request.form.get('address')
        lot.pin_code = request.form.get('pin_code')
        new_max_spots = int(request.form.get('max_spots'))
        
        current_spots = len(lot.spots)
        
        if new_max_spots > current_spots:
            # Add more spots
            for i in range(current_spots + 1, new_max_spots + 1):
                spot = ParkingSpot(lot_id=lot.id, spot_number=i, status='A')
                db.session.add(spot)
        elif new_max_spots < current_spots:
            # Remove excess spots, but first check if they're occupied
            spots_to_remove = ParkingSpot.query.filter_by(lot_id=lot.id).order_by(ParkingSpot.spot_number.desc()).limit(current_spots - new_max_spots).all()
            
            for spot in spots_to_remove:
                if spot.status == 'O':
                    flash(f'Cannot reduce spots as spot #{spot.spot_number} is currently occupied.', 'danger')
                    return redirect(url_for('admin.edit_parking_lot', lot_id=lot_id))
                db.session.delete(spot)
        
        lot.maximum_number_of_spots = new_max_spots
        db.session.commit()
        
        flash(f'Parking lot "{lot.name}" updated successfully.', 'success')
        return redirect(url_for('admin.parking_lots'))
        
    return render_template('admin/edit_parking_lot.html', lot=lot)

@admin.route('/delete-parking-lot/<int:lot_id>')
@login_required
@admin_required
def delete_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    
    # Check if any spots are occupied
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='O').count()
    
    if occupied_spots > 0:
        flash(f'Cannot delete parking lot "{lot.name}" as {occupied_spots} spots are currently occupied.', 'danger')
        return redirect(url_for('admin.parking_lots'))
    
    db.session.delete(lot)
    db.session.commit()
    
    flash(f'Parking lot "{lot.name}" deleted successfully.', 'success')
    return redirect(url_for('admin.parking_lots'))

@admin.route('/view-parking-spots/<int:lot_id>')
@login_required
@admin_required
def view_parking_spots(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).order_by(ParkingSpot.spot_number).all()
    
    # Get active reservations for occupied spots
    spot_reservations = {}
    for spot in spots:
        if spot.status == 'O':
            reservation = ParkingReservation.query.filter_by(spot_id=spot.id, active=True).first()
            if reservation:
                user = User.query.get(reservation.user_id)
                spot_reservations[spot.id] = {
                    'user': user.username,
                    'parking_time': reservation.parking_timestamp
                }
    
    return render_template('admin/view_parking_spots.html', lot=lot, spots=spots, spot_reservations=spot_reservations)

@admin.route('/delete-parking-spot/<int:spot_id>')
@login_required
@admin_required
def delete_parking_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot_id = spot.lot_id
    
    if spot.status == 'O':
        flash(f'Cannot delete spot #{spot.spot_number} as it is currently occupied.', 'danger')
        return redirect(url_for('admin.view_parking_spots', lot_id=lot_id))
    
    # Update spot numbers for all spots after this one
    later_spots = ParkingSpot.query.filter(
        ParkingSpot.lot_id == lot_id,
        ParkingSpot.spot_number > spot.spot_number
    ).order_by(ParkingSpot.spot_number).all()
    
    for later_spot in later_spots:
        later_spot.spot_number -= 1
    
    # Update the maximum number of spots in the lot
    lot = ParkingLot.query.get(lot_id)
    lot.maximum_number_of_spots -= 1
    
    db.session.delete(spot)
    db.session.commit()
    
    flash(f'Parking spot #{spot.spot_number} deleted successfully.', 'success')
    return redirect(url_for('admin.view_parking_spots', lot_id=lot_id))

@admin.route('/view-users')
@login_required
@admin_required
def view_users():
    users = User.query.filter_by(is_admin=False).all()
    
    # Get active reservations for each user
    user_reservations = {}
    for user in users:
        active_reservations = ParkingReservation.query.filter_by(user_id=user.id, active=True).all()
        if active_reservations:
            user_reservations[user.id] = []
            for reservation in active_reservations:
                spot = ParkingSpot.query.get(reservation.spot_id)
                lot = ParkingLot.query.get(spot.lot_id)
                
                # Calculate the duration
                now = datetime.now(IST)
                start_time = reservation.parking_timestamp
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=IST)
                
                diff_seconds = (now - start_time).total_seconds()
                hours = int(diff_seconds // 3600)
                minutes = int((diff_seconds % 3600) // 60)
                duration = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                
                user_reservations[user.id].append({
                    'lot_name': lot.name,
                    'lot_id': lot.id,
                    'spot_number': spot.spot_number,
                    'parking_time': reservation.parking_timestamp,
                    'duration': duration
                })
    
    return render_template('admin/view_users.html', users=users, user_reservations=user_reservations)

@admin.route('/api/parking-stats')
@login_required
@admin_required
def parking_stats_api():
    # Get stats for all parking lots
    lots = ParkingLot.query.all()
    stats = []
    
    for lot in lots:
        total_spots = len(lot.spots)
        available_spots = sum(1 for spot in lot.spots if spot.status == 'A')
        occupied_spots = sum(1 for spot in lot.spots if spot.status == 'O')
        
        stats.append({
            'name': lot.name,
            'total': total_spots,
            'available': available_spots,
            'occupied': occupied_spots
        })
    
    return jsonify(stats)

@admin.route('/delete-user/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Check if user has active reservations
    if user.active_reservations > 0:
        flash(f'Cannot delete user "{user.username}" as they have active reservations.', 'danger')
        return redirect(url_for('admin.view_users'))
        
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User "{user.username}" deleted successfully.', 'success')
    return redirect(url_for('admin.view_users'))

@admin.route('/force-release-spot/<int:spot_id>')
@login_required
@admin_required
def force_release_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot_id = spot.lot_id
    
    if spot.status == 'A':
        flash(f'Spot #{spot.spot_number} is already available.', 'info')
        return redirect(url_for('admin.view_parking_spots', lot_id=lot_id))
        
    # Find the active reservation for this spot
    reservation = ParkingReservation.query.filter_by(spot_id=spot.id, active=True).first()
    
    if not reservation:
        # This case should ideally not happen if status is 'O', but handle it defensively
        spot.status = 'A'
        db.session.commit()
        flash(f'No active reservation found for spot #{spot.spot_number}, setting it to available.', 'warning')
        return redirect(url_for('admin.view_parking_spots', lot_id=lot_id))
    
    # Mark the reservation as inactive
    reservation.active = False
    reservation.leaving_timestamp = datetime.now(IST)
    
    # Calculate parking duration in hours
    duration = (reservation.leaving_timestamp - reservation.parking_timestamp.replace(tzinfo=IST)).total_seconds() / 3600
    
    # Get the lot information for the price
    lot = ParkingLot.query.get(lot_id)
    
    # Calculate parking cost
    reservation.parking_cost = lot.price * duration
    
    # Update spot status to available
    spot.status = 'A'
    
    db.session.commit()
    
    flash(f'Spot #{spot.spot_number} force-released. User {reservation.user.username} charged ${reservation.parking_cost:.2f}', 'success')
    return redirect(url_for('admin.view_parking_spots', lot_id=lot_id))

@admin.route('/summary')
@login_required
@admin_required
def summary():
    # 1. Revenue per Parking Lot (for Pie Chart)
    revenue_by_lot = db.session.query(
        ParkingLot.name, 
        func.sum(ParkingReservation.parking_cost)
    ).join(ParkingSpot, ParkingSpot.lot_id == ParkingLot.id)\
     .join(ParkingReservation, ParkingReservation.spot_id == ParkingSpot.id)\
     .filter(ParkingReservation.parking_cost.isnot(None))\
     .group_by(ParkingLot.name)\
     .all()
    
    lot_names = [item[0] for item in revenue_by_lot]
    lot_revenues = [round(float(item[1] or 0), 2) for item in revenue_by_lot]

    # 2. Overall Spot Status (for Doughnut/Bar Chart)
    total_available_spots = ParkingSpot.query.filter_by(status='A').count()
    total_occupied_spots = ParkingSpot.query.filter_by(status='O').count()
    spot_status_labels = ['Available', 'Occupied']
    spot_status_data = [total_available_spots, total_occupied_spots]
    
    # 3. Free spots per parking lot (for Bar Chart)
    parking_lots = ParkingLot.query.all()
    free_spots_per_lot = []
    booked_spots_per_lot = []
    all_lot_names = []
    
    for lot in parking_lots:
        all_lot_names.append(lot.name)
        free_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        booked_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
        free_spots_per_lot.append(free_spots)
        booked_spots_per_lot.append(booked_spots)
    
    return render_template(
        'admin/summary.html', 
        lot_names=lot_names,
        lot_revenues=lot_revenues,
        spot_status_labels=spot_status_labels,
        spot_status_data=spot_status_data,
        all_lot_names=all_lot_names,
        free_spots_per_lot=free_spots_per_lot,
        booked_spots_per_lot=booked_spots_per_lot
    )

@admin.route('/edit-profile', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        # Check if username is already taken by another user
        existing_user = User.query.filter(User.username == username, User.id != current_user.id).first()
        if existing_user:
            flash('Username already taken. Please choose another one.', 'danger')
            return redirect(url_for('admin.edit_profile'))
            
        # Check if email is already taken by another user
        existing_email = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_email:
            flash('Email already registered. Please use another email.', 'danger')
            return redirect(url_for('admin.edit_profile'))
        
        # Update user profile
        current_user.username = username
        current_user.email = email
        
        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/edit_profile.html', admin=current_user, User=User, ParkingLot=ParkingLot)

@admin.route('/change-password', methods=['POST'])
@login_required
@admin_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Verify current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('admin.edit_profile'))
    
    # Check if new passwords match
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('admin.edit_profile'))
    
    # Update password
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    flash('Your password has been updated successfully!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin.route('/view-parking-spot/<int:spot_id>')
@login_required
@admin_required
def view_parking_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot = ParkingLot.query.get(spot.lot_id)
    
    # Get active reservation for occupied spot
    active_reservation = None
    if spot.status == 'O':
        active_reservation = ParkingReservation.query.filter_by(spot_id=spot.id, active=True).first()
        if active_reservation:
            user = User.query.get(active_reservation.user_id)
            active_reservation.user = user
    
    return render_template('admin/view_parking_spot.html', spot=spot, lot=lot, active_reservation=active_reservation)

@admin.route('/delete-parking-spot-ajax/<int:spot_id>')
@login_required
@admin_required
def delete_parking_spot_ajax(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot_id = spot.lot_id
    
    # Check if spot is occupied
    if spot.status == 'O':
        return jsonify({
            'success': False,
            'message': f'Cannot delete spot #{spot.spot_number} as it is currently occupied.'
        })
    
    # Update spot numbers for all spots after this one
    later_spots = ParkingSpot.query.filter(
        ParkingSpot.lot_id == lot_id,
        ParkingSpot.spot_number > spot.spot_number
    ).order_by(ParkingSpot.spot_number).all()
    
    for later_spot in later_spots:
        later_spot.spot_number -= 1
    
    # Update the maximum number of spots in the lot
    lot = ParkingLot.query.get(lot_id)
    lot.maximum_number_of_spots -= 1
    
    db.session.delete(spot)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Parking spot #{spot.spot_number} deleted successfully.',
        'redirect_url': url_for('admin.view_parking_spots', lot_id=lot_id)
    })

@admin.route('/view-occupied-spot/<int:spot_id>')
@login_required
@admin_required
def view_occupied_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    
    # Ensure spot is occupied
    if spot.status != 'O':
        flash('This parking spot is not currently occupied.', 'warning')
        return redirect(url_for('admin.view_parking_spot', spot_id=spot.id))
    
    # Get the active reservation
    reservation = ParkingReservation.query.filter_by(spot_id=spot.id, active=True).first()
    if not reservation:
        # This is an inconsistent state - spot marked as occupied but no active reservation
        # Try to find the most recent reservation for this spot
        last_reservation = ParkingReservation.query.filter_by(spot_id=spot.id).order_by(ParkingReservation.parking_timestamp.desc()).first()
        
        if last_reservation:
            # Fix the inconsistency - reactivate the most recent reservation
            last_reservation.active = True
            db.session.commit()
            flash('Fixed inconsistent reservation state.', 'warning')
            reservation = last_reservation
        else:
            flash('No active reservation found for this spot. The spot status has been reset.', 'warning')
            # Reset the spot status
            spot.status = 'A'
            db.session.commit()
            return redirect(url_for('admin.view_parking_spot', spot_id=spot.id))
    
    # Get user and lot information
    user = User.query.get(reservation.user_id)
    lot = ParkingLot.query.get(spot.lot_id)
    
    # Handle case where user was deleted
    if not user:
        flash('The user associated with this reservation no longer exists.', 'warning')
        return redirect(url_for('admin.view_parking_spot', spot_id=spot.id))
    
    # Get all users and determine sequential ID for the current user
    all_users = User.query.filter_by(is_admin=False).order_by(User.id).all()
    sequential_id = 0
    for i, u in enumerate(all_users):
        if u.id == user.id:
            sequential_id = i + 1  # +1 to start from 1 instead of 0
            break
    
    # Calculate estimated parking cost
    now = datetime.now(IST)
    duration_hours = (now - reservation.parking_timestamp.replace(tzinfo=IST)).total_seconds() / 3600
    estimated_cost = lot.price * duration_hours
    
    # If reservation is missing vehicle number but user has one, update it
    if (not reservation.vehicle_no or reservation.vehicle_no.strip() == '') and user.vehicle_no:
        reservation.vehicle_no = user.vehicle_no
        db.session.commit()
        flash('Updated missing vehicle number from user profile.', 'info')
    
    return render_template(
        'admin/view_occupied_spot.html', 
        spot=spot, 
        lot=lot, 
        reservation=reservation, 
        user=user,
        estimated_cost=round(estimated_cost, 2),
        sequential_id=sequential_id
    )

@admin.route('/search', methods=['GET', 'POST'])
@login_required
@admin_required
def search():
    search_type = request.args.get('search_type', '')
    search_term = request.args.get('search_term', '')
    results = None
    
    if search_type and search_term:
        if search_type == 'user_id':
            # Search by user ID
            try:
                user_id = int(search_term)
                results = {
                    'type': 'users',
                    'data': User.query.filter_by(id=user_id, is_admin=False).all()
                }
            except ValueError:
                flash('User ID must be a number', 'warning')
        
        elif search_type == 'user_email':
            # Search by user email
            results = {
                'type': 'users',
                'data': User.query.filter(User.email.like(f'%{search_term}%'), User.is_admin==False).all()
            }
            
        elif search_type == 'user_name':
            # Search by user name
            results = {
                'type': 'users',
                'data': User.query.filter((User.username.like(f'%{search_term}%') | 
                                          User.full_name.like(f'%{search_term}%')), 
                                          User.is_admin==False).all()
            }
            
        elif search_type == 'parking_location':
            # Search parking lots by location
            results = {
                'type': 'parking_lots',
                'data': ParkingLot.query.filter(
                    (ParkingLot.name.like(f'%{search_term}%')) | 
                    (ParkingLot.prime_location_name.like(f'%{search_term}%')) |
                    (ParkingLot.address.like(f'%{search_term}%'))
                ).all()
            }
            
            # Prepare additional data for each lot
            if results['data']:
                for lot in results['data']:
                    # Count available and occupied spots
                    available_spots = sum(1 for spot in lot.spots if spot.status == 'A')
                    occupied_spots = sum(1 for spot in lot.spots if spot.status == 'O')
                    lot.available_spots_count = available_spots
                    lot.occupied_spots_count = occupied_spots
        
        elif search_type == 'spot_number':
            # Search by spot number
            try:
                spot_number = int(search_term)
                spots = ParkingSpot.query.filter_by(spot_number=spot_number).all()
                
                # Get related parking lots
                lot_ids = [spot.lot_id for spot in spots]
                parking_lots = ParkingLot.query.filter(ParkingLot.id.in_(lot_ids)).all()
                
                # Map spots to their lots
                for lot in parking_lots:
                    lot.matching_spots = [spot for spot in spots if spot.lot_id == lot.id]
                    
                    # Count available and occupied spots
                    available_spots = sum(1 for spot in lot.spots if spot.status == 'A')
                    occupied_spots = sum(1 for spot in lot.spots if spot.status == 'O')
                    lot.available_spots_count = available_spots
                    lot.occupied_spots_count = occupied_spots
                
                results = {
                    'type': 'parking_lots_with_spots',
                    'data': parking_lots
                }
            except ValueError:
                flash('Spot number must be a number', 'warning')
        
        elif search_type == 'active_reservations':
            # Search for active reservations
            active_reservations = ParkingReservation.query.filter_by(active=True).all()
            
            # Group by user
            users_with_reservations = {}
            for reservation in active_reservations:
                if reservation.user_id not in users_with_reservations:
                    user = User.query.get(reservation.user_id)
                    if user and not user.is_admin:
                        users_with_reservations[user.id] = user
                        user.active_reservation_count = 0
                    
                if reservation.user_id in users_with_reservations:
                    users_with_reservations[reservation.user_id].active_reservation_count += 1
            
            results = {
                'type': 'users',
                'data': list(users_with_reservations.values())
            }
    
    # Get data for search dropdowns
    search_options = [
        {'value': 'user_id', 'label': 'User ID'},
        {'value': 'user_email', 'label': 'User Email'},
        {'value': 'user_name', 'label': 'User Name'},
        {'value': 'parking_location', 'label': 'Parking Location'},
        {'value': 'spot_number', 'label': 'Spot Number'},
        {'value': 'active_reservations', 'label': 'Active Reservations'}
    ]
    
    return render_template(
        'admin/search.html',
        search_type=search_type,
        search_term=search_term,
        search_options=search_options,
        results=results
    )