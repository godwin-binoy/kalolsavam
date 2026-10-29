#!/usr/bin/env python3
"""
Kalolsavam static build — the single source of truth for shared chrome.

Every page (index + 5 service pages) repeats the same <head>, header, mobile
drawer and footer. That duplication was the root cause of theme-toggle bugs:
hand-copied blocks drifted apart page by page. This script assembles all six
pages from ONE template + ONE content map, so shared markup can never diverge.

Usage:  python3 tools/build.py
Output: index.html and pages/*.html at the repo root.

Design decisions baked into the template (do not "simplify" these away):
  * The theme bootstrap is INLINED in <head> and reads js/theme-boot.js —
    it must run before first paint or dark mode flashes light on load.
  * Theme state lives ONLY on <html class="dark">; nothing else mirrors it.
  * Toggle buttons ship EMPTY: JS injects fixed-size SVG icons, so swapping
    states never shifts the header layout (no emoji/text icons).
  * Relative URLs are computed per depth (root vs pages/) automatically.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Global site configuration — add/rename a module here and every page updates.
# ---------------------------------------------------------------------------
SITE = {
    "title": "Mala Sub-District Kalolsavam | St. Antony's HSS Mala",
    "school": "St. Antony's HSS Mala",
    "tagline": "Sub-District School Kalolsavam",
    "footer_note": "Official Festival On-Premise Information Desk",
    "footer_ops": "Operated by Host School IT &amp; Media Committee",
}

# key -> (nav label, drawer label, <title> prefix)
MODULES = {
    "venues":       ("Stages",           "01. Stage &amp; Venues Live Tracker", "Stage &amp; Venues"),
    "competitions": ("Competitions",     "02. Competitions &amp; Results",      "Competitions &amp; Results"),
    "photos":       ("Photos",           "03. Stage Photos &amp; Media",        "Stage Photos"),
    "facilities":   ("Facilities",       "04. Facilities &amp; Campus Map",     "Facilities &amp; Campus Map"),
    "help":         ("Help / Emergency", "05. Help Desk &amp; Emergency",       "Help Desk &amp; Emergency"),
}
HELP_KEY = "help"                    # rendered with the red emergency styling
HOME_LABEL = ("Home", "Home Portal")

PAGES = {
    "home": {
        "title": SITE["title"],
        "service": None,
        "main": """
  <!-- HERO SECTION -->
  <section>
    <div class="hero-container">
      <div class="max-w-3xl space-y-4">

        <h2 class="page-title leading-snug">
          Mala Sub-District <br class="hidden sm:inline">School Kalolsavam
        </h2>
        <p class="text-sm sm:text-base text-muted leading-relaxed max-w-2xl">
          Welcome to the official web desk for participants, parents, and teachers. Track ongoing stage events, view official point tallies, locate amenities, and download performance photographs.
        </p>

        <div class="pt-2 flex flex-wrap gap-3">
          <a href="#portal-menu" class="btn-primary">Access Services</a>
        </div>
      </div>
    </div>
  </section>

  <!-- PORTAL NAVIGATION (The Clean Card Grid) -->
  <main id="portal-menu" class="main-container">

    <div class="divider-bottom pb-3 mb-6">
      <div>
        <h3 class="section-title">Services</h3>
        <p class="text-xs text-muted mt-0.5">Select a module to view updates and services</p>
      </div>
    </div>

    <!-- One card per module, generated from MODULES/CARD_COPY config -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
{cards}
    </div>

    <!-- HOST INSTITUTION SUMMARY BAR -->
    <div class="mt-8 p-4 rounded inner-box flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
      <div class="text-center sm:text-left">
        <span class="font-semibold text-main">Venue Location:</span>
        <span class="text-muted ml-1">St. Antony's Higher Secondary School, Mala, Thrissur, Kerala 680732</span>
      </div>
      <a href="https://maps.google.com/?q=St+Antonys+Higher+Secondary+School+Mala" target="_blank" rel="noopener" class="text-gov-blue font-semibold card-base px-3 py-1.5 rounded shadow-sm shrink-0">Google Maps</a>
    </div>

  </main>
""",
    },
    "venues": {
        "title": f"{MODULES['venues'][2]} | Mala Sub-District Kalolsavam",
        "service": 1,
        "main": """
  <main class="main-container">
    <div class="mb-8">
      <div class="chip-service chip mb-2">Module 01 &bull; Stages &amp; Venues</div>
      <h2 class="page-title">Stage &amp; Venues Live Tracker</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Real-time stage queue, active chest numbers on stage, delays, and stage locations.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="card-base">
        <div class="flex justify-between items-start mb-3">
          <div>
            <span class="badge-live"><span class="live-dot"></span>ON STAGE NOW</span>
            <h3 class="card-title mt-1.5">Stage 1: Main Auditorium</h3>
            <p class="text-xs text-muted">HS Bharathanatyam (Girls)</p>
          </div>
          <span class="chip-service chip-sm">Code: S101</span>
        </div>
        <div class="inner-box text-xs space-y-1.5">
          <div class="flex justify-between items-center"><span class="text-muted">Current Chest No:</span><span class="font-bold text-main">142 - Ananya P.</span></div>
          <div class="flex justify-between items-center"><span class="text-muted">Up Next:</span><span class="font-medium text-main">143, 145, 148</span></div>
        </div>
      </div>

      <div class="card-base">
        <div class="flex justify-between items-start mb-3">
          <div>
            <span class="badge-live"><span class="live-dot"></span>ON STAGE NOW</span>
            <h3 class="card-title mt-1.5">Stage 2: Open Air Theatre</h3>
            <p class="text-xs text-muted">UP Oppana (Common)</p>
          </div>
          <span class="chip-service chip-sm">Code: S102</span>
        </div>
        <div class="inner-box text-xs space-y-1.5">
          <div class="flex justify-between items-center"><span class="text-muted">Current Team:</span><span class="font-bold text-main">Team #08 - St. Antony's UPS</span></div>
          <div class="flex justify-between items-center"><span class="text-muted">Up Next:</span><span class="font-medium text-main">Team #09, Team #10</span></div>
        </div>
      </div>
    </div>
  </main>
""",
    },
    "competitions": {
        "title": f"{MODULES['competitions'][2]} | Mala Sub-District Kalolsavam",
        "service": 2,
        "main": """
  <main class="main-container">
    <div class="mb-8">
      <div class="chip-service chip mb-2">Module 02 &bull; Competitions &amp; Results</div>
      <h2 class="page-title">Competitions &amp; Results Tabulation</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Category-wise schedules, verified result announcements, and school points table.</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2 space-y-6">
        <div class="card-base">
          <h3 class="card-title mb-4 flex items-center justify-between">
            <span>Latest Declared Results</span>
            <span class="text-xs font-normal text-muted">Updated 10 mins ago</span>
          </h3>

          <div class="space-y-4">
            <div class="inner-box p-4 rounded">
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center text-xs mb-2 gap-2">
                <span class="chip-service chip-sm">Item #12 - HS Bharathanatyam (Girls)</span>
                <span class="badge-live">Verified &amp; Published</span>
              </div>
              <div class="space-y-1.5 text-xs pt-1">
                <div class="flex flex-col sm:flex-row justify-between py-1 divider-bottom gap-1">
                  <span class="font-medium text-main">1st Place: Ananya P. (Chest No. 142)</span>
                  <span class="text-muted">St. Antony's HSS Mala (A Grade)</span>
                </div>
                <div class="flex flex-col sm:flex-row justify-between py-1 gap-1">
                  <span class="font-medium text-main">2nd Place: Sneha K. (Chest No. 108)</span>
                  <span class="text-muted">GVHSS Annamanada (A Grade)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div>
        <div class="card-base">
          <h3 class="card-title mb-3">Points Tally (Top Schools)</h3>
          <div class="space-y-2 text-xs">
            <div class="chip-service chip-row font-semibold">
              <span>1. St. Antony's HSS Mala</span>
              <span>145 pts</span>
            </div>
            <div class="chip-row inner-box">
              <span class="font-medium text-main">2. GVHSS Annamanada</span>
              <span class="text-muted font-medium">112 pts</span>
            </div>
            <div class="chip-row inner-box">
              <span class="font-medium text-main">3. Carmel HSS Mala</span>
              <span class="text-muted font-medium">98 pts</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>
""",
    },
    "photos": {
        "title": f"{MODULES['photos'][2]} | Mala Sub-District Kalolsavam",
        "service": 3,
        "main": """
  <main class="main-container">
    <div class="mb-8">
      <div class="badge-gov mb-2">Module 03</div>
      <h2 class="page-title">Official Media &amp; Stage Photographs</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Search and download performance photographs uploaded directly by the official media room.</p>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      <div class="card-base overflow-hidden p-0">
        <img src="{r}res/school.jpeg" alt="Bharathanatyam HS performance on Stage 1" class="photo-cover" loading="lazy" decoding="async" />
        <div class="p-4">
          <span class="badge-gov">Stage 1</span>
          <h3 class="font-semibold text-heading text-sm mt-2">Bharathanatyam HS</h3>
          <p class="text-xs text-muted mt-0.5">Uploaded 1 hour ago</p>
          <div class="mt-4 pt-3 divider-top flex justify-between items-center text-xs">
            <span class="text-muted font-medium">High Resolution</span>
            <a href="{r}res/school.jpeg" download class="text-gov-blue font-semibold">Download</a>
          </div>
        </div>
      </div>

      <div class="card-base overflow-hidden p-0">
        <img src="{r}res/school.jpeg" alt="Oppana UP performance on Stage 2" class="photo-cover" loading="lazy" decoding="async" />
        <div class="p-4">
          <span class="badge-gov">Stage 2</span>
          <h3 class="font-semibold text-heading text-sm mt-2">Oppana UP</h3>
          <p class="text-xs text-muted mt-0.5">Uploaded 2 hours ago</p>
          <div class="mt-4 pt-3 divider-top flex justify-between items-center text-xs">
            <span class="text-muted font-medium">High Resolution</span>
            <a href="{r}res/school.jpeg" download class="text-gov-blue font-semibold">Download</a>
          </div>
        </div>
      </div>
    </div>
  </main>
""",
    },
    "facilities": {
        "title": f"{MODULES['facilities'][2]} | Mala Sub-District Kalolsavam",
        "service": 4,
        "main": """
  <main class="main-container">
    <div class="mb-8">
      <div class="badge-gov mb-2">Module 04</div>
      <h2 class="page-title">Campus Facilities &amp; Locations</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Locations for dining hall, clean drinking water, green rooms, washrooms, and designated vehicle parking.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="card-base">
        <h3 class="card-title mb-1">Festival Dining Hall (Oottupura)</h3>
        <p class="text-xs text-muted mb-3 font-medium">Main Block Ground Floor</p>
        <p class="text-xs text-main leading-relaxed">
          Free meals and snacks for all participants and accompanying teachers throughout the festival.
        </p>
      </div>

      <div class="card-base">
        <h3 class="card-title mb-1">Drinking Water Stations</h3>
        <p class="text-xs text-muted mb-3 font-medium">Behind Main Stage &amp; Near Green Room</p>
        <p class="text-xs text-main leading-relaxed">
          Purified water points with disposable cups; refill bottles at the station beside the dining hall.
        </p>
      </div>

      <div class="card-base">
        <h3 class="card-title mb-1">Green Rooms &amp; Practice Spaces</h3>
        <p class="text-xs text-muted mb-3 font-medium">Annex Block, Rooms G-1 to G-6</p>
        <p class="text-xs text-main leading-relaxed">
          Grouped by item number; volunteers guide each delegation to its allotted room before performance.
        </p>
      </div>

      <div class="card-base">
        <h3 class="card-title mb-1">Washrooms &amp; Parking</h3>
        <p class="text-xs text-muted mb-3 font-medium">East Wing &amp; Front Lawn</p>
        <p class="text-xs text-main leading-relaxed">
          Sanitized facilities cleaned hourly; two-wheeler and car parking along the perimeter road.
        </p>
      </div>
    </div>
  </main>
""",
    },
    "help": {
        "title": f"{MODULES['help'][2]} | Mala Sub-District Kalolsavam",
        "service": 5,
        "main": """
  <main class="main-container">
    <div class="mb-8">
      <div class="badge-emergency mb-2">Emergency &amp; Coordination</div>
      <h2 class="page-title">Help Desk &amp; Emergency Directory</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Convenor contact numbers, First Aid / Medical unit location, and Volunteer control room.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="card-base">
        <h3 class="card-title mb-1">Medical &amp; First Aid Unit</h3>
        <p class="text-xs text-muted mb-3 font-medium">Main Office Room 102</p>
        <p class="text-xs text-main leading-relaxed mb-4">
          Doctor, nursing staff, and ambulance service on standby throughout festival hours.
        </p>
        <a href="tel:04802890100" class="btn-call-emergency btn-call">Call Medical Desk: 0480 2890100</a>
      </div>

      <div class="card-base">
        <h3 class="card-title mb-1">General Convener Desk</h3>
        <p class="text-xs text-muted mb-3 font-medium">Control Room (Auditorium Lobby)</p>
        <p class="text-xs text-main leading-relaxed mb-4">
          For urgent queries regarding stage timings, chest number rescheduling, and committee approvals.
        </p>
        <a href="tel:04802890000" class="btn-call-desk btn-call">Call Control Room: 0480 2890000</a>
      </div>
    </div>
  </main>
""",
    },
}

# Home-card copy per module (single place to edit blurbs)
CARD_COPY = {
    "venues": ("Stage &amp; Venues",
               "Real-time stage queue, active chest numbers on stage, delays, and stage locations across campus.",
               "Open Stage Tracker"),
    "competitions": ("Competitions &amp; Results",
                     "Category-wise schedules (LP, UP, HS, HSS), verified result announcements, and school points table.",
                     "View Scoreboard"),
    "photos": ("Stage Photos",
               "Search and download performance photographs uploaded directly by the official media room.",
               "Download Photos"),
    "facilities": ("Facilities &amp; Map",
                   "Locations for dining hall, clean drinking water, green rooms, washrooms, and designated vehicle parking.",
                   "View Campus Map"),
    "help": ("Help Desk &amp; Coordination",
             "Convenor contact numbers, First Aid / Medical unit location, Volunteer control room, and Lost &amp; Found counter.",
             "View Contact Directory"),
}

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <!-- GENERATED FILE: edit tools/build.py, then run `python3 tools/build.py`. Do not hand-edit. -->
  <!-- Theme bootstrap runs BEFORE first paint (prevents dark-mode white flash).
       Canonical logic lives in js/theme-boot.js and is inlined here at build time. -->
  <script>{boot}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="{r}css/style.css">{home_css}
</head>
<body class="font-sans antialiased flex flex-col min-h-screen"{body_attrs}>

  <header class="site-header">
    <div class="header-container flex items-center justify-between">
      <a href="{r}index.html" class="flex items-center gap-3 group">
        <img src="{r}res/logo.webp" alt="St. Antony's Logo" class="logo-box object-contain shrink-0" width="38" height="38" decoding="async" />
        <span class="pl-3">
          <span class="block text-sm sm:text-lg font-bold leading-tight text-heading heading-transition">{school}</span>
          <span class="block text-[11px] sm:text-xs text-muted font-medium">{tagline}</span>
        </span>
      </a>

      <!-- Desktop Nav -->
      <nav class="hidden md:flex items-center gap-1 text-xs font-semibold">
{desktop_nav}        <button id="dark-mode-toggle" type="button" aria-label="Toggle Dark Mode" class="nav-link theme-toggle ml-1"></button>
      </nav>

      <!-- Mobile controls -->
      <div class="flex items-center gap-2 md:hidden">
        <button id="dark-mode-toggle-mobile" type="button" aria-label="Toggle Dark Mode" class="nav-link theme-toggle"></button>
        <a href="{r}pages/venues.html" class="btn-mobile-live">Live</a>
        <button id="mobile-menu-btn" type="button" aria-label="Toggle Menu" aria-expanded="false" class="p-2 text-muted rounded-md">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
          </svg>
        </button>
      </div>
    </div>

    <!-- Mobile Drawer -->
    <div id="mobile-menu" class="md:hidden mobile-menu-drawer space-y-1">
{drawer_links}
    </div>
  </header>
{main}
  <footer class="site-footer">
    <div class="footer-container">
      <div>
        <p class="footer-text font-medium">{school_tag}</p>
        <p class="text-[11px] text-subtle mt-0.5">{footer_note}</p>
      </div>
      <div class="text-[11px] text-subtle">{footer_ops}</div>
    </div>
  </footer>

  <script defer src="{r}js/main.js"></script>

</body>
</html>
"""


def nav_html(active_key, r):
    """Desktop nav + drawer links generated from one config — always in sync."""
    def link(key, href, cls_map, label):
        active = " active" if key == active_key else ""
        return f'        <a href="{href}" class="{cls_map}{active}">{label}</a>'

    desktop = [link("home", f"{r}index.html", "nav-link", HOME_LABEL[0])]
    for key, (label, _, _) in MODULES.items():
        cls = "nav-link-help" if key == HELP_KEY else "nav-link"
        desktop.append(link(key, f"{r}pages/{key}.html", cls, label))

    drawer = [link("home", f"{r}index.html", "mobile-menu-link", HOME_LABEL[1])]
    for key, (_, drawer_label, _) in MODULES.items():
        cls = "mobile-menu-link-help" if key == HELP_KEY else "mobile-menu-link"
        drawer.append(link(key, f"{r}pages/{key}.html", cls, drawer_label))

    return "\n".join(desktop) + "\n", "\n".join(drawer)


def home_cards(r):
    cards = []
    for i, (key, (title, desc, cta)) in enumerate(CARD_COPY.items(), start=1):
        span = " sm:col-span-2 lg:col-span-2" if key == HELP_KEY else ""
        cards.append(f"""      <a href="{r}pages/{key}.html" class="group card-base card-service flex flex-col justify-between{span}" data-service="{i}">
        <div>
          <div class="w-9 h-9 rounded service-icon flex items-center justify-center font-bold text-sm mb-3">{i:02d}</div>
          <h4 class="font-semibold text-heading text-base heading-transition">{title}</h4>
          <p class="text-xs text-muted mt-1.5 leading-relaxed">{desc}</p>
        </div>
        <div class="pt-4 mt-4 divider-top flex items-center justify-between text-xs font-semibold service-arrow">
          <span>{cta}</span>
          <span class="arrow-icon" aria-hidden="true"></span>
        </div>
      </a>""")
    return "\n".join(cards)


def strip_js_comments(src):
    """Drop /* */ block comments so the inlined bootstrap stays tiny."""
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def main():
    boot = strip_js_comments((ROOT / "js" / "theme-boot.js").read_text(encoding="utf-8"))
    # Collapse to a single line so the generated head stays compact.
    boot_inline = " ".join(line.strip() for line in boot.splitlines() if line.strip())

    for key, page in PAGES.items():
        r = "./" if key == "home" else "../"
        desktop_nav, drawer_links = nav_html(key, r)
        body_attrs = ""
        if page["service"]:
            body_attrs = f' data-service="{page["service"]}"'
        html_out = TEMPLATE.format(
            title=page["title"],
            boot=boot_inline,
            r=r,
            home_css='\n  <link rel="stylesheet" href="./css/pages/home.css">' if key == "home" else "",
            body_attrs=body_attrs,
            school=SITE["school"],
            tagline=SITE["tagline"],
            desktop_nav=desktop_nav,
            drawer_links=drawer_links,
            main=page["main"].format(r=r, cards=home_cards(r)),
            school_tag=f"Sub-District School Kalolsavam &bull; {SITE['school']}",
            footer_note=SITE["footer_note"],
            footer_ops=SITE["footer_ops"],
        )
        out = ROOT / ("index.html" if key == "home" else f"pages/{key}.html")
        out.write_text(html_out, encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
