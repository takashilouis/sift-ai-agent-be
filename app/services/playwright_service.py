"""
Real Web Scraping Service using Playwright

Replaces mock scraping with actual browser automation and LLM-based extraction.
"""

from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
from app.agents.llm_router import run_llm_structured, get_system_instruction
from pydantic import BaseModel, Field
import asyncio
import re


class ProductData(BaseModel):
    """Structured product data extracted from page"""
    url: str
    title: Optional[str] = None
    price: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: Optional[int] = None
    features: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    availability: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    images: list[str] = Field(default_factory=list)


async def scrape_product_page(url: str, use_llm_extraction: bool = True) -> Dict[str, Any]:
    """
    Scrape product page using Playwright
    
    Args:
        url: Product page URL to scrape
        use_llm_extraction: Whether to use LLM for data extraction (more reliable)
        
    Returns:
        Product data dictionary
    """
    print(f"[Playwright Service] Scraping URL: {url}")
    
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Create page
            page = await browser.new_page()
            
            # Set user agent to avoid bot detection
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            
            # Navigate to page
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait a bit for dynamic content
            await asyncio.sleep(2)
            
            # Get page content
            html_content = await page.content()
            
            await browser.close()
            
            print(f"[Playwright Service] Page loaded, HTML length: {len(html_content)}")
            
            # Extract product data
            if use_llm_extraction:
                product_data = await extract_with_llm(url, html_content)
                
                # Fallback/Augment: If LLM missed critical fields, try selectors
                if not product_data.price or not product_data.rating or not product_data.review_count:
                    print("[Playwright Service] LLM missing critical data, trying selectors to augment...")
                    selector_data = extract_with_selectors(url, html_content)
                    
                    if not product_data.price and selector_data.price:
                        product_data.price = selector_data.price
                        print(f"[Playwright Service] Recovered price from selectors: {product_data.price}")
                        
                    if not product_data.rating and selector_data.rating:
                        product_data.rating = selector_data.rating
                        print(f"[Playwright Service] Recovered rating from selectors: {product_data.rating}")
                        
                    if not product_data.review_count and selector_data.review_count:
                        product_data.review_count = selector_data.review_count
                        print(f"[Playwright Service] Recovered review_count from selectors: {product_data.review_count}")
            else:
                product_data = extract_with_selectors(url, html_content)
            
            return product_data.model_dump()
            
    except Exception as e:
        print(f"[Playwright Service] Error scraping {url}: {e}")
        # Return minimal data on error
        return {
            "url": url,
            "title": None,
            "price": None,
            "rating": None,
            "error": str(e)
        }


async def extract_with_llm(url: str, html_content: str) -> ProductData:
    """
    Use LLM to extract structured product data from HTML
    
    This is more reliable than CSS selectors as it adapts to different page structures.
    
    Args:
        url: Product URL
        html_content: Raw HTML content
        
    Returns:
        ProductData model
    """
    # Clean HTML to reduce token usage
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style tags
    for tag in soup(['script', 'style', 'noscript', 'svg']):
        tag.decompose()
    
    # Get text content
    text_content = soup.get_text(separator='\n', strip=True)
    
    # Truncate to avoid token limits (keep first 8000 chars)
    if len(text_content) > 8000:
        text_content = text_content[:8000] + "\n... [truncated]"
    
    print(f"[Playwright Service] Extracting data with LLM from {len(text_content)} chars")
    
    # Create extraction prompt
    prompt = f"""Extract structured product information from this webpage content.

URL: {url}

Page Content:
{text_content}

Extract the following information:
- title: Product name/title
- price: Current price (as string with currency symbol)
- rating: Average rating (0-5 scale, as float)
- review_count: Number of reviews (as integer)
- features: List of key product features
- description: Product description
- availability: Stock status (In Stock, Out of Stock, etc.)
- brand: Brand name
- category: Product category
- images: List of image URLs (if visible in content)

If any field cannot be determined, use null."""
    
    try:
        # Use LLM with structured output
        product_data = await run_llm_structured(
            prompt=prompt,
            response_model=ProductData,
            temperature=0.3,  # Lower temperature for extraction
            system_instruction=get_system_instruction("extract")
        )
        
        # Set URL
        product_data.url = url
        
        print(f"[Playwright Service] Extracted: {product_data.title}")
        
        return product_data
        
    except Exception as e:
        print(f"[Playwright Service] LLM extraction failed: {e}")
        # Fallback to selector-based extraction
        return extract_with_selectors(url, html_content)


def extract_with_selectors(url: str, html_content: str) -> ProductData:
    """
    Fallback: Extract product data using CSS selectors
    
    Args:
        url: Product URL
        html_content: Raw HTML
        
    Returns:
        ProductData model
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Determine site and use appropriate selectors
    if 'amazon.com' in url:
        return extract_amazon(url, soup)
    elif 'bestbuy.com' in url:
        return extract_bestbuy(url, soup)
    else:
        return extract_generic(url, soup)


def extract_amazon(url: str, soup: BeautifulSoup) -> ProductData:
    """Extract from Amazon product page"""
    title_elem = soup.select_one('#productTitle, h1.product-title')
    price_elem = soup.select_one('.a-price-whole, .a-price .a-offscreen')
    
    # Improved rating selectors
    rating_elem = soup.select_one(
        '#acrPopover, .a-icon-star .a-icon-alt, [data-hook="rating-out-of-text"], a.a-popover-trigger span'
    )
    
    # Improved review count selectors
    review_elem = soup.select_one(
        '#acrCustomerReviewText, [data-hook="total-review-count"], #acrCustomerReviewLink span'
    )
    
    # Extract features
    features = []
    feature_bullets = soup.select('#feature-bullets li, .a-unordered-list.a-vertical li')
    for bullet in feature_bullets[:5]:
        text = bullet.get_text(strip=True)
        if text:
            features.append(text)
    
    # Extract description
    desc_elem = soup.select_one('#productDescription, #feature-bullets')
    description = desc_elem.get_text(strip=True)[:500] if desc_elem else None
    
    # Parse rating
    rating = None
    if rating_elem:
        rating_text = rating_elem.get_text(strip=True)
        # Look for "4.2 out of 5" or just "4.2"
        match = re.search(r'(\d+\.?\d*)', rating_text)
        if match:
            try:
                val = float(match.group(1))
                if 0 <= val <= 5:
                    rating = val
            except ValueError:
                pass
    
    # Parse review count
    review_count = None
    if review_elem:
        review_text = review_elem.get_text(strip=True)
        match = re.search(r'([\d,]+)', review_text.replace(',', ''))
        if match:
            review_count = int(match.group(1))
    
    return ProductData(
        url=url,
        title=title_elem.get_text(strip=True) if title_elem else None,
        price=price_elem.get_text(strip=True) if price_elem else None,
        rating=rating,
        review_count=review_count,
        features=features,
        description=description,
        availability="In Stock"  # Simplified
    )


def extract_bestbuy(url: str, soup: BeautifulSoup) -> ProductData:
    """Extract from Best Buy product page"""
    title_elem = soup.select_one('.sku-title, h1')
    price_elem = soup.select_one('.priceView-customer-price span, .priceView-hero-price span')
    
    return ProductData(
        url=url,
        title=title_elem.get_text(strip=True) if title_elem else None,
        price=price_elem.get_text(strip=True) if price_elem else None,
    )


def extract_generic(url: str, soup: BeautifulSoup) -> ProductData:
    """Generic extraction for unknown sites"""
    # Try common selectors
    title_elem = soup.select_one('h1, .product-title, .product-name')
    price_elem = soup.select_one('.price, .product-price, [itemprop="price"]')
    
    return ProductData(
        url=url,
        title=title_elem.get_text(strip=True) if title_elem else "Unknown Product",
        price=price_elem.get_text(strip=True) if price_elem else None,
    )


async def scrape_multiple_products(urls: list[str]) -> list[Dict[str, Any]]:
    """
    Scrape multiple product pages concurrently
    
    Args:
        urls: List of product URLs
        
    Returns:
        List of product data dictionaries
    """
    tasks = [scrape_product_page(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions
    valid_results = []
    for result in results:
        if isinstance(result, dict):
            valid_results.append(result)
        else:
            print(f"[Playwright Service] Scraping failed: {result}")
    
    return valid_results
