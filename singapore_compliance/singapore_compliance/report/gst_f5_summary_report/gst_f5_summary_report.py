import frappe
from erpnext.accounts.report.financial_statements import get_data as financial_state_data
from erpnext.accounts.report.financial_statements import get_period_list
from frappe import _


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters=None):
	columns = [
		{"fieldname": "transaction_type", "label": _("Transaction Type"), "fieldtype": "Data", "width": 1000},
		{"fieldname": "amount", "label": _("AMOUNT"), "fieldtype": "Currency", "width": 200},
	]
	return columns


def get_data(filters=None):
	out_data = []
	acc_diff = 0
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	sgst_details = frappe.db.get_all(
		"SGST Detail",
		{"parent": "Singapore GST Settings", "company": filters.company},
		[
			"box_1",
			"box_2",
			"box_3",
			"box_5",
			"bank_interest_income",
			"realised_exchange_gainloss",
			"other_income",
		],
	)
	acc_diff = get_account_data(filters, sgst_details)
	if sgst_details and (
		sgst_details[0].get("box_1")
		or sgst_details[0].get("box_2")
		or sgst_details[0].get("box_3")
		or sgst_details[0].get("bank_interest_income")
		or sgst_details[0].get("realised_exchange_gainloss")
	):
		jv_query = """
			SELECT
				je.name AS name,
				jea.account AS account,
				sum(jea.debit_in_account_currency) AS debit,
				sum(jea.credit_in_account_currency) AS credit
			FROM
				`tabJournal Entry` AS je 
			LEFT JOIN
				`tabJournal Entry Account` AS jea on jea.parent=je.name
			WHERE
				je.docstatus=1
				AND (jea.account = %(bank_interest)s OR jea.account = %(exchange_gain)s)
			"""
		
		params = {
			"bank_interest": sgst_details[0].get("bank_interest_income"),
			"exchange_gain": sgst_details[0].get("realised_exchange_gainloss"),
		}
		
		if filters.company:
			jv_query += " AND je.company = %(company)s"
			params["company"] = filters.company

		if filters.from_date:
			jv_query += " AND DATE(je.posting_date) >= %(from_date)s"
			params["from_date"] = filters.from_date

		if filters.to_date:
			jv_query += " AND DATE(je.posting_date) <= %(to_date)s"
			params["to_date"] = filters.to_date

		jv_query += " GROUP BY jea.account, je.name"
		jv_data = frappe.db.sql(jv_query, params, as_dict=True)
		total_jv = 0
		for data in jv_data:
			data["amount"] = data.get("debit") or data.get("credit")
			k = data.get("debit") - data.get("credit")
			total_jv = total_jv + k
		py_query = """
			SELECT
				pe.name AS name,
				pe.party_name AS party_name,
				ped.amount AS amount,
				ped.account AS account

			FROM
				`tabPayment Entry` AS pe 
			LEFT JOIN
				`tabPayment Entry Deduction` AS ped on ped.parent=pe.name

			WHERE
				ped.parent=pe.name 
				AND (ped.account = %(bank_interest)s OR ped.account = %(exchange_gain)s)
				AND pe.docstatus = 1
			"""
		
		params = {
			"bank_interest": sgst_details[0].get("bank_interest_income"),
			"exchange_gain": sgst_details[0].get("realised_exchange_gainloss"),
		}
		
		if filters.company:
			py_query += " AND pe.company = %(company)s"
			params["company"] = filters.company

		if filters.from_date:
			py_query += " AND DATE(pe.posting_date) >= %(from_date)s"
			params["from_date"] = filters.from_date

		if filters.to_date:
			py_query += " AND DATE(pe.posting_date) <= %(to_date)s"
			params["to_date"] = filters.to_date

		py_query += " GROUP BY ped.account, pe.name"
		py_data = frappe.db.sql(py_query, params, as_dict=True)
		total_py = 0
		for data in py_data:
			k = data.get("amount")
			total_py = total_py + k
		query = """
		SELECT
			st.account_head AS gst_code,
			st.base_tax_amount as amount,
			IF(st.included_in_print_rate, si.net_total, si.base_total) as taxless_total
		FROM
			`tabSales Invoice` AS si,
			`tabSales Taxes and Charges` AS st
		WHERE
			st.parent=si.name AND si.docstatus = 1 AND st.parenttype = "Sales Invoice"
			"""
		
		params = {}

		if filters.company:
			query += " AND si.company = %(company)s"
			params["company"] = filters.company

		if filters.from_date:
			query += " AND DATE(si.posting_date) >= %(from_date)s"
			params["from_date"] = filters.from_date
		if filters.to_date:
			query += " AND DATE(si.posting_date) <= %(to_date)s"
			params["to_date"] = filters.to_date

		sql_data = frappe.db.sql(query, params, as_dict=True)
		out_data = []
		sales_invoice_with_tax = []
		sales_invoice_with_tax_total = 0
		box_1_total = 0
		box_2_total = 0
		box_3_total = 0
		total = 0
		if sql_data:
			cp_sqldata = sql_data.copy()
			for data in cp_sqldata:
				if data.get("gst_code") in [
					sgst_details[0].get("box_1"),
					sgst_details[0].get("box_2"),
					sgst_details[0].get("box_3"),
				]:
					sales_invoice_with_tax_total = sales_invoice_with_tax_total + data["amount"]
					sales_invoice_with_tax.append(data)
				cp_dict = data.copy()
				cp_dict["amount"] = cp_dict["taxless_total"]
				if data.get("gst_code") == sgst_details[0].get("box_1"):
					total = total + cp_dict.get("amount")
					box_1_total = box_1_total + cp_dict.get("amount")
				elif data.get("gst_code") == sgst_details[0].get("box_2"):
					total = total + cp_dict.get("amount")
					box_2_total = box_2_total + cp_dict.get("amount")
				elif data.get("gst_code") == sgst_details[0].get("box_3"):
					total = total + cp_dict.get("amount")
					box_3_total = box_3_total + cp_dict.get("amount")
		box_1_total_line = [
			{
				"transaction_type": "Box 1 Total value of standard-rated supplies (excluding GST)",
				"heading": 1,
				"amount": box_1_total,
			}
		]
		box_2_total_line = [
			{
				"transaction_type": "Box 2 Total value of standard-rated supplies (excluding GST)",
				"heading": 1,
				"amount": box_2_total,
			}
		]
		box_3_total_line = [
			{
				"transaction_type": "Box 3 Total value of standard-rated supplies (excluding GST)",
				"heading": 1,
				"amount": abs(box_3_total + total_jv + total_py),
			}
		]
		total = total + abs(total_jv) + abs(total_py)
		out_data = box_1_total_line + box_2_total_line + box_3_total_line
		out_data.append(
			{"transaction_type": "Box 4 Total (Box 1, Box 2, Box 3)", "heading": 1, "amount": total}
		)

		pi_query = '''
		SELECT
			pt.account_head AS gst_code,
			pt.base_tax_amount as amount,
			IF(pt.included_in_print_rate, p.net_total, p.base_net_total) as taxless_total
		FROM
			`tabPurchase Invoice` AS p,
			`tabPurchase Taxes and Charges` AS pt
		WHERE
			pt.parent = p.name
			AND p.docstatus = 1
			AND pt.parenttype = 'Purchase Invoice'
			AND pt.account_head = %(box_5)s
		"'''

		params = {
			"box_5": sgst_details[0].get("box_5")
		}
		
		if filters.company:
			pi_query += " AND p.company = %(company)s"
			params["company"] = filters.company

		if filters.from_date:
			pi_query += " AND DATE(p.posting_date) >= %(from_date)s"
			params["from_date"] = filters.from_date

		if filters.to_date:
			pi_query += " AND DATE(p.posting_date) <= %(to_date)s"
			params["to_date"] = filters.to_date

		pi_query += " ORDER BY p.name"
		p_sql_data = frappe.db.sql(pi_query, params, as_dict=True)
		box_5_balance_total = 0
		box_7_balance_total = 0
		box_5 = [
			{
				"transaction_type": "Total for Box 5 Total value of taxable purchases (excluding GST)",
				"heading": 1,
				"amount": 0,
			}
		]
		p_total = 0
		purchase_invoice_with_tax = []
		purchase_invoice_with_tax_total = 0
		if p_sql_data:
			# out_data = out_data + [{'transaction_type':'Box 5 Total value of taxable purchases (excluding GST)', 'heading':1}]
			cp_sqldata = p_sql_data.copy()
			for data in cp_sqldata:
				# if data.get('gst_code') in [sgst_details[0].get('box_1'), sgst_details[0].get('box_2'), sgst_details[0].get('box_3')]:
				purchase_invoice_with_tax_total = purchase_invoice_with_tax_total + data["amount"]
				box_7_balance_total = box_7_balance_total + data.get("amount")
				data["balance"] = box_7_balance_total
				purchase_invoice_with_tax.append(data)
				cp_dict = data.copy()
				cp_dict["amount"] = cp_dict["taxless_total"]
				box_5_balance_total = box_5_balance_total + cp_dict.get("amount")
				cp_dict["balance"] = box_5_balance_total
				p_total = p_total + cp_dict.get("amount")
			box_5[0]["amount"] = p_total
		out_data = out_data + box_5
		box_6 = [{"transaction_type": "Total for Box 6 Output tax due", "heading": 1, "amount": 0}]
		if sales_invoice_with_tax:
			box_6[0]["amount"] = sales_invoice_with_tax_total
			# out_data = out_data + [{'transaction_type':'Total for Box 6 Output tax due', 'heading':1, 'amount':sales_invoice_with_tax_total}]
		box_7 = [
			{"transaction_type": "Total for Box 7 Input tax and refunds claimed", "heading": 1, "amount": 0}
		]
		if purchase_invoice_with_tax:
			box_7[0]["amount"] = purchase_invoice_with_tax_total
			# out_data = out_data + [{'transaction_type':'Total for Box 7 Input tax and refunds claimed', 'heading':1, 'amount':purchase_invoice_with_tax_total}]
		out_data = out_data + box_6 + box_7
		box_8 = [{"transaction_type": "Box 8 Tax", "heading": 1, "amount": 0}]
		if purchase_invoice_with_tax_total and sales_invoice_with_tax_total:
			if sales_invoice_with_tax_total > purchase_invoice_with_tax_total:
				box_8[0]["transaction_type"] = "Box 8 Tax To Be Paid"
				box_8[0]["amount"] = sales_invoice_with_tax_total - purchase_invoice_with_tax_total
				# box_8 = [{'transaction_type':'Box 8 Tax To Be Paid', 'heading':1, 'amount': sales_invoice_with_tax_total-purchase_invoice_with_tax_total}]
			elif sales_invoice_with_tax_total < purchase_invoice_with_tax_total:
				box_8[0]["transaction_type"] = "Box 8 Tax To Be Claimed"
				box_8[0]["amount"] = purchase_invoice_with_tax_total - sales_invoice_with_tax_total
				# box_8 = [{'transaction_type':'Box 8 Tax To Be Claimed', 'heading':1, 'amount': purchase_invoice_with_tax_total-sales_invoice_with_tax_total}]
			elif sales_invoice_with_tax_total == purchase_invoice_with_tax_total:
				box_8 = [
					{"transaction_type": "Box 8 Tax", "heading": 1, "amount": purchase_invoice_with_tax_total}
				]
		box_9 = [
			{"transaction_type": "Total value of goods imported under this scheme", "heading": 1, "amount": 0}
		]
		box_10 = [{"transaction_type": "Total value of tourist refund claimed", "heading": 1, "amount": 0}]
		box_11 = [{"transaction_type": "Total value of bad debts relief", "heading": 1, "amount": 0}]
		box_12 = [{"transaction_type": "Pre-registration claims", "heading": 1, "amount": 0}]
		box_13 = [{"transaction_type": "Revenue", "heading": 1, "amount": acc_diff}]
		out_data = out_data + box_8 + box_9 + box_10 + box_11 + box_12 + box_13
	return out_data


def get_account_data(filters, sgst_details):
	total = 0
	other_income_total = 0
	acc_diff = 0

	if not filters.from_date or not filters.to_date:
		return 0

	if sgst_details and not sgst_details[0].get("other_income"):
		return 0

	period_list = get_period_list(
		frappe.defaults.get_user_default("fiscal_year"),
		frappe.defaults.get_user_default("fiscal_year"),
		filters.from_date,
		filters.to_date,
		"Date Range",
		"Yearly",
		company=filters.company,
	)

	period_list_filter = frappe._dict(
		{
			"from_fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
			"to_fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
			"period_start_date": filters.from_date,
			"period_end_date": filters.to_date,
			"periodicity": "Yearly",
			"filter_based_on": "Fiscal Year",
			"company": filters.company,
			"accumulated_values": 1,
			"cost_center": [],
			"include_default_book_entries": 1,
			"division": [],
			"project": [],
			"presentation_currency": frappe.db.get_single_value("Global Defaults", "default_currency"),
		}
	)

	income = financial_state_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=period_list_filter,
		accumulated_values=0,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	for inc in income:
		account_name = clean_name(inc.get("account_name", ""))
		if account_name == "Total Income (Credit)":
			total = inc.get("total")
		if inc.get("account") == sgst_details[0].get("other_income"):
			other_income_total = inc.get("total")
	acc_diff = float(total) - float(other_income_total)

	return acc_diff


def clean_name(val):
	if not val:
		return ""
	return val.replace('"', "").replace("'", "").strip()
