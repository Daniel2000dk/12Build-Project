# Lead Automation Systeem – CLAUDE.md

## Wat is dit project

Een zelfgebouwd lead automation systeem voor een commercieel team in de bouwsector Nederland.
Het systeem zoekt ZELF actief naar relevante bedrijven – er wordt niet gewacht op inkomende leads.

De kern van het systeem:
1. Zoek zelf bedrijven op die passen bij onze doelgroep
2. Vind automatisch de juiste beslisser per bedrijf (DMU)
3. Stuur een gepersonaliseerd LinkedIn bericht + mail
4. Wacht op reactie – alleen bij reactie krijgt de gebruiker een melding
5. Melding = hete lead = bellen

Geen HubSpot koppeling. Geen externe CRM. Eigen database, eigen interface, alles lokaal.

---

## Doelgroep van het systeem

Het systeem zoekt naar deze bedrijven in Nederland:

- Onderaannemers in de bouw die meer projecten willen
- Bouwbedrijven die groeien (vacatures, nieuwe vestiging, uitbreiding)
- Bedrijven die zoeken naar meer vindbaarheid of commerciële slagkracht
- Bedrijven met een account manager of commercieel directeur vacature open
- Leveranciers in de bouw die hun klantenbestand willen uitbreiden

Signalen dat een bedrijf relevant is:
- Vacature voor: account manager, commercieel directeur, salesmanager, inkoper
- LinkedIn post over: groei, nieuw project, nieuwe medewerker, uitbreiding
- Website tekst: "wij zoeken projecten", "wij hebben capaciteit", "neem contact op voor samenwerking"
- Branchevereniging lidmaatschap (Bouwend Nederland, Uneto-VNI, etc.)

---

## Stack

| Laag | Technologie | Waarom |
|------|-------------|--------|
| Frontend | Vanilla HTML + CSS + JS | Simpel, geen framework nodig |
| Backend | Python + Flask | Gratis, werkt lokaal |
| Database | SQLite | Geen installatie, één bestand |
| Mail | Python smtplib + Gmail app-wachtwoord | Gratis, geen API |
| AI teksten | Anthropic API (claude-sonnet-4-6) | Genereert berichten |
| Leadfinder | Python requests + BeautifulSoup + SerpAPI | Zoekt publieke bronnen |
| LinkedIn | Handmatig met voorbereide templates | Gratis, geen blokkade risico |

---

## Projectstructuur

```
/lead-automation
  CLAUDE.md                    ← dit bestand, altijd in root
  app.py                       ← Flask backend
  database.py                  ← alle databasefuncties
  leads.db                     ← SQLite (automatisch aangemaakt)
  requirements.txt
  .env                         ← wachtwoorden en keys (NOOIT in Git)
  .env.example                 ← voorbeeld zonder echte waarden
  .gitignore                   ← bevat: .env, leads.db, logs/

  /templates
    index.html                 ← dashboard (leadoverzicht + acties)
    lead_detail.html           ← detailpagina per lead
    scanner.html               ← leadfinder interface
    notificaties.html          ← alleen hete leads
    instellingen.html          ← mail instellen, zoektermen beheren

  /static
    style.css
    app.js

  /modules
    leadfinder.py              ← zoekt zelf nieuwe bedrijven (KERN MODULE)
    dmu_finder.py              ← vindt beslissers per bedrijf
    ai_writer.py               ← schrijft berichten via Claude API
    mail_sender.py             ← verstuurt mails via Gmail SMTP
    linkedin_prep.py           ← bereidt LinkedIn berichten voor
    notifier.py                ← beheert meldingen en hete lead status
    reply_checker.py           ← checkt of er een reactie is binnengekomen

  /data
    zoektermen.json            ← trefwoorden voor de leadfinder
    mock_leads.json            ← testdata voor fase 1
    mock_bedrijven.json        ← nep zoekresultaten voor fase 1

  /logs
    app.log
    scanner.log
```

---

## De volledige workflow

```
STAP 1 – LEADFINDER (automatisch, draait continu op achtergrond)
─────────────────────────────────────────────────────────────────
Systeem zoekt op:
  • Google / DuckDuckGo: "onderaannemer bouw Nederland capaciteit beschikbaar"
  • Indeed: vacatures voor account manager + bouw + Nederland
  • Nationale Vacaturebank: zelfde zoekopdracht
  • LinkedIn publiek: posts met "wij groeien", "nieuw project", "wij zoeken"
  • Bouwend Nederland ledenlijst (publiek beschikbaar)

Filter: is het een bouwbedrijf? Actief in NL? Meer dan 5 medewerkers?
Resultaat: lijst nieuwe bedrijven met naam, website, sector, bron

        ↓

STAP 2 – DMU FINDER (automatisch per nieuw bedrijf)
────────────────────────────────────────────────────
Per gevonden bedrijf:
  • Website scrapen → "Over ons" / "Team" pagina → naam + functie extraheren
  • LinkedIn publiek zoeken: "[bedrijfsnaam] directeur" of "commercieel directeur"
  • Prioriteit: eigenaar / DGA > commercieel directeur > salesmanager > inkoper

Resultaat: 1-3 contactpersonen met naam, functie, LinkedIn URL, eventueel mailadres

        ↓

STAP 3 – AI BERICHTGENERATOR (automatisch per contactpersoon)
─────────────────────────────────────────────────────────────
Claude API genereert op basis van:
  • Bedrijfsnaam, sector, locatie, grootte
  • Waarom het bedrijf gevonden is (groeisignaal, vacature, etc.)
  • Naam en functie van de contactpersoon

Output 1: LinkedIn bericht (max 300 tekens, persoonlijk, geen spam-taal)
Output 2: Mail (onderwerp + 3 alinea's, professioneel, concreet)
Output 3: Follow-up mail voor als er geen reactie komt na 5 dagen

Alle berichten worden opgeslagen – nooit twee keer genereren voor dezelfde persoon

        ↓

STAP 4 – LINKEDIN BERICHT (handmatig met één klik)
───────────────────────────────────────────────────
Dashboard toont: "5 LinkedIn berichten klaarstaan vandaag"
Gebruiker klikt op naam → ziet bericht → klikt "Kopieer" → plakt op LinkedIn
Klikt "Verstuurd" → systeem registreert datum en tijd
Systeem wacht 1 dag → dan automatisch mail versturen

        ↓

STAP 5 – MAIL VERSTUREN (volledig automatisch)
──────────────────────────────────────────────
Mail gaat automatisch via Gmail SMTP
Onderwerp en inhoud al gegenereerd in stap 3
Systeem wacht op reply in inbox

Geen reactie na 5 dagen → follow-up mail automatisch
Nog geen reactie na 10 dagen → lead status wordt "koud"

        ↓

STAP 6 – REACTIE DETECTIE (automatisch, elke 30 minuten)
─────────────────────────────────────────────────────────
reply_checker.py logt in op Gmail → zoekt op replies van bekende leads
Reactie gevonden? → Lead status = HEET 🔥
Melding aangemaakt: "Bel [naam] nu – reageerde op [datum]"
Dashboard toont rood notificatie-icoontje

        ↓

STAP 7 – MELDING AAN GEBRUIKER
───────────────────────────────
Notificatiepagina toont:
  • Naam + bedrijf + functie
  • Wat ze precies zeiden (mail preview)
  • Telefoonnummer indien gevonden
  • Knop: "Markeer als gebeld"
  • Knop: "Plan afspraak in"
```

---

## Bouwfases – in deze volgorde

### Fase 1 – Interface en database (gratis, geen API)
**Doel: werkende app met mock data om aan manager te laten zien**

- [ ] SQLite database aanmaken met tabellen: leads, contactpersonen, berichten, acties, notificaties
- [ ] Mock data inladen: 15 nep-bedrijven in verschillende fases van de workflow
- [ ] Dashboard bouwen: tabel met bedrijven, status, laatste actie, volgende actie
- [ ] Statusflow zichtbaar maken: Gevonden → DMU zoeken → Berichten klaar → LinkedIn verstuurd → Mail verstuurd → Reactie → HEET → Gebeld
- [ ] Detailpagina per lead: tijdlijn van alle acties, contactpersonen, berichten
- [ ] Notificatiepagina: alleen hete leads, gesorteerd op recentste reactie
- [ ] Basisfilters: status, sector, regio, datum gevonden

**Resultaat:** Volledig werkende interface, alles nep maar realistisch. Geschikt om voor te leggen.

---

### Fase 2 – Leadfinder (gratis)
**Doel: systeem vindt zelf echte bedrijven**

- [ ] `zoektermen.json` vullen met relevante zoekopdrachten voor bouwsector NL
- [ ] DuckDuckGo zoekmodule – haalt eerste 10 resultaten op per zoekopdracht
- [ ] Indeed scraper – zoekt vacatures op trefwoord + sector + locatie NL
- [ ] Resultaten filteren op relevantie (is het een bouwbedrijf? NL? groot genoeg?)
- [ ] Duplicaten detecteren – zelfde bedrijf niet twee keer toevoegen
- [ ] Goedkeuringsscherm – gebruiker ziet nieuwe bedrijven, keurt goed of wijst af
- [ ] Na goedkeuring: bedrijf wordt lead, DMU finder start automatisch

**Let op bij bouwen:**
- Gebruik DuckDuckGo in plaats van Google (minder blokkade)
- Altijd 5-10 seconden pauze tussen requests
- Maximaal 20 zoekopdrachten per sessie
- User-Agent instellen als normale browser header
- Als een site blokkeert: overslaan, niet crashen

---

### Fase 3 – DMU Finder (gratis)
**Doel: systeem vindt de juiste beslisser per bedrijf**

- [ ] Website scraper – bezoekt bedrijfswebsite, zoekt "Team" of "Over ons" pagina
- [ ] Naam + functie extraheren uit tekst (eigenaar, directeur, manager)
- [ ] LinkedIn zoek-URL genereren: `linkedin.com/search/results/people/?keywords=[naam]+[bedrijf]`
- [ ] Prioriteitslogica: DGA/eigenaar eerst, dan commercieel directeur, dan salesmanager
- [ ] Contactpersoon opslaan bij lead met: naam, functie, LinkedIn URL, vertrouwen-score
- [ ] Interface toont: "2 beslissers gevonden – bekijk en bevestig"

**Let op bij bouwen:**
- LinkedIn scrapen is gevoelig – gebruik alleen de publieke zoekpagina, niet inloggen
- Als website geen teampagina heeft: sla DMU op als "niet gevonden", ga toch door
- Vertrouwen-score toevoegen: zeker (naam op website) / waarschijnlijk (LinkedIn match) / onzeker

---

### Fase 4 – AI berichtgenerator (kleine kosten ~€2-5/mnd)
**Doel: gepersonaliseerde berichten zonder handmatig typen**

- [ ] Anthropic API koppelen via .env bestand
- [ ] Prompt voor LinkedIn bericht: kort, persoonlijk, geen buzzwords, max 300 tekens
- [ ] Prompt voor eerste mail: 3 alinea's, waarom juist dit bedrijf, concrete propositie
- [ ] Prompt voor follow-up mail: lichte reminder, andere invalshoek
- [ ] Gegenereerde berichten opslaan in database (nooit dubbel genereren)
- [ ] Interface: bericht tonen met "Aanpassen" en "Goedkeuren" knop
- [ ] Kosten-teller: toont hoeveel API calls gedaan zijn deze maand

**Prompt structuur voor Claude (gebruik dit als basis):**
```
Schrijf een LinkedIn bericht voor een commercieel medewerker in de bouwsector.

Bedrijf: [naam]
Sector: [sector]
Locatie: [stad]
Contactpersoon: [naam], [functie]
Reden van contact: [groeisignaal / vacature / capaciteit beschikbaar]

Regels:
- Maximaal 300 tekens
- Professioneel maar niet formeel
- Specifiek voor dit bedrijf, geen generieke tekst
- Geen: "Ik zag uw profiel", "Ik kom graag in contact", "Hopelijk tot snel"
- Wel: directe opening, concrete reden, duidelijke volgende stap
- Schrijf in het Nederlands
```

---

### Fase 5 – Mail versturen (gratis)
**Doel: mails gaan automatisch de deur uit**

- [ ] Gmail app-wachtwoord instellen (zie instructie hieronder)
- [ ] `mail_sender.py` bouwen met Python smtplib
- [ ] Mail versturen vanuit zakelijk Gmail adres
- [ ] Daglimiet instellen: maximaal 150 mails per dag (anders blokkeert Gmail)
- [ ] Bounce detectie: als mail niet aankomt → lead markeren als "ongeldig mailadres"
- [ ] Verzonden mails opslaan in database met datum en tijd
- [ ] Interface toont: mailstatus per lead (gepland / verstuurd / geopend / reactie)

**Gmail app-wachtwoord instellen:**
```
1. Ga naar myaccount.google.com
2. Beveiliging → zet 2-stapsverificatie AAN
3. Beveiliging → App-wachtwoorden
4. Kies "Overige" → naam: "Lead Automation"
5. Kopieer het 16-cijferige wachtwoord
6. Zet in .env bestand:
   GMAIL_ADDRESS=jouw@gmail.com
   GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

**Let op:**
- Nooit meer dan 150 mails per dag via Gmail
- Altijd een echte afzendernaam gebruiken (niet noreply)
- Bouw een pauze van 30-60 seconden tussen mails
- Mailadres van leads altijd verifiëren voor verzending

---

### Fase 6 – Reactie detectie (gratis)
**Doel: systeem herkent automatisch een reactie en maakt melding aan**

- [ ] `reply_checker.py` logt in op Gmail via IMAP
- [ ] Zoekt elke 30 minuten op nieuwe mails van bekende lead-adressen
- [ ] Reactie gevonden → lead status wordt HEET
- [ ] Notificatie aangemaakt met: naam, bedrijf, preview van het bericht, tijdstip
- [ ] Dashboard toont rood icoontje bij notificaties
- [ ] Notificatiepagina toont alle hete leads gesorteerd op recentste reactie

---

### Fase 7 – LinkedIn voorbereiding uitbreiden (gratis)
**Doel: LinkedIn flow zo efficiënt mogelijk maken**

- [ ] Dagelijkse wachtrij: "Dit moet je vandaag versturen op LinkedIn"
- [ ] Per bericht: kopieerknop + directe link naar LinkedIn profiel
- [ ] Na klikken "Verstuurd": systeem plant automatisch de mail voor morgen
- [ ] Statistieken: hoeveel LinkedIn berichten verstuurd, hoeveel geopend, hoeveel reacties

**Later optioneel – PhantomBuster (~€55/mnd):**
Volledig automatisch LinkedIn berichten versturen. Alleen zinvol bij meer dan 20 leads per week.
Bouw het systeem zo dat PhantomBuster er later als losse module aan gekoppeld kan worden.

---

## Veiligheid – verplicht vanaf dag 1

```
# .env bestand (NOOIT committen naar Git)
GMAIL_ADDRESS=jouw@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=willekeurige-lange-string-van-32-tekens

# .gitignore (altijd aanmaken in fase 1)
.env
leads.db
logs/
__pycache__/
*.pyc
```

Verplichte beveiligingsmaatregelen:
- Alle keys en wachtwoorden alleen in `.env` – nooit hardcoded in Python of HTML
- `leads.db` nooit online zetten – bevat persoonsgegevens
- Geen namen of mailadressen in logbestanden schrijven
- App alleen bereikbaar via `localhost` – niet publiek
- Wekelijkse backup van `leads.db` naar externe schijf

---

## Stijlregels interface

- Alle tekst in het Nederlands
- Statuskleur: Gevonden (grijs) → Benaderd (blauw) → LinkedIn verstuurd (paars) → Mail verstuurd (geel) → Reactie (oranje) → HEET (rood) → Gebeld (groen)
- Tijdlijn per lead: elke actie met datum en tijd
- Alleen tonen wat nu relevant is – geen onnodige knoppen
- Desktop tool – mobiel hoeft niet

---

## Hoe te starten

```bash
# Installeer vereisten
pip install flask requests beautifulsoup4 anthropic python-dotenv

# Maak .env aan
cp .env.example .env
# Vul je eigen waarden in

# Start de app
python app.py
# Open: http://localhost:5000
```

---

## Instructies voor Claude Code

- Begin altijd met fase 1 – database + mock data + interface
- Bouw één fase volledig af voor je verder gaat
- Elke module moet zelfstandig te testen zijn zonder de rest
- Schrijf Nederlandse comments boven elke functie
- Voeg altijd foutafhandeling toe – als externe bron niet reageert crasht de app niet
- Gebruik mock data tot fase 5 klaar is – geen echte persoonsgegevens tijdens ontwikkeling
- Bij elke fase: maak eerst een werkende versie, dan pas verfijnen
