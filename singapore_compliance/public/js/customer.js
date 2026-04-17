frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Download SOA"), function () {
				frappe.show_alert({ message: __("Generating SOA…"), indicator: "blue" });
				frappe.call({
					method: "singapore_compliance.events.process_statement_of_accounts.get_customer_soa",
					args: { customer: frm.doc.name },
					callback: function (r) {
						if (!r.message || r.message.error) {
							frappe.msgprint(
								__(r.message ? r.message.error : "Failed to generate SOA.")
							);
							return;
						}
						let p_html = build_soa_html(frm.doc.name, r.message);
						frappe.render_pdf(p_html, { orientation: "Portrait" });
					},
				});
			});
		}
	},
});
