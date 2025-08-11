# ZabaSearch Web Scraper

A Selenium-based web scraper for extracting people search results from ZabaSearch.com with human-like interaction patterns and error handling.

## Features

- Automated search on ZabaSearch.com with configurable inputs
- Human-like delays and interaction patterns to avoid detection
- Robust error handling with fallback mechanisms
- Consent modal handling with multiple interaction approaches
- Results saving to individual text files
- Configurable Chrome options for stealth browsing

## Prerequisites

- Python 3.6+
- Chrome browser installed
- ChromeDriver matching your Chrome version
- Required Python packages (install via `pip3 install -r requirements.txt`)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/airborne-commando/zabasearch-auto.git
   cd zabasearch-auto
   ```

2. Install dependencies:

   ```
   python3 -m venv venv && source /venv/bin/activate && pip3 install -r requirements.txt
   ```

3. Download ChromeDriver:
   - Get the appropriate version from https://chromedriver.chromium.org/
   - Place it in `/usr/bin/chromedriver` or update the path in the script

## Usage

### Single Search Mode
Run the script and choose manual input when prompted:
```
python ZabaSearch-auto.py
```

### Batch Search Mode
1. Prepare a CSV or tab-delimited text file with the following format:
   ```
   first_name,last_name,city,state
   John,Doe,New York,NY
   Jane,Smith,Los Angeles,CA
   ```

2. Run the script and choose file input when prompted:
``` 
python ZabaSearch-auto.py
```

### Input File Format
The script accepts both CSV and tab-delimited files with the following columns:
1. First Name (required)
2. Last Name (required)
3. City (optional)
4. State (optional)

## Configuration

You can modify the following parameters in the script:
- `chrome_driver_path`: Path to your ChromeDriver executable
- Human delay timing in the `human_delay()` function
- Chrome options in the `main()` function

## Output

Results are saved as individual text files named:
```
..results/zaba_results_[firstname]_[lastname].txt
```

# **NEW TOOL**

`filter.py`
A tool that can filter results for you on county and will spit out information.

Example:

      Name: first last
      Age: AGE
      
      AKA: first last
      
      Phone Numbers:
        - xxx-xxx-xxxx
      
      Email Addresses:
        - email@email.com
      
      Current Address: 1111 street street New street, Pennsylvania 00000
      Current ZIP: 15068
      Current County: Westmoreland
      
      In Target County: YES
      
      Found 3 matches in zaba_results_dev_new.txt

Will ask you about the county *in number format*
```
Available counties:
1. Adams
2. Allegheny
3. Armstrong
4. Beaver
5. Bedford
6. Berks
7. Blair
8. Bradford
9. Bucks
10. Butler
11. Cambria
12. Cameron
13. Carbon
14. Centre
15. Chester
16. Clarion
17. Clearfield
18. Clinton
19. Columbia
20. Crawford
21. Cumberland
22. Dauphin
23. Delaware
24. Elk
25. Erie
26. Fayette
27. Forest
28. Franklin
29. Fulton
30. Greene
31. Huntingdon
32. Indiana
33. Jefferson
34. Juniata
35. Lackawanna
36. Lancaster
37. Lawrence
38. Lebanon
39. Lehigh
40. Luzerne
41. Lycoming
42. Mckean
43. Mercer
44. Mifflin
45. Monroe
46. Montgomery
47. Montour
48. Northampton
49. Northumberland
50. Perry
51. Philadelphia
52. Pike
53. Potter
54. Schuylkill
55. Snyder
56. Somerset
57. Sullivan
58. Susquehanna
59. Tioga
60. Union
61. Venango
62. Warren
63. Washington
64. Wayne
65. Westmoreland
66. Wyoming
67. York

Enter county number to filter by (or 0 for all): 
```
## Anti-Detection Features

- Randomized user-agent strings
- Human-like typing delays and interaction patterns
- JavaScript-based element interaction
- Screenshot capture on errors
- Randomized delays between searches (10-30 seconds)

## Error Handling

The script includes:
- Multiple fallback mechanisms for element interaction
- Screenshot capture when errors occur
- Retry logic for form submission
- Graceful handling of missing elements

## Legal Notice

Please use this script responsibly and in compliance with:
- ZabaSearch's Terms of Service
- Applicable laws and regulations in your jurisdiction
- Website robots.txt restrictions

The maintainers of this project are not responsible for any misuse of this tool.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
