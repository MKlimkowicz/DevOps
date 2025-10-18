from faker import Faker
from typing import Dict, List, Optional
import random
import string

fake = Faker()


class BookFactory:
    @staticmethod
    def create(
        title: Optional[str] = None,
        author: Optional[str] = None,
        publication_year: Optional[int] = None,
        description: Optional[str] = None
    ) -> Dict:
        return {
            "title": title or fake.catch_phrase(),
            "author": author or fake.name(),
            "publication_year": publication_year or random.randint(1900, 2025),
            "description": description or fake.text(max_nb_chars=200)
        }
    
    @staticmethod
    def create_batch(count: int) -> List[Dict]:
        return [BookFactory.create() for _ in range(count)]
    
    @staticmethod
    def create_with_long_fields() -> Dict:
        return {
            "title": "A" * 200,
            "author": "B" * 100,
            "publication_year": 2020,
            "description": "C" * 1000
        }
    
    @staticmethod
    def create_minimal() -> Dict:
        return {
            "title": fake.word(),
            "author": fake.last_name(),
            "publication_year": 2020
        }


def bulk_books_generator(count: int, unique: bool = True) -> List[Dict]:
    books = []
    for i in range(count):
        book = {
            "title": f"{fake.catch_phrase()} {i}" if unique else fake.catch_phrase(),
            "author": fake.name(),
            "publication_year": random.randint(1900, 2025),
            "description": fake.text(max_nb_chars=150)
        }
        books.append(book)
    return books


def malicious_input_generator() -> Dict[str, Dict]:
    return {
        "sql_injection": {
            "title": "'; DROP TABLE books; --",
            "author": "admin' OR '1'='1",
            "publication_year": 2020,
            "description": "1' UNION SELECT * FROM users--"
        },
        "xss_script": {
            "title": "<script>alert('XSS')</script>",
            "author": "<img src=x onerror=alert('XSS')>",
            "publication_year": 2020,
            "description": "javascript:alert('XSS')"
        },
        "command_injection": {
            "title": "; ls -la; echo",
            "author": "| cat /etc/passwd",
            "publication_year": 2020,
            "description": "$(whoami)"
        },
        "path_traversal": {
            "title": "../../../etc/passwd",
            "author": "..\\..\\windows\\system32",
            "publication_year": 2020,
            "description": "../../../../root/.ssh/id_rsa"
        },
        "ldap_injection": {
            "title": "*)(uid=*))(|(uid=*",
            "author": "admin)(|(password=*",
            "publication_year": 2020,
            "description": "*)(&(objectClass=*"
        },
        "xml_injection": {
            "title": "<?xml version='1.0'?><!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>",
            "author": "<![CDATA[<script>alert('XSS')</script>]]>",
            "publication_year": 2020,
            "description": "&xxe;"
        },
        "null_bytes": {
            "title": "Test\x00Book",
            "author": "Author\x00Name",
            "publication_year": 2020,
            "description": "Desc\x00ription"
        },
        "unicode_overflow": {
            "title": "\u0000\uffff\U0001f600",
            "author": "\u202e\u202d",
            "publication_year": 2020,
            "description": "\ufeff" * 100
        }
    }


def edge_case_generator() -> Dict[str, Dict]:
    return {
        "min_year": {
            "title": "Minimum Year Book",
            "author": "Edge Case Author",
            "publication_year": 1900,
            "description": "Testing minimum year"
        },
        "max_year": {
            "title": "Maximum Year Book",
            "author": "Edge Case Author",
            "publication_year": 2025,
            "description": "Testing maximum year"
        },
        "single_char_fields": {
            "title": "A",
            "author": "B",
            "publication_year": 2020,
            "description": "C"
        },
        "max_length_fields": {
            "title": "X" * 200,
            "author": "Y" * 100,
            "publication_year": 2020,
            "description": "Z" * 1000
        },
        "whitespace_heavy": {
            "title": "   Book   With   Spaces   ",
            "author": "\t\tTabbed\t\tAuthor\t\t",
            "publication_year": 2020,
            "description": "\n\nNewline\n\nDescription\n\n"
        },
        "special_chars": {
            "title": "!@#$%^&*()_+-=[]{}|;:',.<>?/~`",
            "author": "Ñoño Façade Müller O'Brien",
            "publication_year": 2020,
            "description": "™®©€£¥§¶†‡•"
        },
        "empty_description": {
            "title": "Book With No Description",
            "author": "Some Author",
            "publication_year": 2020,
            "description": None
        },
        "numeric_strings": {
            "title": "123456789",
            "author": "987654321",
            "publication_year": 2020,
            "description": "000000000"
        }
    }


def random_string(length: int, charset: str = string.ascii_letters) -> str:
    return ''.join(random.choice(charset) for _ in range(length))


def create_large_payload(field_multiplier: int = 10) -> Dict:
    return {
        "title": random_string(200 * field_multiplier),
        "author": random_string(100 * field_multiplier),
        "publication_year": 2020,
        "description": random_string(1000 * field_multiplier)
    }

