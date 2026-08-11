# Service Generation Rules (per Niche)

## Template Variable Pattern
When generating service cards for a lead, produce 6 cards as HTML (with SVG icons, NOT emoji, NOT price badges):

```html
<div class="service-card">
  <div class="icon"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="SVG_PATH_HERE"/></svg></div>
  <h3>Service Name</h3>
  <p>Service description — brief, specific, no fluff.</p>
</div>
```

## Plumber
1. Emergency Repair — 24/7 for burst pipes, sewage backups, gas leaks
2. Drain Cleaning — Clogged drains, slow sinks, backed-up toilets
3. Water Heater — Installation, repair, replacement — tank & tankless
4. Pipe Repair — Leaks, frozen pipes, repiping — copper, PEX, PVC
5. Fixture Installation — Toilets, faucets, disposals, shower heads
6. Sewer & Drain — Sewer scope, main line cleaning, trenchless repair

## HVAC
1. AC Repair — Central air, ductless mini-splits, heat pumps
2. Furnace Service — Gas, oil, electric — repair & installation
3. Heating Repair — Boilers, radiators, baseboard heat
4. Thermostat — Smart thermostats, zoning, programmable
5. Ductwork — Cleaning, sealing, installation, repair
6. Indoor Air Quality — Humidifiers, air purifiers, ventilation

## Electrician
1. Electrical Repair — Wiring, outlets, switches, panels
2. Lighting — Installation, fixtures, outdoor lighting
3. Panel Upgrade — 200 amp service, breaker panels, wiring
4. Safety Inspection — Home electrical safety audit
5. Generator — Standby generator installation & service
6. Smart Home — Smart switches, thermostats, automation

## About Section Generation
Generate 2 paragraphs:
- ABOUT_HEADING: "Serving {CITY} for Over {YEARS} Years"
- ABOUT_TEXT: "We're a locally owned and operated {niche} serving the {REGION} area. Every job gets our full attention, and every fix comes with a guarantee. No upselling, no hidden fees, no excuses."
- ABOUT_TEXT_2: "Every technician is background-checked, licensed, and trained on the latest equipment. 100% satisfaction guarantee. If you're not happy, we're not happy."
