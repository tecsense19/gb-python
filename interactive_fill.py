#!/usr/bin/env python3
"""
interactive_fill.py — Interactive CLI to fill tax forms (W-9, W-8BEN, W-8BEN-E).
"""

import os, json, subprocess, sys

def get_input(prompt, default=""):
    val = input(f"{prompt} [{default}]: ").strip()
    return val if val else default

def main():
    print("=== Tax Form Generator (Python CLI) ===")
    print("1. Form W-9")
    print("2. W-8BEN (Individual)")
    print("3. W-8BEN-E (Entity)")
    
    choice = get_input("Select form type (1-3)", "1")
    
    if choice == "1":
        form_type = "w9"
        template = "fw9_blank.pdf"
        fields = {
            "f1_1":  get_input("Legal Name"),
            "f1_2":  get_input("Business Name"),
            "f1_7":  get_input("Address"),
            "f1_8":  get_input("City, State, ZIP"),
            "f1_11": get_input("SSN Part 1 (3 digits)"),
            "f1_12": get_input("SSN Part 2 (2 digits)"),
            "f1_13": get_input("SSN Part 3 (4 digits)"),
            "c1_1":  get_input("Classification (1=Indiv, 2=C-Corp, 3=S-Corp)", "1")
        }
    elif choice == "2":
        form_type = "w8i"
        template = "W8forIndividuals.pdf"
        fields = {
            "f_1":  get_input("Individual Name"),
            "f_2":  get_input("Country"),
            "f_3":  get_input("Permanent Address"),
            "f_4":  get_input("City/Town"),
            "f_5":  get_input("ZIP/Postal/Country"),
            "f_9":  get_input("Foreign TIN"),
            "f_13": get_input("Date of Birth (MM-DD-YYYY)")
        }
    elif choice == "3":
        form_type = "w8e"
        template = "W8forEntities.pdf"
        fields = {
            "f1_1":  get_input("Organization Name"),
            "f1_2":  get_input("Country of Incorporation"),
            "f1_7":  get_input("Permanent Address"),
            "f1_8":  get_input("City, ZIP, Country"),
            "f1_11": get_input("U.S. TIN (EIN)"),
            "c1_1":  get_input("Chapter 3 Status (1=Corp, 2=Partnership)", "1"),
            "c1_2":  get_input("Chapter 4 Status", "1")
        }
    else:
        print("Invalid choice.")
        return

    output_pdf = f"generated_{form_type}_{fields.get('f1_1', fields.get('f_1', 'form'))}.pdf"
    output_pdf = output_pdf.replace(" ", "_").lower()
    
    # Save temporary JSON
    with open("temp_fields.json", "w") as f:
        json.dump(fields, f)

    # Call fill_pdf.py
    cmd = [
        "python", "fill_pdf.py",
        template,
        "temp_fields.json",
        output_pdf,
        "sample_signature.png",
        form_type
    ]
    
    print(f"\nGenerating {output_pdf}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"SUCCESS: Created {output_pdf}")
        else:
            print(f"ERROR: {result.stderr}")
    except Exception as e:
        print(f"FAILED to run script: {e}")
    finally:
        if os.path.exists("temp_fields.json"):
            os.remove("temp_fields.json")

if __name__ == "__main__":
    main()
