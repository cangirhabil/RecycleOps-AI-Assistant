"""
RecycleOps AI Assistant - Text Utilities

Text preprocessing and formatting utilities.
"""
import re
from typing import Optional


def clean_slack_text(text: str) -> str:
    """
    Clean Slack-specific formatting from text.
    
    Removes:
    - User mentions (<@U123>)
    - Channel mentions (<#C123>)
    - URLs (<http://...|label>)
    - Emoji codes (:emoji:)
    
    Args:
        text: Raw Slack message text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove user mentions
    text = re.sub(r"<@[A-Z0-9]+>", "", text)
    
    # Remove channel mentions
    text = re.sub(r"<#[A-Z0-9]+\|?[^>]*>", "", text)
    
    # Replace URLs with their labels or domain
    def replace_url(match):
        url_parts = match.group(1).split("|")
        if len(url_parts) > 1:
            return url_parts[1]  # Return label
        return "[link]"
    
    text = re.sub(r"<(https?://[^>]+)>", replace_url, text)
    
    # Remove emoji codes (keep the text readable)
    text = re.sub(r":([a-z0-9_+-]+):", r"\1", text)
    
    # Clean up extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    return text


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text or ""
    
    return text[:max_length - len(suffix)] + suffix


def extract_code_blocks(text: str) -> list[str]:
    """
    Extract code blocks from Slack-formatted text.
    
    Args:
        text: Text potentially containing code blocks
        
    Returns:
        List of code block contents
    """
    # Match triple backtick code blocks
    triple_pattern = r"```(?:\w+\n)?(.*?)```"
    triple_matches = re.findall(triple_pattern, text, re.DOTALL)
    
    # Match single backtick inline code
    single_pattern = r"`([^`]+)`"
    single_matches = re.findall(single_pattern, text)
    
    return triple_matches + single_matches


def format_slack_message(
    text: str,
    bold_patterns: Optional[list[str]] = None,
) -> str:
    """
    Format text for Slack with optional highlighting.
    
    Args:
        text: Text to format
        bold_patterns: Patterns to make bold
        
    Returns:
        Formatted text
    """
    if not text:
        return ""
    
    # Apply bold to patterns
    if bold_patterns:
        for pattern in bold_patterns:
            text = re.sub(
                f"({re.escape(pattern)})",
                r"*\1*",
                text,
                flags=re.IGNORECASE,
            )
    
    return text


def normalize_turkish(text: str) -> str:
    """
    Normalize Turkish characters for search.
    
    Converts special Turkish characters to ASCII equivalents
    for case-insensitive searching.
    
    Args:
        text: Text with Turkish characters
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    replacements = {
        "ı": "i", "İ": "I",
        "ğ": "g", "Ğ": "G",
        "ü": "u", "Ü": "U",
        "ş": "s", "Ş": "S",
        "ö": "o", "Ö": "O",
        "ç": "c", "Ç": "C",
    }
    
    for turkish, ascii_char in replacements.items():
        text = text.replace(turkish, ascii_char)
    
    return text
