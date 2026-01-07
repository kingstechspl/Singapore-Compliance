# Copyright (c) 2024, earthians and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import formatdate


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
	condition = ""
	if filters.get("company"):
		condition += f" and pe.company = '{filters.get('company')}'"
	if filters.get("payment_entry"):
		condition += f" and pe.name = '{filters.get('payment_entry')}'"
	if filters.get("party_type"):
		condition += f" and pe.party_type = '{filters.get('party_type')}'"
	if filters.get("party"):
		condition += " and pe.party in {} ".format(
			"(" + ", ".join([f'"{l}"' for l in filters.get("party")]) + ")"
		)

	data = frappe.db.sql(
		f"""
			Select pe.name, pe.party_type, pe.party, ref.reference_doctype, ref.reference_name, ref.total_amount, ref.outstanding_amount, ref.allocated_amount
			From `tabPayment Entry` as pe
			Left join `tabPayment Entry Reference` as ref ON pe.name = ref.parent
			where pe.docstatus = 1  {condition}
	""",
		as_dict=1,
	)

	return data


@frappe.whitelist()
def get_print_data(customer, from_date, to_date, company):
	result = {}

	condition = ""
	condition += f" and pe.company = '{company}'"
	condition += f" and pe.party = '{customer}'"
	condition += f" and pe.posting_date >= '{from_date}'"
	condition += f" and pe.posting_date <= '{to_date}'"

	data = frappe.db.sql(
		f"""
			Select pe.name, pe.party_type, pe.party, ref.reference_doctype,
			ref.reference_name, ref.total_amount, ref.outstanding_amount,
			ref.allocated_amount, pe.posting_date,
			pe.paid_from_account_currency
			From `tabPayment Entry` as pe
			Left join `tabPayment Entry Reference` as ref ON pe.name = ref.parent
			where pe.docstatus = 1  {condition}
	""",
		as_dict=1,
	)

	for row in data:
		row.update({"posting_date": formatdate(row.posting_date, "dd MMM YYYY")})

	address = frappe.db.sql(
		f"""
		Select ad.name as title, ad.address_line1, ad.address_line2, ad.city, ad.country, ad.pincode, dl.link_name as party
		From `tabAddress` as ad
		Left join `tabDynamic Link` as  dl ON dl.parent = ad.name
		Where ad.address_type = "Billing" and dl.link_name = '{customer}'
	""",
		as_dict=1,
	)
	if not data:
		frappe.throw("Transaction are not available")
	result["data"] = data
	result["address"] = address[0]
	result["currency"] = data[0].paid_from_account_currency
	result["payment_terms"] = "C.O.D"

	return result
