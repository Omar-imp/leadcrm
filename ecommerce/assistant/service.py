import os
import json
from groq import Client as GroqClientBase
from groq import Groq
from ecommerce.models import (
    EcommerceAssistantConversation, EcommerceAssistantMessage,
    EcommerceAssistantAuditLog, EcommerceUserPermissions
)
from .tools import TOOL_REGISTRY, TOOL_SCHEMAS

client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

ALL_TOOLS = list(TOOL_SCHEMAS.keys())

ECOMMERCE_SYSTEM_PROMPT = """You are the Assistant for Raabta 360's E-commerce CRM.
You help staff manage products, orders, customers, inventory, and payments.
Answer naturally and conversationally, like a knowledgeable colleague — not a robotic command parser.
Use the tools available to fetch real data before answering. Never make up numbers or names.
If a follow-up question refers to something mentioned earlier in the conversation, use that context.
If the user refers to a customer or product by name rather than ID, use search_customers_by_name or search_products_by_name first to find the correct ID before taking any action.
If more than one match is found, list them and ask which one they mean before proceeding.
Before creating an order, briefly confirm the details (customer name, product name, quantity) in your response and only call create_order once the user's message clearly confirms or the details were unambiguous and explicitly requested.
Never write function calls as plain text in your response (e.g. never output things like <function=...> or similar). Only use the proper tool-calling mechanism provided to you.
Never mention tool or function names to the user. If the user asks where to find something you can look up, call the appropriate tool yourself and show them the actual result — don't describe how they could look it up themselves.
Never claim you created, updated, or found something unless you actually called the corresponding tool and it returned success. If no matching tool exists for what the user is asking, say so honestly instead of pretending it was done.
Keep answers concise and useful — a sentence or short list, not a wall of text, unless asked for detail."""


class EcommerceAssistantService:
    def __init__(self, user):
        self.user = user
        self.permission, _ = EcommerceUserPermissions.objects.get_or_create(user=user)

    def can_query(self):
        if self.user.is_superuser:
            return True
        return self.permission.chatbot in ('view', 'full')

    def can_act(self):
        if self.user.is_superuser:
            return True
        return self.permission.chatbot == 'full'

    def _audit(self, query, action, success, response):
        EcommerceAssistantAuditLog.objects.create(
            user=self.user,
            query=query[:1000],
            action_executed=action,
            success=success,
            response=response[:2000] if response else '',
        )

    def _build_history(self, conversation):
        msgs = list(conversation.messages.order_by('created_at').values('role', 'content'))
        return msgs[-20:]

    def handle_message(self, message, conversation_id=None):
        if not self.can_query():
            return {'response': "You don't have access to this assistant.", 'conversation_id': conversation_id}

        if conversation_id:
            conversation = EcommerceAssistantConversation.objects.filter(id=conversation_id, user=self.user).first()
        else:
            conversation = None

        if not conversation:
            conversation = EcommerceAssistantConversation.objects.create(user=self.user)

        EcommerceAssistantMessage.objects.create(conversation=conversation, role='user', content=message)

        history = self._build_history(conversation)
        response_text = self._run_llm_loop(history, message)

        EcommerceAssistantMessage.objects.create(conversation=conversation, role='assistant', content=response_text)
        conversation.save()  # bump updated_at

        return {'response': response_text, 'conversation_id': conversation.id}

    def _run_llm_loop(self, history, latest_message):
        messages = [{"role": "system", "content": ECOMMERCE_SYSTEM_PROMPT}]
        for m in history:
            role = 'assistant' if m['role'] == 'assistant' else 'user'
            messages.append({"role": role, "content": m['content']})

        tool_schemas = [TOOL_SCHEMAS[name] for name in ALL_TOOLS if name in TOOL_SCHEMAS]

        seen_calls = set()
        max_iterations = 6
        for _ in range(max_iterations):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=600,
                    messages=messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                    parallel_tool_calls=False,
                )
            except Exception as e:
                error_str = str(e)
                if 'tool_use_failed' in error_str:
                    try:
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            max_tokens=600,
                            messages=messages,
                        )
                        choice = response.choices[0]
                        msg = choice.message
                        return msg.content or "Sorry, I couldn't process that — could you rephrase?"
                    except Exception as e2:
                        self._audit(latest_message, 'llm_call', False, str(e2))
                        return "I'm having trouble processing requests right now. Please try again shortly."
                elif 'rate_limit' in error_str or '429' in error_str:
                    self._audit(latest_message, 'llm_call', False, error_str)
                    return "I've hit my usage limit for today — please try again later or contact your admin."
                else:
                    self._audit(latest_message, 'llm_call', False, error_str)
                    return "I'm having trouble reaching the assistant service right now. Please try again in a moment."

            choice = response.choices[0]
            msg = choice.message

            if not msg.tool_calls:
                content = msg.content or ""
                if '<function=' in content or '</function>' in content:
                    messages.append({"role": "assistant", "content": "Let me try that again properly."})
                    messages.append({"role": "user", "content": "Please use the proper tool-calling mechanism, not text."})
                    continue
                return content or "I'm not sure how to answer that."

            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})

            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name

                call_signature = (tool_name, tool_call.function.arguments)
                if call_signature in seen_calls:
                    return "Here's what I found — let me know if you'd like more detail or want to try a different question."
                seen_calls.add(call_signature)

                try:
                    params = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    params = {}

                if tool_name not in TOOL_REGISTRY:
                    result = {'error': 'Tool not permitted'}
                    success = False
                else:
                    tool = TOOL_REGISTRY[tool_name]
                    if tool['requires_action'] and not self.can_act():
                        result = {'error': 'View-only access — action not permitted'}
                        success = False
                    else:
                        try:
                            result = tool['fn'](self.user, params)
                            success = 'error' not in result
                        except Exception as e:
                            result = {'error': str(e)}
                            success = False

                self._audit(latest_message, tool_name, success, json.dumps(result)[:500])

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

        return "I gathered some information but couldn't finish forming a response — try rephrasing."