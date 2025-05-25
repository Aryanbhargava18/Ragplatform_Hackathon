import os
import json
import requests
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
    "slack_webhook_url": os.environ.get("SLACK_WEBHOOK_URL", ""),
    "email_notifications_enabled": False,  # Disable email for now
    "sms_notifications_enabled": True,     # Enable SMS
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

def send_slack_notification(message, document=None):
    """
    Send a notification to Slack
    """
    if notification_settings["dev_mode"]:
        print("\n=== Development Mode: Slack Notification ===")
        print(f"Message: {message}")
        if document:
            print(f"Document ID: {document.get('id', 'Unknown')}")
            print(f"Risk Score: {document.get('risk_score', 0):.2f}")
        print("==========================================\n")
        return True
        
    webhook_url = notification_settings["slack_webhook_url"]
    
    if not webhook_url:
        print("Slack webhook URL not configured")
        return False
    
    try:
        # Prepare the Slack message payload
        payload = {
            "text": message,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Compliance Alert 🚨"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
        }
        
        # Add document details if provided
        if document:
            payload["blocks"].append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Document ID:*\n{document.get('id', 'Unknown')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Risk Score:*\n{document.get('risk_score', 0):.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Jurisdiction:*\n{document.get('jurisdiction', 'Unknown')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Source:*\n{document.get('source', 'Unknown')}"
                    }
                ]
            })
            
            # Add document content
            payload["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Document Preview:*\n```{document.get('content', '')[:200]}...```"
                }
            })
        
        # Send the request to Slack
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 200:
            print("Slack notification sent successfully")
            return True
        else:
            print(f"Failed to send Slack notification: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"Error sending Slack notification: {str(e)}")
        return False

def send_email_notification(recipient, subject, message, document=None):
    """
    Send an email notification
    """
    if notification_settings["dev_mode"]:
        print("\n=== Development Mode: Email Notification ===")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(f"Message: {message}")
        if document:
            print(f"Document ID: {document.get('id', 'Unknown')}")
            print(f"Risk Score: {document.get('risk_score', 0):.2f}")
        print("==========================================\n")
        return True
        
    try:
        # In a production environment, send the actual email
        print(f"Email notification:")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(f"Message: {message}")
        
        if document:
            print(f"Document ID: {document.get('id', 'Unknown')}")
            print(f"Risk Score: {document.get('risk_score', 0):.2f}")
        
        return True
    except Exception as e:
        print(f"Error sending email notification: {str(e)}")
        return False

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
        
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, NOTIFICATION_PHONE_NUMBER]):
        print("Twilio credentials not fully configured")
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
        
        # Send the SMS
        twilio_message = client.messages.create(
            body=sms_message,
            from_=TWILIO_FROM_NUMBER,
            to=NOTIFICATION_PHONE_NUMBER
        )
        
        print(f"SMS notification sent with SID: {twilio_message.sid}")
        return True
    
    except Exception as e:
        print(f"Error sending SMS notification: {str(e)}")
        return False

def check_and_send_alerts(document, risk_analysis):
    """
    Check if alerts should be sent based on risk analysis
    """
    try:
        risk_score = risk_analysis.get('risk_score', 0)
        
        # For demo purposes, we'll just print the alerts
        if risk_score >= 0.7:
            print(f"[HIGH RISK ALERT] Document {document.get('id', 'Unknown')} requires immediate attention!")
            print(f"Risk Score: {risk_score:.2%}")
            print(f"Jurisdiction: {risk_analysis.get('jurisdiction', 'Unknown')}")
            print(f"Categories: {', '.join(risk_analysis.get('risk_categories', []))}")
            
            # In a production environment, we would send actual notifications
            if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
                send_sms_alert(document, risk_analysis)
        
        return True
    except Exception as e:
        print(f"Error in check_and_send_alerts: {str(e)}")
        return False

def send_sms_alert(document, risk_analysis):
    """
    Send SMS alert using Twilio
    """
    try:
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]):
            return False
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message = f"""
        🚨 HIGH RISK ALERT
        Document: {document.get('id', 'Unknown')}
        Risk Score: {risk_analysis.get('risk_score', 0):.2%}
        Jurisdiction: {risk_analysis.get('jurisdiction', 'Unknown')}
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # In a production environment, we would send to registered phone numbers
        # For demo, we'll just print the message
        print("Would send SMS:", message)
        
        return True
    except Exception as e:
        print(f"Error sending SMS alert: {str(e)}")
        return False

def send_notification(message, document_id=None, risk_score=None):
    """
    Send a manual notification
    """
    # Prepare document info if provided
    document = None
    if document_id:
        document = {
            "id": document_id,
            "risk_score": risk_score if risk_score is not None else 0.8
        }
    
    # Send notifications
    notifications_sent = 0
    errors = []
    
    # In development mode, we'll simulate all notifications
    if notification_settings["dev_mode"]:
        print("\n=== Development Mode: Sending Notifications ===")
        
        # Send Slack notification
        if send_slack_notification(message, document):
            notifications_sent += 1
        
        # Send SMS notification
        if send_sms_notification(message, document):
            notifications_sent += 1
        
        # Send email notification
        if send_email_notification("test@example.com", "Test Notification", message, document):
            notifications_sent += 1
            
        print(f"Successfully sent {notifications_sent} notifications in development mode")
        print("============================================\n")
        
        return {
            "success": True,
            "notifications_sent": notifications_sent,
            "errors": [],
            "dev_mode": True
        }
    
    # Production mode notifications
    # Send Slack notification
    if notification_settings["slack_webhook_url"]:
        try:
            if send_slack_notification(message, document):
                notifications_sent += 1
            else:
                errors.append("Slack notification failed")
        except Exception as e:
            errors.append(f"Slack error: {str(e)}")
    else:
        errors.append("Slack webhook URL not configured")
    
    # Send SMS notification
    if notification_settings["sms_notifications_enabled"]:
        try:
            if send_sms_notification(message, document):
                notifications_sent += 1
            else:
                errors.append("SMS notification failed")
        except Exception as e:
            errors.append(f"SMS error: {str(e)}")
    
    # Send email notification
    if notification_settings["email_notifications_enabled"]:
        try:
            if send_email_notification("test@example.com", "Test Notification", message, document):
                notifications_sent += 1
            else:
                errors.append("Email notification failed")
        except Exception as e:
            errors.append(f"Email error: {str(e)}")
    
    return {
        "success": notifications_sent > 0,
        "notifications_sent": notifications_sent,
        "errors": errors,
        "dev_mode": False
    }

def get_notification_history():
    """
    Get the notification history
    """
    with history_lock:
        return notification_settings["notification_history"]
