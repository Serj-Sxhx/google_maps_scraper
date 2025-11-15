import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import io

# Page config
st.set_page_config(
    page_title="Google Maps Business Scraper",
    page_icon="🗺️",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🗺️ Google Maps Business Scraper</h1>', unsafe_allow_html=True)

# Initialize session state
if 'scraping_complete' not in st.session_state:
    st.session_state.scraping_complete = False
if 'results_df' not in st.session_state:
    st.session_state.results_df = None

def setup_driver():
    """Setup Chrome driver with options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    return driver

def scrape_google_maps(keywords, location, max_results_per_keyword, progress_bar, status_text, log_container=None):
    """Scrape Google Maps for business information"""
    all_results = []
    total_keywords = len(keywords)
    logs = []  # Store logs for browser display
    
    def log(message, also_print=True):
        """Log to both console and browser"""
        if also_print:
            print(message)
        logs.append(message)
        if log_container:
            # Display last 50 logs in browser
            log_container.text_area("Debug Logs", "\n".join(logs[-50:]), height=400, key=f"logs_{len(logs)}")
    
    # Log: Driver initialization
    log(f"\n{'='*80}")
    log(f"[INIT] Starting scraper with {total_keywords} keywords")
    log(f"[INIT] Location: {location}")
    log(f"[INIT] Max results per keyword: {max_results_per_keyword}")
    log(f"{'='*80}\n")
    
    driver = setup_driver()
    log(f"[DRIVER] Chrome driver initialized successfully")
    
    try:
        for idx, keyword in enumerate(keywords):
            log(f"\n{'='*80}")
            log(f"[KEYWORD {idx+1}/{total_keywords}] Processing: '{keyword}'")
            log(f"{'='*80}")
            
            status_text.text(f"🔍 Scraping: {keyword} in {location}...")
            
            # Build search URL
            search_query = f"{keyword} in {location}"
            url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            log(f"[URL] Constructed search URL: {url}")
            
            log(f"[NAV] Navigating to URL...")
            driver.get(url)
            log(f"[NAV] Page loaded, current URL: {driver.current_url}")
            
            # Wait for page to fully load and results to populate
            # Using longer wait time as proven in working code (main_scraper.py line 36)
            log(f"[WAIT] Waiting 15 seconds for page to fully load...")
            time.sleep(15)
            log(f"[WAIT] Wait complete")
            
            # Verify the results container loaded
            # This XPath matches the working code pattern (main_scraper.py line 42)
            log(f"[CONTAINER] Searching for results container with XPath: '//div[contains(@aria-label, \"Results for\")]'")
            try:
                results_container = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
                aria_label = results_container.get_attribute("aria-label")
                log(f"[CONTAINER] ✓ Results container found! aria-label: '{aria_label}'")
            except Exception as e:
                # If results container doesn't load, skip this keyword
                log(f"[CONTAINER] ✗ FAILED to find results container")
                log(f"[CONTAINER] Exception: {str(e)}")
                log(f"[CONTAINER] Page source length: {len(driver.page_source)} characters")
                log(f"[CONTAINER] Skipping keyword '{keyword}'")
                status_text.text(f"⚠️ Could not find results for: {keyword} in {location}")
                continue
            
            # Scroll to load more results
            # Using the proven XPath selector from working code (main_scraper.py line 42)
            results_count = 0
            scroll_attempts = 0
            max_scroll_attempts = max_results_per_keyword // 20 + 3
            
            log(f"\n[SCROLL] Starting scroll phase - max attempts: {max_scroll_attempts}, target results: {max_results_per_keyword}")
            
            while scroll_attempts < max_scroll_attempts and results_count < max_results_per_keyword:
                try:
                    # Find all result elements using the working XPath selector
                    # This selector scopes to the results sidebar container (main_scraper.py line 42, 108, 114)
                    xpath_selector = '//div[contains(@aria-label, "Results for")]/div/div[./a]'
                    log(f"[SCROLL] Attempt {scroll_attempts + 1}/{max_scroll_attempts} - Finding elements with XPath: '{xpath_selector}'")
                    elements = driver.find_elements(By.XPATH, xpath_selector)
                    
                    if elements:
                        log(f"[SCROLL] ✓ Found {len(elements)} elements")
                        # Scroll to last element to load more results
                        # Using the proven pattern from working code (main_scraper.py line 43)
                        last_element = elements[-1]
                        log(f"[SCROLL] Scrolling to last element (index {len(elements)-1})...")
                        driver.execute_script("arguments[0].scrollIntoView();", last_element)
                        # Use longer wait time as in working code (main_scraper.py line 45)
                        log(f"[SCROLL] Waiting 5 seconds after scroll...")
                        time.sleep(5)
                        
                        results_count = len(elements)
                        scroll_attempts += 1
                        log(f"[SCROLL] Current results count: {results_count}")
                    else:
                        # No elements found, stop scrolling
                        log(f"[SCROLL] ✗ No elements found, stopping scroll")
                        break
                except Exception as e:
                    log(f"[SCROLL] ✗ Exception during scroll: {str(e)}")
                    break
            
            log(f"[SCROLL] Scroll phase complete - Total elements found: {results_count}")
            
            # Extract data from each listing
            # Re-fetch elements using the same working XPath selector (main_scraper.py line 114)
            log(f"\n[EXTRACT] Re-fetching elements for data extraction...")
            elements = driver.find_elements(By.XPATH, '//div[contains(@aria-label, "Results for")]/div/div[./a]')
            log(f"[EXTRACT] Found {len(elements)} elements to process")
            log(f"[EXTRACT] Will process up to {min(len(elements), max_results_per_keyword)} elements")
            
            for i, element in enumerate(elements[:max_results_per_keyword]):
                if i >= max_results_per_keyword:
                    break
                
                log(f"\n[ITEM {i+1}/{min(len(elements), max_results_per_keyword)}] Processing element at index {i}")
                    
                try:
                    # Click on the listing to load details
                    # Re-fetch elements to avoid stale element reference (main_scraper.py line 117)
                    # Use retry logic from working code (main_scraper.py line 115-126)
                    retry_count = 0
                    max_retries = 3
                    click_successful = False
                    
                    log(f"[CLICK] Starting click attempts (max retries: {max_retries})")
                    
                    while retry_count < max_retries:
                        try:
                            # Re-fetch elements to avoid stale references
                            log(f"[CLICK] Retry {retry_count + 1}/{max_retries} - Re-fetching elements...")
                            current_elements = driver.find_elements(By.XPATH, '//div[contains(@aria-label, "Results for")]/div/div[./a]')
                            log(f"[CLICK] Found {len(current_elements)} elements")
                            
                            if i >= len(current_elements):
                                log(f"[CLICK] ✗ Index {i} out of range (only {len(current_elements)} elements)")
                                break
                            
                            # Click the element at index i
                            log(f"[CLICK] Attempting to click element at index {i}...")
                            current_elements[i].click()
                            log(f"[CLICK] ✓ Click successful!")
                            
                            # Use longer wait time as in working code (main_scraper.py line 118)
                            log(f"[CLICK] Waiting 5 seconds for details to load...")
                            time.sleep(5)
                            click_successful = True
                            break  # Click succeeded, exit retry loop
                            
                        except Exception as click_error:
                            # If click fails, scroll to the CORRECT element at index i and retry
                            retry_count += 1
                            log(f"[CLICK] ✗ Click failed: {str(click_error)}")
                            
                            if retry_count < max_retries:
                                try:
                                    # Scroll to element at index i (not [-1])
                                    log(f"[CLICK] Attempting to scroll to element at index {i}...")
                                    elem = driver.find_elements(By.XPATH, '//div[contains(@aria-label, "Results for")]/div/div[./a]')[i]
                                    driver.execute_script("arguments[0].scrollIntoView();", elem)
                                    log(f"[CLICK] Scroll successful, waiting 5 seconds...")
                                    time.sleep(5)
                                    # Continue loop to retry the click
                                except Exception as scroll_error:
                                    # If scroll fails, exit retry loop
                                    log(f"[CLICK] ✗ Scroll failed: {str(scroll_error)}")
                                    break
                            else:
                                # Max retries reached, exit retry loop
                                log(f"[CLICK] ✗ Max retries reached, giving up on this element")
                                break
                    
                    if not click_successful:
                        log(f"[ITEM {i+1}] ✗ Failed to click element, skipping...")
                        continue
                    
                    item = {}
                    log(f"[DATA] Extracting business data...")
                    
                    # Extract name
                    try:
                        item['name'] = driver.find_element(By.CSS_SELECTOR, "h1.fontHeadlineLarge").text
                        log(f"[DATA] ✓ Name: '{item['name']}'")
                    except Exception as e:
                        item['name'] = ""
                        log(f"[DATA] ✗ Name extraction failed: {str(e)}")
                    
                    # Extract link
                    try:
                        item['link'] = driver.current_url
                        log(f"[DATA] ✓ Link: {item['link']}")
                    except Exception as e:
                        item['link'] = ""
                        log(f"[DATA] ✗ Link extraction failed: {str(e)}")
                    
                    # Extract rating
                    try:
                        item['rating'] = driver.find_element(By.CSS_SELECTOR, "div[jsaction='pane.rating.moreReviews']").text.split('\n')[0]
                        log(f"[DATA] ✓ Rating: {item['rating']}")
                    except Exception as e:
                        item['rating'] = ""
                        log(f"[DATA] ✗ Rating extraction failed: {str(e)}")
                    
                    # Extract reviews
                    try:
                        reviews_text = driver.find_element(By.CSS_SELECTOR, 'button[jsaction="pane.rating.moreReviews"]').text
                        item['reviews'] = reviews_text.split()[0].replace('(', '').replace(')', '')
                        log(f"[DATA] ✓ Reviews: {item['reviews']}")
                    except Exception as e:
                        item['reviews'] = ""
                        log(f"[DATA] ✗ Reviews extraction failed: {str(e)}")
                    
                    # Extract status
                    try:
                        item['status'] = driver.find_element(By.CSS_SELECTOR, "span.ZDu9vd").text.split('·')[0].strip()
                        log(f"[DATA] ✓ Status: {item['status']}")
                    except Exception as e:
                        item['status'] = ""
                        log(f"[DATA] ✗ Status extraction failed: {str(e)}")
                    
                    # Extract address
                    try:
                        address_elem = driver.find_element(By.CSS_SELECTOR, "button[data-item-id='address']")
                        item['address'] = address_elem.get_attribute("aria-label").split(":")[-1].strip()
                        log(f"[DATA] ✓ Address: {item['address']}")
                    except Exception as e:
                        item['address'] = ""
                        log(f"[DATA] ✗ Address extraction failed: {str(e)}")
                    
                    # Extract website
                    try:
                        item['website'] = driver.find_element(By.CSS_SELECTOR, "a[data-tooltip='Open website']").get_attribute("href")
                        log(f"[DATA] ✓ Website: {item['website']}")
                    except Exception as e:
                        item['website'] = ""
                        log(f"[DATA] ✗ Website extraction failed: {str(e)}")
                    
                    # Extract phone
                    try:
                        phone_elem = driver.find_element(By.CSS_SELECTOR, "button[data-item-id*='phone']")
                        item['phone'] = phone_elem.get_attribute("aria-label").split(":")[-1].strip()
                        log(f"[DATA] ✓ Phone: {item['phone']}")
                    except Exception as e1:
                        try:
                            item['phone'] = driver.find_element(By.CSS_SELECTOR, "button[data-tooltip='Copy phone number']").get_attribute("aria-label").split(":")[-1].strip()
                            log(f"[DATA] ✓ Phone (fallback): {item['phone']}")
                        except Exception as e2:
                            item['phone'] = ""
                            log(f"[DATA] ✗ Phone extraction failed: {str(e1)}, fallback also failed: {str(e2)}")
                    
                    # Extract opening hours
                    try:
                        item['opening_hours'] = driver.find_element(By.CSS_SELECTOR, "div.t39EBf.GUrTXd").get_attribute("aria-label")
                        log(f"[DATA] ✓ Opening hours: {item['opening_hours']}")
                    except Exception as e:
                        item['opening_hours'] = ""
                        log(f"[DATA] ✗ Opening hours extraction failed: {str(e)}")
                    
                    item['keyword'] = keyword
                    item['location'] = location
                    item['scraped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if item['name']:  # Only add if we got at least a name
                        all_results.append(item)
                        log(f"[ITEM {i+1}] ✓ Successfully added to results (Total: {len(all_results)})")
                    else:
                        log(f"[ITEM {i+1}] ✗ Skipped - no name extracted")
                    
                    # Update status
                    status_text.text(f"🔍 Scraping: {keyword} in {location} - Found {len(all_results)} businesses")
                    
                except Exception as e:
                    log(f"[ITEM {i+1}] ✗ Exception during extraction: {str(e)}")
                    continue
            
            # Update progress bar
            progress_bar.progress((idx + 1) / total_keywords)
            
            log(f"\n[KEYWORD {idx+1}/{total_keywords}] Complete - Collected {len([r for r in all_results if r['keyword'] == keyword])} results for '{keyword}'")
            log(f"[SUMMARY] Total results so far: {len(all_results)}")
            
    finally:
        log(f"\n{'='*80}")
        log(f"[CLEANUP] Closing Chrome driver...")
        driver.quit()
        log(f"[CLEANUP] Driver closed")
        log(f"{'='*80}\n")
    
    log(f"\n{'='*80}")
    log(f"[FINAL] Scraping complete!")
    log(f"[FINAL] Total results collected: {len(all_results)}")
    log(f"[FINAL] Keywords processed: {total_keywords}")
    if all_results:
        log(f"[FINAL] Results breakdown by keyword:")
        for kw in keywords:
            count = len([r for r in all_results if r['keyword'] == kw])
            log(f"[FINAL]   - '{kw}': {count} results")
    else:
        log(f"[FINAL] ⚠️ WARNING: No results collected!")
    log(f"{'='*80}\n")
    
    return all_results

# Main UI
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("### 📝 Search Parameters")
    
    with st.form("scraper_form"):
        keywords_input = st.text_area(
            "Keywords (one per line)",
            value="Coworking spaces\nMakerspaces\nHackerspaces",
            height=150,
            help="Enter one keyword per line"
        )
        
        location = st.text_input(
            "Location",
            value="Taipei",
            help="City or region to search in"
        )
        
        max_results = st.slider(
            "Max results per keyword",
            min_value=10,
            max_value=100,
            value=20,
            step=10,
            help="Maximum number of results to scrape for each keyword"
        )
        
        submit_button = st.form_submit_button("🚀 Start Scraping", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("### ℹ️ About")
    st.markdown("""
    This tool scrapes Google Maps for business contact information.
    
    **Extracted Data:**
    - Business Name
    - Phone Number
    - Website
    - Address
    - Rating & Reviews
    - Opening Hours
    - Status
    
    **Note:** Scraping may take several minutes depending on the number of keywords and results.
    """)
    st.markdown('</div>', unsafe_allow_html=True)

# Scraping logic
if submit_button:
    keywords_list = [k.strip() for k in keywords_input.split('\n') if k.strip()]
    
    if not keywords_list:
        st.error("❌ Please enter at least one keyword")
    elif not location:
        st.error("❌ Please enter a location")
    else:
        st.session_state.scraping_complete = False
        st.session_state.results_df = None
        
        st.markdown("---")
        st.markdown("### 🔄 Scraping in Progress...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create expandable log container
        with st.expander("🔍 Debug Logs (Click to expand)", expanded=False):
            log_container = st.empty()
        
        try:
            results = scrape_google_maps(keywords_list, location, max_results, progress_bar, status_text, log_container)
            
            if results:
                df = pd.DataFrame(results)
                st.session_state.results_df = df
                st.session_state.scraping_complete = True
                
                status_text.text(f"✅ Scraping complete! Found {len(results)} businesses")
                progress_bar.progress(1.0)
                
            else:
                st.warning("⚠️ No results found. Try different keywords or location.")
                
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            st.error("Please try again or adjust your search parameters.")

# Display results
if st.session_state.scraping_complete and st.session_state.results_df is not None:
    st.markdown("---")
    st.markdown("### 📊 Results Preview")
    
    df = st.session_state.results_df
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Results", len(df))
    with col2:
        st.metric("With Phone", df['phone'].notna().sum())
    with col3:
        st.metric("With Website", df['website'].notna().sum())
    with col4:
        # Extract rating calculation outside f-string to avoid backslash in f-string expression
        try:
            avg_rating = df['rating'].str.extract(r'(\d+\.?\d*)')[0].astype(float).mean()
            rating_display = f"{avg_rating:.1f}" if not pd.isna(avg_rating) else "N/A"
        except:
            rating_display = "N/A"
        st.metric("Avg Rating", rating_display)
    
    # Preview table
    st.dataframe(df.head(10), use_container_width=True)
    
    # Download button
    csv = df.to_csv(index=False).encode('utf-8')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"google_maps_scrape_{timestamp}.csv"
    
    st.download_button(
        label="📥 Download Full CSV",
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=True
    )
    
    st.success(f"✅ Ready to download! File contains {len(df)} business records.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <small>💡 For CRM import, use the CSV download button above. | ⚠️ Use responsibly and respect Google's Terms of Service</small>
</div>
""", unsafe_allow_html=True)
