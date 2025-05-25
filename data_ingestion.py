import pathway as pw
import time
import requests
import json
import os
import threading
from datetime import datetime, timedelta
import random

from compliance_keywords import COMPLIANCE_KEYWORDS
from vector_store import update_vector_index
from compliance_analyzer import analyze_document_risk, categorize_by_jurisdiction
from notification_service import send_notification
from mock_websocket import start_mock_websocket_server

# API endpoints (for demo purposes)
SEC_API_ENDPOINT = "https://www.sec.gov/cgi-bin/browse-edgar"
NEWS_API_ENDPOINT = "https://newsapi.org/v2/everything"
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

# Global variables
running = False
pipeline_thread = None

def fetch_sec_filings(company_ticker=None, form_type="10-K,10-Q,8-K", count=10):
    """
    Fetch SEC filings from the EDGAR database
    """
    try:
        params = {
            "action": "getcurrent",
            "output": "atom",
            "count": count
        }
        
        if company_ticker:
            params["CIK"] = company_ticker
        
        if form_type:
            params["type"] = form_type
            
        response = requests.get(SEC_API_ENDPOINT, params=params)
        
        if response.status_code == 200:
            # In a production environment, we would parse the XML response
            # For this prototype, we'll simulate the documents
            documents = []
            for i in range(count):
                doc_type = random.choice(form_type.split(","))
                company = f"COMPANY-{random.randint(1000, 9999)}"
                
                # Generate some random content with compliance keywords
                keywords = list(COMPLIANCE_KEYWORDS.keys())
                selected_keywords = random.sample(keywords, k=random.randint(1, 5))
                
                content = f"This is a {doc_type} filing for {company}. "
                for keyword in selected_keywords:
                    content += f"The document contains information about {keyword}. "
                
                documents.append({
                    "id": f"SEC-{doc_type}-{company}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    "type": "SEC_FILING",
                    "form_type": doc_type,
                    "company": company,
                    "filing_date": datetime.now().strftime("%Y-%m-%d"),
                    "content": content,
                    "keywords": selected_keywords,
                    "source": "SEC EDGAR",
                    "jurisdiction": "US"
                })
            
            return documents
        else:
            print(f"Error fetching SEC filings: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception in fetch_sec_filings: {str(e)}")
        return []

def fetch_financial_news(query="financial regulation compliance", days=1, count=10):
    """
    Fetch financial news articles related to compliance
    """
    try:
        if not NEWS_API_KEY:
            # If no API key is available, generate mock news
            return generate_mock_news(count)
            
        params = {
            "q": query,
            "from": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            "sortBy": "publishedAt",
            "apiKey": NEWS_API_KEY,
            "language": "en",
            "pageSize": count
        }
        
        response = requests.get(NEWS_API_ENDPOINT, params=params)
        
        if response.status_code == 200:
            data = response.json()
            documents = []
            
            for article in data.get("articles", []):
                # Determine jurisdiction based on source or content
                jurisdiction = categorize_by_jurisdiction(article.get("content", ""))
                
                documents.append({
                    "id": f"NEWS-{hash(article.get('url', ''))}",
                    "type": "NEWS_ARTICLE",
                    "title": article.get("title", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "published_date": article.get("publishedAt", ""),
                    "content": article.get("content", ""),
                    "url": article.get("url", ""),
                    "jurisdiction": jurisdiction
                })
            
            return documents
        else:
            print(f"Error fetching news: {response.status_code}")
            return generate_mock_news(count)
    except Exception as e:
        print(f"Exception in fetch_financial_news: {str(e)}")
        return generate_mock_news(count)

def generate_mock_news(count=5):
    """
    Generate mock news articles when API is not available
    """
    sources = ["Bloomberg", "Financial Times", "Wall Street Journal", "Reuters", "CNBC"]
    topics = ["ESG Reporting", "GDPR Compliance", "Anti-Money Laundering", 
              "MiFID II", "Basel III", "SEC Enforcement", "Insider Trading",
              "Data Privacy", "Financial Fraud", "Regulatory Changes"]
    
    documents = []
    for i in range(count):
        source = random.choice(sources)
        topic = random.choice(topics)
        jurisdiction = "EU" if any(eu_term in topic for eu_term in ["GDPR", "MiFID", "EU"]) else "US"
        
        # Generate random content with compliance keywords
        keywords = list(COMPLIANCE_KEYWORDS.keys())
        selected_keywords = random.sample(keywords, k=random.randint(1, 3))
        
        content = f"This is a news article about {topic} from {source}. "
        for keyword in selected_keywords:
            content += f"The article discusses {keyword} implications. "
        
        documents.append({
            "id": f"NEWS-{hash(source + '-' + topic + '-' + datetime.now().strftime('%Y%m%d-%H%M%S'))}",
            "type": "NEWS_ARTICLE",
            "title": f"New developments in {topic}",
            "source": source,
            "published_date": datetime.now().strftime("%Y-%m-%d"),
            "content": content,
            "url": f"https://example.com/news/{i}",
            "jurisdiction": jurisdiction,
            "keywords": selected_keywords
        })
    
    return documents

def setup_pathway_pipeline():
    """
    Set up the Pathway data processing pipeline
    """
    # Initialize Pathway context
    pw.io.init()
    
    # SEC filings input connector
    # In a production environment, this would be a real connector to SEC data
    # For this prototype, we'll use a simple input table
    sec_filings_schema = pw.schema_builder(
        id=str, type=str, form_type=str, company=str, filing_date=str,
        content=str, keywords=list, source=str, jurisdiction=str
    )
    sec_filings = pw.io.csv("", schema=sec_filings_schema)
    
    # News articles input connector
    news_schema = pw.schema_builder(
        id=str, type=str, title=str, source=str, published_date=str,
        content=str, url=str, jurisdiction=str, keywords=list
    )
    news_articles = pw.io.csv("", schema=news_schema)
    
    # Mock regulatory updates from WebSocket
    reg_updates_schema = pw.schema_builder(
        id=str, type=str, title=str, agency=str, published_date=str,
        content=str, url=str, jurisdiction=str, importance=int
    )
    reg_updates = pw.io.csv("", schema=reg_updates_schema)
    
    # Combine all document sources
    all_documents = pw.union(
        sec_filings.select(
            pw.this.id, pw.this.type, pw.this.content, pw.this.jurisdiction,
            title=pw.this.form_type + " for " + pw.this.company,
            source=pw.this.source,
            date=pw.this.filing_date,
            keywords=pw.this.keywords
        ),
        news_articles.select(
            pw.this.id, pw.this.type, pw.this.content, pw.this.jurisdiction,
            title=pw.this.title,
            source=pw.this.source,
            date=pw.this.published_date,
            keywords=pw.this.keywords
        ),
        reg_updates.select(
            pw.this.id, pw.this.type, pw.this.content, pw.this.jurisdiction,
            title=pw.this.title,
            source=pw.this.agency,
            date=pw.this.published_date,
            keywords=pw.apply(lambda x: [], pw.this.content),
            importance=pw.this.importance
        )
    )
    
    # Process documents for compliance analysis
    analyzed_documents = all_documents.select(
        pw.this.id, pw.this.type, pw.this.title, pw.this.source, 
        pw.this.date, pw.this.content, pw.this.jurisdiction,
        risk_score=pw.apply(lambda doc: analyze_document_risk(doc["id"], doc["content"])["risk_score"], pw.this),
        keywords=pw.this.keywords
    )
    
    # Output connectors
    # In a production environment, these would write to persistent storage
    # For this prototype, we'll use simple callbacks
    
    # Update vector index with new documents
    analyzed_documents.sink_to(pw.io.python_callback(
        lambda row: update_vector_index(row)
    ))
    
    # Check for high-risk documents and send alerts
    analyzed_documents.filter(
        pw.this.risk_score >= 0.7  # High risk threshold
    ).sink_to(pw.io.python_callback(
        lambda row: check_and_send_alerts(row, {"risk_score": row["risk_score"], "jurisdiction": row["jurisdiction"]})
    ))
    
    # Run the pipeline
    pw.run()

def data_ingestion_thread():
    """
    Thread function to run the data ingestion pipeline
    """
    global running
    
    try:
        # Start the mock WebSocket server
        websocket_thread = threading.Thread(target=start_mock_websocket_server)
        websocket_thread.daemon = True
        websocket_thread.start()
        
        # In a loop, fetch data and feed it to the Pathway pipeline
        while running:
            # Fetch SEC filings
            sec_documents = fetch_sec_filings(count=random.randint(1, 3))
            for doc in sec_documents:
                # In a production environment, this would be fed into the Pathway input connectors
                # For this prototype, we'll directly update the vector index
                update_vector_index(doc)
                risk_analysis = analyze_document_risk(doc["id"], doc["content"])
                if risk_analysis["risk_score"] >= 0.7:
                    check_and_send_alerts(doc, risk_analysis)
            
            # Fetch financial news
            news_documents = fetch_financial_news(count=random.randint(1, 3))
            for doc in news_documents:
                # In a production environment, this would be fed into the Pathway input connectors
                # For this prototype, we'll directly update the vector index
                update_vector_index(doc)
                risk_analysis = analyze_document_risk(doc["id"], doc["content"])
                if risk_analysis["risk_score"] >= 0.7:
                    check_and_send_alerts(doc, risk_analysis)
            
            # Wait before the next iteration
            time.sleep(10)
    except Exception as e:
        print(f"Exception in data_ingestion_thread: {str(e)}")
    finally:
        running = False

def start_ingestion_pipeline(uploaded_file=None):
    """
    Start the data ingestion pipeline
    If a file is uploaded, process it directly
    """
    if uploaded_file is not None:
        # For uploaded files, just return the content
        try:
            # Convert the uploaded file to text
            if uploaded_file.type == "text/plain":
                return uploaded_file.getvalue().decode("utf-8")
            else:
                # For demo purposes, return a mock response
                return f"Mock content for {uploaded_file.name}: This is a sample document containing compliance-related information about insider trading and regulatory reporting requirements. The document discusses various aspects of financial compliance and risk management."
        except Exception as e:
            print(f"Error processing uploaded file: {str(e)}")
            return "Error processing the uploaded file."
    
    global running, pipeline_thread
    
    if not running:
        running = True
        pipeline_thread = threading.Thread(target=data_ingestion_thread)
        pipeline_thread.daemon = True
        pipeline_thread.start()
        
        # Start the mock WebSocket server in a separate thread
        websocket_thread = threading.Thread(target=start_mock_websocket_server)
        websocket_thread.daemon = True
        websocket_thread.start()
        
        return "Pipeline started successfully"
    else:
        return "Pipeline is already running"

def stop_ingestion_pipeline():
    """
    Stop the data ingestion pipeline
    """
    global running
    running = False

def check_and_send_alerts(document, risk_analysis):
    """
    Check if alerts should be sent based on risk analysis
    """
    try:
        risk_score = risk_analysis.get('risk_score', 0)
        
        # Send alerts for high-risk documents (risk score >= 0.7)
        if risk_score >= 0.7:
            message = f"""🚨 HIGH RISK ALERT
Document: {document.get('id', 'Unknown')}
Risk Score: {risk_score:.2%}
Jurisdiction: {risk_analysis.get('jurisdiction', 'Unknown')}
Categories: {', '.join(risk_analysis.get('risk_categories', []))}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            # Send notification
            notification_result = send_notification(
                message=message,
                document_id=document.get('id'),
                risk_score=risk_score
            )
            
            return notification_result.get("success", False)
        
        return True
    except Exception as e:
        print(f"Error in check_and_send_alerts: {str(e)}")
        return False
