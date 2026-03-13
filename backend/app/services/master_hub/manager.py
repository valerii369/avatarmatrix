import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.models.master_hub import (
    MasterHubSchema, IdentityModel, PsychologyModel, SphereModel, HubMetadata
)

class MasterHubManager:
    """
    Сервис управления жизненным циклом Master Hub.
    Отвечает за создание, инъекцию эзотерических данных и обновление нарратива.
    """

    @staticmethod
    async def create_initial_hub(user_id: str) -> MasterHubSchema:
        """Создает пустой скелет Хаба для нового пользователя."""
        
        # Список из 12 базовых сфер
        sphere_keys = [
            "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS",
            "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION",
            "EXPANSION", "STATUS", "VISION", "SPIRIT"
        ]
        
        spheres = {
            key: SphereModel(
                state_description="Глава еще не написана...",
                evolution_stage="Зарождение",
                central_symbols=[]
            ) for key in sphere_keys
        }

        return MasterHubSchema(
            user_id=user_id,
            identity=IdentityModel(
                summary="Личность в процессе самопознания",
                core_archetype="Искатель",
                narrative_role="Герой в начале пути",
                energy_description="Потенциал ожидает раскрытия"
            ),
            psychology=PsychologyModel(),
            spheres=spheres,
            metadata=HubMetadata()
        )

    @staticmethod
    async def inject_static_esoterics(hub: MasterHubSchema, esoteric_data: Dict[str, Any]) -> MasterHubSchema:
        """
        Интегрирует статические расчеты (Дождь -> Реки -> Океан).
        """
        from app.services.alchemists.registry import registry
        
        # 1. Дождь -> Реки
        rivers = await registry.process_all(esoteric_data)
        
        # 2. Реки -> Океан
        hub = await MasterHubManager._synthesize_ocean(hub, rivers)
        
        hub.metadata.last_updated = datetime.utcnow()
        hub.metadata.update_count += 1
        
        return hub

    @staticmethod
    async def _synthesize_ocean(hub: MasterHubSchema, rivers: List[Any]) -> MasterHubSchema:
        """
        Мастер-Алхимия: Сливает несколько системных Рек в единый Океан (Master Hub).
        """
        from openai import AsyncOpenAI
        import os
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        rivers_data = [r.model_dump() for r in rivers]
        
        prompt = f"""
ТЫ — ГЛАВНЫЙ АЛХИМИК СИСТЕМЫ AVATAR.
Твоя задача — провести финальный синтез «Океана» (Master Hub/Книга Человека).

У тебя есть несколько «РЕК» (системных интерпретаций):
{json.dumps(rivers_data, ensure_ascii=False)}

КЛЮЧЕВАЯ ЗАДАЧА:
1. Создай ЕДИНЫЙ, ЦЕЛЬНЫЙ нарратив для каждой из 12 сфер жизни. 
2. Объедини мудрость разных систем (Астрология, HD и т.д.) в один голос. 
3. Обнови Идентичность (Identity) на основе этих данных.
4. УБЕРИ любой технический шум. Оставь только чистую психологию и смыслы.

ВЕРНИ ОБНОВЛЕННЫЙ JSON, строго соответствующий схеме MasterHubSchema.
"""
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"}
            )
            updated_data = json.loads(response.choices[0].message.content)
            # Сохраняем user_id из исходного хаба
            updated_data["user_id"] = hub.user_id
            return MasterHubSchema(**updated_data)
        except Exception as e:
            print(f"Error in Ocean Synthesis: {e}")
            return hub

    @staticmethod
    def update_narrative_state(hub: MasterHubSchema, insights: Dict[str, Any]) -> MasterHubSchema:
        """
        Обновляет Хаб на основе инсайтов из сессий (UPSERT).
        insights: словарь с новыми данными для Identity, Psychology или Spheres.
        """
        if "identity" in insights:
            for k, v in insights["identity"].items():
                if hasattr(hub.identity, k):
                    setattr(hub.identity, k, v)

        if "psychology" in insights:
            psy = insights["psychology"]
            for list_field in ["guiding_thoughts", "active_requests", "inner_tensions", "talents", "limitations", "somatic_anchors"]:
                if list_field in psy:
                    current_list = getattr(hub.psychology, list_field)
                    # Добавляем только уникальные новые элементы
                    for item in psy[list_field]:
                        if item not in current_list:
                            current_list.append(item)

        if "spheres" in insights:
            for sphere_key, sphere_data in insights["spheres"].items():
                if sphere_key in hub.spheres:
                    current_sphere = hub.spheres[sphere_key]
                    for k, v in sphere_data.items():
                        if hasattr(current_sphere, k):
                            setattr(current_sphere, k, v)

        hub.metadata.last_updated = datetime.utcnow()
        hub.metadata.update_count += 1
        return hub

    @staticmethod
    def export_for_llm_context(hub: MasterHubSchema, target_sphere: Optional[str] = None) -> str:
        """
        Генерирует Markdown-контекст для AI-агента.
        Фокусируется на target_sphere, если она указана.
        """
        lines = [f"# USER_MASTER_HUB (The Book of {hub.user_id})"]
        
        # Identity Section
        lines.append("## IDENTITY")
        lines.append(f"- Summary: {hub.identity.summary}")
        lines.append(f"- Archetype: {hub.identity.core_archetype}")
        lines.append(f"- Role: {hub.identity.narrative_role}")
        
        # Psychology Summary
        lines.append("## PSYCHOLOGICAL STATE")
        if hub.psychology.active_requests:
            lines.append(f"- Requests: {', '.join(hub.psychology.active_requests[:3])}")
        if hub.psychology.inner_tensions:
            lines.append(f"- Tensions: {', '.join(hub.psychology.inner_tensions[:3])}")
        if hub.psychology.somatic_anchors:
            lines.append(f"- Somatic: {', '.join(hub.psychology.somatic_anchors[:2])}")

        # Spheres Section
        lines.append("## CHAPTERS (SPHERES)")
        if target_sphere and target_sphere in hub.spheres:
            s = hub.spheres[target_sphere]
            lines.append(f"### [FOCUS] {target_sphere}")
            lines.append(f"- State: {s.state_description}")
            lines.append(f"- Conflict: {s.active_conflict or 'None'}")
            lines.append(f"- Lesson: {s.key_lesson or 'Ongoing'}")
        else:
            # Short summary of all spheres for general context
            for key, s in hub.spheres.items():
                if s.state_description != "Глава еще не написана...":
                    lines.append(f"- {key}: {s.evolution_stage}")

        return "\n".join(lines)
