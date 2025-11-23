import re
from typing import Optional


def clean_html_text(html: str) -> str:
    """
    Clean HTML text by removing tags and extra whitespace
    
    Args:
        html: Raw HTML string
        
    Returns:
        Cleaned text string
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters
    text = re.sub(r'[^\w\s\.\,\!\?\-\$\%]', '', text)
    
    return text.strip()


def extract_price(text: str) -> Optional[str]:
    """
    Extract price from text using regex
    
    Args:
        text: Text containing price information
        
    Returns:
        Extracted price string or None
    """
    # Pattern for prices like $199.99, $1,299.00, etc.
    pattern = r'\$[\d,]+\.?\d*'
    match = re.search(pattern, text)
    
    if match:
        return match.group(0)
    
    return None


def extract_rating(text: str) -> Optional[float]:
    """
    Extract rating from text (e.g., "4.5 out of 5 stars")
    
    Args:
        text: Text containing rating information
        
    Returns:
        Rating as float or None
    """
    # Pattern for ratings like "4.5", "4.5 out of 5", etc.
    pattern = r'(\d+\.?\d*)\s*(?:out of|\/)\s*5'
    match = re.search(pattern, text)
    
    if match:
        return float(match.group(1))
    
    # Try simple decimal pattern
    pattern = r'\b([0-5]\.\d+)\b'
    match = re.search(pattern, text)
    
    if match:
        rating = float(match.group(1))
        if 0 <= rating <= 5:
            return rating
    
    return None


def truncate_text(text: str, max_length: int = 500) -> str:
    """
    Truncate text to a maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."
