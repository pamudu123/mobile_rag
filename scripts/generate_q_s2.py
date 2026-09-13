"""Generate Q_S2.json benchmark with mixed answerable and unanswerable RAG test questions."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "questions" / "Q_S2.json"

TEMPLATES = (
    ("night_shift_worker", "On night shift at the health centre, I encounter this situation: {topic}. What should I do according to the guideline?"),
    ("parent_counselling", "A worried parent asks me about {topic}. What is the correct guidance I should give?"),
    ("referral_decision", "I must decide whether to keep the patient here or refer urgently. The issue is {topic}. What do the documents say?"),
    ("doctor_on_call", "The on-call doctor phones and asks about {topic}. What is the evidence-based answer from our documents?"),
)

# Each topic uses templates in pairs (0+1 or 2+3) like Q_S1 alternates frontline/busy.
TOPICS: list[dict] = [
    # --- Answerable (35 topics) ---
    {
        "category": "Malaria",
        "topic": "Uncomplicated malaria ACT treatment",
        "answerable": True,
        "answer": "For uncomplicated malaria with a positive malaria test (or when testing is unavailable) and no severe signs, give ACT (Co-artem/MALA), paracetamol if temperature is 38°C or higher, treat other causes of fever if present, continue treatment at home, and review if fever persists.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 73.",
        "templates": (0, 1),
    },
    {
        "category": "Malaria",
        "topic": "Severe malaria pre-referral artesunate",
        "answerable": True,
        "answer": "For very sick, unconscious, or convulsing children with severe malaria, give pre-referral artesunate suppository 10 mg/kg, hold the buttocks together for 10 minutes after insertion, repeat after 24 hours and daily until referral, and refer urgently to hospital.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 74.",
        "templates": (2, 3),
    },
    {
        "category": "Measles",
        "topic": "Measles vitamin A dosing",
        "answerable": True,
        "answer": "Give two doses of oral vitamin A to children with measles at a hospital or health centre: under 1 year 100,000 units on day 1 and day 2; age 1 year or more 200,000 units on day 1 and day 2.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 100.",
        "templates": (0, 1),
    },
    {
        "category": "Measles",
        "topic": "Measles admission criteria",
        "answerable": True,
        "answer": "Admit a child with measles if they look very sick, are malnourished, or have serious complications such as pneumonia, dark staining rash, diarrhoea with dehydration, stridor, convulsions, severe oral thrush, or difficulty drinking.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 100.",
        "templates": (2, 3),
    },
    {
        "category": "Pneumonia",
        "topic": "Fast breathing thresholds by age",
        "answerable": True,
        "answer": "Fast breathing is defined as: age 0–2 months greater than 60 breaths/min; age 2–12 months greater than 50 breaths/min; age over 12 months greater than 40 breaths/min.",
        "source_of_truth": "PNG Standard Treatment Book (2016), pp. 119–120.",
        "templates": (0, 1),
    },
    {
        "category": "Pneumonia",
        "topic": "Severe pneumonia initial management",
        "answerable": True,
        "answer": "For severe pneumonia with too-sick signs plus chest indrawing and/or cyanosis: give oxygen, give first dose of amoxyl (or penicillin) and gentamicin, and admit or refer urgently to hospital if possible.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 119.",
        "templates": (2, 3),
    },
    {
        "category": "Pneumonia",
        "topic": "Parent warning signs of pneumonia",
        "answerable": True,
        "answer": "Teach parents the warning signs of pneumonia: fast breathing and chest indrawing. Antibiotics must not be used for colds; fast breathing or another clear indication is needed before treating cough with antibiotics.",
        "source_of_truth": "PNG Standard Treatment Book (2016), pp. 43–44.",
        "templates": (0, 1),
    },
    {
        "category": "Convulsions",
        "topic": "Convulsion airway care",
        "answerable": True,
        "answer": "Ensure a clear airway: place the child on the side, suction secretions, give oxygen during the fit, and check blood sugar if possible. Treat hypoglycaemia with dextrose or sugar under the tongue when indicated.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 45.",
        "templates": (2, 3),
    },
    {
        "category": "Convulsions",
        "topic": "Rectal diazepam dose 3–5.9 kg",
        "answerable": True,
        "answer": "For a child weighing 3–5.9 kg, give ¼ ml rectal diazepam (10 mg/2 ml vial), or the equivalent IV or IM paraldehyde dose as listed in the convulsions section.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 45.",
        "templates": (0, 1),
    },
    {
        "category": "Diarrhoea",
        "topic": "Severe dehydration fast IV bolus 10–14.9 kg",
        "answerable": True,
        "answer": "For severe dehydration, give fast IV Half Strength Darrow's or Hartmann's solution: 250 ml for a child weighing 10–14.9 kg, then reassess immediately and repeat if severe dehydration persists.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 49.",
        "templates": (2, 3),
    },
    {
        "category": "Diarrhoea",
        "topic": "ORS when IV access fails",
        "answerable": True,
        "answer": "If IV access cannot be obtained for severe dehydration, give ORS or Half Strength Darrow's by nasogastric drip, confirming tube placement and splinting the elbows. Use ReSoMal if the child has severe malnutrition and ReSoMal is available.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 50.",
        "templates": (0, 1),
    },
    {
        "category": "Snake bite",
        "topic": "Snake bite limb bandaging",
        "answerable": True,
        "answer": "At the bite site, bandage the whole length of the bitten limb from hand or foot toward shoulder or thigh as firmly as an ankle bandage, splint the limb, place the child in the left lateral recovery position, and keep the airway clear.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 138.",
        "templates": (2, 3),
    },
    {
        "category": "Snake bite",
        "topic": "Snake bite clotting test",
        "answerable": True,
        "answer": "Take a blood sample and leave it 20 minutes without shaking; failure to clot after 20 minutes is abnormal and indicates need for envenomation treatment with antivenom.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 138.",
        "templates": (0, 1),
    },
    {
        "category": "Obstetrics",
        "topic": "Eclampsia magnesium urgency",
        "answerable": True,
        "answer": "For eclampsia (fits after 20 weeks), ensure airway by rolling onto the side and give magnesium sulphate loading dose urgently to control and prevent further fits. Do not wait for a doctor's order.",
        "source_of_truth": "PNG O&G Standard Management Manual (2018), pp. 74–75.",
        "templates": (2, 3),
    },
    {
        "category": "Obstetrics",
        "topic": "Eclampsia minimum urine output",
        "answerable": True,
        "answer": "For an unconscious eclamptic patient, maintain airway, give oxygen, use an indwelling catheter, and record urine output hourly; minimum safe urine output is greater than 25 ml/hour.",
        "source_of_truth": "PNG O&G Standard Management Manual (2018), p. 74.",
        "templates": (0, 1),
    },
    {
        "category": "Obstetrics",
        "topic": "Primary PPH definition",
        "answerable": True,
        "answer": "Primary postpartum haemorrhage is defined as measured blood loss of 500 ml or more within the first 24 hours after vaginal delivery.",
        "source_of_truth": "PNG O&G Standard Management Manual (2018), p. 157.",
        "templates": (2, 3),
    },
    {
        "category": "Obstetrics",
        "topic": "PPH prevention oxytocin",
        "answerable": True,
        "answer": "To help prevent PPH, give oxytocin 10 IU IM with delivery of the baby or as soon after as possible, perform controlled cord traction when the uterus contracts, and rub up the fundus after placental delivery.",
        "source_of_truth": "PNG O&G Standard Management Manual (2018), p. 158.",
        "templates": (0, 1),
    },
    {
        "category": "Nutrition",
        "topic": "F-100 volume for 5 kg child",
        "answerable": True,
        "answer": "For a 5.0 kg child on F-100 catch-up feeding, the reference card gives a minimum daily volume of 750 ml (150 ml/kg/day) and maximum 1100 ml (220 ml/kg/day), with 125–185 ml per 4-hourly feed.",
        "source_of_truth": "F-100 Reference Card, p. 1.",
        "templates": (2, 3),
    },
    {
        "category": "Nutrition",
        "topic": "F-75 feed interval escalation",
        "answerable": True,
        "answer": "Start F-75 feeds 2-hourly for at least the first day; when there is little or no vomiting, modest diarrhoea, and most feeds are finished, change to 3-hourly feeds, then to 4-hourly after another day if tolerated.",
        "source_of_truth": "F-75 Reference Card, p. 1.",
        "templates": (0, 1),
    },
    {
        "category": "Nutrition",
        "topic": "SAM oedema F-75 volume",
        "answerable": True,
        "answer": "For children with severe (+++) oedema, the F-75 card uses 100 ml/kg/day instead of 130 ml/kg/day when calculating feed volumes.",
        "source_of_truth": "F-75 Reference Card, p. 2.",
        "templates": (2, 3),
    },
    {
        "category": "Nutrition",
        "topic": "SAM antibiotics and albendazole",
        "answerable": True,
        "answer": "In severe malnutrition management, start antibiotics and albendazole, exclude HIV and TB, and begin therapeutic milk feeding immediately at about 130 ml/kg/day in frequent feeds while continuing breastfeeding.",
        "source_of_truth": "Management of Severe Malnutrition chart.",
        "templates": (0, 1),
    },
    {
        "category": "CPAP",
        "topic": "Initial bubble CPAP pressure",
        "answerable": True,
        "answer": "When setting up bubble CPAP, dial the CPAP level required and start at 7 cmH2O, then adjust flows and monitor SpO2 and respiratory distress.",
        "source_of_truth": "Bubble-CPAP Guidelines (2017), p. 5.",
        "templates": (2, 3),
    },
    {
        "category": "CPAP",
        "topic": "CPAP troubleshooting no bubbles",
        "answerable": True,
        "answer": "If there are no continuous bubbles during CPAP, check that nasal prongs are attached properly and fit snugly, then check the circuit for leaks and increase air or oxygen flow according to the troubleshooting table.",
        "source_of_truth": "Bubble-CPAP Guidelines (2017), p. 6.",
        "templates": (0, 1),
    },
    {
        "category": "CPAP",
        "topic": "Pre-CPAP hypoxaemia checklist",
        "answerable": True,
        "answer": "Before starting CPAP, confirm oxygen is flowing, tubing is not leaking, prongs are fitted correctly, concentrator output is adequate if used, and assess for pleural effusion, pneumothorax, bronchospasm, heart disease, or inadequate respiratory effort.",
        "source_of_truth": "Bubble-CPAP Guidelines (2017), p. 2.",
        "templates": (2, 3),
    },
    {
        "category": "Outbreak",
        "topic": "Cholera outbreak trigger",
        "answerable": True,
        "answer": "For cholera, one suspected case (severe dehydration or death from acute watery diarrhoea in a patient aged 5 years or more) is enough to trigger notification and investigation.",
        "source_of_truth": "Pacific Outbreak Manual (2016), p. 31.",
        "templates": (0, 1),
    },
    {
        "category": "Outbreak",
        "topic": "Chikungunya analgesia choice",
        "answerable": True,
        "answer": "Chikungunya treatment is symptomatic and paracetamol is the drug of choice. Avoid aspirin and other NSAIDs because dengue fever is an important differential diagnosis.",
        "source_of_truth": "Pacific Outbreak Manual (2016), p. 28.",
        "templates": (2, 3),
    },
    {
        "category": "Immunization",
        "topic": "Vaccine refrigerator storage",
        "answerable": True,
        "answer": "Keep all vaccines in the main refrigerator compartment at 2–8°C, not in the freezer; only ice packs belong in the freezer compartment.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 67.",
        "templates": (0, 1),
    },
    {
        "category": "Immunization",
        "topic": "Measles vaccine with high fever",
        "answerable": True,
        "answer": "Measles vaccine should always be given even if there is a high temperature. Pentavalent and hepatitis B vaccines should be delayed until temperature falls if fever is above 38°C.",
        "source_of_truth": "PNG Standard Treatment Book (2016), pp. 43 and 67.",
        "templates": (2, 3),
    },
    {
        "category": "Immunization",
        "topic": "BCG birth dose",
        "answerable": True,
        "answer": "BCG should be given as soon as possible after birth: 0.05 ml intradermally in the left upper arm.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 68.",
        "templates": (0, 1),
    },
    {
        "category": "HIV",
        "topic": "HIV-exposed infant AZT prophylaxis >2500 g",
        "answerable": True,
        "answer": "For HIV-exposed infants from birth to 6 weeks with birthweight over 2500 g, give AZT 15 mg twice daily as infant prophylaxis when AZT is used.",
        "source_of_truth": "PNG Standard Treatment Book (2016), p. 65.",
        "templates": (2, 3),
    },
    {
        "category": "HIV",
        "topic": "Paediatric DTG 14–19.9 kg dose",
        "answerable": True,
        "answer": "For the DTG 10 mg scored dispersible tablet, the WHO-recommended once-daily dose for children weighing 14–19.9 kg is 2.5 tablets.",
        "source_of_truth": "Summary of PNG Preferred First-Line ART (November 2021), p. 1.",
        "templates": (0, 1),
    },
    {
        "category": "HIV",
        "topic": "DTG 50 mg transition weight",
        "answerable": True,
        "answer": "DTG 50 mg is the preferred DTG formulation starting at 20 kg; children in lower weight bands use DTG 10 mg scored dispersible tablets.",
        "source_of_truth": "Summary of PNG Preferred First-Line ART (November 2021), p. 1.",
        "templates": (2, 3),
    },
    {
        "category": "Infectious disease",
        "topic": "Rabies status in PNG",
        "answerable": True,
        "answer": "Rabies is not established in Papua New Guinea, although there is a large potential reservoir from imported dogs; once clinical rabies develops the prognosis is very poor even with intensive care.",
        "source_of_truth": "Paediatrics for Doctors in Papua New Guinea (2003), p. 339.",
        "templates": (0, 1),
    },
    {
        "category": "Obstetrics",
        "topic": "PPH high-risk anaemia in labour",
        "answerable": True,
        "answer": "Women with uncorrected anaemia in labour (Hb below 8 g%) are at much higher risk of shock and death from smaller postpartum haemorrhages and should be identified as higher-risk antenatally.",
        "source_of_truth": "PNG O&G Standard Management Manual (2018), p. 157.",
        "templates": (2, 3),
    },
    {
        "category": "Nutrition",
        "topic": "SAM target weight gain",
        "answerable": True,
        "answer": "During inpatient severe malnutrition treatment, good weight gain is defined as 10 g/kg/day, with weighing every second day.",
        "source_of_truth": "Management of Severe Malnutrition chart.",
        "templates": (0, 1),
    },
    # --- Unanswerable (15 topics) ---
    {
        "category": "Unanswerable",
        "topic": "Dengue vaccine schedule in PNG",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. The corpus discusses dengue clinical care and outbreak response but does not provide a PNG dengue vaccination schedule or product recommendations.",
        "source_of_truth": "Not in corpus.",
        "templates": (0, 1),
    },
    {
        "category": "Unanswerable",
        "topic": "OpenRouter model choice for on-device iOS RAG",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. The clinical document set does not contain mobile-app engineering or OpenRouter configuration guidance.",
        "source_of_truth": "Not in corpus.",
        "templates": (2, 3),
    },
    {
        "category": "Unanswerable",
        "topic": "PNG health worker salary grades",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. None of the 14 clinical documents include health workforce pay scales or salary grades.",
        "source_of_truth": "Not in corpus.",
        "templates": (0, 1),
    },
    {
        "category": "Unanswerable",
        "topic": "COVID-19 paediatric antiviral treatment protocol",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. COVID-19 is mentioned only in passing (for example TB/BCG context) and no paediatric COVID-19 antiviral treatment protocol is provided.",
        "source_of_truth": "Not in corpus.",
        "templates": (2, 3),
    },
    {
        "category": "Unanswerable",
        "topic": "Medical evacuation airline contract for remote PNG",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Referral and transfer are discussed clinically, but no aeromedical evacuation airline contracts or vendor names are listed.",
        "source_of_truth": "Not in corpus.",
        "templates": (0, 1),
    },
    {
        "category": "Unanswerable",
        "topic": "Retail price of snake antivenom in Kina",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Snake-bite management is covered clinically, but drug pricing or procurement costs are not documented.",
        "source_of_truth": "Not in corpus.",
        "templates": (2, 3),
    },
    {
        "category": "Unanswerable",
        "topic": "WhatsApp telemedicine consent policy",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. The corpus contains no telemedicine platform policies or WhatsApp consent standards.",
        "source_of_truth": "Not in corpus.",
        "templates": (0, 1),
    },
    {
        "category": "Unanswerable",
        "topic": "Paediatric brain tumour MRI contrast protocol",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Imaging protocols for paediatric brain tumours are not included in the supplied PNG/WHO clinical guidance set.",
        "source_of_truth": "Not in corpus.",
        "templates": (2, 3),
    },
    {
        "category": "Unanswerable",
        "topic": "Hepatitis C direct-acting antiviral first-line regimen for PNG",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Hepatitis C is referenced in HIV co-infection context, but no complete PNG first-line HCV DAA regimen is provided.",
        "source_of_truth": "Not in corpus.",
        "templates": (0, 1),
    },
    {
        "category": "Unanswerable",
        "topic": "Mpox ward negative-pressure airflow requirements",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Mpox/monkeypox isolation engineering specifications are not covered in the Pacific outbreak or hospital-care manuals supplied.",
        "source_of_truth": "Not in corpus.",
        "templates": (2, 3),
    },
    {
        "category": "Unanswerable",
        "topic": "Blockchain patient records for aid posts",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Health information system architecture and blockchain implementations are outside the clinical corpus.",
        "source_of_truth": "Not in corpus.",
        "templates": (0, 1),
    },
    {
        "category": "Unanswerable",
        "topic": "Expected iPhone battery life for offline mobile RAG",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Mobile hardware performance and battery-life estimates for on-device RAG are not clinical content in the corpus.",
        "source_of_truth": "Not in corpus.",
        "templates": (2, 3),
    },
    {
        "category": "Unanswerable",
        "topic": "PNG national cancer registry hotline number",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Cancer care is mentioned in general terms, but no national cancer registry telephone hotline is listed.",
        "source_of_truth": "Not in corpus.",
        "templates": (0, 1),
    },
    {
        "category": "Unanswerable",
        "topic": "Zika virus vaccine for pregnant women",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Zika appears in outbreak differential lists, but no Zika vaccination recommendations for pregnant women are provided.",
        "source_of_truth": "Not in corpus.",
        "templates": (2, 3),
    },
    {
        "category": "Unanswerable",
        "topic": "Swift CoreML embedding quantization bit width",
        "answerable": False,
        "answer": "This cannot be answered from the supplied documents. Software implementation details for Swift/CoreML embedding quantization are not part of the clinical document set.",
        "source_of_truth": "Not in corpus.",
        "templates": (0, 1),
    },
]

DOCUMENTS = [
    {"id": 1, "title": "Child Health for Nurses and Health Extension Officers in Papua New Guinea, 3rd ed. (2022)"},
    {"id": 2, "title": "Standard Treatment for Common Illnesses of Children in Papua New Guinea, 10th ed. (2016)"},
    {"id": 3, "title": "WHO Pocket Book of Hospital Care for Children, 2nd ed. (2013)"},
    {"id": 4, "title": "Paediatrics for Doctors in Papua New Guinea, 2nd ed. (2003)"},
    {"id": 5, "title": "WHO Oxygen Therapy for Children (2016)"},
    {"id": 6, "title": "Guidelines for use of Bubble-CPAP concentrators (2017)"},
    {"id": 7, "title": "Management of Severe Malnutrition chart"},
    {"id": 8, "title": "F-75 / F-100 Feeding Reference Cards"},
    {"id": 9, "title": "PNG National Guidelines for HIV Care and Treatment (2019)"},
    {"id": 10, "title": "NDoH Updated for Children - paediatric DTG update memo"},
    {"id": 11, "title": "Summary of PNG preferred first-line ART as of November 2021"},
    {"id": 12, "title": "WHO Operational Handbook on TB, Module 5: Children and Adolescents (2022)"},
    {"id": 13, "title": "Pacific Outbreak Manual, PPHSN (2016)"},
    {"id": 14, "title": "PNG Manual of Standard Managements in Obstetrics and Gynaecology, 7th ed. (2016; minor edits 2018)"},
]


def build_questions() -> list[dict]:
    questions: list[dict] = []
    qid = 1
    for item in TOPICS:
        for idx in item["templates"]:
            template_key, template_text = TEMPLATES[idx]
            questions.append(
                {
                    "id": qid,
                    "category": item["category"],
                    "topic": item["topic"],
                    "question_template": template_key,
                    "question": template_text.format(topic=item["topic"]),
                    "answer": item["answer"],
                    "source_of_truth": item["source_of_truth"],
                }
            )
            qid += 1
    return questions


def main() -> None:
    payload = {
        "metadata": {
            "title": "FrontlineAI - Set 2: Scenario-Based RAG Test Questions & Answers",
            "subtitle": "Papua New Guinea / WHO benchmark with mixed answerable and deliberately unanswerable items",
            "purpose": "Evaluation set for RAG grounding tests. Includes clinically answerable questions from the 14 supplied documents and deliberately unanswerable questions where the corpus lacks authoritative guidance. A correct system should cite sources for answerable items and refuse or state uncertainty for unanswerable ones.",
            "design": "Fifty topics x two scenario templates = 100 questions. Scenario templates differ from Set 1: night_shift_worker, parent_counselling, referral_decision, and doctor_on_call. Unanswerable items use category 'Unanswerable' and source_of_truth 'Not in corpus.'",
            "source_hierarchy": "1) Newer PNG/WHO updates for the exact topic; 2) PNG national standard-treatment guidance for local practice; 3) WHO technical guidance; 4) older PNG textbooks mainly as supporting context. The older 2003 paediatrics text was not allowed to override later treatment guidance.",
        },
        "questions": build_questions(),
        "documents_considered": DOCUMENTS,
        "clinical_validity_limitation": "Answers are constrained to the supplied documents. Unanswerable items are intentional negative tests; a clinically plausible guess without corpus support should be scored incorrect. Have appropriate PNG clinical leads review drug-dose and treatment-regimen items before production use.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    answerable = sum(1 for q in payload["questions"] if q["category"] != "Unanswerable")
    print(f"Wrote {len(payload['questions'])} questions to {OUT}")
    print(f"Answerable: {answerable}, Unanswerable: {len(payload['questions']) - answerable}")


if __name__ == "__main__":
    main()
