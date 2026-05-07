# Invoke-CafeScrape.ps1
# Scrapes Vancouver cafes across 4 neighbourhoods.

# one-time setup (safe to re-run; pip will skip if already installed)
pip install requests
$env:GOOGLE_PLACES_API_KEY = "your-key-here"

# run for Mount Pleasant (Vancouver)
python discover_cafes.py "Mount Pleasant" 49.2647 -123.1009 1500

# then Main Street, Gastown, Kitsilano
python discover_cafes.py "Main Street" 49.2517 -123.1009 1200
python discover_cafes.py "Gastown" 49.2827 -123.1067 600
python discover_cafes.py "Kitsilano" 49.2682 -123.1697 1500