from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
import os
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime

# Constants
CHROME_DRIVER_PATH = '/usr/bin/chromedriver'
JUNK_FILE_SIZE = 2252  # 2.2 KiB
JUNK_PATTERNS = (
    "Status: 404, NOT FOUND",
    "Search Error",
    "Please try again",
    "No records found",
    "No matches found"
)
USER_AGENT = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,115)}.0.0.0 Safari/537.36"
BASE_URL = 'https://www.zabasearch.com/'
RESULTS_DIR = 'results'
LOG_DIR = 'logs'
MAX_RETRIES = 3
BLACKLIST_FILE = 'blacklist.txt'

# Configure logging
def setup_logging():
    """Configure logging system."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_filename = datetime.now().strftime('zabasearch_%Y%m%d_%H%M%S.log')
    log_filepath = os.path.join(LOG_DIR, log_filename)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filepath),
            logging.StreamHandler()
        ]
    )

def human_delay(min_delay: float = 0.5, max_delay: float = 2.5) -> None:
    """Random delay to mimic human behavior."""
    delay = random.uniform(min_delay, max_delay)
    logging.debug(f"Human delay: {delay:.2f} seconds")
    time.sleep(delay)

def is_junk_file(file_path: str) -> bool:
    """Check if file is junk based on size."""
    try:
        return os.path.getsize(file_path) == JUNK_FILE_SIZE
    except OSError as e:
        logging.warning(f"Error checking file size for {file_path}: {e}")
        return False

def is_junk_content(content: str) -> bool:
    """Check if content contains junk patterns."""
    return any(pattern in content for pattern in JUNK_PATTERNS)

def check_and_remove_junk_files(filename: str) -> bool:
    """Check and remove junk files."""
    filepath = os.path.join(RESULTS_DIR, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                if is_junk_file(filepath) or is_junk_content(content):
                    logging.info(f"Removing junk file: {filepath}")
                    os.remove(filepath)
                    return True
        except OSError as e:
            logging.error(f"Error checking junk file {filepath}: {e}")
    return False

def extract_relevant_info(content: str) -> str:
    """Extract specified fields from Zabasearch results."""
    try:
        soup = BeautifulSoup(content, 'html.parser')
        relevant_info = []
        email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+')
        
        for person in soup.find_all('div', class_='person'):
            # Extract name
            if name_tag := person.find('h2'):
                if name_a := name_tag.a:
                    relevant_info.append(f"Name: {name_a.get_text(strip=True)}")
            
            # Extract age
            if age_tag := person.find('h3'):
                relevant_info.append(f"Age: {age_tag.get_text(strip=True)}")
            
            # Extract AKA/Aliases
            if aka_div := person.find('div', id='container-alt-names'):
                aliases = [li.get_text(strip=True) for li in aka_div.find_all('li')]
                if aliases:
                    relevant_info.append("AKA: " + ", ".join(aliases))
            
            # Extract phone numbers
            if phones_div := person.find('h3', string='Associated Phone Numbers'):
                if phones_ul := phones_div.find_next('ul'):
                    phones = [a.get_text(strip=True) for a in phones_ul.find_all('a')]
                    if phones:
                        relevant_info.append("Associated Phone Numbers: " + ", ".join(phones))
            
            # Extract email addresses
            if emails_div := person.find('h3', string='Associated Email Addresses'):
                if emails_ul := emails_div.find_next('ul'):
                    emails = [
                        email_match.group(0)
                        for li in emails_ul.find_all('li')
                        if '@' in (email_text := li.get_text(strip=True))
                        for email_match in [email_pattern.search(email_text)]
                        if email_match
                    ]
                    if emails:
                        relevant_info.append("Associated Email Addresses: " + ", ".join(emails))
            
            # Extract last known address
            if address_div := person.find('h3', string='Last Known Address'):
                if address_p := address_div.find_next('p'):
                    address = address_p.get_text(" ", strip=True).replace("\n", "").replace("  ", " ")
                    relevant_info.append("Last Known Address: " + address)
            
            # Extract past addresses
            if past_addresses_div := person.find('h3', string='Past Addresses'):
                if past_addresses_ul := past_addresses_div.find_next('ul'):
                    past_addresses = [
                        li.get_text(" ", strip=True).replace("\n", " ").replace("  ", " ")
                        for li in past_addresses_ul.find_all('li')
                    ]
                    if past_addresses:
                        relevant_info.append("Past Addresses:\n" + "\n".join(past_addresses))
            
            relevant_info.append("\n" + "-"*50 + "\n")
        
        # Remove last separator if exists
        if relevant_info and relevant_info[-1].strip() == '-'*50:
            relevant_info = relevant_info[:-1]
        
        return '\n'.join(relevant_info)
    except Exception as e:
        logging.error(f"Error extracting relevant info: {e}")
        return ""

def save_results(filename: str, content: str) -> bool:
    """Save filtered results to file."""
    if not content or is_junk_content(content):
        logging.info(f"Not saving junk content to {filename}")
        return False
    
    try:
        # Create results directory if it doesn't exist
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        # Prepend the directory to the filename
        filepath = os.path.join(RESULTS_DIR, filename)
        
        filtered_content = extract_relevant_info(content)
        if not filtered_content:
            logging.warning(f"No relevant information found for {filename}")
            return False
            
        with open(filepath, 'w') as f:
            f.write(filtered_content)
        
        if is_junk_file(filepath) or is_junk_content(open(filepath).read()):
            logging.info(f"Removing junk file after verification: {filepath}")
            os.remove(filepath)
            return False
            
        logging.info(f"Successfully saved results to {filepath}")
        return True
    except OSError as e:
        logging.error(f"Error saving results: {e}")
        return False

def read_input_from_file(file_path: str) -> List[Dict[str, str]]:
    """Read input data from file with improved error handling."""
    try:
        with open(file_path, 'r') as file:
            entries = []
            for line_num, line in enumerate(file, 1):
                try:
                    if line.startswith(("First Name", "first_name")) or not line.strip():
                        continue
                        
                    # Handle both CSV and tab-delimited
                    delimiter = '\t' if '\t' in line else ','
                    parts = [p.strip() for p in line.strip().split(delimiter)]
                    
                    if len(parts) >= 2:
                        entries.append({
                            'first_name': parts[0],
                            'last_name': parts[1],
                            'city': parts[2] if len(parts) > 2 else "",
                            'state': parts[3] if len(parts) > 3 else "",
                            'original_line': line_num  # Track original line for reference
                        })
                except Exception as e:
                    logging.warning(f"Error parsing line {line_num}: {e}")
            return entries
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        return []

def handle_consent_modal(driver: webdriver.Chrome) -> bool:
    """Handle consent modal if it appears."""
    try:
        # Try to find and close the modal using different approaches
        try:
            # First approach - click agree button directly
            agree_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".inside-copy")))
            driver.execute_script("arguments[0].click();", agree_button)
            human_delay()
            logging.info("Consent modal handled (direct click)")
            return True
        except TimeoutException:
            # Second approach - check checkbox then click agree
            checkbox = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#security-check .check-wrapper")))
            driver.execute_script("arguments[0].click();", checkbox)
            logging.info("Waiting 10 seconds after checking consent box...")
            time.sleep(10)  # Added 10-second delay after checking the box
            
            agree_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".inside-copy")))
            driver.execute_script("arguments[0].click();", agree_button)
            human_delay()
            logging.info("Consent modal handled (checkbox + click)")
            return True
            
    except Exception as e:
        logging.error(f"Error handling consent modal: {str(e)}")
        # Try refreshing the page as a fallback
        try:
            driver.refresh()
            human_delay(2, 3)
            logging.info("Refreshed page as fallback for consent modal")
            return True
        except Exception as refresh_error:
            logging.error(f"Failed to refresh page: {refresh_error}")
            return False

def perform_search(input_data: Dict[str, str], driver: webdriver.Chrome) -> Optional[str]:
    """Perform search with given input data."""
    def fill_field(selector: str, value: str) -> bool:
        for attempt in range(3):
            try:
                field = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                field.clear()
                field.send_keys(value)
                human_delay(0.5, 1.5)
                logging.debug(f"Filled field {selector} with {value}")
                return True
            except Exception as e:
                if attempt == 2:
                    logging.error(f"Failed to fill {selector}: {e}")
                    return False
                time.sleep(1)
        return False
    
    try:
        logging.info(f"Starting search for {input_data['first_name']} {input_data['last_name']}")
        
        if not fill_field(".search-first-name", input_data['first_name']):
            return None
        if not fill_field(".search-last-name", input_data['last_name']):
            return None
            
        if input_data['city']:
            fill_field(".search-city", input_data['city'])
            logging.debug(f"Filled city: {input_data['city']}")
            
        if input_data['state']:
            try:
                state_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".search-state")))
                Select(state_element).select_by_visible_text(input_data['state'])
                human_delay(1, 2)
                logging.debug(f"Selected state: {input_data['state']}")
            except Exception as e:
                logging.warning(f"Couldn't select state: {e}")

        for attempt in range(2):
            try:
                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".button-search")))
                search_button.click()
                logging.debug("Clicked search button")
                break
            except:
                if attempt == 1:
                    logging.error("Failed to submit search form")
                    return None
                time.sleep(2)

        try:
            WebDriverWait(driver, random.uniform(5, 10)).until(
                lambda d: "results" in d.current_url.lower() or 
                d.find_elements(By.CSS_SELECTOR, ".results-container"))
            logging.debug("Search results page loaded")
        except:
            logging.warning("Timeout waiting for results page, continuing anyway")
            pass

        # Check for 404 after getting page source
        page_source = driver.page_source
        if "Status: 404, NOT FOUND" in page_source:
            full_name = f"{input_data['first_name']} {input_data['last_name']}"
            update_blacklist(full_name)
            return None
            
        return page_source

    except Exception as e:
        logging.error(f"Search error: {e}")
        screenshot_name = f"search_error_{time.time()}.png"
        driver.save_screenshot(screenshot_name)
        logging.info(f"Saved screenshot to {screenshot_name}")
        return None

def create_driver() -> webdriver.Chrome:
    """Create and configure Chrome WebDriver."""
    try:
        service = Service(CHROME_DRIVER_PATH)
        options = webdriver.ChromeOptions()
        
        # Headless mode settings
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f"user-agent={USER_AGENT}")
        
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": USER_AGENT})
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logging.info("WebDriver created successfully")
        return driver
    except Exception as e:
        logging.error(f"Error creating WebDriver: {e}")
        raise

def reset_browser(driver: webdriver.Chrome) -> bool:
    """Reset the browser by clearing cookies and refreshing."""
    try:
        driver.delete_all_cookies()
        driver.get(BASE_URL)
        human_delay(2, 3)
        logging.info("Browser reset successfully")
        return True
    except Exception as e:
        logging.error(f"Error resetting browser: {e}")
        return False

def update_blacklist(name: str) -> None:
    """Add a name to the blacklist file."""
    try:
        with open(BLACKLIST_FILE, 'a') as f:
            f.write(f"{name}\n")
        logging.info(f"Added {name} to blacklist")
    except Exception as e:
        logging.error(f"Error updating blacklist: {e}")

def is_blacklisted(name: str) -> bool:
    """Check if name is in blacklist."""
    try:
        if not os.path.exists(BLACKLIST_FILE):
            return False
        with open(BLACKLIST_FILE, 'r') as f:
            return name.lower() in [line.strip().lower() for line in f]
    except Exception as e:
        logging.error(f"Error checking blacklist: {e}")
        return False

def scan_log_for_errors(log_filepath: str) -> Dict[str, List[str]]:
    """Scan log file for errors and return categorized information."""
    results = {
        'errors': [],
        'failed_searches': [],
        'completed_searches': [],
        'blacklisted_searches': []
    }
    
    try:
        with open(log_filepath, 'r') as f:
            for line in f:
                if 'ERROR' in line:
                    results['errors'].append(line.strip())
                elif 'No results returned from search' in line:
                    if 'Starting search for' in line:
                        name = line.split('Starting search for')[-1].strip()
                        results['failed_searches'].append(name)
                elif 'Successfully saved valid results to' in line:
                    filename = line.split('results/zaba_results_')[-1].split('.txt')[0]
                    first, last = filename.split('_')[:2]
                    results['completed_searches'].append(f"{first} {last}")
                elif 'Added to blacklist' in line:
                    name = line.split('Added ')[-1].split(' to blacklist')[0]
                    results['blacklisted_searches'].append(name)
    
    except Exception as e:
        logging.error(f"Error scanning log file: {e}")
    
    return results

def get_latest_log_file() -> Optional[str]:
    """Get the most recent log file path."""
    try:
        log_files = [f for f in os.listdir(LOG_DIR) if f.startswith('zabasearch_') and f.endswith('.log')]
        if not log_files:
            return None
        log_files.sort(reverse=True)
        return os.path.join(LOG_DIR, log_files[0])
    except Exception as e:
        logging.error(f"Error finding log files: {e}")
        return None

def get_failed_searches_from_logs() -> List[str]:
    """Get all failed searches from all log files."""
    failed_searches = set()
    try:
        for log_file in os.listdir(LOG_DIR):
            if log_file.startswith('zabasearch_') and log_file.endswith('.log'):
                with open(os.path.join(LOG_DIR, log_file), 'r') as f:
                    for line in f:
                        if 'No results returned from search' in line and 'Starting search for' in line:
                            name = line.split('Starting search for')[-1].strip()
                            failed_searches.add(name)
    except Exception as e:
        logging.error(f"Error reading failed searches from logs: {e}")
    return list(failed_searches)

def compare_with_input(input_data: List[Dict[str, str]], log_scan: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Compare log scan results with input data to identify pending searches."""
    completed_names = set(log_scan['completed_searches'])
    failed_names = set(log_scan['failed_searches'])
    blacklisted_names = set(log_scan['blacklisted_searches'])
    
    pending_searches = []
    for entry in input_data:
        full_name = f"{entry['first_name']} {entry['last_name']}"
        if (full_name not in completed_names and 
            full_name not in failed_names and 
            full_name not in blacklisted_names):
            pending_searches.append(full_name)
    
    return {
        'pending_searches': pending_searches,
        'completed_searches': list(completed_names),
        'failed_searches': list(failed_names),
        'blacklisted_searches': list(blacklisted_names),
        'errors': log_scan['errors']
    }

def filter_input_for_retry(input_data: List[Dict[str, str]], status_report: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """Filter input data to only include searches that need retrying."""
    # Get names from status report
    completed_names = set(status_report['completed_searches'])
    failed_names = set(status_report['failed_searches'])
    blacklisted_names = set(status_report['blacklisted_searches'])
    
    # Also check all logs for any additional failures
    log_failed_names = set(get_failed_searches_from_logs())
    all_failed_names = failed_names.union(log_failed_names)
    
    # Track retry counts
    retry_counts = {}
    for entry in input_data:
        full_name = f"{entry['first_name']} {entry['last_name']}"
        retry_counts[full_name] = retry_counts.get(full_name, 0) + 1
    
    # Find entries that either failed or weren't completed
    retry_entries = []
    for entry in input_data:
        full_name = f"{entry['first_name']} {entry['last_name']}"
        
        # Skip if blacklisted
        if is_blacklisted(full_name):
            continue
            
        # Skip if already completed
        if full_name in completed_names:
            continue
            
        # Only retry if under max retries
        if retry_counts[full_name] <= MAX_RETRIES:
            retry_entries.append(entry)
    
    return retry_entries

def generate_status_report(comparison_results: Dict[str, List[str]], report_file: str = 'search_status_report.txt') -> None:
    """Generate a status report file based on comparison results."""
    try:
        with open(report_file, 'w') as f:
            f.write("=== ZabaSearch Automation Status Report ===\n\n")
            
            f.write(f"Total Errors Found: {len(comparison_results['errors'])}\n")
            if comparison_results['errors']:
                f.write("\nError Details:\n")
                f.write("\n".join(comparison_results['errors']) + "\n")
            
            f.write(f"\nCompleted Searches: {len(comparison_results['completed_searches'])}\n")
            if comparison_results['completed_searches']:
                f.write("\n".join(comparison_results['completed_searches']) + "\n")
            
            f.write(f"\nFailed Searches: {len(comparison_results['failed_searches'])}\n")
            if comparison_results['failed_searches']:
                f.write("\n".join(comparison_results['failed_searches']) + "\n")
            
            f.write(f"\nBlacklisted Searches (404): {len(comparison_results['blacklisted_searches'])}\n")
            if comparison_results['blacklisted_searches']:
                f.write("\n".join(comparison_results['blacklisted_searches']) + "\n")
            
            f.write(f"\nPending Searches: {len(comparison_results['pending_searches'])}\n")
            if comparison_results['pending_searches']:
                f.write("\n".join(comparison_results['pending_searches']) + "\n")
            
            logging.info(f"Status report generated: {report_file}")
    except Exception as e:
        logging.error(f"Error generating status report: {e}")

def main() -> None:
    """Main execution function with enhanced retry logic."""
    setup_logging()
    logging.info("Starting ZabaSearch automation script")
    
    try:
        file_path = input("Enter input file path: ").strip()
        logging.info(f"Reading input from file: {file_path}")
        original_input_data = read_input_from_file(file_path)
        
        if not original_input_data:
            logging.error("No valid input data found")
            return

        # Initialize blacklist file if it doesn't exist
        if not os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE, 'w'):
                pass

        # Check for existing status report
        status_report = {
            'errors': [],
            'completed_searches': [],
            'failed_searches': [],
            'blacklisted_searches': [],
            'pending_searches': []
        }
        
        if os.path.exists('search_status_report.txt'):
            with open('search_status_report.txt', 'r') as f:
                current_section = None
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('Error Details:'):
                        current_section = 'errors'
                    elif line.startswith('Completed Searches:'):
                        current_section = 'completed_searches'
                    elif line.startswith('Failed Searches:'):
                        current_section = 'failed_searches'
                    elif line.startswith('Blacklisted Searches (404):'):
                        current_section = 'blacklisted_searches'
                    elif line.startswith('Pending Searches:'):
                        current_section = 'pending_searches'
                    elif line.startswith('==='):
                        current_section = None
                    elif current_section == 'errors' and line:
                        status_report['errors'].append(line)
                    elif current_section == 'completed_searches' and line and not line.startswith('Completed Searches:'):
                        status_report['completed_searches'].append(line)
                    elif current_section == 'failed_searches' and line and not line.startswith('Failed Searches:'):
                        status_report['failed_searches'].append(line)
                    elif current_section == 'blacklisted_searches' and line and not line.startswith('Blacklisted Searches (404):'):
                        status_report['blacklisted_searches'].append(line)
                    elif current_section == 'pending_searches' and line and not line.startswith('Pending Searches:'):
                        status_report['pending_searches'].append(line)

        # Main processing loop with retries
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                logging.info(f"\nStarting retry attempt {attempt + 1} of {MAX_RETRIES}\n")
                
            input_data_list = filter_input_for_retry(original_input_data, status_report)
            
            if not input_data_list:
                logging.info("All searches completed successfully")
                break

            logging.info(f"Found {len(input_data_list)} entries to process (including retries)")
            
            for i, input_data in enumerate(input_data_list):
                full_name = f"{input_data['first_name']} {input_data['last_name']}"
                logging.info(f"Processing entry {i+1}/{len(input_data_list)} (Line {input_data.get('original_line', '?')}: {full_name}")
                
                # Create new driver for each search to ensure clean state
                driver = create_driver()
                try:
                    logging.info("Navigating to base URL")
                    driver.get(BASE_URL)
                    human_delay()
                    
                    if not handle_consent_modal(driver):
                        logging.warning("Failed to handle consent modal. Creating new browser session...")
                        if not reset_browser(driver):
                            logging.error("Failed to reset browser. Skipping this search...")
                            continue

                    # Add 10-second delay after consent modal but before searching
                    logging.info("Waiting 10 seconds before performing search...")
                    time.sleep(10)

                    filename = f"zaba_results_{input_data['first_name']}_{input_data['last_name']}.txt"
                    check_and_remove_junk_files(filename)
                    
                    if results := perform_search(input_data, driver):
                        if save_results(filename, results):
                            logging.info(f"Successfully saved valid results to {os.path.join(RESULTS_DIR, filename)}")
                        else:
                            logging.info(f"Results not saved - detected as junk")
                    else:
                        logging.warning("No results returned from search")

                    if i < len(input_data_list) - 1:
                        delay = random.randint(15, 45)
                        logging.info(f"Waiting {delay} seconds before next search...")
                        time.sleep(delay)
                except Exception as e:
                    logging.error(f"Error during search process: {e}")
                finally:
                    # Always quit the driver after each search
                    try:
                        driver.quit()
                        logging.info("WebDriver closed successfully")
                    except Exception as e:
                        logging.error(f"Error closing WebDriver: {e}")

            # Generate intermediate status report after each attempt
            latest_log = get_latest_log_file()
            if latest_log:
                log_scan = scan_log_for_errors(latest_log)
                status_report = compare_with_input(original_input_data, log_scan)
                generate_status_report(status_report)

    except Exception as e:
        logging.error(f"Fatal error in main execution: {e}")
    finally:
        # Generate final status report
        latest_log = get_latest_log_file()
        if latest_log:
            log_scan = scan_log_for_errors(latest_log)
            comparison = compare_with_input(original_input_data, log_scan)
            generate_status_report(comparison)
        
        logging.info("Script execution completed")

if __name__ == "__main__":
    main()