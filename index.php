<?php
/**
 * index.php — Unified Tax Form PDF Filler (W-9, W-8BEN, W-8BEN-E)
 */

define('OUTPUT_DIR',    __DIR__ . '/filled/');
define('PYTHON_SCRIPT', __DIR__ . '/fill_pdf.py');
// define('SIGNATURE_IMG', __DIR__ . '/sample_signature.png');

if (!is_dir(OUTPUT_DIR)) mkdir(OUTPUT_DIR, 0755, true);

// ─── Templates ──────────────────────────────────────────────────────────────
$TEMPLATES = [
    'w9'  => __DIR__ . '/fw9_new.pdf',
    'w8i' => __DIR__ . '/W8forIndividuals.pdf',
    'w8e' => __DIR__ . '/W8forEntities.pdf',
];

// ─── Helpers ─────────────────────────────────────────────────────────────────
function post(string $key, $default = ''): string {
    return isset($_POST[$key]) ? trim(strip_tags((string)$_POST[$key])) : (string)$default;
}
function h(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}

function generate_pdf(string $form_type, array $fields, string $output_path): array {
    global $TEMPLATES;
    if (!isset($TEMPLATES[$form_type])) return ['success' => false, 'output' => 'Invalid form type.'];

    $tmp_json = tempnam(sys_get_temp_dir(), 'tax_') . '.json';
    file_put_contents($tmp_json, json_encode($fields));

    $script = escapeshellarg(PYTHON_SCRIPT);
    $blank  = escapeshellarg($TEMPLATES[$form_type]);
    $json   = escapeshellarg($tmp_json);
    $out    = escapeshellarg($output_path);
    $sig    = isset($fields['signature_url']) ? escapeshellarg($fields['signature_url']) : '""';
    $type   = escapeshellarg($form_type);

    // Try absolute python path first (common for WAMP service)
    $py_path = 'C:\Python314\python.exe';
    $cmd = "{$py_path} {$script} {$blank} {$json} {$out} {$sig} {$type} 2>&1";
    $result = (string)shell_exec($cmd);
    
    if (!file_exists($output_path) || filesize($output_path) === 0) {
        // Fallback to generic 'python'
        $cmd_fallback = "python {$script} {$blank} {$json} {$out} {$sig} {$type} 2>&1";
        $result .= "\nFallback (python): " . (string)shell_exec($cmd_fallback);
    }

    @unlink($tmp_json);
    $success = file_exists($output_path) && filesize($output_path) > 0;
    return ['success' => $success, 'output' => $result];
}

// ─── Form Processing ─────────────────────────────────────────────────────────
$errors = [];
$submitted = ($_SERVER['REQUEST_METHOD'] === 'POST');

if ($submitted) {
    $form_type = post('form_type', 'w9');
    $xfa_fields = [];

    if ($form_type === 'w9') {
        $xfa_fields = [
            'f1_01' => post('w9_name'),
            'f1_02' => post('w9_business_name'),
            'f1_07' => post('w9_address'),
            'f1_08' => post('w9_city_state_zip'),
            'f1_11' => post('w9_ssn1'),
            'f1_12' => post('w9_ssn2'),
            'f1_13' => post('w9_ssn3'),
            'c1_1'  => post('w9_classification', '1'),
            'signature_url' => post('w9_signature_url'),
        ];
    } elseif ($form_type === 'w8i') {
        $xfa_fields = [
            'f_1'  => post('w8i_name'),
            'f_2'  => post('w8i_country'),
            'f_3'  => post('w8i_address'),
            'f_4'  => post('w8i_city'),
            'f_5'  => post('w8i_zip_country'),
            'f_9'  => post('w8i_tin'),
            'f_13' => post('w8i_dob'),
        ];
    } elseif ($form_type === 'w8e') {
        $xfa_fields = [
            'f1_1'  => post('w8e_name'),
            'f1_2'  => post('w8e_country'),
            'f1_7'  => post('w8e_address'),
            'f1_8'  => post('w8e_city_zip'),
            'f1_11' => post('w8e_tin'),
            'c1_1'  => post('w8e_ch3_status', '1'),
            'c1_2'  => post('w8e_ch4_status', '1'),
        ];
    }

    if (empty($xfa_fields[array_key_first($xfa_fields)])) {
        $errors['_global'] = "Please fill in at least the primary name field.";
    }

    if (empty($errors)) {
        $filename = OUTPUT_DIR . 'tax_form_' . uniqid() . '.pdf';
        $gen_result = generate_pdf($form_type, $xfa_fields, $filename);
        
        if ($gen_result['success']) {
            header('Content-Type: application/pdf');
            header('Content-Disposition: attachment; filename="'.$form_type.'_Generated.pdf"');
            header('Content-Length: ' . filesize($filename));
            readfile($filename);
            @unlink($filename);
            exit;
        } else {
            $errors['_global'] = "PDF generation failed. <br><pre style='background:#000; color:#0f0; padding:10px; margin-top:10px'>" . h($gen_result['output']) . "</pre>";
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Unified Tax Form Filler</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 40px auto; background: #f8f9fa; color: #333; padding: 20px; }
        .card { background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        h1 { color: #003087; text-align: center; margin-bottom: 30px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 25px; border-bottom: 2px solid #eee; }
        .tab { padding: 12px 24px; cursor: pointer; border-radius: 8px 8px 0 0; background: #eee; font-weight: 600; transition: 0.3s; }
        .tab.active { background: #003087; color: #fff; }
        .form-section { display: none; }
        .form-section.active { display: block; }
        .row { margin-bottom: 15px; }
        label { display: block; font-weight: 600; margin-bottom: 6px; font-size: 14px; }
        input[type=text], select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
        .btn { display: block; width: 100%; padding: 15px; background: #003087; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer; margin-top: 20px; }
        .btn:hover { background: #00256a; }
        .alert { background: #fee; color: #900; padding: 15px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #fcc; }
    </style>
</head>
<body>

<div class="card">
    <h1>Tax Form Generator</h1>

    <?php if (!empty($errors['_global'])): ?>
        <div class="alert"><?= $errors['_global'] ?></div>
    <?php endif; ?>

    <form method="POST">
        <input type="hidden" name="form_type" id="form_type" value="w9">

        <div class="tabs">
            <div class="tab active" onclick="switchForm('w9')">Form W-9</div>
            <div class="tab" onclick="switchForm('w8i')">W-8BEN (Indiv)</div>
            <div class="tab" onclick="switchForm('w8e')">W-8BEN-E (Entity)</div>
        </div>

        <!-- W-9 Section -->
        <div id="section_w9" class="form-section active">
            <div class="row">
                <label>Legal Name</label>
                <input type="text" name="w9_name" placeholder="As shown on tax return">
            </div>
            <div class="row">
                <label>Business Name (Optional)</label>
                <input type="text" name="w9_business_name">
            </div>
            <div class="row">
                <label>Classification</label>
                <select name="w9_classification">
                    <option value="1">Individual / Sole Proprietor</option>
                    <option value="2">C Corporation</option>
                    <option value="3">S Corporation</option>
                </select>
            </div>
            <div class="row">
                <label>Address</label>
                <input type="text" name="w9_address">
            </div>
            <div class="row">
                <label>City, State, ZIP</label>
                <input type="text" name="w9_city_state_zip">
            </div>
            <div class="row">
                <label>SSN (X-X-X)</label>
                <div style="display:flex; gap:5px">
                    <input type="text" name="w9_ssn1" maxlength="3" style="width:60px">
                    <input type="text" name="w9_ssn2" maxlength="2" style="width:50px">
                    <input type="text" name="w9_ssn3" maxlength="4" style="width:80px">
                </div>
            </div>
            <div class="row">
                <label>Signature URL (Optional)</label>
                <input type="text" name="w9_signature_url" placeholder="http://localhost:8080/path/to/sig.png">
            </div>
        </div>

        <!-- W-8BEN Section -->
        <div id="section_w8i" class="form-section">
            <div class="row">
                <label>Name of Individual</label>
                <input type="text" name="w8i_name">
            </div>
            <div class="row">
                <label>Country of Citizenship</label>
                <input type="text" name="w8i_country">
            </div>
            <div class="row">
                <label>Permanent Residence Address</label>
                <input type="text" name="w8i_address" placeholder="Street Address">
            </div>
            <div class="row">
                <input type="text" name="w8i_city" placeholder="City or town, state or province">
            </div>
            <div class="row">
                <input type="text" name="w8i_zip_country" placeholder="ZIP or postal code, country">
            </div>
            <div class="row">
                <label>Foreign TIN</label>
                <input type="text" name="w8i_tin">
            </div>
            <div class="row">
                <label>Date of Birth (MM-DD-YYYY)</label>
                <input type="text" name="w8i_dob">
            </div>
        </div>

        <!-- W-8BEN-E Section -->
        <div id="section_w8e" class="form-section">
            <div class="row">
                <label>Name of Organization</label>
                <input type="text" name="w8e_name">
            </div>
            <div class="row">
                <label>Country of Incorporation</label>
                <input type="text" name="w8e_country">
            </div>
            <div class="row">
                <label>Permanent Residence Address</label>
                <input type="text" name="w8e_address" placeholder="Street, apt., or suite no.">
            </div>
            <div class="row">
                <input type="text" name="w8e_city_zip" placeholder="City, state, country, ZIP">
            </div>
            <div class="row">
                <label>U.S. TIN (EIN)</label>
                <input type="text" name="w8e_tin">
            </div>
            <div class="row">
                <label>Chapter 3 Status</label>
                <select name="w8e_ch3_status">
                    <option value="1">Corporation</option>
                    <option value="2">Partnership</option>
                </select>
            </div>
        </div>

        <button type="submit" class="btn">Generate Signed PDF</button>
    </form>
</div>

<script>
    function switchForm(type) {
        document.getElementById('form_type').value = type;
        
        // Update tabs
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');

        // Update sections
        document.querySelectorAll('.form-section').forEach(s => s.classList.remove('active'));
        document.getElementById('section_' + type).classList.add('active');
    }
</script>

</body>
</html>
