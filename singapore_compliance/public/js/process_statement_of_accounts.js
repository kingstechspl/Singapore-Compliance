frappe.ui.form.on("Process Statement Of Accounts", {
	refresh(frm) {
		frm.add_custom_button(__("Download SOA"), function () {
			frappe.call({
				method: "singapore_compliance.events.process_statement_of_accounts.get_statements_of_account",
				args: {
					name: frm.doc.name,
				},
				callback: function (r) {
					let p_html = build_soa_html(frm.doc.name, r.message);
					frappe.render_pdf(p_html, { orientation: "Portrait" });
				},
			});
		});
		frm.remove_custom_button(__("Download"));
	},
});
