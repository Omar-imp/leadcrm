import os
import json
from django.utils import timezone
from groq import Groq
from leads.models import AssistantPermission, AssistantConversation, AssistantMessage, AssistantAuditLog
from .tools import TOOL_REGISTRY, TOOL_SCHEMAS

client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

CRM_SYSTEM_PROMPT = """You are the CRM Assistant for a Lead CRM system (Hajj/Umrah travel business).
You have access to CRM-wide data: all leads, tasks, meetings, quotations, and salesperson performance.
Answer naturally and conversationally, like a knowledgeable colleague — not a robotic command parser.
Use the tools available to fetch real data before answering. Never make up numbers or names.
If a follow-up question refers to something mentioned earlier in the conversation, use that context.
Keep answers concise and useful — a sentence or short list, not a wall of text, unless asked for detail."""

SALES_SYSTEM_PROMPT = """You are the Sales Assistant for a Lead CRM system (Hajj/Umrah travel business).
You only have access to the logged-in salesperson's own leads, tasks, meetings, and quotations — never other salespeople's data or company-wide analytics.
Answer naturally and conversationally, like a helpful colleague — not a robotic command parser.
Use the tools available to fetch real data before answering. Never make up numbers or names.
If a follow-up question refers to something mentioned earlier in the conversation, use that context.
Keep answers concise and useful."""

# which tools each assistant type is allowed to see/call
CRM_TOOLS = ['show_hot_leads', 'show_pending_tasks', 'show_today_meetings',
             'show_best_salesperson', 'show_quotations_above',
             'create_followup', 'create_meeting', 'create_quotation']

SALES_TOOLS = ['show_hot_leads', 'show_pending_tasks', 'show_today_meetings',
               'show_quotations_above', 'create_followup', 'create_meeting', 'create_quotation']


class AssistantService:
    def __init__(self, user, assistant_type):
        self.user = user
        self.assistant_type = assistant_type
        self.permission, _ = AssistantPermission.objects.get_or_create(user=user)

    def check_access(self):
        return self.permission.can_query(self.assistant_type)

    def handle_message(self, message_text, conversation_id=None):
        if not self.check_access():
            return {'response': "You don't have access to this assistant."}

        conversation = self._get_or_create_conversation(conversation_id)
        AssistantMessage.objects.create(conversation=conversation, role='user', content=message_text)

        history = self._build_history(conversation)
        allowed_tools = CRM_TOOLS if self.assistant_type == 'crm' else SALES_TOOLS
        system_prompt = CRM_SYSTEM_PROMPT if self.assistant_type == 'crm' else SALES_SYSTEM_PROMPT

        response_text = self._run_llm_loop(system_prompt, history, allowed_tools, message_text)

        AssistantMessage.objects.create(conversation=conversation, role='assistant', content=response_text)
        return {'conversation_id': conversation.id, 'response': response_text}

    def _build_history(self, conversation):
        messages = list(conversation.messages.order_by('created_at').values('role', 'content'))
        # cap history so we don't blow context — last 10 turns is plenty
        return messages[-20:]

    def _run_llm_loop(self, system_prompt, history, allowed_tools, latest_message):
        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            role = 'assistant' if m['role'] == 'assistant' else 'user'
            messages.append({"role": role, "content": m['content']})

        tool_schemas = [TOOL_SCHEMAS[name] for name in allowed_tools if name in TOOL_SCHEMAS]

        max_iterations = 4
        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=600,
                messages=messages,
                tools=tool_schemas,
                tool_choice="auto",
            )
            choice = response.choices[0]
            msg = choice.message

            if not msg.tool_calls:
                return msg.content or "I'm not sure how to answer that."

            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})

            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                try:
                    params = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    params = {}

                if tool_name not in allowed_tools or tool_name not in TOOL_REGISTRY:
                    result = {'error': 'Tool not permitted'}
                    success = False
                else:
                    tool = TOOL_REGISTRY[tool_name]
                    if tool['requires_action'] and not self.permission.can_act(self.assistant_type):
                        result = {'error': 'View-only access — action not permitted'}
                        success = False
                    else:
                        try:
                            result = tool['fn'](self.user, self.assistant_type, params)
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

    def _get_or_create_conversation(self, conversation_id):
        if conversation_id:
            try:
                return AssistantConversation.objects.get(id=conversation_id, user=self.user)
            except AssistantConversation.DoesNotExist:
                pass
        return AssistantConversation.objects.create(user=self.user, assistant_type=self.assistant_type)

    def _audit(self, query, action, success, response):
        AssistantAuditLog.objects.create(
            user=self.user,
            assistant_type=self.assistant_type,
            query=query,
            action_executed=action,
            success=success,
            response=response[:2000],
        )