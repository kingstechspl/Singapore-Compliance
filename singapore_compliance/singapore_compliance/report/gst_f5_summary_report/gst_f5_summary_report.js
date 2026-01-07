// Copyright (c) 2022, earthians and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GST F5 Summary Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			width: 100,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			width: 100,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			width: 100,
			default: frappe.datetime.month_end(),
		},
	],
};
