"""
RecycleOps AI Assistant - Generator

LLM-based response generation using OpenAI.
"""
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import structlog

from src.config import settings


logger = structlog.get_logger(__name__)

# Singleton LLM instance
_llm: Optional[ChatOpenAI] = None


def get_llm() -> ChatOpenAI:
    """
    Get the OpenAI LLM instance.
    
    Returns:
        Configured ChatOpenAI instance
    """
    global _llm
    
    if _llm is None:
        logger.info(
            "Initializing OpenAI LLM",
            model=settings.openai_model,
        )
        
        _llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=0.3,  # Lower temperature for more consistent responses
            max_tokens=1500,
        )
    
    return _llm


# System prompts for different use cases
SYSTEM_PROMPTS = {
    "solution_search": """Sen bir teknik destek asistanısın. Görevin, makine arızaları ve teknik sorunlar için 
geçmiş çözümleri özetleyerek teknisyenlere yardımcı olmaktır.

Yanıtlarında:
- Açık ve anlaşılır ol
- Adım adım çözüm önerilerinde bulun
- Teknik detayları basitleştir ama önemli bilgileri atla
- Güvenlik uyarılarını vurgula
- Türkçe yanıt ver

Eğer yeterli bilgi yoksa, bunu belirt ve alternatif öneriler sun.""",

    "conversation_analysis": """Sen bir teknik konuşma analiz asistanısın. Görevin, Slack üzerindeki 
teknik destek konuşmalarını analiz ederek sorun-çözüm çiftlerini çıkarmaktır.

Analiz ederken:
1. Ana sorunu/hatayı belirle
2. Kök nedeni tespit et
3. Uygulanan çözümü özetle
4. Çözümün işe yarayıp yaramadığını değerlendir

Çıktı formatı:
- Hata Özeti: [kısa açıklama]
- Kök Neden: [neden/sebep]
- Çözüm: [adımlar]
- Sonuç: [başarılı/başarısız]""",

    "expert_suggestion": """Sen bir teknik ekip koordinatörüsün. Görevin, belirli bir sorun için 
en uygun uzmanı önermektir.

Önerirken:
- Uzmanlık alanlarını eşleştir
- Geçmiş deneyimi değerlendir
- Nazik ve profesyonel ol
- Türkçe yanıt ver""",

    "proactive_support": """Sen proaktif bir teknik destek asistanısın. Yeni bir hata bildirimi 
gördüğünde, geçmiş çözümlerden yararlanarak hemen yardımcı oluyorsun.

Yanıtlarında:
- Dostça ve yardımsever ol
- Geçmiş deneyimlere referans ver
- Adım adım öneriler sun
- Emin olmadığın durumları belirt
- Türkçe yanıt ver""",
}


class ResponseGenerator:
    """
    LLM-based response generator for various use cases.
    """
    
    def __init__(self):
        self.llm = get_llm()
    
    async def generate_solution_response(
        self,
        query: str,
        retrieved_solutions: list[dict],
        conversation_context: Optional[str] = None,
    ) -> str:
        """
        Generate a response based on retrieved solutions.
        
        Args:
            query: User's query
            retrieved_solutions: List of relevant solutions from retrieval
            conversation_context: Optional conversation context
            
        Returns:
            Generated response string
        """
        # Build context from retrieved solutions
        solutions_context = ""
        for i, solution in enumerate(retrieved_solutions, 1):
            solutions_context += f"\n--- Çözüm {i} (Benzerlik: {solution.get('similarity', 0):.0%}) ---\n"
            solutions_context += f"Hata: {solution.get('metadata', {}).get('error_pattern', 'N/A')}\n"
            solutions_context += f"Çözüm: {solution.get('metadata', {}).get('solution_preview', solution.get('document', 'N/A'))}\n"
        
        # Build the prompt
        user_message = f"""Kullanıcı Sorusu: {query}

Bulunan Geçmiş Çözümler:
{solutions_context if solutions_context else "Henüz kayıtlı çözüm bulunamadı."}

{f"Konuşma Bağlamı: {conversation_context[:500]}" if conversation_context else ""}

Lütfen bu bilgilere dayanarak kullanıcıya yardımcı ol. Eğer uygun bir çözüm bulunduysa özetle, 
bulunamadıysa alternatif öneriler sun."""

        messages = [
            SystemMessage(content=SYSTEM_PROMPTS["solution_search"]),
            HumanMessage(content=user_message),
        ]
        
        response = await self.llm.ainvoke(messages)
        
        logger.info(
            "Generated solution response",
            query_length=len(query),
            solutions_count=len(retrieved_solutions),
        )
        
        return response.content
    
    async def analyze_conversation(
        self,
        messages: list[dict],
    ) -> dict:
        """
        Analyze a conversation to extract problem-solution pairs.
        
        Args:
            messages: List of Slack messages from a thread
            
        Returns:
            Dict with extracted information
        """
        # Format messages
        conversation_text = ""
        for msg in messages:
            user = msg.get("user", "Unknown")
            text = msg.get("text", "")
            conversation_text += f"[{user}]: {text}\n\n"
        
        user_message = f"""Aşağıdaki teknik destek konuşmasını analiz et ve sorun-çözüm bilgilerini çıkar:

{conversation_text}

Lütfen şu formatta yanıt ver:
HATA_OZETI: [tek cümle]
KOK_NEDEN: [neden]
COZUM: [adımlar]
MAKINE_TIPI: [varsa makine kodu]
KATEGORI: [kategori adı]
BASARILI: [evet/hayır]"""

        messages = [
            SystemMessage(content=SYSTEM_PROMPTS["conversation_analysis"]),
            HumanMessage(content=user_message),
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # Parse the response
        result = self._parse_analysis_response(response.content)
        
        logger.info(
            "Analyzed conversation",
            message_count=len(messages),
            success=result.get("successful", False),
        )
        
        return result
    
    def _parse_analysis_response(self, response: str) -> dict:
        """Parse the structured analysis response."""
        result = {
            "error_summary": "",
            "root_cause": "",
            "solution": "",
            "machine_type": None,
            "category": None,
            "successful": False,
            "raw_response": response,
        }
        
        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("HATA_OZETI:"):
                result["error_summary"] = line.split(":", 1)[1].strip()
            elif line.startswith("KOK_NEDEN:"):
                result["root_cause"] = line.split(":", 1)[1].strip()
            elif line.startswith("COZUM:"):
                result["solution"] = line.split(":", 1)[1].strip()
            elif line.startswith("MAKINE_TIPI:"):
                value = line.split(":", 1)[1].strip()
                if value.lower() not in ["yok", "n/a", "-", ""]:
                    result["machine_type"] = value
            elif line.startswith("KATEGORI:"):
                value = line.split(":", 1)[1].strip()
                if value.lower() not in ["yok", "n/a", "-", ""]:
                    result["category"] = value
            elif line.startswith("BASARILI:"):
                value = line.split(":", 1)[1].strip().lower()
                result["successful"] = value in ["evet", "yes", "true", "1"]
        
        return result
    
    async def generate_proactive_suggestion(
        self,
        error_text: str,
        similar_solutions: list[dict],
    ) -> str:
        """
        Generate a proactive support message.
        
        Args:
            error_text: The new error message
            similar_solutions: Similar past solutions
            
        Returns:
            Proactive support message
        """
        if not similar_solutions:
            return ""
        
        solutions_context = ""
        for i, solution in enumerate(similar_solutions[:2], 1):
            similarity = solution.get("similarity", 0)
            solutions_context += f"\n{i}. (Benzerlik: {similarity:.0%})\n"
            solutions_context += f"   Hata: {solution.get('metadata', {}).get('error_pattern', '')[:150]}\n"
            solutions_context += f"   Çözüm: {solution.get('metadata', {}).get('solution_preview', '')[:200]}\n"
        
        user_message = f"""Yeni bir hata bildirimi alındı:
"{error_text}"

Benzer geçmiş çözümler:
{solutions_context}

Lütfen kısa ve yardımcı bir mesaj yaz. Geçmiş deneyime referans ver ve 
olası çözümü öner. 2-3 cümleyi geçme."""

        messages = [
            SystemMessage(content=SYSTEM_PROMPTS["proactive_support"]),
            HumanMessage(content=user_message),
        ]
        
        response = await self.llm.ainvoke(messages)
        
        return response.content
    
    async def suggest_expert(
        self,
        error_text: str,
        available_experts: list[dict],
    ) -> str:
        """
        Generate an expert suggestion message.
        
        Args:
            error_text: The error description
            available_experts: List of available experts
            
        Returns:
            Expert suggestion message
        """
        if not available_experts:
            return "Bu konuda uzman önerisi bulunamadı."
        
        experts_context = ""
        for expert in available_experts[:3]:
            experts_context += f"\n- {expert.get('display_name', 'Unknown')}: "
            experts_context += f"Uzmanlık: {', '.join(expert.get('expertise_areas', [])[:3])}, "
            experts_context += f"Çözüm sayısı: {expert.get('solution_count', 0)}"
        
        user_message = f"""Sorun: {error_text}

Uygun uzmanlar:
{experts_context}

En uygun uzmanı öner ve neden bu kişiyi önerdiğini kısaca açıkla."""

        messages = [
            SystemMessage(content=SYSTEM_PROMPTS["expert_suggestion"]),
            HumanMessage(content=user_message),
        ]
        
        response = await self.llm.ainvoke(messages)
        
        return response.content


def get_generator() -> ResponseGenerator:
    """Get a ResponseGenerator instance."""
    return ResponseGenerator()
