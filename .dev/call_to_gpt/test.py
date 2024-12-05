import os
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Twilio credentials
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
phone_number = os.getenv("PERSONAL_PHONE_NUMBER")
jw = "+46720170950"
brian = ""
kai = "+46737176463"

# Initialize Twilio client
client = Client(account_sid, auth_token)

# Make the call
try:
    call = client.calls.create(
        url="http://demo.twilio.com/docs/voice.xml",  # URL containing TwiML instructions
        to=jw,  # Replace with the recipient's phone number
        from_=phone_number,  # Replace with your Twilio phone number
    )
    print(f"Call initiated successfully. Call SID: {call.sid}")
except Exception as e:
    print(f"Error occurred: {e}")
