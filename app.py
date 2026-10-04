import os
import streamlit as st
from datetime import datetime
from engine.legal_advisor import LegalAdvisor
from drafting.notice_generator import NoticeGenerator

# Configure Streamlit page
st.set_page_config(
    page_title="QanoonSahulat | قانون سہولت - Pakistani Legal & Rights Explainer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Nastaliq Urdu, Roman Urdu, and modern legal card badges
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&family=Inter:wght@300;400;600;700&display=swap');

    .urdu-font {
        font-family: 'Noto Nastaliq Urdu', serif;
        direction: rtl;
        text-align: right;
        font-size: 1.25rem;
        line-height: 2.2;
    }
    .badge-statute {
        background-color: #0b5351;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .badge-forum {
        background-color: #003566;
        color: #ffc300;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-right: 6px;
    }
    .legal-card {
        background-color: #f8f9fa;
        border-left: 5px solid #0077b6;
        padding: 16px 20px;
        border-radius: 8px;
        margin: 14px 0px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .disclaimer-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 12px 16px;
        border-radius: 8px;
        font-size: 0.88rem;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Advisor and Generator in session state
@st.cache_resource
def get_advisor_and_generator():
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data")
    advisor = LegalAdvisor(data_dir=data_dir)
    generator = NoticeGenerator()
    return advisor, generator

advisor, generator = get_advisor_and_generator()

# Sidebar Settings
st.sidebar.image("https://img.icons8.com/color/96/scales--v1.png", width=70)
st.sidebar.title("QanoonSahulat (قانون سہولت)")
st.sidebar.caption("🇵🇰 Urdu-First Legal Rights Explainer & Notice Generator")

language_choice = st.sidebar.selectbox(
    "🌐 Language / زبان منتخب کریں:",
    ["Roman Urdu (رومن اردو)", "Urdu (اردو رسم الخط)", "English"],
    index=0
)
lang_key = "roman_urdu"
if "Urdu (" in language_choice:
    lang_key = "urdu"
elif language_choice == "English":
    lang_key = "english"

city_choice = st.sidebar.selectbox(
    "📍 Your City / آپ کا شہر:",
    ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Gujranwala", "Other / تمام پاکستان"],
    index=0
)

# Optional Gemini API Key config
api_key_env = os.environ.get("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input("🔑 Gemini API Key (Optional):", value=api_key_env, type="password", help="If provided, enables dynamic Gemini 2.5/3.8 Flash legal reasoning. If blank, uses built-in statutory RAG.")
if api_key_input:
    os.environ["GEMINI_API_KEY"] = api_key_input
    # Re-init client if newly provided
    if not advisor.gemini_client:
        advisor.gemini_client = advisor._init_gemini_client()

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Covered Legal Domains:**
- 🛒 Consumer Rights (15-Day Notice)
- 🏠 Tenancy & Eviction Protection
- 📱 Cybercrime & Blackmail (PECA 2016)
- 💼 Unpaid Wages & Employment Rights
""")

# Main Navigation Tabs
tab_explainer, tab_drafting, tab_forums, tab_library = st.tabs([
    "💡 Rights Explainer (حقوق کی معلومات)",
    "📝 Legal Notice Generator (قانونی نوٹس تیار کریں)",
    "🏛️ Authority / Forum Finder (عدالت تلاش کریں)",
    "📚 Statutes Library (قوانین کی فہرست)"
])

# ==============================================================================
# TAB 1: Rights Explainer & Chat
# ==============================================================================
with tab_explainer:
    st.header("⚖️ Pakistani Legal Rights Explainer")
    st.write("Apna masla aam Roman Urdu ya Urdu me bayan karein. Hamara RAG system Pakistani qawaneen ke tehat aapke haqooq aur agla qadam bataye ga.")

    # Quick scenario buttons
    st.markdown("**📌 Quick Scenarios (Yahan se koi misaal muntakhab karein):**")
    col1, col2 = st.columns(2)
    sample_query = None
    with col1:
        if st.button("🛒 Daraz se kharab mobile mila, wapis nahi kr rahay"):
            sample_query = "Daraz se kharab mobile mila he, shopkeeper keh raha he warranty nahi he aur wapis nahi kar raha, meray paisay wapis kaisay milein gay?"
        if st.button("🏠 Makan malik advance wapis nahi kr raha"):
            sample_query = "Maine ghar khali kar dia he aur saray bijli gas k bill ada kar diye hain, lekin makan malik 1 lakh advance security deposit wapis nahi kar raha."
    with col2:
        if st.button("📱 Facebook / WhatsApp par koi photos se blackmail kr raha he"):
            sample_query = "Social media WhatsApp par aik shakhs meri tasweerein viral karne ki dhamki de kar blackmail kar raha he aur paisay maang raha he."
        if st.button("💼 Seth 3 mahinay se tankhwah nahi de raha"):
            sample_query = "Main factory me kaam karta tha, seth ne 3 mahinay se tankhwah roki hui he aur ab nokri se nikaal dia he bina kisi notice k."

    user_query = st.text_area(
        "Enter your legal question or situation here:",
        value=sample_query if sample_query else "",
        placeholder="Maslan: Makan malik ne bijli ka meter katwa dia he... ya online shopping me fraud ho gaya...",
        height=100
    )

    if st.button("🔍 Explain My Rights (میرے حقوق بتائیں)", type="primary"):
        if not user_query.strip():
            st.warning("Please enter a question or select a scenario above.")
        else:
            with st.spinner("Analyzing Pakistani statutes, precedents, and competent courts..."):
                advice_result = advisor.advise(user_query, language=lang_key, city=city_choice)

                is_urdu_script = (lang_key == "urdu")
                text_css = "urdu-font" if is_urdu_script else ""

                st.markdown(f'<div class="{text_css}">', unsafe_allow_html=True)
                st.markdown(advice_result["answer"])
                st.markdown('</div>', unsafe_allow_html=True)

                # Forum Summary Card
                forum = advice_result.get("forum")
                if forum:
                    st.markdown("---")
                    st.subheader("🏛️ Competent Authority / Court to Approach")
                    f_col1, f_col2 = st.columns(2)
                    with f_col1:
                        st.markdown(f"**Court / Office:** {forum.get('name_english')} ({forum.get('name_urdu')})")
                        st.markdown(f"**Presiding Officer:** {forum.get('presiding_officer')}")
                        st.markdown(f"**Court Fee:** {forum.get('court_fee')}")
                    with f_col2:
                        st.markdown(f"**Lawyer Needed?** {forum.get('lawyer_needed')}")
                        if "city_address" in forum:
                            st.markdown(f"**Office Address in {city_choice}:** {forum['city_address']}")
                        elif "helpline" in forum:
                            st.markdown(f"**Helpline / Portal:** {forum.get('helpline')} | [{forum.get('online_portal')}]({forum.get('online_portal')})")

                # Suggest Notice Drafting
                rec_template = advice_result.get("recommended_template")
                if rec_template:
                    st.info(f"💡 **Recommended Action**: You can automatically generate the formal legal document for this dispute in the **Legal Notice Generator** tab.")

# ==============================================================================
# TAB 2: Legal Notice & Complaint Generator
# ==============================================================================
with tab_drafting:
    st.header("📝 Automated Statutory Legal Notice & Complaint Generator")
    st.write("Pakistani adalat ya idaray jane se pehle statutory notice ya application tayyar karein. Ye print karne aur dispatch karne k liye mukammal qanooni format par tayyar hota he.")

    doc_type = st.selectbox(
        "Select Legal Document Type / دستاویز منتخب کریں:",
        [
            ("consumer_notice", "15-Day Consumer Pre-Suit Legal Notice (Section 28 Consumer Act)"),
            ("tenancy_notice", "Tenancy Security Deposit (Advance) Refund Demand Notice (Section 10)"),
            ("fia_complaint", "FIA Cyber Crime Wing Formal Complaint Application (PECA 2016)"),
            ("unpaid_wages", "Notice for Recovery of Unpaid Wages & Gratuity (Payment of Wages Act)")
        ],
        format_func=lambda x: x[1]
    )[0]

    meta = generator.get_template_metadata(doc_type)
    st.markdown(f"**Governing Law:** `{meta.get('governing_law')}` | **Target Forum:** `{meta.get('target_forum')}` | **Statutory Cure Period:** `{meta.get('cure_period')}`")

    with st.form("notice_draft_form"):
        st.subheader("1. Complainant / Sender Details (آپ کی تفصیلات)")
        c1, c2 = st.columns(2)
        with c1:
            s_name = st.text_input("Your Full Name (آپ کا نام):", value="Muhammad Usman Ali")
            s_cnic = st.text_input("CNIC (قومی شناختی کارڈ نمبر):", value="35201-1234567-1")
        with c2:
            s_phone = st.text_input("Mobile / WhatsApp Number:", value="0300-1234567")
            s_address = st.text_input("Your Complete Address:", value="House 12, Street 4, Gulberg III, Lahore")

        st.subheader("2. Opponent / Merchant / Landlord Details (مخالف فریق کی تفصیلات)")
        o1, o2 = st.columns(2)
        with o1:
            o_name = st.text_input("Opponent / Merchant / Landlord Name:", value="Alpha Electronics & Mobile Plaza")
            o_details = st.text_input("Contact / Phone / Shop No:", value="Shop # 14, Hafeez Centre, Main Boulevard, Gulberg, Lahore")
        with o2:
            o_address = st.text_input("Complete Address of Opponent:", value="Hafeez Centre, Main Boulevard, Gulberg, Lahore")
            inc_amount = st.text_input("Disputed Amount (PKR):", value="65,000")

        st.subheader("3. Incident & Claim Details (واقعہ اور دعویٰ کی تفصیل)")
        inc_date = st.text_input("Date of Incident / Purchase / Agreement:", value="15 September, 2026")
        grievance_desc = st.text_area(
            "Grievance Description (Kya masla hua?):",
            value="The complainant purchased a brand-new smartphone model X for PKR 65,000 with a 1-year official company warranty. Within 3 days of purchase, the motherboard suffered total failure. Despite taking it to the respondent's outlet with original receipt and box, the respondent verbally abused the complainant, refused replacement, and refused refund of the price.",
            height=90
        )
        remedy_dem = st.text_input(
            "Remedy Demanded (Aap kya chahte hain?):",
            value="Immediately refund the full purchase price of PKR 65,000 or provide a defect-free brand-new replacement unit with fresh warranty."
        )

        generate_submitted = st.form_submit_button("📄 Draft Statutory Legal Document (نوٹس تیار کریں)", type="primary")

    if generate_submitted:
        notice_data = {
            "date": datetime.now().strftime("%d %B, %Y"),
            "sender_name": s_name,
            "sender_cnic": s_cnic,
            "sender_phone": s_phone,
            "sender_address": s_address,
            "opponent_name": o_name,
            "opponent_details": o_details,
            "opponent_address": o_address,
            "amount": inc_amount,
            "incident_date": inc_date,
            "grievance_description": grievance_desc,
            "remedy_demanded": remedy_dem,
            "compensation_amount": "15,000"
        }

        generated_notice = generator.render_notice(doc_type, notice_data)
        st.success("✅ Statutory Legal Document Drafted Successfully!")

        st.text_area("Generated Document Preview (Copy or Print):", value=generated_notice, height=400)

        st.download_button(
            label="💾 Download Notice (.txt)",
            data=generated_notice,
            file_name=f"legal_notice_{doc_type}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )

        st.markdown("""
        > **⚠️ Important Dispatch Instructions (نوٹس بھیجنے کا طریقہ):**
        > 1. Print 2 copies of this notice. Sign both copies.
        > 2. Send one copy to the opponent via **Pakistan Post Registered Post A.D.** or **TCS / UMS Courier**.
        > 3. Keep the postal booking receipt (`Raseed`) safely. This receipt is **mandatory statutory evidence** under Section 28 of the Consumer Protection Act when filing in court.
        """)

# ==============================================================================
# TAB 3: Court & Authority Finder
# ==============================================================================
with tab_forums:
    st.header("🏛️ Pakistani Legal Authority & Forum Finder")
    st.write("Janain k aapke sheher me Consumer Court, Rent Tribunal, aur FIA Cyber Crime Reporting Center kahan waqay hain.")

    for f in advisor.forums:
        with st.expander(f"📌 {f.get('domain')} - {f.get('name_english')} ({f.get('name_urdu')})", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Presiding Official:** {f.get('presiding_officer')}")
                st.markdown(f"**Court Fee:** {f.get('court_fee')}")
                st.markdown(f"**Lawyer Required?** {f.get('lawyer_needed')}")
            with col_b:
                st.markdown(f"**Mandatory Prior Step:** {f.get('mandatory_step')}")
                if "helpline" in f:
                    st.markdown(f"**Helpline:** `{f.get('helpline')}`")
                if "online_portal" in f:
                    st.markdown(f"**Online Portal:** [{f.get('online_portal')}]({f.get('online_portal')})")

            if "address_info" in f:
                st.markdown("**City Locations:**")
                for c_name, c_addr in f["address_info"].items():
                    st.markdown(f"- **{c_name}**: {c_addr}")

# ==============================================================================
# TAB 4: Statutes & Judgments Library (ChromaDB Integrated)
# ==============================================================================
with tab_library:
    st.header("📚 Pakistani Legal Statutes & Judgments Directory")
    st.write("Browse the curated civic laws or search the complete vectorized corpus of **967 Federal Statutes** and **1,414 Supreme Court of Pakistan Judgments** (from `pk-eli-mcp`).")

    library_mode = st.radio(
        "Select Library View / کیٹیگری منتخب کریں:",
        ["📌 Curated Civic Laws (Urdu & Roman Urdu)", "🔍 ChromaDB Semantic Vector Search (All 967 Federal Statutes & 1,414 SC Judgments)"],
        horizontal=True
    )

    if library_mode.startswith("📌"):
        search_statute = st.text_input("Filter curated civic statutes by keyword (e.g. peca, 28, eviction, notice):")

        filtered_docs = advisor.retriever.documents
        if search_statute.strip():
            filtered_docs = [d for d in filtered_docs if search_statute.lower() in json.dumps(d).lower()]

        for doc in filtered_docs:
            with st.expander(f"📖 {doc.get('act')} — {doc.get('section')}"):
                st.markdown(f"<span class='badge-statute'>{doc.get('category')}</span> <span class='badge-forum'>{doc.get('jurisdiction')}</span>", unsafe_allow_html=True)
                st.markdown(f"**Limitation Period:** `{doc.get('limitation_period')}`")
                st.markdown(f"**Competent Forum:** `{doc.get('forum')}`")
                
                st.markdown("**English Legal Text:**")
                st.write(doc.get("content_english"))

                st.markdown("**Urdu (اردو):**")
                st.markdown(f"<div class='urdu-font'>{doc.get('content_urdu')}</div>", unsafe_allow_html=True)

                st.markdown("**Roman Urdu:**")
                st.write(doc.get("content_roman_urdu"))

    else:
        st.subheader("🔍 ChromaDB Semantic Legal Search")
        st.caption("Powered by vectorized embeddings over `AyeshaJadoon/Pakistan_Laws_Dataset` and `Ibtehaj10/supreme-court-of-pak-judgments`.")

        from query_chroma import PKLegalVectorStore
        vector_store = PKLegalVectorStore()

        stat_count = vector_store.statutes_col.count() if vector_store.statutes_col else 0
        jdg_count = vector_store.judgments_col.count() if vector_store.judgments_col else 0

        st.markdown(f"📊 **Vector Database Stats**: `{stat_count:,}` Federal Statute vectors | `{jdg_count:,}` Supreme Court Judgment vectors indexed.")

        col_search, col_filter = st.columns([3, 1])
        with col_search:
            v_query = st.text_input("Search query / قانونی سوال یا دفعہ تلاش کریں:", value="Pakistan Penal Code Section 302 murder punishment")
        with col_filter:
            v_filter = st.selectbox("Target Corpus:", ["All (Statutes + Judgments)", "Statutes Only", "Judgments Only"])

        if st.button("🔎 Search Vector Database", type="primary"):
            if not v_query.strip():
                st.warning("Please enter a search query.")
            else:
                with st.spinner("Searching ChromaDB vector collections..."):
                    if v_filter == "Statutes Only":
                        v_results = vector_store.search_statutes(v_query, top_k=6)
                    elif v_filter == "Judgments Only":
                        v_results = vector_store.search_judgments(v_query, top_k=6)
                    else:
                        v_results = vector_store.search_all(v_query, top_k=6)

                    if not v_results:
                        st.info("No matching vectors found. Database is indexing in background or query too generic.")
                    else:
                        st.success(f"Found {len(v_results)} relevant legal sections / judgments in ChromaDB:")
                        for idx, item in enumerate(v_results, 1):
                            title = item.get("title") or item.get("case_title", "Document")
                            dist = item.get("distance", 0.0)
                            doc_badge = "📖 Statute" if "title" in item else "⚖️ SC Judgment"

                            with st.expander(f"[{doc_badge}] {title} — (Relevance Distance: {dist})", expanded=(idx <= 2)):
                                st.write(item.get("text", ""))
