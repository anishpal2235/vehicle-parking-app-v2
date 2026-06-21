"""
Test script for scheduler jobs.
Run specific scheduler jobs directly to verify they work correctly.
"""

from app import create_app
import logging
import sys
import argparse
from datetime import datetime
from jobs.scheduler import send_daily_reminders, generate_monthly_reports, cleanup_old_files
from models import IST

# Setup logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Create the Flask app
app = create_app()

def test_daily_reminders():
    print(f"\n=== Testing daily reminders at {datetime.now(IST)} ===")
    with app.app_context():
        send_daily_reminders(app)
    print("=== Daily reminders test complete ===\n")

def test_monthly_reports():
    print(f"\n=== Testing monthly reports at {datetime.now(IST)} ===")
    with app.app_context():
        generate_monthly_reports(app)
    print("=== Monthly reports test complete ===\n")

def test_cleanup_old_files():
    print(f"\n=== Testing cleanup of old files at {datetime.now(IST)} ===")
    with app.app_context():
        cleanup_old_files(app)
    print("=== Cleanup test complete ===\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test scheduler jobs directly.')
    parser.add_argument('job', choices=['daily', 'monthly', 'cleanup', 'all'], 
                        help='Which scheduler job to test')
    
    args = parser.parse_args()
    
    if args.job == 'daily' or args.job == 'all':
        test_daily_reminders()
        
    if args.job == 'monthly' or args.job == 'all':
        test_monthly_reports()
        
    if args.job == 'cleanup' or args.job == 'all':
        test_cleanup_old_files() 