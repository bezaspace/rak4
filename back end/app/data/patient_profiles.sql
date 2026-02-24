CREATE TABLE IF NOT EXISTS patient_profiles (
  user_id TEXT PRIMARY KEY,
  full_name TEXT,
  age INTEGER,
  sex TEXT,
  conditions_json TEXT NOT NULL,
  treatments_json TEXT NOT NULL,
  allergies_json TEXT NOT NULL,
  contraindications_json TEXT NOT NULL,
  family_history_json TEXT NOT NULL,
  biomarker_targets_json TEXT NOT NULL,
  notes TEXT,
  updated_at TEXT NOT NULL
);

INSERT OR IGNORE INTO patient_profiles (
  user_id,
  full_name,
  age,
  sex,
  conditions_json,
  treatments_json,
  allergies_json,
  contraindications_json,
  family_history_json,
  biomarker_targets_json,
  notes,
  updated_at
) VALUES (
  'raksha-user',
  'Demo User A',
  49,
  'female',
  '[{"name":"Type 2 diabetes","status":"active"},{"name":"Hypertension","status":"active"}]',
  '[{"name":"Metformin","status":"ongoing","dosage":"500 mg twice daily"},{"name":"Losartan","status":"ongoing","dosage":"50 mg daily"}]',
  '["Penicillin"]',
  '["Systemic corticosteroids unless advised by clinician"]',
  '["Family history of cardiovascular disease"]',
  '[{"biomarker":"HbA1c","target":"< 7.0","unit":"%"},{"biomarker":"LDL-C","target":"< 70","unit":"mg/dL"},{"biomarker":"Blood Pressure","target":"< 130/80","unit":"mmHg"}]',
  'Prioritize cardio-metabolic risk reduction and medication adherence.',
  '2026-02-20T10:00:00Z'
);

INSERT OR IGNORE INTO patient_profiles (
  user_id,
  full_name,
  age,
  sex,
  conditions_json,
  treatments_json,
  allergies_json,
  contraindications_json,
  family_history_json,
  biomarker_targets_json,
  notes,
  updated_at
) VALUES (
  'raksha-user-b',
  'Demo User B',
  34,
  'male',
  '[{"name":"Hypothyroidism","status":"active"},{"name":"Vitamin D deficiency","status":"active"}]',
  '[{"name":"Levothyroxine","status":"ongoing","dosage":"75 mcg daily"},{"name":"Vitamin D3","status":"ongoing","dosage":"2000 IU daily"}]',
  '["No known drug allergies"]',
  '["Avoid unnecessary iodine supplementation"]',
  '["Family history of thyroid disorders"]',
  '[{"biomarker":"TSH","target":"0.5-2.5","unit":"mIU/L"},{"biomarker":"Free T4","target":"Within lab range"},{"biomarker":"Vitamin D (25-OH)","target":"30-50","unit":"ng/mL"}]',
  'Watch fatigue trend and sleep quality alongside thyroid labs.',
  '2026-02-20T10:00:00Z'
);
