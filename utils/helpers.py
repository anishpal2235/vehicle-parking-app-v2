from datetime import datetime, timezone, timedelta

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def calculate_parking_cost(start_time, end_time, hourly_rate):
    """
    Calculate the parking cost based on the start and end times and hourly rate.
    
    Args:
        start_time (datetime): The time when the vehicle was parked
        end_time (datetime): The time when the vehicle was removed
        hourly_rate (float): The cost per hour
    
    Returns:
        float: The total parking cost
    """
    if not start_time or not end_time:
        return 0
    
    # Calculate duration in hours
    duration = (end_time - start_time).total_seconds() / 3600
    
    # Calculate cost
    cost = duration * hourly_rate
    
    return round(cost, 2)

def format_datetime(dt):
    """
    Format a datetime object as a string.
    
    Args:
        dt (datetime): The datetime to format
    
    Returns:
        str: The formatted datetime string
    """
    if not dt:
        return ""
    
    # Ensure datetime is in IST
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    elif dt.tzinfo != IST:
        dt = dt.astimezone(IST)
        
    return dt.strftime("%Y-%m-%d %H:%M:%S IST")

def get_time_difference(start_time, end_time=None):
    """
    Get the time difference between two datetime objects.
    
    Args:
        start_time (datetime): The start time
        end_time (datetime, optional): The end time. Defaults to current time.
    
    Returns:
        str: The formatted time difference
    """
    if not start_time:
        return ""
    
    if not end_time:
        end_time = datetime.now(IST)
    
    # Ensure both datetimes are timezone-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=IST)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=IST)
    
    # Calculate difference in seconds
    diff_seconds = (end_time - start_time).total_seconds()
    
    # Convert to hours and minutes
    hours = int(diff_seconds // 3600)
    minutes = int((diff_seconds % 3600) // 60)
    
    if hours > 0:
        return f"{hours} hours, {minutes} minutes"
    else:
        return f"{minutes} minutes"

def normalize_phone_number(phone):
    """
    Normalize phone numbers for comparison by extracting the last 10 digits.
    
    This function handles various phone formats:
    - +country_code<digits> (e.g., +919876543210)
    - +country_code-<digits> (e.g., +91-9876543210)
    - 0<digits> (e.g., 09876543210)
    
    Args:
        phone (str): The phone number string
        
    Returns:
        str: The last 10 digits of the phone number, or empty string if invalid
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    digits_only = ''.join(c for c in phone if c.isdigit())
    
    # Extract the last 10 digits if there are at least 10 digits
    if len(digits_only) >= 10:
        return digits_only[-10:]
    
    # Return empty string for invalid numbers
    return ""

def validate_vehicle_format(vehicle_no):
    """
    Validate that a vehicle number matches the required format: AB12CD3456
    (2 letters, 2 numbers, 2 letters, 4 numbers)
    
    Args:
        vehicle_no (str): The vehicle number to validate
        
    Returns:
        tuple: (is_valid, normalized_vehicle_no) where:
               - is_valid is a boolean indicating if the format is valid
               - normalized_vehicle_no is the uppercase version of the input if valid, or None if invalid
    """
    import re
    
    if not vehicle_no:
        return (False, None)
    
    # Define the pattern: 2 letters, 2 numbers, 2 letters, 4 numbers
    pattern = r'^[A-Za-z]{2}\d{2}[A-Za-z]{2}\d{4}$'
    
    # Check if the vehicle number matches the pattern
    is_valid = bool(re.match(pattern, vehicle_no))
    
    # If valid, return the normalized (uppercase) version
    if is_valid:
        return (True, vehicle_no.upper())
    
    return (False, None)

# Add a utility function to normalize a vehicle number without validation
def normalize_vehicle_number(vehicle_no):
    """
    Normalize a vehicle number to uppercase for consistent comparison.
    
    Args:
        vehicle_no (str): The vehicle number to normalize
        
    Returns:
        str: The uppercase version of the vehicle number, or empty string if None
    """
    if not vehicle_no:
        return ""
    
    return vehicle_no.upper()

def validate_email_domain(email):
    """
    Validate that an email's domain is in the list of allowed domains.
    
    Args:
        email (str): The email address to validate
        
    Returns:
        tuple: (is_valid, message) where:
               - is_valid is a boolean indicating if the domain is valid
               - message is a string explaining why it's invalid (if applicable)
    """
    if not email or '@' not in email:
        return (False, "Invalid email format")
    
    # List of allowed domains
    valid_domains = [
        'gmail.com', 
        'yahoo.com', 
        'outlook.com',
        'hotmail.com',
        'icloud.com',
        'aol.com',
        'mail.com',
        'protonmail.com',
        'zoho.com',
        'yandex.com',
        'parking.com'  # Company domain
    ]
    
    # Extract domain from email
    domain = email.split('@')[1].lower()
    
    # Check if domain is in the allowed list
    if domain in valid_domains:
        return (True, "")
    
    return (False, f"Email domain '{domain}' is not allowed. Please use one of the following domains: {', '.join(valid_domains)}")
