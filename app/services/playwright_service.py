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
    reviews: list[str] = Field(default_factory=list)

from app.services.proxy_service import proxy_service

async def scrape_product_page(url: str, use_llm_extraction: bool = True) -> Dict[str, Any]:
    """
    Scrape product page using Playwright with rotating proxies
    
    Args:
        url: Product page URL to scrape
        use_llm_extraction: Whether to use LLM for data extraction (more reliable)
        
    Returns:
        Product data dictionary
    """
    print(f"[Playwright Service] Scraping URL: {url}")
    
    try:
        async with async_playwright() as p:
            # Launch browser (no global proxy)
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox', 
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized' 
                ]
            )
            
            # Stealth: Randomize User-Agent
            import random
            user_agents = [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'
            ]
            
            # Retry logic for blocking/captchas
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                context = None
                try:
                    # Determine proxy and UA for this attempt
                    current_proxy = None
                    if attempt > 0:
                        print("Rotating User-Agent")
                        raw_proxy = await proxy_service.get_next_proxy()
                        if raw_proxy:
                            current_proxy = {"server": f"http://{raw_proxy}"}
                            print(f"[Playwright Service] Retry attempt {attempt+1}/{max_retries} using proxy: {raw_proxy}")
                        else:
                            print(f"[Playwright Service] Retry attempt {attempt+1}/{max_retries} (No proxy available)")
                    
                    user_agent = random.choice(user_agents)
                    
                    # Create isolated context with proxy and UA
                    context = await browser.new_context(
                        user_agent=user_agent,
                        proxy=current_proxy,
                        viewport={'width': 1920, 'height': 1080},
                        device_scale_factor=1,
                    )
                    
                    # Stealth: Hide webdriver property
                    await context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """)
                    
                    page = await context.new_page()
                    
                    # Extra headers
                    await page.set_extra_http_headers({
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Upgrade-Insecure-Requests': '1'
                    })
                    
                    # Navigate
                    print(f"[Playwright Service] Navigating to {url} (Attempt {attempt+1})")
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000) # Increased slightly for proxies
                    except Exception as e:
                        print(f"[Playwright Service] Navigation timeout/error: {e}")
                        # If meaningful error, maybe raise to trigger retry logic
                        
                    # Human-like delays
                    delay = 1 + random.random() * 2
                    await asyncio.sleep(delay)
                    
                    # Scroll & Mouse
                    try:
                        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(1)
                    except:
                        pass
                        
                    # Get content
                    html_content = await page.content()
                    content_length = len(html_content)
                    print(f"[Playwright Service] Page loaded, length: {content_length}")
                    
                    # Block detection
                    if content_length < 15000:
                        raise Exception(f"Content too short (<15KB). Blocked/Captcha detected.")
                    
                    # If we got here, success! 
                    # Extract data...
                    
                    # Close context to clean up
                    # await context.close() (do this in finally or after extraction)
                    
                    # Extract product data (logic remains same)
                    if use_llm_extraction:
                        product_data = await extract_with_llm(url, html_content)
                        # ... fallback ...
                        if not product_data.price or not product_data.rating or not product_data.review_count:
                            selector_data = extract_with_selectors(url, html_content)
                            if not product_data.price and selector_data.price: product_data.price = selector_data.price
                            if not product_data.rating and selector_data.rating: product_data.rating = selector_data.rating
                            if not product_data.review_count and selector_data.review_count: product_data.review_count = selector_data.review_count
                    else:
                        product_data = extract_with_selectors(url, html_content)
                    
                    await context.close()
                    await browser.close()
                    return product_data.model_dump()
                    
                except Exception as e:
                    print(f"[Playwright Service] Error in attempt {attempt+1}: {e}")
                    last_error = e
                    if context:
                        await context.close()
                    # Continue loop to retry
            
            await browser.close()
            
            # If all retries failed
            return {
                "url": url,
                "title": "Access Denied / Captcha",
                "price": None,
                "rating": None,
                "error": f"Failed after {max_retries} attempts. Last error: {str(last_error)}"
            }
            
    except Exception as e:
        print(f"[Playwright Service] Error scraping {url}: {e}")
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
    
    # Extract image URLs BEFORE removing tags
    image_urls = []
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src') or img.get('srcset', '').split()[0] if img.get('srcset') else None
        if src and src.startswith('http'):
            # Filter out small icons and logos
            if 'logo' not in src.lower() and 'icon' not in src.lower():
                # Clean URL: remove parameters after image extension
                # e.g., .jpg;maxHeight=128 -> .jpg
                import re
                cleaned_src = re.sub(r'(\.(jpg|jpeg|png|webp|gif));.*', r'\1', src, flags=re.IGNORECASE)
                image_urls.append(cleaned_src)
    
    # Remove duplicates while preserving order
    image_urls = list(dict.fromkeys(image_urls))[:10]  # Keep first 10 unique images
    
    print(f"[Playwright Service] Found {len(image_urls)} image URLs")
    
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
- reviews: List of latest 5 user reviews of the product

NOTE: Images will be extracted separately from HTML, so you can leave the images field empty.

If any field cannot be determined, use null."""
    
    try:
        # Use LLM with structured output
        product_data = await run_llm_structured(
            prompt=prompt,
            response_model=ProductData,
            temperature=0.3,  # Lower temperature for extraction
            system_instruction=get_system_instruction("extract")
        )
        
        # Set URL and images
        product_data.url = url
        product_data.images = image_urls
        
        print(f"[Playwright Service] Extracted: {product_data.title} with {len(product_data.images)} images")
        
        return product_data
        
    except Exception as e:
        print(f"[Playwright Service] LLM extraction failed: {e}")
        # Fallback to selector-based extraction
        fallback_data = extract_with_selectors(url, html_content)
        fallback_data.images = image_urls  # Add images to fallback data
        return fallback_data



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
