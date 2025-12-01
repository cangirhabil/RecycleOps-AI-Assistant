"""
RecycleOps AI Assistant - Proactive Service

Proactive support functionality that automatically suggests solutions
when new error messages are detected.
"""
from typing import Optional

from slack_sdk import WebClient
import structlog

from src.config import settings
from src.services.solution_service import SolutionService
from src.services.expert_service import ExpertService
from src.rag.chain import get_rag_chain


logger = structlog.get_logger(__name__)


class ProactiveService:
    """
    Service for proactive support functionality.
    
    Automatically monitors channels for error messages and
    suggests relevant solutions from the knowledge base.
    """
    
    def __init__(self, slack_client: WebClient):
        """
        Initialize the proactive service.
        
        Args:
            slack_client: Slack WebClient for posting messages
        """
        self.slack_client = slack_client
        self.solution_service = SolutionService()
        self.expert_service = ExpertService()
        self.rag_chain = get_rag_chain()
    
    async def suggest_solution(
        self,
        channel_id: str,
        thread_ts: str,
        error_text: str,
        error_info: Optional[dict] = None,
    ) -> bool:
        """
        Automatically suggest a solution for a detected error.
        
        This is triggered when a new error message is posted.
        If a similar solution exists, posts a helpful message in the thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            error_text: The error message text
            error_info: Optional extracted error info (machine type, etc.)
            
        Returns:
            True if a suggestion was posted
        """
        logger.info(
            "Checking for proactive suggestion",
            channel_id=channel_id,
            thread_ts=thread_ts,
        )
        
        # Search for similar solutions
        results = await self.solution_service.search_solutions(
            query=error_text,
            max_results=3,
            min_similarity=settings.similarity_threshold,
            machine_type=error_info.get("machine_type") if error_info else None,
        )
        
        if not results:
            logger.debug("No similar solutions found for proactive suggestion")
            
            # Try to suggest an expert instead
            await self._suggest_expert(
                channel_id=channel_id,
                thread_ts=thread_ts,
                error_text=error_text,
                error_info=error_info,
            )
            return False
        
        # Generate suggestion message
        message = self._format_proactive_message(results, error_info)
        
        # Post suggestion in thread
        try:
            self.slack_client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=message,
                unfurl_links=False,
            )
            
            logger.info(
                "Posted proactive suggestion",
                channel_id=channel_id,
                thread_ts=thread_ts,
                solutions_count=len(results),
            )
            return True
            
        except Exception as e:
            logger.error("Failed to post proactive suggestion", error=str(e))
            return False
    
    async def respond_to_mention(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
        query: str,
    ) -> bool:
        """
        Respond to a direct mention with solution suggestions.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            user_id: User who mentioned the bot
            query: User's query/question
            
        Returns:
            True if response was posted
        """
        logger.info(
            "Responding to mention",
            channel_id=channel_id,
            user_id=user_id,
            query=query[:50],
        )
        
        # Use RAG chain for intelligent response
        rag_response = await self.rag_chain.query(
            question=query,
            n_results=3,
            min_similarity=0.5,  # Lower threshold for direct questions
        )
        
        if rag_response.has_solutions:
            message = self._format_mention_response(query, rag_response)
        else:
            # No solutions found, suggest expert
            expert_suggestion = await self.expert_service.suggest_experts_for_query(query)
            message = self._format_no_solution_response(query, expert_suggestion)
        
        try:
            self.slack_client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=message,
                unfurl_links=False,
            )
            return True
        except Exception as e:
            logger.error("Failed to respond to mention", error=str(e))
            return False
    
    async def _suggest_expert(
        self,
        channel_id: str,
        thread_ts: str,
        error_text: str,
        error_info: Optional[dict],
    ) -> None:
        """Suggest an expert when no solution is found."""
        machine_type = error_info.get("machine_type") if error_info else None
        
        experts = await self.expert_service.find_experts(
            query=error_text,
            machine_type=machine_type,
        )
        
        if experts:
            message = "🤔 Bu soruna benzer kayıtlı bir çözüm bulamadım.\n\n"
            message += "Ancak bu konuda deneyimli ekip üyelerimiz:\n"
            
            for expert in experts[:3]:
                message += f"• <@{expert['slack_user_id']}>"
                if expert.get("expertise_areas"):
                    message += f" - {', '.join(expert['expertise_areas'][:2])}"
                message += "\n"
            
            message += "\nBelki onlara danışmak istersiniz? 💡"
            
            try:
                self.slack_client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=message,
                    unfurl_links=False,
                )
            except Exception as e:
                logger.error("Failed to suggest expert", error=str(e))
    
    def _format_proactive_message(
        self,
        results: list[dict],
        error_info: Optional[dict],
    ) -> str:
        """Format the proactive suggestion message."""
        message = "👋 Merhaba! Bu hatayı fark ettim ve geçmiş kayıtlarımızda benzer durumlar buldum:\n\n"
        
        for i, result in enumerate(results[:2], 1):
            similarity = int(result.get("similarity", 0) * 100)
            
            message += f"*{i}. Benzer Durum* (Eşleşme: {similarity}%)\n"
            message += f"📋 {result.get('error_pattern', '')[:150]}\n"
            message += f"✅ {result.get('solution_summary', result.get('solution_text', ''))[:200]}\n"
            
            if result.get("source_link"):
                message += f"🔗 <{result['source_link']}|Detaylar için tıklayın>\n"
            
            message += "\n"
        
        message += "---\n"
        message += "💡 Bu öneri yardımcı olduysa 👍, olmadıysa 👎 ile geri bildirim verebilirsiniz."
        
        return message
    
    def _format_mention_response(self, query: str, rag_response) -> str:
        """Format response to a direct mention."""
        message = f"🔍 *\"{query[:50]}{'...' if len(query) > 50 else ''}\"* için arama yaptım:\n\n"
        message += rag_response.answer
        message += "\n\n---\n"
        
        if rag_response.sources:
            message += f"📚 *Kaynaklar:* {len(rag_response.sources)} kayıt bulundu "
            message += f"(Güven: {int(rag_response.confidence * 100)}%)\n"
            
            for source in rag_response.sources[:2]:
                if source.get("error_pattern"):
                    message += f"• {source['error_pattern'][:80]}...\n"
        
        message += "\n💡 Daha fazla bilgi için `/search` komutunu kullanabilirsiniz."
        
        return message
    
    def _format_no_solution_response(
        self,
        query: str,
        expert_suggestion: Optional[str],
    ) -> str:
        """Format response when no solution is found."""
        message = f"🤔 *\"{query[:50]}{'...' if len(query) > 50 else ''}\"* için "
        message += "kayıtlı bir çözüm bulamadım.\n\n"
        
        if expert_suggestion:
            message += expert_suggestion
        else:
            message += "Bu yeni bir sorun olabilir. Çözüldüğünde `/cozum-ekle` komutuyla "
            message += "kaydetmeyi unutmayın, gelecekte başkalarına yardımcı olacaktır! 🌟"
        
        return message
