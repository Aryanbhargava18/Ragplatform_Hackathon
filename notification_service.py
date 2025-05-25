import os
import json
from datetime import datetime
import threading
import time
import random
import streamlit as st

# Use the Twilio blueprint for sending SMS
from twilio.rest import Client

# Development mode flag
DEV_MODE = False  # Set to False to enable production mode

def get_credentials():
    """Get credentials from either environment variables or Streamlit secrets"""
    try:
        # Try to get from Streamlit secrets first (for production)
        return {
            "account_sid": st.secrets.twilio.account_sid,
            "auth_token": st.secrets.twilio.auth_token,
            "from_number": st.secrets.twilio.from_number
        }
    except (AttributeError, KeyError):
        # Fallback to environment variables (for local development)
        return {
            "account_sid": os.environ.get("TWILIO_ACCOUNT_SID"),
            "auth_token": os.environ.get("TWILIO_AUTH_TOKEN"),
            "from_number": os.environ.get("TWILIO_FROM_NUMBER")
        }

# Global notification settings
notification_settings = {
    "sms_notifications_enabled": True,  # Enable SMS by default
    "notification_history": [],
    "dev_mode": DEV_MODE
}

# Notification history lock
history_lock = threading.Lock()

# Initialize Twilio credentials as None
TWILIO_ACCOUNT_SID = None
TWILIO_AUTH_TOKEN = None
TWILIO_FROM_NUMBER = None
NOTIFICATION_PHONE_NUMBER = None  # Will be set when user enters their number in the UI

def initialize_twilio_credentials():
    """Initialize Twilio credentials from environment or secrets"""
    global TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
    credentials = get_credentials()
    TWILIO_ACCOUNT_SID = credentials["account_sid"]
    TWILIO_AUTH_TOKEN = credentials["auth_token"]
    TWILIO_FROM_NUMBER = credentials["from_number"]

# Initialize credentials when module is loaded
initialize_twilio_credentials()

def send_sms_notification(message, document=None):
    """
    Send an SMS notification using Twilio
    """
    if notification_settings["dev_mode"]:
        print("\n=== Development Mode: SMS Notification ===")
        print(f"Message: {message}")
        if document:
            print(f"Document ID: {document.get('id', 'Unknown')}")
            print(f"Risk Score: {document.get('risk_score', 0):.2f}")
        print("==========================================\n")
        return True
        
    # Debug logging
    print("\n=== SMS Notification Debug ===")
    print(f"TWILIO_ACCOUNT_SID: {'Set' if TWILIO_ACCOUNT_SID else 'Not Set'}")
    print(f"TWILIO_AUTH_TOKEN: {'Set' if TWILIO_AUTH_TOKEN else 'Not Set'}")
    print(f"TWILIO_FROM_NUMBER: {TWILIO_FROM_NUMBER if TWILIO_FROM_NUMBER else 'Not Set'}")
    print(f"NOTIFICATION_PHONE_NUMBER: {NOTIFICATION_PHONE_NUMBER if NOTIFICATION_PHONE_NUMBER else 'Not Set'}")
    
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, NOTIFICATION_PHONE_NUMBER]):
        print("❌ Twilio credentials or phone number not fully configured")
        return False
    
    try:
        # Initialize the Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Prepare the message
        sms_message = message
        if document:
            sms_message += f"\nDoc ID: {document.get('id', 'Unknown')}"
            sms_message += f"\nRisk: {document.get('risk_score', 0):.2f}"
            sms_message += f"\nJurisdiction: {document.get('jurisdiction', 'Unknown')}"
        
        print(f"Sending SMS to: {NOTIFICATION_PHONE_NUMBER}")
        print(f"Message: {sms_message}")
        
        # Send the SMS
        twilio_message = client.messages.create(
            body=sms_message,
            from_=TWILIO_FROM_NUMBER,
            to=NOTIFICATION_PHONE_NUMBER
        )
        
        print(f"✅ SMS notification sent with SID: {twilio_message.sid}")
        return True
    
    except Exception as e:
        print(f"❌ Error sending SMS notification: {str(e)}")
        return False

def send_notification(message, document_id=None, risk_score=None):
    """
    Send a notification
    """
    # Prepare document info if provided
    document = None
    if document_id:
        document = {
            "id": document_id,
            "risk_score": risk_score if risk_score is not None else 0.8
        }
    
    # In development mode, we'll simulate notifications
    if notification_settings["dev_mode"]:
        print("\n=== Development Mode: Sending Notifications ===")
        
        # Send SMS notification
        if send_sms_notification(message, document):
            print("Successfully sent SMS notification in development mode")
            print("============================================\n")
            return {
                "success": True,
                "notifications_sent": 1,
                "errors": [],
                "dev_mode": True
            }
    
    # Production mode notifications
    # Send SMS notification
    if notification_settings["sms_notifications_enabled"]:
        try:
            if send_sms_notification(message, document):
                return {
                    "success": True,
                    "notifications_sent": 1,
                    "errors": [],
                    "dev_mode": False
                }
            else:
                return {
                    "success": False,
                    "notifications_sent": 0,
                    "errors": ["SMS notification failed"],
                    "dev_mode": False
                }
        except Exception as e:
            return {
                "success": False,
                "notifications_sent": 0,
                "errors": [f"SMS error: {str(e)}"],
                "dev_mode": False
            }
    
    return {
        "success": False,
        "notifications_sent": 0,
        "errors": ["No notification methods enabled"],
        "dev_mode": False
    }

def get_notification_history():
    """
    Get the notification history
    """
    with history_lock:
        return notification_settings["notification_history"]
