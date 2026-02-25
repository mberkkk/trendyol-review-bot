import logging
import re
import time
from dataclasses import dataclass, field

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapedProduct:
    product_id: str
    product_name: str
    category: str
    description: str
    reviews: list[str] = field(default_factory=list)


def _build_driver() -> webdriver.Chrome:
    """Create a stealth headless Chrome driver."""
    options = Options()
    if settings.scraper_headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    stealth(
        driver,
        languages=["tr-TR", "tr"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver


def _extract_product_id(url: str) -> str:
    """Extract numeric product ID from Trendyol URL."""
    match = re.search(r"-p-(\d+)", url)
    if match:
        return match.group(1)
    # Fallback: use last numeric segment
    parts = url.rstrip("/").split("-")
    for part in reversed(parts):
        if part.isdigit():
            return part
    return url.split("/")[-1][:20]


def _get_initial_state(driver: webdriver.Chrome) -> dict:
    """Extract Trendyol's embedded state JSON to bypass UI DOM completely."""
    try:
        state = driver.execute_script("return window.__INITIAL_STATE__;")
        return state if isinstance(state, dict) else {}
    except Exception as e:
        logger.warning("Could not extract window.__INITIAL_STATE__: %s", e)
        return {}


def _scrape_product_info(driver: webdriver.Chrome, wait: WebDriverWait) -> dict:
    """Extract product name, category, and description securely from JSON state or DOM fallback."""
    info = {"product_name": "Bilinmiyor", "category": "Genel", "description": ""}

    state = _get_initial_state(driver)
    
    # Try finding product name in state
    try:
        product_info = state.get("product", {}).get("product", {})
        if product_info and "name" in product_info:
            info["product_name"] = f"{product_info.get('brand', {}).get('name', '')} {product_info['name']}".strip()
            
        # Try getting category hierarchy
        categories = state.get("product", {}).get("categoryHierarchy", [])
        if categories and len(categories) > 0:
            info["category"] = categories[-1].get("name", "Genel")
            
        # Try getting description
        desc = product_info.get("description", "")
        if desc:
            info["description"] = re.sub(r'<[^>]+>', '', desc)[:500]
            
    except Exception as e:
        logger.debug("Failed extracting metadata from initial state, falling back to DOM: %s", e)

    # Fallback to DOM if JSON state failed
    if info["product_name"] == "Bilinmiyor":
        try:
            info["product_name"] = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-title, h1.pr-new-br, h1"))
            ).text.strip()
        except TimeoutException:
            logger.warning("Product name not found in JS or DOM")

    if info["category"] == "Genel":
        try:
            breadcrumbs = driver.find_elements(By.CSS_SELECTOR, "a.product-detail-breadcrumb-item, div.breadcrumb-wrapper a")
            if len(breadcrumbs) >= 2:
                info["category"] = breadcrumbs[-2].text.strip()
        except Exception:
            pass

    return info


def _scrape_reviews(driver: webdriver.Chrome, product_url: str, wait: WebDriverWait) -> list[str]:
    """Visit the /yorumlar page and aggressively hunt for comments in JS initial state and DOM."""
    reviews: list[str] = []
    
    reviews_url = product_url.split("?")[0]
    if not reviews_url.endswith("/yorumlar"):
        reviews_url = f"{reviews_url.rstrip('/')}/yorumlar"
        
    logger.info("Fetching reviews page: %s", reviews_url)
    driver.get(reviews_url)
    time.sleep(3) # Wait for React render/bot check

    # 1. Approach: Extract from JS __INITIAL_STATE__
    state = _get_initial_state(driver)
    if state:
        def find_comments(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "comment" and isinstance(v, str) and len(v) > 10:
                        reviews.append(v)
                    elif isinstance(v, (dict, list)):
                        find_comments(v)
            elif isinstance(obj, list):
                for item in obj:
                    find_comments(item)
                    
        find_comments(state)
        # Deduplicate while preserving order mostly
        seen = set()
        unique_reviews = []
        for r in reviews:
            if r not in seen:
                seen.add(r)
                unique_reviews.append(r)
        reviews = unique_reviews
        logger.info("Extracted %d reviews from JSON state", len(reviews))

    # 2. Approach: DOM search (Fallback)
    if not reviews:
        logger.info("JSON state empty, exploring JS DOM with generic selectors")
        try:
            # Scroll to trigger lazy loading if we are on a standard page
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            all_p = driver.find_elements(By.TAG_NAME, "p")
            for p in all_p:
                text = p.text.strip()
                if len(text) > 15 and text not in reviews:
                    reviews.append(text)
                    if len(reviews) >= settings.max_reviews_per_product:
                        break
        except Exception as e:
            logger.warning("Error exploring DOM fallback for reviews: %s", e)

    return reviews[: settings.max_reviews_per_product]


def scrape_product(url: str) -> ScrapedProduct:
    """
    Main entry point: scrape product info and reviews from a Trendyol URL.

    Args:
        url: Full Trendyol product URL.

    Returns:
        ScrapedProduct dataclass with all extracted data.

    Raises:
        ValueError: If the page cannot be loaded.
        RuntimeError: If required product data is missing.
    """
    driver = _build_driver()
    try:
        driver.get(url)
        wait = WebDriverWait(driver, settings.scraper_timeout)

        product_id = _extract_product_id(url)
        info = _scrape_product_info(driver, wait)

        reviews = _scrape_reviews(driver, url, wait)
        logger.info(
            "Scraped product '%s' (id=%s): %d reviews",
            info["product_name"],
            product_id,
            len(reviews),
        )

        return ScrapedProduct(
            product_id=product_id,
            product_name=info["product_name"],
            category=info["category"],
            description=info["description"],
            reviews=reviews,
        )
    finally:
        driver.quit()
