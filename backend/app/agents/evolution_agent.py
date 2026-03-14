import json
import random
from typing import List, Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel, Field
from app.database import Base
from app.models.data_architecture import UserBehaviorProfileV2
from app.models.text_diagnostics import TextScene, SceneStats, Sphere, Archetype, SceneInteraction
from app.agents.common import client, settings
from app.agents.sync_agent import get_embedding

# --- Pydantic Models for Structured Output (High Standard) ---
class Interpretation(BaseModel):
    object: str = Field(description="Ключевой объект в сцене (например 'Зеркало')")
    interpretation_broken: str = Field(description="Интерпретация, если объект сломан/разрушен")
    interpretation_beautiful: str = Field(description="Интерпретация, если объект красивый/притягательный")
    interpretation_threatening: str = Field(description="Интерпретация, если объект угрожающий/пугающий")

class ImmersionArchitecture(BaseModel):
    orientation: str = Field(description="Атмосферное описание стартовой среды (2-3 предложения)")
    complication: str = Field(description="Событие-триггер внутри сцены, создающее давление (1 предложение)")

class DiagnosticFocus(BaseModel):
    pennebaker_markers: list[str] = Field(description="Маркеры Пеннебейкера")
    mcadams_markers: list[str] = Field(description="Маркеры Макадамса")

class TransformationMechanics(BaseModel):
    externalization_question: str = Field(description="Вопрос для экстернализации проблемы по М. Уайту")
    action_prompt: str = Field(description="Вопрос про телесную/пространственную реакцию (Что делает ваше тело...)")

class SceneData(BaseModel):
    scene_name: str
    psychological_foundation: str
    immersion_architecture: ImmersionArchitecture
    projection_dictionary: list[Interpretation]
    diagnostic_focus: DiagnosticFocus
    transformation_mechanics: TransformationMechanics

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

        system_prompt = f"""
        Ты — старший системный архитектор и эксперт по нарративной психологии AVATAR.
        Творчески соединяя Жака Лакана, Карла Юнга, Уильяма Лабова, Генри Мюррея, Джеймса Пеннебейкера, Майкла Уайта и Дэн Макадамса, создай УНИКАЛЬНУЮ проективную текстовую сцену.
        
        СФЕРА В ФОКУСЕ: {sphere.name_ru}
        АРХЕТИП В ФОКУСЕ: {archetype.name} (Свет: {getattr(archetype, 'light', '')}, Тень: {getattr(archetype, 'shadow', '')})
        
        ИНСТРУКЦИЯ ПО АРХИТЕКТУРЕ (Лабов + Мюррей):
        - Сложность: {complexity} (0-1)
        - Напряжение: {tension} (0-1)
        Orientation: Атмосферное описание стартовой среды. Оно должно быть сюрреалистичным, богатым проекциями и отсылать к архетипу и сфере. Без людей. 2-3 предложения.
        Complication: Событие-триггер внутри сцены, создающее давление (Press). 1 предложение.
        
        ИНСТРУКЦИЯ ПО СИМВОЛАМ (Юнг):
        Выберите 3-4 ключевых объекта среды и обоснуйте, что значит для анализа, если пользователь воспримет их как "сломанные", "красивые" или "угрожающие".
        
        СТРОГИЙ ФОРМАТ ВЫВОДА — JSON. Все тексты (сцена, вопросы, описания) должны быть только на РУССКОМ языке.
        """

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": "Сгенерируй эволюционную сцену в формате JSON."}],
            response_format={
                "type": "json_schema", 
                "json_schema": {"name": "scene_schema", "schema": SceneData.model_json_schema()}
            },
            temperature=0.7
        )
        
        data_obj = SceneData.model_validate_json(response.choices[0].message.content)
        data = data_obj.model_dump()
        
        # Concatenate text as per standard
        full_text = f"{data_obj.immersion_architecture.orientation} {data_obj.immersion_architecture.complication}"
        if data_obj.transformation_mechanics.action_prompt:
            full_text += f"\n\n[Системный хук]: {data_obj.transformation_mechanics.action_prompt}"

        emb = await get_embedding(full_text)

        new_scene = TextScene(
            sphere_id=sphere_id,
            archetype_id=archetype_id,
            scene_text=full_text,
            scene_embedding=emb,
            complexity_score=complexity,
            tension_level=tension,
            ambiguity_score=0.7,
            environment_type="Projective Landscape (Evolved)",
            meta_data=data
        )
        db.add(new_scene)
        await db.commit()
        await db.refresh(new_scene)
        
        # Initialize stats
        db.add(SceneStats(scene_id=new_scene.id))
        await db.commit()
        
        return new_scene
