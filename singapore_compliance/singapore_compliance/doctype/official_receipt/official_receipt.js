// Copyright (c) 2024, earthians and contributors
// For license information, please see license.txt

frappe.ui.form.on("Official Receipt", {
	refresh: function (frm) {
		frm.add_custom_button(__("Download"), function () {
			frappe.call({
				method: "singapore_compliance.singapore_compliance.report.official_receipt___kgs.official_receipt___kgs.get_print_data",
				args: {
					customer: frm.doc.customer,
					from_date: frm.doc.from_date,
					to_date: frm.doc.to_date,
					company: frm.doc.company,
				},
				callback: function (r) {
					console.log(r.message);
					// Get company logo first, then build HTML
					get_html_with_logo(frm, r.message);
				},
			});
		});
	},
});

// Helper function to safely get values
let safeGet = (value, defaultValue = "") => {
	return value !== undefined && value !== null ? value : defaultValue;
};

let get_html_with_logo = function (frm, r) {
	// First get company logo
	frappe.call({
		method: "singapore_compliance.singapore_compliance.doctype.official_receipt.official_receipt.get_company_logo",
		args: {
			company: frm.doc.company,
		},
		callback: (logo_response) => {
			let company_logo = logo_response.message || "/files/KGS-Logo.png";
			let html = get_html(frm, r, company_logo);
			console.log(html);
			frappe.render_pdf(html, { orientation: "Portrait" });
		},
	});
};

let get_html = function (frm, r, company_logo) {
	// Check if response has data
	if (!r) {
		return "<p>No data available</p>";
	}

	let html = `
	<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">
	<style>
    .page-break{ display: block; page-break-before: always; }
    .lhead{
	font-size:10px;
	margin-top:0px;
	margin-bottom:0px !important;
	vertical-align: top !important;
	}
	*{
		font-family: 'IBM Plex Sans', sans-serif !important;
	}
	.blhead{
	font-weight:600 ;
	font-size:8px;
	vertical-align: top !important;
	}
    p{
        font-size: 13px;
    }
	.print-format {
		margin-left: 4mm;
		margin-right: 4mm;
	}
	.print-format .letterhead td, .print-format th {
	padding: 0 0px 0 0px !important;
	vertical-align: top !important;
	margin:0px !important;
	}
	.print-format p{
	margin:0px 0px 2px;
	}
	.print-format .letter-head {
	margin-bottom: 0px;
	padding-top:5px;
	}
	.container p{
		margin-bottom:2px;
	}
	.onbottom{
		border-bottom : 1px solid black;
	}
	.ontop{
		border-top : 1px solid black;
	}
	.address-sec{
		margin-top:0px;
		margin-bottom:0px !important;
	}
	.left_dotted {
		border-left: 2px dotted !important;
	  }
</style>
<table width="100%">
<tbody>
    <tr>
        <td width="10%">
            <img height="60" src="${company_logo}" width="60">
        </td>
        <td width="21%">
            <p class="lhead"><b class="blhead">KGS Pte Ltd</b>
            </p>
            <p class="lhead">8 Tuas South Lane,</p>
            <p class="lhead">#01-71, Factory 4,</p>
            <p class="lhead">Singapore 637302</p>
        </td>
        <td width="32%">
            <br>
            <p class="lhead"><b class="blhead">Web:</b>KGS Pte Ltd</p>
            <p class="lhead"><b class="blhead">UEN/GST No:</b> 201607799N</p>
        </td>
        <td >
            <b style="font-size: 20px; text-transform: uppercase;">
            OFFICIAL RECEIPT
            </b>
        </td>
    </tr>
</tbody>
</table>
<hr>
<table width="100%" class="cust_head">
	<tbody>
		<tr>
			<td>
				<p class="address-sec">${safeGet(r.data && r.data[0] ? r.data[0].party : "")}</p>
				<p class="address-sec">${safeGet(r.address ? r.address.address_line1 : "")}</p>
				<p class="address-sec">${safeGet(
					r.address && r.address.address_line2 ? r.address.address_line2 : ""
				)}</p>
				<p class="address-sec">${safeGet(r.address ? r.address.city : "")}${
		r.address && r.address.city && r.address.country ? ", " : ""
	}${safeGet(r.address ? r.address.country : "")}${
		r.address && r.address.pincode ? ", " : ""
	}${safeGet(r.address ? r.address.pincode : "")}</p>
			</td>
			<td>
				<p class="address-sec">Currency : ${safeGet(r.currency)}</p>
				<p class="address-sec">Payment Terms : ${safeGet(r.payment_terms)}</p>
				<p class="address-sec">Payment Amount : </p>
			</td>
			<td class="left_dotted">
				<p class="address-sec" style="padding-left:10px;">Voucher No : ${safeGet(frm.doc.name)}</p>
				<p class="address-sec" style="padding-left:10px;">Cheque No : </p>
				<p class="address-sec" style="padding-left:10px;">Date : </p>
			</td>
		</tr>
	</tbody>
</table>
<hr style="border-top: dotted 1px;" />
<table width="100%" style="border-spacing: 0px;">
	  <tbody>
	  	<tr>
	  		<td class="onbottom">
	  			<p>Doc Date</p>
			</td>
			<td class="onbottom">
	  			<p>Doc No</p>
			</td>
			<td class="onbottom">
	  			<p>Reference</p>
			</td>
			<td class="onbottom" align="right">
	  			<p>Invoice Total</p>
			</td class="onbottom">
			<td class="onbottom" align="right">
	  			<p>Amount</p>
			</td>
			<td class="onbottom" align="right">
	  			<p>Balance</p>
			</td>
		<tr>
		`;
	if (r.data && Array.isArray(r.data)) {
		r.data.forEach((e) => {
			html += `<tr>
						<td>
							<p>${safeGet(e.posting_date)}</p>
						</td>
						<td>
							<p>${safeGet(e.name)}</p>
						</td>
						<td>
							<p>${safeGet(e.reference_name)}</p>
						</td>
						<td align="right">
							<p>${safeGet(e.total_amount, 0)}</p>
						</td>
						<td align="right">
							<p>${safeGet(e.allocated_amount, 0)}</p>
						</td>
						<td align="right">
							<p>${safeGet(e.outstanding_amount, 0)}</p>
						</td>
					</tr>`;
		});
	}
	html += `<tr>
			<td colspan = '4' class="ontop">
				<b style="font-size:13px;">In Words</b>
				</td>
			<td colspan='2' class="ontop" align="right">
				<b style="font-size:13px;">Total Due</b>
			</td>
	</tr>`;

	html += `</tbody>
			</table>
				`;

	html += `
	<div id="footer-html" class="visible-print" style="padding-top:0rem; !important;">
		<div class="letter-head-footer">
			<table width="100%">
				<tr style ="line-height:50mm;">
					<td width="65%"></td>
					<td>
						<p align="left">Received by:</p>
					</td>
				</tr>
				<tr>
					<td width="65%"></td>
					<td style="border-top:1px solid black;">
						<p align="right">SIGNATURE / COMPANY STAMP & DATE</p>
					</td>
				</tr>
			</table>
		</div>
	</div>

	`;
	return html;
};
