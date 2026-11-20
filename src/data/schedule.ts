export interface ProgramItem {
  item: string;
  cat: string;
  venue_n: number;
  day: string;
  time: string;
}

export const FESTIVAL_SCHEDULE: ProgramItem[] = [
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

  // Venue 3 - GMLPS, Mala (Chendamelam followed by Sanskrit Drama from Venue 5)
  { item: "Chenda / Thayambaka HS", cat: "HS General", venue_n: 3, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Chendamelam HSS", cat: "HSS General", venue_n: 3, day: "Friday (20.11.2026)", time: "09:30 AM" },
  { item: "Chendamelam HS", cat: "HS General", venue_n: 3, day: "Friday (20.11.2026)", time: "10:00 AM" },
  { item: "Nadakam (Sanskrit) UP", cat: "UP Sanskrit", venue_n: 3, day: "Friday (20.11.2026)", time: "After Chendamelam" },
  { item: "Nadakam (Sanskrit) HS", cat: "HS Sanskrit", venue_n: 3, day: "Friday (20.11.2026)", time: "After Chendamelam" },

  // Venue 4 - HSS Hall II Floor (Arabic General)
  { item: "Padyam Chollal (Arabic) LP", cat: "LP Arabic", venue_n: 4, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Padyam Chollal (Arabic) UP", cat: "UP Arabic", venue_n: 4, day: "Friday (20.11.2026)", time: "11:00 AM" },
  { item: "Padyam Chollal (Arabic) HS", cat: "HS Arabic", venue_n: 4, day: "Friday (20.11.2026)", time: "12:05 PM" },
  { item: "Padyam Chollal (Arabic) HSS", cat: "HSS General", venue_n: 4, day: "Friday (20.11.2026)", time: "12:10 PM" },

  // Venue 5 - Silver Jubilee Hall III Floor (Moved from Venue 7 Vyapara Bhavan)
  { item: "Mono Act LP", cat: "LP General", venue_n: 5, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Mono Act UP", cat: "UP General", venue_n: 5, day: "Friday (20.11.2026)", time: "10:40 AM" },
  { item: "Mono Act HSS (B)", cat: "HSS General", venue_n: 5, day: "Friday (20.11.2026)", time: "11:40 AM" },
  { item: "Mono Act HSS (G)", cat: "HSS General", venue_n: 5, day: "Friday (20.11.2026)", time: "11:50 AM" },
  { item: "Mono Act HS (B)", cat: "HS General", venue_n: 5, day: "Friday (20.11.2026)", time: "12:10 PM" },
  { item: "Mono Act HS (G)", cat: "HS General", venue_n: 5, day: "Friday (20.11.2026)", time: "12:30 PM" },
  { item: "Mimicry HS (B)", cat: "HS General", venue_n: 5, day: "Friday (20.11.2026)", time: "01:10 PM" },
  { item: "Mimicry HS (G)", cat: "HS General", venue_n: 5, day: "Friday (20.11.2026)", time: "01:30 PM" },
  { item: "Kathaprasangam HSS", cat: "HSS General", venue_n: 5, day: "Friday (20.11.2026)", time: "02:00 PM" },
  { item: "Kathaprasangam UP", cat: "UP General", venue_n: 5, day: "Friday (20.11.2026)", time: "02:10 PM" },
  { item: "Kathaprasangam HS", cat: "HS General", venue_n: 5, day: "Friday (20.11.2026)", time: "03:00 PM" },

  // Venue 6 - HSS Hall III Floor East (Sanskrit items excluding Drama moved from Venue 5)
  { item: "Padyam Chollal Sanskrit HSS (SKT)", cat: "HSS General", venue_n: 6, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Prasangam Sanskrit HSS (SKT)", cat: "HSS General", venue_n: 6, day: "Friday (20.11.2026)", time: "09:25 AM" },
  { item: "Pathakam (Sanskrit) HS (B)", cat: "HS Sanskrit", venue_n: 6, day: "Friday (20.11.2026)", time: "09:30 AM" },
  { item: "Pathakam (Sanskrit) HS (G)", cat: "HS Sanskrit", venue_n: 6, day: "Friday (20.11.2026)", time: "10:15 AM" },
  { item: "Aksharaslokam Sanskrit UP", cat: "UP Sanskrit", venue_n: 6, day: "Friday (20.11.2026)", time: "11:40 AM" },
  { item: "Aksharaslokam Sanskrit HS", cat: "HS Sanskrit", venue_n: 6, day: "Friday (20.11.2026)", time: "12:10 PM" },

  // Venue 8 - E1 Class (HSS)
  { item: "Prasangam Malayalam HS", cat: "HS General", venue_n: 8, day: "Friday (20.11.2026)", time: "09:00 AM" },
  { item: "Prasangam Malayalam UP", cat: "UP General", venue_n: 8, day: "Friday (20.11.2026)", time: "10:00 AM" },
  { item: "Prasangam Malayalam HSS", cat: "HSS General", venue_n: 8, day: "Friday (20.11.2026)", time: "10:30 AM" },
  { item: "Aksharaslokam HS", cat: "HS General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:15 AM" },
  { item: "Aksharaslokam HSS", cat: "HSS General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:20 AM" },
  { item: "Aksharaslokam UP", cat: "UP General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:25 AM" },
  { item: "Kavyakeli HS", cat: "HS General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:30 AM" },
  { item: "Kavyakeli HSS", cat: "HSS General", venue_n: 8, day: "Friday (20.11.2026)", time: "11:35 AM" }
];
