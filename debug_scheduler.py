"""
Debug scheduler for parking app.
This script will show the currently scheduled jobs and test the reminder functionality.
"""

from flask import Flask
from app import create_app
import logging
import sys
from datetime import datetime
from jobs.scheduler import scheduler, send_daily_reminders
from models import IST

# Setup logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Create the Flask app
app = create_app()

# Function to display scheduler info
def display_scheduler_info():
    print("\n===== SCHEDULER INFORMATION =====")
    print(f"Scheduler running: {scheduler.running}")
    
    # Get scheduler state
    state = {
        "running": scheduler.running,
        "timezone": scheduler._scheduler.timezone
    }
    print(f"Scheduler state: {state}")
    
    # List all jobs
    print("\n----- SCHEDULED JOBS -----")
    jobs = scheduler.get_jobs()
    if not jobs:
        print("No jobs scheduled!")
    
    for job in jobs:
        print(f"Job ID: {job.id}")
        print(f"    Function: {job.func}")
        print(f"    Trigger: {job.trigger}")
        print(f"    Next run: {job.next_run_time}")
        print()

# Function to test daily reminders
def test_daily_reminder():
    print("\n===== TESTING DAILY REMINDER =====")
    print(f"Current time (IST): {datetime.now(IST)}")
    
    # Run the daily_reminders function directly
    with app.app_context():
        print("Executing send_daily_reminders function...")
        result = send_daily_reminders(app)
        print("Daily reminders function executed")
        
    return result

if __name__ == "__main__":
    with app.app_context():
        display_scheduler_info()
        test_daily_reminder() 