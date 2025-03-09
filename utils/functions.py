import re

def validate_email(email):
    # Define the regular expression pattern for a valid email
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    
    # Match the email against the pattern
    if re.match(email_regex, email):
        return True
    else:
        return False