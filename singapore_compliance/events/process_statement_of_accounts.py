import json

import frappe
from weasyprint import HTML as WeasyprintHTML
from erpnext import get_company_currency
from erpnext.accounts.party import get_party_account_currency
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
	execute as get_ageing,
)
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa
from frappe.utils import getdate, money_in_words, today as frappe_today


@frappe.whitelist(allow_guest=False)
def soa_to_pdf(html: str, orientation: str = "Portrait"):
	pdf_bytes = WeasyprintHTML(string=html).write_pdf(
		presentational_hints=True,
		optimize_images=True,
	)
	frappe.local.response.filename = "statement_of_account.pdf"
	frappe.local.response.filecontent = pdf_bytes
	frappe.local.response.type = "pdf"


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
						["due_date", "po_no", "total", "custom_doc_title"],
						as_dict=1,
					)
					if sales_invoice.get("due_date"):
						re["due_date"] = (
							sales_invoice.get("due_date") if sales_invoice.get("due_date") else ""
						)
					if sales_invoice.get("po_no"):
						re["po_no"] = sales_invoice.get("po_no") if sales_invoice.get("po_no") else ""
					if sales_invoice.get("custom_doc_title"):
						re["doc_title"] = sales_invoice.get("custom_doc_title") if sales_invoice.get("custom_doc_title") else ""
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
			frappe.log_error(title="ageing", message=ageing)
			if ageing:
				matching = next(
					(a for a in ageing if a.get("party") == cust.customer), None
				)
				if matching:
					matching["ageing_based_on"] = psoa_doc.ageing_based_on
					cust_dict["ageing"] = matching
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
	for cust_entry in out_data["cust"]:
		if cust_entry.get("ageing"):
			ageing = cust_entry["ageing"]
			ageing["outstanding_in_words"] = money_in_words(abs(ageing.get("outstanding") or 0))
			ageing["current_due"] = (
				(ageing.get("outstanding") or 0)
				- (ageing.get("range1") or 0)
				- (ageing.get("range2") or 0)
				- (ageing.get("range3") or 0)
				- (ageing.get("range4") or 0)
				- (ageing.get("range5") or 0)
			)
	frappe.log_error(title="output", message=out_data)
	return out_data


@frappe.whitelist()
def get_customer_soa(customer: str) -> dict:
	"""Generate SOA data for a single customer up to today, used by the Customer form button."""
	from erpnext.accounts.utils import get_fiscal_year

	company = frappe.defaults.get_global_default("company")
	today_date = getdate(frappe_today())

	try:
		fy = get_fiscal_year(today_date, company=company)
		from_date = fy[1]
	except Exception:
		from_date = frappe.utils.add_months(today_date, -12)

	presentation_currency = (
		get_party_account_currency("Customer", customer, company)
		or get_company_currency(company)
	)
	tax_id = frappe.get_doc("Customer", customer).tax_id

	filters = frappe._dict({
		"from_date": str(from_date),
		"to_date": str(today_date),
		"company": company,
		"finance_book": None,
		"account": None,
		"party_type": "Customer",
		"party": [customer],
		"presentation_currency": presentation_currency,
		"currency": presentation_currency,
		"cost_center": [],
		"project": [],
		"show_opening_entries": 0,
		"include_default_book_entries": 0,
		"tax_id": tax_id if tax_id else None,
	})

	col, res = get_soa(filters)

	for x in [0, -2, -1]:
		res[x]["account"] = res[x]["account"].replace("'", "")

	if len(res) == 3:
		return {"error": "No transactions found for this customer."}

	for row in res:
		if row.get("voucher_type") == "Sales Invoice":
			si = frappe.db.get_value(
				row["voucher_type"],
				row["voucher_no"],
				["due_date", "po_no", "total"],
				as_dict=1,
			)
			if si:
				row["due_date"] = si.get("due_date") or ""
				row["po_no"] = si.get("po_no") or ""
				row["total"] = si.get("total") or 0

	cad_query = """
		SELECT ad.name, ad.address_line1, ad.address_line2, ad.city,
			ad.email_id, ad.phone, ad.pincode, ad.country,
			cus.name as customer, cus.customer_name as customer_name, cus.payment_terms
		FROM tabAddress AS ad
		LEFT JOIN `tabDynamic Link` AS dl ON dl.parent = ad.name
		LEFT JOIN tabCustomer AS cus ON dl.link_name = cus.name
		WHERE dl.link_doctype = 'Customer' AND dl.link_name = %s
	"""
	cad_data = frappe.db.sql(cad_query, customer, as_dict=True)

	ageing_filters = frappe._dict({
		"company": company,
		"report_date": str(today_date),
		"ageing_based_on": "Due Date",
		"range1": 30,
		"range2": 60,
		"range3": 90,
		"range4": 120,
		"customer": customer,
	})
	col1, ageing_rows = get_ageing(ageing_filters)
	matching = next((a for a in ageing_rows if a.get("party") == customer), None)

	if matching:
		matching["ageing_based_on"] = "Due Date"
		matching["outstanding_in_words"] = money_in_words(abs(matching.get("outstanding") or 0))
		matching["current_due"] = (
			(matching.get("outstanding") or 0)
			- (matching.get("range1") or 0)
			- (matching.get("range2") or 0)
			- (matching.get("range3") or 0)
			- (matching.get("range4") or 0)
			- (matching.get("range5") or 0)
		)

	out = {
		"cust": [{
			"data": res,
			"cad_data": cad_data[0] if cad_data else {"customer_name": customer},
			"ageing": matching or {},
		}],
		"currency": presentation_currency,
		"posting_date": frappe.utils.formatdate(frappe_today(), "dd MMM YYYY"),
		"to_date": frappe.utils.formatdate(today_date, "dd MMM YYYY"),
	}
	return out
