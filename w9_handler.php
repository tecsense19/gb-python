<?php
/**
 * w9_handler.php — W-9 PDF Filler (PHP form + Python PDF engine)
 *
 * WHY PYTHON IS REQUIRED:
 *   The IRS W-9 is an XFA PDF. When stream data changes size, the PDF's
 *   cross-reference (xref) table must be rebuilt — otherwise Adobe Reader
 *   cannot locate the updated objects and shows blank fields.
 *   pypdf (Python) handles xref rebuilding automatically. Pure PHP cannot
 *   do this without reimplementing a full PDF writer.
 *
 * SETUP:
 *   1. pip install pypdf
 *   2. Place fill_w9.py + fw9_blank.pdf + this file + filled/ in same folder
 *   3. chmod 755 filled/
 *   4. Open w9_handler.php in browser
 *
 * REQUIREMENTS:
 *   PHP 7.4+  |  Python 3.7+  |  pypdf (pip install pypdf)
 */

define('BLANK_PDF',     __DIR__ . '/fw9_blank.pdf');
define('OUTPUT_DIR',    __DIR__ . '/filled/');
define('PYTHON_SCRIPT', __DIR__ . '/fill_w9.py');

if (!is_dir(OUTPUT_DIR)) mkdir(OUTPUT_DIR, 0755, true);

// ─── Helpers ─────────────────────────────────────────────────────────────────
function post(string $key, string $default = ''): string {
    return isset($_POST[$key]) ? trim(strip_tags($_POST[$key])) : $default;
}
function h(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}

// ─── PDF Filler ───────────────────────────────────────────────────────────────
function fill_w9(array $xfa_fields, string $output_path): bool
{
    // Write fields to temp JSON
    $tmp_json = tempnam(sys_get_temp_dir(), 'w9_') . '.json';
    file_put_contents($tmp_json, json_encode($xfa_fields, JSON_PRETTY_PRINT));

    $script = escapeshellarg(PYTHON_SCRIPT);
    $blank  = escapeshellarg(BLANK_PDF);
    $json   = escapeshellarg($tmp_json);
    $out    = escapeshellarg($output_path);

    // Try python3 first, fall back to python
    $cmd    = "python3 {$script} {$blank} {$json} {$out} 2>&1";
    $result = shell_exec($cmd);

    if (!file_exists($output_path) || filesize($output_path) === 0) {
        // Try with 'python' command
        $cmd    = "python {$script} {$blank} {$json} {$out} 2>&1";
        $result = shell_exec($cmd);
    }

    @unlink($tmp_json);

    $ok = file_exists($output_path) && filesize($output_path) > 0;
    if (!$ok) error_log('W9 fill failed: ' . $result);
    return $ok;
}

// ─── Validation & Submission ──────────────────────────────────────────────────
$errors    = [];
$submitted = ($_SERVER['REQUEST_METHOD'] === 'POST');

if ($submitted) {
    $name            = post('name');
    $business_name   = post('business_name');
    $tax_class       = post('tax_classification');
    $llc_type        = post('llc_type');
    $other_desc      = post('other_description');
    $exempt_code     = post('exempt_payee_code');
    $fatca_code_val  = post('fatca_code');
    $address         = post('address');
    $city_state_zip  = post('city_state_zip');
    $requester_info  = post('requester_info');
    $account_numbers = post('account_numbers');
    $tax_id_type     = post('tax_id_type');
    $ssn1 = post('ssn1'); $ssn2 = post('ssn2'); $ssn3 = post('ssn3');
    $ein1 = post('ein1'); $ein2 = post('ein2');

    if (empty($name))           $errors['name']        = 'Full name is required.';
    if (empty($address))        $errors['address']     = 'Address is required.';
    if (empty($city_state_zip)) $errors['city']        = 'City, state, and ZIP are required.';
    if (!in_array($tax_id_type, ['ssn','ein']))
                                $errors['tin_type']    = 'Please select SSN or EIN.';
    if ($tax_id_type === 'ssn' && (
            !preg_match('/^\d{3}$/',$ssn1) ||
            !preg_match('/^\d{2}$/',$ssn2) ||
            !preg_match('/^\d{4}$/',$ssn3)))
                                $errors['ssn']         = 'Enter a valid 9-digit SSN.';
    if ($tax_id_type === 'ein' && (
            !preg_match('/^\d{2}$/',$ein1) ||
            !preg_match('/^\d{7}$/',$ein2)))
                                $errors['ein']         = 'Enter a valid 9-digit EIN.';

    if (empty($errors)) {
        $class_map = [
            'individual'=>'1','c_corp'=>'2','s_corp'=>'3',
            'partnership'=>'4','trust'=>'5','llc'=>'6','other'=>'7',
        ];

        $xfa = [
            'f1_1'  => $name,
            'f1_2'  => $business_name,
            'f1_5'  => $exempt_code,
            'f1_6'  => $fatca_code_val,
            'f1_7'  => $address,
            'f1_8'  => $city_state_zip,
            'f1_9'  => $requester_info,
            'f1_10' => $account_numbers,
            'c1_1'  => $class_map[$tax_class] ?? '0',
        ];

        if ($tax_class === 'llc')   $xfa['f1_3'] = strtoupper($llc_type);
        if ($tax_class === 'other') $xfa['f1_4'] = $other_desc;

        if ($tax_id_type === 'ssn') {
            $xfa['f1_11'] = $ssn1;
            $xfa['f1_12'] = $ssn2;
            $xfa['f1_13'] = $ssn3;
        } else {
            $xfa['f1_14'] = $ein1;
            $xfa['f1_15'] = $ein2;
        }

        $filename = OUTPUT_DIR . 'w9_' . uniqid() . '.pdf';

        if (fill_w9($xfa, $filename)) {
            header('Content-Type: application/pdf');
            header('Content-Disposition: attachment; filename="W9_' . date('Ymd') . '.pdf"');
            header('Content-Length: ' . filesize($filename));
            header('Cache-Control: private, must-revalidate');
            header('Pragma: private');
            header('Expires: 0');
            ob_end_clean();
            readfile($filename);
            @unlink($filename);
            exit;
        }

        $errors['_global'] = 'PDF generation failed. Check: (1) Python 3 is installed, '
            . '(2) pypdf is installed: <code>pip install pypdf</code>, '
            . '(3) fill_w9.py is in the same folder, '
            . '(4) filled/ is writable.';
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>W-9 — Taxpayer Identification Number</title>
<style>
*,*::before,*::after{box-sizing:border-box}
body{font-family:Arial,sans-serif;max-width:820px;margin:30px auto;padding:0 20px;background:#f4f6f8;color:#333}
.card{background:#fff;border:1px solid #ddd;border-radius:6px;padding:22px 24px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
h1{color:#003087;border-bottom:2px solid #003087;padding-bottom:10px;font-size:22px;margin-bottom:20px}
h3{margin:0 0 14px;color:#003087;font-size:13px;text-transform:uppercase;letter-spacing:.5px}
label{display:block;font-weight:700;font-size:13px;margin-bottom:5px}
label.inline{font-weight:400;display:inline-flex;align-items:center;gap:6px;cursor:pointer;margin-right:20px}
input[type=text],select{width:100%;padding:8px 10px;border:1px solid #ccc;border-radius:4px;font-size:14px;transition:border .2s}
input[type=text]:focus,select:focus{border-color:#003087;outline:none;box-shadow:0 0 0 3px rgba(0,48,135,.12)}
.row{display:flex;gap:16px;margin-bottom:16px}
.row>div{flex:1}
.mb{margin-bottom:16px}
.err{color:#c0392b;font-size:12px;margin-top:4px}
.alert{background:#fde8e8;border:1px solid #f5b8b8;color:#7b1f1f;padding:12px 16px;border-radius:4px;margin-bottom:20px;font-size:14px}
.alert code{background:#f5c2c7;padding:1px 5px;border-radius:3px;font-size:13px}
.radio-group{display:flex;flex-wrap:wrap;gap:10px 20px}
.tin-row{display:flex;align-items:center;gap:8px}
.tin-row input{width:85px;flex:none;text-align:center;letter-spacing:2px}
.sep{font-size:20px;color:#aaa;font-weight:700}
#llc_type_row,#other_desc_row,#ssn_fields,#ein_fields{display:none;margin-top:12px;padding-top:12px;border-top:1px dashed #e0e0e0}
.btn{background:#003087;color:#fff;padding:12px 36px;border:none;border-radius:4px;font-size:16px;cursor:pointer;font-weight:700}
.btn:hover{background:#00205b}
.req{color:red}
.hint{display:block;font-size:11px;color:#888;font-weight:400;margin-top:2px}
</style>
</head>
<body>

<h1>&#x1F4CB; Form W-9 &mdash; Request for Taxpayer Identification Number</h1>

<?php if (!empty($errors['_global'])): ?>
<div class="alert">&#x26A0; <?= $errors['_global'] ?></div>
<?php endif; ?>

<form method="POST">

<!-- 1. Name -->
<div class="card">
    <h3>Identification</h3>
    <div class="mb">
        <label>1. Name (as shown on your income tax return) <span class="req">*</span></label>
        <input type="text" name="name" value="<?= h($submitted?($name??''):'') ?>" placeholder="Full legal name" maxlength="100">
        <?php if(!empty($errors['name'])): ?><div class="err"><?= h($errors['name']) ?></div><?php endif; ?>
    </div>
    <div>
        <label>2. Business name / disregarded entity name <span class="hint">(if different from above)</span></label>
        <input type="text" name="business_name" value="<?= h($submitted?($business_name??''):'') ?>" placeholder="Business or DBA name" maxlength="100">
    </div>
</div>

<!-- 2. Classification -->
<div class="card">
    <h3>3. Federal Tax Classification</h3>
    <div class="radio-group">
        <?php foreach(['individual'=>'Individual / Sole proprietor / Single-member LLC','c_corp'=>'C Corporation','s_corp'=>'S Corporation','partnership'=>'Partnership','trust'=>'Trust / Estate','llc'=>'LLC','other'=>'Other'] as $val=>$lbl): ?>
        <label class="inline">
            <input type="radio" name="tax_classification" value="<?= $val ?>" <?= ($submitted&&($tax_class??'')===$val)?'checked':'' ?>>
            <?= h($lbl) ?>
        </label>
        <?php endforeach; ?>
    </div>
    <div id="llc_type_row">
        <label>LLC tax classification <span class="req">*</span></label>
        <select name="llc_type" style="width:auto;min-width:220px">
            <option value="">Select...</option>
            <option value="C" <?= ($submitted&&($llc_type??'')==='C')?'selected':'' ?>>C = C Corporation</option>
            <option value="S" <?= ($submitted&&($llc_type??'')==='S')?'selected':'' ?>>S = S Corporation</option>
            <option value="P" <?= ($submitted&&($llc_type??'')==='P')?'selected':'' ?>>P = Partnership</option>
        </select>
    </div>
    <div id="other_desc_row">
        <label>Other — describe</label>
        <input type="text" name="other_description" value="<?= h($submitted?($other_desc??''):'') ?>">
    </div>
</div>

<!-- 3. Exemptions -->
<div class="card">
    <h3>4. Exemptions <span class="hint" style="font-size:12px;text-transform:none">(entities only)</span></h3>
    <div class="row">
        <div>
            <label>Exempt payee code</label>
            <input type="text" name="exempt_payee_code" value="<?= h($submitted?($exempt_code??''):'') ?>" style="width:80px" maxlength="2" placeholder="—">
        </div>
        <div>
            <label>FATCA exemption code</label>
            <input type="text" name="fatca_code" value="<?= h($submitted?($fatca_code_val??''):'') ?>" style="width:80px" maxlength="2" placeholder="—">
        </div>
        <div></div>
    </div>
</div>

<!-- 4. Address -->
<div class="card">
    <h3>Address</h3>
    <div class="mb">
        <label>5. Street address <span class="req">*</span></label>
        <input type="text" name="address" value="<?= h($submitted?($address??''):'') ?>" placeholder="123 Main St, Suite 100" maxlength="200">
        <?php if(!empty($errors['address'])): ?><div class="err"><?= h($errors['address']) ?></div><?php endif; ?>
    </div>
    <div class="mb">
        <label>6. City, state, and ZIP code <span class="req">*</span></label>
        <input type="text" name="city_state_zip" value="<?= h($submitted?($city_state_zip??''):'') ?>" placeholder="New York, NY 10001" maxlength="100">
        <?php if(!empty($errors['city'])): ?><div class="err"><?= h($errors['city']) ?></div><?php endif; ?>
    </div>
    <div class="mb">
        <label>7. Account number(s) <span class="hint">(optional)</span></label>
        <input type="text" name="account_numbers" value="<?= h($submitted?($account_numbers??''):'') ?>">
    </div>
    <div>
        <label>Requester's name and address <span class="hint">(optional)</span></label>
        <input type="text" name="requester_info" value="<?= h($submitted?($requester_info??''):'') ?>">
    </div>
</div>

<!-- 5. TIN -->
<div class="card">
    <h3>Part I &mdash; Taxpayer Identification Number</h3>
    <div class="mb">
        <label>TIN type <span class="req">*</span></label>
        <div style="display:flex;gap:24px;margin-top:6px">
            <label class="inline"><input type="radio" name="tax_id_type" value="ssn" <?= ($submitted&&($tax_id_type??'')==='ssn')?'checked':'' ?>> Social Security Number (SSN)</label>
            <label class="inline"><input type="radio" name="tax_id_type" value="ein" <?= ($submitted&&($tax_id_type??'')==='ein')?'checked':'' ?>> Employer Identification Number (EIN)</label>
        </div>
        <?php if(!empty($errors['tin_type'])): ?><div class="err"><?= h($errors['tin_type']) ?></div><?php endif; ?>
    </div>
    <div id="ssn_fields">
        <label>Social Security Number</label>
        <div class="tin-row">
            <input type="text" name="ssn1" maxlength="3" placeholder="XXX"  value="<?= h($submitted?($ssn1??''):'') ?>">
            <span class="sep">–</span>
            <input type="text" name="ssn2" maxlength="2" placeholder="XX"   value="<?= h($submitted?($ssn2??''):'') ?>">
            <span class="sep">–</span>
            <input type="text" name="ssn3" maxlength="4" placeholder="XXXX" value="<?= h($submitted?($ssn3??''):'') ?>">
        </div>
        <?php if(!empty($errors['ssn'])): ?><div class="err"><?= h($errors['ssn']) ?></div><?php endif; ?>
    </div>
    <div id="ein_fields">
        <label>Employer Identification Number</label>
        <div class="tin-row">
            <input type="text" name="ein1" maxlength="2"  placeholder="XX"      value="<?= h($submitted?($ein1??''):'') ?>">
            <span class="sep">–</span>
            <input type="text" name="ein2" maxlength="7"  placeholder="XXXXXXX" value="<?= h($submitted?($ein2??''):'') ?>">
        </div>
        <?php if(!empty($errors['ein'])): ?><div class="err"><?= h($errors['ein']) ?></div><?php endif; ?>
    </div>
</div>

<p style="font-size:12px;color:#666;margin-bottom:16px">Under penalties of perjury, I certify the information provided is accurate and complete.</p>
<button type="submit" class="btn">&#x2B07; Generate &amp; Download W-9 PDF</button>
</form>

<script>
document.querySelectorAll('input[name="tax_classification"]').forEach(function(r){
    r.addEventListener('change',function(){
        document.getElementById('llc_type_row').style.display  =this.value==='llc'  ?'block':'none';
        document.getElementById('other_desc_row').style.display=this.value==='other'?'block':'none';
    });
});
document.querySelectorAll('input[name="tax_id_type"]').forEach(function(r){
    r.addEventListener('change',function(){
        document.getElementById('ssn_fields').style.display=this.value==='ssn'?'block':'none';
        document.getElementById('ein_fields').style.display=this.value==='ein'?'block':'none';
    });
});
(function(){
    var tc=document.querySelector('input[name="tax_classification"]:checked');
    if(tc){if(tc.value==='llc')document.getElementById('llc_type_row').style.display='block';if(tc.value==='other')document.getElementById('other_desc_row').style.display='block';}
    var tt=document.querySelector('input[name="tax_id_type"]:checked');
    if(tt){document.getElementById('ssn_fields').style.display=tt.value==='ssn'?'block':'none';document.getElementById('ein_fields').style.display=tt.value==='ein'?'block':'none';}
})();
['ssn1','ssn2','ein1'].forEach(function(n){
    var el=document.querySelector('input[name="'+n+'"]');
    if(el)el.addEventListener('input',function(){
        if(this.value.length===+this.getAttribute('maxlength')){
            var inputs=this.closest('.tin-row').querySelectorAll('input');
            for(var i=0;i<inputs.length-1;i++)if(inputs[i]===this){inputs[i+1].focus();break;}
        }
    });
});
</script>
</body>
</html>
