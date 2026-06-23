import os
import logging
import time

logger = logging.getLogger(__name__)


def _maak_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY niet gevonden in .env")
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


def _genereer(model, prompt, max_pogingen=3):
    for poging in range(max_pogingen):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini poging {poging + 1} mislukt: {e}")
            if poging < max_pogingen - 1:
                time.sleep(3)
    raise RuntimeError("Gemini API niet bereikbaar na 3 pogingen")


def genereer_linkedin_bericht(model, lead, contactpersoon):
    voornaam = contactpersoon["naam"].split()[0]
    prompt = f"""Schrijf een LinkedIn bericht voor een commercieel medewerker in de bouwsector.

Bedrijf: {lead["bedrijfsnaam"]}
Sector: {lead.get("sector", "Bouw")}
Locatie: {lead.get("regio", "Nederland")}
Contactpersoon: {contactpersoon["naam"]}, {contactpersoon.get("functie", "directeur")}
Reden van contact: {lead.get("groeisignaal", "bedrijf actief in de bouwsector")}

Regels:
- Maximaal 300 tekens (tel zelf na – dit is STRIKT)
- Professioneel maar direct, geen formele aanhef
- Specifiek voor dit bedrijf op basis van het groeisignaal
- Geen: "Ik zag uw profiel", "Ik kom graag in contact", "Hopelijk tot snel", "even"
- Wel: directe opening met concrete reden, één duidelijke vraag of volgende stap
- Schrijf in het Nederlands
- Geef ALLEEN het bericht terug, geen uitleg, geen aanhalingstekens"""

    tekst = _genereer(model, prompt)
    if len(tekst) > 300:
        tekst = tekst[:297] + "..."
    return tekst


def genereer_eerste_mail(model, lead, contactpersoon):
    voornaam = contactpersoon["naam"].split()[0]
    prompt = f"""Schrijf een zakelijke e-mail voor een commercieel medewerker in de bouwsector.

Bedrijf: {lead["bedrijfsnaam"]}
Sector: {lead.get("sector", "Bouw")}
Locatie: {lead.get("regio", "Nederland")}
Contactpersoon: {contactpersoon["naam"]}, {contactpersoon.get("functie", "directeur")}
Reden van contact: {lead.get("groeisignaal", "bedrijf actief in de bouwsector")}

Formaat:
ONDERWERP: [schrijf hier een pakkende onderwerpregel]

Beste {voornaam},

[Alinea 1: waarom juist dit bedrijf – koppel concreet aan het groeisignaal]

[Alinea 2: wat wij bieden – commerciële ondersteuning, meer projecten, betere vindbaarheid voor bouwbedrijven]

[Alinea 3: concrete uitnodiging voor 15 minuten gesprek deze of volgende week]

Met vriendelijke groet

Regels:
- Totaal max 200 woorden
- Geen buzzwords of verkoopjargon
- Schrijf in het Nederlands
- Geef ALLEEN de mail terug in het bovenstaande formaat, geen extra uitleg"""

    tekst = _genereer(model, prompt)

    onderwerp = f"Samenwerking {lead['bedrijfsnaam']}"
    inhoud_regels = []
    for regel in tekst.split("\n"):
        if regel.startswith("ONDERWERP:"):
            onderwerp = regel.replace("ONDERWERP:", "").strip()
        else:
            inhoud_regels.append(regel)

    inhoud = "\n".join(inhoud_regels).strip()
    return onderwerp, inhoud


def genereer_followup_mail(model, lead, contactpersoon):
    voornaam = contactpersoon["naam"].split()[0]
    prompt = f"""Schrijf een korte follow-up e-mail. Dit is een herinnering na 5 dagen zonder reactie.

Bedrijf: {lead["bedrijfsnaam"]}
Contactpersoon: {contactpersoon["naam"]}, {contactpersoon.get("functie", "directeur")}
Groeisignaal: {lead.get("groeisignaal", "")}

Formaat:
ONDERWERP: [schrijf hier de onderwerpregel]

Beste {voornaam},

[Korte, vriendelijke herinnering. Andere invalshoek dan de eerste mail. Max 3 zinnen.]

Met vriendelijke groet

Regels:
- Max 80 woorden
- Niet opdringerig, luchtig van toon
- Schrijf in het Nederlands
- Geef ALLEEN de mail terug, geen extra uitleg"""

    tekst = _genereer(model, prompt)

    onderwerp = f"Korte vraag – {lead['bedrijfsnaam']}"
    inhoud_regels = []
    for regel in tekst.split("\n"):
        if regel.startswith("ONDERWERP:"):
            onderwerp = regel.replace("ONDERWERP:", "").strip()
        else:
            inhoud_regels.append(regel)

    inhoud = "\n".join(inhoud_regels).strip()
    return onderwerp, inhoud


def run_ai_writer(lead, contactpersoon):
    """Genereert LinkedIn bericht, eerste mail en follow-up voor een lead/contactpersoon."""
    logger.info(f"AI Writer: {lead['bedrijfsnaam']} / {contactpersoon['naam']}")

    model = _maak_client()

    linkedin = genereer_linkedin_bericht(model, lead, contactpersoon)
    logger.info("LinkedIn bericht klaar")

    mail_onderwerp, mail_inhoud = genereer_eerste_mail(model, lead, contactpersoon)
    logger.info("Eerste mail klaar")

    followup_onderwerp, followup_inhoud = genereer_followup_mail(model, lead, contactpersoon)
    logger.info("Follow-up mail klaar")

    return {
        "linkedin": linkedin,
        "mail_onderwerp": mail_onderwerp,
        "mail_inhoud": mail_inhoud,
        "followup_onderwerp": followup_onderwerp,
        "followup_inhoud": followup_inhoud,
    }
