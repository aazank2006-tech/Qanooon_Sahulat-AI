# QanoonSahulat (قانون سہولت)
### Urdu-First Pakistani Legal & Rights Explainer with Automated Statutory Notice Generator

An access-to-justice AI platform for Pakistani citizens that bridges the language and knowledge barrier in the legal system. It uses RAG over Pakistani statutory laws (Consumer Protection, Tenancy, Cybercrime/PECA, and Labor laws) to explain citizen rights in simple **Roman Urdu** or **Urdu script**, identify the exact competent forum to approach, and auto-draft enforceable legal notices.

---

## 🌟 Key Features

1. **Urdu & Roman Urdu Accessibility**:
   - Queries can be typed in colloquial phonetic Roman Urdu (*"makan malik advance wapis nahi kr raha"*) or standard Urdu script (*"مکان مالک ایڈوانس واپس نہیں کر رہا"*).
2. **Statutory Grounding & Guardrails**:
   - Strictly references specific sections of Pakistani statutes (e.g., *Section 28 of Punjab Consumer Protection Act 2005*, *Section 10 of Punjab Rented Premises Act 2009*, *Sections 20, 21 & 24 of PECA 2016*).
   - Enforces prominent legal information disclaimers in accordance with legal and bar council guidelines.
3. **Court & Forum Routing**:
   - Details the exact judicial or administrative authority (e.g., District Consumer Protection Court, Rent Tribunal, FIA Cyber Crime Reporting Center, Authority under Payment of Wages Act).
   - Provides fees (highlighting free forums like Consumer Courts and Banking Mohtasib) and indicates whether self-representation is permitted.
4. **Automated Legal Document & Notice Generator**:
   - **15-Day Consumer Pre-Suit Legal Notice** (Mandatory prerequisite under Section 28 before court filing).
   - **Tenancy Security Deposit Refund Demand Notice** (Section 10).
   - **FIA Cyber Crime Wing Formal Complaint Application** (Sections 14/20/21/24 of PECA 2016).
   - **Recovery of Unpaid Wages & Settlement Notice** (Payment of Wages Act 1936).
5. **Dual Interface**:
   - **Interactive Web App**: Built with Streamlit featuring responsive Urdu Nastaliq styling.
   - **WhatsApp Bot Service**: Built with FastAPI for Meta WhatsApp Cloud API webhooks and voice-note readiness.

---

## 📁 Project Architecture

```
qanoon_sahulat/
├── app.py                      # Streamlit interactive web portal
├── whatsapp_service.py         # FastAPI WhatsApp Cloud API webhook service
├── test_system.py              # Automated test suite
├── data/
│   ├── statutes/               # Curated Pakistani statutory corpus with metadata
│   │   ├── consumer_protection.json
│   │   ├── peca_cybercrime.json
│   │   ├── tenancy_rent.json
│   │   └── labor_employment.json
│   └── forums/
│       └── pakistan_legal_forums.json # Legal forums, locations & guidelines
├── rag/
│   └── retriever.py            # Section-aware Hybrid BM25 & Semantic retriever
├── engine/
│   ├── legal_advisor.py        # Gemini 2.5 Flash / Statutory synthesis engine
│   └── prompts.py              # Bilingual prompt guardrails and templates
├── drafting/
│   ├── notice_generator.py     # Template rendering engine
│   └── templates/              # Jinja2 statutory legal notice templates
│       ├── consumer_notice.j2
│       ├── tenancy_deposit_notice.j2
│       ├── fia_cybercrime_complaint.j2
│       └── unpaid_wages_notice.j2
└── requirements.txt
```

---

## 🚀 Running the Project

### 1. Run Automated Tests
```powershell
.\.venv\Scripts\python.exe test_system.py
```

### 2. Launch the Streamlit Web Application
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```
Open your browser at `http://localhost:8501`.

### 3. Launch the WhatsApp Bot Service (FastAPI)
```powershell
.\.venv\Scripts\uvicorn.exe whatsapp_service:app --reload --port 8000
```
- Interactive API Docs & Simulator: `http://localhost:8000/docs`
- WhatsApp Webhook URL: `http://localhost:8000/webhook`

---

## ⚖️ Legal Disclaimer
*QanoonSahulat is an automated civic legal empowerment platform. The information generated is for public education and informational purposes only and does not constitute formal legal counsel or create an attorney-client relationship. For complex litigation, users are advised to consult a licensed advocate.*
