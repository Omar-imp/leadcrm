import os
from groq import Groq
from leads.models import Lead

client = Groq(api_key=os.environ.get('GROQ_API_KEY'))


def call_llm_for_content(intent, user, assistant_type):
    task = intent['task']
    lead_id = intent['params'].get('lead_id')
    lead = Lead.objects.filter(id=lead_id).first() if lead_id else None

    prompts = {
        'generate_proposal': f"Write a concise business proposal for lead: {lead.name if lead else 'unspecified'}, contact: {lead.contact_number if lead else ''}.",
        'meeting_summary': f"Summarize the latest meeting notes for lead: {lead.name if lead else 'unspecified'}.",
        'draft_email': f"Draft a professional follow-up email for lead: {lead.name if lead else 'unspecified'}.",
        'draft_whatsapp': f"Draft a short, friendly WhatsApp follow-up message for lead: {lead.name if lead else 'unspecified'}.",
        'followup_content': f"Write follow-up talking points for lead: {lead.name if lead else 'unspecified'}.",
    }

    prompt = prompts.get(task, intent.get('raw_text', ''))

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content