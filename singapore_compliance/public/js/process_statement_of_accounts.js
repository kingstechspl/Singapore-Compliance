frappe.ui.form.on("Process Statement Of Accounts", {
	refresh(frm) {
		frm.add_custom_button(__("Download SOA"), function () {
			frappe.call({
				method: "singapore_compliance.events.process_statement_of_accounts.get_statements_of_account",
				args: {
					name: frm.doc.name,
				},
				callback: function (r) {
					// let p_html = build_soa_html(frm.doc.name, r.message);
					let p_html = get_html(frm, r.message);
					frappe.render_pdf(p_html, { orientation: "Portrait" });
					console.log(r.message);
				},
			});
		});
		frm.remove_custom_button(__("Download"));
	},
});


var get_html = function (frm, r) {
	let style = `
	<style>
		.page-break    { display: block; page-break-before: always; }

		.lhead{
			font-size:9px;
			margin-top:0px;
			margin-bottom:0px !important;
			vertical-align: top !important;
			}
			*{
				font-family: 'IBM Plex Sans', sans-serif !important;
			}
		.print-format {
			margin-left: 4mm;
			margin-right: 4mm;	  
		}
		.new1{
			border-top: 1px dotted !important;
			}
		.blhead{
		font-weight:600 !important;
		font-size:9px !important;
		}
		.print-format .letter-head {
			margin-bottom: 0px;
			}
		.print-format .letterhead td, .print-format th {
		padding: 1 1px 1 1px !important;
		vertical-align: top !important;
		margin:0px !important;
		}
		.print-format p{
		margin:0px 0px 2px;
		}
		.print-format .letter-head {
		margin-bottom: 0px;
		}
		
		p{
			font-size: 13px;
		}
		.address-sec{
			margin-top:0px;
			margin-bottom:0px !important;
			vertical-align: text-top;
		}
		.left_dotted {
			border-left: 2px dotted !important;
		}
		.ontop{
			border-top: 1px;
		}
		.onbottom{
			border-bottom: 1px;;
		}
	</style>`;

	let header = `
		<div id="header-html" class="letter-head visible-pdf"  style="padding-top:10px;">
			<div class="letter-head">
				<table  width="100%" "class="letter-head">
					<tbody>
					<tr>
						<td width="10%">
							<img height="60" src="/files/JLES_logo.png" width="60">
						</td>
						<td width="22%">
							<p style="margin-bottom:0px !important; margin-top:0px;">
								<b style="font-size:11px; margin-bottom:0px !important; margin-top:0px;">JLES SERVICES PTE. LTD.</b>
							</p>
							<p class="lhead">67 UBI CRESCENT,</p>
							<p class="lhead">#03-02,</p>
							<p class="lhead">Singapore 408560</p>
						</td>
						<td width="28%">
							<br>
							<p class="lhead"><b class="blhead">Web:</b>-</p>
							<p class="lhead"><b class="blhead">UEN/GST No:</b> 202330432M</p>
						</td>
						<td align="centre">
							<b style="font-size: 20px; text-transform: uppercase;">
							Statement of Account
							</b>
						</td>
					</tr></tbody>
				</table>
			<div/>
		<div/>
		<hr>
		<div>
		`;

	let html = style + `
	<table width="100%" style="border-collapse:collapse;">

	<thead style="display: table-header-group;">
	<tr>
	<td>

	${header}
	`;
	if (r.cust) {
		var total_credit = 0
		var total_debit = 0
		var total_credit_count = 0
		var total_debit_count = 0
		var closing_balance = 0
		$.each(r.cust, function (j, cu) {
			if (cu.data) {
				cu.data.forEach(val => {
					if (val.voucher_no) {
						total_credit += (val.credit || 0);
						total_debit += (val.debit || 0);

						if (val.debit) total_debit_count++;
						if (val.credit) total_credit_count++;

					}
				});
				closing_balance = (total_debit || 0) - (total_credit || 0);
			}
			html += `

		<table width="100%" class="cust_head">
	<tbody>
		<tr>
			<td>
			<p class="address-sec">${
				cu.cad_data && cu.cad_data.customer_name ? cu.cad_data.customer_name : ""
			}</p>
			<p class="address-sec">${
				cu.cad_data && cu.cad_data.address_line1 ? cu.cad_data.address_line1 : ""
			}</p>
			<p class="address-sec">${
				cu.cad_data && cu.cad_data.address_line2 ? cu.cad_data.address_line2 : ""
			}</p>
			<p class="address-sec">${cu.cad_data && cu.cad_data.city ? cu.cad_data.city : ""} ${
				cu.cad_data && cu.cad_data.pincode ? cu.cad_data.pincode : ""
			}</p>
			<p class="address-sec">${cu.cad_data && cu.cad_data.country ? cu.cad_data.country : ""}</p>
			</td>
			
			<td class="left_dotted">
				<p class="address-sec" style="padding-left:10px;">Statement No.: ${frm.doc.name}</p>
				<p class="address-sec" style="padding-left:10px;">Date.: ${r.posting_date} </p>
				<div style="margin-top:10px; padding:8px; border:1px solid #000; font-size:13px;">

				<p style="margin:0; display:flex; justify-content:space-between;">
					<span>Total Debit (${total_debit_count || 0})</span>
					<span>${format_currency(total_debit || 0)}</span>
				</p>

				<p style="margin:0; display:flex; justify-content:space-between;">
					<span>Total Credit (${total_credit_count || 0})</span>
					<span>${format_currency(total_credit || 0)}</span>
				</p>

				<hr style="margin:6px 0;">

				<p style="margin:0; display:flex; justify-content:space-between; font-weight:bold;">
					<span>Closing Balance</span>
					<span>${format_currency(closing_balance || 0)}</span>
				</p>
			</div>
			</td>
		</tr>
	</tbody>
</table>
<hr class="new1">
		<table width="100%" style="font-size:12px; margin-top:5px; border-bottom:1px solid #000; border-collapse:collapse;">
			<tr>
				<td width="18%" style="vertical-align:top; padding:4px;">
					<b>Attention</b><br>
					${cu.cco_data?.first_name || ""}
				</td>

				<td width="8%" style="vertical-align:top; padding:4px; text-align:center;">
					<b>Currency</b><br>
					${r.currency || ""}
				</td>

				<td width="10%" style="vertical-align:top; padding:4px;">
					<b>Terms</b><br>
					${cu.cad_data?.payment_terms || ""}
				</td>

				<td width="10%" style="vertical-align:top; padding:4px; text-align:right;">
					<b>Date</b><br>
					${r.posting_date || ""}
				</td>
			</tr>
		</table>
		</thead> 
		<table class="table table-bordered"  style="font-size: 12px; border-spacing: 1px;">
		<thead>
			<tr>
				<td style="width: 10%"><b>DOCDATE</b></td>
				<td style="width: 20%"><b>Doc NO</b></td>
				<td style="width: 20%"><b>Doc Title</b></td>
				<td style="width: 10%" align="right"><b>DEBIT</b></td>
				<td style="width: 10%" align="right"><b>CREDIT</b></td>
				<td style="width: 20%" align="right"><b>ACCUM. BALANCE</b></td>
			</tr>
		</thead>
		<tbody>
		`;
			if (cu.data) {
				var idx = 1;
				var running_balance = 0;

				// Initialize running balance from opening row (pre-period outstanding invoices)
				if (cu.data[0] && !cu.data[0].voucher_no && cu.data[0].account === "Opening" && cu.data[0].debit) {
					running_balance = cu.data[0].balance || 0;
					html += `<tr>
						<td style="width: 5%"></td>
						<td style="width: 20%"><b>Opening Balance</b></td>
						<td style="width: 12%"></td>
						<td style="width: 10%"></td>
						<td style="width: 10%" align="right"><b>${format_currency(cu.data[0].debit.toFixed(2)).replace("$", "")}</b></td>
						<td style="width: 10%" align="right">-</td>
						<td style="width: 14%" align="right"><b>${format_currency(running_balance)}</b></td>
					</tr>`;
				}

				$.each(cu.data, function (i, val) {
					if (val.voucher_no) {
						running_balance += (val.debit || 0) - (val.credit || 0);
						html += `<tr>
						<td style="width: 12%">${val.posting_date ? val.posting_date : ""}</td>
						<td style="width: 15%">${val.voucher_no ? val.voucher_no : ""}</td>
						<td style="width: 15%">${val.doc_title ? val.doc_title : ""}</td>
						<td style="width: 10%" align="right">${
							val.debit
								? format_currency(val.debit.toFixed(2)).replace("$", "")
								: "-"
						}</td>
						<td style="width: 10%" align="right">${
							val.credit
								? format_currency(
										(
											Number(Math.round(val.credit + Number.EPSILON) * 100) /
											100
										).toFixed(2)
								  ).replace("$", "")
								: "-"
						}</td>
						<td style="width: 14%" align="right">${format_currency(running_balance)}</td>
					</tr>`;
						if (i % 30 == 0 && idx > 1) {
							html += `
						</tbody>
						</table>
						<div class="page-break"></div>
						`;
							html = html + header;
							html += `
							<table class="table table-bordered"  style="font-size: 13px; border-spacing: 1px;">
							<thead>
								<tr>
									<td style="width: 10%"><b>DOCDATE</b></td>
									<td style="width: 20%"><b>Doc NO</b></td>
									<td style="width: 20%"><b>Doc Title</b></td>
									<td style="width: 10%" align="right"><b>DEBIT</b></td>
									<td style="width: 10%" align="right"><b>CREDIT</b></td>
									<td style="width: 20%" align="right"><b>ACCUM. BALANCE</b></td>
								</tr>
							</thead>
							<tbody>
							`;
						}
						idx += 1;
					}
				});
			}
			html += `</tbody>
		</table>

		<div id="footer-html" class="visible-pdf letter-head-footer">
		<table width="100%" class="table" >
			<tbody>
				<tr>
					<td width="14%" class="ontop onbottom"><p><b>In Words:</b></p></td>
					<td width="60%" class="ontop onbottom"><p>${cu.ageing.outstanding_in_words}</p></td>
					<td width="12%" class="ontop onbottom"><p><b>Total Due</b>:</p></td>
					<td width="14%" class="ontop onbottom"><p>${
						cu.ageing && cu.ageing.outstanding
							? format_currency(cu.ageing.outstanding)
							: "-"
					}</p></td>
				</tr>
			</tbody>
		</table>
		<table class="table table-bordered" style="font-size: 13px; border-spacing: 0px;">
		<thead>
			<tr>
				<td style="width: 16%" align="center"><b>Current Due</b></td>
				<td style="width: 16%" align="center"><b>1-30 Days</b></td>
				<td style="width: 16%" align="center"><b>31-60 Days</b></td>
				<td style="width: 16%" align="center"><b>61-90 Days</b></td>
				<td style="width: 16%" align="center"><b>120+ Days</b></td>
				<td style="width: 16%" align="center"><b>Amount Due</b></td>
			</tr>
		</thead>
		<tbody>
			<tr>
				<td align="center">${
					cu.ageing && cu.ageing.current_due
						? format_currency(cu.ageing.current_due)
						: "-"
				}</td>
				<td align="center">${cu.ageing && cu.ageing.range1 ? format_currency(cu.ageing.range1) : "-"}</td>
				<td align="center">${cu.ageing && cu.ageing.range2 ? format_currency(cu.ageing.range2) : "-"}</td>
				<td align="center">${cu.ageing && cu.ageing.range3 ? format_currency(cu.ageing.range3) : "-"}</td>
				<td align="center">${
						cu.ageing && (cu.ageing.range4 || cu.ageing.range5)
							? format_currency((cu.ageing.range4 || 0) + (cu.ageing.range5 || 0))
							: "-"
					}</td>
				<td align="center">${
					cu.ageing && cu.ageing.outstanding
						? format_currency(cu.ageing.outstanding)
						: "-"
				}</td>
			</tr>
		</tbody>
	</table>
	<center style="font-size: 8px;">THIS IS A COMPUTER GENERATED DOCUMENT. NO SIGNATURE IS REQUIRED. </center>
	</div>`;
			if (j + 1 < r.cust.length) {
				html += `
			<div style="page-break-before: always;" class="pagebreak"></div>`;
				html += header;
			}
		});
	}

	html += "</div>";
	return html;
};
