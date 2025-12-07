# future_skills/services/file_parser.py

"""
CSV/Excel parser utilities for bulk employee import.
Handles file parsing, validation, and error handling for employee data.
"""

import csv
import io
import json
from numbers import Number
from typing import Any, Dict, List, Optional, Tuple


REQUIRED_HEADERS = {"name", "email", "department", "position"}
REQUIRED_FIELD_ERRORS = {
    "name": "Name is required",
    "email": "Email is required",
    "department": "Department is required",
    "position": "Position is required",
}
EMAIL_FORMAT_ERROR = "Invalid email format: {value}"
JOB_ROLE_ID_ERROR = "Invalid job_role_id: must be integer"
ENCODING_FALLBACK_ERROR = "File encoding issue detected, used latin-1 fallback"


def _normalize_value(value: Any) -> str:
    """Return a stripped string representation, handling pandas NaN values."""

    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _collect_required_field_errors(
    values: Dict[str, str], row_num: int
) -> List[Dict[str, str]]:
    """Build error payloads for missing required fields."""

    errors: List[Dict[str, str]] = []
    for field in REQUIRED_HEADERS:
        if not values.get(field):
            errors.append(
                {"row": row_num, "field": field, "error": REQUIRED_FIELD_ERRORS[field]}
            )
    return errors


def _validate_email_format(email: str, row_num: int) -> List[Dict[str, str]]:
    """Validate email address structure."""

    if "@" not in email or "." not in email.split("@")[-1]:
        return [
            {
                "row": row_num,
                "field": "email",
                "error": EMAIL_FORMAT_ERROR.format(value=email),
            }
        ]
    return []


def _extract_current_skills(raw_value: str) -> List[str]:
    """Normalize textual representation of skill lists."""

    text = raw_value.strip()
    if not text:
        return []

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass

    if ";" in text:
        return [skill.strip() for skill in text.split(";") if skill.strip()]

    if "," in text:
        return [skill.strip() for skill in text.split(",") if skill.strip()]

    return [text]


def _coerce_int_value(value: Any) -> Optional[int]:
    """Attempt to parse an integer from raw spreadsheet/CSV values."""

    if isinstance(value, bool):
        return None
    if isinstance(value, Number):
        return int(value) if float(value).is_integer() else None

    cleaned = _normalize_value(value)
    if not cleaned:
        return None

    try:
        return int(cleaned)
    except ValueError:
        try:
            float_value = float(cleaned)
            return int(float_value) if float_value.is_integer() else None
        except ValueError:
            return None


def parse_employee_csv(
    file, encoding: str = "utf-8"
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
            content = file.read().decode("latin-1")
            errors.append(
                {
                    "row": 0,
                    "field": "encoding",
                    "error": ENCODING_FALLBACK_ERROR,
                }
            )

        # Create CSV reader from string content
        csv_reader = csv.DictReader(io.StringIO(content))

        # Validate headers
        headers = set(csv_reader.fieldnames or [])
        missing_headers = REQUIRED_HEADERS - headers

        if missing_headers:
            errors.append(
                {
                    "row": 0,
                    "field": "headers",
                    "error": f'Missing required columns: {", ".join(missing_headers)}',
                }
            )
            return [], errors

        # Process each row
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
            # Skip empty rows
            if not any(row.values()) or all(v.strip() == "" for v in row.values()):
                continue

            # Validate and extract employee data
            employee_data, row_errors = _validate_csv_row(row, row_num)

            if row_errors:
                errors.extend(row_errors)
            else:
                validated_employees.append(employee_data)

    except Exception as e:
        errors.append(
            {"row": 0, "field": "file", "error": f"Failed to parse CSV file: {str(e)}"}
        )

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
            df = pd.read_excel(file, engine="openpyxl")
        except Exception:
            # Try with xlrd for older .xls files
            file.seek(0)
            try:
                df = pd.read_excel(file, engine="xlrd")
            except ImportError:
                errors.append(
                    {
                        "row": 0,
                        "field": "file",
                        "error": "openpyxl or xlrd library required for Excel parsing. Install with: pip install openpyxl",
                    }
                )
                return [], errors

        # Validate headers
        headers = set(df.columns)
        missing_headers = REQUIRED_HEADERS - headers

        if missing_headers:
            errors.append(
                {
                    "row": 0,
                    "field": "headers",
                    "error": f'Missing required columns: {", ".join(missing_headers)}',
                }
            )
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
        errors.append(
            {
                "row": 0,
                "field": "library",
                "error": "pandas library required for Excel parsing. Install with: pip install pandas openpyxl",
            }
        )
    except Exception as e:
        errors.append(
            {
                "row": 0,
                "field": "file",
                "error": f"Failed to parse Excel file: {str(e)}",
            }
        )

    return validated_employees, errors


def _validate_csv_row(
    row: Dict[str, str], row_num: int
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Validate a single CSV row and extract employee data.

    Args:
        row: Dictionary of row data from CSV
        row_num: Row number for error reporting

    Returns:
        Tuple of (employee_data, errors)
    """
    errors: List[Dict[str, str]] = []
    employee_data: Dict[str, Any] = {}

    sanitized = {field: row.get(field, "").strip() for field in REQUIRED_HEADERS}
    errors.extend(_collect_required_field_errors(sanitized, row_num))
    if errors:
        return None, errors

    email_errors = _validate_email_format(sanitized["email"], row_num)
    if email_errors:
        return None, email_errors

    employee_data.update(sanitized)

    job_role_id_raw = row.get("job_role_id", "").strip()
    if job_role_id_raw:
        job_role_id_value = _coerce_int_value(job_role_id_raw)
        if job_role_id_value is None:
            errors.append(
                {
                    "row": row_num,
                    "field": "job_role_id",
                    "error": JOB_ROLE_ID_ERROR,
                }
            )
        else:
            employee_data["job_role_id"] = job_role_id_value

    elif job_role_name := _normalize_value(row.get("job_role_name", "")):
        employee_data["job_role_name"] = job_role_name

    current_skills_raw = row.get("current_skills", "")
    skills_list = _extract_current_skills(current_skills_raw) if current_skills_raw else []
    if skills_list:
        employee_data["current_skills"] = skills_list

    return employee_data, errors


def _validate_excel_row(
    row: Dict[str, Any], row_num: int
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Validate a single Excel row and extract employee data.

    Args:
        row: Dictionary of row data from Excel (pandas Series converted to dict)
        row_num: Row number for error reporting

    Returns:
        Tuple of (employee_data, errors)
    """
    import pandas as pd
    errors: List[Dict[str, str]] = []
    employee_data: Dict[str, Any] = {}

    sanitized = {field: _normalize_value(row.get(field)) for field in REQUIRED_HEADERS}
    errors.extend(_collect_required_field_errors(sanitized, row_num))
    if errors:
        return None, errors

    email_errors = _validate_email_format(sanitized["email"], row_num)
    if email_errors:
        return None, email_errors

    employee_data.update(sanitized)

    job_role_id_raw = row.get("job_role_id")
    normalized_job_role_id = _normalize_value(job_role_id_raw)
    if normalized_job_role_id:
        job_role_id_value = _coerce_int_value(job_role_id_raw)
        if job_role_id_value is None:
            errors.append(
                {
                    "row": row_num,
                    "field": "job_role_id",
                    "error": JOB_ROLE_ID_ERROR,
                }
            )
        else:
            employee_data["job_role_id"] = job_role_id_value
    elif job_role_name := _normalize_value(row.get("job_role_name")):
        employee_data["job_role_name"] = job_role_name

    current_skills_raw = _normalize_value(row.get("current_skills"))
    skills_list = _extract_current_skills(current_skills_raw) if current_skills_raw else []
    if skills_list:
        employee_data["current_skills"] = skills_list

    return employee_data, errors
                else:
                    skills_list = [
                        s.strip() for s in current_skills.split(",") if s.strip()
                    ]
            else:
                skills_list = [current_skills]

            employee_data["current_skills"] = skills_list

    return employee_data, errors


def parse_employee_file(
    file, file_extension: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Universal parser that detects file type and calls appropriate parser.

    Args:
        file: File object (Django UploadedFile or file-like object)
        file_extension: File extension (.csv, .xlsx, .xls)

    Returns:
        Tuple of (validated_employees, errors)
    """
    file_extension = file_extension.lower()

    if file_extension == ".csv":
        return parse_employee_csv(file)
    elif file_extension in [".xlsx", ".xls"]:
        return parse_employee_excel(file)
    else:
        return [], [
            {
                "row": 0,
                "field": "file",
                "error": f"Unsupported file format: {file_extension}. Supported: .csv, .xlsx, .xls",
            }
        ]
