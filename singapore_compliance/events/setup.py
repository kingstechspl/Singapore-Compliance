import frappe, time
from frappe import _
from frappe.utils.background_jobs import enqueue


def create_charts_of_accounts(company):
	frappe.flags.ignore_permissions = True

	# -----------------------------
	# TAX ACCOUNTS
	# -----------------------------
	tax_asset_accounts = [
		"Input-GST-TX9",
		"Input-GST-ZP",
		"Input-GST-IM9",
	]

	liability_tax_accounts = [
		"Output-GST-SR9",
		"Output-GST-ZR",
		"Output-GST-ES33",
	]

	# -----------------------------
	# TAX ASSET PARENT
	# -----------------------------
	tax_assets_parent = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_name": "Tax Assets",
			"is_group": 1,
		},
		"name",
	)

	if not tax_assets_parent:
		frappe.throw(_("Tax Assets account not found. Chart of Accounts missing."))

	for account_name in tax_asset_accounts:
		if frappe.db.exists("Account", {"account_name": account_name, "company": company}):
			continue

		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": tax_assets_parent,
				"company": company,
				"account_type": "Tax",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	# -----------------------------
	# TAX LIABILITY PARENT
	# -----------------------------
	duties_taxes_parent = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_name": "Duties and Taxes",
			"is_group": 1,
		},
		"name",
	)

	if not duties_taxes_parent:
		frappe.throw(_("Duties and Taxes account not found."))

	for account_name in liability_tax_accounts:
		if frappe.db.exists("Account", {"account_name": account_name, "company": company}):
			continue

		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": duties_taxes_parent,
				"company": company,
				"account_type": "Tax",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	# -----------------------------
	# SALES TAX TEMPLATES
	# -----------------------------
	sales_tax_templates = [
		{"name": "GST-SR9", "rate": 9},
		{"name": "GST-ZR", "rate": 0},
		{"name": "GST-ES33", "rate": 0},
	]

	for row in sales_tax_templates:
		if frappe.db.exists(
			"Sales Taxes and Charges Template",
			{"title": row["name"], "company": company},
		):
			continue

		account_head = frappe.db.get_value(
			"Account",
			{"account_name": f"Output-{row['name']}", "company": company},
			"name",
		)

		if not account_head:
			continue

		default = 0
		if row["name"] == "GST-SR9":
			default = 1

		frappe.get_doc(
			{
				"doctype": "Sales Taxes and Charges Template",
				"title": row["name"],
				"company": company,
				"is_default": default,
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": account_head,
						"rate": row["rate"],
						"description": row["name"],
					}
				],
			}
		).insert(ignore_permissions=True)

	# -----------------------------
	# PURCHASE TAX TEMPLATES
	# -----------------------------
	purchase_tax_templates = [
		{"name": "GST-TX9", "account": "Input-GST-TX9", "rate": 9},
		{"name": "GST-ZP", "account": "Input-GST-ZP", "rate": 0},
		{"name": "GST-IM9", "account": "Input-GST-IM9", "rate": 9},
	]

	for row in purchase_tax_templates:
		if frappe.db.exists(
			"Purchase Taxes and Charges Template",
			{"title": row["name"], "company": company},
		):
			continue

		account_head = frappe.db.get_value(
			"Account",
			{"account_name": row["account"], "company": company},
			"name",
		)

		if not account_head:
			continue

		default = 0
		if row["account"] == "Input-GST-IM9":
			default = 1

		frappe.get_doc(
			{
				"doctype": "Purchase Taxes and Charges Template",
				"title": row["name"],
				"company": company,
				"is_default": default,
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": account_head,
						"rate": row["rate"],
						"description": row["name"],
					}
				],
			}
		).insert(ignore_permissions=True)
	
	charts_of_account = frappe.db.get_value("Company", company, "chart_of_accounts")
	params = frappe._dict({
		"company_name" : company,
		"chart_of_accounts" : charts_of_account
	})

	if charts_of_account == "Singapore - Chart of Accounts":
		if income_account := frappe.db.exists(
			"Account", 
			{"company": company, "account_name": "Sales Income"},
		):
			frappe.db.set_value("Company", company, "default_income_account", income_account)
		else:
			set_income_account(params)

	if params.get("chart_of_accounts") == "Standard" or params.get("chart_of_accounts") == "Standard with Numbers":
		if income_account := frappe.db.exists(
			"Account", 
			{"company": company, "account_name": "Sales"},
		):
			frappe.db.set_value("Company", company, "default_income_account", income_account)
			return
		else:
			time.sleep(1)
			set_income_account(params)
			return
	
	if params.get("chart_of_accounts") == "Singapore - F&B Chart of Accounts":
		set_income_account(params)

	frappe.db.commit() # nosemgrep - required for setup wizard


def get_setup_wizard_stages(params=None):
	# Run only during first setup
	if frappe.db.exists("Account"):
		return []

	if frappe.db.exists("Company"):
		return []

	return [
		{
			"status": _("Setting up Singapore Compliance"),
			"fail_msg": _("Singapore Compliance setup failed"),
			"tasks": [
				{
					"fn": run_sg_tax_setup,
					"args": params,
				},
				{
					"fn": update_gst_settings,
					"args": params,
				},
				{
					"fn" : set_income_account,
					"args": params
				}
			],
		}
	]

def set_income_account(params, retry=0):
	enqueue(
		setup_income_account,
		params=params,
		retry=retry,
		queue="short"
	)


def setup_income_account(params, retry=0):
	company = params.get("company_name")
	max_retry = 20

	if retry > max_retry:
		frappe.log_error("Income account setup failed after retries", company)
		return

	# ---- Check company exists ---- #
	if not frappe.db.exists("Company", company):
		time.sleep(1)
		set_income_account(params, retry + 1)
		return

	# --- check if chart of accounts are Singapore - Chart of Accounts --- #
	if params.get("chart_of_accounts") == "Singapore - Chart of Accounts":
		if income_account := frappe.db.exists(
			"Account", 
			{"company": company, "account_name": "Sales Income"},
		):
			frappe.db.set_value("Company", company, "default_income_account", income_account)
			return
		else:
			time.sleep(1)
			set_income_account(params, retry + 1)
			return
	
	if params.get("chart_of_accounts") == "Standard" or params.get("chart_of_accounts") == "Standard with Numbers":
		if income_account := frappe.db.exists(
			"Account", 
			{"company": company, "account_name": "Sales"},
		):
			frappe.db.set_value("Company", company, "default_income_account", income_account)
			return
		else:
			time.sleep(1)
			set_income_account(params, retry + 1)
			return
			

	# ---- Check Direct Income exists for this company ----
	parent = frappe.db.get_value(
		"Account",
		{"company": company, "account_name": "Direct Income"},
		"name"
	)

	if not parent:
		time.sleep(1)
		set_income_account(params, retry + 1)
		return

	# ---- Check if Sales already created ----
	existing_sales = frappe.db.exists("Account", {
		"company": company,
		"account_name": "Sales"
	})

	if existing_sales and params.get("chart_of_accounts") == "Singapore - F&B Chart of Accounts":
		frappe.db.set_value("Company", company, "default_income_account", existing_sales)
		return  

	# ---- Create Sales safely ----
	try:
		if params.get("chart_of_accounts") == "Singapore - F&B Chart of Accounts":
			income_account = frappe.get_doc({
				"doctype": "Account",
				"account_name": "Sales",
				"company": company,
				"root_type": "Income",
				"report_type": "Profit and Loss",
				"account_currency": frappe.get_cached_value("Company", company, "default_currency"),
				"parent_account": parent,
			})
			income_account.insert(ignore_if_duplicate=True)

	except Exception:
		frappe.log_error("Not Found Income Account", "Default Income Account")
	

	# ---- Set default income ----
	frappe.db.set_value("Company", company, "default_income_account", income_account.name)


def run_sg_tax_setup(params):
	company = params.company_name
	from singapore_compliance.events.setup import create_charts_of_accounts

	create_charts_of_accounts(company)


def update_gst_settings(params):
	company = params.company_name
	if not frappe.db.exists("Singapore GST Settings", "Singapore GST Settings"):
		return

	doc = frappe.get_single("Singapore GST Settings")
	box_1 = frappe.db.get_value("Account", {"account_name": "Output-GST-SR9"}, "name")
	box_2 = frappe.db.get_value("Account", {"account_name": "Output-GST-ZR"}, "name")
	box_3 = frappe.db.get_value("Account", {"account_name": "Output-GST-ES33"}, "name")
	box_5 = frappe.db.get_value("Account", {"account_name": "Input-GST-TX9"}, "name")
	box_5_1 = frappe.db.get_value("Account", {"account_name": "Input-GST-ZP"}, "name")
	box_5_2 = frappe.db.get_value("Account", {"account_name": "Input-GST-IM9"}, "name")

	default_income_account = frappe.db.get_value("Account", {"account_name": "Other Income"}, "name")
	default_bank_interest_account = frappe.db.get_value(
		"Account", {"account_name": "Fixed Deposit Interest Earned"}, "name"
	)

	exchange_gain_loss_account = frappe.db.get_value(
		"Account", {"account_name": "Currency Exchange Differences"}, "name"
	)

	doc.append(
		"sgst_details",
		{
			"company": company,
			"box_1": box_1,
			"box_2": box_2,
			"box_3": box_3,
			"box_5": box_5,
			"box_5_1": box_5_1,
			"box_5_2": box_5_2,
			"other_income": default_income_account,
			"bank_interest_income": default_bank_interest_account,
			"realised_exchange_gainloss": exchange_gain_loss_account,
		},
	)

	doc.flags.ignore_permissions = True
	doc.save()
	frappe.db.commit() # nosemgrep - required for setup wizard
