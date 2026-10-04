import os
from datetime import datetime
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader

class NoticeGenerator:
    """
    Renders statutory legal notices and formal complaints under Pakistani law.
    """

    TEMPLATES = {
        "consumer_notice": "consumer_notice.j2",
        "tenancy_notice": "tenancy_deposit_notice.j2",
        "fia_complaint": "fia_cybercrime_complaint.j2",
        "unpaid_wages": "unpaid_wages_notice.j2"
    }

    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.templates_dir = templates_dir
        self.env = Environment(loader=FileSystemLoader(self.templates_dir), autoescape=True)

    def render_notice(self, template_key: str, data: Dict[str, Any]) -> str:
        """
        Renders the legal notice template with the provided case data.
        """
        if template_key not in self.TEMPLATES:
            raise ValueError(f"Unknown template key: {template_key}. Available: {list(self.TEMPLATES.keys())}")

        template_file = self.TEMPLATES[template_key]
        template = self.env.get_template(template_file)

        # Set default date if missing
        if "date" not in data or not data["date"]:
            data["date"] = datetime.now().strftime("%d %B, %Y")

        rendered_text = template.render(**data)
        return rendered_text

    def get_template_metadata(self, template_key: str) -> Dict[str, Any]:
        meta = {
            "consumer_notice": {
                "title_en": "15-Day Consumer Pre-Suit Legal Notice",
                "title_ur": "15 روزہ صارف قانونی نوٹس (کنزیومر کورٹ)",
                "governing_law": "Punjab/Sindh Consumer Protection Act (Section 28)",
                "target_forum": "District Consumer Court",
                "cure_period": "15 Days"
            },
            "tenancy_notice": {
                "title_en": "Tenancy Advance / Security Refund Demand Notice",
                "title_ur": "کرایہ سیکیورٹی ڈپازٹ واپسی نوٹس",
                "governing_law": "Punjab Rented Premises Act 2009 (Section 10)",
                "target_forum": "Rent Tribunal / Special Judge Rent",
                "cure_period": "7 Days"
            },
            "fia_complaint": {
                "title_en": "FIA Cyber Crime Wing Formal Complaint Application",
                "title_ur": "ایف آئی اے سائبر کرائم باضابطہ شکایت درخواست",
                "governing_law": "Prevention of Electronic Crimes Act (PECA) 2016",
                "target_forum": "FIA Cyber Crime Reporting Center (NR3C)",
                "cure_period": "Immediate"
            },
            "unpaid_wages": {
                "title_en": "Notice for Recovery of Unpaid Wages & Settlement",
                "title_ur": "رکی ہوئی تنخواہ اور بقایاجات کا قانونی نوٹس",
                "governing_law": "Payment of Wages Act 1936 (Section 15)",
                "target_forum": "Authority under Payment of Wages Act / Labour Court",
                "cure_period": "7 Days"
            }
        }
        return meta.get(template_key, {})
