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

export interface TeamMember {
  role: string;
  name: string;
  desc: string;
}

export interface VolunteerGroup {
  group: string;
  desc: string;
}

export const BUS_SCHEDULE: BusRoute[] = [
  { time: "06:30", route: "Mala → Thrissur", type: "Private", notes: "First bus" },
  { time: "07:15", route: "Mala → Chalakudy", type: "Private", notes: "Via Annamanada" },
  { time: "08:00", route: "Mala → Thrissur", type: "KSRTC Fast", notes: "Limited stop" },
  { time: "09:30", route: "Mala → Kodungallur", type: "Private", notes: "Regular" },
  { time: "12:00", route: "Mala → Thrissur", type: "KSRTC Ordinary", notes: "Midday" },
  { time: "15:00", route: "Mala → Chalakudy", type: "Private", notes: "Return service" },
  { time: "17:30", route: "Mala → Thrissur", type: "KSRTC Fast", notes: "Evening rush" },
  { time: "19:45", route: "Mala → Thrissur", type: "Private", notes: "Last bus" },
];

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

export const FACILITIES: FacilityItem[] = [
  { title: "Green Room", titleI18n: "fac.green.title", sub: "Dressing · Annex 1st Floor", subI18n: "fac.green.sub", desc: "Rooms G1–G6 for dressing and pre-stage waiting.", descI18n: "fac.green.desc", location: "Annex Block, 1st Floor", href: "/facilities-green-room", tone: "teal", icon: "user" },
  { title: "Toilet", titleI18n: "fac.toilet.title", sub: "Washrooms · 3 Blocks", subI18n: "fac.toilet.sub", desc: "Washroom blocks A, B, C across the campus.", descI18n: "fac.toilet.desc", location: "Blocks A, B, C", href: "/facilities-toilet", tone: "blue", icon: "water" },
  { title: "Drinking Water", titleI18n: "fac.water.title", sub: "Filtered · 4 Stations", subI18n: "fac.water.sub", desc: "Filtered RO water dispensers with disposable cups.", descI18n: "fac.water.desc", location: "Main Block, Annex, Ground, Dining Hall", tone: "teal", icon: "sparkle" },
  { title: "Dining Hall", titleI18n: "fac.dining.title", sub: "Oottupura · Main Block GF", subI18n: "fac.dining.sub", desc: "Free meals for participants and accompanying teachers. Lunch from 12:30–14:30.", descI18n: "fac.dining.desc", location: "Main Block, Ground Floor", tone: "orange", icon: "grid" },
  { title: "Help Desk", titleI18n: "fac.help.title", sub: "Convener · Main Gate", subI18n: "fac.help.sub", desc: "General convener, chest-number queries, schedule changes, and volunteer dispatch.", descI18n: "fac.help.desc", location: "Main Gate / Control Room", href: "/help", tone: "purple", icon: "building" },
  { title: "Medical Room", titleI18n: "fac.med.title", sub: "First Aid · 24/7 Standby", subI18n: "fac.med.sub", desc: "Nursing staff, oxygen, stretcher, and emergency ambulance.", descI18n: "fac.med.desc", location: "Near Main Gate (west side)", href: "/help", tone: "rose", icon: "medical" },
];

export const RESULTS_CATEGORIES = {
  offstage: {
    badge: "Results · Off Stage",
    title: "Off Stage Results",
    items: ["Chithra Drawing", "Pencil Drawing", "Collage", "Cartoon", "Clay Modeling"],
  },
  individual: {
    badge: "Results · Individual Stage",
    title: "Individual Stage Results",
    items: ["Bharathanatyam", "Mohiniyattam", "Light Music", "Classical Music", "Elocution"],
  },
  group: {
    badge: "Results · Group Stage",
    title: "Group Stage Results",
    items: ["Oppana", "Margamkali", "Nadan Pattu", "Group Dance", "Drama"],
  },
};

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
