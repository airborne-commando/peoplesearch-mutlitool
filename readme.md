
# PA Court Case Search Tool

A Flask web application that processes personal information files and searches Pennsylvania court records for matching cases.

## Features

- **File Processing**: Extracts personal information including:
  - Full name and aliases
  - Current and past addresses
  - Associated email addresses
- **Court Case Search**:
  - Searches [UJS Portal](https://ujsportal.pacourts.us/) for cases
  - Covers multiple counties (current and past residences)
  - Filters by docket type (criminal, civil, traffic, etc.)
- **Results Management**:
  - Downloads case details as CSV
  - Tracks search status
  - Updates records with found information (e.g., dates of birth)

## Installation

1. Clone the repository:
   ``` 
   git clone https://github.com/airborne-commando/peoplesearch-mutlitool.git
   cd peoplesearch-mutlitool
   ```

2. Create and activate a virtual environment:
   ``` 
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ``` 
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python multi-tool.py
   ```

2. Access the web interface at `http://localhost:5000`

3. Upload a file containing personal information (sample format below)

4. View extracted information and initiate court case searches

### Sample Input File Format

```
Name: [Redacted First] [Redacted Last]
Age: [Age]
AKA: [Alternate Name 1], [Alternate Name 2]
Associated Email Addresses: [email1@example.com], [email2@example.com]
Last Known Address: [Street Address] [City], [State] [ZIP]
Past Addresses:
[Past Street Address 1] [Past City], [Past State] [Past ZIP]
[Past Street Address 2] [Past City], [Past State] [Past ZIP]
```

Read the readme [here](https://github.com/airborne-commando/peoplesearch-mutlitool/blob/main/ZabaSearch-auto.md)

## Configuration

Create a `.env` file for environment variables:
```
FLASK_SECRET_KEY=your_secret_key_here
DEBUG=True
```

## Dependencies

- Python 3.8+
- Flask
- Selenium
- pandas
- webdriver-manager

## File Structure

```
.
├── multi-tool.py             # Main application
├── templates/
│   └── index.html            # Web interface
├── case_results/             # Generated CSV files
├── zip-database/             # ZIP code data
│   └── zip-codes.txt
├── static/                   # Static files
└── README.md
```
