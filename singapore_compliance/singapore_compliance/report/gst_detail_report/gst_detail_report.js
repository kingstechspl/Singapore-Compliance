// Copyright (c) 2022, earthians and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GST Detail Report"] = {
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
		{
			fieldname: "order_by_date",
			label: __("Order By Date"),
			fieldtype: "Select",
			options: "\nAscending\nDescending",
			default: "",
			width: 100,
		},
		{
			fieldname: "order_by_supplier",
			label: __("Order By Supplier"),
			fieldtype: "Select",
			options: "\nAscending\nDescending",
			default: "",
			width: 100,
		},
	],
};
