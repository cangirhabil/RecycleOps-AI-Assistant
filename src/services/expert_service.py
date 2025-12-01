"""
RecycleOps AI Assistant - Expert Service

Expert routing and suggestion functionality.
"""
from typing import Optional

import structlog

from src.database.connection import get_async_session
from src.database.repositories import ExpertRepository
from src.learning.extractor import SolutionExtractor


logger = structlog.get_logger(__name__)


class ExpertService:
    """
    Service for expert-related operations.
    
    Handles:
    - Finding experts by expertise area
    - Suggesting experts for specific problems
    - Managing expert profiles
    """
    
    def __init__(self):
        self.extractor = SolutionExtractor()
    
    async def find_experts(
        self,
        query: str,
        machine_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 3,
    ) -> list[dict]:
        """
        Find experts relevant to a query.
        
        Args:
            query: Error description or query
            machine_type: Optional machine type filter
            category: Optional category filter
            limit: Maximum number of experts to return
            
        Returns:
            List of expert dicts
        """
        # Auto-detect category if not provided
        if not category:
            category = self.extractor._detect_category(query)
        
        # Auto-detect machine type if not provided
        if not machine_type:
            machine_type = self.extractor._extract_machine_type(query)
        
        async with get_async_session() as session:
            expert_repo = ExpertRepository(session)
            experts = []
            
            # First, try to find by machine type
            if machine_type:
                machine_experts = await expert_repo.find_by_machine_type(
                    machine_type=machine_type,
                    limit=limit,
                )
                experts.extend(machine_experts)
            
            # Then, find by category if we need more
            if category and len(experts) < limit:
                remaining = limit - len(experts)
                category_experts = await expert_repo.find_by_expertise(
                    expertise_area=category,
                    limit=remaining,
                )
                
                # Add experts not already in list
                existing_ids = {e.slack_user_id for e in experts}
                for expert in category_experts:
                    if expert.slack_user_id not in existing_ids:
                        experts.append(expert)
            
            # If still not enough, get top experts
            if len(experts) < limit:
                remaining = limit - len(experts)
                top_experts = await expert_repo.get_top_experts(limit=remaining)
                
                existing_ids = {e.slack_user_id for e in experts}
                for expert in top_experts:
                    if expert.slack_user_id not in existing_ids:
                        experts.append(expert)
            
            # Convert to dicts
            return [
                {
                    "slack_user_id": e.slack_user_id,
                    "display_name": e.display_name,
                    "expertise_areas": e.expertise_areas or [],
                    "machine_types": e.machine_types or [],
                    "solution_count": e.solution_count,
                    "response_count": e.response_count,
                    "is_available": e.is_available,
                }
                for e in experts[:limit]
            ]
    
    async def suggest_experts_for_query(
        self,
        query: str,
    ) -> Optional[str]:
        """
        Generate an expert suggestion message for a query.
        
        Args:
            query: The problem/error description
            
        Returns:
            Formatted suggestion message or None
        """
        experts = await self.find_experts(query, limit=3)
        
        if not experts:
            return None
        
        # Build suggestion message
        message = "Bu konuda deneyimli ekip üyelerimiz:\n\n"
        
        for expert in experts:
            message += f"• <@{expert['slack_user_id']}>"
            
            details = []
            if expert.get("expertise_areas"):
                details.append(f"Uzmanlık: {', '.join(expert['expertise_areas'][:2])}")
            if expert.get("solution_count", 0) > 0:
                details.append(f"{expert['solution_count']} çözüm")
            
            if details:
                message += f" ({', '.join(details)})"
            
            message += "\n"
        
        message += "\nBelki onlara danışmak istersiniz? 💡"
        
        return message
    
    async def update_expert_from_solution(
        self,
        slack_user_id: str,
        category: Optional[str] = None,
        machine_type: Optional[str] = None,
    ) -> None:
        """
        Update expert profile based on a new solution.
        
        Called when a user's solution is saved to update
        their expertise areas.
        
        Args:
            slack_user_id: Slack user ID
            category: Solution category
            machine_type: Machine type from solution
        """
        async with get_async_session() as session:
            expert_repo = ExpertRepository(session)
            
            # Get or create expert
            expert = await expert_repo.create_or_update(slack_user_id=slack_user_id)
            
            # Update expertise areas
            if category:
                current_areas = expert.expertise_areas or []
                if category not in current_areas:
                    current_areas.append(category)
                    await expert_repo.update_expertise(
                        slack_user_id=slack_user_id,
                        expertise_areas=current_areas,
                        machine_types=expert.machine_types,
                    )
            
            # Update machine types
            if machine_type:
                current_machines = expert.machine_types or []
                if machine_type not in current_machines:
                    current_machines.append(machine_type)
                    await expert_repo.update_expertise(
                        slack_user_id=slack_user_id,
                        expertise_areas=expert.expertise_areas,
                        machine_types=current_machines,
                    )
            
            # Increment solution count
            await expert_repo.increment_solution_count(slack_user_id)
            
            await session.commit()
            
            logger.info(
                "Updated expert profile",
                slack_user_id=slack_user_id,
                category=category,
                machine_type=machine_type,
            )
    
    async def get_expert_profile(
        self,
        slack_user_id: str,
    ) -> Optional[dict]:
        """
        Get an expert's profile.
        
        Args:
            slack_user_id: Slack user ID
            
        Returns:
            Expert profile dict or None
        """
        async with get_async_session() as session:
            expert_repo = ExpertRepository(session)
            expert = await expert_repo.create_or_update(slack_user_id=slack_user_id)
            
            if expert:
                return {
                    "slack_user_id": expert.slack_user_id,
                    "display_name": expert.display_name,
                    "expertise_areas": expert.expertise_areas or [],
                    "machine_types": expert.machine_types or [],
                    "solution_count": expert.solution_count,
                    "response_count": expert.response_count,
                    "avg_response_time_minutes": expert.avg_response_time_minutes,
                    "is_available": expert.is_available,
                    "last_active_at": expert.last_active_at.isoformat() if expert.last_active_at else None,
                }
        
        return None
