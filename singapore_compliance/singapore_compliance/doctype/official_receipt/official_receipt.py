# Copyright (c) 2025, Kingstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OfficialReceipt(Document):
	pass


@frappe.whitelist()
def get_company_logo(company):
	return frappe.db.get_value("Company", company, "company_logo")