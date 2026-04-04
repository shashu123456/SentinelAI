def detect_sql_injection(code: str) -> list:
    """
    Detect SQL injection vulnerabilities using simple string matching.
    Looks for patterns like database queries with string concatenation.
    """
    issues = []
    code_lower = code.lower()
    
    # Check for SQL injection patterns
    sql_patterns = [
        "select * from",
        "' or '1'='1",
        "--",
        "union select",
        "drop table",
        "insert into",
        "update set",
    ]
    
    for pattern in sql_patterns:
        if pattern in code_lower:
            issues.append(f"SQL Injection: Found '{pattern}' in code")
    
    return issues


def detect_hardcoded_secrets(code: str) -> list:
    """
    Detect hardcoded secrets like passwords and API keys.
    Looks for assignments of sensitive values.
    """
    issues = []
    code_lower = code.lower()
    
    # Check for hardcoded secret patterns
    secret_keywords = [
        "password =",
        "api_key =",
        "secret =",
        "token =",
        "private_key =",
        "api_secret =",
    ]
    
    for keyword in secret_keywords:
        if keyword in code_lower:
            issues.append(f"Hardcoded Secret: Found '{keyword}' in code")
    
    return issues


def detect_missing_auth(code: str) -> list:
    """
    Detect missing authentication in code.
    Flags code that doesn't contain auth-related keywords.
    """
    issues = []
    code_lower = code.lower()
    
    # Check if any authentication keywords are present
    auth_keywords = ["auth", "token", "jwt", "oauth"]
    
    has_auth = any(keyword in code_lower for keyword in auth_keywords)
    
    # If the code looks like an endpoint/function but has no auth
    if (("def " in code_lower or "@app" in code_lower or "@router" in code_lower) and 
        not has_auth):
        issues.append("Missing Authentication: Code contains endpoints/functions without authentication")
    
    return issues


def run_scanner(code: str) -> list:
    """
    Run all security checks on the provided code.
    Returns a list of all detected security issues.
    Automatically removes duplicates.
    """
    # Collect all issues from all detectors
    all_issues = []
    all_issues.extend(detect_sql_injection(code))
    all_issues.extend(detect_hardcoded_secrets(code))
    all_issues.extend(detect_missing_auth(code))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_issues = []
    for issue in all_issues:
        if issue not in seen:
            seen.add(issue)
            unique_issues.append(issue)
    
    return unique_issues
