# LeadCRM

A Django-based CRM platform with three parts in one project:

- **Lead CRM**: lead management with AI-assisted sales tools
- **E-commerce CRM**: store operations from products to refunds
- **WhatsApp chatbot**: an AI sales assistant that talks to leads on WhatsApp and books demos

AI features run on [Groq](https://groq.com) (`openai/gpt-oss-120b`).

## Features

### Lead CRM
- Lead, contact and company management, sales pipeline, quotations and proposals
- Meetings, tasks, projects and support tickets
- Per-user access control
- AI tools: lead scoring, duplicate lead detection, follow-up message drafts, churn risk, upsell recommendations, closing insights, lead assignment, sales forecasting, lifetime value, next best action, meeting summaries and AI proposal writing
- In-app AI assistant

### E-commerce CRM
- Products, categories, customers (with CSV/Excel bulk import) and orders
- Inventory with low-stock alerts, multiple warehouses and stock transfers
- Suppliers and purchase orders (receiving an order updates stock)
- Payments, invoices (PDF export), shipping, returns and refunds
- Support tickets with reply threads and in-app notifications
- Coupons and promotions, loyalty points, abandoned cart tracking and product reviews
- Document storage, reports and an analytics dashboard
- Section-level permissions per user (no access / view only / full access)
- AI assistant that answers questions and can create orders using tool calling, with an audit log

### WhatsApp chatbot
- Receives and replies to WhatsApp messages through the Meta WhatsApp Cloud API
- AI sales assistant that qualifies leads step by step (business type, service, timeline)
- Books demos and creates a matching meeting in the CRM
- Hands the conversation to a human when needed
- Looks up existing leads by phone number for context

## Tech stack

- Python and Django
- SQLite (default database)
- Groq API (LLM)
- Meta WhatsApp Cloud API
- python-dotenv, requests, openpyxl, pdfplumber, pypdf, pypdfium2

## Getting started

Requires Python 3.12 or newer.

```bash
# 1. Clone the repository
git clone https://github.com/Omar-imp/leadcrm.git
cd leadcrm

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# then open .env and fill in your own keys

# 5. Set up the database and an admin user
python manage.py migrate
python manage.py createsuperuser

# 6. Run the app
python manage.py runserver
```

Then open `http://127.0.0.1:8000/`. The E-commerce CRM lives under `/ecommerce/`.

## Configuration

All secrets are read from environment variables (see `.env.example`).

| Variable | Used for |
| --- | --- |
| `GROQ_API_KEY` | AI features |
| `META_WHATSAPP_TOKEN`, `META_PHONE_NUMBER_ID` | Sending WhatsApp messages |
| `META_VERIFY_TOKEN` | Verifying the WhatsApp webhook |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Sending email over SMTP |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `SITE_BASE_URL` | Base URL of the app |

The AI features need a Groq API key. Without one, the WhatsApp chatbot falls back to simple placeholder replies.

## WhatsApp chatbot setup

1. Create a Meta app with the WhatsApp Cloud API and note your access token and phone number ID.
2. Put them in `.env` and choose a verify token.
3. Expose your local server with a public HTTPS URL (for example with ngrok).
4. In Meta's webhook settings, set the callback URL to `https://<your-public-url>/chatbot/webhook/` and use your verify token.

## Project structure

```
leadcrm/        Django project settings and URLs
leads/          Lead CRM app and its AI modules
ecommerce/      E-commerce CRM app, including its AI assistant
chatbot/        WhatsApp chatbot (webhook, AI replies, demo booking)
static/         CSS and images
```

## Notes

- This is a learning and portfolio project, not hardened for production use. Before deploying, set `DEBUG = False`, use a strong `SECRET_KEY`, restrict `ALLOWED_HOSTS` and switch to a production database.
- `db.sqlite3`, `.env` and uploaded media are excluded from the repository.
