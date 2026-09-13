"""Apply common OCR cleanup fixes to extracted markdown documents."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPLACEMENTS: list[tuple[str, str]] = [
    ("\uFB01", "fi"),
    ("\uFB02", "fl"),
    ("\uFB00", "ff"),
    ("\uFB03", "ffi"),
    ("\uFB04", "ffl"),
    ("\uFB05", "ft"),
    ("\uFB06", "st"),
    ("", "- "),
    ("", "- "),
    ("", "- "),
    ("■", "- "),
    ("«", "<"),
    ("brochioitis", "bronchiolitis"),
    ("weith", "with"),
    ("MALNUTRION", "MALNUTRITION"),
    ("diarhoea", "diarrhoea"),
    ("withSevere", "with Severe"),
    ("VolumeofF-75", "Volume of F-75"),
    ("Every3hours°", "Every 3 hours"),
    ("cAfter", "c After"),
    ("WHo ", "WHO "),
    ("HIv", "HIV"),
    ("2okg", "20 kg"),
    ("firstnline", "first-line"),
    ("prferred", "preferred"),
    ("aspeferred", "as preferred"),
    ("seedosing", "see dosing"),
    ("tofordosage", "for dosage"),
    ("linewith", "line with"),
    ("treatmentatthesametime", "treatment at the same time"),
    ("norpleased", "is now pleased"),
    ("programis", "programme is"),
    (
        "andfinishingmostfeeds,changeto3-hourlyfeeds.",
        "and finishing most feeds, change to 3-hourly feeds.",
    ),
    ("Aftera dayon3-hourlyfeeds:", "After a day on 3-hourly feeds:"),
    ("lfnovomiting", "If no vomiting"),
    ("sulfamethoxozole", "sulfamethoxazole"),
    ("meﬂ oquine", "mefloquine"),
    ("mefl oquine", "mefloquine"),
    ("ciproﬂ oxacin", "ciprofloxacin"),
    ("ﬂ ucloxacillin", "flucloxacillin"),
    ("ﬂ uconazole", "fluconazole"),
    ("ﬂ ow", "flow"),
    ("ﬁ rst", "first"),
    ("ﬁ rst-", "first-"),
    ("beneﬁ t", "benefit"),
    ("beneﬁ ts", "benefits"),
    ("Conﬁ rmation", "Confirmation"),
    ("classiﬁ cations", "classifications"),
    ("classiﬁ cation", "classification"),
    ("identiﬁ ed", "identified"),
    ("speciﬁ c", "specific"),
    ("signiﬁ cant", "significant"),
    ("sufﬁ cient", "sufficient"),
    ("inﬂ uenza", "influenza"),
    ("proﬁ le", "profile"),
    ("reﬂ ect", "reflect"),
    ("difﬁ cult", "difficult"),
    ("efﬁ cacy", "efficacy"),
    ("life-ﬂ ow", "life-flow"),
    ("cmH20", "cmH2O"),
    ("(130 Ml/kg)", "(130 ml/kg)"),
    (" on xray", " on chest X-ray"),
    (" xray,", " chest X-ray,"),
    (" xray ", " X-ray "),
    (" xray.", " X-ray."),
    (" xray)", " X-ray)"),
    ("Skull xray", "Skull X-ray"),
    ("chest xray", "chest X-ray"),
    ("chest x-ray", "chest X-ray"),
    ("MgS04", "MgSO4"),
    ("Bu11", "Bull"),
    ("Meml Fund", "Memorial Fund"),
    ("6-m mercaptopurine", "6-mercaptopurine"),
    ("No. OO2220", "No. 002220"),
    ("No. OO1476", "No. 001476"),
    ("No. OOl503", "No. 001503"),
    ("Oxygen t\ntherapy", "Oxygen therapy"),
    ("| 006 |", "| 900 |"),
    (" 006\n720", " 900\n720"),
    ("Pa02", "PaO2"),
    ("Berhard Frey", "Bernhard Frey"),
    ("form the Bill", "from the Bill"),
    ("prior advise", "prior advice"),
    ("triaget", "triage"),
    ("assessment and treatment: care of critically-ill chil­", "assessment and treatment: care of critically-ill children"),
    ("1.Anoxia", "1. Anoxia"),
    ("2.Oxygen", "2. Oxygen"),
    ("3.Child", "3. Child"),
    ("4.Pneumonia", "4. Pneumonia"),
    ("5.Handbooks", "5. Handbooks"),
    ("I.World", "I. World"),
    ("immuniization", "immunisation"),
    ("ArtemetherLumefantrine", "Artemether-Lumefantrine"),
    ("HIVnegative", "HIV-negative"),
    ("HIVpositive", "HIV-positive"),
    ("benzyIpenicillin", "benzylpenicillin"),
    ("DrugResistant", "Drug-Resistant"),
    ("bThe ", "The "),
    ("ReSoMal If", "ReSoMal. If"),
    ("SmellieVeit", "Smellie-Veit"),
    ("110mmHge", "110 mmHg"),
    ("SnowWhite", "Snow White"),
    ("10 -I4 kg", "10-14 kg"),
    ("I30 ml", "130 ml"),
    ("SECOND EDITION 2003 Copyright", "SECOND EDITION 2003\n\nCopyright"),
    ("steriIe", "sterile"),
    ("DIARROHEA", "DIARRHOEA"),
    ("ANAESTHETHICS", "ANAESTHETICS"),
    ("inbetween", "in between"),
    ("1020ml/kg", "10-20 ml/kg"),
    ("10-19.9Kg", "10-19.9 kg"),
    ("20-39.9Kg", "20-39.9 kg"),
    ("40-49.9Kg", "40-49.9 kg"),
    ("10mg/10mls", "10 mg/10 ml"),
    ("80mgs/2mls", "80 mg/2 ml"),
    ("5–10ml/kg", "5–10 ml/kg"),
    ("", "-"),
    ("🗝Key Message:", "**Key message:**"),
    ("🗝Key message:", "**Key message:**"),
    ("ugms", "micrograms"),
    ("200micrograms", "200 micrograms"),
    ("March 2016 The information", "March 2016\n\nThe information"),
    ("March 2016 PACIFIC OUTBREAK", "March 2016\n\nPACIFIC OUTBREAK"),
    ("March 2016 Introduction", "March 2016\n\nIntroduction"),
    ("March 2016 Additional", "March 2016\n\nAdditional"),
    ("previTRAUMA AND INJURIES", "previously undiagnosed injury may become apparent.\n\nTRAUMA AND INJURIES"),
    ("selfCOMMON PROBLEMS OF LOW-BIRTH-WEIGHT INFANTS", "self-limiting condition, because\n\nCOMMON PROBLEMS OF LOW-BIRTH-WEIGHT INFANTS"),
    ("lowbirth-weight", "low-birth-weight"),
    ("trimethoprimsulfamethoxazole", "trimethoprim-sulfamethoxazole"),
    ("weightfor-height", "weight-for-height"),
    ("midupper arm circumference", "mid-upper arm circumference"),
    ("C0-artem", "Co-Artem"),
    ("providerinitiated", "provider-initiated"),
    ("ricewater", "rice water"),
    ("Koplik spotsearly sign", "Koplik spots—early sign"),
    ("intestinal obstructionvomiting", "intestinal obstruction: vomiting"),
    ("mouthto-mouth", "mouth-to-mouth"),
    ("skin-toskin", "skin-to-skin"),
    ("measlesrubella", "measles/rubella"),
    ("1stdose", "1st dose"),
    ("proteinenergy", "protein energy"),
    ("0.1m/kg rectally", "0.1 mg/kg rectally"),
    ("1.5G", "1.5 g"),
    ("Neverapine", "Nevirapine"),
    ("DTGcontaining", "DTG-containing"),
    ("non-DTGbased", "non-DTG-based"),
    ("as there as risks", "as there are risks"),
    ("on and EFV-based regimen", "on an EFV-based regimen"),
    ("EFZbased", "EFV-based"),
    ("NPV-based", "NVP-based"),
    ("super-boosting o LPV/r", "super-boosting of LPV/r"),
    ("Culturebased", "Culture-based"),
    ("lowcomplexity", "low-complexity"),
    ("highrisk", "high-risk"),
    ("drugsusceptible", "drug-susceptible"),
    ("oxyg enenriched", "oxygen-enriched"),
    ("oxygenenriched", "oxygen-enriched"),
    ("bag-andmask", "bag-and-mask"),
    ("endexpiratory", "end-expiratory"),
    ("cm H20", "cmH₂O"),
    ("alcuronium 0.250.5 mg/kg", "alcuronium 0.25–0.5 mg/kg"),
    ("PANCURONIUM 4mg mg/2 ml", "PANCURONIUM 4 mg/2 ml"),
    ("VECURONIUM 4mg/2 ml", "VECURONIUM 4 mg/2 ml"),
    ("less than l0 g/dl", "less than 10 g/dl"),
    ("Hb is less than l0 g/dl", "Hb is less than 10 g/dl"),
    ("Hb less than l0 g/dl", "Hb less than 10 g/dl"),
    ("(8 m1) KCl", "(8 ml) KCl"),
    ("l0 g magnesium hydroxide", "10 g magnesium hydroxide"),
    ("250 mg/l0 ml amp", "250 mg/10 ml amp"),
    ("1 mg/0.5 m1", "1 mg/0.5 ml"),
    ("10 mg/2 m1", "10 mg/2 ml"),
    ("l0 mg/2 ml ampoule", "10 mg/2 ml ampoule"),
    ("Amoxicillin 5001000mg tds", "Amoxicillin 500–1000 mg tds"),
    ("K4045,000.00", "K40–45,000.00"),
    ("IntranatalCareoftheMother", "Intranatal Care of the Mother"),
    ("culturepositive", "culture-positive"),
    ("outbreakprone", "outbreak-prone"),
    ("capacitybuilding", "capacity-building"),
    ("<50ml50mlml/min", "<50 mL/min"),
    ("0.7mg/kg for Cyprotococcosis", "0.7 mg/kg for cryptococcosis"),
    ("1.0/mg/kg for Aspergillosis", "1.0 mg/kg for aspergillosis"),
    ("Amphotercin B (1mg/kd/day)", "Amphotericin B (1 mg/kg/day)"),
    ("12mg/kd/day", "12 mg/kg/day"),
    ("15–20 g/kg", "15–20 mg/kg"),
    ("15–20\u00a0g/kg", "15–20 mg/kg"),
    ("Pyrimethamine 2550mg/day", "Pyrimethamine 25–50 mg/day"),
    ("200ucg/kg", "200 µg/kg"),
    ("Trimethroprim15-20mg/kg/day", "Trimethoprim 15–20 mg/kg/day"),
]


def fix_soft_hyphens(text: str) -> tuple[str, int]:
    changes = 0
    while True:
        new_text = re.sub(r"(\w)\u00ad\s*\n\s*(\w)", r"\1\2", text)
        new_text2 = new_text.replace("\u00ad", "")
        if new_text2 == text:
            break
        changes += 1
        text = new_text2
    return text, changes


def fix_n_bullets(text: str) -> tuple[str, int]:
    count = len(re.findall(r"^n\t", text, re.M))
    text = re.sub(r"^n\t", "- ", text, flags=re.MULTILINE)
    return text, count


def fix_broken_urls(text: str) -> tuple[str, int]:
    changes = 0
    patterns = [
        (r"\(http://www\.\s*\n\s*who\.int", r"(http://www.who.int"),
        (r"\(http://who\.\s*\n\s*int", r"(http://who.int"),
        (r"(https?://[^\s\n\)]+)\n([a-z0-9_./\-]+)", r"\1\2"),
    ]
    for pattern, repl in patterns:
        prev = text
        text = re.sub(pattern, repl, text)
        if text != prev:
            changes += 1
    return text, changes


def fix_toc_tabs(text: str) -> tuple[str, int]:
    count = len(re.findall(r"\t", text))
    # TOC lines: "Section name<TAB>page" -> "Section name (p. page)"
    text = re.sub(r"([^\t\n]+)\t+(\d+)\s*$", r"\1 (p. \2)", text, flags=re.MULTILINE)
    # Remaining tabs -> single space
    text = text.replace("\t", " ")
    return text, count


def fix_em_dash_artifacts(text: str) -> tuple[str, int]:
    """Clean up over-aggressive tab-to-em-dash conversion."""
    changes = 0
    replacements = [
        (r"(\d+\.)\s+—\s+", r"\1 "),
        (r"(\d+\.\d+)\s+—\s+", r"\1 "),
        (r" — \n", " "),
        (r" — (\d+)\s*$", r" (p. \1)"),
    ]
    for pattern, repl in replacements:
        new_text, n = re.subn(pattern, repl, text, flags=re.MULTILINE)
        if n:
            changes += n
            text = new_text
    return text, changes


def fix_section_heading_breaks(text: str) -> tuple[str, int]:
    """Join '1.3 — \\nTitle' or '1.3  \\nTitle' into '1.3 Title'."""
    count = 0
    for pattern in [
        r"(\d+(?:\.\d+)*)\s+—\s*\n(\S)",
        r"(\d+(?:\.\d+)*)\s+\n(\S)",
    ]:
        new_text, n = re.subn(pattern, r"\1 \2", text)
        if n:
            count += n
            text = new_text
    return text, count


def remove_duplicate_page_headers(text: str) -> tuple[str, int]:
    """Remove repeated running headers like 'OXYGEN THERAPY FOR CHILDREN\\n2'."""
    changes = 0
    patterns = [
        r"\nOXYGEN THERAPY FOR CHILDREN\n\d+\n",
        r"\n\d+\n\d\. [A-Z][A-Z ]+\n",
    ]
    for pattern in patterns:
        new_text, n = re.subn(pattern, "\n", text)
        if n:
            changes += n
            text = new_text
    return text, changes


def remove_control_chars(text: str) -> tuple[str, int]:
    count = len(re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text))
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return cleaned, count


def merge_broken_bullets(text: str) -> tuple[str, int]:
    changes = 0

    def repl_bullet(match: re.Match[str]) -> str:
        nonlocal changes
        changes += 1
        return f"- {match.group(1).strip()}"

    text = re.sub(r"^•\s*\n(.+)$", repl_bullet, text, flags=re.MULTILINE)

    def repl_dash(match: re.Match[str]) -> str:
        nonlocal changes
        changes += 1
        return f"  - {match.group(1).strip()}"

    text = re.sub(r"^–\s*\n(.+)$", repl_dash, text, flags=re.MULTILINE)
    return text, changes


def dehyphenate_line_breaks(text: str) -> tuple[str, int]:
    changes = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal changes
        changes += 1
        return match.group(1) + match.group(2)

    text = re.sub(r"(\w)-\n(\w)", repl, text)
    return text, changes


def collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{4,}", "\n\n\n", text)


def fix_unit_spacing(text: str) -> tuple[str, int]:
    changes = 0
    rules = [
        (r"1020ml/kg", "10-20 ml/kg"),
        (r"(\d+)ml/kg", r"\1 ml/kg"),
        (r"(\d+)mls\b", r"\1 ml"),
        (r"(\d+)ml\b(?!/)", r"\1 ml"),
        (r"(\d+)Kg\b", r"\1 kg"),
        (r"(\d+)kg\b", r"\1 kg"),
    ]
    for pattern, repl in rules:
        new_text, n = re.subn(pattern, repl, text)
        if n:
            changes += n
            text = new_text
    text = re.sub(r"(\d+) ml ml\b", r"\1 ml", text)
    return text, changes


def remove_empty_consecutive_pages(text: str) -> tuple[str, int]:
    count = 0
    while True:
        new_text, n = re.subn(
            r"(## Page \d+)\n\n(## Page \d+\n\n(?![#]))",
            r"\2",
            text,
        )
        if not n:
            break
        count += n
        text = new_text
    return text, count


def clean_text(text: str) -> tuple[str, int]:
    changes = 0

    text, n = remove_control_chars(text)
    changes += n

    text, n = fix_soft_hyphens(text)
    changes += n

    text, n = fix_broken_urls(text)
    changes += n

    for old, new in REPLACEMENTS:
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            changes += count

    text, n = merge_broken_bullets(text)
    changes += n

    text, n = dehyphenate_line_breaks(text)
    changes += n

    text, n = fix_n_bullets(text)
    changes += n

    text, n = fix_toc_tabs(text)
    changes += n

    text, n = remove_duplicate_page_headers(text)
    changes += n

    text, n = fix_unit_spacing(text)
    changes += n

    text, n = remove_empty_consecutive_pages(text)
    changes += n

    text = re.sub(r"(\d)  h\b", r"\1 h", text)
    text = re.sub(r"(?<=\S)  +(?=\S)", " ", text)
    text = collapse_blank_lines(text)
    return text, changes


def format_feeding_chart(text: str) -> str:
    """Rewrite Feeding Chart columnar OCR output as markdown tables."""
    if "F-75 Reference Card" not in text:
        return text

    header = text.split("## Page 1")[0] + "## Page 1\n\n"

    page1 = """### F-75 Reference Card — Volume of F-75 per feed (ml)

| Weight (kg) | Every 2 hours (12 feeds) | Every 3 hours (8 feeds) | Every 4 hours (6 feeds) | Daily total (130 ml/kg) | 80% of daily total (minimum) |
| --- | --- | --- | --- | --- | --- |
| 2.0 | 20 | 30 | 45 | 260 | 210 |
| 2.2 | 25 | 35 | 50 | 286 | 230 |
| 2.4 | 25 | 40 | 55 | 312 | 250 |
| 2.6 | 30 | 45 | 55 | 338 | 265 |
| 2.8 | 30 | 45 | 60 | 364 | 290 |
| 3.0 | 35 | 50 | 65 | 390 | 310 |
| 3.2 | 35 | 55 | 70 | 416 | 335 |
| 3.4 | 35 | 55 | 75 | 442 | 355 |
| 3.6 | 40 | 60 | 80 | 468 | 375 |
| 3.8 | 40 | 60 | 85 | 494 | 395 |
| 4.0 | 45 | 65 | 90 | 520 | 415 |
| 4.2 | 45 | 70 | 90 | 546 | 435 |
| 4.4 | 50 | 70 | 95 | 572 | 460 |
| 4.6 | 50 | 75 | 100 | 598 | 480 |
| 4.8 | 55 | 80 | 105 | 624 | 500 |
| 5.0 | 55 | 80 | 110 | 650 | 520 |
| 5.2 | 55 | 85 | 115 | 676 | 540 |
| 5.4 | 60 | 90 | 120 | 702 | 560 |
| 5.6 | 60 | 90 | 125 | 728 | 580 |
| 5.8 | 65 | 95 | 130 | 754 | 605 |
| 6.0 | 65 | 100 | 130 | 780 | 625 |
| 6.2 | 70 | 100 | 135 | 806 | 645 |
| 6.4 | 70 | 105 | 140 | 832 | 665 |
| 6.6 | 75 | 110 | 145 | 858 | 685 |
| 6.8 | 75 | 110 | 150 | 884 | 705 |
| 7.0 | 75 | 115 | 155 | 910 | 730 |
| 7.2 | 80 | 120 | 160 | 936 | 750 |
| 7.4 | 80 | 120 | 160 | 962 | 770 |
| 7.6 | 85 | 125 | 165 | 988 | 790 |
| 7.8 | 85 | 130 | 170 | 1014 | 810 |
| 8.0 | 90 | 130 | 175 | 1040 | 830 |
| 8.2 | 90 | 135 | 180 | 1066 | 855 |
| 8.4 | 90 | 140 | 185 | 1092 | 875 |
| 8.6 | 95 | 140 | 190 | 1118 | 895 |
| 8.8 | 95 | 145 | 195 | 1144 | 915 |
| 9.0 | 100 | 145 | 200 | 1170 | 935 |
| 9.2 | 100 | 150 | 200 | 1196 | 960 |
| 9.4 | 105 | 155 | 205 | 1222 | 980 |
| 9.6 | 105 | 155 | 210 | 1248 | 1000 |
| 9.8 | 110 | 160 | 215 | 1274 | 1020 |
| 10.0 | 110 | 160 | 220 | 1300 | 1040 |

**Notes**

- Volumes in these columns are rounded to the nearest 5 ml.
- Feed 2-hourly for at least the first day. Then, when little or no vomiting, modest diarrhoea (<5 watery stools per day), and finishing most feeds, change to 3-hourly feeds.
- After a day on 3-hourly feeds: If no vomiting, less diarrhoea, and finishing most feeds, change to 4-hourly feeds.
"""

    page2 = """## Page 2

### Volume of F-75 for Children with Severe (+++) Oedema

| Weight (kg) | Every 2 hours (12 feeds) | Every 3 hours (8 feeds) | Every 4 hours (6 feeds) | Daily total (100 ml/kg) | 80% of daily total (minimum) |
| --- | --- | --- | --- | --- | --- |
| 3.0 | 25 | 40 | 50 | 300 | 240 |
| 3.2 | 25 | 40 | 55 | 320 | 255 |
| 3.4 | 30 | 45 | 60 | 340 | 270 |
| 3.6 | 30 | 45 | 60 | 360 | 290 |
| 3.8 | 30 | 50 | 65 | 380 | 305 |
| 4.0 | 35 | 50 | 65 | 400 | 320 |
| 4.2 | 35 | 55 | 70 | 420 | 335 |
| 4.4 | 35 | 55 | 75 | 440 | 350 |
| 4.6 | 40 | 60 | 75 | 460 | 370 |
| 4.8 | 40 | 60 | 80 | 480 | 385 |
| 5.0 | 40 | 65 | 85 | 500 | 400 |
| 5.2 | 45 | 65 | 85 | 520 | 415 |
| 5.4 | 45 | 70 | 90 | 540 | 430 |
| 5.6 | 45 | 70 | 95 | 560 | 450 |
| 5.8 | 50 | 75 | 95 | 580 | 465 |
| 6.0 | 50 | 75 | 100 | 600 | 480 |
| 6.2 | 50 | 80 | 105 | 620 | 495 |
| 6.4 | 55 | 80 | 105 | 640 | 510 |
| 6.6 | 55 | 85 | 110 | 660 | 530 |
| 6.8 | 55 | 85 | 115 | 680 | 545 |
| 7.0 | 60 | 90 | 115 | 700 | 560 |
| 7.2 | 60 | 90 | 120 | 720 | 575 |
| 7.4 | 60 | 95 | 125 | 740 | 590 |
| 7.6 | 65 | 95 | 125 | 760 | 610 |
| 7.8 | 65 | 100 | 130 | 780 | 625 |
| 8.0 | 65 | 100 | 135 | 800 | 640 |
| 8.2 | 70 | 105 | 135 | 820 | 655 |
| 8.4 | 70 | 105 | 140 | 840 | 670 |
| 8.6 | 70 | 110 | 145 | 860 | 690 |
| 8.8 | 75 | 110 | 145 | 880 | 705 |
| 9.0 | 75 | 115 | 150 | 900 | 720 |
| 9.2 | 75 | 115 | 155 | 920 | 735 |
| 9.4 | 80 | 120 | 155 | 940 | 750 |
| 9.6 | 80 | 120 | 160 | 960 | 770 |
| 9.8 | 80 | 125 | 165 | 980 | 785 |
| 10.0 | 85 | 125 | 165 | 1000 | 800 |
| 10.2 | 85 | 130 | 170 | 1020 | 815 |
| 10.4 | 85 | 130 | 175 | 1040 | 830 |
| 10.6 | 90 | 135 | 175 | 1060 | 850 |
| 10.8 | 90 | 135 | 180 | 1080 | 865 |
| 11.0 | 90 | 140 | 185 | 1100 | 880 |
| 11.2 | 95 | 140 | 185 | 1120 | 895 |
| 11.4 | 95 | 145 | 190 | 1140 | 910 |
| 11.6 | 95 | 145 | 195 | 1160 | 930 |
| 11.8 | 100 | 150 | 195 | 1180 | 945 |
| 12.0 | 100 | 150 | 200 | 1200 | 960 |

**Notes**

- Volumes in these columns are rounded to the nearest 5 ml.
- Feed 2-hourly for at least the first day. Then, when little or no vomiting, modest diarrhoea (<5 watery stools per day), and finishing most feeds, change to 3-hourly feeds.
- After a day on 3-hourly feeds: If no vomiting, less diarrhoea, and finishing most feeds, change to 4-hourly feeds.
"""

    page3 = """## Page 3

### F-100 Reference Card — Range of Volumes for Free-Feeding with F-100

| Weight (kg) | Minimum per 4-hourly feed (ml) | Maximum per 4-hourly feed (ml) | Minimum daily (150 ml/kg/day) | Maximum daily (220 ml/kg/day) |
| --- | --- | --- | --- | --- |
| 2.0 | 50 | 75 | 300 | 440 |
| 2.2 | 55 | 80 | 330 | 484 |
| 2.4 | 60 | 90 | 360 | 528 |
| 2.6 | 65 | 95 | 390 | 572 |
| 2.8 | 70 | 105 | 420 | 616 |
| 3.0 | 75 | 110 | 450 | 660 |
| 3.2 | 80 | 115 | 480 | 704 |
| 3.4 | 85 | 125 | 510 | 748 |
| 3.6 | 90 | 130 | 540 | 792 |
| 3.8 | 95 | 140 | 570 | 836 |
| 4.0 | 100 | 145 | 600 | 880 |
| 4.2 | 105 | 155 | 630 | 924 |
| 4.4 | 110 | 160 | 660 | 968 |
| 4.6 | 115 | 170 | 690 | 1012 |
| 4.8 | 120 | 175 | 720 | 1056 |
| 5.0 | 125 | 185 | 750 | 1100 |
| 5.2 | 130 | 190 | 780 | 1144 |
| 5.4 | 135 | 200 | 810 | 1188 |
| 5.6 | 140 | 205 | 840 | 1232 |
| 5.8 | 145 | 215 | 870 | 1276 |
| 6.0 | 150 | 220 | 900 | 1320 |
| 6.2 | 155 | 230 | 930 | 1364 |
| 6.4 | 160 | 235 | 960 | 1408 |
| 6.6 | 165 | 240 | 990 | 1452 |
| 6.8 | 170 | 250 | 1020 | 1496 |
| 7.0 | 175 | 255 | 1050 | 1540 |
| 7.2 | 180 | 265 | 1080 | 1588 |
| 7.4 | 185 | 270 | 1110 | 1628 |
| 7.6 | 190 | 280 | 1140 | 1672 |
| 7.8 | 195 | 285 | 1170 | 1716 |
| 8.0 | 200 | 295 | 1200 | 1760 |
| 8.2 | 205 | 300 | 1230 | 1804 |
| 8.4 | 210 | 310 | 1260 | 1848 |
| 8.6 | 215 | 315 | 1290 | 1892 |
| 8.8 | 220 | 325 | 1320 | 1936 |
| 9.0 | 225 | 330 | 1350 | 1980 |
| 9.2 | 230 | 335 | 1380 | 2024 |
| 9.4 | 235 | 345 | 1410 | 2068 |
| 9.6 | 240 | 350 | 1440 | 2112 |
| 9.8 | 245 | 360 | 1470 | 2156 |
| 10.0 | 250 | 365 | 1500 | 2200 |

**Notes**

- Volumes per feed are rounded to the nearest 5 ml.
"""

    return header + page1 + page2 + page3


def format_malnutrition_chart(text: str) -> str:
    if "MANAGEMENT OF SEVERE" not in text:
        return text

    header = text.split("## Page 1")[0] + "## Page 1\n\n"
    body = """## Management of Severe Malnutrition

Prepared by The Paediatric Society of PNG. For more information, contact your local paediatrician.

## Checklist

- Check for hypoglycaemia
- Prevent hypothermia
- Treat dehydration if present
- Electrolytes — zinc, potassium, magnesium
- Infection
  - Start antibiotics + albendazole
  - Exclude HIV and TB
- Micronutrients — vitamin A, folate
- Start milk feeding immediately
  - Full strength sunshine milk (or FSS)
  - At least 6 feeds per day, every 3 hours
  - 130 ml/kg/day
  - An 8 kg child should receive 8 × 130 = 1040 ml per day; at 6 feeds = ~170 ml per feed
  - Continue breast feeding
- Start iron in the 2nd week of treatment*
- Catch-up growth
  - Give Milk Oil Formula (or F-100); increase volume per feed as tolerated
  - Start RUTF
  - Continued breast-feeding
- Sensory stimulation and play
- Monitoring
  - Weigh every 2nd day
  - Good weight gain = 10 g/kg/day
- Supportive care — check Hb, start iron*
- Discharge planning
  - Good weight gain consistently for 1–2 weeks, weight >3 Z-scores
  - Good appetite
  - Parents able to feed child
- Follow-up weekly

For details, refer to Chapter 7, pp. 197–223.
"""
    return header + body


def format_bubble_cpap(text: str) -> str:
    """Improve Bubble CPAP markdown structure where tables were flattened."""
    if "Bubble-CPAP guidelines" not in text:
        return text

    text = text.replace(
        "conditions like staphylococcal pneumonia with pneumatocoeles on chest xray, CPAP can",
        "conditions like staphylococcal pneumonia with pneumatocoeles on chest X-ray, CPAP can",
    )

    # Convert the troubleshooting matrix into a readable table.
    matrix = """| Clinical status | Bubbles present | Action |
| --- | --- | --- |
| SpO2 >90%, mild respiratory distress | Yes | No immediate change needed; may reduce CPAP level to 5 cmH2O or reduce flow rates |
| SpO2 >90%, moderate to severe respiratory distress | Yes | Increase CPAP level |
| SpO2 <90% | Yes | Increase CPAP level; increase oxygen flow |
| Any status | No | Check nasal prongs and circuit for leaks; increase air or oxygen flow and check for bubbles |

"""
    old_block = (
        "SpO2 >90% and only \n"
        "mild respiratory distress \n"
        "SpO2 >90% but \n"
        "moderate to severe \n"
        "respiratory distress \n"
        "SpO2 <90% \n"
        "Bubbles \n"
        "No immediate change \n"
        "needed, may be able to \n"
        "reduce CPAP level to 5 \n"
        "cmH2O or reduce flow \n"
        "rates \n"
        "Increase CPAP level \n"
        "Increase CPAP level \n"
        "Increase oxygen flow \n"
        "No bubbles \n"
        "Check nasal prongs and \n"
        "check to see that there is \n"
        "no leak in the circuit \n"
        "Wean CPAP level and \n"
        "check if child still needs \n"
        "CPAP \n"
        "Check nasal prongs \n"
        "and check to see that \n"
        "there is no leak in the \n"
        "circuit Increase air \n"
        "flow, check for \n"
        "bubbles \n"
        "Increase CPAP level \n"
        "Check nasal prongs \n"
        "and check to see that \n"
        "there is no leak in the \n"
        "circuit \n"
        "Increase oxygen flow, \n"
        "check for bubbles \n"
        "Increase CPAP level"
    )
    if old_block in text:
        text = text.replace(old_block, matrix)

    # Cleaning section bullets
    cleaning = """- Staff cleaning the equipment must wear protective clothing to avoid splash exposure or contact with dirty equipment: wear apron, gloves and glasses.
- Good ventilation of the area is needed where you are cleaning the equipment.
- **What you need**
  - Soap for initial clean
  - Disinfectant solution: sodium hypochlorite 0.05% or household bleach, diluted to 0.05% hypochlorite. The household bleach bottle will indicate its strength; dilution is essential.
  - Sink or buckets to clean equipment
  - Brush to clean both inside and outside of circuit. All brushes and cleaning implements must be properly cleaned after use — soap water and drip dry
  - Gown or waterproof apron, mask and water-proof gloves
  - Drying rack
"""
    old_cleaning = (
        "• \n"
        "Staff cleaning the equipment must wear protective clothing to avoid splash exposure \n"
        "or contact with dirty equipment: wear apron, gloves and glasses. \n"
        "• \n"
        "Good ventilation of the area is needed where you are cleaning the equipment \n"
        "• \n"
        "What you need \n"
        "• \n"
        "Soap for initial clean \n"
        "• \n"
        "Disinfectant solution: (sodium hypochlorite 0.05% or household bleach, diluted to \n"
        "0.05% hypochlorite. The household bleach bottle will indicate its strength, dilution is \n"
        "essential) \n"
        "• \n"
        "Sink or buckets to clean equipment \n"
        "• \n"
        "Brush to clean both inside and outside of circuit. All brushes and cleaning \n"
        "implements must be properly cleaned after use – soap water and drip dry \n"
        "• \n"
        "Gown or waterproof apron, mask and water-proof gloves \n"
        "• \n"
        "Drying rack"
    )
    if old_cleaning in text:
        text = text.replace(old_cleaning, cleaning)

    return text


SPECIAL_HANDLERS = {
    "Feeding Chart.md": format_feeding_chart,
    "Malnutrition Treatment Chart.md": format_malnutrition_chart,
    "Bubble-CPAP-guidelines-2017.md": format_bubble_cpap,
}


def process_file(path: Path, dry_run: bool = False) -> int:
    original = path.read_text(encoding="utf-8")
    cleaned, changes = clean_text(original)

    handler = SPECIAL_HANDLERS.get(path.name)
    if handler:
        rewritten = handler(cleaned)
        if rewritten != cleaned:
            changes += 1
            cleaned = rewritten

    if cleaned != original and not dry_run:
        path.write_text(cleaned, encoding="utf-8")
    elif cleaned != original:
        changes = max(changes, 1)

    return changes if cleaned != original else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix common OCR issues in markdown docs.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/md_docs"),
        help="Directory containing markdown files.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing.")
    args = parser.parse_args()

    files = sorted(args.input_dir.glob("*.md"))
    if not files:
        print("No markdown files found.", file=sys.stderr)
        return 1

    total = 0
    for path in files:
        changes = process_file(path, dry_run=args.dry_run)
        total += changes
        if changes:
            mode = "would fix" if args.dry_run else "fixed"
            print(f"[{mode}] {path.name}: {changes} changes")

    print(f"\nTotal files changed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
