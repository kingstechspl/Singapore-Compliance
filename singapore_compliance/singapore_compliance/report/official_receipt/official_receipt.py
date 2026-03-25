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
    conditions = []
    params = {}

    if filters.get("company"):
        conditions.append("pe.company = %(company)s")
        params["company"] = filters.get("company")

    if filters.get("payment_entry"):
        conditions.append("pe.name = %(payment_entry)s")
        params["payment_entry"] = filters.get("payment_entry")

    if filters.get("party_type"):
        conditions.append("pe.party_type = %(party_type)s")
        params["party_type"] = filters.get("party_type")

    if filters.get("party"):
        conditions.append("pe.party IN %(party_list)s")
        params["party_list"] = tuple(filters.get("party")) 

    where_clause = ""
    if conditions:
        where_clause = " AND " + " AND ".join(conditions)

    query = (
        "SELECT pe.name, pe.party_type, pe.party, "
        "ref.reference_doctype, ref.reference_name, "
        "ref.total_amount, ref.outstanding_amount, ref.allocated_amount "
        "FROM `tabPayment Entry` AS pe "
        "LEFT JOIN `tabPayment Entry Reference` AS ref ON pe.name = ref.parent "
        "WHERE pe.docstatus = 1" + where_clause
    )

    data = frappe.db.sql(query, params, as_dict=1)
    return data


@frappe.whitelist()
def get_print_data(customer: str, from_date: str, to_date: str, company: str) -> dict:
    result = {}

    query = (
        "SELECT pe.name, pe.party_type, pe.party, ref.reference_doctype, "
        "ref.reference_name, ref.total_amount, ref.outstanding_amount, "
        "ref.allocated_amount, pe.posting_date, pe.paid_from_account_currency "
        "FROM `tabPayment Entry` AS pe "
        "LEFT JOIN `tabPayment Entry Reference` AS ref ON pe.name = ref.parent "
        "WHERE pe.docstatus = 1 "
        "AND pe.company = %(company)s "
        "AND pe.party = %(customer)s "
        "AND pe.posting_date >= %(from_date)s "
        "AND pe.posting_date <= %(to_date)s"
    )

    params = {
        "company": company,
        "customer": customer,
        "from_date": from_date,
        "to_date": to_date,
    }

    data = frappe.db.sql(query, params, as_dict=1)

    for row in data:
        row["posting_date"] = formatdate(row["posting_date"], "dd MMM YYYY")

    address_query = (
        "SELECT ad.name AS title, ad.address_line1, ad.address_line2, ad.city, "
        "ad.country, ad.pincode, dl.link_name AS party "
        "FROM `tabAddress` AS ad "
        "LEFT JOIN `tabDynamic Link` AS dl ON dl.parent = ad.name "
        "WHERE ad.address_type = 'Billing' AND dl.link_name = %(customer)s"
    )
    address = frappe.db.sql(address_query, {"customer": customer}, as_dict=1)

    if not data:
        frappe.throw(_("Transactions are not available"))

    result["data"] = data
    result["address"] = address[0] if address else {}
    result["currency"] = data[0]["paid_from_account_currency"] if data else None
    result["payment_terms"] = "C.O.D"

    return result
