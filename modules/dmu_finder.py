import re
import requests
import logging
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
}

FUNCTIE_PRIORITEIT = {
    'eigenaar': 10, 'dga': 10, 'directeur-grootaandeelhouder': 10,
    'directeur': 9, 'ceo': 9, 'managing director': 9, 'algemeen directeur': 9,
    'zaakvoerder': 9, 'bestuurder': 9, 'oprichter': 8, 'founder': 8,
    'commercieel directeur': 8, 'commercial director': 8, 'directrice': 9,
    'salesmanager': 7, 'sales manager': 7, 'hoofd verkoop': 7,
    'business development': 7, 'verkoopmanager': 7,
    'accountmanager': 6, 'account manager': 6,
    'inkoper': 5, 'hoofd inkoop': 5, 'purchasing': 5,
    'manager': 4, 'teamleider': 3,
}

FUNCTIE_WOORDEN = list(set(
    list(FUNCTIE_PRIORITEIT.keys()) + [
        'partner', 'vennoot', 'president', 'hoofd', 'director',
        'owner', 'procurement', 'leidinggevende', 'bestuurslid',
    ]
))

TEAM_PADEN = [
    '/over-ons', '/over', '/team', '/management', '/directie',
    '/bestuur', '/mensen', '/ons-team', '/organisatie',
    '/about', '/about-us', '/wie-zijn-wij', '/medewerkers',
    '/leadership', '/our-team', '/contact', '/over-ons/team',
    '/over-ons/directie', '/bedrijf', '/over-ons/management',
]

# Trefwoorden voor team-pagina links
TEAM_LINK_WOORDEN = [
    'team', 'over ons', 'over-ons', 'management', 'directie',
    'mensen', 'medewerkers', 'organisatie', 'wie zijn wij', 'bestuur',
    'about', 'leadership', 'our team',
]


def is_naam(tekst):
    if not tekst or len(tekst) < 4 or len(tekst) > 60:
        return False
    if any(c.isdigit() for c in tekst):
        return False
    if any(c in tekst for c in ['@', '.com', '.nl', ':', '/', '\\', '<', '>']):
        return False
    woorden = tekst.strip().split()
    if len(woorden) < 2 or len(woorden) > 6:
        return False
    eerste = woorden[0].lower()
    if eerste in ('de', 'van', 'den', 'der', 'het', "'t", 'voor', 'bij'):
        return False
    if not woorden[0][0].isupper():
        return False
    return True


def is_functie(tekst):
    if not tekst or len(tekst) < 3 or len(tekst) > 100:
        return False
    tekst_lower = tekst.lower()
    return any(f in tekst_lower for f in FUNCTIE_WOORDEN)


def prioriteit_score(functie):
    if not functie:
        return 0
    f_lower = functie.lower()
    for f, score in FUNCTIE_PRIORITEIT.items():
        if f in f_lower:
            return score
    return 1


def email_naar_naam(lokaal_deel):
    """Probeert 'j.deboer' of 'jan.deboer' om te zetten naar leesbare naam."""
    lokaal_deel = re.sub(r'\d+', '', lokaal_deel)
    delen = re.split(r'[._\-]', lokaal_deel)
    delen = [d for d in delen if len(d) > 1]
    if len(delen) < 2:
        return None
    return ' '.join(d.capitalize() for d in delen)


def haal_pagina_op(url, timeout=10):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, 'html.parser')
    except Exception:
        pass
    return None


def extraheer_contacten_uit_soup(soup):
    contacten = []

    # Strategie 1: Schema.org Person markup
    for person_el in soup.find_all(attrs={'itemtype': re.compile('schema.org/Person', re.I)}):
        naam_el = person_el.find(attrs={'itemprop': 'name'})
        functie_el = person_el.find(attrs={'itemprop': 'jobTitle'})
        email_el = person_el.find(attrs={'itemprop': 'email'})
        if naam_el:
            naam = naam_el.get_text(strip=True)
            if is_naam(naam):
                contacten.append({
                    'naam': naam,
                    'functie': functie_el.get_text(strip=True) if functie_el else '',
                    'email': email_el.get_text(strip=True) if email_el else '',
                    'bron': 'website (schema.org)',
                    'vertrouwen': 'zeker',
                })
    if contacten:
        return contacten

    # Strategie 2: CSS class patronen voor team-blokken
    team_class_patronen = [
        r'team[\-_]?member', r'medewerker', r'person[\-_]?card',
        r'staff[\-_]?member', r'team[\-_]?item', r'management[\-_]?item',
        r'profile[\-_]?card', r'bio[\-_]?card', r'employee',
        r'organisatie[\-_]?item', r'team[\-_]?card', r'people[\-_]?item',
    ]
    for patroon in team_class_patronen:
        blokken = soup.find_all(class_=re.compile(patroon, re.I))
        for blok in blokken[:6]:
            naam = None
            functie = None
            email = None
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'strong']:
                for el in blok.find_all(tag)[:2]:
                    tekst = el.get_text(strip=True)
                    if is_naam(tekst):
                        naam = tekst
                        break
                if naam:
                    break
            for tag in ['p', 'span', 'em', 'small', 'div']:
                for el in blok.find_all(tag)[:5]:
                    tekst = el.get_text(strip=True)
                    if is_functie(tekst) and tekst != naam:
                        functie = tekst[:80]
                        break
                if functie:
                    break
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', blok.get_text())
            if email_match:
                email = email_match.group()
            if naam:
                contacten.append({
                    'naam': naam,
                    'functie': functie or '',
                    'email': email or '',
                    'bron': 'website',
                    'vertrouwen': 'zeker' if functie else 'waarschijnlijk',
                })
    if contacten:
        return contacten

    # Strategie 3: Tekstpatronen "Naam, Functie" of "Functie: Naam"
    tekst = soup.get_text(' ', strip=True)
    for functie_woord in ['Directeur', 'Eigenaar', 'CEO', 'DGA', 'Zaakvoerder',
                           'Commercieel Directeur', 'Salesmanager', 'Manager']:
        p1 = re.compile(
            r'([A-Z][a-z]+(?:\s+(?:van\s+|de\s+|den\s+|der\s+)?[A-Z][a-z]+)+)'
            r',?\s+' + re.escape(functie_woord), re.I
        )
        p2 = re.compile(
            re.escape(functie_woord) + r'[:\s]+([A-Z][a-z]+(?:\s+(?:van\s+|de\s+|den\s+|der\s+)?[A-Z][a-z]+)+)',
            re.I
        )
        for p in [p1, p2]:
            for m in p.finditer(tekst):
                naam = m.group(1).strip()
                if is_naam(naam) and naam not in [c['naam'] for c in contacten]:
                    contacten.append({
                        'naam': naam,
                        'functie': functie_woord,
                        'bron': 'website (tekst)',
                        'vertrouwen': 'waarschijnlijk',
                    })

    # Strategie 4: DL/DT/DD lijsten
    for dl in soup.find_all('dl'):
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            key = dt.get_text(strip=True).lower()
            val = dd.get_text(strip=True)
            if any(f in key for f in ['naam', 'name', 'eigenaar', 'directeur', 'manager', 'contact']):
                if is_naam(val):
                    contacten.append({
                        'naam': val,
                        'functie': key.title(),
                        'bron': 'website',
                        'vertrouwen': 'zeker',
                    })

    # Strategie 5: Email-adressen als fallback
    if not contacten:
        skip_lokaal = {
            'info', 'contact', 'administratie', 'reception', 'secretariaat',
            'algemeen', 'post', 'mail', 'office', 'support', 'service',
            'verkoop', 'sales', 'inkoop', 'directie',
        }
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', tekst)
        for email in emails[:5]:
            lokaal = email.split('@')[0].lower()
            if lokaal in skip_lokaal:
                continue
            naam = email_naar_naam(lokaal)
            if naam and is_naam(naam):
                contacten.append({
                    'naam': naam,
                    'functie': 'Onbekend',
                    'email': email,
                    'bron': 'website (email)',
                    'vertrouwen': 'onzeker',
                })

    return contacten


def scrape_website_dmu(website_url):
    """Scrapet de bedrijfswebsite en geeft lijst van contactpersonen terug."""
    if not website_url:
        return []
    if not website_url.startswith('http'):
        website_url = 'https://' + website_url

    parsed = urlparse(website_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    alle_contacten = []
    geprobeerde_urls = {website_url}
    team_links_gevonden = []

    # Stap 1: Homepage
    soup = haal_pagina_op(website_url)
    if soup:
        alle_contacten.extend(extraheer_contacten_uit_soup(soup))
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').strip()
            tekst = a.get_text(strip=True).lower()
            if any(t in tekst or t in href.lower() for t in TEAM_LINK_WOORDEN):
                full_url = urljoin(base_url, href)
                if full_url.startswith(base_url) and full_url not in geprobeerde_urls:
                    team_links_gevonden.append(full_url)
                    geprobeerde_urls.add(full_url)

    # Stap 2: Team-links gevonden via homepage
    for url in team_links_gevonden[:4]:
        if len(alle_contacten) >= 3:
            break
        soup = haal_pagina_op(url)
        if soup:
            alle_contacten.extend(extraheer_contacten_uit_soup(soup))
        time.sleep(random.uniform(1, 2))

    # Stap 3: Standaard paden als we nog onvoldoende hebben
    if len(alle_contacten) < 2:
        for pad in TEAM_PADEN[:10]:
            url = base_url + pad
            if url in geprobeerde_urls:
                continue
            geprobeerde_urls.add(url)
            soup = haal_pagina_op(url)
            if soup:
                alle_contacten.extend(extraheer_contacten_uit_soup(soup))
            if len(alle_contacten) >= 3:
                break
            time.sleep(random.uniform(1, 2))

    # Dedupliceren op naam
    gezien = set()
    uniek = []
    for c in alle_contacten:
        key = c['naam'].lower().strip()
        if key not in gezien:
            gezien.add(key)
            uniek.append(c)

    uniek.sort(key=lambda c: -prioriteit_score(c.get('functie', '')))
    return uniek[:3]


def zoek_kvk_info(bedrijfsnaam):
    """
    Haalt KVK informatie op.
    Geeft altijd minimaal een zoek-URL terug.
    Probeert de KVK API (test endpoint) voor basisgegevens.
    """
    kvk_info = {
        'kvk_nummer': '',
        'rechtsvorm': '',
        'vestigingsplaats': '',
        'sbi_omschrijving': '',
        'zoek_url': f"https://www.kvk.nl/zoeken/?q={quote_plus(bedrijfsnaam)}",
    }

    try:
        # KVK test API – geeft testdata maar valideert de integratie
        api_url = f"https://api.kvk.nl/test/api/v1/zoeken?q={quote_plus(bedrijfsnaam)}&resultatenPerPagina=1"
        resp = requests.get(
            api_url,
            headers={**HEADERS, 'apikey': 'l7xx1f2691f2520d487185884a012e8ab72c'},
            timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            resultaten = data.get('resultaten', [])
            if resultaten:
                r = resultaten[0]
                kvk_info.update({
                    'kvk_nummer': r.get('kvkNummer', ''),
                    'rechtsvorm': r.get('rechtsvorm', ''),
                    'vestigingsplaats': r.get('vestigingsplaats', ''),
                    'sbi_omschrijving': r.get('sbiOmschrijving', ''),
                })
    except Exception as e:
        logger.debug(f"KVK API niet bereikbaar voor '{bedrijfsnaam}': {e}")

    return kvk_info


def genereer_linkedin_urls(contacten, bedrijfsnaam):
    """Voegt LinkedIn zoek-URL toe aan elk contact en geeft bedrijfs-URL terug."""
    for c in contacten:
        naam = c.get('naam', '')
        if naam:
            c['linkedin_zoek_url'] = (
                f"https://www.linkedin.com/search/results/people/"
                f"?keywords={quote_plus(naam + ' ' + bedrijfsnaam)}"
            )
    bedrijf_url = (
        f"https://www.linkedin.com/search/results/companies/"
        f"?keywords={quote_plus(bedrijfsnaam)}"
    )
    return contacten, bedrijf_url


def run_dmu_finder(bedrijfsnaam, website):
    """
    Hoofdfunctie: zoekt contactpersonen via website, KVK en LinkedIn.
    Geeft dict terug met contacten, kvk_info en linkedin_bedrijf_url.
    """
    logger.info(f"DMU Finder gestart voor: {bedrijfsnaam}")

    # 1. Website scrapen
    contacten = []
    if website:
        logger.info(f"Website scrapen: {website}")
        contacten = scrape_website_dmu(website)
        logger.info(f"Gevonden op website: {len(contacten)} contacten")

    # 2. KVK info ophalen
    logger.info(f"KVK opzoeken: {bedrijfsnaam}")
    kvk_info = zoek_kvk_info(bedrijfsnaam)

    # 3. LinkedIn URLs genereren
    contacten, linkedin_bedrijf_url = genereer_linkedin_urls(contacten, bedrijfsnaam)

    logger.info(f"DMU Finder klaar: {len(contacten)} contacten voor {bedrijfsnaam}")
    return {
        'contacten': contacten,
        'kvk_info': kvk_info,
        'linkedin_bedrijf_url': linkedin_bedrijf_url,
    }
