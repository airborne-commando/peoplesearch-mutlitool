from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, abort
import re
import os
import time
import random
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import logging

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_tool.log'),
        logging.StreamHandler()
    ]
)

# Constants
DOCKET_TYPES = [
    "",  # Blank option
    "Civil",
    "Criminal",
    "Landlord/Tenant",
    "Miscellaneous",
    "Non-Traffic",
    "Summary Appeal",
    "Traffic"
]

# Global variables
ZIP_TO_COUNTY = {}
ZIP_TO_CITY = {}

def load_zip_codes():
    """Load ZIP code to county/city mapping from file."""
    file_path = os.path.join('zip-database', 'zip-codes.txt')
    
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if line.strip() and line.startswith("ZIP Code"):
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        zip_code = parts[0].replace("ZIP Code ", "").strip()
                        city = parts[1].strip().title()
                        county = parts[2].strip().upper()
                        ZIP_TO_COUNTY[zip_code] = county
                        ZIP_TO_CITY[zip_code] = city
        logging.info(f"Loaded ZIP code mapping with {len(ZIP_TO_COUNTY)} entries")
    except Exception as e:
        logging.error(f"Error loading ZIP code mapping: {e}")

def get_county(zip_code):
    """Get county name for a given ZIP code."""
    return ZIP_TO_COUNTY.get(zip_code)

def get_all_counties():
    """Return a sorted list of all unique counties."""
    return sorted(list(set(ZIP_TO_COUNTY.values()))) if ZIP_TO_COUNTY else []

def setup_driver():
    """Configure and return a Selenium WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    
    service = Service(executable_path='/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def extract_person_info(content):
    """Extract person information including past addresses from content."""
    entries = content.split('--------------------------------------------------')
    results = []
    
    for entry in entries:
        if not entry.strip():
            continue
            
        # Extract full name
        name_match = re.search(r'^Name:\s*(.+)$', entry, re.MULTILINE)
        full_name = name_match.group(1).strip() if name_match else "Unknown"
        
        # Split name
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Current address - more flexible matching
        current_zip = None
        current_county = None
        address_match = re.search(r'^Last Known Address:\s*(.+?)\s*(\d{5})?$', entry, re.MULTILINE)
        if address_match:
            address = address_match.group(1).strip()
            current_zip = address_match.group(2)
            if not current_zip:  # If ZIP not captured in main pattern
                zip_match = re.search(r'\b(\d{5})\b', address)
                if zip_match:
                    current_zip = zip_match.group(1)
            if current_zip:
                current_county = get_county(current_zip)
        
        # Past addresses - improved parsing
        past_addresses = []
        past_address_section = re.search(r'^Past Addresses:\s*(.+?)(?:\n\n|\Z)', entry, re.MULTILINE | re.DOTALL)
        if past_address_section:
            past_address_lines = past_address_section.group(1).strip().split('\n')
            for line in past_address_lines:
                line = line.strip()
                if line:
                    # Extract address and ZIP
                    addr_parts = re.match(r'^(.+?)(\d{5})?$', line.strip())
                    if addr_parts:
                        address = addr_parts.group(1).strip()
                        zip_code = addr_parts.group(2)
                        if not zip_code:  # If ZIP not captured in main pattern
                            zip_match = re.search(r'\b(\d{5})\b', line)
                            if zip_match:
                                zip_code = zip_match.group(1)
                        if zip_code:
                            county = get_county(zip_code)
                            past_addresses.append({
                                'address': address,
                                'zip': zip_code,
                                'county': county
                            })
        
        # Only add if we have valid name and at least one address
        if (first_name and last_name) and (current_zip or past_addresses):
            results.append({
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'current_zip': current_zip,
                'current_county': current_county,
                'past_addresses': past_addresses,
                'cases_downloaded': False,
                'download_filename': None,
                'dob': None
            })
    
    return results

def search_participant(driver, last_name, first_name, counties, docket_type="", retry_count=0):
    """Search for court cases across multiple counties."""
    all_results = []
    
    for county in counties:
        if not county:  # Skip empty counties
            continue
            
        try:
            url = "https://ujsportal.pacourts.us/CaseSearch"
            driver.get(url)
            
            # Wait for search dropdown
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#SearchBy-Control select"))
            )
            
            # Select participant search
            search_by_dropdown = Select(driver.find_element(By.CSS_SELECTOR, "#SearchBy-Control select"))
            search_by_dropdown.select_by_visible_text("Participant Name")
            
            # Enter name
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, "ParticipantLastName")))
            driver.find_element(By.NAME, "ParticipantLastName").send_keys(last_name)
            driver.find_element(By.NAME, "ParticipantFirstName").send_keys(first_name)
            
            # Select county
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#County-Control select"))
            )
            county_dropdown = Select(driver.find_element(By.CSS_SELECTOR, "#County-Control select"))
            try:
                county_dropdown.select_by_visible_text(county.title())
            except:
                if county.endswith(" COUNTY"):
                    county_dropdown.select_by_visible_text(county.replace(" COUNTY", "").title())
                else:
                    county_dropdown.select_by_visible_text(f"{county.title()} County")
            
            # Select docket type if specified
            if docket_type:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#DocketType-Control select"))
                )
                docket_dropdown = Select(driver.find_element(By.CSS_SELECTOR, "#DocketType-Control select"))
                try:
                    docket_dropdown.select_by_visible_text(docket_type)
                except:
                    logging.warning(f"Invalid docket type: {docket_type}")
            
            # Execute search
            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btnSearch"))
            )
            search_button.click()
            
            # Wait for results
            try:
                WebDriverWait(driver, 15).until(
                    lambda d: d.find_element(By.ID, "caseSearchResultGrid").is_displayed() or 
                            d.find_element(By.CLASS_NAME, "noResultsMessage").is_displayed()
                )
            except:
                pass
            
            # Check for no results
            no_results = driver.find_elements(By.CLASS_NAME, "noResultsMessage")
            if no_results and "No results match" in no_results[0].text:
                continue
            
            # Parse results
            try:
                table = driver.find_element(By.ID, "caseSearchResultGrid")
                rows = table.find_elements(By.TAG_NAME, "tr")[1:]
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 19:
                        all_results.append({
                            'Docket Number': cols[2].text.strip(),
                            'Case Caption': cols[4].text.strip(),
                            'Case Status': cols[5].text.strip(),
                            'Filing Date': cols[6].text.strip(),
                            'Participant': cols[7].text.strip(),
                            'Date of Birth': cols[8].text.strip(),
                            'County': cols[9].text.strip(),
                            'Docket Type': cols[10].text.strip(),
                            'Search Name': f"{last_name}, {first_name}",
                            'Search County': county,
                            'Docket PDF URL': cols[18].find_elements(By.TAG_NAME, "a")[0].get_attribute("href") if len(cols[18].find_elements(By.TAG_NAME, "a")) > 0 else None,
                            'Summary PDF URL': cols[18].find_elements(By.TAG_NAME, "a")[1].get_attribute("href") if len(cols[18].find_elements(By.TAG_NAME, "a")) > 1 else None
                        })
            except Exception as e:
                logging.warning(f"Error parsing results in county {county}: {e}")
                
        except Exception as e:
            if retry_count < 2:
                delay = random.uniform(10, 30)
                logging.warning(f"Retry {retry_count+1} in {county} after error: {e}... Waiting {delay:.1f} sec...")
                time.sleep(delay)
                return search_participant(driver, last_name, first_name, counties, docket_type, retry_count+1)
            else:
                logging.error(f"Max retries reached in {county}: {e}")
                continue
                
    return all_results

def save_results(results, last_name, first_name, county, docket_type=""):
    """Save search results to CSV."""
    if not results:
        return None
    
    try:
        os.makedirs('case_results', exist_ok=True)
        
        clean_last = "".join(c for c in last_name if c.isalnum())
        clean_first = "".join(c for c in first_name if c.isalnum())
        clean_county = "".join(c for c in county if c.isalnum())
        clean_docket = "".join(c for c in docket_type if c.isalnum()) if docket_type else "all"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"{clean_last}_{clean_first}_{clean_county}_{clean_docket}_{timestamp}.csv"
        filepath = os.path.join('case_results', filename)
        
        pd.DataFrame(results).to_csv(filepath, index=False)
        logging.info(f"Saved CSV to: {os.path.abspath(filepath)}")
        return filename
    except Exception as e:
        logging.error(f"Error saving results: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main application route."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index.html', error="No file uploaded")
        
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', error="No file selected")
        
        if file:
            content = file.read().decode('utf-8')
            results = extract_person_info(content)
            session['search_data'] = results
            counties = get_all_counties()
            return render_template('index.html', results=results, counties=counties, show_case_search=True)
    
    return render_template('index.html')

@app.route('/search_cases', methods=['POST'])
def search_cases():
    """Bulk search cases for all persons."""
    if 'search_data' not in session:
        return redirect(url_for('index'))
    
    search_data = session.get('search_data', [])
    docket_type = request.form.get('docket_type', '')
    
    # Convert numeric docket type to text
    if docket_type.isdigit():
        try:
            docket_type = DOCKET_TYPES[int(docket_type)]
        except IndexError:
            docket_type = ""
    
    driver = setup_driver()
    case_results = []
    
    try:
        for i, person in enumerate(search_data):
            if i > 0:
                time.sleep(random.uniform(5, 15))  # Rate limiting
            
            # Get all counties to search (current + past addresses)
            counties_to_search = []
            if person['current_county']:
                counties_to_search.append(person['current_county'])
            if person.get('past_addresses'):
                counties_to_search.extend([addr['county'] for addr in person['past_addresses'] if addr['county']])
            counties_to_search = list(set(counties_to_search))  # Remove duplicates
            
            if not counties_to_search:
                continue
                
            results = search_participant(
                driver,
                person['last_name'],
                person['first_name'],
                counties_to_search,
                docket_type
            )
            
            if results:
                # Use first county for filename
                filename = save_results(
                    results,
                    person['last_name'],
                    person['first_name'],
                    counties_to_search[0],
                    docket_type
                )
                
                # Update session data
                if results and 'Date of Birth' in results[0]:
                    session['search_data'][i]['dob'] = results[0]['Date of Birth']
                    session['search_data'][i]['cases_downloaded'] = True
                    session['search_data'][i]['download_filename'] = filename
                    session.modified = True
                
                case_results.append({
                    'name': f"{person['last_name']}, {person['first_name']}",
                    'county': ", ".join(counties_to_search),
                    'docket_type': docket_type if docket_type else "All",
                    'case_count': len(results),
                    'filename': filename
                })
            else:
                case_results.append({
                    'name': f"{person['last_name']}, {person['first_name']}",
                    'county': ", ".join(counties_to_search),
                    'docket_type': docket_type if docket_type else "All",
                    'case_count': 0,
                    'filename': None
                })
    finally:
        driver.quit()
    
    return render_template('index.html', 
                         case_results=case_results,
                         results=session.get('search_data'),
                         counties=get_all_counties())

@app.route('/case_results/<path:filename>')
def download_case_results(filename):
    """Serve case result files."""
    if not filename.endswith('.csv'):
        abort(404)
    
    file_path = os.path.join('case_results', filename)
    if not os.path.exists(file_path):
        abort(404)
        
    return send_from_directory('case_results', filename, as_attachment=True)

@app.route('/download_cases', methods=['POST'])
def download_cases():
    """Handle individual case downloads."""
    if 'search_data' not in session:
        return jsonify({'success': False, 'message': 'Session expired'})
    
    selected_county = request.form.get('county')
    person_index = int(request.form.get('person_index'))
    person = session['search_data'][person_index]
    docket_type = request.form.get('docket_type', '')
    
    # Convert numeric docket type
    if docket_type.isdigit():
        try:
            docket_type = DOCKET_TYPES[int(docket_type)]
        except IndexError:
            docket_type = ""
    
    # Get all counties to search
    counties_to_search = [selected_county]  # Start with selected county
    if person.get('past_addresses'):
        counties_to_search.extend([addr['county'] for addr in person['past_addresses'] if addr['county']])
    counties_to_search = list(set(counties_to_search))  # Remove duplicates
    
    driver = setup_driver()
    try:
        results = search_participant(
            driver,
            person['last_name'],
            person['first_name'],
            counties_to_search,
            docket_type
        )
        
        if results:
            filename = save_results(
                results,
                person['last_name'],
                person['first_name'],
                selected_county,
                docket_type
            )
            
            # Update session data
            if results and 'Date of Birth' in results[0]:
                session['search_data'][person_index]['dob'] = results[0]['Date of Birth']
                session['search_data'][person_index]['cases_downloaded'] = True
                session['search_data'][person_index]['download_filename'] = filename
                session.modified = True
            
            return jsonify({
                'success': True,
                'dob': results[0].get('Date of Birth', ''),
                'filename': filename
            })
        return jsonify({'success': False, 'message': 'No cases found'})
    except Exception as e:
        logging.error(f"Error downloading cases: {e}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        driver.quit()

if __name__ == '__main__':
    # Create directories
    os.makedirs('zip-database', exist_ok=True)
    os.makedirs('case_results', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Load ZIP data
    load_zip_codes()
    
    # Run app
    app.run(debug=True)