CREATE TABLE IF NOT EXISTS schedule_items (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  activity_type TEXT NOT NULL,
  title TEXT NOT NULL,
  instructions_json TEXT NOT NULL,
  window_start_local TEXT NOT NULL,
  window_end_local TEXT NOT NULL,
  display_order INTEGER NOT NULL DEFAULT 0,
  active BOOLEAN NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS adherence_reports (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  schedule_item_id TEXT NOT NULL,
  report_date_local TEXT NOT NULL,
  activity_type TEXT NOT NULL,
  status TEXT NOT NULL,
  followed_plan BOOLEAN NOT NULL,
  changes_made TEXT,
  felt_after TEXT,
  symptoms TEXT,
  notes TEXT,
  alert_level TEXT NOT NULL DEFAULT 'none',
  summary TEXT NOT NULL,
  reported_at_iso TEXT NOT NULL,
  conversation_turn_id TEXT,
  session_id TEXT,
  created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO schedule_items (
  id, user_id, activity_type, title, instructions_json, window_start_local, window_end_local, display_order, active, created_at, updated_at
) VALUES (
  'sched_raksha_user_breakfast',
  'raksha-user',
  'diet',
  'Breakfast',
  '["1 cup vegetable oats","1 boiled egg or sprouts","Take water before meal"]',
  '08:00',
  '08:45',
  1,
  1,
  '2026-02-20T10:00:00Z',
  '2026-02-20T10:00:00Z'
);

INSERT OR IGNORE INTO schedule_items (
  id, user_id, activity_type, title, instructions_json, window_start_local, window_end_local, display_order, active, created_at, updated_at
) VALUES (
  'sched_raksha_user_med_morning',
  'raksha-user',
  'medication',
  'Morning Medication',
  '["Metformin 500 mg","Losartan 50 mg","Take after breakfast"]',
  '09:00',
  '09:30',
  2,
  1,
  '2026-02-20T10:00:00Z',
  '2026-02-20T10:00:00Z'
);

INSERT OR IGNORE INTO schedule_items (
  id, user_id, activity_type, title, instructions_json, window_start_local, window_end_local, display_order, active, created_at, updated_at
) VALUES (
  'sched_raksha_user_lunch',
  'raksha-user',
  'diet',
  'Lunch',
  '["1 cup dal + vegetables","2 phulkas","No sugary drink"]',
  '13:00',
  '14:00',
  3,
  1,
  '2026-02-20T10:00:00Z',
  '2026-02-20T10:00:00Z'
);

INSERT OR IGNORE INTO schedule_items (
  id, user_id, activity_type, title, instructions_json, window_start_local, window_end_local, display_order, active, created_at, updated_at
) VALUES (
  'sched_raksha_user_walk_evening',
  'raksha-user',
  'activity',
  'Evening Walk',
  '["30-minute brisk walk","Maintain comfortable pace","Hydrate after walk"]',
  '18:00',
  '19:00',
  4,
  1,
  '2026-02-20T10:00:00Z',
  '2026-02-20T10:00:00Z'
);

INSERT OR IGNORE INTO schedule_items (
  id, user_id, activity_type, title, instructions_json, window_start_local, window_end_local, display_order, active, created_at, updated_at
) VALUES (
  'sched_raksha_user_sleep',
  'raksha-user',
  'sleep',
  'Night Sleep',
  '["Lights off by 10:30 PM","No screen 30 mins prior","Aim for 7-8 hours"]',
  '22:00',
  '23:59',
  5,
  1,
  '2026-02-20T10:00:00Z',
  '2026-02-20T10:00:00Z'
);

INSERT OR IGNORE INTO schedule_items (
  id, user_id, activity_type, title, instructions_json, window_start_local, window_end_local, display_order, active, created_at, updated_at
) VALUES (
  'sched_raksha_user_b_breakfast',
  'raksha-user-b',
  'diet',
  'Protein Breakfast',
  '["2 idlis + sambar or oats","Take thyroid medicine on empty stomach first"]',
  '08:00',
  '08:45',
  1,
  1,
  '2026-02-20T10:00:00Z',
  '2026-02-20T10:00:00Z'
);
