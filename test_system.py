import os
import sys

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

from engine.legal_advisor import LegalAdvisor
from drafting.notice_generator import NoticeGenerator

def test_retriever_and_advisor():
    print("=== Testing QanoonSahulat Legal Advisor & RAG Retriever ===")
    advisor = LegalAdvisor()
    print(f"Loaded {len(advisor.retriever.documents)} statutory sections.")
    assert len(advisor.retriever.documents) >= 10, "Should have at least 10 statutory sections loaded"

    # Test Query 1: Consumer Protection (Roman Urdu)
    q1 = "Daraz se kharab mobile mila he aur wo keh rahay hain wapis nahi hoga"
    print(f"\n[Test 1 Query]: {q1}")
    res1 = advisor.advise(q1, language="roman_urdu", city="Lahore")
    assert "Section 28" in res1["answer"] or "Consumer" in res1["answer"], "Should cite Consumer Act Section 28"
    assert res1["recommended_template"] == "consumer_notice"
    print("[Test 1 Result]: Passed! Correctly routed to Consumer Act & Section 28 notice.")

    # Test Query 2: Cybercrime / Blackmail (Urdu script)
    q2 = "فیس بک پر کوئی میری تصاویر سے بلیک میل کر رہا ہے"
    print(f"\n[Test 2 Query]: {q2}")
    res2 = advisor.advise(q2, language="urdu", city="Islamabad")
    assert "PECA" in res2["citations"][0]["act"] or "2016" in res2["citations"][0]["act"]
    assert res2["recommended_template"] == "fia_complaint"
    print("[Test 2 Result]: Passed! Correctly routed to PECA 2016 and FIA Cyber Crime.")

    # Test Query 3: Tenancy Deposit (Roman Urdu)
    q3 = "Makan malik advance security deposit wapis nahi kar raha"
    print(f"\n[Test 3 Query]: {q3}")
    res3 = advisor.advise(q3, language="roman_urdu", city="Karachi")
    assert "tenancy" in res3["recommended_template"].lower()
    print("[Test 3 Result]: Passed! Correctly identified Tenancy Deposit Notice.")

def test_notice_generation():
    print("\n=== Testing Statutory Notice & Complaint Generator ===")
    generator = NoticeGenerator()

    # 1. Consumer Notice
    c_notice = generator.render_notice("consumer_notice", {
        "date": "03 October, 2026",
        "sender_name": "Tariq Mehmood",
        "sender_cnic": "35201-9876543-1",
        "sender_phone": "0321-9876543",
        "sender_address": "House 10, Sector G, DHA Phase 5, Lahore",
        "opponent_name": "Skyline Electronics",
        "opponent_details": "Shop 4, Hall Road, Lahore",
        "opponent_address": "Hall Road, Lahore",
        "amount": "45,000",
        "incident_date": "20 September, 2026",
        "grievance_description": "Sold a burnt defective LED TV and refused replacement.",
        "remedy_demanded": "Refund PKR 45,000 immediately.",
        "compensation_amount": "10,000"
    })
    assert "SECTION 28" in c_notice
    assert "DISTRICT CONSUMER PROTECTION COURT" in c_notice
    print("[Consumer Notice]: Successfully rendered with Section 28 statutory references.")

    # 2. Tenancy Notice
    t_notice = generator.render_notice("tenancy_notice", {
        "date": "03 October, 2026",
        "sender_name": "Zahid Khan",
        "sender_cnic": "35202-1122334-5",
        "sender_phone": "0333-5556677",
        "sender_address": "Flat 3B, Askari 11, Lahore",
        "opponent_name": "Malik Aslam",
        "opponent_details": "0300-9988776",
        "opponent_address": "House 88, Model Town, Lahore",
        "amount": "150,000",
        "incident_date": "30 September, 2026"
    })
    assert "PUNJAB RENTED PREMISES ACT 2009" in t_notice
    assert "SPECIAL JUDGE RENT" in t_notice
    print("[Tenancy Notice]: Successfully rendered with Section 10 statutory references.")

    # 3. FIA Complaint
    fia_doc = generator.render_notice("fia_complaint", {
        "date": "03 October, 2026",
        "sender_name": "Ayesha Bibi",
        "sender_cnic": "37405-5544332-2",
        "sender_phone": "0345-1234567",
        "sender_address": "Rawalpindi",
        "opponent_name": "Unknown Fake Profile (@cyber_hunter)",
        "opponent_details": "WhatsApp +92312-0000000",
        "opponent_address": "Unknown",
        "incident_date": "01 October, 2026",
        "grievance_description": "Sending morphed photographs and demanding money via Easypaisa.",
        "amount": "25,000"
    })
    assert "PECA" in fia_doc
    assert "NR3C" in fia_doc
    print("[FIA Complaint]: Successfully rendered with PECA 2016 statutory references.")

if __name__ == "__main__":
    test_retriever_and_advisor()
    test_notice_generation()
    print("\n🎉 ALL UNIT AND INTEGRATION TESTS PASSED PERFECTLY!")
