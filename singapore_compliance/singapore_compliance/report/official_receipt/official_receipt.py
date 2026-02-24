# Copyright (c) 2024, earthians and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import formatdate
from typing import Dict, Any


def execute(filters=None):
	columns, data = [], []

	data = get_data(filters)

	columns = [
		{
			"fieldname": "name",
			"label": _("Payment Entry"),
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 150,
		},
		{
			"fieldname": "party_type",
			"label": _("Party Type"),
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 150,
		},
		{
			"fieldname": "party",
			"label": _("Party"),
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 150,
		},
		{
			"fieldname": "reference_doctype",
			"label": _("Reference Doctype"),
			"fieldtype": "Link",
			"options": "Doctype",
			"width": 150,
		},
		{
			"fieldname": "reference_name",
			"label": _("Reference Name"),
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 150,
		},
		{"fieldname": "total_amount", "label": _("Total Amount"), "fieldtype": "Float", "width": 150},
		{"fieldname": "allocated_amount", "label": _("Allocated Amount"), "fieldtype": "Float", "width": 150},
		{
			"fieldname": "outstanding_amount",
			"label": _("Outstanding Amount"),
			"fieldtype": "Float",
			"width": 150,
		},
	]

	return columns, data


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("company"):
		conditions.append("pe.company = %(company)s")
		values["company"] = filters.get("company")
	if filters.get("payment_entry"):
		conditions.append("pe.name = %(payment_entry)s")
		values["payment_entry"] = filters.get("payment_entry")
	if filters.get("party_type"):
		conditions.append("pe.party_type = %(party_type)s")
		values["party_type"] = filters.get("party_type")
	if filters.get("party"):
		conditions.append("pe.party IN %(party)s")
		values["party"] = tuple(filters.get("party"))

	condition_sql = ""
	if conditions:
		condition_sql = " AND " + " AND ".join(conditions)

	query = """
		Select pe.name, 
			pe.party_type, 
			pe.party, 
			ref.reference_doctype, 
			ref.reference_name, 
			ref.total_amount, 
			ref.outstanding_amount, 
			ref.allocated_amount
		From 
			`tabPayment Entry` as pe
		Left join 
			`tabPayment Entry Reference` as ref ON pe.name = ref.parent
		where pe.docstatus = 1 
	""" + condition_sql
	
	data = frappe.db.sql(query, values, as_dict=1)

	return data


@frappe.whitelist()
def get_print_data(customer: str, from_date: str, to_date: str, company: str) -> Dict[str, Any]:
	result: Dict[str, Any] = {}

	values = {
		"customer": customer,
		"from_date": from_date,
		"to_date": to_date,
		"company": company,
	}

	data = frappe.db.sql(
		"""
			Select pe.name, 
				pe.party_type, 
				pe.party, 
				ref.reference_doctype,
				ref.reference_name, 
				ref.total_amount, 
				ref.outstanding_amount,
				ref.allocated_amount, 
				pe.posting_date,
				pe.paid_from_account_currency
			From 
				`tabPayment Entry` as pe
			Left join 
				`tabPayment Entry Reference` as ref ON pe.name = ref.parent
			Where 
				pe.docstatus = 1
				AND pe.company = %(company)s
				AND pe.party = %(customer)s
				AND pe.posting_date >= %(from_date)s
				AND pe.posting_date <= %(to_date)s
		""",
		values,
		as_dict=1,
	)

	for row in data:
		row.update({"posting_date": formatdate(row.posting_date, "dd MMM YYYY")})

	address = frappe.db.sql(
		"""
		Select 
			ad.name as title, 
			ad.address_line1, 
			ad.address_line2, 
			ad.city, 
			ad.country, 
			ad.pincode, 
			dl.link_name as party
		From 
			`tabAddress` as ad
		Left join 
			`tabDynamic Link` as  dl ON dl.parent = ad.name
		Where 
			ad.address_type = "Billing" 
			AND dl.link_name = %(customer)s
		""",
		{"customer": customer},
		as_dict=1,
	)
	if not data:
		frappe.throw(_("Transactions are not available"))
	result["data"] = data
	result["address"] = address[0]
	result["currency"] = data[0].paid_from_account_currency
	result["payment_terms"] = _("C.O.D")

	return result
