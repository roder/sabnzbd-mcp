# Automation Pipeline

Combine with Prowlarr (mcparr) and RomM (romm-mcp) for a complete media pipeline:

1. Search Prowlarr for a ROM → `prowlarr_search`
2. Send NZB to SABnzbd → `sab_add_url`
3. Wait for download → `sab_queue` / `sab_history`
4. Scan RomM library → `romm_system` (via docker exec)
5. Browse new ROMs → `romm_search_roms`
