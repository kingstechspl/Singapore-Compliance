import frappe
from singapore_compliance.events.setup import (
	create_charts_of_accounts,
	update_gst_settings,
)


MAX_RETRY = 10
RETRY_INTERVAL = 10  # seconds


def setup_charts_of_account_for_new_company(doc, method=None):
	"""
	Execute Chart of Accounts creation ONLY when:
	- Site setup is completed
	- A new company is created (not the first one)
	"""

	# Ensure default company exists
	default_company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not default_company:
		return

	if _tax_parents_exist(doc.name):
		_run_sg_setup(doc)
	else:
		frappe.enqueue(
			create_chart_of_accounts_in_rq,
			doc_name=doc.name,
			retry=0,
			queue="short",
		)


def create_chart_of_accounts_in_rq(doc_name, retry=0):
	"""
	RQ job with retry limit to avoid infinite loop
	"""

	if retry >= MAX_RETRY:
		frappe.log_error(
			title="Singapore COA Setup Failed",
			message=(
				f"Tax parent accounts not found for company {doc_name} "
				f"after {MAX_RETRY} retries"
			),
		)
		return

	if _tax_parents_exist(doc_name):
		doc = frappe.get_doc("Company", doc_name)
		_run_sg_setup(doc)
		return

	# Re-enqueue with delay instead of blocking sleep
	frappe.enqueue(
		create_chart_of_accounts_in_rq,
		doc_name=doc_name,
		retry=retry + 1,
		queue="short",
		enqueue_in=RETRY_INTERVAL,
	)


# ------------------------
# Helper methods
# ------------------------

def _tax_parents_exist(company):
	tax_assets_parent = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_name": "Tax Assets",
			"is_group": 1,
		},
		"name",
	)

	duties_taxes_parent = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_name": "Duties and Taxes",
			"is_group": 1,
		},
		"name",
	)

	return bool(tax_assets_parent and duties_taxes_parent)


def _run_sg_setup(doc):
	"""
	Run Singapore COA + GST setup safely (idempotent)
	"""
	create_charts_of_accounts(doc.name)
	doc.update({"company_name": doc.name})
	update_gst_settings(doc)
