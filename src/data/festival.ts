export interface BusRoute {
  time: string;
  route: string;
  type: string;
  notes: string;
}

export interface AutoDriver {
  name: string;
  sub: string;
  desc: string;
  phone: string;
}

export interface FacilityItem {
  title: string;
  titleI18n?: string;
  sub: string;
  subI18n?: string;
  desc: string;
  descI18n?: string;
  location: string;
  href?: string;
  tone: string;
  icon: string;
}

export interface LiveStreamItem {
  stage: string;
  title: string;
  channel: string;
  desc: string;
  url: string;
  tone: string;
}

export interface TeamMember {
  role: string;
  name: string;
  desc: string;
}

export interface VolunteerGroup {
  group: string;
  desc: string;
}

export interface BusService {
  sl: number;
  time: string;
  route: string;
  type: string;
  duty?: string;
  notes?: string;
}

export const MALA_TO_ALUVA_BUSES: BusService[] = [
  { sl: 1, time: "03:45", route: "Mala → Aluva → Thiruvananthapuram (TVM)", type: "KSRTC", duty: "2", notes: "Via Aluva" },
  { sl: 2, time: "04:40", route: "Mala → Aluva → Thiruvananthapuram (TVM)", type: "KSRTC", duty: "4", notes: "Via Aluva" },
  { sl: 3, time: "05:10", route: "Mala → Aluva → Ernakulam (EKM)", type: "KSRTC", duty: "56", notes: "Via Aluva" },
  { sl: 4, time: "05:40", route: "Mala → Aluva → Kollam (KLM/CLD)", type: "KSRTC", duty: "3", notes: "Via Chalakudy" },
  { sl: 5, time: "06:10", route: "Mala → Aluva (EVTR)", type: "KSRTC", duty: "17", notes: "EVTR service" },
  { sl: 6, time: "06:30", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "18", notes: "Regular" },
  { sl: 7, time: "07:00", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "21", notes: "Regular" },
  { sl: 8, time: "07:10", route: "Mala → Aluva (EVTR)", type: "KSRTC", duty: "25", notes: "EVTR service" },
  { sl: 9, time: "07:45", route: "Mala → Aluva → Ernakulam (EKM)", type: "KSRTC Fast", duty: "5", notes: "To Ernakulam" },
  { sl: 10, time: "08:10", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "32", notes: "Morning peak" },
  { sl: 11, time: "09:15", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "18", notes: "Regular" },
  { sl: 12, time: "10:10", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "21", notes: "Regular" },
  { sl: 13, time: "10:25", route: "Mala → Aluva (EVTR)", type: "KSRTC", duty: "29", notes: "EVTR service" },
  { sl: 14, time: "10:40", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "17", notes: "Regular" },
  { sl: 15, time: "11:20", route: "Mala → Aluva (EVTR)", type: "KSRTC", duty: "32", notes: "EVTR service" },
  { sl: 16, time: "12:20", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "18", notes: "Midday" },
  { sl: 17, time: "13:20", route: "Mala → Aluva (EVTR)", type: "KSRTC", duty: "11", notes: "EVTR service" },
  { sl: 18, time: "13:35", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "21", notes: "Regular" },
  { sl: 19, time: "14:00", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "29", notes: "Regular" },
  { sl: 20, time: "14:40", route: "Mala → Aluva (EVTR)", type: "KSRTC", duty: "32", notes: "EVTR service" },
  { sl: 21, time: "15:00", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "34", notes: "Afternoon" },
  { sl: 22, time: "15:50", route: "Mala → Aluva (VNR)", type: "KSRTC", duty: "18", notes: "VNR service" },
  { sl: 23, time: "16:15", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "13", notes: "Evening" },
  { sl: 24, time: "16:25", route: "Mala → Aluva (ANDA)", type: "KSRTC", duty: "25", notes: "Via Annamanada" },
  { sl: 25, time: "17:00", route: "Mala → Aluva → Thiruvananthapuram (TVM)", type: "KSRTC Fast", duty: "1", notes: "Evening limited stop" },
  { sl: 26, time: "17:10", route: "Mala → Aluva", type: "KSRTC Ordinary", duty: "12", notes: "Evening rush" },
  { sl: 27, time: "17:20", route: "Mala → Aluva (EVTR)", type: "KSRTC", duty: "17", notes: "EVTR service" },
];

export const ALUVA_TO_MALA_BUSES: BusService[] = [
  { sl: 1, time: "07:30", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "17", notes: "Morning first" },
  { sl: 2, time: "07:55", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "18", notes: "Regular" },
  { sl: 3, time: "08:25", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "21", notes: "Morning peak" },
  { sl: 4, time: "08:50", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "25", notes: "Regular" },
  { sl: 5, time: "09:50", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "32", notes: "Regular" },
  { sl: 6, time: "10:40", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "18", notes: "Regular" },
  { sl: 7, time: "11:35", route: "Aluva → Mala", type: "KSRTC Super Fast (SFP)", duty: "1", notes: "Fast service" },
  { sl: 8, time: "11:45", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "21", notes: "Regular" },
  { sl: 9, time: "11:50", route: "Aluva → Mala (EVTR)", type: "KSRTC", duty: "29", notes: "EVTR service" },
  { sl: 10, time: "12:05", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "17", notes: "Midday" },
  { sl: 11, time: "12:45", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "32", notes: "Regular" },
  { sl: 12, time: "13:50", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "18", notes: "Afternoon" },
  { sl: 13, time: "14:45", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "11", notes: "Regular" },
  { sl: 14, time: "15:00", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "21", notes: "Regular" },
  { sl: 15, time: "15:25", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "29", notes: "Regular" },
  { sl: 16, time: "16:10", route: "Aluva → Mala (EVTR)", type: "KSRTC", duty: "32", notes: "EVTR service" },
  { sl: 17, time: "17:05", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "25", notes: "Evening rush" },
  { sl: 18, time: "17:15", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "18", notes: "Evening" },
  { sl: 19, time: "17:35", route: "Aluva → Mala (EVTR)", type: "KSRTC", duty: "13", notes: "EVTR service" },
  { sl: 20, time: "18:05", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "56", notes: "Evening" },
  { sl: 21, time: "18:45", route: "Aluva → Mala", type: "KSRTC Ordinary", duty: "12", notes: "Night service" },
  { sl: 22, time: "19:10", route: "Aluva → Mala (EVTR)", type: "KSRTC", duty: "17", notes: "EVTR service" },
  { sl: 23, time: "19:30", route: "Aluva → Mala", type: "KSRTC Super Fast (SFP)", duty: "2", notes: "Fast service" },
  { sl: 24, time: "20:45", route: "Aluva → Mala", type: "KSRTC Super Fast (SFP)", duty: "3", notes: "Late night fast" },
  { sl: 25, time: "21:00", route: "Aluva → Mala", type: "KSRTC Fast Passenger (FP)", duty: "5", notes: "Night service" },
  { sl: 26, time: "21:50", route: "Aluva → Mala", type: "KSRTC Super Fast (SFP)", duty: "4", notes: "Last bus to Mala" },
];

export const OTHER_BUS_ROUTES: BusRoute[] = [
  { time: "06:30", route: "Mala → Thrissur", type: "Private", notes: "First morning bus" },
  { time: "07:15", route: "Mala → Chalakudy", type: "Private", notes: "Via Annamanada" },
  { time: "08:00", route: "Mala → Thrissur", type: "KSRTC Fast", notes: "Limited stop" },
  { time: "09:30", route: "Mala → Kodungallur", type: "Private", notes: "Regular" },
  { time: "12:00", route: "Mala → Thrissur", type: "KSRTC Ordinary", notes: "Midday" },
  { time: "15:00", route: "Mala → Chalakudy", type: "Private", notes: "Return service" },
  { time: "17:30", route: "Mala → Thrissur", type: "KSRTC Fast", notes: "Evening rush" },
  { time: "19:45", route: "Mala → Thrissur", type: "Private", notes: "Last bus to Thrissur" },
];

export const BUS_SCHEDULE = OTHER_BUS_ROUTES;

export const AUTO_DRIVERS: AutoDriver[] = [
  { name: "Anil T. V.", sub: "Auto · Mala Junction", desc: "Quick hops to bus stand and railway station. Meter + ₹10 festival surcharge.", phone: "+919999000103" },
  { name: "Shibu P.", sub: "Auto · 5-Seater", desc: "Shared auto for groups up to 5. Mala ↔ Annamanada fixed fare.", phone: "+919999000105" },
  { name: "Suresh N.", sub: "Auto · Mala Town", desc: "Local trips within Mala town. Cash / UPI. Available on call from 5 AM.", phone: "+919999000107" },
  { name: "Manoj K.", sub: "Auto · Bus Stand", desc: "Standby near Mala Bus Stand. Direct trips to the school main gate on request.", phone: "+919999000108" },
  { name: "Varghese P.", sub: "Auto · Annamanada Route", desc: "Regular driver on the Mala ↔ Annamanada route.", phone: "+919000000109" },
];

export const GREEN_ROOMS = [
  { name: "Rooms G1 & G2", sub: "Boys · Annex 1st Floor", desc: "Dressing space for male participants in the HS General category.", loc: "Annex Block, 1st Floor, East Stairs" },
  { name: "Rooms G3 & G4", sub: "Girls · Annex 1st Floor", desc: "Dressing space for female participants. Full-length mirrors and electrical points.", loc: "Annex Block, 1st Floor, West Stairs" },
  { name: "Rooms G5 & G6", sub: "Common · Annex 1st Floor", desc: "Shared rooms for HSS General and team items.", loc: "Annex Block, 1st Floor, North Wing" },
];

export const TOILET_BLOCKS = [
  { name: "Block A", sub: "Main Block · Ground Floor", desc: "Main washroom block. Separate sections for boys and girls.", loc: "Main Block, GF, North Corridor" },
  { name: "Block B", sub: "Annex Block · 1st Floor", desc: "Nearest washroom to the green rooms.", loc: "Annex Block, 1st Floor, Next to G3" },
  { name: "Block C", sub: "Ground Wing · Near Stage 2", desc: "Open-air stage side washroom.", loc: "Ground Wing, East of Stage 2" },
];

export const WATER_STATIONS = [
  { name: "Station W1", sub: "Main Block · Ground Floor", desc: "Filtered RO drinking water cooler with disposable cups.", loc: "Main Block, GF, Central Verandah" },
  { name: "Station W2", sub: "Annex Block · Near Green Rooms", desc: "Dedicated chilled water dispenser for stage performers.", loc: "Annex Block, Ground Floor Entrance" },
  { name: "Station W3", sub: "Main Ground · Stage 1 Side", desc: "High-capacity water point for spectators and teams.", loc: "Main Ground, West Side near Canteen" },
  { name: "Station W4", sub: "Dining Hall (Oottupura)", desc: "Filtered drinking water and handwash counters.", loc: "Main Block, GF, Dining Wing" },
];

export const DINING_HALLS = [
  { name: "Main Oottupura", sub: "Lunch · 12:30 – 14:30", desc: "Free traditional meals for registered participants, escort teachers, and volunteers.", loc: "Main Block, Ground Floor, East Wing" },
  { name: "Refreshment Counter", sub: "Light Snacks · All Day", desc: "Drinking water, lime juice, and light refreshments for performers between items.", loc: "Near Main Ground Flag Post" },
];

export const LIVE_STREAMS: LiveStreamItem[] = [
  {
    stage: "Stage 1",
    title: "St. Antony's HSS Ground",
    channel: "Official Main Stage Stream",
    desc: "Live telecast of flagship dance, group, and open-air events from Stage 1.",
    url: "https://www.youtube.com/",
    tone: "rose",
  },
  {
    stage: "Stage 2",
    title: "HS Hall",
    channel: "Indoor Auditorium Stream",
    desc: "Live coverage of classical music, recitation, and indoor competitions from Stage 2.",
    url: "https://www.youtube.com/",
    tone: "blue",
  },
  {
    stage: "Stage 5",
    title: "HSS Seminar Hall",
    channel: "Seminar Hall Stream",
    desc: "Live stream of literary, elocution, and stage events from Stage 5.",
    url: "https://www.youtube.com/",
    tone: "purple",
  },
];

export const FACILITIES: FacilityItem[] = [
  { title: "Green Room", sub: "Dressing · Annex 1st Floor", desc: "Rooms G1–G6 for dressing and pre-stage waiting.", location: "Annex Block, 1st Floor", href: "/facilities-green-room", tone: "teal", icon: "user" },
  { title: "Toilet", sub: "Washrooms · 3 Blocks", desc: "Washroom blocks A, B, C across the campus.", location: "Blocks A, B, C", href: "/facilities-toilet", tone: "blue", icon: "water" },
  { title: "Drinking Water", sub: "Filtered · 4 Stations", desc: "Filtered RO water dispensers with disposable cups.", location: "4 Campus Stations", href: "/facilities-water", tone: "teal", icon: "sparkle" },
  { title: "Dining Hall", sub: "Oottupura · Main Block GF", desc: "Free meals for participants and accompanying teachers. Lunch from 12:30–14:30.", location: "Main Block, Ground Floor", href: "/facilities-dining", tone: "orange", icon: "grid" },
  { title: "Help Desk", sub: "Convener · Main Gate", desc: "General convener, chest-number queries, schedule changes, and volunteer dispatch.", location: "Main Gate / Control Room", href: "/help", tone: "purple", icon: "building" },
  { title: "Medical Room", sub: "First Aid · 24/7 Standby", desc: "Nursing staff, oxygen, stretcher, and emergency ambulance.", location: "Near Main Gate (west side)", href: "/help", tone: "rose", icon: "medical" },
];

export const TEAM_MEMBERS: TeamMember[] = [
  { role: "Lead Architect", name: "Name 1", desc: "Full-stack Frontend, Backend FastAPI API, Infrastructure & CI/CD Pipeline." },
  { role: "UI/UX Designer", name: "Name 2", desc: "Design System, Glassmorphism Animations, Micro-interactions & Accessibility." },
  { role: "Systems Admin", name: "Name 3", desc: "Deployment, Reverse Proxy, SQLite WAL Database & Automated Backups." },
  { role: "Data HR", name: "Name 4", desc: "Participant Data Management, Schedule Synchronization & Validation." },
  { role: "Logo Designer 1", name: "Name 5", desc: "Master Logo Branding, Vector Assets & Festival Visual Identity." },
  { role: "Logo Designer 2", name: "Name 6", desc: "PWA Iconography, Watermark Graphics & Promotional Banners." },
];

export const VOLUNTEERS: VolunteerGroup[] = [
  { group: "Coordination Team", desc: "Overall festival coordination, stage timing oversight, and committee liaison." },
  { group: "Media & Stage Captures", desc: "High-resolution stage performance photography and candid gallery management." },
  { group: "Streaming & Recording", desc: "Live streaming telecasts, stage video capture, and archive maintenance." },
  { group: "Post-Production Desk", desc: "Instant highlight reels, media sorting, and daily photo/video publishing." },
  { group: "Help & Stage Control", desc: "Chest number reporting, convener assistance, and stage queue management." },
  { group: "Backend & Database Ops", desc: "Real-time SSE monitoring, server uptime, and database backups." },
];
