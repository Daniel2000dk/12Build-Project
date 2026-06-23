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
    'inkoper': 5, 'hoofd inkoop': 5,
    'manager': 4, 'teamleider': 3,
}

FUNCTIE_WOORDEN = list(set(list(FUNCTIE_PRIORITEIT.keys()) + [
    'partner', 'vennoot', 'president', 'hoofd', 'director', 'owner',
    'procurement', 'leidinggevende', 'bestuurslid',
]))


def prioriteit_score(functie):
    if not functie:
        return 0
    f = functie.lower()
    for kw, score in FUNCTIE_PRIORITEIT.items():
        if kw in f:
            return score
    return 1


def is_naam(tekst):
    if not tekst or len(tekst) < 4 or len(tekst) > 60:
        return False
    if any(c.isdigit() for c in tekst):
        return False
    if any(c in tekst for c in ['@', '/', '\\', '<', '>', '|', '&']):
        return False
    woorden = tekst.strip().split()
    if len(woorden) < 2 or len(woorden) > 6:
        return False
    if not woorden[0][0].isupper():
        return False
    return True


def is_functie(tekst):
    if not tekst or len(tekst) < 2 or len(tekst) > 100:
        return False
    return any(f in tekst.lower() for f in FUNCTIE_WOORDEN)


def extraheer_uit_linkedin_titel(titel):
    """
    Haalt naam en functie uit LinkedIn zoekresultaat titel.
    Voorbeeld: "Jan de Vries - Directeur bij Heijmans Bouw | LinkedIn"
    """
    # Verwijder " | LinkedIn" suffix
    titel = re.sub(r'\s*\|\s*LinkedIn.*$', '', titel, flags=re.I).strip()

    # Patroon: "Naam - Functie bij Bedrijf" of "Naam – Functie | Bedrijf"
    patronen = [
        r'^(.+?)\s*[-–]\s*(.+?)\s+(?:bij|at|@)\s+.+$',
        r'^(.+?)\s*[-–]\s*(.+)$',
        r'^(.+?)\s*[|,]\s*(.+?)\s*[|,]',
    ]
    for p in patronen:
        m = re.match(p, titel, re.I)
        if m:
            naam = m.group(1).strip()
            functie = m.group(2).strip()
            if is_naam(naam) and (is_functie(functie) or len(functie) < 50):
                return naam, functie[:80]
    return None, None


def extraheer_naam_uit_snippet(snippet, bedrijfsnaam):
    """Zoekt naar persoonsnamen in een zoekresultaat snippet."""
    gevonden = []
    bedrijf_lower = bedrijfsnaam.lower()

    # Patroon: naam gevolgd door functiewoord
    for functie in ['directeur', 'eigenaar', 'ceo', 'manager', 'dga', 'bestuurder',
                    'oprichter', 'zaakvoerder', 'commercieel', 'salesmanager']:
        p = re.compile(
            r'([A-Z][a-z]+(?:\s+(?:van\s+|de\s+|den\s+|der\s+)?[A-Z][a-z]+)+)'
            r'(?:[,\s]+' + functie + r'|\s+is\s+' + functie + r')',
            re.I
        )
        for m in p.finditer(snippet):
            naam = m.group(1).strip()
            if is_naam(naam) and naam.lower() not in bedrijf_lower:
                gevonden.append((naam, functie.title()))

    return gevonden[:2]


def zoek_duckduckgo_html(zoekopdracht, timeout=8):
    """Haalt DuckDuckGo zoekresultaten op, geeft lijst van {url, titel, snippet} terug."""
    resultaten = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(zoekopdracht)}"
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code != 200:
            return resultaten
        soup = BeautifulSoup(resp.text, 'html.parser')

        for result in soup.select('.result')[:8]:
            titel_el = result.select_one('.result__a')
            snippet_el = result.select_one('.result__snippet')
            url_el = result.select_one('.result__url')

            titel = titel_el.get_text(strip=True) if titel_el else ''
            snippet = snippet_el.get_text(strip=True) if snippet_el else ''
            link = titel_el.get('href', '') if titel_el else ''
            weergave_url = url_el.get_text(strip=True) if url_el else ''

            if titel:
                resultaten.append({
                    'titel': titel,
                    'snippet': snippet,
                    'url': link,
                    'weergave_url': weergave_url,
                })
    except Exception as e:
        logger.warning(f"DuckDuckGo fout: {e}")
    return resultaten


def zoek_beslissers_via_google(bedrijfsnaam):
    """
    Zoekt via DuckDuckGo naar beslissers van een bedrijf.
    Gebruikt LinkedIn, bedrijfswebsite en algemene zoekresultaten.
    """
    contacten = []
    geziene_namen = set()

    zoekopdrachten = [
        f'site:linkedin.com/in "{bedrijfsnaam}" directeur OR eigenaar OR CEO OR manager',
        f'"{bedrijfsnaam}" directeur eigenaar commercieel',
    ]

    for opdracht in zoekopdrachten:
        logger.info(f"Zoeken: {opdracht[:60]}")
        resultaten = zoek_duckduckgo_html(opdracht)

        for r in resultaten:
            titel = r['titel']
            snippet = r['snippet']
            url = r['url']
            is_linkedin = 'linkedin.com/in/' in url.lower() or 'linkedin.com/in/' in r.get('weergave_url', '').lower()

            naam, functie = None, None

            # LinkedIn resultaten hebben gestructureerde titels
            if is_linkedin:
                naam, functie = extraheer_uit_linkedin_titel(titel)

            # Probeer uit snippet
            if not naam:
                gevonden = extraheer_naam_uit_snippet(titel + ' ' + snippet, bedrijfsnaam)
                if gevonden:
                    naam, functie = gevonden[0]

            if naam and naam.lower() not in geziene_namen:
                geziene_namen.add(naam.lower())
                linkedin_url = url if is_linkedin else ''
                contacten.append({
                    'naam': naam,
                    'functie': functie or 'Onbekend',
                    'linkedin_url': linkedin_url,
                    'linkedin_zoek_url': f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(naam + ' ' + bedrijfsnaam)}",
                    'email': '',
                    'bron': 'LinkedIn (via Google)' if is_linkedin else 'Google zoekresultaat',
                    'vertrouwen': 'waarschijnlijk' if is_linkedin else 'onzeker',
                })

        time.sleep(random.uniform(4, 7))

    # Sorteren op prioriteit
    contacten.sort(key=lambda c: -prioriteit_score(c.get('functie', '')))
    return contacten[:3]


def scrape_homepage_snel(website_url, timeout=4):
    """Snelle scan van alleen de homepage – max 4 seconden."""
    contacten = []
    if not website_url:
        return contacten
    if not website_url.startswith('http'):
        website_url = 'https://' + website_url
    try:
        resp = requests.get(website_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return contacten
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Schema.org Person markup
        for el in soup.find_all(attrs={'itemtype': re.compile('schema.org/Person', re.I)}):
            naam_el = el.find(attrs={'itemprop': 'name'})
            functie_el = el.find(attrs={'itemprop': 'jobTitle'})
            if naam_el and is_naam(naam_el.get_text(strip=True)):
                contacten.append({
                    'naam': naam_el.get_text(strip=True),
                    'functie': functie_el.get_text(strip=True) if functie_el else '',
                    'bron': 'website (homepage)',
                    'vertrouwen': 'zeker',
                })

        # Email extractie
        if not contacten:
            skip = {'info', 'contact', 'administratie', 'secretariaat', 'post', 'mail', 'office', 'sales', 'directie'}
            for email in re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', soup.get_text()):
                lokaal = email.split('@')[0].lower()
                if lokaal not in skip and '.' in lokaal or '_' in lokaal:
                    delen = re.split(r'[._]', lokaal)
                    if len(delen) >= 2 and all(len(d) > 1 for d in delen):
                        naam = ' '.join(d.capitalize() for d in delen)
                        if is_naam(naam):
                            contacten.append({
                                'naam': naam,
                                'functie': 'Onbekend',
                                'email': email,
                                'bron': 'website (email)',
                                'vertrouwen': 'onzeker',
                            })
                            break
    except Exception as e:
        logger.debug(f"Homepage scan mislukt: {e}")
    return contacten


def genereer_zoeklinks(bedrijfsnaam):
    """Geeft directe zoeklinks terug voor handmatig gebruik."""
    naam_enc = quote_plus(bedrijfsnaam)
    return {
        'kvk': f"https://www.kvk.nl/zoeken/?q={naam_enc}",
        'linkedin_bedrijf': f"https://www.linkedin.com/search/results/companies/?keywords={naam_enc}",
        'linkedin_mensen': f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(bedrijfsnaam + ' directeur eigenaar')}",
        'google': f"https://www.google.com/search?q={quote_plus('\"' + bedrijfsnaam + '\" directeur eigenaar')}",
    }


def run_dmu_finder(bedrijfsnaam, website):
    """
    Hoofdfunctie: zoekt beslissers via DuckDuckGo (LinkedIn + Google) en snel homepage scan.
    Geeft dict terug met contacten en zoeklinks.
    """
    logger.info(f"DMU Finder gestart: {bedrijfsnaam}")

    # 1. Zoek via DuckDuckGo (LinkedIn + Google resultaten)
    contacten = zoek_beslissers_via_google(bedrijfsnaam)
    logger.info(f"Via Google/LinkedIn: {len(contacten)} contacten")

    # 2. Snelle homepage scan als aanvulling
    if len(contacten) < 2 and website:
        logger.info(f"Snelle homepage scan: {website}")
        homepage_contacten = scrape_homepage_snel(website)
        gezien = {c['naam'].lower() for c in contacten}
        for c in homepage_contacten:
            if c['naam'].lower() not in gezien:
                contacten.append(c)
                gezien.add(c['naam'].lower())

    # 3. LinkedIn zoek-URL toevoegen aan elk contact
    for c in contacten:
        if not c.get('linkedin_zoek_url'):
            c['linkedin_zoek_url'] = (
                f"https://www.linkedin.com/search/results/people/"
                f"?keywords={quote_plus(c['naam'] + ' ' + bedrijfsnaam)}"
            )

    contacten.sort(key=lambda c: -prioriteit_score(c.get('functie', '')))

    logger.info(f"DMU Finder klaar: {len(contacten)} contacten voor {bedrijfsnaam}")
    return {
        'contacten': contacten[:3],
        'zoeklinks': genereer_zoeklinks(bedrijfsnaam),
    }
