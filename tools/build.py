#!/usr/bin/env python3
"""
Kalolsavam static build compiler.
Reads all SVG files dynamically from res/svg/ and generates index.html and all pages.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SVG_DIR = ROOT / "res" / "svg"

def get_svg(filename, extra_class=""):
    content = (SVG_DIR / filename).read_text(encoding="utf-8").strip()
    if extra_class:
        content = re.sub(r'<svg\s+', f'<svg class="{extra_class}" ', content, count=1)
    return content

SITE = {
    "title": "Mala Sub-District Kalolsavam | St. Antony's HSS Mala",
    "school": "St. Antony's HSS Mala",
    "tagline": "Sub-District School Kalolsavam",
    "footer_note": "Official Festival On-Premise Information Desk",
    "footer_ops": "Operated by Host School IT & Media Committee",
}

MODULES = {
    "venues":       ("Stages",           "01. Stage &amp; Venues Live Tracker", "Stage &amp; Venues"),
    "competitions": ("Competitions",     "02. Competitions &amp; Results",      "Competitions &amp; Results"),
    "photos":       ("Photos",           "03. Stage Photos &amp; Media",        "Stage Photos"),
    "facilities":   ("Facilities",       "04. Facilities &amp; Campus Map",     "Facilities &amp; Campus Map"),
    "help":         ("Help / Emergency", "05. Help Desk &amp; Emergency",       "Help Desk &amp; Emergency"),
}
HELP_KEY = "help"
HOME_LABEL = ("Home", "Home Portal")

# Load SVGs directly from res/svg/
WM_MASKS = get_svg("wm-masks.svg", "fest-watermark")
WM_PALETTE = get_svg("wm-palette.svg", "fest-watermark")
WM_LEAF = get_svg("wm-leaf.svg", "fest-watermark")
WM_QUILL = get_svg("wm-quill.svg", "fest-watermark")

ICON_RESULTS = get_svg("icon-results.svg")
ICON_POINTS = get_svg("icon-points.svg")
ICON_SCHOOL = get_svg("icon-school.svg")
ICON_STAGE = get_svg("icon-stage.svg")
ICON_PHONE = get_svg("icon-phone.svg")
ARROW_RIGHT = get_svg("icon-arrow.svg")

# Official government results portal. The site never hosts results itself;
# main.js upgrades these links with the live URL from /api/public/meta.
GOV_RESULTS_URL = "https://kalolsavam.kerala.gov.in/"
RESULTS_HREF = GOV_RESULTS_URL

PAGES = {
    "home": {
        "title": SITE["title"],
        "service": None,
        "main": f"""
  <section>
    <div class="hero-container">
      <div class="max-w-3xl space-y-4">
        <span class="badge-gov">Official Live Portal</span>
        <h2 class="page-title leading-tight">
          Mala Sub-District <br class="hidden sm:inline">School Kalolsavam
        </h2>
        <p class="text-sm sm:text-base text-muted leading-relaxed max-w-2xl">
          Welcome to the official web desk for participants, parents, and teachers. Track real-time stage events, access verified result declarations, view school points tallies, and download high-resolution stage photographs.
        </p>
        <div class="pt-2 flex flex-wrap gap-3">
          <a href="#portal-menu" class="btn-primary">Explore Services</a>
          <a href="{{r}}pages/venues.html" class="btn-secondary">Live Stages</a>
        </div>
      </div>
    </div>
  </section>

  <main id="portal-menu" class="main-container">
    <div class="divider-bottom pb-4 mb-8">
      <div>
        <h3 class="section-title">Festival Services &amp; Portals</h3>
        <p class="text-xs text-muted mt-1">Select any module below for real-time announcements and services</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

      <div class="fest-card">
        <div class="fest-header banner-blue">
          <h4 class="fest-title">STAGES &amp; VENUES</h4>
          <span class="fest-subtitle">MODULE 01 &bull; LIVE TRACKER</span>
          {WM_MASKS}
        </div>
        <div class="fest-body">
          <a href="{{r}}pages/venues.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_STAGE}</span>
              <span>On-Stage Tracker</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="{{r}}pages/venues.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_RESULTS}</span>
              <span>Next Chest Numbers</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="{{r}}pages/facilities.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_POINTS}</span>
              <span>Venue Locations</span>
            </div>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-purple">
          <h4 class="fest-title">COMPETITIONS</h4>
          <span class="fest-subtitle">MODULE 02 &bull; RESULTS &amp; POINTS</span>
          {WM_PALETTE}
        </div>
        <div class="fest-body">
          <a href="{RESULTS_HREF}" data-results-link target="_blank" rel="noopener noreferrer" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_RESULTS}</span>
              <span>Results Declared</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="{{r}}pages/competitions.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_POINTS}</span>
              <span>District Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="{{r}}pages/competitions.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_SCHOOL}</span>
              <span>School Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-pink">
          <h4 class="fest-title">STAGE PHOTOS</h4>
          <span class="fest-subtitle">MODULE 03 &bull; OFFICIAL MEDIA</span>
          {WM_LEAF}
        </div>
        <div class="fest-body">
          <a href="{{r}}pages/photos.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_STAGE}</span>
              <span>Stage 1 Performance</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="{{r}}pages/photos.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_RESULTS}</span>
              <span>Stage 2 Performance</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="{{r}}pages/photos.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_POINTS}</span>
              <span>High-Res Downloads</span>
            </div>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-teal">
          <h4 class="fest-title">CAMPUS MAP</h4>
          <span class="fest-subtitle">MODULE 04 &bull; AMENITIES</span>
          {WM_QUILL}
        </div>
        <div class="fest-body">
          <a href="{{r}}pages/facilities.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_SCHOOL}</span>
              <span>Dining Hall (Oottupura)</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="{{r}}pages/facilities.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_POINTS}</span>
              <span>Green Rooms &amp; Water</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="{{r}}pages/facilities.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_RESULTS}</span>
              <span>Vehicle Parking Zones</span>
            </div>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

      <div class="fest-card md:col-span-2 lg:col-span-2">
        <div class="fest-header banner-orange">
          <h4 class="fest-title">HELP DESK &amp; MEDICAL</h4>
          <span class="fest-subtitle">MODULE 05 &bull; EMERGENCY DIRECTORY</span>
          {WM_MASKS}
        </div>
        <div class="fest-body grid grid-cols-1 sm:grid-cols-2 gap-3">
          <a href="{{r}}pages/help.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_PHONE}</span>
              <span>First Aid / Medical Unit</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="{{r}}pages/help.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_SCHOOL}</span>
              <span>General Convener Desk</span>
            </div>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

    </div>

    <div class="mt-10 p-5 rounded-2xl card-base flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
      <div class="text-center sm:text-left">
        <span class="font-bold text-main">Festival Host Location:</span>
        <span class="text-muted ml-1">St. Antony's Higher Secondary School, Mala, Thrissur, Kerala 680732</span>
      </div>
      <a href="https://maps.google.com/?q=St+Antonys+Higher+Secondary+School+Mala" target="_blank" rel="noopener" class="btn-primary py-2 px-4 text-xs shrink-0">Open in Google Maps</a>
    </div>
  </main>
""",
    },
    "competitions": {
        "title": f"{MODULES['competitions'][2]} | Mala Sub-District Kalolsavam",
        "service": 2,
        "main": f"""
  <main class="main-container">
    <div class="mb-8">
      <div class="badge-gov mb-2">Category Portals</div>
      <h2 class="page-title">Competitions &amp; Tabulation</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Select a category below for declared results, chest numbers, and official school point tallies.</p>
    </div>

    <!-- 4 CARDS AS IN THE REFERENCE IMAGE -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">

      <!-- Card 1: HS GENERAL -->
      <div class="fest-card">
        <div class="fest-header banner-purple">
          <h3 class="fest-title">HS GENERAL</h3>
          <span class="fest-subtitle">FESTIVAL CATEGORY</span>
          {WM_MASKS}
        </div>
        <div class="fest-body">
          <a href="{RESULTS_HREF}" data-results-link target="_blank" rel="noopener noreferrer" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_RESULTS}</span>
              <span>Results Declared</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_POINTS}</span>
              <span>District Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_SCHOOL}</span>
              <span>School Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

      <!-- Card 2: HSS GENERAL -->
      <div class="fest-card">
        <div class="fest-header banner-pink">
          <h3 class="fest-title">HSS GENERAL</h3>
          <span class="fest-subtitle">FESTIVAL CATEGORY</span>
          {WM_PALETTE}
        </div>
        <div class="fest-body">
          <a href="{RESULTS_HREF}" data-results-link target="_blank" rel="noopener noreferrer" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_RESULTS}</span>
              <span>Results Declared</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_POINTS}</span>
              <span>District Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_SCHOOL}</span>
              <span>School Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

      <!-- Card 3: HS ARABIC -->
      <div class="fest-card">
        <div class="fest-header banner-teal">
          <h3 class="fest-title">HS ARABIC</h3>
          <span class="fest-subtitle">FESTIVAL CATEGORY</span>
          {WM_LEAF}
        </div>
        <div class="fest-body">
          <a href="{RESULTS_HREF}" data-results-link target="_blank" rel="noopener noreferrer" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_RESULTS}</span>
              <span>Results Declared</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_POINTS}</span>
              <span>District Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_SCHOOL}</span>
              <span>School Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

      <!-- Card 4: HS SANSKRIT -->
      <div class="fest-card">
        <div class="fest-header banner-orange">
          <h3 class="fest-title">HS SANSKRIT</h3>
          <span class="fest-subtitle">FESTIVAL CATEGORY</span>
          {WM_QUILL}
        </div>
        <div class="fest-body">
          <a href="{RESULTS_HREF}" data-results-link target="_blank" rel="noopener noreferrer" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_RESULTS}</span>
              <span>Results Declared</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_POINTS}</span>
              <span>District Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">{ICON_SCHOOL}</span>
              <span>School Points</span>
            </div>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8" id="results-feed">
      <div class="lg:col-span-2 space-y-6">
        <div class="card-base">
          <h3 class="card-title mb-4 flex items-center justify-between">
            <span>Latest Declared Results</span>
            <a href="{RESULTS_HREF}" data-results-link target="_blank" rel="noopener noreferrer" class="text-xs font-semibold text-gov-blue hover:underline">Official portal &nearr;</a>
          </h3>

          <div class="space-y-4">
            <div class="inner-box">
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center text-xs mb-2 gap-2">
                <span class="badge-gov">Item #12 &bull; HS Bharathanatyam (Girls)</span>
                <span class="badge-live">Verified &amp; Published</span>
              </div>
              <div class="space-y-1.5 text-xs pt-1">
                <div class="flex flex-col sm:flex-row justify-between py-1 divider-bottom gap-1">
                  <span class="font-bold text-main">1st Place: Ananya P. (Chest No. 142)</span>
                  <span class="text-muted">St. Antony's HSS Mala (A Grade)</span>
                </div>
                <div class="flex flex-col sm:flex-row justify-between py-1 gap-1">
                  <span class="font-bold text-main">2nd Place: Sneha K. (Chest No. 108)</span>
                  <span class="text-muted">GVHSS Annamanada (A Grade)</span>
                </div>
              </div>
            </div>

            <div class="inner-box">
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center text-xs mb-2 gap-2">
                <span class="badge-gov">Item #24 &bull; HSS Oppana (Common)</span>
                <span class="badge-live">Verified &amp; Published</span>
              </div>
              <div class="space-y-1.5 text-xs pt-1">
                <div class="flex flex-col sm:flex-row justify-between py-1 divider-bottom gap-1">
                  <span class="font-bold text-main">1st Place: Team #08 (St. Antony's HSS)</span>
                  <span class="text-muted">St. Antony's HSS Mala (A Grade)</span>
                </div>
                <div class="flex flex-col sm:flex-row justify-between py-1 gap-1">
                  <span class="font-bold text-main">2nd Place: Team #04 (Carmel HSS)</span>
                  <span class="text-muted">Carmel HSS Mala (A Grade)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div id="points-table">
        <div class="card-base">
          <h3 class="card-title mb-3">Overall School Points</h3>
          <div class="space-y-2 text-xs">
            <div class="p-3 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 flex justify-between items-center font-bold text-purple-900 dark:text-purple-200">
              <span>1. St. Antony's HSS Mala</span>
              <span>145 pts</span>
            </div>
            <div class="p-3 rounded-xl inner-box flex justify-between items-center">
              <span class="font-medium text-main">2. GVHSS Annamanada</span>
              <span class="text-muted font-bold">112 pts</span>
            </div>
            <div class="p-3 rounded-xl inner-box flex justify-between items-center">
              <span class="font-medium text-main">3. Carmel HSS Mala</span>
              <span class="text-muted font-bold">98 pts</span>
            </div>
            <div class="p-3 rounded-xl inner-box flex justify-between items-center">
              <span class="font-medium text-main">4. GHS Mala</span>
              <span class="text-muted font-bold">84 pts</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>
""",
    },
    "venues": {
        "title": f"{MODULES['venues'][2]} | Mala Sub-District Kalolsavam",
        "service": 1,
        "main": f"""
  <main class="main-container">
    <div class="mb-8">
      <div class="badge-gov mb-2">Module 01 &bull; Live Tracker</div>
      <h2 class="page-title">Stage &amp; Venues Live Tracker</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Real-time stage queue, active chest numbers on stage, delays, and stage locations across campus.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">

      <div class="fest-card">
        <div class="fest-header banner-blue">
          <div class="flex justify-between items-center">
            <h3 class="fest-title">STAGE 1 &bull; MAIN HALL</h3>
            <span class="badge-live"><span class="live-dot"></span>LIVE</span>
          </div>
          <span class="fest-subtitle">HS BHARATHANATYAM (GIRLS)</span>
          {WM_MASKS}
        </div>
        <div class="fest-body">
          <div class="fest-action-item">
            <div>
              <span class="text-xs text-muted block">On Stage Chest No:</span>
              <span class="font-bold text-base text-main">142 - Ananya P.</span>
            </div>
            <span class="badge-gov">Item #12</span>
          </div>
          <div class="fest-action-item">
            <div>
              <span class="text-xs text-muted block">Up Next in Queue:</span>
              <span class="font-semibold text-main">143, 145, 148</span>
            </div>
            <span class="text-xs text-muted font-medium">Ready in Green Room</span>
          </div>
          <div class="fest-action-item">
            <div>
              <span class="text-xs text-muted block">Stage In-charge:</span>
              <span class="font-semibold text-main">Sri. Rajesh K. (Auditorium Lobby)</span>
            </div>
            {ARROW_RIGHT}
          </div>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-teal">
          <div class="flex justify-between items-center">
            <h3 class="fest-title">STAGE 2 &bull; OPEN AIR</h3>
            <span class="badge-live"><span class="live-dot"></span>LIVE</span>
          </div>
          <span class="fest-subtitle">UP OPPANA (COMMON)</span>
          {WM_PALETTE}
        </div>
        <div class="fest-body">
          <div class="fest-action-item">
            <div>
              <span class="text-xs text-muted block">On Stage Team:</span>
              <span class="font-bold text-base text-main">Team #08 - St. Antony's UPS</span>
            </div>
            <span class="badge-gov">Item #04</span>
          </div>
          <div class="fest-action-item">
            <div>
              <span class="text-xs text-muted block">Up Next in Queue:</span>
              <span class="font-semibold text-main">Team #09, Team #10</span>
            </div>
            <span class="text-xs text-muted font-medium">Reporting done</span>
          </div>
          <div class="fest-action-item">
            <div>
              <span class="text-xs text-muted block">Stage In-charge:</span>
              <span class="font-semibold text-main">Smt. Deepa V. (Ground Wing)</span>
            </div>
            {ARROW_RIGHT}
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
        "main": f"""
  <main class="main-container">
    <div class="mb-8">
      <div class="badge-gov mb-2">Module 03 &bull; Media Room</div>
      <h2 class="page-title">Official Media &amp; Stage Photographs</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Search and download performance photographs uploaded directly by the official media room.</p>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      <div class="fest-card p-0">
        <img src="{{r}}res/school.jpeg" alt="Bharathanatyam HS performance on Stage 1" class="photo-cover" loading="lazy" decoding="async" />
        <div class="p-4 flex flex-col justify-between flex-grow">
          <div>
            <span class="badge-gov">Stage 1 &bull; Classical Dance</span>
            <h3 class="font-bold text-heading text-base mt-2">Bharathanatyam HS Girls</h3>
            <p class="text-xs text-muted mt-0.5">Uploaded 1 hour ago by Media Desk</p>
          </div>
          <div class="mt-4 pt-3 divider-top flex justify-between items-center text-xs">
            <span class="text-muted font-medium">Resolution: 4K UHD</span>
            <a href="{{r}}res/school.jpeg" download class="btn-primary py-1.5 px-3 text-xs">Download</a>
          </div>
        </div>
      </div>

      <div class="fest-card p-0">
        <img src="{{r}}res/school.jpeg" alt="Oppana UP performance on Stage 2" class="photo-cover" loading="lazy" decoding="async" />
        <div class="p-4 flex flex-col justify-between flex-grow">
          <div>
            <span class="badge-gov">Stage 2 &bull; Folk Item</span>
            <h3 class="font-bold text-heading text-base mt-2">Oppana UP Common</h3>
            <p class="text-xs text-muted mt-0.5">Uploaded 2 hours ago by Media Desk</p>
          </div>
          <div class="mt-4 pt-3 divider-top flex justify-between items-center text-xs">
            <span class="text-muted font-medium">Resolution: 4K UHD</span>
            <a href="{{r}}res/school.jpeg" download class="btn-primary py-1.5 px-3 text-xs">Download</a>
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
        "main": f"""
  <main class="main-container">
    <div class="mb-8">
      <div class="badge-gov mb-2">Module 04 &bull; Amenities</div>
      <h2 class="page-title">Campus Facilities &amp; Locations</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Locations for dining hall, clean drinking water, green rooms, washrooms, and designated vehicle parking.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="fest-card">
        <div class="fest-header banner-orange">
          <h3 class="fest-title">DINING HALL</h3>
          <span class="fest-subtitle">OOTTUPURA &bull; MAIN BLOCK</span>
          {WM_PALETTE}
        </div>
        <div class="fest-body">
          <p class="text-xs text-main leading-relaxed mb-2">
            Free meals and refreshments for all participants and accompanying school teachers throughout the festival days.
          </p>
          <div class="fest-action-item">
            <span>Location: Ground Floor, Main Block</span>
            {ARROW_RIGHT}
          </div>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-teal">
          <h3 class="fest-title">GREEN ROOMS</h3>
          <span class="fest-subtitle">PRACTICE SPACES &bull; ROOMS G1-G6</span>
          {WM_MASKS}
        </div>
        <div class="fest-body">
          <p class="text-xs text-main leading-relaxed mb-2">
            Designated delegatory rooms allotted by competition code. Dressing facilities with full-length mirrors and electrical ports.
          </p>
          <div class="fest-action-item">
            <span>Location: Annex Block 1st Floor</span>
            {ARROW_RIGHT}
          </div>
        </div>
      </div>
    </div>
  </main>
""",
    },
    "help": {
        "title": f"{MODULES['help'][2]} | Mala Sub-District Kalolsavam",
        "service": 5,
        "main": f"""
  <main class="main-container">
    <div class="mb-8">
      <div class="badge-emergency mb-2">Emergency Desk</div>
      <h2 class="page-title">Help Desk &amp; Emergency Directory</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Convenor contact numbers, First Aid / Medical unit location, and Volunteer control room.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="fest-card">
        <div class="fest-header banner-pink">
          <h3 class="fest-title">MEDICAL UNIT</h3>
          <span class="fest-subtitle">FIRST AID &bull; 24/7 STANDBY</span>
          {WM_LEAF}
        </div>
        <div class="fest-body">
          <p class="text-xs text-main leading-relaxed mb-3">
            Physicians, nursing staff, and emergency medical ambulance available on campus during festival hours.
          </p>
          <a href="tel:04802890100" class="fest-action-item bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800">
            <span class="font-bold text-rose-700 dark:text-rose-300">Call Medical Unit: 0480 2890100</span>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-purple">
          <h3 class="fest-title">GENERAL CONVENER</h3>
          <span class="fest-subtitle">CONTROL ROOM &bull; AUDITORIUM</span>
          {WM_QUILL}
        </div>
        <div class="fest-body">
          <p class="text-xs text-main leading-relaxed mb-3">
            For urgent inquiries regarding chest number reporting, schedule rescheduling, and official committee sanctions.
          </p>
          <a href="tel:04802890000" class="fest-action-item bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-800">
            <span class="font-bold text-purple-700 dark:text-purple-300">Call Convener: 0480 2890000</span>
            {ARROW_RIGHT}
          </a>
        </div>
      </div>
    </div>
  </main>
""",
    },
}

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <!-- GENERATED FILE: edit tools/build.py, then run `python3 tools/build.py`. Do not hand-edit. -->
  <meta name="description" content="Official information desk for the Mala Sub-District School Kalolsavam at St. Antony's HSS Mala \u2014 live stage tracker, schedule, facilities and emergency contacts." />
  <meta name="theme-color" content="#F8F6F0" />
  <link rel="icon" type="image/webp" href="{r}res/logo.webp" />
  {api_meta}
  <script>{boot}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@700;800;900&display=swap">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@700;800;900&display=swap" media="print" onload="this.media='all'">
  <link rel="stylesheet" href="{r}css/style.css">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@700;800;900&display=swap"></noscript>
  <!-- Tailwind runtime only when served by our backend (KAL_TW_CDN injected);
       static hosting relies on the CSS fallback utilities instead. -->{tw_cdn}
</head>
<body class="font-sans antialiased flex flex-col min-h-screen"{body_attrs}>

  <header class="site-header">
    <div class="header-container flex items-center justify-between">
      <a href="{r}index.html" class="flex items-center gap-3 group">
        <img src="{r}res/logo.webp" alt="St. Antony's Logo" class="logo-box object-contain shrink-0" width="38" height="38" decoding="async" />
        <span class="pl-2">
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
    <div id="mobile-menu" class="md:hidden mobile-menu-drawer space-y-1" role="navigation" aria-label="Mobile menu">
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

def strip_js_comments(src):
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)

def main():
    boot = strip_js_comments((ROOT / "js" / "theme-boot.js").read_text(encoding="utf-8"))
    boot_inline = " ".join(line.strip() for line in boot.splitlines() if line.strip())

    for key, page in PAGES.items():
        r = "./" if key == "home" else "../"
        desktop_nav, drawer_links = nav_html(key, r)
        body_attrs = f' data-service="{page["service"]}"' if page["service"] else ""
        html_out = TEMPLATE.format(
            title=page["title"],
            boot=boot_inline,
            r=r,
            body_attrs=body_attrs,
            school=SITE["school"],
            tagline=SITE["tagline"],
            desktop_nav=desktop_nav,
            drawer_links=drawer_links,
            main=page["main"].format(r=r, RESULTS_HREF=RESULTS_HREF),
            api_meta=(f'<meta name="api-base" content="{__import__("os").environ["KAL_API_BASE"].rstrip("/")}/">'
                      if __import__("os").environ.get("KAL_API_BASE") else ""),
            tw_cdn=('\n  <script src="https://cdn.tailwindcss.com"></script>'
                    if __import__("os").environ.get("KAL_TW_CDN") else ''),
            school_tag=f"Sub-District School Kalolsavam &bull; {SITE['school']}",
            footer_note=SITE["footer_note"],
            footer_ops=SITE["footer_ops"],
        )
        out = ROOT / ("index.html" if key == "home" else f"pages/{key}.html")
        out.write_text(html_out, encoding="utf-8")
        print(f"compiled: {out.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
