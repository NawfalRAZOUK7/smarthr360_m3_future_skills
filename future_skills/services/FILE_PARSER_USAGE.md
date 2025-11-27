# File Parser Usage Examples

## CSV/Excel Employee Import Parser

### Overview

The `file_parser.py` module provides utilities for parsing CSV and Excel files containing employee data for bulk import operations.

### Features

- ✅ CSV parsing with encoding fallback (UTF-8 → Latin-1)
- ✅ Excel parsing (.xlsx and .xls formats)
- ✅ Field validation (required and optional)
- ✅ Error tracking per row
- ✅ Empty row skipping
- ✅ Multiple skill format support (comma, semicolon, JSON)
- ✅ Email format validation

---

## Function Reference

### `parse_employee_csv(file, encoding='utf-8')`

Parse CSV file containing employee data.

**Parameters:**

- `file`: File object (Django UploadedFile or file-like object)
- `encoding`: File encoding (default: 'utf-8')

**Returns:**

- Tuple of `(validated_employees, errors)`

**Example:**

```python
from future_skills.services.file_parser import parse_employee_csv

# In a Django view
def upload_csv(request):
    csv_file = request.FILES['file']
    employees, errors = parse_employee_csv(csv_file)

    if errors:
        return Response({'errors': errors}, status=400)

    # Process employees...
    return Response({'count': len(employees)})
```

---

### `parse_employee_excel(file)`

Parse Excel file (.xlsx or .xls) containing employee data.

**Parameters:**

- `file`: File object (Django UploadedFile or file-like object)

**Returns:**

- Tuple of `(validated_employees, errors)`

**Requirements:**

```bash
pip install pandas openpyxl
# or for older .xls files:
pip install pandas xlrd
```

**Example:**

```python
from future_skills.services.file_parser import parse_employee_excel

def upload_excel(request):
    excel_file = request.FILES['file']
    employees, errors = parse_employee_excel(excel_file)

    if errors:
        return Response({'errors': errors}, status=400)

    # Process employees...
    return Response({'count': len(employees)})
```

---

### `parse_employee_file(file, file_extension)`

Universal parser that auto-detects file type.

**Parameters:**

- `file`: File object
- `file_extension`: File extension (`.csv`, `.xlsx`, `.xls`)

**Example:**

```python
from future_skills.services.file_parser import parse_employee_file
import os

def upload_file(request):
    uploaded_file = request.FILES['file']
    _, ext = os.path.splitext(uploaded_file.name)

    employees, errors = parse_employee_file(uploaded_file, ext)

    if errors:
        return Response({'errors': errors}, status=400)

    # Process employees...
```

---

## CSV Format

### Required Columns:

- `name` - Employee full name
- `email` - Employee email address
- `department` - Department name
- `position` - Job position/title

### Optional Columns:

- `job_role_id` - Foreign key to JobRole (integer)
- `job_role_name` - JobRole name (used if job_role_id not provided)
- `current_skills` - Employee skills (comma or semicolon separated)

### Example CSV:

```csv
name,email,department,position,job_role_id,job_role_name,current_skills
John Doe,john@example.com,Engineering,Senior Dev,1,,Python;Django;REST
Jane Smith,jane@example.com,Data Science,Analyst,,Data Analyst,"SQL,Tableau,Python"
```

---

## Skill Format Support

The parser supports multiple skill formats:

### 1. Semicolon-separated:

```csv
current_skills
Python;Django;REST API;PostgreSQL
```

### 2. Comma-separated:

```csv
current_skills
"Python,Django,REST API,PostgreSQL"
```

### 3. JSON array:

```csv
current_skills
"[""Python"",""Django"",""REST API""]"
```

---

## Error Handling

### Error Response Format:

```python
{
    'row': 5,           # Row number (0 = file-level error)
    'field': 'email',   # Field name or 'file'/'encoding'
    'error': 'Email is required'  # Error message
}
```

### Common Errors:

- **Encoding errors**: Auto-fallback to Latin-1
- **Missing required fields**: Name, email, department, position
- **Invalid email format**: Must contain @ and domain
- **Invalid job_role_id**: Must be integer
- **Missing headers**: Required columns not found

### Example Error Response:

```python
[
    {'row': 2, 'field': 'email', 'error': 'Email is required'},
    {'row': 5, 'field': 'email', 'error': 'Invalid email format: invalid'},
    {'row': 8, 'field': 'job_role_id', 'error': 'Invalid job_role_id: must be integer'}
]
```

---

## Integration with Bulk Import View

### Example View Integration:

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from future_skills.services.file_parser import parse_employee_file
import os

class BulkEmployeeUploadAPIView(APIView):
    permission_classes = [IsHRStaff]

    def post(self, request):
        # Get uploaded file
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=400
            )

        uploaded_file = request.FILES['file']
        _, ext = os.path.splitext(uploaded_file.name)

        # Parse file
        employees, parse_errors = parse_employee_file(uploaded_file, ext)

        if parse_errors:
            return Response(
                {'status': 'error', 'errors': parse_errors},
                status=400
            )

        # Use BulkEmployeeImportSerializer
        serializer = BulkEmployeeImportSerializer(data={
            'employees': employees,
            'auto_predict': request.data.get('auto_predict', True),
            'horizon_years': request.data.get('horizon_years', 5)
        })

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        # Save and return results
        result = serializer.save()
        return Response(result, status=201)
```

---

## Testing

### Quick Test:

```python
from future_skills.services.file_parser import parse_employee_csv
from io import BytesIO

# Create test CSV
csv_content = b"""name,email,department,position,job_role_id,current_skills
John Doe,john@test.com,Engineering,Developer,1,Python;Django
Jane Smith,jane@test.com,Data,Analyst,2,SQL;Tableau"""

csv_file = BytesIO(csv_content)
employees, errors = parse_employee_csv(csv_file)

print(f"Parsed {len(employees)} employees")
print(f"Errors: {len(errors)}")
```

---

## Dependencies

### Required (built-in):

- `csv`
- `json`
- `io`
- `typing`

### Optional (for Excel support):

```bash
pip install pandas openpyxl  # For .xlsx files
pip install pandas xlrd      # For .xls files (older format)
```

---

## Notes

1. **Encoding Handling**: Auto-detects and falls back from UTF-8 to Latin-1
2. **Empty Rows**: Automatically skipped during parsing
3. **Email Validation**: Basic format check (contains @ and domain)
4. **Job Role Resolution**: `job_role_id` takes precedence over `job_role_name`
5. **Skill Parsing**: Supports multiple formats for flexibility
6. **Error Tracking**: Per-row errors with field-level detail
7. **Transaction Safety**: Use with Django's `transaction.atomic()` in views

---

## Template File

A CSV template is provided at:

```
future_skills/services/employees_import_template.csv
```

Users can download this template and fill it with employee data.
