import os
import json
import random
import openai
from openai import OpenAI
from datetime import datetime
from compliance_keywords import COMPLIANCE_KEYWORDS, RISK_LEVELS
from redis_cache import get_cached_result, cache_result

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_document_risk(doc_id, content):
    """
    Analyze document content for compliance risk
    For the prototype, we'll use a keyword-based approach
    In a production environment, this would use more sophisticated ML/AI analysis
    """
    # Check cache first
    cache_key = f"risk:{doc_id}"
    cached_result = get_cached_result(cache_key)
    if cached_result:
        return json.loads(cached_result)
    
    # For demo purposes, if the content is short, use a simplified approach
    if len(content) < 200:
        result = simplified_risk_analysis(content)
        cache_result(cache_key, json.dumps(result))
        return result
    
    try:
        # Use OpenAI to analyze the document
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[
                {
                    "role": "system",
                    "content": """You are a financial compliance expert. Analyze the document for compliance risks.
                    Focus on identifying potential issues related to securities regulations, financial reporting, 
                    money laundering, insider trading, and other financial compliance areas.
                    Return a JSON object with the following fields:
                    - risk_score: A float between 0 and 1 indicating the overall risk level
                    - risk_categories: Array of risk categories identified (e.g. "insider trading", "AML", etc.)
                    - key_findings: Array of specific concerning elements found
                    - jurisdiction: Either "US", "EU", or "GLOBAL" based on regulatory context
                    - summary: A brief summary of the compliance implications
                    """
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Cache the result
        cache_result(cache_key, json.dumps(result))
        
        return result
    except Exception as e:
        print(f"Error in analyze_document_risk: {str(e)}")
        # Fallback to simplified analysis
        result = simplified_risk_analysis(content)
        cache_result(cache_key, json.dumps(result))
        return result

def simplified_risk_analysis(content):
    """
    Simplified risk analysis based on keyword matching
    """
    content_lower = content.lower()
    
    # Count keyword matches and their risk levels
    matches = {}
    total_risk = 0
    max_risk = 0
    risk_categories = []
    
    for keyword, risk_level in COMPLIANCE_KEYWORDS.items():
        if keyword.lower() in content_lower:
            matches[keyword] = RISK_LEVELS[risk_level]
            risk_value = RISK_LEVELS[risk_level]
            total_risk += risk_value
            max_risk = max(max_risk, risk_value)
            
            # Add risk category
            category = keyword.split()[0] if " " in keyword else keyword
            if category not in risk_categories:
                risk_categories.append(category)
    
    # Calculate overall risk score
    if not matches:
        risk_score = 0.1  # Base risk level
    else:
        # Weighted approach: 70% from max risk, 30% from average
        avg_risk = total_risk / len(matches) if matches else 0
        risk_score = 0.7 * max_risk + 0.3 * avg_risk
    
    # Determine jurisdiction
    jurisdiction = categorize_by_jurisdiction(content)
    
    # Create key findings
    key_findings = [f"Found potential {keyword} issue" for keyword in matches.keys()]
    
    # Generate a simple summary
    if matches:
        keywords_list = ", ".join(list(matches.keys())[:3])
        summary = f"Document contains {len(matches)} compliance-related keywords including {keywords_list}."
        if risk_score > 0.7:
            summary += " This document indicates high compliance risk and requires immediate review."
        elif risk_score > 0.4:
            summary += " This document indicates moderate compliance risk and should be reviewed."
        else:
            summary += " This document indicates low compliance risk but should still be monitored."
    else:
        summary = "No specific compliance risks identified in this document."
    
    return {
        "risk_score": risk_score,
        "risk_categories": risk_categories,
        "key_findings": key_findings,
        "jurisdiction": jurisdiction,
        "summary": summary
    }

def categorize_by_jurisdiction(content):
    """
    Determine whether a document relates to US, EU, India, Asia or Global jurisdiction
    """
    content_lower = content.lower()
    
    # US-specific terms
    us_terms = ["sec", "finra", "dodd-frank", "securities act", "exchange act", "federal reserve", 
                "cftc", "us treasury", "fasb", "us gaap", "sarbanes-oxley", "sox", "united states"]
    
    # EU-specific terms
    eu_terms = ["esma", "eba", "ecb", "mifid", "gdpr", "emir", "european union", "eu", "eba", 
                "european commission", "ifrs", "brexit", "european central bank"]
    
    # India-specific terms
    india_terms = ["sebi", "rbi", "companies act india", "indian securities", "nse india", "bse india",
                  "reserve bank of india", "ministry of corporate affairs india", "fema india", 
                  "indian regulatory", "indian compliance", "india"]
    
    # Asia-specific terms (excluding India)
    asia_terms = ["mas singapore", "hkma", "csrc china", "jfsa japan", "bank of japan", "pboc",
                 "korean fsc", "asian regulatory", "apac compliance", "asian markets",
                 "singapore exchange", "hong kong exchange", "tokyo exchange", "shanghai exchange",
                 "asian development bank", "asean"]
    
    us_count = sum(1 for term in us_terms if term in content_lower)
    eu_count = sum(1 for term in eu_terms if term in content_lower)
    india_count = sum(1 for term in india_terms if term in content_lower)
    asia_count = sum(1 for term in asia_terms if term in content_lower)
    
    # Find the jurisdiction with the most matches
    counts = {
        "US": us_count,
        "EU": eu_count,
        "INDIA": india_count,
        "ASIA": asia_count
    }
    
    max_count = max(counts.values())
    if max_count > 0:
        # Get the jurisdiction with the highest count
        jurisdiction = max(counts.items(), key=lambda x: x[1])[0]
        return jurisdiction
    else:
        # If no specific jurisdiction mentioned, look for currency indicators
        if "dollar" in content_lower or "$" in content:
            return "US"
        elif "euro" in content_lower or "€" in content:
            return "EU"
        elif "rupee" in content_lower or "₹" in content:
            return "INDIA"
        elif "yen" in content_lower or "¥" in content or "yuan" in content_lower:
            return "ASIA"
        else:
            # Default to global if can't determine
            return "GLOBAL"

def get_risk_level_label(risk_score):
    """
    Convert a risk score to a human-readable label
    """
    if risk_score >= 0.9:
        return "Critical"
    elif risk_score >= 0.7:
        return "High"
    elif risk_score >= 0.4:
        return "Medium"
    else:
        return "Low"

def analyze_compliance(content):
    """
    Main function to analyze compliance of a document
    Returns a dictionary with analysis results
    """
    # Generate a temporary document ID for caching
    doc_id = f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Get the risk analysis
    risk_analysis = analyze_document_risk(doc_id, content)
    
    # Format the results for display
    return {
        'summary': risk_analysis['summary'],
        'detailed_analysis': {
            'Risk Level': get_risk_level_label(risk_analysis['risk_score']),
            'Risk Score': f"{risk_analysis['risk_score']:.2%}",
            'Jurisdiction': risk_analysis['jurisdiction'],
            'Risk Categories': ', '.join(risk_analysis['risk_categories']),
            'Key Findings': risk_analysis['key_findings']
        },
        'risk_data': {
            'score': risk_analysis['risk_score'],
            'jurisdiction': risk_analysis['jurisdiction'],
            'categories': risk_analysis['risk_categories']
        }
    }
