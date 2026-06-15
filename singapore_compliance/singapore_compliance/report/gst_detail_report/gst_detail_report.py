import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "transaction_type", "label": _("TRANSACTION TYPE"), "fieldtype": "Data", "width": 420},
		{"fieldname": "date", "label": _("DATE"), "fieldtype": "Date", "width": 100},
		{"fieldname": "name", "label": _("NO"), "fieldtype": "Data", "width": 180},
		{"fieldname": "party_name", "label": _("NAME"), "fieldtype": "Data", "width": 150},
		{"fieldname": "gst_code", "label": _("GST CODE"), "fieldtype": "Link", "options": "Account", "width": 100},
		{"fieldname": "gst_rate", "label": _("GST RATE"), "fieldtype": "Data", "width": 100},
		{"fieldname": "net_amount", "label": _("NET AMOUNT"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "amount", "label": _("AMOUNT"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "balance", "label": _("BALANCE"), "fieldtype": "Currency", "width": 100},
	]


def get_sgst_details(filters):
	return frappe.db.get_all(
		"SGST Detail",
		{"parent": "Singapore GST Settings", "company": filters.company},
		["box_1", "box_2", "box_3", "box_5", "box_5_1", "box_5_2", "box_5_3", "bank_interest_income", "realised_exchange_gainloss"],
	)


def get_journal_entry_data(sgst, filters):
	params = {
		"bank_interest": sgst.get("bank_interest_income"),
		"exchange_gain": sgst.get("realised_exchange_gainloss"),
	}
	conditions = (
		"jea.parent = je.name"
		" AND (jea.account = %(bank_interest)s OR jea.account = %(exchange_gain)s)"
		" AND je.docstatus = 1"
	)

	if filters.company:
		conditions += " AND je.company = %(company)s"
		params["company"] = filters.company
	if filters.get("from_date"):
		conditions += " AND DATE(je.posting_date) >= %(from_date)s"
		params["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions += " AND DATE(je.posting_date) <= %(to_date)s"
		params["to_date"] = filters.get("to_date")

	jv_data = frappe.db.sql(
		f"""
		SELECT
			je.posting_date AS date,
			'Journal Entry' AS transaction_type,
			je.name AS name,
			jea.account AS account,
			SUM(jea.debit_in_account_currency) AS debit,
			SUM(jea.credit_in_account_currency) AS credit
		FROM
			`tabJournal Entry` AS je
			LEFT JOIN `tabJournal Entry Account` AS jea ON jea.parent = je.name
		WHERE
			{conditions}
		GROUP BY jea.account, je.name
		""",
		params,
		as_dict=True,
	)

	total = 0
	for row in jv_data:
		row["amount"] = -row.get("credit") or row.get("debit")
		total += row.get("debit") - row.get("credit")

	return jv_data, total


def get_payment_entry_data(sgst, filters):
	params = {
		"bank_interest": sgst.get("bank_interest_income"),
		"exchange_gain": sgst.get("realised_exchange_gainloss"),
	}
	conditions = (
		"ped.parent = pe.name"
		" AND (ped.account = %(bank_interest)s OR ped.account = %(exchange_gain)s)"
		" AND pe.docstatus = 1"
	)

	if filters.company:
		conditions += " AND pe.company = %(company)s"
		params["company"] = filters.company
	if filters.get("from_date"):
		conditions += " AND DATE(pe.posting_date) >= %(from_date)s"
		params["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions += " AND DATE(pe.posting_date) <= %(to_date)s"
		params["to_date"] = filters.get("to_date")

	py_data = frappe.db.sql(
		f"""
		SELECT
			pe.posting_date AS date,
			'Payment Entry' AS transaction_type,
			pe.name AS name,
			pe.party_name AS party_name,
			ped.amount AS amount,
			ped.account AS account
		FROM
			`tabPayment Entry` AS pe
			LEFT JOIN `tabPayment Entry Deduction` AS ped ON ped.parent = pe.name
		WHERE
			{conditions}
		GROUP BY ped.account, pe.name
		""",
		params,
		as_dict=True,
	)

	total = sum(row.get("amount") or 0 for row in py_data)
	return py_data, total


def get_sales_invoice_data(filters):
	params = {}
	conditions = "st.parent = si.name AND si.docstatus = 1"

	if filters.company:
		conditions += " AND si.company = %(company)s"
		params["company"] = filters.company
	if filters.get("from_date"):
		conditions += " AND DATE(si.posting_date) >= %(from_date)s"
		params["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions += " AND DATE(si.posting_date) <= %(to_date)s"
		params["to_date"] = filters.get("to_date")

	return frappe.db.sql(
		f"""
		SELECT
			si.posting_date AS date,
			'Sales Invoice' AS transaction_type,
			si.name AS name,
			si.customer_name AS party_name,
			st.account_head AS gst_code,
			st.rate AS gst_rate,
			st.base_total AS net_amount,
			st.base_tax_amount AS amount,
			IF(st.included_in_print_rate, si.net_total, si.base_total) AS taxless_total
		FROM
			`tabSales Invoice` AS si,
			`tabSales Taxes and Charges` AS st
		WHERE
			{conditions}
		ORDER BY si.name
		""",
		params,
		as_dict=True,
	)


def get_purchase_invoice_data(sgst, filters):
	box_5_accounts = [
		acc for acc in [
			sgst.get("box_5"),
			sgst.get("box_5_1"),
			sgst.get("box_5_2"),
			sgst.get("box_5_3"),
		]
		if acc
	]

	if not box_5_accounts:
		return []

	placeholders = ", ".join(["%s"] * len(box_5_accounts))
	params = list(box_5_accounts)
	conditions = (
		f"pt.parent = p.name AND p.docstatus = 1"
		f" AND pt.parenttype = 'Purchase Invoice'"
		f" AND pt.account_head IN ({placeholders})"
	)

	if filters.company:
		conditions += " AND p.company = %s"
		params.append(filters.company)
	if filters.get("from_date"):
		conditions += " AND DATE(p.posting_date) >= %s"
		params.append(filters.get("from_date"))
	if filters.get("to_date"):
		conditions += " AND DATE(p.posting_date) <= %s"
		params.append(filters.get("to_date"))

	return frappe.db.sql(
		f"""
		SELECT
			p.posting_date AS date,
			'Purchase Invoice' AS transaction_type,
			p.name AS name,
			p.supplier_name AS party_name,
			pt.account_head AS gst_code,
			pt.rate AS gst_rate,
			pt.base_total AS net_amount,
			pt.base_tax_amount AS amount,
			IF(pt.included_in_print_rate, p.net_total, p.total) AS taxless_total
		FROM
			`tabPurchase Invoice` AS p,
			`tabPurchase Taxes and Charges` AS pt
		WHERE
			{conditions}
		ORDER BY p.name
		""",
		params,
		as_dict=True,
	)


def get_data(filters=None):
	sgst_details = get_sgst_details(filters)

	if not sgst_details or not (
		sgst_details[0].get("box_1")
		or sgst_details[0].get("box_2")
		or sgst_details[0].get("box_3")
		or sgst_details[0].get("bank_interest_income")
		or sgst_details[0].get("realised_exchange_gainloss")
	):
		return []

	sgst = sgst_details[0]

	jv_data, total_jv = get_journal_entry_data(sgst, filters)
	py_data, total_py = get_payment_entry_data(sgst, filters)
	sql_data = get_sales_invoice_data(filters)

	box_1 = [{"transaction_type": "Box 1 Total value of standard-rated supplies (excluding GST)", "heading": 1}]
	box_2 = [{"transaction_type": "Box 2 Total value of standard-rated supplies (excluding GST)", "heading": 1}]
	box_3 = [{"transaction_type": "Box 3 Total value of standard-rated supplies (excluding GST)", "heading": 1}]

	sales_invoice_with_tax = []
	sales_invoice_with_tax_total = 0
	box_1_total = box_2_total = box_3_total = 0
	box_1_balance = box_2_balance = box_3_balance = 0
	box_6_balance = 0
	total = 0

	for data in sql_data:
		if data.get("gst_code") in [sgst.get("box_1"), sgst.get("box_2"), sgst.get("box_3")]:
			sales_invoice_with_tax_total += data["amount"]
			box_6_balance += data.get("amount")
			data["balance"] = box_6_balance
			sales_invoice_with_tax.append(data)

		cp = data.copy()
		cp["gst_rate"] = 0
		cp["net_amount"] = 0
		cp["amount"] = cp["taxless_total"]

		if data.get("gst_code") == sgst.get("box_1"):
			total += cp.get("amount")
			box_1_total += cp.get("amount")
			box_1_balance += cp.get("amount")
			cp["balance"] = box_1_balance
			box_1.append(cp)
		elif data.get("gst_code") == sgst.get("box_2"):
			total += cp.get("amount")
			box_2_balance += cp.get("amount")
			cp["balance"] = box_2_balance
			box_2.append(cp)
			box_2_total += cp.get("amount")
		elif data.get("gst_code") == sgst.get("box_3"):
			total += cp.get("amount")
			box_3_balance += cp.get("amount")
			cp["balance"] = box_3_balance
			box_3.append(cp)
			box_3_total += cp.get("amount")

	if jv_data:
		box_3.extend(jv_data)
	if py_data:
		box_3.extend(py_data)
	box_3_total += total_jv + total_py

	out_data = (
		box_1
		+ [{"transaction_type": "<b>Box 1 Total value of standard-rated supplies (excluding GST)</b>", "heading": 1, "amount": box_1_total}]
		+ box_2
		+ [{"transaction_type": "<b>Box 2 Total value of standard-rated supplies (excluding GST)</b>", "heading": 1, "amount": box_2_total}]
		+ box_3
		+ [{"transaction_type": "<b>Box 3 Total value of standard-rated supplies (excluding GST)</b>", "heading": 1, "amount": box_3_total}]
		+ [{"transaction_type": "<b>Box 4 Total (Box 1, Box 2, Box 3)</b>", "heading": 1, "amount": total}]
	)

	p_sql_data = get_purchase_invoice_data(sgst, filters)
	purchase_row_without_gst = []
	purchase_invoice_with_tax = []
	purchase_invoice_with_tax_total = 0
	box_5_balance = box_7_balance = 0
	p_total = 0

	if p_sql_data:
		out_data.append({"transaction_type": "Box 5 Total value of taxable purchases (excluding GST)", "heading": 1})
		for data in p_sql_data:
			purchase_invoice_with_tax_total += data["amount"]
			box_7_balance += data.get("amount")
			data["balance"] = box_7_balance
			purchase_invoice_with_tax.append(data)

			cp = data.copy()
			cp["gst_rate"] = 0
			cp["net_amount"] = 0
			cp["amount"] = cp["taxless_total"]
			box_5_balance += cp.get("amount")
			cp["balance"] = box_5_balance
			purchase_row_without_gst.append(cp)
			p_total += cp.get("amount")

		out_data += purchase_row_without_gst + [
			{"transaction_type": "<b>Total for Box 5 Total value of taxable purchases (excluding GST)</b>", "heading": 1, "amount": p_total}
		]

	if sales_invoice_with_tax:
		out_data += (
			[{"transaction_type": "Box 6 Output tax due", "heading": 1}]
			+ sales_invoice_with_tax
			+ [{"transaction_type": "<b>Total for Box 6 Output tax due</b>", "heading": 1, "amount": sales_invoice_with_tax_total}]
		)

	if purchase_invoice_with_tax:
		out_data += (
			[{"transaction_type": "Box 7 Input tax and refunds claimed", "heading": 1}]
			+ purchase_invoice_with_tax
			+ [{"transaction_type": "<b>Total for Box 7 Input tax and refunds claimed</b>", "heading": 1, "amount": purchase_invoice_with_tax_total}]
		)

	if purchase_invoice_with_tax_total and sales_invoice_with_tax_total:
		diff = sales_invoice_with_tax_total - purchase_invoice_with_tax_total
		if diff > 0:
			label, amount = "<b>Box 8 Tax To Be Paid</b>", diff
		elif diff < 0:
			label, amount = "<b>Box 8 Tax To Be Claimed</b>", -diff
		else:
			label, amount = "<b>Box 8 Tax</b>", purchase_invoice_with_tax_total
		out_data.append({"transaction_type": label, "heading": 1, "amount": amount})

	return out_data
