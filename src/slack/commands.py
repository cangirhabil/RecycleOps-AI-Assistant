"""
RecycleOps AI Assistant - Slack Slash Commands

Implementation of slash commands:
- /cozum-ara [query] - Search for solutions
- /cozum-getir - Get solution for current thread
- /cozum-ekle - Add current thread as a solution
"""
import asyncio
from typing import Optional

from slack_bolt import App, Ack, Respond
from slack_sdk import WebClient
import structlog

from src.config import settings
from src.services.solution_service import SolutionService
from src.services.conversation_service import ConversationService


logger = structlog.get_logger(__name__)


def handle_search_command(
    ack: Ack,
    respond: Respond,
    command: dict,
    client: WebClient,
) -> None:
    """
    Handle /cozum-ara command.
    
    Usage: /cozum-ara [sorun tanımı]
    Example: /cozum-ara A1100 şişe sıkışması
    
    Searches the knowledge base for similar past solutions.
    """
    ack()
    
    query = command.get("text", "").strip()
    user_id = command.get("user_id")
    channel_id = command.get("channel_id")
    
    if not query:
        respond(
            text="❓ Lütfen aranacak bir sorun tanımı girin.\n"
                 "Örnek: `/cozum-ara A1100 şişe sıkışması`",
            response_type="ephemeral",
        )
        return
    
    logger.info(
        "Search command received",
        user=user_id,
        channel=channel_id,
        query=query,
    )
    
    # Show searching indicator
    respond(
        text=f"🔍 *\"{query}\"* için geçmiş çözümler aranıyor...",
        response_type="ephemeral",
    )
    
    try:
        # Search for solutions
        solution_service = SolutionService()
        results = solution_service.search_solutions(
            query=query,
            max_results=settings.max_search_results,
            min_similarity=settings.similarity_threshold,
        )
        
        if not results:
            respond(
                text=f"ℹ️ *\"{query}\"* ile ilgili kayıtlı bir çözüm bulunamadı.\n\n"
                     "💡 İpucu: Farklı anahtar kelimelerle aramayı deneyin veya "
                     "sorunu daha detaylı açıklayın.",
                response_type="ephemeral",
            )
            return
        
        # Format results
        blocks = format_search_results(query, results)
        
        respond(
            blocks=blocks,
            text=f"{len(results)} çözüm bulundu",  # Fallback text
            response_type="in_channel",  # Make visible to all
        )
        
    except Exception as e:
        logger.error("Search command failed", error=str(e))
        respond(
            text="⚠️ Arama sırasında bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
            response_type="ephemeral",
        )


def format_search_results(query: str, results: list[dict]) -> list[dict]:
    """Format search results as Slack blocks."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔎 Arama Sonuçları",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Aranan: *{query}* | {len(results)} sonuç bulundu",
                },
            ],
        },
        {"type": "divider"},
    ]
    
    for i, result in enumerate(results, 1):
        similarity_pct = int(result.get("similarity", 0) * 100)
        
        # Solution block
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{i}. Çözüm* (Benzerlik: {similarity_pct}%)\n\n"
                    f"📋 *Hata:* {result.get('error_pattern', 'N/A')[:200]}\n\n"
                    f"✅ *Çözüm:* {result.get('solution_summary', result.get('solution_text', 'N/A'))[:300]}"
                ),
            },
        })
        
        # Add source link if available
        if result.get("source_link"):
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📎 <{result['source_link']}|Kaynak konuşmaya git>",
                    },
                ],
            })
        
        # Add metadata
        metadata_parts = []
        if result.get("machine_type"):
            metadata_parts.append(f"🔧 {result['machine_type']}")
        if result.get("category"):
            metadata_parts.append(f"📁 {result['category']}")
        if result.get("success_rate"):
            metadata_parts.append(f"✓ {int(result['success_rate'] * 100)}% başarı")
        
        if metadata_parts:
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": " | ".join(metadata_parts)},
                ],
            })
        
        blocks.append({"type": "divider"})
    
    # Add feedback prompt
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "💡 Çözüm işe yaradı mı? 👍 veya 👎 ile geri bildirim verin.",
            },
        ],
    })
    
    return blocks


def handle_cozum_getir_command(
    ack: Ack,
    respond: Respond,
    command: dict,
    client: WebClient,
) -> None:
    """
    Handle /cozum-getir command.
    
    Usage: /cozum-getir (must be used in a thread)
    
    Analyzes the current thread and suggests relevant solutions.
    """
    ack()
    
    user_id = command.get("user_id")
    channel_id = command.get("channel_id")
    
    # Note: Slack doesn't directly provide thread_ts in command payload
    # We'll need to check if this was invoked from a thread
    # For now, we'll prompt the user to use it in a thread
    
    logger.info(
        "Cozum-getir command received",
        user=user_id,
        channel=channel_id,
    )
    
    respond(
        text="🔍 Bu komutu bir hata thread'inin içinde kullanın.\n\n"
             "Thread'e girin ve `/cozum-getir` komutunu orada çalıştırın. "
             "Sistem thread'deki konuşmayı analiz edip çözüm önerecektir.\n\n"
             "Alternatif olarak, beni etiketleyerek (@RecycleOps) doğrudan "
             "sorununuzu sorabilirsiniz.",
        response_type="ephemeral",
    )


def handle_cozum_ekle_command(
    ack: Ack,
    respond: Respond,
    command: dict,
    client: WebClient,
) -> None:
    """
    Handle /cozum-ekle command.
    
    Usage: /cozum-ekle (must be used in a thread)
    
    Immediately analyzes the current thread and adds it as a solution,
    bypassing the 12-hour waiting rule.
    """
    ack()
    
    user_id = command.get("user_id")
    channel_id = command.get("channel_id")
    
    logger.info(
        "Cozum-ekle command received",
        user=user_id,
        channel=channel_id,
    )
    
    respond(
        text="📝 Bu komutu çözümün bulunduğu thread'in içinde kullanın.\n\n"
             "Thread'e girin ve `/cozum-ekle` komutunu orada çalıştırın. "
             "Sistem konuşmayı analiz edip çözümü hemen kaydedecektir.\n\n"
             "Bu komut 12 saat bekleme kuralını atlar ve çözümü anında sisteme ekler.",
        response_type="ephemeral",
    )


async def handle_cozum_getir_thread(
    client: WebClient,
    channel_id: str,
    thread_ts: str,
    user_id: str,
) -> dict:
    """
    Process /cozum-getir for a specific thread.
    
    Args:
        client: Slack WebClient
        channel_id: Channel ID
        thread_ts: Thread timestamp
        user_id: User who triggered the command
        
    Returns:
        Response dict with success status and message
    """
    try:
        # Fetch thread messages
        result = await asyncio.to_thread(
            client.conversations_replies,
            channel=channel_id,
            ts=thread_ts,
            limit=50,
        )
        
        messages = result.get("messages", [])
        if not messages:
            return {
                "success": False,
                "message": "Thread'de mesaj bulunamadı.",
            }
        
        # Combine messages into context
        conversation_text = "\n".join([
            f"{msg.get('user', 'Unknown')}: {msg.get('text', '')}"
            for msg in messages
        ])
        
        # Search for similar solutions
        solution_service = SolutionService()
        results = await solution_service.search_solutions(
            query=conversation_text,
            max_results=3,
            min_similarity=0.6,  # Lower threshold for thread context
        )
        
        return {
            "success": True,
            "results": results,
            "message": f"{len(results)} olası çözüm bulundu.",
        }
        
    except Exception as e:
        logger.error("Failed to process thread", error=str(e))
        return {
            "success": False,
            "message": f"Thread işlenirken hata oluştu: {str(e)}",
        }


async def handle_cozum_ekle_thread(
    client: WebClient,
    channel_id: str,
    thread_ts: str,
    user_id: str,
) -> dict:
    """
    Process /cozum-ekle for a specific thread.
    
    Immediately analyzes and saves the thread as a solution.
    """
    try:
        # Fetch thread messages
        result = await asyncio.to_thread(
            client.conversations_replies,
            channel=channel_id,
            ts=thread_ts,
            limit=100,
        )
        
        messages = result.get("messages", [])
        if len(messages) < 2:
            return {
                "success": False,
                "message": "Bu thread'de yeterli konuşma yok. "
                          "En az 2 mesaj gerekli.",
            }
        
        # Process the conversation
        conversation_service = ConversationService()
        solution = await conversation_service.analyze_and_save_solution(
            channel_id=channel_id,
            thread_ts=thread_ts,
            messages=messages,
            added_by=user_id,
            force=True,  # Bypass 12-hour rule
        )
        
        if solution:
            return {
                "success": True,
                "solution_id": str(solution.id),
                "message": "✅ Çözüm başarıyla kaydedildi! "
                          "Artık benzer sorunlarda önerilecek.",
            }
        else:
            return {
                "success": False,
                "message": "Konuşmadan çözüm çıkarılamadı. "
                          "Lütfen konuşmada net bir sorun-çözüm ilişkisi olduğundan emin olun.",
            }
            
    except Exception as e:
        logger.error("Failed to add solution", error=str(e))
        return {
            "success": False,
            "message": f"Çözüm eklenirken hata oluştu: {str(e)}",
        }


def register_commands(app: App) -> None:
    """
    Register all slash commands with the Slack app.
    
    Args:
        app: The Slack App instance
    """
    
    @app.command("/cozum-ara")
    def search_command(ack, respond, command, client):
        handle_search_command(ack, respond, command, client)
    
    @app.command("/cozum-getir")
    def cozum_getir_command(ack, respond, command, client):
        handle_cozum_getir_command(ack, respond, command, client)
    
    @app.command("/cozum-ekle")
    def cozum_ekle_command(ack, respond, command, client):
        handle_cozum_ekle_command(ack, respond, command, client)
    
    logger.info("Slack slash commands registered")
