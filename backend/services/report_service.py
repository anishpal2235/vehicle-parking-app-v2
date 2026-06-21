import os
import csv
import logging
from datetime import datetime
from flask import render_template
from sqlalchemy import func
from models import db, ParkingReservation, ParkingSpot, ParkingLot, IST
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Create a logger for the module
logger = logging.getLogger(__name__)

# Import pandas only when needed
PANDAS_AVAILABLE = False
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass

class ReportService:
    def __init__(self, app=None):
        self.app = app
        
        # Create reports directory if it doesn't exist
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        reports_dir = os.path.join(base_dir, 'frontend', 'static', 'reports')
        exports_dir = os.path.join(base_dir, 'frontend', 'static', 'exports')
        
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(exports_dir, exist_ok=True)
        
        if not PANDAS_AVAILABLE and app:
            app.logger.warning("Pandas is not available. Some features may be limited.")
        
    def generate_monthly_activity_report(self, user, report_format='html'):
        """
        Generate a monthly activity report for a user
        
        Parameters:
        - user: User object
        - report_format: 'html' or 'pdf'
        
        Returns:
        - report_path: Path to the generated report
        """
        # Get current month data
        current_date = datetime.now(IST)
        first_day = datetime(current_date.year, current_date.month, 1, tzinfo=IST)
        
        # Previous month for the report
        if current_date.month == 1:
            prev_month = 12
            prev_year = current_date.year - 1
        else:
            prev_month = current_date.month - 1
            prev_year = current_date.year
            
        # First day of previous month
        first_day_prev_month = datetime(prev_year, prev_month, 1, tzinfo=IST)
        
        # Determine the last day of the previous month
        if prev_month == 12:
            last_day_prev_month = datetime(prev_year, prev_month, 31, 23, 59, 59, tzinfo=IST)
        else:
            # Calculate last day of month by getting first day of next month and subtracting 1 day
            next_month = 1 if prev_month == 12 else prev_month + 1
            next_month_year = prev_year + 1 if prev_month == 12 else prev_year
            
            # Get first day of next month, then subtract 1 day
            from datetime import timedelta
            first_day_next_month = datetime(next_month_year, next_month, 1, tzinfo=IST)
            last_day_prev_month = first_day_next_month - timedelta(seconds=1)
        
        # Log the date range to help with debugging
        if self.app:
            self.app.logger.info(f"Generating report for user {user.id} from {first_day_prev_month} to {last_day_prev_month}")
        else:
            logger.info(f"Generating report for user {user.id} from {first_day_prev_month} to {last_day_prev_month}")
        
        # Get all reservations for the previous month
        reservations = ParkingReservation.query.filter(
            ParkingReservation.user_id == user.id,
            ParkingReservation.parking_timestamp >= first_day_prev_month,
            ParkingReservation.parking_timestamp <= last_day_prev_month
        ).all()
        
        # Calculate summary data
        total_bookings = len(reservations)
        total_spent = sum(r.parking_cost or 0 for r in reservations)
        
        # Get the most used parking lot
        lot_usage = {}
        for reservation in reservations:
            spot = ParkingSpot.query.get(reservation.spot_id)
            lot = ParkingLot.query.get(spot.lot_id)
            lot_usage[lot.id] = lot_usage.get(lot.id, 0) + 1
        
        most_used_lot_id = max(lot_usage.items(), key=lambda x: x[1])[0] if lot_usage else None
        most_used_lot = ParkingLot.query.get(most_used_lot_id) if most_used_lot_id else None
        
        # Prepare reservation details for the report
        reservation_details = []
        for res in reservations:
            spot = ParkingSpot.query.get(res.spot_id)
            lot = ParkingLot.query.get(spot.lot_id)
            
            reservation_details.append({
                'date': res.parking_timestamp.strftime('%Y-%m-%d %H:%M'),
                'lot_name': lot.name,
                'spot_number': spot.spot_number,
                'duration': res.duration,
                'cost': res.parking_cost or 0
            })
            
        # Sort reservations by date (newest first)
        reservation_details.sort(key=lambda x: x['date'], reverse=True)
        
        # Generate the report
        month_name = first_day_prev_month.strftime('%B %Y')
        
        # Create report filename
        filename = f"monthly_report_{user.id}_{prev_year}_{prev_month}"
        
        if report_format.lower() == 'pdf':
            return self._generate_pdf_report(
                user, 
                month_name, 
                total_bookings, 
                total_spent, 
                most_used_lot, 
                reservation_details,
                filename
            )
        else:
            return self._generate_html_report(
                user, 
                month_name, 
                total_bookings, 
                total_spent, 
                most_used_lot, 
                reservation_details,
                filename
            )
    
    def generate_current_month_report(self, user, report_format='html'):
        """
        Generate a monthly activity report for the current month
        
        Parameters:
        - user: User object
        - report_format: 'html' or 'pdf'
        
        Returns:
        - report_path: Path to the generated report
        """
        # Get current month data
        current_date = datetime.now(IST)
        current_month = current_date.month
        current_year = current_date.year
        
        # First day of current month
        first_day = datetime(current_year, current_month, 1, tzinfo=IST)
        
        # Log the date range to help with debugging
        if self.app:
            self.app.logger.info(f"Generating CURRENT month report for user {user.id} from {first_day} to {current_date}")
        else:
            logger.info(f"Generating CURRENT month report for user {user.id} from {first_day} to {current_date}")
        
        # Get all reservations for the current month
        reservations = ParkingReservation.query.filter(
            ParkingReservation.user_id == user.id,
            ParkingReservation.parking_timestamp >= first_day,
            ParkingReservation.parking_timestamp <= current_date
        ).all()
        
        if self.app:
            self.app.logger.info(f"Found {len(reservations)} reservations for current month")
        else:
            logger.info(f"Found {len(reservations)} reservations for current month")
        
        # Print each reservation for debugging
        for res in reservations:
            logger.info(f"Reservation ID: {res.id}, Time: {res.parking_timestamp}, Cost: {res.parking_cost}")
        
        # Calculate summary data
        total_bookings = len(reservations)
        total_spent = sum(r.parking_cost or 0 for r in reservations)
        
        # Get the most used parking lot
        lot_usage = {}
        for reservation in reservations:
            spot = ParkingSpot.query.get(reservation.spot_id)
            lot = ParkingLot.query.get(spot.lot_id)
            lot_usage[lot.id] = lot_usage.get(lot.id, 0) + 1
        
        most_used_lot_id = max(lot_usage.items(), key=lambda x: x[1])[0] if lot_usage else None
        most_used_lot = ParkingLot.query.get(most_used_lot_id) if most_used_lot_id else None
        
        # Prepare reservation details for the report
        reservation_details = []
        for res in reservations:
            spot = ParkingSpot.query.get(res.spot_id)
            lot = ParkingLot.query.get(spot.lot_id)
            
            reservation_details.append({
                'date': res.parking_timestamp.strftime('%Y-%m-%d %H:%M'),
                'lot_name': lot.name,
                'spot_number': spot.spot_number,
                'duration': res.duration,
                'cost': res.parking_cost or 0
            })
            
        # Sort reservations by date (newest first)
        reservation_details.sort(key=lambda x: x['date'], reverse=True)
        
        # Generate the report
        month_name = current_date.strftime('%B %Y')
        
        # Create report filename with "current" indicator
        filename = f"current_monthly_report_{user.id}_{current_year}_{current_month}"
        
        if report_format.lower() == 'pdf':
            return self._generate_pdf_report(
                user, 
                month_name, 
                total_bookings, 
                total_spent, 
                most_used_lot, 
                reservation_details,
                filename
            )
        else:
            return self._generate_html_report(
                user, 
                month_name, 
                total_bookings, 
                total_spent, 
                most_used_lot, 
                reservation_details,
                filename
            )
            
    def _generate_html_report(self, user, month_name, total_bookings, total_spent, most_used_lot, reservation_details, filename):
        """Generate an HTML report"""
        if self.app:
            with self.app.app_context():
                html_content = render_template(
                    'reports/monthly_report.html',
                    user=user,
                    month_name=month_name,
                    total_bookings=total_bookings,
                    total_spent=total_spent,
                    most_used_lot=most_used_lot,
                    reservation_details=reservation_details,
                    generated_date=datetime.now(IST).strftime('%Y-%m-%d %H:%M')
                )
        else:
            # In case we don't have an app context, log a warning
            logger.warning("Generating HTML report outside of app context, template rendering might fail")
            try:
                html_content = render_template(
                    'reports/monthly_report.html',
                    user=user,
                    month_name=month_name,
                    total_bookings=total_bookings,
                    total_spent=total_spent,
                    most_used_lot=most_used_lot,
                    reservation_details=reservation_details,
                    generated_date=datetime.now(IST).strftime('%Y-%m-%d %H:%M')
                )
            except Exception as e:
                logger.error(f"Failed to render template: {str(e)}")
                # Create a simple HTML report as fallback
                html_content = f"""
                <html>
                    <body>
                        <h1>Monthly Parking Report - {month_name}</h1>
                        <p>User: {user.full_name} ({user.email})</p>
                        <p>Total Bookings: {total_bookings}</p>
                        <p>Total Spent: ${total_spent:.2f}</p>
                        <p>Generated on {datetime.now(IST).strftime('%Y-%m-%d %H:%M')}</p>
                    </body>
                </html>
                """
            
        # Save the HTML report
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        reports_dir = os.path.join(base_dir, 'frontend', 'static', 'reports')
        report_path = os.path.join(reports_dir, f"{filename}.html")
        
        with open(report_path, 'w') as f:
            f.write(html_content)
            
        return report_path
            
    def _generate_pdf_report(self, user, month_name, total_bookings, total_spent, most_used_lot, reservation_details, filename):
        """Generate a PDF report"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        reports_dir = os.path.join(base_dir, 'frontend', 'static', 'reports')
        report_path = os.path.join(reports_dir, f"{filename}.pdf")
        
        # Create PDF document
        doc = SimpleDocTemplate(report_path, pagesize=letter)
        elements = []
        
        # Set up styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Add title
        elements.append(Paragraph(f"Monthly Parking Activity Report - {month_name}", title_style))
        elements.append(Spacer(1, 0.25*inch))
        
        # Add user info
        elements.append(Paragraph(f"User: {user.full_name} ({user.email})", normal_style))
        elements.append(Paragraph(f"Generated on: {datetime.now(IST).strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.25*inch))
        
        # Add summary section
        elements.append(Paragraph("Summary", heading_style))
        
        summary_data = [
            ["Total Bookings", str(total_bookings)],
            ["Total Amount Spent", f"${total_spent:.2f}"],
            ["Most Used Parking Lot", most_used_lot.name if most_used_lot else "N/A"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.25*inch))
        
        # Add reservation details
        if reservation_details:
            elements.append(Paragraph("Reservation Details", heading_style))
            
            # Table header
            reservation_table_data = [["Date", "Parking Lot", "Spot #", "Duration", "Cost"]]
            
            # Table rows
            for res in reservation_details:
                reservation_table_data.append([
                    res['date'],
                    res['lot_name'],
                    str(res['spot_number']),
                    res['duration'],
                    f"${res['cost']:.2f}"
                ])
                
            reservation_table = Table(reservation_table_data, colWidths=[1.2*inch, 2*inch, 0.8*inch, 1*inch, 1*inch])
            reservation_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(reservation_table)
        else:
            elements.append(Paragraph("No reservations found for this month.", normal_style))
            
        # Build the PDF
        doc.build(elements)
        
        return report_path
        
    def generate_csv_export(self, user):
        """
        Generate a CSV export of all parking reservations for a user
        
        Parameters:
        - user: User object
        
        Returns:
        - export_path: Path to the generated CSV file
        """
        # Get all reservations for the user
        reservations = ParkingReservation.query.filter_by(user_id=user.id).all()
        
        # Prepare data for CSV
        csv_data = []
        for res in reservations:
            spot = ParkingSpot.query.get(res.spot_id)
            lot = ParkingLot.query.get(spot.lot_id)
            
            csv_data.append({
                'reservation_id': res.id,
                'parking_lot': lot.name,
                'spot_number': spot.spot_number,
                'vehicle_number': res.vehicle_no,
                'parking_time': res.parking_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'leaving_time': res.leaving_timestamp.strftime('%Y-%m-%d %H:%M:%S') if res.leaving_timestamp else 'Still Active',
                'duration': res.duration,
                'cost': res.parking_cost or 0,
                'status': 'Active' if res.active else 'Completed'
            })
            
        # Create filename with timestamp
        timestamp = datetime.now(IST).strftime('%Y%m%d%H%M%S')
        
        # Get the absolute path to the frontend/static/exports directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        exports_dir = os.path.join(base_dir, 'frontend', 'static', 'exports')
        
        # Ensure the exports directory exists
        os.makedirs(exports_dir, exist_ok=True)
        
        export_path = os.path.join(exports_dir, f"parking_data_{user.id}_{timestamp}.csv")
        
        # Write to CSV file
        with open(export_path, 'w', newline='') as csvfile:
            fieldnames = [
                'reservation_id', 'parking_lot', 'spot_number', 'vehicle_number',
                'parking_time', 'leaving_time', 'duration', 'cost', 'status'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in csv_data:
                writer.writerow(row)
                
        return export_path 