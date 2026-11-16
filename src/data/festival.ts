export interface KSRTCBus {
  time: string;
  board: string;
  via: string;
  type: string;
  extra?: string;
}

// -----------------------------------------------------------------------------
// 1. MALA ↔ THRISSUR (Via Kodakara / KDA)
// -----------------------------------------------------------------------------
export const MALA_TO_TSR: KSRTCBus[] = [
  { time: "04:50", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (05:30)", type: "Ordinary" },
  { time: "05:10", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (05:50)", type: "Ordinary" },
  { time: "05:30", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (06:10)", type: "Ordinary" },
  { time: "05:40", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (06:10)", type: "Fast Passenger" },
  { time: "05:50", board: "MALA - MOONNUPEEDIKA - THRISSUR", via: "Moonnupeedika · Kodakara", type: "Ordinary" },
  { time: "05:50", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (06:35)", type: "Ordinary" },
  { time: "06:10", board: "MALA - KODAKARA", via: "Direct Kodakara", type: "Ordinary" },
  { time: "06:30", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (07:10)", type: "Ordinary" },
  { time: "07:00", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (07:30)", type: "Fast Passenger" },
  { time: "07:05", board: "MALA - KODAKARA", via: "Direct Kodakara", type: "Ordinary" },
  { time: "07:15", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (07:55)", type: "Ordinary" },
  { time: "07:30", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (08:10)", type: "Ordinary" },
  { time: "07:50", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (08:30)", type: "Ordinary" },
  { time: "08:00", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (08:30)", type: "Fast Passenger" },
  { time: "08:10", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (08:50)", type: "Ordinary" },
  { time: "08:30", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (09:10)", type: "Ordinary" },
  { time: "08:40", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (09:10)", type: "Fast Passenger" },
  { time: "09:00", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (09:30)", type: "Ordinary" },
  { time: "09:20", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (10:00)", type: "Ordinary" },
  { time: "09:45", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (10:25)", type: "Ordinary" },
  { time: "10:00", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (10:30)", type: "Ordinary" },
  { time: "10:20", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (11:00)", type: "Ordinary" },
  { time: "10:40", board: "MALA - GURUVAYUR", via: "Kodakara (11:20) · Thrissur", type: "Ordinary" },
  { time: "11:00", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (11:40)", type: "Ordinary" },
  { time: "11:20", board: "MALA - MOONNUPEEDIKA - THRISSUR", via: "Moonnupeedika", type: "Ordinary" },
  { time: "11:40", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (12:20)", type: "Ordinary" },
  { time: "12:00", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (12:40)", type: "Ordinary" },
  { time: "12:40", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (13:20)", type: "Ordinary" },
  { time: "13:20", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (14:00)", type: "Ordinary" },
  { time: "13:40", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (14:20)", type: "Ordinary" },
  { time: "14:00", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (14:40)", type: "Ordinary" },
  { time: "14:15", board: "MALA - MOONNUPEEDIKA - THRISSUR", via: "Moonnupeedika", type: "Ordinary" },
  { time: "14:40", board: "MALA - GURUVAYUR", via: "Kodakara (15:20) · Thrissur", type: "Ordinary" },
  { time: "15:00", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (15:40)", type: "Ordinary" },
  { time: "15:20", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (16:00)", type: "Ordinary" },
  { time: "15:40", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (16:20)", type: "Ordinary" },
  { time: "16:10", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (16:50)", type: "Ordinary" },
  { time: "16:30", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (17:10)", type: "Ordinary" },
  { time: "16:50", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (17:30)", type: "Ordinary" },
  { time: "17:05", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (17:55)", type: "Ordinary" },
  { time: "17:30", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (18:10)", type: "Ordinary" },
  { time: "17:50", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara (19:30)", type: "Ordinary" },
  { time: "18:40", board: "MALA - KODAKARA - THRISSUR", via: "Kodakara", type: "Ordinary" },
];

export const TSR_TO_MALA: KSRTCBus[] = [
  { time: "06:30", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (07:20)", type: "Ordinary" },
  { time: "06:50", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (07:40)", type: "Ordinary" },
  { time: "07:00", board: "KODAKARA - MALA", via: "Direct to Mala", type: "Ordinary" },
  { time: "07:10", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (08:00)", type: "Ordinary" },
  { time: "07:30", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (08:20)", type: "Ordinary" },
  { time: "07:40", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (08:30)", type: "Ordinary" },
  { time: "07:50", board: "KODAKARA - MALA", via: "Direct to Mala", type: "Ordinary" },
  { time: "08:10", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (09:00)", type: "Ordinary" },
  { time: "08:30", board: "THRISSUR - MOONNUPEEDIKA - MALA", via: "Moonnupeedika", type: "Ordinary" },
  { time: "08:40", board: "GURUVAYUR - THRISSUR - MALA", via: "Kodakara", type: "Ordinary" },
  { time: "08:55", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (09:45)", type: "Ordinary" },
  { time: "09:15", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (10:05)", type: "Ordinary" },
  { time: "09:30", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (10:20)", type: "Ordinary" },
  { time: "10:00", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (10:50)", type: "Ordinary" },
  { time: "10:10", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (11:00)", type: "Ordinary" },
  { time: "10:40", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (11:30)", type: "Ordinary" },
  { time: "11:00", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (11:50)", type: "Ordinary" },
  { time: "11:20", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (12:10)", type: "Ordinary" },
  { time: "11:40", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (12:30)", type: "Ordinary" },
  { time: "12:00", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (12:50)", type: "Ordinary" },
  { time: "12:20", board: "GURUVAYUR - THRISSUR - MALA", via: "Kodakara (13:10)", type: "Ordinary" },
  { time: "12:40", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (13:30)", type: "Ordinary" },
  { time: "13:35", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (14:25)", type: "Ordinary" },
  { time: "14:00", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (14:50)", type: "Ordinary" },
  { time: "14:20", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (15:10)", type: "Ordinary" },
  { time: "14:40", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (15:30)", type: "Ordinary" },
  { time: "15:00", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (15:50)", type: "Ordinary" },
  { time: "15:20", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (16:10)", type: "Ordinary" },
  { time: "15:50", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (16:40)", type: "Ordinary" },
  { time: "16:10", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (17:00)", type: "Ordinary" },
  { time: "16:40", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (17:30)", type: "Ordinary" },
  { time: "17:00", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (17:50)", type: "Ordinary" },
  { time: "17:20", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (18:10)", type: "Ordinary" },
  { time: "17:30", board: "THRISSUR - MOONNUPEEDIKA - MALA", via: "Moonnupeedika", type: "Ordinary" },
  { time: "17:50", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (18:40)", type: "Ordinary" },
  { time: "18:10", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (19:00)", type: "Ordinary" },
  { time: "18:30", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (19:20)", type: "Ordinary" },
  { time: "18:45", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (19:35)", type: "Ordinary" },
  { time: "19:10", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (20:00)", type: "Ordinary" },
  { time: "19:30", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (20:20)", type: "Ordinary" },
  { time: "20:15", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara", type: "Ordinary" },
  { time: "20:30", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (21:00)", type: "Fast Passenger" },
  { time: "21:30", board: "THRISSUR - KODAKARA - MALA", via: "Kodakara (22:00)", type: "Fast Passenger" },
];

// -----------------------------------------------------------------------------
// 2. MALA ↔ ALUVA (Via Annamanada / Eravathur)
// -----------------------------------------------------------------------------
export const MALA_TO_ALV: KSRTCBus[] = [
  { time: "03:45", board: "MALA - THIRUVANANTHAPURAM", via: "Aluva · Ernakulam", type: "Fast Passenger" },
  { time: "04:40", board: "MALA - THIRUVANANTHAPURAM", via: "Aluva · Ernakulam", type: "Fast Passenger" },
  { time: "05:10", board: "MALA - ERNAKULAM", via: "Annamanada · Aluva", type: "Ordinary" },
  { time: "05:40", board: "MALA - KOLLAM", via: "Chalakudy · Aluva", type: "Ordinary" },
  { time: "06:10", board: "MALA - ERAVATHUR - ALUVA", via: "Eravathur · Annamanada", type: "Ordinary" },
  { time: "06:30", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "07:00", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "07:10", board: "MALA - ERAVATHUR - ALUVA", via: "Eravathur · Annamanada", type: "Ordinary" },
  { time: "07:45", board: "MALA - ERNAKULAM", via: "Annamanada · Aluva", type: "Fast Passenger" },
  { time: "08:10", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "09:15", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "10:10", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "10:25", board: "MALA - ERAVATHUR - ALUVA", via: "Eravathur · Annamanada", type: "Ordinary" },
  { time: "10:40", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "11:20", board: "MALA - ERAVATHUR - ALUVA", via: "Eravathur · Annamanada", type: "Ordinary" },
  { time: "12:20", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "13:20", board: "MALA - ERAVATHUR - ALUVA", via: "Eravathur · Annamanada", type: "Ordinary" },
  { time: "13:35", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "14:00", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "14:40", board: "MALA - ERAVATHUR - ALUVA", via: "Eravathur · Annamanada", type: "Ordinary" },
  { time: "15:00", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "15:50", board: "MALA - VENNUR - ALUVA", via: "Vennur · Annamanada", type: "Ordinary" },
  { time: "16:15", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "16:25", board: "MALA - ANNAMANADA - ALUVA", via: "Annamanada Direct", type: "Ordinary" },
  { time: "17:00", board: "MALA - THIRUVANANTHAPURAM", via: "Aluva · Ernakulam", type: "Fast Passenger" },
  { time: "17:10", board: "MALA - ALUVA", via: "Meladoor · Annamanada", type: "Ordinary" },
  { time: "17:20", board: "MALA - ERAVATHUR - ALUVA", via: "Eravathur · Annamanada", type: "Ordinary" },
];

export const ALV_TO_MALA: KSRTCBus[] = [
  { time: "07:30", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "07:55", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "08:25", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "08:50", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "09:50", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "10:40", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "11:35", board: "ALUVA - MALA", via: "Annamanada", type: "Super Fast" },
  { time: "11:45", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "11:50", board: "ALUVA - ERAVATHUR - MALA", via: "Eravathur", type: "Ordinary" },
  { time: "12:05", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "12:45", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "13:50", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "14:45", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "15:00", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "15:25", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "16:10", board: "ALUVA - ERAVATHUR - MALA", via: "Eravathur", type: "Ordinary" },
  { time: "17:05", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "17:15", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "17:35", board: "ALUVA - ERAVATHUR - MALA", via: "Eravathur", type: "Ordinary" },
  { time: "18:05", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "18:45", board: "ALUVA - MALA", via: "Annamanada · Meladoor", type: "Ordinary" },
  { time: "19:10", board: "ALUVA - ERAVATHUR - MALA", via: "Eravathur", type: "Ordinary" },
  { time: "19:30", board: "ALUVA - MALA", via: "Annamanada", type: "Super Fast" },
  { time: "20:45", board: "ALUVA - MALA", via: "Annamanada", type: "Super Fast" },
  { time: "21:00", board: "ALUVA - MALA", via: "Annamanada", type: "Fast Passenger" },
  { time: "21:50", board: "ALUVA - MALA", via: "Annamanada", type: "Super Fast" },
];

// -----------------------------------------------------------------------------
// 3. MALA ↔ KODUNGALLUR (Via Poyya / Karupadanna)
// -----------------------------------------------------------------------------
export const MALA_TO_KDLR: KSRTCBus[] = [
  { time: "05:20", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "05:30", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "06:00", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "06:05", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "06:20", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "06:40", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "07:05", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "07:50", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "08:30", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "09:05", board: "MALA - KARUPADANNA - KODUNGALLUR", via: "Karupadanna", type: "Ordinary" },
  { time: "09:10", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "09:40", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "10:10", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "10:25", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "11:10", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "11:50", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "12:15", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "13:00", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "13:30", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "13:50", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "14:20", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "15:00", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "15:15", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "15:40", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "16:10", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "16:25", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "17:10", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "17:25", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "18:20", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "18:25", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
  { time: "18:30", board: "MALA - POYYA - KODUNGALLUR", via: "Poyya", type: "Ordinary" },
];

export const KDLR_TO_MALA: KSRTCBus[] = [
  { time: "06:00", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "06:45", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "07:00", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "07:20", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "07:45", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "08:30", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "09:00", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "09:15", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "09:50", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "10:00", board: "KODUNGALLUR - KARUPADANNA - MALA", via: "Karupadanna", type: "Ordinary" },
  { time: "10:25", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "10:50", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "11:05", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "11:45", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "12:30", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "13:10", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "13:40", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "14:10", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "14:35", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "15:00", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "15:35", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "15:50", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "16:20", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "16:50", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "17:15", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "18:05", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "18:20", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "18:30", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "19:00", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
  { time: "19:10", board: "KODUNGALLUR - POYYA - MALA", via: "Poyya", type: "Ordinary" },
];

export const BUS_SCHEDULE = MALA_TO_TSR;


export const AUTO_DRIVERS: AutoDriver[] = [
  { name: "Anil T. V.", sub: "Auto · Mala Junction", desc: "Quick trips between Mala Bus Stand, festival venues, and St. Antony's HSS.", phone: "+919999000103" },
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
