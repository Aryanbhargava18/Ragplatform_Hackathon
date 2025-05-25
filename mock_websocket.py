import asyncio
import websockets
import json
import random
import time
from datetime import datetime
import threading

# Global variables
running = True
connected_clients = set()
regulatory_agencies = {
    "US": ["SEC", "FINRA", "CFTC", "Federal Reserve", "OCC"],
    "EU": ["ESMA", "EBA", "ECB", "European Commission", "EIOPA"]
}

regulatory_topics = {
    "US": [
        "Climate-Related Disclosures",
        "Cybersecurity Risk Management",
        "Digital Assets and Cryptocurrency",
        "SPACs Disclosures",
        "Insider Trading Prevention",
        "Market Manipulation Rules",
        "Investment Adviser Marketing",
        "ESG Reporting Requirements",
        "Private Fund Adviser Regulation",
        "Whistleblower Program Updates"
    ],
    "EU": [
        "GDPR Compliance Updates",
        "MiFID II Implementation",
        "Sustainable Finance Disclosure Regulation",
        "Markets in Crypto Assets (MiCA)",
        "Digital Operational Resilience Act",
        "Anti-Money Laundering Directives",
        "Corporate Sustainability Reporting Directive",
        "Payment Services Directive (PSD2)",
        "Taxonomy Regulation",
        "Bank Recovery and Resolution Directive"
    ]
}

async def mock_websocket_handler(websocket, path):
    """
    Mock WebSocket handler that sends regulatory updates
    """
    try:
        while True:
            # Generate a mock regulatory update
            update = {
                "id": f"REG-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "type": "REGULATORY_UPDATE",
                "title": "New Regulatory Guidance",
                "agency": random.choice(["SEC", "FINRA", "FCA", "ESMA"]),
                "published_date": datetime.now().strftime("%Y-%m-%d"),
                "content": "This is a mock regulatory update.",
                "url": "https://example.com/regulatory-update",
                "jurisdiction": random.choice(["US", "EU", "GLOBAL"]),
                "importance": random.randint(1, 5)
            }
            
            await websocket.send(json.dumps(update))
            await asyncio.sleep(60)  # Send update every minute
    except websockets.exceptions.ConnectionClosed:
        pass

async def start_server():
    """
    Start the WebSocket server
    """
    global running
    
    # Start the server
    server = await websockets.serve(
        mock_websocket_handler,
        "localhost",
        8765
    )
    
    # Keep the server running
    while running:
        await asyncio.sleep(1)
    
    # Stop the server
    server.close()
    await server.wait_closed()

def start_mock_websocket_server():
    """
    Start the mock WebSocket server
    """
    global running
    
    running = True
    
    try:
        start_server()
    except Exception as e:
        print(f"Error starting mock WebSocket server: {str(e)}")
    finally:
        running = False
