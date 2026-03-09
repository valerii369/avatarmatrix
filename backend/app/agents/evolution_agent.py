import json
import random
from typing import List, Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base
from app.models.data_architecture import UserBehaviorProfileV2
from app.models.text_diagnostics import TextScene, SceneStats, Sphere, Archetype, SceneInteraction
from app.agents.common import client, settings

class EvolutionAgent:
    """
    Self-improving agent for textual diagnostic scenes and user behavioral mapping.
    """
    
    @staticmethod
    async def analyze_session_impact(
        db: AsyncSession, 
        session_id: int
    ):
        """
        Analyzes a completed textual diagnostic session and updates scene effectiveness.
        """
        # Fetch interactions for this session
        result = await db.execute(
            select(SceneInteraction).where(SceneInteraction.session_id == session_id)
        )
        interactions = result.scalars().all()
        if not interactions:
            return

        for interaction in interactions:
            # 1. Update views/stats for the scene
            stats_result = await db.execute(
                select(SceneStats).where(SceneStats.scene_id == interaction.scene_id)
            )
            stats = stats_result.scalar_one_or_none()
            if not stats:
                stats = SceneStats(scene_id=interaction.scene_id)
                db.add(stats)
                await db.flush()

            stats.times_shown += 1
            
            # 2. Update rolling metrics
            n = stats.times_shown
            stats.avg_reading_time = (stats.avg_reading_time * (n-1) + interaction.reading_time) / n
            stats.avg_response_length = (stats.avg_response_length * (n-1) + interaction.response_length) / n
            
            # 3. Diagnostic Power Calculation
            # Effective scene = moderate reading time (reflection) + healthy response length
            # Too fast + too short = low power. Too long + too short = low power.
            ideal_time = 15.0 # seconds
            time_factor = max(0.2, 1.0 - abs(interaction.reading_time - ideal_time) / 30.0)
            length_factor = min(1.0, interaction.response_length / 200.0)
            
            current_power = time_factor * length_factor
            # Rolling average power
            stats.diagnostic_power_score = (stats.diagnostic_power_score * 0.8) + (current_power * 0.2)

        await db.commit()


    @staticmethod
    async def evolve_text_library(db: AsyncSession):
        """
        Identifies scenes with low diagnostic power and triggers generation of replacements.
        """
        # 1. Find weak scenes (Low diagnostic_power_score and shown enough times)
        stmt = (
            select(SceneStats)
            .where(SceneStats.times_shown > 20)
            .where(SceneStats.diagnostic_power_score < 0.4)
            .limit(10)
        )
        result = await db.execute(stmt)
        weak_stats = result.scalars().all()
        
        for stats in weak_stats:
            scene_res = await db.execute(select(TextScene).where(TextScene.id == stats.scene_id))
            scene = scene_res.scalar_one_or_none()
            if scene:
                # Mark as inactive
                scene.is_active = False
                # Generate replacement
                await EvolutionAgent.generate_text_scene(
                    db, 
                    sphere_id=scene.sphere_id, 
                    archetype_id=scene.archetype_id,
                    complexity=scene.complexity_score,
                    tension=scene.tension_level
                )
        
        await db.commit()

class DatasetBuilder:
    """
    Builds training datasets for scene effectiveness and latent state prediction.
    """
    @staticmethod
    async def prepare_training_data(db: AsyncSession):
        """
        Exports scene + interaction -> effectiveness labels.
        """
        stmt = select(SceneInteraction, TextScene).join(TextScene)
        result = await db.execute(stmt)
        rows = result.all()
        
        dataset = []
        for interaction, scene in rows:
            dataset.append({
                "scene_id": scene.id,
                "sphere": scene.sphere_id,
                "archetype": scene.archetype_id,
                "response_text": interaction.response_text,
                "reading_time": interaction.reading_time,
                "response_vector": interaction.response_embedding,
                # Simple label: deep engagement if response is long and reading time is significant
                "is_effective": interaction.response_length > 100 and interaction.reading_time > 10.0
            })
            
        return dataset


    @staticmethod
    async def generate_text_scene(
        db: AsyncSession, 
        sphere_id: int, 
        archetype_id: int,
        complexity: float = 0.5,
        tension: float = 0.5
    ) -> TextScene:
        """
        Scene Forge: Generates a new textual diagnostic scene.
        """
        # Fetch names
        sphere_res = await db.execute(select(Sphere).where(Sphere.id == sphere_id))
        sphere = sphere_res.scalar_one()
        arch_res = await db.execute(select(Archetype).where(Archetype.id == archetype_id))
        archetype = arch_res.scalar_one()

        prompt = f"""
        Создай текстовую диагностическую сцену для системы AVATAR.
        Сфера: {sphere.name_ru}
        Архетип: {archetype.name}
        Параметры:
        - Сложность: {complexity} (0-1)
        - Напряжение: {tension} (0-1)
        
        ТРЕБОВАНИЯ:
        1. Длина: 60-120 слов.
        2. МИНИМАЛЬНАЯ СЦЕНА: Только 1-2 элемента среды.
        3. ОТКРЫТАЯ ИНТЕРПРЕТАЦИЯ: Никаких навязанных эмоций или выводов.
        4. СЕНСОРНЫЙ ФОКУС: Описание пространства и положения тела.
        
        Формат ответа JSON:
        {{
            "scene_text": "текст сцены...",
            "environment_type": "тип окружения (лес, комната, пустота...)",
            "ambiguity_score": 0.5
        }}
        """

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "system", "content": "Ты — AI-сценарист психологических диагностических систем."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        
        new_scene = TextScene(
            sphere_id=sphere_id,
            archetype_id=archetype_id,
            scene_text=data["scene_text"],
            complexity_score=complexity,
            tension_level=tension,
            ambiguity_score=data.get("ambiguity_score", 0.5),
            environment_type=data.get("environment_type", "unknown")
        )
        db.add(new_scene)
        await db.commit()
        await db.refresh(new_scene)
        
        # Initialize stats
        db.add(SceneStats(scene_id=new_scene.id))
        await db.commit()
        
        return new_scene
