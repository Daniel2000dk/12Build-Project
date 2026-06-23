import requests
import json
import time
import random
import logging
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZOEKTERMEN_PATH = os.path.join(BASE_DIR, 'data', 'zoektermen.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
}

def laad_zoektermen():
    with open(ZOEKTERMEN_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def wacht(min_sec=5, max_sec=10):
    tijd = random.uniform(min_sec, max_sec)
    time.sleep(tijd)

def is_relevant_domein(url, zoektermen):
    irrelevant = zoektermen.get('filter_keywords', {}).get('irrelevant', [])
    domein = urlparse(url).netloc.lower()
    for woord in irrelevant:
        if woord in domein:
            return False
    # Skip bekende niet-bedrijfsdomeinen
    skip_domeinen = [
        'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
        'youtube.com', 'wikipedia.org', 'kvk.nl', 'indeed.com',
        'werkenbij', 'jobbird', 'nationalevacaturebank', 'monsterboard',
        'glassdoor', 'intermediair', 'vacature', 'jobs.'
    ]
    for skip in skip_domeinen:
        if skip in domein:
            return False
    return True

def is_bouwbedrijf(tekst, zoektermen):
    relevant_keywords = zoektermen.get('filter_keywords', {}).get('relevant', [])
    tekst_lower = tekst.lower()
    gevonden = sum(1 for kw in relevant_keywords if kw in tekst_lower)
    return gevonden >= 1

def extraheer_bedrijfsnaam_uit_url(url):
    domein = urlparse(url).netloc
    domein = domein.replace('www.', '')
    naam = domein.split('.')[0]
    # Maak leesbaar: koppeltekens naar spaties, hoofdletter
    naam = naam.replace('-', ' ').replace('_', ' ')
    return naam.title()

def zoek_duckduckgo(zoekopdracht, max_resultaten=10):
    """Zoekt op DuckDuckGo en geeft lijst van gevonden URLs terug."""
    resultaten = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(zoekopdracht)}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        for link in soup.select('a.result__url'):
            href = link.get('href', '')
            tekst = link.get_text(strip=True)
            if href and href.startswith('http'):
                resultaten.append({'url': href, 'titel': tekst})
            if len(resultaten) >= max_resultaten:
                break

        # Alternatief: zoek via result__a links
        if not resultaten:
            for link in soup.select('a.result__a'):
                href = link.get('href', '')
                tekst = link.get_text(strip=True)
                if href and 'duckduckgo.com' not in href:
                    resultaten.append({'url': href, 'titel': tekst})
                if len(resultaten) >= max_resultaten:
                    break

    except Exception as e:
        logger.warning(f"DuckDuckGo fout voor '{zoekopdracht}': {e}")

    return resultaten

def haal_website_info(url):
    """Bezoekt een website en haalt basisinformatie op."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Bedrijfsnaam uit title tag
        title = soup.find('title')
        naam = title.get_text(strip=True) if title else ''
        if ' - ' in naam:
            naam = naam.split(' - ')[0].strip()
        elif ' | ' in naam:
            naam = naam.split(' | ')[0].strip()

        # Omschrijving uit meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        omschrijving = meta_desc.get('content', '') if meta_desc else ''

        # Pagina tekst voor relevantie check
        tekst = soup.get_text(' ', strip=True)[:2000]

        # Stad/locatie zoeken in tekst
        regio = extraheer_regio(tekst)

        return {
            'naam': naam[:100] if naam else '',
            'website': url,
            'omschrijving': omschrijving[:300] if omschrijving else '',
            'tekst': tekst,
            'regio': regio,
            'sector': 'Bouw'
        }
    except Exception as e:
        logger.debug(f"Website ophalen mislukt voor {url}: {e}")
        return None

def extraheer_regio(tekst):
    """Probeert een Nederlandse stad te herkennen in de tekst."""
    steden = [
        'Amsterdam', 'Rotterdam', 'Den Haag', 'Utrecht', 'Eindhoven',
        'Tilburg', 'Groningen', 'Almere', 'Breda', 'Nijmegen',
        'Enschede', 'Apeldoorn', 'Haarlem', 'Arnhem', 'Zaanstad',
        'Amersfoort', 'Zwolle', 'Maastricht', 'Leiden', 'Dordrecht',
        'Zoetermeer', 'Deventer', 'Emmen', 'Delft', 'Helmond',
        'Alkmaar', 'Venlo', 'Leeuwarden', 'Ede', 'Westland',
        'Gouda', 'Purmerend', 'Middelburg', 'Roosendaal', 'Bergen op Zoom',
        'Noord-Holland', 'Zuid-Holland', 'Noord-Brabant', 'Gelderland',
        'Utrecht', 'Overijssel', 'Limburg', 'Friesland', 'Groningen',
        'Drenthe', 'Zeeland', 'Flevoland'
    ]
    tekst_lower = tekst.lower()
    for stad in steden:
        if stad.lower() in tekst_lower:
            return stad
    return 'Nederland'

def zoek_indeed_vacatures(trefwoord, locatie='Nederland', max_resultaten=5):
    """Zoekt vacatures op Indeed en retourneert bedrijfsnamen."""
    bedrijven = []
    try:
        url = f"https://nl.indeed.com/jobs?q={quote_plus(trefwoord)}&l={quote_plus(locatie)}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Indeed bedrijfsnamen uit job cards
        for card in soup.select('[data-company-name]'):
            naam = card.get('data-company-name', '').strip()
            if naam and naam not in [b['naam'] for b in bedrijven]:
                bedrijven.append({
                    'naam': naam,
                    'bron': f'Indeed vacature: {trefwoord}',
                    'signaal': f'Vacature gevonden: {trefwoord}',
                    'sector': 'Bouw',
                    'regio': locatie
                })
            if len(bedrijven) >= max_resultaten:
                break

        # Alternatief: span met company class
        if not bedrijven:
            for el in soup.select('span.companyName, [data-testid="company-name"]'):
                naam = el.get_text(strip=True)
                if naam and naam not in [b['naam'] for b in bedrijven]:
                    bedrijven.append({
                        'naam': naam,
                        'bron': f'Indeed vacature: {trefwoord}',
                        'signaal': f'Vacature gevonden: {trefwoord}',
                        'sector': 'Bouw',
                        'regio': locatie
                    })
                if len(bedrijven) >= max_resultaten:
                    break

    except Exception as e:
        logger.warning(f"Indeed fout voor '{trefwoord}': {e}")

    return bedrijven

def run_leadfinder(max_zoekopdrachten=5, max_resultaten_per_opdracht=8):
    """
    Hoofdfunctie: voert zoeksessie uit en geeft lijst van gevonden leads terug.
    Elke lead heeft: naam, website, omschrijving, sector, regio, bron, signaal
    """
    zoektermen = laad_zoektermen()
    gevonden_leads = []
    geziene_urls = set()
    geziene_namen = set()

    duckduckgo_zoekopdrachten = zoektermen.get('duckduckgo', [])[:max_zoekopdrachten]

    logger.info(f"Start leadfinder sessie: {len(duckduckgo_zoekopdrachten)} DuckDuckGo zoekopdrachten")

    for i, opdracht in enumerate(duckduckgo_zoekopdrachten):
        logger.info(f"Zoekopdracht {i+1}/{len(duckduckgo_zoekopdrachten)}: {opdracht}")

        resultaten = zoek_duckduckgo(opdracht, max_resultaten=max_resultaten_per_opdracht)

        for res in resultaten:
            url = res.get('url', '')
            if not url or url in geziene_urls:
                continue
            if not is_relevant_domein(url, zoektermen):
                continue

            geziene_urls.add(url)

            # Website info ophalen
            info = haal_website_info(url)
            if not info:
                continue

            if not is_bouwbedrijf(info.get('tekst', '') + ' ' + info.get('omschrijving', ''), zoektermen):
                continue

            naam = info.get('naam') or extraheer_bedrijfsnaam_uit_url(url)
            naam_lower = naam.lower()

            if naam_lower in geziene_namen or len(naam) < 3:
                continue
            geziene_namen.add(naam_lower)

            lead = {
                'naam': naam,
                'website': url,
                'omschrijving': info.get('omschrijving', ''),
                'sector': 'Bouw',
                'regio': info.get('regio', 'Nederland'),
                'bron': f'DuckDuckGo: {opdracht[:50]}',
                'signaal': 'Website gevonden via zoekopdracht bouwsector NL'
            }
            gevonden_leads.append(lead)
            logger.info(f"Lead gevonden: {naam} ({url[:50]})")

            wacht(2, 5)

        # Pauze tussen zoekopdrachten
        if i < len(duckduckgo_zoekopdrachten) - 1:
            wacht(6, 12)

    # Indeed vacatures
    indeed_opdrachten = zoektermen.get('indeed_vacatures', [])[:3]
    for vac in indeed_opdrachten:
        logger.info(f"Indeed scan: {vac['trefwoord']}")
        indeed_bedrijven = zoek_indeed_vacatures(vac['trefwoord'], vac.get('locatie', 'Nederland'))

        for b in indeed_bedrijven:
            naam_lower = b['naam'].lower()
            if naam_lower not in geziene_namen and len(b['naam']) > 2:
                geziene_namen.add(naam_lower)
                gevonden_leads.append(b)
                logger.info(f"Indeed lead: {b['naam']}")

        wacht(8, 15)

    logger.info(f"Leadfinder klaar: {len(gevonden_leads)} leads gevonden")
    return gevonden_leads
