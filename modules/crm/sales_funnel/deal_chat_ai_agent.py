"""
MODULE: modules.crm.sales_funnel.deal_chat_ai_agent
RESPONSIBILITY: AI agent for deal chat using OpenRouter API.
ALLOWED: typing, loguru, json, requests, config.settings.
FORBIDDEN: Direct DB access.
ERRORS: requests.exceptions.RequestException.

AI-агент для чата по сделкам с интеграцией OpenRouter API.
Поддерживает сокращение переписки через модель для выделения тезисов.
"""

from typing import Dict, Any, Optional, List
from loguru import logger
import json
import requests
from config.settings import config


class DealChatAIAgent:
    """
    AI-агент для общения в чате сделки с использованием OpenRouter API.
    Поддерживает работу с большим контекстом и сокращение переписки.
    """

    def __init__(self):
        self.name = "AI-Ассистент"
        self.api_key = config.openrouter.api_key if hasattr(config, 'openrouter') else None
        self.api_url = config.openrouter.api_url if hasattr(config, 'openrouter') else "https://openrouter.ai/api/v1/chat/completions"
        
        # Модель для сокращения переписки (быстрая и дешевая)
        self.summarization_model = "openai/gpt-3.5-turbo"
        
        # Максимальная длина переписки перед сокращением (в токенах, примерно)
        self.max_conversation_length = 8000

    def generate_response(
        self,
        user_message: str,
        deal_context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        model_id: Optional[str] = None,
    ) -> str:
        """
        Генерация ответа AI-агента на сообщение пользователя.

        Args:
            user_message: Сообщение пользователя
            deal_context: Контекст сделки (данные карточки)
            conversation_history: История переписки
            model_id: ID модели OpenRouter (если не указан, используется модель по умолчанию)

        Returns:
            Ответ AI-агента
        """
        if not self.api_key:
            return (
                "⚠️ OpenRouter API ключ не настроен. "
                "Пожалуйста, добавьте OPENROUTER_API_KEY в .env файл."
            )

        try:
            # Формируем промпт с информацией о сделке
            system_prompt = self._build_system_prompt(deal_context)
            
            # Подготавливаем историю переписки
            messages = self._prepare_messages(
                system_prompt=system_prompt,
                user_message=user_message,
                conversation_history=conversation_history or [],
            )

            # Выбираем модель (по умолчанию DeepSeek - очень дешево и качественно)
            selected_model = model_id or "deepseek/deepseek-chat"

            # Отправляем запрос к OpenRouter
            response = self._call_openrouter_api(
                model=selected_model,
                messages=messages,
            )

            return response

        except Exception as exc:
            logger.error(f"Ошибка при генерации ответа AI-агента: {exc}", exc_info=True)
            return f"⚠️ Произошла ошибка при генерации ответа: {exc}"

    def _build_system_prompt(self, deal_context: Optional[Dict[str, Any]]) -> str:
        """Построение системного промпта с информацией о сделке."""
        prompt = """Ты - AI-ассистент, помогающий пользователю работать со сделками в системе управления продажами.
Твоя задача - отвечать на вопросы о сделке, помогать с анализом, давать рекомендации.

"""
        
        if deal_context:
            deal_data = deal_context.get("deal", {})
            tender_data = deal_context.get("tender", {})
            
            prompt += "Информация о сделке:\n"
            
            # Информация о сделке
            if deal_data:
                prompt += f"- ID сделки: {deal_data.get('id')}\n"
                prompt += f"- Название: {deal_data.get('name', 'Не указано')}\n"
                if deal_data.get('amount'):
                    prompt += f"- Сумма сделки: {deal_data.get('amount'):,.0f} ₽\n"
                if deal_data.get('margin'):
                    prompt += f"- Маржа: {deal_data.get('margin'):.1f}%\n"
                if deal_data.get('status'):
                    prompt += f"- Статус: {deal_data.get('status')}\n"
                if deal_data.get('stage_name'):
                    prompt += f"- Этап воронки: {deal_data.get('stage_name')}\n"
            
            # Информация о закупке
            if tender_data:
                prompt += "\nИнформация о закупке:\n"
                if tender_data.get('auction_name'):
                    prompt += f"- Название: {tender_data.get('auction_name')}\n"
                if tender_data.get('customer'):
                    prompt += f"- Заказчик: {tender_data.get('customer')}\n"
                if tender_data.get('region_name'):
                    prompt += f"- Регион: {tender_data.get('region_name')}\n"
                if tender_data.get('final_price') or tender_data.get('initial_price'):
                    price = tender_data.get('final_price') or tender_data.get('initial_price')
                    prompt += f"- Сумма закупки: {price:,.0f} ₽\n"
                if tender_data.get('start_date'):
                    prompt += f"- Дата начала торгов: {tender_data.get('start_date')}\n"
                if tender_data.get('end_date'):
                    prompt += f"- Дата окончания подачи заявок: {tender_data.get('end_date')}\n"
            
            prompt += "\n"
        
        prompt += """Отвечай кратко, по делу, на русском языке. 
Если не знаешь ответа, честно скажи об этом.
Всегда будь вежливым и профессиональным."""
        
        return prompt

    def _prepare_messages(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """Подготовка сообщений для API с учетом истории переписки."""
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Если история переписки большая, сокращаем её
        if len(conversation_history) > 10:  # Примерная оценка
            try:
                summarized_history = self._summarize_conversation(conversation_history[:-5])  # Оставляем последние 5 сообщений
                if summarized_history:
                    messages.append({
                        "role": "assistant",
                        "content": f"Предыдущая переписка (сокращено):\n{summarized_history}\n\n---\n\nТекущая переписка:"
                    })
                # Добавляем последние сообщения полностью
                for msg in conversation_history[-5:]:
                    role = "user" if msg.get("sender_type") == "user" else "assistant"
                    messages.append({
                        "role": role,
                        "content": msg.get("message_text", "")
                    })
            except Exception as exc:
                logger.warning(f"Ошибка при сокращении переписки, используем последние сообщения: {exc}")
                # В случае ошибки используем только последние сообщения
                for msg in conversation_history[-10:]:
                    role = "user" if msg.get("sender_type") == "user" else "assistant"
                    messages.append({
                        "role": role,
                        "content": msg.get("message_text", "")
                    })
        else:
            # Если переписка короткая, добавляем всю
            for msg in conversation_history:
                role = "user" if msg.get("sender_type") == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": msg.get("message_text", "")
                })

        # Добавляем текущее сообщение пользователя
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    def _summarize_conversation(self, conversation_history: List[Dict[str, Any]]) -> Optional[str]:
        """Сокращение переписки через модель для выделения главных тезисов."""
        if not conversation_history or not self.api_key:
            return None

        try:
            # Формируем текст переписки
            conversation_text = "\n".join([
                f"{'Пользователь' if msg.get('sender_type') == 'user' else 'AI'}: {msg.get('message_text', '')}"
                for msg in conversation_history
            ])

            # Промпт для сокращения
            summarization_prompt = f"""Сократи следующую переписку, выделив главные тезисы и ключевые моменты.
Сохрани важную информацию, но сделай текст более компактным.

Переписка:
{conversation_text}

Сокращенная версия:"""

            # Вызываем API для сокращения
            response = self._call_openrouter_api(
                model=self.summarization_model,
                messages=[
                    {"role": "system", "content": "Ты помощник для сокращения переписки. Выделяй главные тезисы."},
                    {"role": "user", "content": summarization_prompt}
                ],
            )

            return response

        except Exception as exc:
            logger.error(f"Ошибка при сокращении переписки: {exc}", exc_info=True)
            return None

    def _call_openrouter_api(
        self,
        model: str,
        messages: List[Dict[str, str]],
    ) -> str:
        """Вызов OpenRouter API для генерации ответа."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Опционально
            "X-Title": "Deal Chat Assistant",  # Опционально
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            result = response.json()
            
            # Извлекаем ответ
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"Неожиданный формат ответа от OpenRouter: {result}")
                return "⚠️ Не удалось получить ответ от AI."

        except requests.exceptions.RequestException as exc:
            logger.error(f"Ошибка при запросе к OpenRouter API: {exc}", exc_info=True)
            raise
        except Exception as exc:
            logger.error(f"Неожиданная ошибка при обработке ответа OpenRouter: {exc}", exc_info=True)
            raise
