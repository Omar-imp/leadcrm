import re

PATTERNS = [
    (r'hot lead', 'show_hot_leads', {}),
    (r'pending task|pending follow', 'show_pending_tasks', {}),
    (r'meeting.*today|today.*meeting', 'show_today_meetings', {}),
    (r'best salesperson|top performer', 'show_best_salesperson', {}),
    (r'quotation.*above|quotation.*over', 'show_quotations_above', {}),
]

LLM_TASKS = [
    (r'proposal', 'generate_proposal'),
    (r'summar.*meeting|meeting summar', 'meeting_summary'),
    (r'draft.*email|email.*draft', 'draft_email'),
    (r'draft.*whatsapp|whatsapp.*draft', 'draft_whatsapp'),
    (r'follow.?up.*content|write.*follow.?up', 'followup_content'),
]


def classify_intent(text):
    lowered = text.lower()

    for pattern, tool_name, extra_params in PATTERNS:
        if re.search(pattern, lowered):
            params = dict(extra_params)
            amount_match = re.search(r'(\d[\d,]*)', lowered)
            if amount_match and tool_name == 'show_quotations_above':
                params['amount'] = int(amount_match.group(1).replace(',', ''))
            lead_match = re.search(r'lead #?(\d+)', lowered)
            if lead_match:
                params['lead_id'] = int(lead_match.group(1))
            return {'tool_name': tool_name, 'params': params, 'needs_llm': False}

    for pattern, task in LLM_TASKS:
        if re.search(pattern, lowered):
            lead_match = re.search(r'lead #?(\d+)', lowered)
            return {
                'tool_name': None,
                'needs_llm': True,
                'task': task,
                'params': {'lead_id': int(lead_match.group(1))} if lead_match else {},
                'raw_text': text,
            }

    if 'follow up' in lowered or 'followup' in lowered:
        lead_match = re.search(r'lead #?(\d+)', lowered)
        return {
            'tool_name': 'create_followup',
            'params': {'lead_id': int(lead_match.group(1)) if lead_match else None, 'days_from_now': 1},
            'needs_llm': False,
        }

    # Fallback keyword routing — catches loose/single-word queries
    if 'lead' in lowered:
        return {'tool_name': 'show_hot_leads', 'params': {}, 'needs_llm': False}
    if 'task' in lowered:
        return {'tool_name': 'show_pending_tasks', 'params': {}, 'needs_llm': False}
    if 'meeting' in lowered:
        return {'tool_name': 'show_today_meetings', 'params': {}, 'needs_llm': False}
    if 'quotation' in lowered:
        return {'tool_name': 'show_quotations_above', 'params': {}, 'needs_llm': False}
    if 'salesperson' in lowered or 'performer' in lowered:
        return {'tool_name': 'show_best_salesperson', 'params': {}, 'needs_llm': False}

    return {'tool_name': None, 'needs_llm': False, 'params': {}}