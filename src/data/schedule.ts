export interface ProgramItem {
  item: string;
  cat: string;
  venue_n: number;
  day: string;
  time: string;
}

export const FESTIVAL_SCHEDULE: ProgramItem[] = [
  // ── THURSDAY · 19.11.2026 (Day 3) ──────────────────────────────────────────
  // Venue 2 - HS Hall (Moved from Stage 1; yesterday's finished items removed)
  { item: "Kolkali HS", cat: "HS Arabic", venue_n: 2, day: "Thursday (19.11.2026)", time: "09:00 AM" },
  { item: "Oppana HS", cat: "HS Arabic", venue_n: 2, day: "Thursday (19.11.2026)", time: "09:40 AM" },
  { item: "Parichamuttukali HS", cat: "HS General", venue_n: 2, day: "Thursday (19.11.2026)", time: "09:50 AM" },
  { item: "Parichamuttukali HSS", cat: "HSS General", venue_n: 2, day: "Thursday (19.11.2026)", time: "10:00 AM" },
  { item: "Poorakkali HS", cat: "HS General", venue_n: 2, day: "Thursday (19.11.2026)", time: "11:20 AM" },
  { item: "Poorakkali HSS", cat: "HSS General", venue_n: 2, day: "Thursday (19.11.2026)", time: "12:05 PM" },
  { item: "Duffmuttu HS", cat: "HS Arabic", venue_n: 2, day: "Thursday (19.11.2026)", time: "12:15 PM" },
  { item: "Duffmuttu HSS", cat: "HSS General", venue_n: 2, day: "Thursday (19.11.2026)", time: "01:00 PM" },

  // Venue 3 - GMLPS, Mala (Interchanged with Venue 7 Vyapara Bhavan)
  { item: "Sanghagaanam UP", cat: "UP General", venue_n: 3, day: "Thursday (19.11.2026)", time: "09:00 AM" },
  { item: "Sanghagaanam HSS", cat: "HSS General", venue_n: 3, day: "Thursday (19.11.2026)", time: "11:50 AM" },
  { item: "Sanghagaanam HS", cat: "HS General", venue_n: 3, day: "Thursday (19.11.2026)", time: "12:50 PM" },
  { item: "Deshabhakthigaanam UP", cat: "UP General", venue_n: 3, day: "Thursday (19.11.2026)", time: "01:30 PM" },
  { item: "Deshabhakthigaanam HSS", cat: "HSS General", venue_n: 3, day: "Thursday (19.11.2026)", time: "03:00 PM" },
  { item: "Deshabhakthigaanam HS", cat: "HS General", venue_n: 3, day: "Thursday (19.11.2026)", time: "03:30 PM" },

  // Venue 4 - HSS Hall II Floor (Tomorrow's Nadan Pattu removed)
  { item: "Abhinayagaanam LP", cat: "LP General", venue_n: 4, day: "Thursday (19.11.2026)", time: "09:00 AM" },
  { item: "Sanghagaanam UP", cat: "UP General", venue_n: 4, day: "Thursday (19.11.2026)", time: "10:00 AM" },
  { item: "Sanghagaanam HS", cat: "HS General", venue_n: 4, day: "Thursday (19.11.2026)", time: "11:00 AM" },
  { item: "Sanghagaanam HSS", cat: "HSS General", venue_n: 4, day: "Thursday (19.11.2026)", time: "11:40 AM" },
  { item: "Deshabhakthigaanam UP", cat: "UP General", venue_n: 4, day: "Thursday (19.11.2026)", time: "12:10 PM" },
  { item: "Deshabhakthigaanam HS", cat: "HS General", venue_n: 4, day: "Thursday (19.11.2026)", time: "02:00 PM" },
  { item: "Prasangam UP", cat: "UP General", venue_n: 4, day: "Thursday (19.11.2026)", time: "03:15 PM" },
  { item: "Prasangam HS", cat: "HS General", venue_n: 4, day: "Thursday (19.11.2026)", time: "04:00 PM" },

  // Venue 5 - Silver Jubilee Hall III Floor (Yesterday's Kathakali Sangeetham HS removed)
  { item: "Ashtapadi Sanskrit HS (B)", cat: "HS Sanskrit", venue_n: 5, day: "Thursday (19.11.2026)", time: "09:00 AM" },
  { item: "Sanghagaanam Sanskrit UP", cat: "UP Sanskrit", venue_n: 5, day: "Thursday (19.11.2026)", time: "10:00 AM" },
  { item: "Aksharaslokam Sanskrit UP", cat: "UP Sanskrit", venue_n: 5, day: "Thursday (19.11.2026)", time: "11:30 AM" },
  { item: "Aksharaslokam Sanskrit HS", cat: "HS Sanskrit", venue_n: 5, day: "Thursday (19.11.2026)", time: "11:40 AM" },
  { item: "Ganalapanam Sanskrit HS (B)", cat: "HS Sanskrit", venue_n: 5, day: "Thursday (19.11.2026)", time: "01:30 PM" },
  { item: "Ganalapanam Sanskrit HSS", cat: "HSS General", venue_n: 5, day: "Thursday (19.11.2026)", time: "02:15 PM" },
  { item: "Ganalapanam Sanskrit HS (G)", cat: "HS Sanskrit", venue_n: 5, day: "Thursday (19.11.2026)", time: "03:30 PM" },

  // Venue 6 - HSS Hall III Floor East
  { item: "Mappilappattu HS (B)", cat: "HS Arabic", venue_n: 6, day: "Thursday (19.11.2026)", time: "09:00 AM" },
  { item: "Mappilappattu HS (G)", cat: "HS Arabic", venue_n: 6, day: "Thursday (19.11.2026)", time: "09:30 AM" },
  { item: "Mappilappattu HSS (B)", cat: "HSS General", venue_n: 6, day: "Thursday (19.11.2026)", time: "10:20 AM" },
  { item: "Mappilappattu UP", cat: "UP Arabic", venue_n: 6, day: "Thursday (19.11.2026)", time: "10:50 AM" },
  { item: "Mappilappattu HSS (G)", cat: "HSS General", venue_n: 6, day: "Thursday (19.11.2026)", time: "02:00 PM" },
  { item: "Mappilappattu LP", cat: "LP Arabic", venue_n: 6, day: "Thursday (19.11.2026)", time: "02:30 PM" },

  // Venue 7 - Vyapara Bhavan Old (Interchanged with Venue 3 GMLPS Mala)
  { item: "Padyam Chollal Malayalam HSS", cat: "HSS General", venue_n: 7, day: "Thursday (19.11.2026)", time: "09:00 AM" },
  { item: "Padyam Chollal Malayalam UP", cat: "UP General", venue_n: 7, day: "Thursday (19.11.2026)", time: "09:40 AM" },
  { item: "Padyam Chollal Malayalam HS", cat: "HS General", venue_n: 7, day: "Thursday (19.11.2026)", time: "11:40 AM" },
  { item: "Padyam Chollal Malayalam LP", cat: "LP General", venue_n: 7, day: "Thursday (19.11.2026)", time: "12:30 PM" },

  // Venue 8 - E1 Class (HSS) · Today is Lalithagaanam (moved from Friday)
  { item: "Lalithagaanam LP", cat: "LP General", venue_n: 8, day: "Thursday (19.11.2026)", time: "09:00 AM" },
  { item: "Lalithagaanam UP", cat: "UP General", venue_n: 8, day: "Thursday (19.11.2026)", time: "11:30 AM" },
  { item: "Lalithagaanam HS (B)", cat: "HS General", venue_n: 8, day: "Thursday (19.11.2026)", time: "02:00 PM" },
  { item: "Lalithagaanam HSS (B)", cat: "HSS General", venue_n: 8, day: "Thursday (19.11.2026)", time: "02:40 PM" },
  { item: "Lalithagaanam HSS (G)", cat: "HSS General", venue_n: 8, day: "Thursday (19.11.2026)", time: "03:20 PM" },
  { item: "Lalithagaanam HS (G)", cat: "HS General", venue_n: 8, day: "Thursday (19.11.2026)", time: "04:00 PM" },

  // Venue 9 - HS II Floor · Today is Kannada (Arabic Padyam Chollal moved to Friday Venue 4)
  { item: "Prasangam (Kannada) HS", cat: "HS General", venue_n: 9, day: "Thursday (19.11.2026)", time: "09:00 AM" },
  { item: "Prasangam (Kannada) UP", cat: "UP General", venue_n: 9, day: "Thursday (19.11.2026)", time: "09:10 AM" },
  { item: "Prasangam (Kannada) LP", cat: "LP General", venue_n: 9, day: "Thursday (19.11.2026)", time: "09:20 AM" },
  { item: "Padyam Chollal (Kannada) HS", cat: "HS General", venue_n: 9, day: "Thursday (19.11.2026)", time: "10:00 AM" },
  { item: "Padyam Chollal (Kannada) UP", cat: "UP General", venue_n: 9, day: "Thursday (19.11.2026)", time: "10:35 AM" },
  { item: "Padyam Chollal (Kannada) HSS", cat: "HSS General", venue_n: 9, day: "Thursday (19.11.2026)", time: "12:30 PM" },
  { item: "Padyam Chollal (Kannada) LP", cat: "LP General", venue_n: 9, day: "Thursday (19.11.2026)", time: "01:00 PM" },

  // Venue 26 - Maliekkal Garden
  { item: "Band Melam HS", cat: "HS General", venue_n: 26, day: "Thursday (19.11.2026)", time: "11:00 AM" },

  // ── FRIDAY · 20.11.2026 (Day 4) ────────────────────────────────────────────
  // Venue 1 - School Ground
  { item: "Thiruvathirakkali UP", cat: "UP General", venue_n: 1, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Thiruvathirakkali HS", cat: "HS General", venue_n: 1, day: "Friday (20.11.2026)", time: "09:30 AM" },
  { item: "Thiruvathirakkali HSS", cat: "HSS General", venue_n: 1, day: "Friday (20.11.2026)", time: "10:30 AM" },
  { item: "Mohiniyattam HS (G)", cat: "HS General", venue_n: 1, day: "Friday (20.11.2026)", time: "11:30 AM" },
  { item: "Kathakali HS (G)", cat: "HS General", venue_n: 1, day: "Friday (20.11.2026)", time: "01:30 PM" },
  { item: "Kathakali HSS (G)", cat: "HSS General", venue_n: 1, day: "Friday (20.11.2026)", time: "02:10 PM" },

  // Venue 2 - HS Hall (Includes Margamkali HS & HSS moved to Friday)
  { item: "Nadan Pattu HSS", cat: "HSS General", venue_n: 2, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Nadan Pattu HS", cat: "HS General", venue_n: 2, day: "Friday (20.11.2026)", time: "09:40 AM" },
  { item: "Vanchippattu HSS", cat: "HSS General", venue_n: 2, day: "Friday (20.11.2026)", time: "11:45 AM" },
  { item: "Vanchippattu HS", cat: "HS General", venue_n: 2, day: "Friday (20.11.2026)", time: "01:30 PM" },
  { item: "Margamkali HS", cat: "HS General", venue_n: 2, day: "Friday (20.11.2026)", time: "Time TBD" },
  { item: "Margamkali HSS", cat: "HSS General", venue_n: 2, day: "Friday (20.11.2026)", time: "Time TBD" },

  // Venue 3 - GMLPS, Mala (Interchanged with Venue 7 Vyapara Bhavan)
  { item: "Mono Act LP", cat: "LP General", venue_n: 3, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Mono Act UP", cat: "UP General", venue_n: 3, day: "Friday (20.11.2026)", time: "10:40 AM" },
  { item: "Mono Act HSS (B)", cat: "HSS General", venue_n: 3, day: "Friday (20.11.2026)", time: "11:40 AM" },
  { item: "Mono Act HSS (G)", cat: "HSS General", venue_n: 3, day: "Friday (20.11.2026)", time: "11:50 AM" },
  { item: "Mono Act HS (B)", cat: "HS General", venue_n: 3, day: "Friday (20.11.2026)", time: "12:10 PM" },
  { item: "Mono Act HS (G)", cat: "HS General", venue_n: 3, day: "Friday (20.11.2026)", time: "12:30 PM" },
  { item: "Mimicry HS (B)", cat: "HS General", venue_n: 3, day: "Friday (20.11.2026)", time: "01:10 PM" },
  { item: "Mimicry HS (G)", cat: "HS General", venue_n: 3, day: "Friday (20.11.2026)", time: "01:30 PM" },
  { item: "Vattappattu HSS", cat: "HSS General", venue_n: 3, day: "Friday (20.11.2026)", time: "02:00 PM" },
  { item: "Vattappattu UP", cat: "UP Arabic", venue_n: 3, day: "Friday (20.11.2026)", time: "02:10 PM" },
  { item: "Vattappattu HS", cat: "HS Arabic", venue_n: 3, day: "Friday (20.11.2026)", time: "03:00 PM" },

  // Venue 4 - HSS Hall II Floor (Arabic Padyam Chollal)
  { item: "Padyam Chollal (Arabic) LP", cat: "LP Arabic", venue_n: 4, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Padyam Chollal (Arabic) UP", cat: "UP Arabic", venue_n: 4, day: "Friday (20.11.2026)", time: "11:00 AM" },
  { item: "Padyam Chollal (Arabic) HS", cat: "HS Arabic", venue_n: 4, day: "Friday (20.11.2026)", time: "12:05 PM" },
  { item: "Padyam Chollal (Arabic) HSS", cat: "HSS General", venue_n: 4, day: "Friday (20.11.2026)", time: "12:10 PM" },

  // Venue 5 - Silver Jubilee Hall III Floor
  { item: "Padyam Chollal Sanskrit HSS (SKT)", cat: "HSS General", venue_n: 5, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Prasangam Sanskrit HSS (SKT)", cat: "HSS General", venue_n: 5, day: "Friday (20.11.2026)", time: "09:25 AM" },
  { item: "Pathakam HS (B)", cat: "HS Sanskrit", venue_n: 5, day: "Friday (20.11.2026)", time: "09:30 AM" },
  { item: "Pathakam HS (G)", cat: "HS Sanskrit", venue_n: 5, day: "Friday (20.11.2026)", time: "10:15 AM" },
  { item: "Aksharaslokam Sanskrit UP", cat: "UP Sanskrit", venue_n: 5, day: "Friday (20.11.2026)", time: "11:40 AM" },
  { item: "Aksharaslokam Sanskrit HS", cat: "HS Sanskrit", venue_n: 5, day: "Friday (20.11.2026)", time: "12:10 PM" },
  { item: "Nadakam UP", cat: "UP General", venue_n: 5, day: "Friday (20.11.2026)", time: "12:30 PM" },
  { item: "Nadakam HS", cat: "HS General", venue_n: 5, day: "Friday (20.11.2026)", time: "02:30 PM" },

  // Venue 7 - Vyapara Bhavan Old (Interchanged with Venue 3 GMLPS Mala)
  { item: "Chenda / Thayambaka HS", cat: "HS General", venue_n: 7, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Chendamelam HSS", cat: "HSS General", venue_n: 7, day: "Friday (20.11.2026)", time: "09:30 AM" },
  { item: "Chendamelam HS", cat: "HS General", venue_n: 7, day: "Friday (20.11.2026)", time: "10:00 AM" },

  // Venue 8 - E1 Class (HSS) · Tomorrow is Prasangam Malayalam, Aksharaslokam & Kavyakeli
  { item: "Prasangam Malayalam HS", cat: "HS General", venue_n: 8, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Prasangam Malayalam UP", cat: "UP General", venue_n: 8, day: "Friday (20.11.2026)", time: "10:00 AM" },
  { item: "Prasangam Malayalam HSS", cat: "HSS General", venue_n: 8, day: "Friday (20.11.2026)", time: "10:30 AM" },
  { item: "Aksharaslokam HS", cat: "HS General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:15 AM" },
  { item: "Aksharaslokam HSS", cat: "HSS General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:20 AM" },
  { item: "Aksharaslokam UP", cat: "UP General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:25 AM" },
  { item: "Kavyakeli HS", cat: "HS General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:30 AM" },
  { item: "Kavyakeli HSS", cat: "HSS General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:35 AM" }
];
