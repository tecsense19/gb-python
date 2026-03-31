import os, sys, json, uuid, requests, tempfile, datetime
from pathlib import Path

# Required libraries to install on live server:
# pip install flask pypdf requests reportlab

# Add local 'lib' directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(BASE_DIR, 'lib')
if os.path.exists(LIB_PATH) and LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

from flask import Flask, render_template, request, send_file, Response
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject
import logging

# Import our existing PDF generation logic
import fill_pdf

app = Flask(__name__)

# Configuration
TEMPLATES = {
    'w9':  os.path.join(BASE_DIR, 'fw9_new.pdf'),
    'w8i': os.path.join(BASE_DIR, 'W8forIndividuals.pdf'),
    'w8e': os.path.join(BASE_DIR, 'W8forEntities.pdf'),
}
OUTPUT_DIR = os.path.join(BASE_DIR, 'filled')
# Set up logging to generate a log file on the server
log_file_path = os.path.join(BASE_DIR, 'app_server.log')
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Also print to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logging.getLogger('').addHandler(console)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    logging.info("--- NEW REQUEST RECEIVED ---")
    for key, value in request.form.items():
        logging.info(f"FORM DATA: {key} = {value}")
    
    # Get signature path/URL and ensure it's not a placeholder like 'None' or empty
    raw_sig_path = request.form.get('signature_company', '').strip()
    # raw_sig_path = "https://tec-sense.co.in/glassbox_portal/uploads/signatures/sig_69bbf1a80401b.png"
    SIGNATURE_PATH = raw_sig_path if raw_sig_path.lower() not in ['', 'none', 'undefined', 'null'] else ''
    
    logging.info(f"DEBUG: SIGNATURE_PATH = '{SIGNATURE_PATH}'")
    
    form_type = request.form.get('form_type', 'w9')
    fields = {}
    address_line1 = (request.form.get('owner_street_address', '') + (', ' + request.form.get('owner_address_line2') if request.form.get('owner_address_line2') else ''))
    city_state1 = ((request.form.get('owner_city', '')) +(', ' + request.form.get('owner_state') if request.form.get('owner_state') else '') +(' ' + request.form.get('owner_zip_code') if request.form.get('owner_zip_code') else ''))
    city_state = ((request.form.get('city', '')) +(', ' + request.form.get('state') if request.form.get('state') else '') +(' ' + request.form.get('zip_code') if request.form.get('zip_code') else ''))
    if form_type == 'w8i':
        w8i_address_line1 = (request.form.get('street1', '') + (', ' + request.form.get('street2') if request.form.get('street2') else ''))
        w8i_city_state = ((request.form.get('owner_city', '')) +(', ' + request.form.get('owner_state') if request.form.get('owner_state') else '') +(' ' + request.form.get('woner_zip_code') if request.form.get('woner_zip_code') else ''))
        
        address_line2 = (request.form.get('address_line1', '') + (', ' + request.form.get('address_line2') if request.form.get('address_line2') else ''))
        city_state2 = ((request.form.get('city2', '')) +(', ' + request.form.get('state2') if request.form.get('state2') else '') +(' ' + request.form.get('zip_code2') if request.form.get('zip_code2') else ''))

    if form_type == 'w9':
        import re
        
        entity_val = request.form.get('legal_designation')
        raw_tax_id = request.form.get('txt_id') or request.form.get('tax_id', '')
        
        ssn_part1, ssn_part2, ssn_part3 = "", "", ""
        ein_part1, ein_part2 = "", ""

        # First resolve the parts based on whether there are hyphens
        parts = raw_tax_id.split('-')
        if len(parts) == 3:
            s_part1, s_part2, s_part3 = parts[0], parts[1], parts[2]
            e_part1, e_part2 = "".join(parts)[:2], "".join(parts)[2:9]
        elif len(parts) == 2:
            s_part1, s_part2, s_part3 = "".join(parts)[:3], "".join(parts)[3:5], "".join(parts)[5:9]
            e_part1, e_part2 = parts[0], parts[1]
        else:
            clean_tax_id = re.sub(r'\D', '', raw_tax_id) if raw_tax_id else ''
            s_part1, s_part2, s_part3 = clean_tax_id[:3], clean_tax_id[3:5], clean_tax_id[5:9]
            e_part1, e_part2 = clean_tax_id[:2], clean_tax_id[2:9]

        if entity_val == 'Single Person':
            mapped_entity = 'individual'
            ssn_part1, ssn_part2, ssn_part3 = s_part1, s_part2, s_part3
        elif entity_val in ['Entity', 'Entity / Corporation']:
            mapped_entity = 'c-corporation'
            ein_part1, ein_part2 = e_part1, e_part2
        elif entity_val == 'Trust':
            mapped_entity = 'trust'
            ein_part1, ein_part2 = e_part1, e_part2
        else:
            mapped_entity = entity_val.lower() if entity_val else ''
            ein_part1, ein_part2 = e_part1, e_part2

        fields = {
            'f1_01': request.form.get('legal_name'),
            'f1_02': '',
            'f1_04': '',
            'f1_05': '',
            'f1_06': '',
            'f1_07': request.form.get('street_address', ''),
            'f1_08': city_state,
            'f1_09': '',
            'f1_10': '',
            'f1_11': ssn_part1,
            'f1_12': ssn_part2,
            'f1_13': ssn_part3,
            'f1_14': ein_part1,
            'f1_15': ein_part2,

            # 'f1_01': 'f1 value',
            # 'f1_02': 'f2 value',
            # 'f1_04': 'f4 value',
            # 'f1_05': 'f5 value',
            # 'f1_06': 'f6 value',
            # 'f1_07': 'f7 value',
            # 'f1_08': 'f8 value',
            # 'f1_09': 'f9 value',
            # 'f1_10': 'f10 value',
            # 'f1_11': "f11 value",
            # 'f1_12': "f12 value",
            # 'f1_13': 'f13 value',
        }

        if mapped_entity == 'c-corporation':
            fields['f1_03'] = 'C'
        elif mapped_entity == 's-corporation':
            fields['f1_03'] = 'S'
        elif mapped_entity == 'partnership':
            fields['f1_03'] = 'P'
        else:
            fields['f1_03'] = ''

        entity_map = {
            'individual': 'c1_1',
            'c-corporation': 'c1_2',
            's-corporation': 'c1_3',
            'partnership': 'c1_4',
            'trust': 'c1_5',
            'Limited Liability Company': 'c1_6',
            'other': 'c1_7'
        }

        for key in entity_map.values():
            fields[key] = ''

        if mapped_entity in entity_map:
            fields[entity_map[mapped_entity]] = 1
        elif entity_val and entity_val.lower() in entity_map:
            fields[entity_map[entity_val.lower()]] = 1
    elif form_type == 'w8i':
        fields = {
            # 'f_1':  'f1_value',
            # 'f_2':  'f2_value',
            # 'f_3':  'f3_value',
            # 'f_4':  'f4_value',
            # 'f_5':  'f5_value',
            # 'f_6':  'f6_value',
            # 'f_7':  'f7_value',
            # 'f_8':  'f8_value',
            # 'f_9':  'f9_value',
            # 'f_10': 'f10_value',
            # 'f_11': 'f11_value',
            # 'f_12': 'f12_value',
            # 'f_13': 'f13_value',
            # 'f_14': 'f14_value',
            # 'f_15': 'f15_value',
            # 'f_16': 'f16_value',
            # 'f_17': 'f17_value',
            # 'f_18': 'f18_value',
            # 'f_19': 'f19_value',
            # 'f_20': 'f20_value',
            # 'f_21': 'f23_value',
            # 'f_22': 'f22_value',
            # 'f_23': 'f23_value',

            'f_1':  request.form.get('legal_name'),
            'f_2':  request.form.get('citizanship') if request.form.get('citizanship') else 'US',
            'f_3':  request.form.get('street_address', ''),
            'f_4':  w8i_city_state,
            'f_5':  request.form.get('country') if request.form.get('country') else 'US',
            'f_6':  address_line2 if address_line2 else '',
            'f_7':  city_state2 if city_state2 else '',
            'f_8':  request.form.get('country2') if request.form.get('country2') else '',
            'f_9':  request.form.get('txt_id') or request.form.get('tax_id', ''),
            'f_10': '',
            'f_11': request.form.get('ref_number') if request.form.get('ref_number') else '',
            'f_12': request.form.get('dob') if request.form.get('dob') else '',
            # “The commented fields should be filled manually by the company.”
            # 'f_13': '', 
            # 'f_14': '',
            # 'f_15': '',
            # 'f_16': '',
            # 'f_17': '',
            # 'f_18': '',
            # 'f_19': '',
            # 'f_20': '',

            'f_20': '',
            'Date': datetime.datetime.now().strftime("%m-%d-%Y"),
            'f_21': request.form.get('legal_name'),
        }
    elif form_type == 'w8e':
        fields = {
            'f1_1':  request.form.get('legal_name'),
            'f1_2':  request.form.get('owner_country') if request.form.get('owner_country') else 'US',
            'f1_3':  request.form.get('company_name'),
            'f1_4':  address_line1,
            'f1_5':  city_state1,
            'f1_6':  request.form.get('owner_country') if request.form.get('owner_country') else 'US',
            'f1_7':  '',
            'f1_8':  '',
            'f1_9':  '',
            'f1_10': '',
            'f1_11': '',
            'f1_12': '',
            'f1_13': '',
            'f8_31': request.form.get('legal_name'),
            'f8_32': datetime.datetime.now().strftime("%m-%d-%Y"),
            # Those filed are filled by the comapny staff
            # 'f2_1':  'f2_1value',
            # 'f2_2':  'f2_2value',
            # 'f2_3':  'f2_3value',
            # 'f2_4':  'f2_4value',
            # 'f2_5':  'f2_5value',
            # 'f2_6':  'f2_6value',
            # 'f2_7':  'f2_7value',
            # 'f2_8':  'f2_8value',
            # 'f2_9':  'f2_9value',
            # 'f2_10': 'f2_10value',
            # 'f2_11': 'f2_11value',
            # 'f2_12': 'f2_12value',
            # 'f2_13': 'f2_13value',
            
            # 'f3_1':  'f3_1value',
            
            # 'f5_01': 'f5_01value',
            # 'f5_2':  'f5_2value',
            # 'f5_03': 'f5_03value',
            
            # 'f6_1':  'f6_1value',
            # 'f6_2':  'f6_2value',
            
            # 'f7_1':  'f7_1value',
            # 'f7_2':  'f7_2value',
            # 'f7_3':  'f7_3value',
            # 'f7_4':  'f7_4value',
            
            # 'f8_1':  'f8_1value',
            # 'f8_3':  'f8_3value',
            # 'f8_4':  'f8_4value',
            # 'f8_5':  'f8_5value',
            # 'f8_6':  'f8_6value',
            # 'f8_7':  'f8_7value',
            # 'f8_8':  'f8_8value',
            # 'f8_9':  'f8_9value',
            # 'f8_10': 'f8_10value',
            # 'f8_11': 'f8_11value',
            # 'f8_12': 'f8_12value',
            # 'f8_13': 'f8_13value',
            # 'f8_14': 'f8_14value',
            # 'f8_15': 'f8_15value',
            # 'f8_16': 'f8_16value',
            # 'f8_17': 'f8_17value',
            # 'f8_18': 'f8_18value',
            # 'f8_19': 'f8_19value',
            # 'f8_20': 'f8_20value',
            # 'f8_21': 'f8_21value',
            # 'f8_22': 'f8_22value',
            # 'f8_23': 'f8_23value',
            # 'f8_24': 'f8_24value',
            # 'f8_25': 'f8_25value',
            # 'f8_26': 'f8_26value',
            # 'f8_27': 'f8_27value',
            # 'f8_28': 'f8_28value',
            # 'f8_29': 'f8_29value',
            # 'f8_30': 'f8_30value',
            # 'f8_31': 'f8_31value',
            # 'f8_32': 'f8_32value',
        }

        # Question 4: Chapter 3 Status (14 options: c1_1 to c1_14)
        for i in range(1, 15):
            val = request.form.get(f'c1_{i}')
            if val:
                if i <= 12:
                    fields[f'topmostSubform[0].Page1[0].c1_1[{i-1}]'] = val
                else:
                    fields[f'topmostSubform[0].Page1[0].c1_2[{i-13}]'] = val
        
        w8e_entity_val = request.form.get('legal_designation')
        if w8e_entity_val in ['Entity', 'Entity / Corporation']:
            fields['topmostSubform[0].Page1[0].c1_1[0]'] = 1

        # Question 5: Chapter 4 Status (FATCA status) (32 options: c2_1 to c2_32)
        for i in range(1, 33):
            val = request.form.get(f'c2_{i}')
            if val:
                if i <= 13:
                    fields[f'topmostSubform[0].Page1[0].Col1[0].c1_3[{i-1}]'] = val
                else:
                    fields[f'topmostSubform[0].Page1[0].Col2[0].c1_3[{i-14}]'] = val

        # Question 11: (5 options: c3_1 to c3_5)
        for i in range(1, 6):
            val = request.form.get(f'c3_{i}')
            if val:
                fields[f'topmostSubform[0].Page2[0].c2_1[{i-1}]'] = val

        # Question 14: Claim of Tax Treaty Benefits
        if request.form.get('c4_a'):
            fields['topmostSubform[0].Page2[0].c2_2[0]'] = request.form.get('c4_a')
        
        if request.form.get('c4_b'):
            fields['topmostSubform[0].Page2[0].c2_3[0]'] = request.form.get('c4_b')
            
        for i in range(1, 11):
            val = request.form.get(f'c4_b_{i}')
            if val:
                fields[f'topmostSubform[0].Page2[0].c2_4[{i-1}]'] = val
                
        if request.form.get('c4_c'):
            fields['topmostSubform[0].Page2[0].c2_5[0]'] = request.form.get('c4_c')

        # ALL REMAINING CHECKBOXES
        w8e_other_checkboxes = {
            "p2_c2_6_1": "topmostSubform[0].Page2[0].c2_6[0]",
            "p2_c2_6_2": "topmostSubform[0].Page2[0].c2_6[1]",
            "p3_c3_1_1": "topmostSubform[0].Page3[0].c3_1[0]",
            "p3_c3_2_1": "topmostSubform[0].Page3[0].c3_2[0]",
            "p3_c3_3_1": "topmostSubform[0].Page3[0].c3_3[0]",
            "p3_c3_4_1": "topmostSubform[0].Page3[0].c3_4[0]",
            "p3_c3_5_1": "topmostSubform[0].Page3[0].c3_5[0]",
            "p3_c3_6_1": "topmostSubform[0].Page3[0].c3_6[0]",
            "p4_c4_1_1": "topmostSubform[0].Page4[0].c4_1[0]",
            "p4_c4_1_2": "topmostSubform[0].Page4[0].c4_1[1]",
            "p4_c4_2_1": "topmostSubform[0].Page4[0].c4_2[0]",
            "p4_c4_3_1": "topmostSubform[0].Page4[0].c4_3[0]",
            "p4_c4_4_1": "topmostSubform[0].Page4[0].c4_4[0]",
            "p4_c4_4_2": "topmostSubform[0].Page4[0].c4_4[1]",
            "p5_c5_1_1": "topmostSubform[0].Page5[0].c5_1[0]",
            "p5_c5_2_1": "topmostSubform[0].Page5[0].BulletedList1[0].Bullet1[0].c5_2[0]",
            "p5_c5_2_2": "topmostSubform[0].Page5[0].BulletedList1[0].Bullet1[0].c5_2[1]",
            "p5_c5_3_1": "topmostSubform[0].Page5[0].BulletedList1[0].Bullet2[0].c5_3[0]",
            "p5_c5_3_2": "topmostSubform[0].Page5[0].BulletedList1[0].Bullet2[0].c5_3[1]",
            "p5_c5_4_1": "topmostSubform[0].Page5[0].c5_4[0]",
            "p5_c5_5_1": "topmostSubform[0].Page5[0].c5_5[0]",
            "p5_c5_5_2": "topmostSubform[0].Page5[0].c5_5[1]",
            "p5_c5_6_1": "topmostSubform[0].Page5[0].c5_6[0]",
            "p5_c5_6_2": "topmostSubform[0].Page5[0].c5_6[1]",
            "p5_c5_6_3": "topmostSubform[0].Page5[0].c5_6[2]",
            "p6_c5_6_1": "topmostSubform[0].Page6[0].c5_6[0]",
            "p6_c5_6_2": "topmostSubform[0].Page6[0].c5_6[1]",
            "p6_c5_6_3": "topmostSubform[0].Page6[0].c5_6[2]",
            "p6_c6_1_1": "topmostSubform[0].Page6[0].c6_1[0]",
            "p6_c6_2_1": "topmostSubform[0].Page6[0].c6_2[0]",
            "p6_c6_3_1": "topmostSubform[0].Page6[0].c6_3[0]",
            "p6_c6_4_1": "topmostSubform[0].Page6[0].c6_4[0]",
            "p6_c6_5_1": "topmostSubform[0].Page6[0].c6_5[0]",
            "p7_c7_1_1": "topmostSubform[0].Page7[0].c7_1[0]",
            "p7_c7_2_1": "topmostSubform[0].Page7[0].c7_2[0]",
            "p7_c7_3_1": "topmostSubform[0].Page7[0].c7_3[0]",
            "p7_c7_3_2": "topmostSubform[0].Page7[0].c7_3[1]",
            "p7_c7_4_1": "topmostSubform[0].Page7[0].c7_4[0]",
            "p7_c7_5_1": "topmostSubform[0].Page7[0].c7_5[0]",
            "p7_c7_6_1": "topmostSubform[0].Page7[0].c7_6[0]",
            "p7_c7_7_1": "topmostSubform[0].Page7[0].c7_7[0]",
            "p7_c7_7_2": "topmostSubform[0].Page7[0].c7_7[1]",
            "p8_c8_1_1": "topmostSubform[0].Page8[0].c8_1[0]",
            "p8_c8_2_1": "topmostSubform[0].Page8[0].c8_2[0]",
            "p8_c8_3_1": "topmostSubform[0].Page8[0].c8_3[0]"
        }
        for attr, xfa_path in w8e_other_checkboxes.items():
            if request.form.get(attr):
                fields[xfa_path] = request.form.get(attr)


    template_path = TEMPLATES.get(form_type)
    if not template_path or not os.path.exists(template_path):
        return f"Error: Template for {form_type} not found.", 404

    output_filename = f"{form_type}_{uuid.uuid4()}.pdf"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        # Load reader and writer
        reader = PdfReader(template_path)
        writer = PdfWriter()
        writer.clone_reader_document_root(reader)

        # Fill XFA
        fill_pdf.fill_xfa(writer, fields)

        # Add Signature
        temp_sig_path = None
        try:
            if SIGNATURE_PATH.startswith(('http://', 'https://')):
                # Download to temp file
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                response = requests.get(SIGNATURE_PATH, stream=True, headers=headers)
                if response.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                        for chunk in response.iter_content(chunk_size=8192):
                            tmp.write(chunk)
                        temp_sig_path = tmp.name
                else:
                    logging.error(f"Failed to download signature. HTTP Status: {response.status_code}")
                
                if temp_sig_path and os.path.exists(temp_sig_path):
                    fill_pdf.add_signature(writer, temp_sig_path, form_type)
            elif os.path.exists(SIGNATURE_PATH):
                fill_pdf.add_signature(writer, SIGNATURE_PATH, form_type)
        finally:
            # Clean up temp file
            if temp_sig_path and os.path.exists(temp_sig_path):
                os.remove(temp_sig_path)

        # Save output
        with open(output_path, 'wb') as f:
            writer.write(f)

        return send_file(output_path, as_attachment=True, download_name=f"{form_type}_Generated.pdf")
    except Exception as e:
        return f"PDF Generation Failed: {str(e)}", 500


if __name__ == '__main__':
    # Run server on port 5000
    print(f"Starting Native Python Tax Form Generator on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
