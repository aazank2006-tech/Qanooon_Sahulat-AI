import os
import re
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

from rag.retriever import HybridLegalRetriever
from engine.prompts import SYSTEM_PROMPT

class LegalAdvisor:
    """
    RAG-powered Legal Advisor for Pakistani civic, consumer, tenancy, labor, and cyber laws.
    Supports Roman Urdu, Urdu Nastaliq, and English.
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        
        self.statutes_dir = os.path.join(data_dir, "statutes")
        self.forums_file = os.path.join(data_dir, "forums", "pakistan_legal_forums.json")

        self.retriever = HybridLegalRetriever(self.statutes_dir)
        self.forums = self._load_forums()
        self.gemini_client = self._init_gemini_client()

    def _init_gemini_client(self):
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return None
        try:
            from google import genai
            return genai.Client(api_key=api_key)
        except Exception as e:
            print(f"Warning: Could not initialize Google GenAI client: {e}")
            return None

    def _load_forums(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.forums_file):
            try:
                with open(self.forums_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading forums: {e}")
        return []

    def _detect_template_recommendation(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> Optional[str]:
        # Priority 1: Check category from top retrieved statutory document
        if retrieved_docs:
            cat = retrieved_docs[0].get("category", "")
            if "Tenancy" in cat:
                return "tenancy_notice"
            elif "Consumer" in cat:
                return "consumer_notice"
            elif "Cyber" in cat:
                return "fia_complaint"
            elif "Labor" in cat:
                return "unpaid_wages"

        # Priority 2: Keyword matching with specific domains checked first
        q = query.lower()
        if any(w in q for w in ["makan", "kiraya", "tenant", "advance", "deposit", "landlord", "malik"]):
            return "tenancy_notice"
        if any(w in q for w in ["cyber", "facebook", "whatsapp", "blackmail", "tasweer", "fraud", "scam", "otp", "peca", "tang"]):
            return "fia_complaint"
        if any(w in q for w in ["salary", "tankhwah", "wages", "seth", "job", "terminate", "gratuity", "overtime"]):
            return "unpaid_wages"
        if any(w in q for w in ["consumer", "daraz", "kharab", "wapis", "refund", "dokandar", "defective", "warranty"]):
            return "consumer_notice"

        return None

    def _find_matching_forum(self, category: str, city: Optional[str] = None) -> Optional[Dict[str, Any]]:
        for f in self.forums:
            if category.lower() in f.get("domain", "").lower() or f.get("domain", "").lower() in category.lower():
                forum_copy = dict(f)
                if city and "address_info" in forum_copy and city in forum_copy["address_info"]:
                    forum_copy["city_address"] = forum_copy["address_info"][city]
                return forum_copy
        return self.forums[0] if self.forums else None

    def advise(self, query: str, language: str = "roman_urdu", city: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes a civic legal question, searches relevant statutes, and synthesizes advice.
        """
        # 1. Retrieve statutory knowledge
        retrieved_docs = self.retriever.search(query, top_k=3)

        # 2. Identify likely category and forum
        primary_category = retrieved_docs[0].get("category", "General Civic Rights") if retrieved_docs else "Consumer Protection"
        matched_forum = self._find_matching_forum(primary_category, city)
        recommended_template = self._detect_template_recommendation(query, retrieved_docs)

        # 3. Context assembly
        context_snippets = []
        for i, doc in enumerate(retrieved_docs, 1):
            context_snippets.append(
                f"[Document {i}]\n"
                f"Act: {doc.get('act')}\n"
                f"Section: {doc.get('section')}\n"
                f"Jurisdiction: {doc.get('jurisdiction')}\n"
                f"Forum: {doc.get('forum')}\n"
                f"Limitation: {doc.get('limitation_period')}\n"
                f"English Summary: {doc.get('content_english')}\n"
                f"Urdu Summary: {doc.get('content_urdu')}\n"
                f"Roman Urdu Summary: {doc.get('content_roman_urdu')}\n"
            )
        context_str = "\n---\n".join(context_snippets)

        # 4. Generate response via Gemini or Structured Fallback
        answer = None
        if self.gemini_client:
            try:
                lang_instruction = "Respond in natural, conversational Roman Urdu."
                if language == "urdu":
                    lang_instruction = "Respond in formal and clear Urdu script (اردو رسم الخط)."
                elif language == "english":
                    lang_instruction = "Respond in clear English, with statutory section citations."

                prompt = (
                    f"{SYSTEM_PROMPT}\n\n"
                    f"User Selected Language: {lang_instruction}\n"
                    f"User City / Location: {city or 'Pakistan (General)'}\n\n"
                    f"RELEVANT PAKISTANI STATUTORY CONTEXT:\n{context_str}\n\n"
                    f"USER QUERY: {query}\n\n"
                    f"Please provide complete advice answering: 1) What is their legal right? 2) Which sections apply? 3) Which exact forum/court to approach and whether a lawyer is needed? 4) Immediate next step."
                )

                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                if response and response.text:
                    answer = response.text
            except Exception as e:
                print(f"Gemini API call failed or rate-limited: {e}")

        # Fallback offline generator if Gemini client is not initialized or failed
        if not answer:
            answer = self._generate_fallback_advice(query, retrieved_docs, matched_forum, language)

        return {
            "query": query,
            "language": language,
            "answer": answer,
            "citations": [
                {
                    "act": d.get("act"),
                    "section": d.get("section"),
                    "forum": d.get("forum"),
                    "limitation": d.get("limitation_period")
                } for d in retrieved_docs
            ],
            "forum": matched_forum,
            "recommended_template": recommended_template
        }

    def _generate_fallback_advice(self, query: str, docs: List[Dict[str, Any]], forum: Optional[Dict[str, Any]], language: str) -> str:
        """
        High-fidelity statutory synthesis when running offline or without an active Gemini API key.
        """
        if not docs:
            if language == "urdu":
                return "معذرت، اس سوال کے متعلق مخصوص قانون تلاش نہیں ہو سکا۔ برائے مہربانی اپنا مسئلہ مزید وضاحت سے تحریر فرمائیں۔"
            elif language == "english":
                return "We could not find an exact statutory match for your query. Please provide more specific details regarding your dispute."
            else:
                return "Maazrat, is sawal k mutabiq qanoon nahi mil saka. Barah-e-karam apna masla mazeed wazahat se likhein."

        top_doc = docs[0]
        act = top_doc.get("act", "Pakistani Law")
        sec = top_doc.get("section", "Applicable Section")
        forum_name = forum.get("name_english", "Competent Court / Authority") if forum else "District Court"
        court_fee = forum.get("court_fee", "Nominal") if forum else "Zero"
        lawyer_needed = forum.get("lawyer_needed", "Self-representation permitted") if forum else "Optional"
        mandatory_step = forum.get("mandatory_step", "Preserve relevant receipts and evidence") if forum else "Gather proof"

        if language == "urdu":
            explanation = top_doc.get("content_urdu", top_doc.get("content_english", ""))
            return f"""### آپ کا قانونی حق (خلاصہ):
{explanation}

### متعلقہ قانون اور دفعات:
• **ایکٹ**: {act}
• **دفعہ (Section)**: {sec}
• **مدتِ میعاد (Limitation)**: {top_doc.get('limitation_period')}

### کونسے ادارے یا عدالت رجوع کریں؟
• **مجاز فورم**: {forum.get('name_urdu', forum_name)}
• **کورٹ فیس**: {court_fee}
• **وکیل کی ضرورت**: {lawyer_needed}

### اگلا فوری قدم:
{mandatory_step}

---
⚖️ *قانونی آگاہی ڈسکلیمر: یہ معلومات عام شہری آگاہی کے لیے ہیں اور کسی وکیل کی رسمی قانونی مشاورت یا وکیل-کلائنٹ تعلق کا متبادل نہیں ہیں۔*"""

        elif language == "english":
            explanation = top_doc.get("content_english", "")
            return f"""### Your Legal Rights (Summary):
{explanation}

### Statutory Authority & Sections:
• **Act**: {act}
• **Section**: {sec}
• **Limitation Period**: {top_doc.get('limitation_period')}

### Competent Forum to Approach:
• **Forum**: {forum_name}
• **Court Fee**: {court_fee}
• **Lawyer Required**: {lawyer_needed}

### Immediate Next Step:
{mandatory_step}

---
⚖️ *Legal Information Disclaimer: This advice is provided for informational and civic awareness purposes only and does not constitute formal legal counsel or establish an attorney-client relationship.*"""

        else: # roman_urdu
            explanation = top_doc.get("content_roman_urdu", top_doc.get("content_english", ""))
            return f"""### 📌 Aapka Qanooni Haq (Khulasa):
{explanation}

### 📜 Qanooni Dafaat (Applicable Law & Sections):
• **Qanoon**: {act}
• **Section**: {sec}
• **Waqt ki Pabandee (Limitation Period)**: {top_doc.get('limitation_period')}

### 🏛️ Kahan Jana He? (Forum & Court):
• **Idara / Adalat**: {forum_name}
• **Court Fee**: {court_fee}
• **Wakeel ki Zaroorat**: {lawyer_needed}

### ⚡ Agla Fauri Qadam (Immediate Step):
{mandatory_step}

---
⚖️ *Qanooni Aagahi Disclaimer: Ye maloomat aam shehri aagahi ke liye hain aur kisi wakeel ki rasmi qanooni mushawarat ya wakeel-client taaluq ka mutabadil nahi hain.*"""
