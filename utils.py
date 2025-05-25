from datetime import datetime

def format_datetime(dt):
    """
    Format a datetime object or string for display
    """
    if isinstance(dt, str):
        try:
            dt_obj = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            return dt_obj.strftime("%b %d, %Y %H:%M")
        except ValueError:
            try:
                dt_obj = datetime.strptime(dt, "%Y-%m-%d")
                return dt_obj.strftime("%b %d, %Y")
            except ValueError:
                return dt
    elif isinstance(dt, datetime):
        return dt.strftime("%b %d, %Y %H:%M")
    else:
        return str(dt)

def truncate_text(text, max_length=100):
    """
    Truncate text to a maximum length and add ellipsis
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."

def format_risk_score(risk_score):
    """
    Format a risk score for display
    """
    if risk_score is None:
        return "Unknown"
    
    try:
        score = float(risk_score)
        return f"{score:.2f}"
    except (ValueError, TypeError):
        return str(risk_score)

def get_risk_color(risk_score):
    """
    Get a color based on risk score
    """
    if risk_score is None:
        return "gray"
    
    try:
        score = float(risk_score)
        if score >= 0.8:
            return "red"
        elif score >= 0.6:
            return "orange"
        elif score >= 0.4:
            return "yellow"
        else:
            return "green"
    except (ValueError, TypeError):
        return "gray"

def parse_date(date_str):
    """
    Parse a date string into a datetime object
    """
    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S"
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If all formats fail, return None
    return None

def format_jurisdiction(jurisdiction):
    """
    Format a jurisdiction code for display
    """
    if not jurisdiction:
        return "Unknown"
    
    jurisdiction = str(jurisdiction).upper()
    
    if jurisdiction == "US":
        return "United States"
    elif jurisdiction == "EU":
        return "European Union"
    elif jurisdiction == "INDIA":
        return "India"
    elif jurisdiction == "ASIA":
        return "Asia Pacific"
    elif jurisdiction == "GLOBAL":
        return "Global"
    else:
        return jurisdiction
