export interface ProgramItem {
  item: string;
  cat: string;
  venue_n: number;
  day: string;
  time: string;
}

export const FESTIVAL_SCHEDULE: ProgramItem[] = [
  // ── DAY 1 · 17.11.2026 (Tuesday) · ON-STAGE ────────────────────────────────
  { item: "Sanghanritham LP", cat: "LP General", venue_n: 1, day: "Day 1 (17.11.2026)", time: "10:30 AM" },
  { item: "Bharathanatyam UP", cat: "UP General", venue_n: 1, day: "Day 1 (17.11.2026)", time: "12:20 PM" },
  { item: "Bharathanatyam HS (G)", cat: "HS General", venue_n: 1, day: "Day 1 (17.11.2026)", time: "01:50 PM" },
  { item: "Bharathanatyam HSS (G)", cat: "HSS General", venue_n: 1, day: "Day 1 (17.11.2026)", time: "03:00 PM" },

  { item: "Nadodi Nritham LP", cat: "LP General", venue_n: 2, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Nadodi Nritham HSS (G)", cat: "HSS General", venue_n: 2, day: "Day 1 (17.11.2026)", time: "12:30 PM" },
  { item: "Nadodi Nritham HS (B)", cat: "HS General", venue_n: 2, day: "Day 1 (17.11.2026)", time: "01:30 PM" },
  { item: "Nadodi Nritham UP", cat: "UP General", venue_n: 2, day: "Day 1 (17.11.2026)", time: "01:40 PM" },
  { item: "Sanghanritham UP", cat: "UP General", venue_n: 2, day: "Day 1 (17.11.2026)", time: "03:10 PM" },
  { item: "Nadodi Nritham HS (G)", cat: "HS General", venue_n: 2, day: "Day 1 (17.11.2026)", time: "04:10 PM" },

  { item: "Nadakam HS", cat: "HS General", venue_n: 3, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Nadakam HSS", cat: "HSS General", venue_n: 3, day: "Day 1 (17.11.2026)", time: "10:30 AM" },
  { item: "Nadakam UP", cat: "UP General", venue_n: 3, day: "Day 1 (17.11.2026)", time: "12:30 PM" },
  { item: "Chavittunadakam HSS", cat: "HSS General", venue_n: 3, day: "Day 1 (17.11.2026)", time: "01:10 PM" },
  { item: "Chavittunadakam HS", cat: "HS General", venue_n: 3, day: "Day 1 (17.11.2026)", time: "01:30 PM" },
  { item: "Mookabhinayam (Mime) HSS", cat: "HSS General", venue_n: 3, day: "Day 1 (17.11.2026)", time: "02:30 PM" },
  { item: "Mookabhinayam (Mime) HS", cat: "HS General", venue_n: 3, day: "Day 1 (17.11.2026)", time: "03:00 PM" },

  { item: "Prasangam Sanskrit UP", cat: "UP Sanskrit", venue_n: 5, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Prasangam Sanskrit HS", cat: "HS Sanskrit", venue_n: 5, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Ganalapanam Sanskrit UP", cat: "UP Sanskrit", venue_n: 5, day: "Day 1 (17.11.2026)", time: "09:40 AM" },
  { item: "Padyam Chollal Sanskrit UP (B)", cat: "UP Sanskrit", venue_n: 5, day: "Day 1 (17.11.2026)", time: "11:00 AM" },
  { item: "Padyam Chollal Sanskrit UP (G)", cat: "UP Sanskrit", venue_n: 5, day: "Day 1 (17.11.2026)", time: "12:10 PM" },
  { item: "Aksharaslokam / Ashtapadi Sanskrit UP", cat: "UP Sanskrit", venue_n: 5, day: "Day 1 (17.11.2026)", time: "01:30 PM" },

  { item: "Kathakali / Storytelling LP", cat: "LP General", venue_n: 6, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Recitation LP", cat: "LP General", venue_n: 6, day: "Day 1 (17.11.2026)", time: "10:30 AM" },

  { item: "Samoohagaanam / Group Song LP", cat: "LP General", venue_n: 7, day: "Day 1 (17.11.2026)", time: "09:30 AM" },

  { item: "Action Song (English) LP", cat: "LP General", venue_n: 8, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Poem Recitation (English) LP", cat: "LP General", venue_n: 8, day: "Day 1 (17.11.2026)", time: "01:30 PM" },

  // ── DAY 1 · 17.11.2026 (Tuesday) · OFF-STAGE (VENUES 10–25) ────────────────
  { item: "Upanyasam (Essay) Sanskrit UP", cat: "UP Sanskrit", venue_n: 10, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Upanyasam (Essay) Sanskrit HS", cat: "HS Sanskrit", venue_n: 10, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Upanyasam (Essay) Sanskrit HSS", cat: "HSS General", venue_n: 10, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Kadharachana (Story) Sanskrit UP", cat: "UP Sanskrit", venue_n: 10, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Kadharachana (Story) Sanskrit HS", cat: "HS Sanskrit", venue_n: 10, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Kadharachana (Story) Sanskrit HSS", cat: "HSS General", venue_n: 10, day: "Day 1 (17.11.2026)", time: "11:30 AM" },

  { item: "Kavitharachana (Poem) Sanskrit UP", cat: "UP Sanskrit", venue_n: 11, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Kavitharachana (Poem) Sanskrit HS", cat: "HS Sanskrit", venue_n: 11, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Kavitharachana (Poem) Sanskrit HSS", cat: "HSS General", venue_n: 11, day: "Day 1 (17.11.2026)", time: "09:30 AM" },

  { item: "Samasyapooranam Sanskrit UP", cat: "UP Sanskrit", venue_n: 12, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Samasyapooranam Sanskrit HS", cat: "HS Sanskrit", venue_n: 12, day: "Day 1 (17.11.2026)", time: "09:30 AM" },

  { item: "Essay Writing - English HS", cat: "HS General", venue_n: 13, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Essay Writing - English HSS", cat: "HSS General", venue_n: 13, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Poem Writing - English UP", cat: "UP General", venue_n: 13, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Poem Writing - English HS", cat: "HS General", venue_n: 13, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Poem Writing - English HSS", cat: "HSS General", venue_n: 13, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Story Writing - English HS", cat: "HS General", venue_n: 13, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Story Writing - English HSS", cat: "HSS General", venue_n: 13, day: "Day 1 (17.11.2026)", time: "11:30 AM" },

  { item: "Story Writing - Kannada & Tamil HS", cat: "HS General", venue_n: 14, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Poem Writing - Tamil HS", cat: "HS General", venue_n: 14, day: "Day 1 (17.11.2026)", time: "11:30 AM" },

  { item: "Story Writing - Hindi UP", cat: "UP General", venue_n: 15, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Story Writing - Hindi HS", cat: "HS General", venue_n: 15, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Story Writing - Hindi HSS", cat: "HSS General", venue_n: 15, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Essay Writing - Hindi HS", cat: "HS General", venue_n: 15, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Essay Writing - Hindi HSS", cat: "HSS General", venue_n: 15, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Poem Writing - Hindi HS", cat: "HS General", venue_n: 15, day: "Day 1 (17.11.2026)", time: "01:30 PM" },
  { item: "Poem Writing - Hindi HSS", cat: "HSS General", venue_n: 15, day: "Day 1 (17.11.2026)", time: "01:30 PM" },

  { item: "Chithra Rachana Pencil LP", cat: "LP General", venue_n: 16, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Water Colouring LP", cat: "LP General", venue_n: 16, day: "Day 1 (17.11.2026)", time: "11:30 AM" },

  { item: "Chithra Rachana Pencil UP", cat: "UP General", venue_n: 17, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Water Colouring UP", cat: "UP General", venue_n: 17, day: "Day 1 (17.11.2026)", time: "11:30 AM" },

  { item: "Chithra Rachana Pencil HS", cat: "HS General", venue_n: 18, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Chithra Rachana Pencil HSS", cat: "HSS General", venue_n: 18, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Water Colouring HS", cat: "HS General", venue_n: 18, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Water Colouring HSS", cat: "HSS General", venue_n: 18, day: "Day 1 (17.11.2026)", time: "11:30 AM" },

  { item: "Oil Painting HS", cat: "HS General", venue_n: 19, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Oil Painting HSS", cat: "HSS General", venue_n: 19, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Cartoon Rachana HS", cat: "HS General", venue_n: 19, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Cartoon Rachana HSS", cat: "HSS General", venue_n: 19, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Collage Nirmanam HSS", cat: "HSS General", venue_n: 19, day: "Day 1 (17.11.2026)", time: "01:30 PM" },

  { item: "Story Writing - Malayalam UP", cat: "UP General", venue_n: 20, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Story Writing - Malayalam HS", cat: "HS General", venue_n: 20, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Poem Writing - Malayalam UP", cat: "UP General", venue_n: 20, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Poem Writing - Malayalam HS", cat: "HS General", venue_n: 20, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Essay Writing - Malayalam HS", cat: "HS General", venue_n: 20, day: "Day 1 (17.11.2026)", time: "01:30 PM" },

  { item: "Story Writing - Malayalam HSS", cat: "HSS General", venue_n: 21, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Poem Writing - Malayalam HSS", cat: "HSS General", venue_n: 21, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Essay Writing - Malayalam HSS", cat: "HSS General", venue_n: 21, day: "Day 1 (17.11.2026)", time: "01:30 PM" },

  { item: "Story Writing - Urdu HS", cat: "HS General", venue_n: 22, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Story Writing - Urdu HSS", cat: "HSS General", venue_n: 22, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Poem Writing - Urdu HS", cat: "HS General", venue_n: 22, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Poem Writing - Urdu HSS", cat: "HSS General", venue_n: 22, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Essay Writing - Urdu HS", cat: "HS General", venue_n: 22, day: "Day 1 (17.11.2026)", time: "01:30 PM" },
  { item: "Essay Writing - Urdu HSS", cat: "HSS General", venue_n: 22, day: "Day 1 (17.11.2026)", time: "01:30 PM" },

  { item: "Arabic Quiz LP", cat: "LP Arabic", venue_n: 23, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Arabic Quiz UP", cat: "UP Arabic", venue_n: 23, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Arabic Handwriting LP", cat: "LP Arabic", venue_n: 23, day: "Day 1 (17.11.2026)", time: "10:00 AM" },
  { item: "Arabic Aksharakkali / Word Game LP", cat: "LP Arabic", venue_n: 23, day: "Day 1 (17.11.2026)", time: "10:30 AM" },
  { item: "Arabic Translation UP", cat: "UP Arabic", venue_n: 23, day: "Day 1 (17.11.2026)", time: "11:00 AM" },
  { item: "Arabic Padakeli UP", cat: "UP Arabic", venue_n: 23, day: "Day 1 (17.11.2026)", time: "11:30 AM" },

  { item: "Story Writing - Arabic HS", cat: "HS Arabic", venue_n: 24, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Story Writing - Arabic HSS", cat: "HSS General", venue_n: 24, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Poem Writing - Arabic HS", cat: "HS Arabic", venue_n: 24, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Poem Writing - Arabic HSS", cat: "HSS General", venue_n: 24, day: "Day 1 (17.11.2026)", time: "11:30 AM" },
  { item: "Essay Writing - Arabic HS", cat: "HS Arabic", venue_n: 24, day: "Day 1 (17.11.2026)", time: "01:30 PM" },
  { item: "Essay Writing - Arabic HSS", cat: "HSS General", venue_n: 24, day: "Day 1 (17.11.2026)", time: "01:30 PM" },

  { item: "Arabic Prashnothari (Quiz) HS", cat: "HS Arabic", venue_n: 25, day: "Day 1 (17.11.2026)", time: "09:30 AM" },
  { item: "Arabic Note / Caption Writing HS", cat: "HS Arabic", venue_n: 25, day: "Day 1 (17.11.2026)", time: "10:00 AM" },
  { item: "Arabic Translation HS", cat: "HS Arabic", venue_n: 25, day: "Day 1 (17.11.2026)", time: "10:30 AM" },
  { item: "Arabic Poster Making HS", cat: "HS Arabic", venue_n: 25, day: "Day 1 (17.11.2026)", time: "11:00 AM" },
  { item: "Arabic Dictionary Making HS", cat: "HS Arabic", venue_n: 25, day: "Day 1 (17.11.2026)", time: "11:30 AM" },

  // ── DAY 2 · 18.11.2026 (Wednesday) ─────────────────────────────────────────
  { item: "Sanghagaanam UP / HS", cat: "HS General", venue_n: 1, day: "Day 2 (18.11.2026)", time: "09:00 AM" },
  { item: "Sanghagaanam LP", cat: "LP General", venue_n: 1, day: "Day 2 (18.11.2026)", time: "10:10 AM" },
  { item: "Sanghagaanam HSS", cat: "HSS General", venue_n: 1, day: "Day 2 (18.11.2026)", time: "10:40 AM" },
  { item: "Deshabhakthigaanam UP", cat: "UP General", venue_n: 1, day: "Day 2 (18.11.2026)", time: "11:00 AM" },
  { item: "Deshabhakthigaanam HS", cat: "HS General", venue_n: 1, day: "Day 2 (18.11.2026)", time: "11:50 AM" },
  { item: "Kuchuppudi HS (G)", cat: "HS General", venue_n: 1, day: "Day 2 (18.11.2026)", time: "12:10 PM" },
  { item: "Kuchuppudi UP", cat: "UP General", venue_n: 1, day: "Day 2 (18.11.2026)", time: "01:50 PM" },
  { item: "Keralanadanam HS (G)", cat: "HS General", venue_n: 1, day: "Day 2 (18.11.2026)", time: "02:30 PM" },
  { item: "Keralanadanam HSS (G)", cat: "HSS General", venue_n: 1, day: "Day 2 (18.11.2026)", time: "04:15 PM" },

  { item: "English Skit HS", cat: "HS General", venue_n: 3, day: "Day 2 (18.11.2026)", time: "09:00 AM" },
  { item: "English Skit HSS", cat: "HSS General", venue_n: 3, day: "Day 2 (18.11.2026)", time: "09:50 AM" },
  { item: "English Skit UP", cat: "UP General", venue_n: 3, day: "Day 2 (18.11.2026)", time: "10:20 AM" },
  { item: "Prasangam English UP", cat: "UP General", venue_n: 3, day: "Day 2 (18.11.2026)", time: "10:40 AM" },
  { item: "Prasangam English HS", cat: "HS General", venue_n: 3, day: "Day 2 (18.11.2026)", time: "11:00 AM" },
  { item: "Prasangam English HSS", cat: "HSS General", venue_n: 3, day: "Day 2 (18.11.2026)", time: "11:30 AM" },
  { item: "English Poem Recitation HS", cat: "HS General", venue_n: 3, day: "Day 2 (18.11.2026)", time: "12:10 PM" },
  { item: "English Poem Recitation HSS", cat: "HSS General", venue_n: 3, day: "Day 2 (18.11.2026)", time: "01:30 PM" },
  { item: "English Poem Recitation UP", cat: "UP General", venue_n: 3, day: "Day 2 (18.11.2026)", time: "02:00 PM" },

  { item: "Arabic Recitation & Cultural Items", cat: "HS Arabic", venue_n: 9, day: "Day 2 (18.11.2026)", time: "09:00 AM" },

  // ── DAY 3 · 19.11.2026 (Thursday) ──────────────────────────────────────────
  { item: "Mohiniyattam HS", cat: "HS General", venue_n: 1, day: "Day 3 (19.11.2026)", time: "09:00 AM" },
  { item: "Mohiniyattam HSS", cat: "HSS General", venue_n: 1, day: "Day 3 (19.11.2026)", time: "09:40 AM" },
  { item: "Thiruvathirakkali HSS", cat: "HSS General", venue_n: 1, day: "Day 3 (19.11.2026)", time: "09:50 AM" },
  { item: "Thiruvathirakkali UP", cat: "UP General", venue_n: 1, day: "Day 3 (19.11.2026)", time: "10:00 AM" },
  { item: "Margamkali HS", cat: "HS General", venue_n: 1, day: "Day 3 (19.11.2026)", time: "10:15 AM" },
  { item: "Margamkali HSS", cat: "HSS General", venue_n: 1, day: "Day 3 (19.11.2026)", time: "10:50 AM" },
  { item: "Oppana UP", cat: "UP Arabic", venue_n: 1, day: "Day 3 (19.11.2026)", time: "11:20 AM" },
  { item: "Oppana HSS", cat: "HSS General", venue_n: 1, day: "Day 3 (19.11.2026)", time: "12:05 PM" },
  { item: "Oppana HS", cat: "HS Arabic", venue_n: 1, day: "Day 3 (19.11.2026)", time: "12:15 PM" },
  { item: "Thiruvathirakkali HS", cat: "HS General", venue_n: 1, day: "Day 3 (19.11.2026)", time: "01:00 PM" },

  { item: "Kavithaparayanam Malayalam HSS", cat: "HSS General", venue_n: 3, day: "Day 3 (19.11.2026)", time: "09:00 AM" },
  { item: "Kavithaparayanam Malayalam UP", cat: "UP General", venue_n: 3, day: "Day 3 (19.11.2026)", time: "09:40 AM" },
  { item: "Kavithaparayanam Malayalam HS", cat: "HS General", venue_n: 3, day: "Day 3 (19.11.2026)", time: "11:40 AM" },
  { item: "Kavithaparayanam Malayalam LP", cat: "LP General", venue_n: 3, day: "Day 3 (19.11.2026)", time: "12:30 PM" },

  { item: "Prasangam & Recitation (Arabic)", cat: "HS Arabic", venue_n: 9, day: "Day 3 (19.11.2026)", time: "09:00 AM" },

  { item: "Band Display (Band Melam) HS", cat: "HS General", venue_n: 26, day: "Day 3 (19.11.2026)", time: "11:00 AM" },

  // ── DAY 4 · 20.11.2026 (Friday) ────────────────────────────────────────────
  { item: "Vanchippattu HS", cat: "HS General", venue_n: 2, day: "Day 4 (20.11.2026)", time: "01:30 PM" },

  { item: "Chenda / Maddalam HS", cat: "HS General", venue_n: 3, day: "Day 4 (20.11.2026)", time: "09:00 AM" },
  { item: "Chendamelam HSS", cat: "HSS General", venue_n: 3, day: "Day 4 (20.11.2026)", time: "09:30 AM" },
  { item: "Melam HS", cat: "HS General", venue_n: 3, day: "Day 4 (20.11.2026)", time: "10:00 AM" },

  { item: "Recitation / Quran Parayanam LP", cat: "LP Arabic", venue_n: 4, day: "Day 4 (20.11.2026)", time: "09:00 AM" },
  { item: "Recitation / Quran Parayanam UP", cat: "UP Arabic", venue_n: 4, day: "Day 4 (20.11.2026)", time: "11:00 AM" },
  { item: "Recitation / Quran Parayanam HS", cat: "HS Arabic", venue_n: 4, day: "Day 4 (20.11.2026)", time: "12:05 PM" },
  { item: "Recitation HSS", cat: "HSS General", venue_n: 4, day: "Day 4 (20.11.2026)", time: "12:10 PM" },

  { item: "Padyam Chollal Sanskrit UP", cat: "UP Sanskrit", venue_n: 5, day: "Day 4 (20.11.2026)", time: "09:00 AM" },
  { item: "Padyam Chollal Sanskrit HSS", cat: "HSS General", venue_n: 5, day: "Day 4 (20.11.2026)", time: "09:25 AM" },
  { item: "Kathakali Sangeetham UP", cat: "UP General", venue_n: 5, day: "Day 4 (20.11.2026)", time: "11:40 AM" },
  { item: "Kathakali Sangeetham HS", cat: "HS General", venue_n: 5, day: "Day 4 (20.11.2026)", time: "12:10 PM" },
  { item: "Kathaprasangam HS", cat: "HS General", venue_n: 5, day: "Day 4 (20.11.2026)", time: "02:30 PM" }
];
