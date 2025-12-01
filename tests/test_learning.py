"""
Tests for the learning module components.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from src.learning.extractor import SolutionExtractor


class TestSolutionExtractor:
    """Tests for the SolutionExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        """Create a SolutionExtractor instance."""
        return SolutionExtractor()
    
    def test_detect_category_conveyor(self, extractor):
        """Test category detection for conveyor."""
        text = "Konveyör bandında sıkışma var, taşıma durdu"
        category = extractor._detect_category(text)
        assert category in ["konveyör", "sıkışma"]
    
    def test_detect_category_sensor(self, extractor):
        """Test category detection for sensor."""
        text = "Sensör algılama hatası, fotosel yanıp sönüyor"
        category = extractor._detect_category(text)
        assert category == "sensör"
    
    def test_detect_category_motor(self, extractor):
        """Test category detection for motor."""
        text = "Motor sürücü hatası, inverter alarm veriyor"
        category = extractor._detect_category(text)
        assert category == "motor"
    
    def test_extract_machine_type(self, extractor):
        """Test machine type extraction."""
        text = "A1100 makinesinde hata var"
        machine = extractor._extract_machine_type(text)
        assert machine == "A1100"
    
    def test_extract_machine_type_longer(self, extractor):
        """Test machine type extraction with longer code."""
        text = "BC2200 hattında problem"
        machine = extractor._extract_machine_type(text)
        assert machine == "BC2200"
    
    def test_extract_keywords(self, extractor):
        """Test keyword extraction."""
        keywords = extractor._extract_keywords(
            "Motor hatası sensör arızası",
            "Motor sensör hatası",
        )
        assert "motor" in keywords
        assert "sensör" in keywords
    
    def test_find_resolver(self, extractor):
        """Test finding the resolver from messages."""
        messages = [
            {"user": "U1", "text": "Problem var"},
            {"user": "U2", "text": "Anlıyorum"},
            {"user": "U2", "text": "Şunu dene"},
            {"user": "U1", "text": "Çözdük teşekkürler"},
        ]
        resolver = extractor._find_resolver(messages)
        # U2 is more active in the second half
        assert resolver == "U2"
    
    def test_extract_steps_numbered(self, extractor):
        """Test extracting numbered steps."""
        solution = """
        1. İlk adım
        2. İkinci adım
        3. Üçüncü adım
        """
        result = extractor._extract_steps(solution)
        assert result is not None
        assert len(result["steps"]) == 3
    
    def test_extract_steps_bullets(self, extractor):
        """Test extracting bullet point steps."""
        solution = """
        - Birinci adım
        - İkinci adım
        - Üçüncü adım
        """
        result = extractor._extract_steps(solution)
        assert result is not None
        assert len(result["steps"]) == 3
    
    def test_extract_solution_data(self, extractor):
        """Test full solution data extraction."""
        messages = [
            {"user": "U1", "text": "A1100 konveyör sıkışması"},
            {"user": "U2", "text": "Hızı düşür"},
            {"user": "U1", "text": "Çözdük"},
        ]
        analysis = {
            "error_summary": "Konveyör sıkışması",
            "solution": "Hızı düşür",
            "root_cause": "Yüksek hız",
            "successful": True,
        }
        
        result = extractor.extract_solution_data(
            messages=messages,
            analysis=analysis,
            channel_id="C123",
            thread_ts="123.456",
        )
        
        assert "error_pattern" in result
        assert "solution_text" in result
        assert result["machine_type"] == "A1100"
        assert "konveyör" in result.get("category", "").lower() or \
               "sıkışma" in result.get("category", "").lower()
