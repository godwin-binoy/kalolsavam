#!/usr/bin/env python3
"""
Kalolsavam static build — generates index.html and all pages with
Material You + frosted blur + colorful category cards.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

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

ICON_CHECKLIST = '''<svg class="w-4 h-4 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>'''
ICON_POINTS = '''<svg class="w-4 h-4 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>'''
ICON_SCHOOL = '''<svg class="w-4 h-4 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>'''
ICON_STAGE = '''<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>'''
ICON_PHONE = '''<svg class="w-4 h-4 text-rose-600 dark:text-rose-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>'''
ARROW_RIGHT = '''<svg class="fest-arrow" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>'''

WM_MASKS = '''<svg class="fest-watermark" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 13c-.83 0-1.5-.67-1.5-1.5S9.17 12 10 12s1.5.67 1.5 1.5S10.83 15 10 15zm0-5c-.83 0-1.5-.67-1.5-1.5S9.17 7 10 7s1.5.67 1.5 1.5S10.83 10 10 10zm4 5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm0-5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>'''
WM_PALETTE = '''<svg class="fest-watermark" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.49 2 2 6.49 2 12c0 4.14 2.53 7.69 6.13 9.17.48.2.87-.23.87-.71v-.96c0-1.66 1.34-3 3-3h1.5c3.58 0 6.5-2.92 6.5-6.5C20 5.37 16.42 2 12 2zm-5 8c-.83 0-1.5-.67-1.5-1.5S6.17 7 7 7s1.5.67 1.5 1.5S7.83 10 7 10zm3-3c-.83 0-1.5-.67-1.5-1.5S9.17 4 10 4s1.5.67 1.5 1.5S10.83 7 10 7zm4 0c-.83 0-1.5-.67-1.5-1.5S13.17 4 14 4s1.5.67 1.5 1.5S14.83 7 14 7zm3 3c-.83 0-1.5-.67-1.5-1.5S16.17 7 17 7s1.5.67 1.5 1.5S17.83 10 17 10z"/></svg>'''
WM_LEAF = '''<svg class="fest-watermark" viewBox="0 0 24 24" fill="currentColor"><path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.75C6.5 7.5 4 10 4 12c0 2 2.5 3.5 5 2 4.5-2.7 7-6 8-6z"/></svg>'''
WM_QUILL = '''<svg class="fest-watermark" viewBox="0 0 24 24" fill="currentColor"><path d="M21.71 3.29a1 1 0 00-1.42 0l-9.04 9.04a3 3 0 00-.78 1.45l-.47 2.37 2.37-.47a3 3 0 001.45-.78l9.04-9.04a1 1 0 000-1.42l-1.15-1.15zM4 20h16v2H4z"/></svg>'''

PAGES = {
    "home": {
        "title": SITE["title"],
        "service": None,
        "main": """
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
          <a href="{r}pages/venues.html" class="nav-link bg-white/70 dark:bg-neutral-800/80 border border-black/5 dark:border-white/10 px-5 py-3">Live Stages</a>
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
          """ + WM_MASKS + """
        </div>
        <div class="fest-body">
          <a href="{r}pages/venues.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_STAGE + """</span>
              <span>On-Stage Tracker</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="{r}pages/venues.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_CHECKLIST + """</span>
              <span>Next Chest Numbers</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="{r}pages/facilities.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_POINTS + """</span>
              <span>Venue Locations</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-purple">
          <h4 class="fest-title">COMPETITIONS</h4>
          <span class="fest-subtitle">MODULE 02 &bull; RESULTS &amp; POINTS</span>
          """ + WM_PALETTE + """
        </div>
        <div class="fest-body">
          <a href="{r}pages/competitions.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_CHECKLIST + """</span>
              <span>Results Declared</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="{r}pages/competitions.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_POINTS + """</span>
              <span>District Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="{r}pages/competitions.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_SCHOOL + """</span>
              <span>School Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-pink">
          <h4 class="fest-title">STAGE PHOTOS</h4>
          <span class="fest-subtitle">MODULE 03 &bull; OFFICIAL MEDIA</span>
          """ + WM_LEAF + """
        </div>
        <div class="fest-body">
          <a href="{r}pages/photos.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_STAGE + """</span>
              <span>Stage 1 Performance</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="{r}pages/photos.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_CHECKLIST + """</span>
              <span>Stage 2 Performance</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="{r}pages/photos.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_POINTS + """</span>
              <span>High-Res Downloads</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-teal">
          <h4 class="fest-title">CAMPUS MAP</h4>
          <span class="fest-subtitle">MODULE 04 &bull; AMENITIES</span>
          """ + WM_QUILL + """
        </div>
        <div class="fest-body">
          <a href="{r}pages/facilities.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_SCHOOL + """</span>
              <span>Dining Hall (Oottupura)</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="{r}pages/facilities.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_POINTS + """</span>
              <span>Green Rooms &amp; Water</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="{r}pages/facilities.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_CHECKLIST + """</span>
              <span>Vehicle Parking Zones</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
        </div>
      </div>

      <div class="fest-card md:col-span-2 lg:col-span-2">
        <div class="fest-header banner-orange">
          <h4 class="fest-title">HELP DESK &amp; MEDICAL</h4>
          <span class="fest-subtitle">MODULE 05 &bull; EMERGENCY DIRECTORY</span>
          """ + WM_MASKS + """
        </div>
        <div class="fest-body grid grid-cols-1 sm:grid-cols-2 gap-3">
          <a href="{r}pages/help.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_PHONE + """</span>
              <span>First Aid / Medical Unit</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="{r}pages/help.html" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_SCHOOL + """</span>
              <span>General Convener Desk</span>
            </div>
            """ + ARROW_RIGHT + """
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
        "main": """
  <main class="main-container">
    <div class="mb-8">
      <div class="badge-gov mb-2">Category Portals</div>
      <h2 class="page-title">Competitions &amp; Tabulation</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Select a category below for declared results, chest numbers, and official school point tallies.</p>
    </div>

    <!-- 4 CATEGORY CARDS FROM THE REFERENCE IMAGE -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">

      <div class="fest-card">
        <div class="fest-header banner-purple">
          <h3 class="fest-title">HS GENERAL</h3>
          <span class="fest-subtitle">FESTIVAL CATEGORY</span>
          """ + WM_MASKS + """
        </div>
        <div class="fest-body">
          <a href="#results-feed" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_CHECKLIST + """</span>
              <span>Results Declared</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_POINTS + """</span>
              <span>District Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_SCHOOL + """</span>
              <span>School Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-pink">
          <h3 class="fest-title">HSS GENERAL</h3>
          <span class="fest-subtitle">FESTIVAL CATEGORY</span>
          """ + WM_PALETTE + """
        </div>
        <div class="fest-body">
          <a href="#results-feed" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_CHECKLIST + """</span>
              <span>Results Declared</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_POINTS + """</span>
              <span>District Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_SCHOOL + """</span>
              <span>School Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-teal">
          <h3 class="fest-title">HS ARABIC</h3>
          <span class="fest-subtitle">FESTIVAL CATEGORY</span>
          """ + WM_LEAF + """
        </div>
        <div class="fest-body">
          <a href="#results-feed" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_CHECKLIST + """</span>
              <span>Results Declared</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_POINTS + """</span>
              <span>District Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_SCHOOL + """</span>
              <span>School Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-orange">
          <h3 class="fest-title">HS SANSKRIT</h3>
          <span class="fest-subtitle">FESTIVAL CATEGORY</span>
          """ + WM_QUILL + """
        </div>
        <div class="fest-body">
          <a href="#results-feed" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_CHECKLIST + """</span>
              <span>Results Declared</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_POINTS + """</span>
              <span>District Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
          <a href="#points-table" class="fest-action-item">
            <div class="flex items-center">
              <span class="fest-item-icon">""" + ICON_SCHOOL + """</span>
              <span>School Points</span>
            </div>
            """ + ARROW_RIGHT + """
          </a>
        </div>
      </div>

    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8" id="results-feed">
      <div class="lg:col-span-2 space-y-6">
        <div class="card-base">
          <h3 class="card-title mb-4 flex items-center justify-between">
            <span>Latest Declared Results</span>
            <span class="text-xs font-normal text-muted">Updated 10 mins ago</span>
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
        "main": """
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
          """ + WM_MASKS + """
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
            """ + ARROW_RIGHT + """
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
          """ + WM_PALETTE + """
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
            """ + ARROW_RIGHT + """
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
      <div class="badge-gov mb-2">Module 03 &bull; Media Room</div>
      <h2 class="page-title">Official Media &amp; Stage Photographs</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Search and download performance photographs uploaded directly by the official media room.</p>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      <div class="fest-card p-0">
        <img src="{r}res/school.jpeg" alt="Bharathanatyam HS performance on Stage 1" class="photo-cover" loading="lazy" decoding="async" />
        <div class="p-4 flex flex-col justify-between flex-grow">
          <div>
            <span class="badge-gov">Stage 1 &bull; Classical Dance</span>
            <h3 class="font-bold text-heading text-base mt-2">Bharathanatyam HS Girls</h3>
            <p class="text-xs text-muted mt-0.5">Uploaded 1 hour ago by Media Desk</p>
          </div>
          <div class="mt-4 pt-3 divider-top flex justify-between items-center text-xs">
            <span class="text-muted font-medium">Resolution: 4K UHD</span>
            <a href="{r}res/school.jpeg" download class="btn-primary py-1.5 px-3 text-xs">Download</a>
          </div>
        </div>
      </div>

      <div class="fest-card p-0">
        <img src="{r}res/school.jpeg" alt="Oppana UP performance on Stage 2" class="photo-cover" loading="lazy" decoding="async" />
        <div class="p-4 flex flex-col justify-between flex-grow">
          <div>
            <span class="badge-gov">Stage 2 &bull; Folk Item</span>
            <h3 class="font-bold text-heading text-base mt-2">Oppana UP Common</h3>
            <p class="text-xs text-muted mt-0.5">Uploaded 2 hours ago by Media Desk</p>
          </div>
          <div class="mt-4 pt-3 divider-top flex justify-between items-center text-xs">
            <span class="text-muted font-medium">Resolution: 4K UHD</span>
            <a href="{r}res/school.jpeg" download class="btn-primary py-1.5 px-3 text-xs">Download</a>
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
      <div class="badge-gov mb-2">Module 04 &bull; Amenities</div>
      <h2 class="page-title">Campus Facilities &amp; Locations</h2>
      <p class="text-xs sm:text-sm text-muted mt-1">Locations for dining hall, clean drinking water, green rooms, washrooms, and designated vehicle parking.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="fest-card">
        <div class="fest-header banner-orange">
          <h3 class="fest-title">DINING HALL</h3>
          <span class="fest-subtitle">OOTTUPURA &bull; MAIN BLOCK</span>
          """ + WM_PALETTE + """
        </div>
        <div class="fest-body">
          <p class="text-xs text-main leading-relaxed mb-2">
            Free meals and refreshments for all participants and accompanying school teachers throughout the festival days.
          </p>
          <div class="fest-action-item">
            <span>Location: Ground Floor, Main Block</span>
            """ + ARROW_RIGHT + """
          </div>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-teal">
          <h3 class="fest-title">GREEN ROOMS</h3>
          <span class="fest-subtitle">PRACTICE SPACES &bull; ROOMS G1-G6</span>
          """ + WM_MASKS + """
        </div>
        <div class="fest-body">
          <p class="text-xs text-main leading-relaxed mb-2">
            Designated delegatory rooms allotted by competition code. Dressing facilities with full-length mirrors and electrical ports.
          </p>
          <div class="fest-action-item">
            <span>Location: Annex Block 1st Floor</span>
            """ + ARROW_RIGHT + """
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
        "main": """
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
          """ + WM_LEAF + """
        </div>
        <div class="fest-body">
          <p class="text-xs text-main leading-relaxed mb-3">
            Physicians, nursing staff, and emergency medical ambulance available on campus during festival hours.
          </p>
          <a href="tel:04802890100" class="fest-action-item bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800">
            <span class="font-bold text-rose-700 dark:text-rose-300">Call Medical Unit: 0480 2890100</span>
            """ + ARROW_RIGHT + """
          </a>
        </div>
      </div>

      <div class="fest-card">
        <div class="fest-header banner-purple">
          <h3 class="fest-title">GENERAL CONVENER</h3>
          <span class="fest-subtitle">CONTROL ROOM &bull; AUDITORIUM</span>
          """ + WM_QUILL + """
        </div>
        <div class="fest-body">
          <p class="text-xs text-main leading-relaxed mb-3">
            For urgent inquiries regarding chest number reporting, schedule rescheduling, and official committee sanctions.
          </p>
          <a href="tel:04802890000" class="fest-action-item bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-800">
            <span class="font-bold text-purple-700 dark:text-purple-300">Call Convener: 0480 2890000</span>
            """ + ARROW_RIGHT + """
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
  <script>{boot}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="{r}css/style.css">
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
        body_attrs = ""
        if page["service"]:
            body_attrs = f' data-service="{page["service"]}"'
        html_out = TEMPLATE.format(
            title=page["title"],
            boot=boot_inline,
            r=r,
            body_attrs=body_attrs,
            school=SITE["school"],
            tagline=SITE["tagline"],
            desktop_nav=desktop_nav,
            drawer_links=drawer_links,
            main=page["main"].format(r=r),
            school_tag=f"Sub-District School Kalolsavam &bull; {SITE['school']}",
            footer_note=SITE["footer_note"],
            footer_ops=SITE["footer_ops"],
        )
        out = ROOT / ("index.html" if key == "home" else f"pages/{key}.html")
        out.write_text(html_out, encoding="utf-8")
        print(f"compiled: {out.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
