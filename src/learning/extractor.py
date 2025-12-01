"""
RecycleOps AI Assistant - Solution Extractor

Extracts structured solution data from analyzed conversations.
"""
import re
from typing import Optional

import structlog


logger = structlog.get_logger(__name__)


class SolutionExtractor:
    """
    Extracts structured solution data from Slack conversations.
    
    Takes raw messages and LLM analysis results and produces
    a structured solution format for storage.
    """
    
    # Common error keywords for categorization
    CATEGORY_KEYWORDS = {
        "konveyör": ["konveyör", "conveyor", "bant", "taşıma", "besleme"],
        "sensör": ["sensör", "sensor", "algılayıcı", "fotosel"],
        "motor": ["motor", "servo", "sürücü", "drive", "inverter"],
        "hidrolik": ["hidrolik", "piston", "silindir", "pompa", "basınç"],
        "pnömatik": ["pnömatik", "hava", "kompresör", "valf", "valve"],
        "elektrik": ["elektrik", "kablo", "sigorta", "faz", "toprak"],
        "yazılım": ["yazılım", "plc", "hmi", "program", "kod", "software"],
        "mekanik": ["mekanik", "rulman", "kayış", "dişli", "mil"],
        "sıkışma": ["sıkışma", "tıkanma", "jam", "blokaj"],
        "kalibrasyon": ["kalibrasyon", "ayar", "calibration", "setup"],
    }
    
    # Patterns for extracting machine types
    MACHINE_PATTERNS = [
        r"\b([A-Z]{1,3}\d{3,4})\b",  # A1100, BC2200, etc.
        r"makine\s+(?:no|numarası)?\s*[:\s]?\s*(\d+)",
        r"(?:line|hat)\s*[:\s]?\s*(\d+)",
    ]
    
    def extract_solution_data(
        self,
        messages: list[dict],
        analysis: dict,
        channel_id: str,
        thread_ts: str,
    ) -> dict:
        """
        Extract structured solution data from messages and analysis.
        
        Args:
            messages: List of Slack messages
            analysis: LLM analysis results
            channel_id: Source channel ID
            thread_ts: Source thread timestamp
            
        Returns:
            Structured solution data dict
        """
        # Combine all message text
        full_text = " ".join([msg.get("text", "") for msg in messages])
        
        # Extract error pattern
        error_pattern = self._build_error_pattern(
            analysis.get("error_summary", ""),
            full_text,
        )
        
        # Extract category
        category = analysis.get("category") or self._detect_category(full_text)
        
        # Extract machine type
        machine_type = analysis.get("machine_type") or self._extract_machine_type(full_text)
        
        # Extract keywords
        keywords = self._extract_keywords(full_text, error_pattern)
        
        # Find who resolved the issue (usually the last few message authors)
        resolver_user_id = self._find_resolver(messages)
        
        # Build solution steps if possible
        solution_steps = self._extract_steps(analysis.get("solution", ""))
        
        return {
            "error_pattern": error_pattern,
            "solution_summary": analysis.get("error_summary", ""),
            "solution_text": analysis.get("solution", ""),
            "root_cause": analysis.get("root_cause"),
            "category": category,
            "machine_type": machine_type,
            "keywords": keywords,
            "steps": solution_steps,
            "resolver_user_id": resolver_user_id,
            "successful": analysis.get("successful", True),
            "source_channel_id": channel_id,
            "source_thread_ts": thread_ts,
        }
    
    def _build_error_pattern(self, summary: str, full_text: str) -> str:
        """Build a searchable error pattern string."""
        # Start with the summary
        pattern = summary
        
        # Add machine type if found
        machine_type = self._extract_machine_type(full_text)
        if machine_type and machine_type not in pattern:
            pattern = f"{machine_type} - {pattern}"
        
        return pattern
    
    def _detect_category(self, text: str) -> Optional[str]:
        """Detect category from text using keywords."""
        text_lower = text.lower()
        
        # Count keyword matches for each category
        category_scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            # Return category with highest score
            return max(category_scores, key=category_scores.get)
        
        return None
    
    def _extract_machine_type(self, text: str) -> Optional[str]:
        """Extract machine type/model from text."""
        for pattern in self.MACHINE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None
    
    def _extract_keywords(
        self,
        full_text: str,
        error_pattern: str,
    ) -> list[str]:
        """Extract relevant keywords for search."""
        keywords = set()
        
        # Add category keywords that appear in text
        text_lower = full_text.lower()
        for category, kw_list in self.CATEGORY_KEYWORDS.items():
            for kw in kw_list:
                if kw in text_lower:
                    keywords.add(kw)
        
        # Add machine type
        machine_type = self._extract_machine_type(full_text)
        if machine_type:
            keywords.add(machine_type.lower())
        
        # Extract capitalized words (often technical terms)
        caps_words = re.findall(r"\b[A-Z][A-Za-z]{2,}\b", full_text)
        for word in caps_words[:5]:  # Limit to avoid noise
            keywords.add(word.lower())
        
        # Add words from error pattern
        pattern_words = re.findall(r"\b\w{4,}\b", error_pattern.lower())
        keywords.update(pattern_words[:10])
        
        return list(keywords)[:20]  # Limit total keywords
    
    def _find_resolver(self, messages: list[dict]) -> Optional[str]:
        """
        Find who resolved the issue.
        
        Usually the person who provided the solution appears
        in the later messages of the thread.
        """
        if not messages:
            return None
        
        # Look at messages in the second half of the conversation
        mid_point = len(messages) // 2
        later_messages = messages[mid_point:]
        
        # Count message authors
        author_counts = {}
        for msg in later_messages:
            user = msg.get("user")
            if user:
                author_counts[user] = author_counts.get(user, 0) + 1
        
        if author_counts:
            # Return the most active author in the later part
            return max(author_counts, key=author_counts.get)
        
        return None
    
    def _extract_steps(self, solution_text: str) -> Optional[dict]:
        """
        Extract numbered steps from solution text.
        
        Returns:
            Dict with steps list or None if no clear steps
        """
        if not solution_text:
            return None
        
        # Look for numbered lists
        numbered_pattern = r"(\d+)[.\)]\s*(.+?)(?=\d+[.\)]|$)"
        matches = re.findall(numbered_pattern, solution_text, re.DOTALL)
        
        if matches and len(matches) >= 2:
            steps = [match[1].strip() for match in matches]
            return {"steps": steps}
        
        # Look for bullet points or dashes
        bullet_pattern = r"[-•*]\s*(.+?)(?=[-•*]|$)"
        matches = re.findall(bullet_pattern, solution_text, re.DOTALL)
        
        if matches and len(matches) >= 2:
            steps = [match.strip() for match in matches]
            return {"steps": steps}
        
        return None
