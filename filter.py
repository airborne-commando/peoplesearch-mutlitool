import re
import os
from collections import defaultdict
from datetime import datetime

class ZIPCodeAnalyzer:
    def __init__(self, zip_code_file):
        self.zip_data = self._load_zip_data(zip_code_file)
        self.city_to_zips = self._build_city_index()
        self.county_stats = self._calculate_county_stats()
        
    def _load_zip_data(self, filename):
        """Load ZIP code data from file and parse into a dictionary"""
        zip_data = {}
        with open(filename, 'r') as file:
            for line in file:
                if line.strip():
                    parts = line.strip().split('\t')
                    if len(parts) >= 4:
                        zip_code = re.search(r'\d{5}', parts[0]).group()
                        city = parts[1].strip()
                        county = parts[2].strip()
                        zip_type = parts[3].strip()
                        
                        zip_data[zip_code] = {
                            'city': city,
                            'county': county,
                            'type': zip_type
                        }
        return zip_data
    
    def _build_city_index(self):
        """Build an index of cities to ZIP codes for faster lookup"""
        city_index = defaultdict(list)
        for zip_code, data in self.zip_data.items():
            city_index[data['city'].lower()].append(zip_code)
        return city_index
    
    def _calculate_county_stats(self):
        """Calculate statistics about counties (how many ZIPs each has)"""
        county_stats = defaultdict(int)
        for data in self.zip_data.values():
            county_stats[data['county']] += 1
        return county_stats
    
    def get_location_info(self, zip_code):
        """Get detailed information about a specific ZIP code"""
        return self.zip_data.get(zip_code, None)
    
    def analyze_person(self, person_data, target_county=None):
        """Analyze a person's location information with optional county filtering"""
        addresses = person_data.get('Past Addresses', []) + [person_data['Last Known Address']]
        zip_codes = []
        filtered_addresses = []
        
        for address in addresses:
            zip_match = re.search(r'\b\d{5}\b', address)
            if zip_match:
                zip_code = zip_match.group()
                zip_info = self.get_location_info(zip_code)
                if zip_info and (not target_county or zip_info['county'].lower() == target_county.lower()):
                    zip_codes.append(zip_code)
                    filtered_addresses.append(address)
        
        current_zip_match = re.search(r'\b\d{5}\b', person_data['Last Known Address'])
        current_zip = current_zip_match.group() if current_zip_match else None
        current_zip_info = self.get_location_info(current_zip) if current_zip else None
        
        return {
            'name': person_data['Name'],
            'age': person_data.get('Age', 'unknown'),
            'aka': person_data.get('AKA', ''),
            'phone_numbers': person_data.get('Associated Phone Numbers', ''),
            'email_addresses': person_data.get('Associated Email Addresses', ''),
            'current_address': person_data['Last Known Address'],
            'current_zip': current_zip,
            'current_county': current_zip_info['county'] if current_zip_info else 'unknown',
            'in_target_county': bool(filtered_addresses) if target_county else None
        }

def parse_zaba_file(filename):
    """Parse a zaba results file into individual person records"""
    records = []
    current_record = {}
    
    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith('--------------------------------------------------'):
                if current_record:
                    records.append(current_record)
                    current_record = {}
            elif ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key in ['Past Addresses', 'Associated Phone Numbers', 'Associated Email Addresses', 'AKA']:
                    items = []
                    current_item = []
                    for part in value.split(','):
                        if part.strip() and part.strip()[0].isdigit() and current_item:
                            items.append(','.join(current_item).strip())
                            current_item = [part.strip()]
                        else:
                            current_item.append(part.strip())
                    if current_item:
                        items.append(','.join(current_item).strip())
                    current_record[key] = items
                else:
                    current_record[key] = value
    
    if current_record:
        records.append(current_record)
    return records

def format_person_report(person_info):
    """Format the person information into a readable report"""
    report = []
    report.append(f"\n{'='*80}")
    report.append(f"Name: {person_info['name']}")
    report.append(f"Age: {person_info['age']}")
    
    if person_info['aka']:
        report.append(f"\nAKA: {', '.join(person_info['aka'])}")
    
    report.append(f"\nPhone Numbers:")
    for phone in person_info['phone_numbers']:
        report.append(f"  - {phone}")
    
    report.append(f"\nEmail Addresses:")
    for email in person_info['email_addresses']:
        report.append(f"  - {email}")
    
    report.append(f"\nCurrent Address: {person_info['current_address']}")
    report.append(f"Current ZIP: {person_info['current_zip']}")
    report.append(f"Current County: {person_info['current_county']}")
    
    if person_info['in_target_county'] is not None:
        report.append(f"\nIn Target County: {'YES' if person_info['in_target_county'] else 'NO'}")
    
    return "\n".join(report)

def get_target_county(analyzer):
    """Prompt user to select a county to filter by"""
    print("\nAvailable counties:")
    counties = sorted(analyzer.county_stats.keys())
    for i, county in enumerate(counties, 1):
        print(f"{i}. {county}")
    
    while True:
        choice = input("\nEnter county number to filter by (or 0 for all): ")
        if choice == '0':
            return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(counties):
                return counties[index]
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def ensure_directory(directory_name):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)
    return directory_name

def process_results_directory(analyzer, target_county=None):
    """Process all files in the 'results' directory and save filtered results"""
    results_dir = ensure_directory('results')
    output_dir = ensure_directory('filtered_results')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"filtered_results_{timestamp}.txt"
    if target_county:
        output_filename = f"filtered_results_{target_county.replace(' ', '_')}_{timestamp}.txt"
    output_path = os.path.join(output_dir, output_filename)
    
    print(f"\nProcessing all files in '{results_dir}' directory...")
    print(f"Results will be saved to: {output_path}")
    
    with open(output_path, 'w') as output_file:
        output_file.write(f"Filtered Results Report\n")
        output_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if target_county:
            output_file.write(f"Filter County: {target_county}\n")
        output_file.write("="*80 + "\n\n")
        
        total_matches = 0
        
        for filename in os.listdir(results_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(results_dir, filename)
                file_matches = 0
                file_output = []
                
                try:
                    records = parse_zaba_file(filepath)
                    
                    for record in records:
                        person_info = analyzer.analyze_person(record, target_county)
                        
                        if not target_county or person_info['in_target_county']:
                            file_output.append(format_person_report(person_info))
                            file_matches += 1
                    
                    if file_matches > 0:
                        output_file.write(f"\nFile: {filename}\n")
                        output_file.write("-"*60 + "\n")
                        output_file.write("\n".join(file_output) + "\n")
                        output_file.write(f"\nFound {file_matches} matches in {filename}\n")
                        total_matches += file_matches
                
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")
        
        if total_matches > 0:
            output_file.write("\n" + "="*80 + "\n")
            output_file.write(f"TOTAL MATCHES FOUND: {total_matches}\n")
            if target_county:
                output_file.write(f"Filtered by county: {target_county}\n")
        else:
            output_file.write("\nNo matches found with the current filters.\n")
        
        output_file.write(f"Report saved to: {output_path}\n")
    
    print(f"\nProcessing complete. Found {total_matches} total matches.")
    print(f"Results saved to: {output_path}")

def find_zip_database():
    """Locate the zip-codes.txt file in zip-database directory"""
    zip_db_dir = 'zip-database'
    if not os.path.exists(zip_db_dir):
        print(f"Error: Directory '{zip_db_dir}' not found.")
        return None
    
    zip_file = os.path.join(zip_db_dir, 'zip-codes.txt')
    if not os.path.exists(zip_file):
        print(f"Error: File 'zip-codes.txt' not found in '{zip_db_dir}' directory.")
        return None
    
    return zip_file

def main():
    zip_file = find_zip_database()
    if not zip_file:
        return
    
    analyzer = ZIPCodeAnalyzer(zip_file)
    target_county = get_target_county(analyzer)
    if target_county:
        print(f"\nFiltering results for {target_county} County")
    
    process_results_directory(analyzer, target_county)

if __name__ == "__main__":
    main()