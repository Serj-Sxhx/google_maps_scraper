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

def scrape_google_maps(keywords, location, max_results_per_keyword, progress_bar, status_text):
    """Scrape Google Maps for business information"""
    all_results = []
    total_keywords = len(keywords)
    
    driver = setup_driver()
    
    try:
        for idx, keyword in enumerate(keywords):
            status_text.text(f"🔍 Scraping: {keyword} in {location}...")
            
            # Build search URL
            search_query = f"{keyword} in {location}"
            url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            
            driver.get(url)
            time.sleep(5)
            
            # Scroll to load more results
            results_count = 0
            scroll_attempts = 0
            max_scroll_attempts = max_results_per_keyword // 20 + 3
            
            while scroll_attempts < max_scroll_attempts and results_count < max_results_per_keyword:
                try:
                    # Find all result elements
                    elements = driver.find_elements(By.XPATH, '//div[contains(@aria-label, "Results for")]/div/div[./a]')
                    
                    if elements:
                        last_element = elements[-1]
                        driver.execute_script("arguments[0].scrollIntoView();", last_element)
                        time.sleep(3)
                        results_count = len(elements)
                        scroll_attempts += 1
                    else:
                        break
                except Exception as e:
                    break
            
            # Extract data from each listing
            elements = driver.find_elements(By.XPATH, '//div[contains(@aria-label, "Results for")]/div/div[./a]')
            
            for i, element in enumerate(elements[:max_results_per_keyword]):
                if i >= max_results_per_keyword:
                    break
                    
                try:
                    # Click on the listing
                    elements[i].click()
                    time.sleep(2)
                    
                    item = {}
                    
                    # Extract name
                    try:
                        item['name'] = driver.find_element(By.CSS_SELECTOR, "h1.fontHeadlineLarge").text
                    except:
                        item['name'] = ""
                    
                    # Extract link
                    try:
                        item['link'] = driver.current_url
                    except:
                        item['link'] = ""
                    
                    # Extract rating
                    try:
                        item['rating'] = driver.find_element(By.CSS_SELECTOR, "div[jsaction='pane.rating.moreReviews']").text.split('\n')[0]
                    except:
                        item['rating'] = ""
                    
                    # Extract reviews
                    try:
                        reviews_text = driver.find_element(By.CSS_SELECTOR, 'button[jsaction="pane.rating.moreReviews"]').text
                        item['reviews'] = reviews_text.split()[0].replace('(', '').replace(')', '')
                    except:
                        item['reviews'] = ""
                    
                    # Extract status
                    try:
                        item['status'] = driver.find_element(By.CSS_SELECTOR, "span.ZDu9vd").text.split('·')[0].strip()
                    except:
                        item['status'] = ""
                    
                    # Extract address
                    try:
                        address_elem = driver.find_element(By.CSS_SELECTOR, "button[data-item-id='address']")
                        item['address'] = address_elem.get_attribute("aria-label").split(":")[-1].strip()
                    except:
                        item['address'] = ""
                    
                    # Extract website
                    try:
                        item['website'] = driver.find_element(By.CSS_SELECTOR, "a[data-tooltip='Open website']").get_attribute("href")
                    except:
                        item['website'] = ""
                    
                    # Extract phone
                    try:
                        phone_elem = driver.find_element(By.CSS_SELECTOR, "button[data-item-id*='phone']")
                        item['phone'] = phone_elem.get_attribute("aria-label").split(":")[-1].strip()
                    except:
                        try:
                            item['phone'] = driver.find_element(By.CSS_SELECTOR, "button[data-tooltip='Copy phone number']").get_attribute("aria-label").split(":")[-1].strip()
                        except:
                            item['phone'] = ""
                    
                    # Extract opening hours
                    try:
                        item['opening_hours'] = driver.find_element(By.CSS_SELECTOR, "div.t39EBf.GUrTXd").get_attribute("aria-label")
                    except:
                        item['opening_hours'] = ""
                    
                    item['keyword'] = keyword
                    item['location'] = location
                    item['scraped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if item['name']:  # Only add if we got at least a name
                        all_results.append(item)
                    
                    # Update status
                    status_text.text(f"🔍 Scraping: {keyword} in {location} - Found {len(all_results)} businesses")
                    
                except Exception as e:
                    continue
                
                # Re-fetch elements for next iteration
                elements = driver.find_elements(By.XPATH, '//div[contains(@aria-label, "Results for")]/div/div[./a]')
            
            # Update progress bar
            progress_bar.progress((idx + 1) / total_keywords)
            
    finally:
        driver.quit()
    
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
        
        try:
            results = scrape_google_maps(keywords_list, location, max_results, progress_bar, status_text)
            
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
