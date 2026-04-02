frappe.ui.form.on("Process Statement Of Accounts", {
	refresh(frm) {
		frm.add_custom_button(__("Download SOA"), function () {
			frappe.call({
				method: "singapore_compliance.events.process_statement_of_accounts.get_statements_of_account",
				args: {
					name: frm.doc.name,
				},
				callback: function (r) {
					let p_html = set_html(frm, r.message);
					frappe.render_pdf(p_html, { orientation: "Portrait" });
				},
			});
		});
		frm.remove_custom_button(__("Download"));
	},
});

var set_html = function (frm, r) {
	let style = `
	<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">
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
<div class="letter-head"  style="padding-top:10px;">
	<div class="letter-head">
	<table  width="100%" "class="letter-head">
	<tbody>
	   <tr>
		  <td width="10%">
			<img height="60" src="/files/KGS-Logo.png" width="60">
		  </td>
		  <td width="21%">
			 <p style="margin-bottom:0px !important; margin-top:0px;">
			 	<b style="font-size:11px; margin-bottom:0px !important; margin-top:0px;">KGS Pte Ltd</b>
			 </p>
			 <p class="lhead">8 Tuas South Lane,</p>
			 <p class="lhead">#01-71, Factory 4,</p>
			 <p class="lhead">Singapore 637302</p>
		  </td>
		  <td width="32%">
			 <br>
			 <p class="lhead"><b class="blhead">Web:</b>kgs.com.sg</p>
			 <p class="lhead"><b class="blhead">UEN/GST No:</b> 201607799N</p>
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

	let html = style + header;
	if (r.cust) {
		$.each(r.cust, function (j, cu) {
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
			<td>
				<p class="address-sec">Currency : ${r.currency ? r.currency : ""}</p>
				<p class="address-sec">Payment Terms : C.O.D</p>
				<p class="address-sec">Total Due : ${
					cu.ageing && cu.ageing.outstanding
						? format_currency(cu.ageing.outstanding)
						: ""
				}</p>
			</td>
			<td class="left_dotted">
				<p class="address-sec" style="padding-left:10px;">Statement No.: ${frm.doc.name}</p>
				<p class="address-sec" style="padding-left:10px;">Date.: ${r.posting_date} </p>
			</td>
		</tr>
	</tbody>
</table>
<hr class="new1">
		<table class="table table-bordered"  style="font-size: 13px; border-spacing: 1px;">
		<thead>
			<tr>
				<td style="width: 5%"><b>No.</b></td>
				<td style="width: 20%"><b>Doc NO</b></td>
				<td style="width: 12%"><b>DOCDATE</b></td>
				<td style="width: 10%"><b>DUE DATE</b></td>
				<td style="width: 10%" align="right"><b>DEBIT</b></td>
				<td style="width: 10%" align="right"><b>CREDIT</b></td>
				<td style="width: 14%" align="right"><b>ACCUM. BALANCE</b></td>
			</tr>
		</thead>
		<tbody>
		`;
			if (cu.data) {
				var idx = 1;
				$.each(cu.data, function (i, val) {
					if (val.voucher_no) {
						html += `<tr>
						<td style="width: 5%">${idx}</td>
						<td style="width: 20%">${val.voucher_no ? val.voucher_no : ""}</td>
						<td style="width: 12%">${val.posting_date ? val.posting_date : ""}</td>
						<td style="width: 12%">${val.due_date ? val.due_date : ""}</td>
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
						<td style="width: 14%" align="right">${val.balance ? format_currency(val.balance) : "-"}</td>
					</tr>`;
						if (i % 30 == 0) {
							console.log("h");
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
									<td style="width: 5%"><b>No.</b></td>
									<td style="width: 20%"><b>Doc NO</b></td>
									<td style="width: 12%"><b>DOCDATE</b></td>
									<td style="width: 10%"><b>DUE DATE</b></td>
									<td style="width: 10%" align="right"><b>DEBIT</b></td>
									<td style="width: 10%" align="right"><b>CREDIT</b></td>
									<td style="width: 14%" align="right"><b>ACCUM. BALANCE</b></td>
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
				<td align="center">${cu.ageing && cu.ageing.range4 ? format_currency(cu.ageing.range4) : "-"}</td>
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
