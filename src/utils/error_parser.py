"""
RecycleOps AI Assistant - Error Parser

Utilities for parsing and categorizing error messages.
"""
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ParsedError:
    """Parsed error information."""
    machine_type: Optional[str] = None
    error_type: Optional[str] = None
    location: Optional[str] = None
    severity: Optional[str] = None
    keywords: list[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class ErrorParser:
    """
    Parser for error messages from Slack.
    
    Extracts structured information from error reports
    to facilitate better matching and categorization.
    """
    
    # Machine type patterns
    MACHINE_PATTERNS = [
        r"\b([A-Z]{1,3}\d{3,4})\b",  # A1100, BC2200
        r"(?:makine|machine)\s*(?:no|#|numarası)?\s*[:\s]?\s*([A-Z0-9-]+)",
        r"(?:hat|line)\s*[:\s]?\s*(\d+)",
    ]
    
    # Location patterns
    LOCATION_PATTERNS = [
        r"(\w+)\s+(?:şubesi|fabrikası|tesisi|lokasyonu)",
        r"(?:lokasyon|location|yer)[:\s]+(\w+)",
        r"@\s*(\w+)\s+(?:factory|plant|site)",
    ]
    
    # Severity indicators
    SEVERITY_KEYWORDS = {
        "critical": ["acil", "kritik", "urgent", "critical", "durdu", "stopped"],
        "high": ["önemli", "ciddi", "important", "severe", "hata"],
        "medium": ["dikkat", "warning", "uyarı", "problem"],
        "low": ["bilgi", "info", "minor", "küçük"],
    }
    
    # Error type patterns
    ERROR_TYPES = {
        "jam": ["sıkışma", "jam", "tıkanma", "blocked"],
        "sensor": ["sensör", "sensor", "algılama", "detection"],
        "motor": ["motor", "drive", "sürücü", "inverter"],
        "communication": ["iletişim", "communication", "bağlantı", "network"],
        "temperature": ["sıcaklık", "temperature", "ısınma", "overheat"],
        "pressure": ["basınç", "pressure", "hidrolik", "pnömatik"],
        "electrical": ["elektrik", "electrical", "kısa devre", "faz"],
        "calibration": ["kalibrasyon", "calibration", "ayar", "setup"],
        "maintenance": ["bakım", "maintenance", "yağlama", "temizlik"],
    }
    
    def parse(self, text: str) -> ParsedError:
        """
        Parse an error message and extract structured information.
        
        Args:
            text: Error message text
            
        Returns:
            ParsedError with extracted information
        """
        if not text:
            return ParsedError()
        
        return ParsedError(
            machine_type=self._extract_machine_type(text),
            error_type=self._detect_error_type(text),
            location=self._extract_location(text),
            severity=self._detect_severity(text),
            keywords=self._extract_keywords(text),
        )
    
    def _extract_machine_type(self, text: str) -> Optional[str]:
        """Extract machine type from text."""
        for pattern in self.MACHINE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text."""
        for pattern in self.LOCATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _detect_severity(self, text: str) -> str:
        """Detect severity level from text."""
        text_lower = text.lower()
        
        for severity, keywords in self.SEVERITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return severity
        
        return "medium"  # Default severity
    
    def _detect_error_type(self, text: str) -> Optional[str]:
        """Detect error type from text."""
        text_lower = text.lower()
        
        for error_type, keywords in self.ERROR_TYPES.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return error_type
        
        return None
    
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract relevant keywords from text."""
        keywords = set()
        text_lower = text.lower()
        
        # Add matched error type keywords
        for error_type, type_keywords in self.ERROR_TYPES.items():
            for keyword in type_keywords:
                if keyword in text_lower:
                    keywords.add(keyword)
        
        # Add machine type
        machine = self._extract_machine_type(text)
        if machine:
            keywords.add(machine.lower())
        
        # Extract significant words (4+ characters, not common words)
        common_words = {"olan", "için", "gibi", "daha", "nasıl", "neden", "sonra", "önce"}
        words = re.findall(r"\b\w{4,}\b", text_lower)
        for word in words[:10]:
            if word not in common_words:
                keywords.add(word)
        
        return list(keywords)[:15]


# Singleton instance
_parser: Optional[ErrorParser] = None


def get_error_parser() -> ErrorParser:
    """Get the ErrorParser singleton instance."""
    global _parser
    if _parser is None:
        _parser = ErrorParser()
    return _parser


def parse_error(text: str) -> ParsedError:
    """Convenience function to parse an error message."""
    return get_error_parser().parse(text)
