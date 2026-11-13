# Verxas AI Receptionist

**An AI-powered voice receptionist and appointment management platform for clinics and businesses.**

Verxas AI Receptionist is a voice-based automation system designed to help clinics manage incoming calls, answer customer queries, check doctor availability, and handle appointments automatically.

The project currently uses Smile Dental Clinic, Islamabad, as its pilot clinic, with the long-term goal of supporting multiple businesses through one centralized platform.

## Features

### AI Voice Receptionist
- Handles incoming customer conversations using Vapi.
- Provides clinic information and opening hours.
- Answers questions about doctors and their specialties.
- Supports appointment-related conversations.

### Appointment Management
- Checks real-time doctor availability.
- Books appointments through the backend.
- Cancels existing appointments.
- Reschedules appointments.
- Prevents overlapping bookings.
- Validates doctor schedules and clinic working hours.

### Backend & Database
- FastAPI backend for business logic and API endpoints.
- Supabase PostgreSQL database.
- Timezone-aware appointment scheduling.
- Business-specific appointment management.
- Secure webhook authentication.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend development |
| FastAPI | REST API and backend services |
| Supabase | Database and data management |
| PostgreSQL | Relational database |
| Vapi | AI voice receptionist |
| Pydantic | Data validation |
| Uvicorn | ASGI server |
| Ngrok | Local development webhook access |

## Project Structure

```text
verxas-ai-receptionist/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── services/
│   │       └── booking.py
│   │
│   ├── requirements.txt
│   └── .env
│
├── .gitignore
└── README.md
```

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/rabiaabbasi/verxas-ai-receptionist.git
cd verxas-ai-receptionist
```

### 2. Set Up the Backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment on Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file inside the backend directory.

Add the required configuration:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
BUSINESS_ID=your_business_id
VAPI_WEBHOOK_SECRET=your_webhook_secret
```

Keep all API keys and credentials private. Never commit your `.env` file to GitHub.

### 5. Run the Backend

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 6. Access the API

Open the following URLs:

- API: http://127.0.0.1:8000
- Health Check: http://127.0.0.1:8000/health
- Interactive API Documentation: http://127.0.0.1:8000/docs

## Vapi Integration

The project integrates Vapi with FastAPI through custom function tools.

Current configured tools:

1. `get_clinic_information`
2. `get_doctors`
3. `check_availability`
4. `book_appointment`
5. `cancel_appointment`
6. `reschedule_appointment`

Vapi communicates with the backend through an authenticated webhook endpoint:

```text
POST /vapi/tools
```

## Pilot Clinic

**Smile Dental Clinic — Islamabad, Pakistan**

The initial implementation includes:

- Doctor information and specialties.
- Clinic opening hours.
- Doctor-specific schedules.
- Dental consultation service.
- Appointment booking and management.

## Development Roadmap

- [x] Database foundation
- [x] Clinic and doctor data setup
- [x] Appointment availability checking
- [x] Appointment booking
- [x] Appointment cancellation
- [x] Appointment rescheduling
- [x] Double-booking prevention
- [x] Initial Vapi function tool integration
- [ ] Complete end-to-end voice testing
- [ ] Phone number integration
- [ ] Human call transfer
- [ ] Callback request management
- [ ] Call history and transcript management
- [ ] Clinic owner dashboard
- [ ] Multi-clinic onboarding
- [ ] Authentication and role-based access
- [ ] Production deployment

## Project Vision

The long-term vision is to develop a reusable AI receptionist platform where multiple businesses can manage their own AI assistants, customer interactions, appointments, schedules, and business information through a centralized dashboard.

Instead of building a separate receptionist system for every client, Verxas aims to provide one scalable platform that can be configured for different businesses.

## Developer

**Rabia Abbasi**

AI & Software Development | Founder at Verxas

GitHub: https://github.com/rabiaabbasi

---

*Built as part of the Verxas AI initiative.*
