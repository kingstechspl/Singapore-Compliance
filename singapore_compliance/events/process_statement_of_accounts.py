import json

import frappe
from erpnext import get_company_currency
from erpnext.accounts.party import get_party_account_currency
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
	execute as get_ageing,
)
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa
from frappe.utils import getdate, money_in_words


@frappe.whitelist()
def get_statements_of_account(name: str) -> dict:
	name = frappe.form_dict.name
	psoa_doc = frappe.get_doc("Process Statement Of Accounts", name)
	out_data = {}
	out_list = []
	for cust in psoa_doc.customers:
		cust_dict = {}
		presentation_currency = (
			get_party_account_currency("Customer", cust.customer, psoa_doc.company)
			or psoa_doc.currency
			or get_company_currency(psoa_doc.company)
		)
		tax_id = frappe.get_doc("Customer", cust.customer).tax_id
		filters = frappe._dict(
			{
				"from_date": psoa_doc.from_date,
				"to_date": psoa_doc.to_date,
				"company": psoa_doc.company,
				"finance_book": psoa_doc.finance_book if psoa_doc.finance_book else None,
				"account": [psoa_doc.account] if psoa_doc.account else None,
				"party_type": "Customer",
				"party": [cust.customer],
				"presentation_currency": presentation_currency,
				"currency": psoa_doc.currency,
				"cost_center": [cc.cost_center_name for cc in psoa_doc.cost_center],
				"project": [p.project_name for p in psoa_doc.project],
				"show_opening_entries": 0,
				"include_default_book_entries": 0,
				"tax_id": tax_id if tax_id else None,
			}
		)
		col, res = get_soa(filters)

		for x in [0, -2, -1]:
			res[x]["account"] = res[x]["account"].replace("'", "")

		if len(res) == 3:
			continue

		if res:
			for re in res:
				if re.get("voucher_type") and re.get("voucher_type") == "Sales Invoice":
					sales_invoice = frappe.db.get_value(
						re.get("voucher_type"),
						re.get("voucher_no"),
						["due_date", "po_no", "total"],
						as_dict=1,
					)
					if sales_invoice.get("due_date"):
						re["due_date"] = (
							sales_invoice.get("due_date") if sales_invoice.get("due_date") else ""
						)
					if sales_invoice.get("po_no"):
						re["po_no"] = sales_invoice.get("po_no") if sales_invoice.get("po_no") else ""
					if sales_invoice.get("total"):
						re["total"] = sales_invoice.get("total") if sales_invoice.get("total") else 0
			cust_dict["data"] = res

		cad_query = """
			SELECT
				ad.name,
				ad.address_line1,
				ad.address_line2,
				ad.city,
				ad.email_id,
				ad.phone,
				ad.pincode,
				ad.country,
				cus.name as customer,
				cus.customer_name as customer_name,
				cus.payment_terms
			FROM
				tabAddress AS ad 
			LEFT JOIN `tabDynamic Link` AS dl ON dl.parent = ad.name 
			LEFT JOIN tabCustomer AS cus ON dl.link_name = cus.name
			WHERE
				dl.link_doctype = "Customer" 
				AND dl.link_name = %s
		"""
		cad_data = frappe.db.sql(cad_query, cust.get("customer"), as_dict=True)
		if cad_data and cad_data[0]:
			cust_dict["cad_data"] = cad_data[0]
		cco_query = """
			SELECT
				co.first_name,
				co.middle_name,
				co.last_name
			FROM
				tabContact AS co 
			LEFT JOIN `tabDynamic Link` AS dl ON dl.parent = co.name
			WHERE
				dl.link_doctype = "Customer" 
				AND dl.link_name = %s
				AND co.is_primary_contact = 1
		"""
		cco_data = frappe.db.sql(cco_query, cust.get("customer"), as_dict=True)
		if cco_data and cco_data[0]:
			cust_dict["cco_data"] = cco_data[0]
		if psoa_doc.include_ageing:
			ageing_filters = frappe._dict(
				{
					"company": psoa_doc.company,
					"report_date": psoa_doc.to_date,
					"ageing_based_on": psoa_doc.ageing_based_on,
					"range1": 30,
					"range2": 60,
					"range3": 90,
					"range4": 120,
					"customer": cust.customer,
				}
			)
			col1, ageing = get_ageing(ageing_filters)
			if ageing:
				ageing[0]["ageing_based_on"] = psoa_doc.ageing_based_on
				cust_dict["ageing"] = ageing[0]
			out_list.append(cust_dict)
	out_data["cust"] = out_list
	out_data["currency"] = psoa_doc.currency
	out_data["to_date"] = frappe.utils.formatdate(psoa_doc.to_date, "dd MMM YYYY")
	out_data["posting_date"] = frappe.utils.formatdate(getdate(), "dd MMM YYYY")
	cod_query = """
		SELECT
			ad.name,
			ad.address_line1,
			ad.address_line2,
			ad.city,
			ad.email_id,
			ad.phone,
			ad.pincode,
			ad.fax,
			ad.country
		FROM
			tabAddress AS ad 
		LEFT JOIN `tabDynamic Link` AS dl ON dl.parent = ad.name
		WHERE
			dl.link_doctype = "Company" 
			AND dl.link_name = %s
	"""
	cod_data = frappe.db.sql(cod_query, psoa_doc.get("company"), as_dict=True)
	if cod_data and cod_data[0]:
		out_data["cod_data"] = cod_data[0]
	out_data["tax_id"] = frappe.db.get_value("Company", psoa_doc.company, "tax_id")
	if len(out_data["cust"]):
		out_data["cust"][0]["ageing"]["outstanding_in_words"] = money_in_words(
			abs(out_data["cust"][0]["ageing"]["outstanding"])
		)
		out_data["cust"][0]["ageing"]["current_due"] = (
			out_data["cust"][0]["ageing"]["outstanding"]
			- out_data["cust"][0]["ageing"]["range1"]
			- out_data["cust"][0]["ageing"]["range2"]
			- out_data["cust"][0]["ageing"]["range3"]
			- out_data["cust"][0]["ageing"]["range4"]
			- out_data["cust"][0]["ageing"]["range5"]
		)

	return out_data
