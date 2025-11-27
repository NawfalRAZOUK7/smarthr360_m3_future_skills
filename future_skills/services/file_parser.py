# future_skills/services/file_parser.py

"""
CSV/Excel parser utilities for bulk employee import.
Handles file parsing, validation, and error handling for employee data.
"""

import csv
import json
import io
from typing import List, Dict, Any, Optional, Tuple


def parse_employee_csv(
    file,
    encoding: str = 'utf-8'
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Parse CSV file containing employee data.

    Args:
        file: File object (Django UploadedFile or file-like object)
        encoding: File encoding (default: utf-8, fallback: latin-1)

    Returns:
        Tuple of (validated_employees, errors)
        - validated_employees: List of employee dicts ready for serialization
        - errors: List of error dicts with row, field, and error message

    CSV Format Expected:
        name,email,department,position,job_role_id,job_role_name,current_skills
        John Doe,john@example.com,Engineering,Senior Dev,1,,Python;Django;REST
        Jane Smith,jane@example.com,Data Science,Analyst,,Data Analyst,"SQL,Tableau,Python"

    Notes:
        - job_role_id takes precedence over job_role_name
        - current_skills can be semicolon or comma-separated
        - Empty rows are skipped
        - Encoding errors are handled with fallback to latin-1
    """
    validated_employees = []
    errors = []

    # Try to read the file with specified encoding
    try:
        # Reset file pointer to beginning
        file.seek(0)

        # Try UTF-8 first
        try:
            content = file.read().decode(encoding)
        except UnicodeDecodeError:
            # Fallback to latin-1
            file.seek(0)
            content = file.read().decode('latin-1')
            errors.append({
                'row': 0,
                'field': 'encoding',
                'error': f'File encoding issue detected, used latin-1 fallback'
            })

        # Create CSV reader from string content
        csv_reader = csv.DictReader(io.StringIO(content))

        # Validate headers
        required_headers = {'name', 'email', 'department', 'position'}
        headers = set(csv_reader.fieldnames or [])
        missing_headers = required_headers - headers

        if missing_headers:
            errors.append({
                'row': 0,
                'field': 'headers',
                'error': f'Missing required columns: {", ".join(missing_headers)}'
            })
            return [], errors

        # Process each row
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
            # Skip empty rows
            if not any(row.values()) or all(v.strip() == '' for v in row.values()):
                continue

            # Validate and extract employee data
            employee_data, row_errors = _validate_csv_row(row, row_num)

            if row_errors:
                errors.extend(row_errors)
            else:
                validated_employees.append(employee_data)

    except Exception as e:
        errors.append({
            'row': 0,
            'field': 'file',
            'error': f'Failed to parse CSV file: {str(e)}'
        })

    return validated_employees, errors


def parse_employee_excel(file) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Parse Excel file containing employee data (.xlsx or .xls).

    Args:
        file: File object (Django UploadedFile or file-like object)

    Returns:
        Tuple of (validated_employees, errors)
        - validated_employees: List of employee dicts ready for serialization
        - errors: List of error dicts with row, field, and error message

    Excel Format Expected:
        Same as CSV format with columns:
        name | email | department | position | job_role_id | job_role_name | current_skills

    Notes:
        - Requires openpyxl or pandas library
        - First row is treated as header
        - Empty rows are skipped
        - Supports both .xlsx and .xls formats (with pandas)
    """
    validated_employees = []
    errors = []

    try:
        import pandas as pd

        # Reset file pointer
        file.seek(0)

        # Read Excel file
        try:
            df = pd.read_excel(file, engine='openpyxl')
        except Exception:
            # Try with xlrd for older .xls files
            file.seek(0)
            try:
                df = pd.read_excel(file, engine='xlrd')
            except ImportError:
                errors.append({
                    'row': 0,
                    'field': 'file',
                    'error': 'openpyxl or xlrd library required for Excel parsing. Install with: pip install openpyxl'
                })
                return [], errors

        # Validate headers
        required_headers = {'name', 'email', 'department', 'position'}
        headers = set(df.columns)
        missing_headers = required_headers - headers

        if missing_headers:
            errors.append({
                'row': 0,
                'field': 'headers',
                'error': f'Missing required columns: {", ".join(missing_headers)}'
            })
            return [], errors

        # Process each row
        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel rows start at 1, header is row 1

            # Skip empty rows
            if row.isnull().all():
                continue

            # Convert pandas Series to dict
            row_dict = row.to_dict()

            # Validate and extract employee data
            employee_data, row_errors = _validate_excel_row(row_dict, row_num)

            if row_errors:
                errors.extend(row_errors)
            else:
                validated_employees.append(employee_data)

    except ImportError:
        errors.append({
            'row': 0,
            'field': 'library',
            'error': 'pandas library required for Excel parsing. Install with: pip install pandas openpyxl'
        })
    except Exception as e:
        errors.append({
            'row': 0,
            'field': 'file',
            'error': f'Failed to parse Excel file: {str(e)}'
        })

    return validated_employees, errors


def _validate_csv_row(row: Dict[str, str], row_num: int) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Validate a single CSV row and extract employee data.

    Args:
        row: Dictionary of row data from CSV
        row_num: Row number for error reporting

    Returns:
        Tuple of (employee_data, errors)
    """
    errors = []
    employee_data = {}

    # Required fields
    name = row.get('name', '').strip()
    email = row.get('email', '').strip()
    department = row.get('department', '').strip()
    position = row.get('position', '').strip()

    # Validate required fields
    if not name:
        errors.append({'row': row_num, 'field': 'name', 'error': 'Name is required'})
    if not email:
        errors.append({'row': row_num, 'field': 'email', 'error': 'Email is required'})
    if not department:
        errors.append({'row': row_num, 'field': 'department', 'error': 'Department is required'})
    if not position:
        errors.append({'row': row_num, 'field': 'position', 'error': 'Position is required'})

    # If required fields missing, return errors
    if errors:
        return None, errors

    # Basic email validation
    if '@' not in email or '.' not in email.split('@')[-1]:
        errors.append({'row': row_num, 'field': 'email', 'error': f'Invalid email format: {email}'})
        return None, errors

    # Build employee data
    employee_data['name'] = name
    employee_data['email'] = email
    employee_data['department'] = department
    employee_data['position'] = position

    # Optional: job_role_id (takes precedence)
    job_role_id = row.get('job_role_id', '').strip()
    if job_role_id:
        try:
            employee_data['job_role_id'] = int(job_role_id)
        except ValueError:
            errors.append({'row': row_num, 'field': 'job_role_id', 'error': f'Invalid job_role_id: must be integer'})

    # Optional: job_role_name (if job_role_id not provided)
    elif 'job_role_name' in row and row.get('job_role_name', '').strip():
        job_role_name = row.get('job_role_name', '').strip()
        # Note: This will need to be resolved to job_role_id in the view/serializer
        employee_data['job_role_name'] = job_role_name

    # Optional: current_skills (comma or semicolon separated)
    current_skills = row.get('current_skills', '').strip()
    if current_skills:
        # Handle both comma and semicolon separators
        if ';' in current_skills:
            skills_list = [s.strip() for s in current_skills.split(';') if s.strip()]
        elif ',' in current_skills:
            # Check if it's JSON format
            if current_skills.startswith('[') and current_skills.endswith(']'):
                try:
                    skills_list = json.loads(current_skills)
                except json.JSONDecodeError:
                    skills_list = [s.strip() for s in current_skills.split(',') if s.strip()]
            else:
                skills_list = [s.strip() for s in current_skills.split(',') if s.strip()]
        else:
            skills_list = [current_skills]

        employee_data['current_skills'] = skills_list

    return employee_data, errors


def _validate_excel_row(row: Dict[str, Any], row_num: int) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Validate a single Excel row and extract employee data.

    Args:
        row: Dictionary of row data from Excel (pandas Series converted to dict)
        row_num: Row number for error reporting

    Returns:
        Tuple of (employee_data, errors)
    """
    import pandas as pd

    errors = []
    employee_data = {}

    # Required fields (handle NaN values from pandas)
    name = str(row.get('name', '')).strip() if pd.notna(row.get('name')) else ''
    email = str(row.get('email', '')).strip() if pd.notna(row.get('email')) else ''
    department = str(row.get('department', '')).strip() if pd.notna(row.get('department')) else ''
    position = str(row.get('position', '')).strip() if pd.notna(row.get('position')) else ''

    # Validate required fields
    if not name or name == 'nan':
        errors.append({'row': row_num, 'field': 'name', 'error': 'Name is required'})
    if not email or email == 'nan':
        errors.append({'row': row_num, 'field': 'email', 'error': 'Email is required'})
    if not department or department == 'nan':
        errors.append({'row': row_num, 'field': 'department', 'error': 'Department is required'})
    if not position or position == 'nan':
        errors.append({'row': row_num, 'field': 'position', 'error': 'Position is required'})

    # If required fields missing, return errors
    if errors:
        return None, errors

    # Basic email validation
    if '@' not in email or '.' not in email.split('@')[-1]:
        errors.append({'row': row_num, 'field': 'email', 'error': f'Invalid email format: {email}'})
        return None, errors

    # Build employee data
    employee_data['name'] = name
    employee_data['email'] = email
    employee_data['department'] = department
    employee_data['position'] = position

    # Optional: job_role_id (takes precedence)
    job_role_id = row.get('job_role_id')
    if pd.notna(job_role_id):
        try:
            employee_data['job_role_id'] = int(job_role_id)
        except (ValueError, TypeError):
            errors.append({'row': row_num, 'field': 'job_role_id', 'error': 'Invalid job_role_id: must be integer'})

    # Optional: job_role_name (if job_role_id not provided)
    elif 'job_role_name' in row and pd.notna(row.get('job_role_name')):
        job_role_name = str(row.get('job_role_name', '')).strip()
        if job_role_name and job_role_name != 'nan':
            employee_data['job_role_name'] = job_role_name

    # Optional: current_skills
    current_skills = row.get('current_skills')
    if pd.notna(current_skills):
        current_skills = str(current_skills).strip()
        if current_skills and current_skills != 'nan':
            # Handle both comma and semicolon separators
            if ';' in current_skills:
                skills_list = [s.strip() for s in current_skills.split(';') if s.strip()]
            elif ',' in current_skills:
                # Check if it's JSON format
                if current_skills.startswith('[') and current_skills.endswith(']'):
                    try:
                        skills_list = json.loads(current_skills)
                    except json.JSONDecodeError:
                        skills_list = [s.strip() for s in current_skills.split(',') if s.strip()]
                else:
                    skills_list = [s.strip() for s in current_skills.split(',') if s.strip()]
            else:
                skills_list = [current_skills]

            employee_data['current_skills'] = skills_list

    return employee_data, errors


def parse_employee_file(file, file_extension: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Universal parser that detects file type and calls appropriate parser.

    Args:
        file: File object (Django UploadedFile or file-like object)
        file_extension: File extension (.csv, .xlsx, .xls)

    Returns:
        Tuple of (validated_employees, errors)
    """
    file_extension = file_extension.lower()

    if file_extension == '.csv':
        return parse_employee_csv(file)
    elif file_extension in ['.xlsx', '.xls']:
        return parse_employee_excel(file)
    else:
        return [], [{
            'row': 0,
            'field': 'file',
            'error': f'Unsupported file format: {file_extension}. Supported: .csv, .xlsx, .xls'
        }]
