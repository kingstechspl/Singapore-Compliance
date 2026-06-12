import json

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters=None):
	columns = [
		{"fieldname": "transaction_type", "label": _("TRANSACTION TYPE"), "fieldtype": "Data", "width": 420},
		{"fieldname": "date", "label": _("DATE"), "fieldtype": "Date", "width": 100},
		{"fieldname": "name", "label": _("NO"), "fieldtype": "Data", "width": 180},
		{"fieldname": "party_name", "label": _("NAME"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "gst_code",
			"label": _("GST CODE"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 100,
		},
		{"fieldname": "gst_rate", "label": _("GST RATE"), "fieldtype": "Data", "width": 100},
		{"fieldname": "net_amount", "label": _("NET AMOUNT"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "amount", "label": _("AMOUNT"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "balance", "label": _("BALANCE"), "fieldtype": "Currency", "width": 100},
	]
	return columns


def get_data(filters=None):
	out_data = []
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
			"box_5_1",
			"box_5_2",
			"box_5_3",
			"bank_interest_income",
			"realised_exchange_gainloss",
		],
	)
	if sgst_details and (
		sgst_details[0].get("box_1")
		or sgst_details[0].get("box_2")
		or sgst_details[0].get("box_3")
		or sgst_details[0].get("bank_interest_income")
		or sgst_details[0].get("realised_exchange_gainloss")
	):
		jv_query = """
		SELECT
			je.posting_date AS date,
			'Journal Entry' AS transaction_type,
			je.name AS name,
			jea.account AS account,
			sum(jea.debit_in_account_currency) AS debit,
			sum(jea.credit_in_account_currency) AS credit
		FROM
			`tabJournal Entry` AS je LEFT JOIN
			`tabJournal Entry Account` AS jea on jea.parent=je.name

		WHERE
			je.docstatus = 1
			AND (jea.account = %(bank_interest)s
				OR jea.account = %(exchange_gain)s)
		"""

		params = {
			"bank_interest": sgst_details[0].get("bank_interest_income"),
			"exchange_gain": sgst_details[0].get("realised_exchange_gainloss"),
		}
		
		if filters.company:
			jv_query += " AND je.company = %(company)s"
			params["company"] = filters.company

		if from_date:
			jv_query += " AND je.posting_date >= %(from_date)s"
			params["from_date"] = from_date

		if to_date:
			jv_query += " AND je.posting_date <= %(to_date)s"
			params["to_date"] = to_date

		jv_query += " GROUP BY jea.account, je.name"
		jv_data = frappe.db.sql(jv_query, params, as_dict=True)
		total_jv = 0
		for data in jv_data:
			data["amount"] = -data.get("credit") or data.get("debit")
			k = data.get("debit") - data.get("credit")
			total_jv = total_jv + k
		py_query = """
			SELECT
				pe.posting_date AS date,
				'Payment Entry' AS transaction_type,
				pe.name AS name,
				pe.party_name AS party_name,
				ped.amount AS amount,
				ped.account AS account

			FROM
				`tabPayment Entry` AS pe LEFT JOIN
				`tabPayment Entry Deduction` AS ped on ped.parent=pe.name

			WHERE
				pe.docstatus = 1
				AND (ped.account = %(bank_interest)s
					OR ped.account = %(exchange_gain)s)
		"""
		params_py = {
			"bank_interest": sgst_details[0].get("bank_interest_income"),
			"exchange_gain": sgst_details[0].get("realised_exchange_gainloss"),
		}

		if filters.company:
			py_query += " AND pe.company = %(company)s"
			params_py["company"] = filters.company

		if from_date:
			py_query += " AND pe.posting_date >= %(from_date)s"
			params_py["from_date"] = from_date

		if to_date:
			py_query += " AND pe.posting_date <= %(to_date)s"
			params_py["to_date"] = to_date

		py_query += " GROUP BY ped.account, pe.name"

		py_data = frappe.db.sql(py_query, params_py, as_dict=True)
		total_py = 0
		for data in py_data:
			k = data.get("amount")
			total_py = total_py + k
		query = """
		SELECT
			si.posting_date AS date,
			'Sales Invoice' AS transaction_type,
			si.name AS name,
			si.customer_name AS party_name,
			st.account_head AS gst_code,
			st.rate as gst_rate,
			st.base_total as net_amount,
			st.base_tax_amount as amount,
			IF(st.included_in_print_rate, si.net_total, si.base_total) as taxless_total
		FROM
			`tabSales Invoice` AS si,
			`tabSales Taxes and Charges` AS st
		WHERE
			st.parent=si.name AND si.docstatus = 1
			"""
		params_si = {}

		if filters.company:
			query += " AND si.company = %(company)s"
			params_si["company"] = filters.company

		if from_date:
			query += " AND si.posting_date >= %(from_date)s"
			params_si["from_date"] = from_date

		if to_date:
			query += " AND si.posting_date <= %(to_date)s"
			params_si["to_date"] = to_date

		sql_data = frappe.db.sql(query, params_si, as_dict=True)
		box_1 = [
			{"transaction_type": "Box 1 Total value of standard-rated supplies (excluding GST)", "heading": 1}
		]
		box_2 = [
			{"transaction_type": "Box 2 Total value of standard-rated supplies (excluding GST)", "heading": 1}
		]
		box_3 = [
			{"transaction_type": "Box 3 Total value of standard-rated supplies (excluding GST)", "heading": 1}
		]
		out_data = []
		sales_invoice_with_tax = []
		sales_invoice_with_tax_total = 0
		box_1_total = 0
		box_2_total = 0
		box_3_total = 0
		box_1_balance_total = 0
		box_2_balance_total = 0
		box_3_balance_total = 0
		box_6_balance_total = 0
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
					box_6_balance_total = box_6_balance_total + data.get("amount")
					data["balance"] = box_6_balance_total
					sales_invoice_with_tax.append(data)
				cp_dict = data.copy()
				cp_dict["gst_rate"] = (0,)
				cp_dict["net_amount"] = (0,)
				cp_dict["amount"] = cp_dict["taxless_total"]
				if data.get("gst_code") == sgst_details[0].get("box_1"):
					total = total + cp_dict.get("amount")
					box_1_total = box_1_total + cp_dict.get("amount")
					box_1_balance_total = box_1_balance_total + cp_dict.get("amount")
					cp_dict["balance"] = box_1_balance_total
					box_1.append(cp_dict)
				elif data.get("gst_code") == sgst_details[0].get("box_2"):
					total = total + cp_dict.get("amount")
					box_2_balance_total = box_2_balance_total + cp_dict.get("amount")
					cp_dict["balance"] = box_2_balance_total
					box_2.append(cp_dict)
					box_2_total = box_2_total + cp_dict.get("amount")
				elif data.get("gst_code") == sgst_details[0].get("box_3"):
					total = total + cp_dict.get("amount")
					box_3_balance_total = box_3_balance_total + cp_dict.get("amount")
					cp_dict["balance"] = box_3_balance_total
					box_3.append(cp_dict)
					box_3_total = box_3_total + cp_dict.get("amount")
		# added jvtotal
		if jv_data:
			box_3.extend(jv_data)

		if py_data:
			box_3.extend(py_data)
		box_3_total = box_3_total + total_jv + total_py
		box_1_total_line = [
			{
				"transaction_type": "<b>Box 1 Total value of standard-rated supplies (excluding GST)</b>",
				"heading": 1,
				"amount": box_1_total,
			}
		]
		box_2_total_line = [
			{
				"transaction_type": "<b>Box 2 Total value of standard-rated supplies (excluding GST)</b>",
				"heading": 1,
				"amount": box_2_total,
			}
		]
		box_3_total_line = [
			{
				"transaction_type": "<b>Box 3 Total value of standard-rated supplies (excluding GST)</b>",
				"heading": 1,
				"amount": box_3_total,
			}
		]
		out_data = box_1 + box_1_total_line + box_2 + box_2_total_line + box_3 + box_3_total_line
		out_data = [
			*out_data,
			{"transaction_type": "<b>Box 4 Total (Box 1, Box 2, Box 3)</b>", "heading": 1, "amount": total},
		]

		box_5_accounts = '", "'.join(
			acc for acc in [
				sgst_details[0].get("box_5"),
				sgst_details[0].get("box_5_1"),
				sgst_details[0].get("box_5_2"),
				sgst_details[0].get("box_5_3"),
			]
			if acc
		)
		pi_query = f'''
		SELECT
			p.posting_date AS date,
			'Purchase Invoice' AS transaction_type,
			p.name AS name,
			p.supplier_name AS party_name,
			pt.account_head AS gst_code,
			CASE
				WHEN pi.item_tax_template IS NOT NULL AND pi.item_tax_template != ''
				THEN ittd.tax_rate
				ELSE pt.rate
			END as gst_rate,
			pi.base_net_amount as net_amount,
			CASE
				WHEN pi.item_tax_template IS NOT NULL AND pi.item_tax_template != ''
				THEN IFNULL(pi.base_net_amount * ittd.tax_rate / 100, 0)
				ELSE (pi.base_net_amount / NULLIF(p.base_net_total, 0)) * pt.base_tax_amount
			END as amount,
			pi.base_net_amount as taxless_total
		FROM
			`tabPurchase Invoice` AS p
			JOIN `tabPurchase Taxes and Charges` AS pt ON pt.parent = p.name
				AND pt.name = (
					SELECT pt2.name FROM `tabPurchase Taxes and Charges` AS pt2
					WHERE pt2.parent = p.name AND pt2.parenttype = "Purchase Invoice"
					AND pt2.account_head in ("{box_5_accounts}")
					ORDER BY pt2.idx LIMIT 1
				)
			JOIN `tabPurchase Invoice Item` AS pi ON pi.parent = p.name
			LEFT JOIN `tabItem Tax Template Detail` AS ittd ON ittd.parent = pi.item_tax_template
				AND ittd.tax_type = pt.account_head
		WHERE
			p.docstatus = 1 AND pt.parenttype = "Purchase Invoice" AND
			pt.account_head in ("{box_5_accounts}")'''

		if filters.company:
			pi_query += f' AND p.company="{filters.company}"'

		if from_date:
			pi_query += f' AND DATE(p.posting_date) >= "{from_date}"'
		if to_date:
			pi_query += f' AND DATE(p.posting_date) <= "{to_date}"'

		pi_query += " ORDER BY p.name"

		p_sql_data = frappe.db.sql(pi_query, as_dict=True)
		box_5_balance_total = 0
		box_7_balance_total = 0
		box_5 = [
			{
				"transaction_type": "<b>Total for Box 5 Total value of taxable purchases (excluding GST)</b>",
				"heading": 1,
			}
		]
		p_total = 0
		purchase_row_without_gst = []
		purchase_invoice_with_tax = []
		purchase_invoice_with_tax_total = 0
		if p_sql_data:
			out_data.append(
				{"transaction_type": "Box 5 Total value of taxable purchases (excluding GST)", "heading": 1}
			)

			cp_sqldata = p_sql_data.copy()
			for data in cp_sqldata:
				# if data.get('gst_code') in [sgst_details[0].get('box_1'), sgst_details[0].get('box_2'), sgst_details[0].get('box_3')]:
				purchase_invoice_with_tax_total = purchase_invoice_with_tax_total + data["amount"]
				box_7_balance_total = box_7_balance_total + data.get("amount")
				data["balance"] = box_7_balance_total
				purchase_invoice_with_tax.append(data)
				cp_dict = data.copy()
				cp_dict["net_amount"] = (0,)
				cp_dict["amount"] = cp_dict["taxless_total"]
				box_5_balance_total = box_5_balance_total + cp_dict.get("amount")
				cp_dict["balance"] = box_5_balance_total
				purchase_row_without_gst.append(cp_dict)
				p_total = p_total + cp_dict.get("amount")
			box_5[0]["amount"] = p_total
			out_data = out_data + purchase_row_without_gst + box_5
		if sales_invoice_with_tax:
			out_data.append(
				{
					"transaction_type": "Box 6 Output tax due",
					"heading": 1,
				}
			)

			out_data.extend(sales_invoice_with_tax)

			out_data.append(
				{
					"transaction_type": "<b>Total for Box 6 Output tax due</b>",
					"heading": 1,
					"amount": sales_invoice_with_tax_total,
				}
			)

		if purchase_invoice_with_tax:
			out_data.append(
				{
					"transaction_type": "Box 7 Input tax and refunds claimed",
					"heading": 1,
				}
			)

			out_data.extend(purchase_invoice_with_tax)

			out_data.append(
				{
					"transaction_type": "<b>Total for Box 7 Input tax and refunds claimed</b>",
					"heading": 1,
					"amount": purchase_invoice_with_tax_total,
				}
			)
		box_8 = []
		if purchase_invoice_with_tax_total and sales_invoice_with_tax_total:
			if sales_invoice_with_tax_total > purchase_invoice_with_tax_total:
				box_8 = [
					{
						"transaction_type": "<b>Box 8 Tax To Be Paid</b>",
						"heading": 1,
						"amount": sales_invoice_with_tax_total - purchase_invoice_with_tax_total,
					}
				]
			elif sales_invoice_with_tax_total < purchase_invoice_with_tax_total:
				box_8 = [
					{
						"transaction_type": "<b>Box 8 Tax To Be Claimed</b>",
						"heading": 1,
						"amount": purchase_invoice_with_tax_total - sales_invoice_with_tax_total,
					}
				]
			elif sales_invoice_with_tax_total == purchase_invoice_with_tax_total:
				box_8 = [
					{
						"transaction_type": "<b>Box 8 Tax</b>",
						"heading": 1,
						"amount": purchase_invoice_with_tax_total,
					}
				]
			out_data = out_data + box_8

		# for val in out_data:
		# 	frappe.msgprint(json.dumps(val['heading'], default=str))
		# 	if val['transaction_type'] == 'Box 3 Total value of standard-rated supplies (excluding GST)' and val['heading'] == 2:
		# 		val['amount'] = val['amount'] + total_jv
		# 		frappe.msgprint(json.dumps(val['amount'], default=str))

	return out_data
