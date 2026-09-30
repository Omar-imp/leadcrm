"""
AI Proposal Writer using Groq.
Extracts PDF text and merges with manual notes to generate
a professional business proposal.
"""
import logging
import os
logger = logging.getLogger(__name__)


def extract_pdf_text(pdf_file_path: str) -> str:
    """
    Extracts raw text from a PDF file.
    Tries pdfplumber first (better formatting), falls back to pypdf.
    Returns empty string if extraction fails or no file provided.
    """
    if not pdf_file_path or not os.path.exists(pdf_file_path):
        return ''

    # try pdfplumber first — better at tables and formatting
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        if text_parts:
            extracted = '\n\n'.join(text_parts)
            logger.info(
                'Extracted %d chars from PDF via pdfplumber: %s',
                len(extracted), pdf_file_path
            )
            return extracted
    except Exception as exc:
        logger.warning('pdfplumber failed, trying pypdf: %s', exc)

    # fallback to pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        extracted = '\n\n'.join(text_parts)
        logger.info(
            'Extracted %d chars from PDF via pypdf: %s',
            len(extracted), pdf_file_path
        )
        return extracted
    except Exception as exc:
        logger.error('PDF extraction completely failed: %s', exc)
        return ''


def generate_proposal(
    manual_notes: str = '',
    pdf_text: str = '',
    lead_context: dict = None,
) -> str:
    """
    Generates a professional business proposal using Groq.

    Args:
        manual_notes:  User's rough notes typed into the textarea
        pdf_text:      Text extracted from uploaded PDF
        lead_context:  Dict with lead info (name, company, quotation etc)

    Returns:
        Generated proposal as a Markdown string.
        Never raises — returns error message string on failure.
    """
    try:
        from django.conf import settings
        from groq import Groq

        if not manual_notes.strip() and not pdf_text.strip():
            return (
                '## Error\n\n'
                'Please provide either a PDF file or manual notes '
                '(or both) to generate a proposal.'
            )

        client = Groq(api_key=settings.GROQ_API_KEY)

        # build lead context string
        lead_info = ''
        if lead_context:
            lead_info = f"""
CLIENT INFORMATION:
- Client Name: {lead_context.get('name', 'Valued Client')}
- Company: {lead_context.get('company', 'N/A')}
- Email: {lead_context.get('email', 'N/A')}
- Budget/Quotation: {lead_context.get('quotation', 'To be discussed')}
- Source: {lead_context.get('source', 'N/A')}
"""

        system_prompt = """
You are a Senior Business Development Writer at Synergy Integrated Solutions,
a professional software and digital solutions company.

Your task is to write a complete, professional business proposal in Markdown format.

CRITICAL RULES:
1. Manual notes provided by the user ALWAYS take absolute priority.
   If anything in the PDF contradicts the manual notes, use the manual notes.
2. Merge all information intelligently — do not repeat the same point twice.
3. Never hallucinate or invent facts. Only use information provided.
4. Keep a professional, confident and client-focused tone.
5. Use specific numbers, timelines and deliverables where provided.
6. If pricing is not provided, write "To be discussed based on requirements".

OUTPUT FORMAT — write exactly these sections in order:

# [Proposal Title]

## Executive Summary
[2-3 paragraphs summarizing the opportunity, our understanding of the client's needs, and why Synergy is the right partner]

## Client Challenges & Objectives
[Bullet points of the client's key problems we are solving]

## Proposed Solution
[Detailed description of what we will build/deliver, organized by component]

## Scope of Work
[Clear list of deliverables with brief description of each]

## Pricing

| Service | Description | Cost |
|---------|-------------|------|
| [item]  | [desc]      | [price] |

**Total Investment:** [total or "To be discussed"]

## Project Timeline

| Phase | Deliverable | Duration |
|-------|------------|----------|
| Phase 1 | [milestone] | [X weeks] |
| Phase 2 | [milestone] | [X weeks] |

**Estimated Total Duration:** [X weeks/months]

## Why Synergy Integrated Solutions
- [3-5 bullet points on our strengths and relevant experience]

## Terms & Next Steps
[Brief paragraph on how to proceed, payment terms if provided, and CTA]

---
*This proposal is valid for 30 days from the date of issue.*
*Synergy Integrated Solutions | +92 334 1674855 | synergyintegratedsolutions.pk*
""".strip()

        # build user message
        sections = []

        if lead_info:
            sections.append(lead_info.strip())

        if manual_notes.strip():
            sections.append(
                f"MANUAL NOTES FROM SALES TEAM "
                f"(HIGHEST PRIORITY — override PDF if conflicting):\n"
                f"{manual_notes.strip()}"
            )

        if pdf_text.strip():
            # truncate PDF text if too long
            truncated = pdf_text.strip()[:6000]
            if len(pdf_text) > 6000:
                truncated += '\n\n[PDF content truncated for length]'
            sections.append(
                f"EXTRACTED PDF CONTENT:\n{truncated}"
            )

        user_message = (
            'Based on the information below, write a complete professional '
            'business proposal following the exact format specified.\n\n'
            + '\n\n---\n\n'.join(sections)
        )

        response = client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message},
            ],
            max_tokens=4000,
            temperature=0.2,
        )

        proposal_text = response.choices[0].message.content.strip()
        logger.info('AI proposal generated successfully (%d chars)', len(proposal_text))
        return proposal_text

    except Exception as exc:
        logger.exception('Proposal generation failed: %s', exc)
        return f'## Generation Failed\n\nError: {exc}\n\nPlease try again.'