import sqlite3
import json
import os
from datetime import datetime, timedelta
import random

# Absoluut pad zodat de database altijd op de juiste plek staat (ook op PythonAnywhere)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "leads.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bedrijfsnaam TEXT NOT NULL,
            website TEXT,
            sector TEXT,
            regio TEXT,
            grootte TEXT,
            bron TEXT,
            groeisignaal TEXT,
            status TEXT DEFAULT 'gevonden',
            datum_gevonden TEXT,
            laatste_actie TEXT,
            volgende_actie TEXT,
            notities TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS contactpersonen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            naam TEXT NOT NULL,
            functie TEXT,
            linkedin_url TEXT,
            email TEXT,
            telefoon TEXT,
            vertrouwen TEXT DEFAULT 'onzeker',
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS berichten (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            contactpersoon_id INTEGER,
            type TEXT NOT NULL,
            onderwerp TEXT,
            inhoud TEXT NOT NULL,
            status TEXT DEFAULT 'concept',
            datum_aangemaakt TEXT,
            datum_verstuurd TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS acties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            omschrijving TEXT,
            datum TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notificaties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            titel TEXT NOT NULL,
            bericht TEXT,
            gelezen INTEGER DEFAULT 0,
            datum TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    """)

    conn.commit()
    conn.close()

def laad_mock_data():
    conn = get_db()
    c = conn.cursor()

    # Alleen laden als DB leeg is
    c.execute("SELECT COUNT(*) FROM leads")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    mock_bedrijven = [
        {"naam": "Van der Berg Bouwgroep", "website": "vandenbergbouw.nl", "sector": "Woningbouw", "regio": "Utrecht", "grootte": "25-50 medewerkers", "bron": "LinkedIn", "signaal": "Vacature: Commercieel Directeur", "status": "heet", "dagen": 2},
        {"naam": "Heijmans Infra BV", "website": "heijmans-infra.nl", "sector": "Infra & GWW", "regio": "Noord-Brabant", "grootte": "50-100 medewerkers", "bron": "Indeed", "signaal": "Vacature: Account Manager Bouw", "status": "reactie", "dagen": 5},
        {"naam": "Dura Vermeer Projecten", "website": "duravermeer.nl", "sector": "Utiliteitsbouw", "regio": "Zuid-Holland", "grootte": "100+ medewerkers", "bron": "DuckDuckGo", "signaal": "Website: wij zoeken onderaannemers", "status": "mail_verstuurd", "dagen": 8},
        {"naam": "Strukton Rail", "website": "strukton.nl", "sector": "Infra & GWW", "regio": "Utrecht", "grootte": "50-100 medewerkers", "bron": "Bouwend Nederland", "signaal": "Nieuw project gewonnen", "status": "linkedin_verstuurd", "dagen": 10},
        {"naam": "Aannemersbedrijf Smit", "website": "smitbouw.nl", "sector": "Renovatie", "regio": "Noord-Holland", "grootte": "10-25 medewerkers", "bron": "DuckDuckGo", "signaal": "Capaciteit beschikbaar melding", "status": "berichten_klaar", "dagen": 12},
        {"naam": "Bouwbedrijf De Vries & Zn", "website": "devrieszn.nl", "sector": "Woningbouw", "regio": "Gelderland", "grootte": "10-25 medewerkers", "bron": "Indeed", "signaal": "Vacature: Salesmanager", "status": "dmu_zoeken", "dagen": 14},
        {"naam": "Trigion Bouw", "website": "trigionbouw.nl", "sector": "Utiliteitsbouw", "regio": "Overijssel", "grootte": "25-50 medewerkers", "bron": "LinkedIn", "signaal": "LinkedIn post: nieuwe vestiging geopend", "status": "gevonden", "dagen": 15},
        {"naam": "Kooyman Projectbouw", "website": "kooyman.nl", "sector": "Woningbouw", "regio": "Friesland", "grootte": "10-25 medewerkers", "bron": "Nationale Vacaturebank", "signaal": "Vacature: Inkoper", "status": "gevonden", "dagen": 16},
        {"naam": "BAM Bouw en Techniek", "website": "bam.nl", "sector": "Infra & GWW", "regio": "Noord-Holland", "grootte": "100+ medewerkers", "bron": "DuckDuckGo", "signaal": "Uitbreiding activiteiten", "status": "koud", "dagen": 30},
        {"naam": "Janssen & Slomp Installaties", "website": "janssenslomop.nl", "sector": "Installatie", "regio": "Limburg", "grootte": "25-50 medewerkers", "bron": "Uneto-VNI", "signaal": "Branchevereniging lid", "status": "koud", "dagen": 35},
        {"naam": "Vink Bouw", "website": "vinkbouw.nl", "sector": "Woningbouw", "regio": "Zuid-Holland", "grootte": "25-50 medewerkers", "bron": "Indeed", "signaal": "Vacature: Commercieel Directeur", "status": "gebeld", "dagen": 20},
        {"naam": "Rotsbouw Groep", "website": "rotsbouw.nl", "sector": "Renovatie", "regio": "Groningen", "grootte": "10-25 medewerkers", "bron": "DuckDuckGo", "signaal": "Website: wij hebben capaciteit", "status": "dmu_zoeken", "dagen": 13},
        {"naam": "Volker Wessels Bouw", "website": "volkerwessels.nl", "sector": "Utiliteitsbouw", "regio": "Utrecht", "grootte": "100+ medewerkers", "bron": "LinkedIn", "signaal": "Nieuw project aankondiging", "status": "berichten_klaar", "dagen": 11},
        {"naam": "Aannemersbedrijf Hoekstra", "website": "hoekstrabouw.nl", "sector": "Woningbouw", "regio": "Zeeland", "grootte": "10-25 medewerkers", "bron": "Bouwend Nederland", "signaal": "Branchevereniging lid", "status": "mail_verstuurd", "dagen": 7},
        {"naam": "TBI Bouw & Techniek", "website": "tbi.nl", "sector": "Installatie", "regio": "Noord-Brabant", "grootte": "50-100 medewerkers", "bron": "Indeed", "signaal": "Vacature: Account Manager", "status": "linkedin_verstuurd", "dagen": 9},
    ]

    contactpersonen_mock = [
        ("Jan van der Berg", "Directeur", "linkedin.com/in/janvanderberg", "j.vanderberg@vandenbergbouw.nl", "06-12345678", "zeker"),
        ("Mark Heijmans", "Commercieel Directeur", "linkedin.com/in/markheijmans", "m.heijmans@heijmans-infra.nl", None, "waarschijnlijk"),
        ("Sandra Dura", "Salesmanager", "linkedin.com/in/sandradura", None, None, "onzeker"),
        ("Peter Strukton", "Inkoper", "linkedin.com/in/peterstrukton", "p.strukton@strukton.nl", "06-98765432", "zeker"),
        ("Lisa Smit", "Eigenaar", "linkedin.com/in/lisasmit", "lisa@smitbouw.nl", "06-55512345", "zeker"),
        ("Tom de Vries", "Directeur", "linkedin.com/in/tomdevries", "t.devries@devrieszn.nl", None, "waarschijnlijk"),
        ("Karin Trigion", "Commercieel Directeur", "linkedin.com/in/karintrigion", None, None, "onzeker"),
        ("Henk Kooyman", "Eigenaar", "linkedin.com/in/henkkooyman", "h.kooyman@kooyman.nl", "06-44433322", "zeker"),
        ("Marieke BAM", "Salesmanager", "linkedin.com/in/mariekebam", None, None, "onzeker"),
        ("Dirk Janssen", "Directeur", "linkedin.com/in/dirkjanssen", "d.janssen@janssenslomop.nl", None, "waarschijnlijk"),
        ("Arie Vink", "Eigenaar", "linkedin.com/in/arievink", "a.vink@vinkbouw.nl", "06-11122233", "zeker"),
        ("Bert Rotsbouw", "Commercieel Directeur", "linkedin.com/in/bertrotsbouw", None, None, "onzeker"),
        ("Wim Volker", "Salesmanager", "linkedin.com/in/wimvolker", "w.volker@volkerwessels.nl", None, "waarschijnlijk"),
        ("Ans Hoekstra", "Eigenaar", "linkedin.com/in/anshoekstra", "a.hoekstra@hoekstrabouw.nl", "06-77788899", "zeker"),
        ("Theo TBI", "Inkoper", "linkedin.com/in/theotbi", None, None, "onzeker"),
    ]

    nu = datetime.now()

    for i, b in enumerate(mock_bedrijven):
        datum = (nu - timedelta(days=b["dagen"])).strftime("%Y-%m-%d %H:%M")
        volgende = _volgende_actie(b["status"])

        c.execute("""
            INSERT INTO leads (bedrijfsnaam, website, sector, regio, grootte, bron, groeisignaal, status, datum_gevonden, laatste_actie, volgende_actie)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (b["naam"], b["website"], b["sector"], b["regio"], b["grootte"], b["bron"], b["signaal"], b["status"], datum, datum, volgende))

        lead_id = c.lastrowid
        cp = contactpersonen_mock[i]
        c.execute("""
            INSERT INTO contactpersonen (lead_id, naam, functie, linkedin_url, email, telefoon, vertrouwen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (lead_id, cp[0], cp[1], cp[2], cp[3], cp[4], cp[5]))

        cp_id = c.lastrowid

        # Acties op basis van status
        acties = _genereer_acties(b["status"], datum, b["namen"] if "namen" in b else cp[0])
        for actie in acties:
            c.execute("INSERT INTO acties (lead_id, type, omschrijving, datum) VALUES (?, ?, ?, ?)",
                      (lead_id, actie[0], actie[1], actie[2]))

        # Berichten voor statussen waar ze relevant zijn
        if b["status"] in ["berichten_klaar", "linkedin_verstuurd", "mail_verstuurd", "reactie", "heet", "gebeld"]:
            c.execute("""
                INSERT INTO berichten (lead_id, contactpersoon_id, type, onderwerp, inhoud, status, datum_aangemaakt)
                VALUES (?, ?, 'linkedin', NULL, ?, 'goedgekeurd', ?)
            """, (lead_id, cp_id, f"Goedemiddag {cp[0].split()[0]}, ik zag dat {b['naam']} {b['signaal'].lower()}. Graag vertel ik meer over hoe wij hierbij kunnen helpen.", datum))

            c.execute("""
                INSERT INTO berichten (lead_id, contactpersoon_id, type, onderwerp, inhoud, status, datum_aangemaakt)
                VALUES (?, ?, 'mail', ?, ?, 'goedgekeurd', ?)
            """, (lead_id, cp_id,
                  f"Samenwerking {b['naam']} – {b['sector']}",
                  f"Beste {cp[0].split()[0]},\n\nIk neem contact met u op naar aanleiding van {b['signaal'].lower()}.\n\nOns team helpt bouwbedrijven in {b['regio']} bij het uitbreiden van hun klantenportfolio. Graag licht ik toe wat wij voor {b['naam']} kunnen betekenen.\n\nKunt u deze week 15 minuten vrijmaken voor een kort gesprek?\n\nMet vriendelijke groet",
                  datum))

        # Notificatie voor hete leads
        if b["status"] in ["heet", "reactie"]:
            c.execute("""
                INSERT INTO notificaties (lead_id, titel, bericht, gelezen, datum)
                VALUES (?, ?, ?, ?, ?)
            """, (lead_id, f"Reactie van {cp[0]} – {b['naam']}",
                  f"{cp[0]} reageerde op uw mail. Aanbeveling: bel nu.", 0, datum))

    conn.commit()
    conn.close()

def _volgende_actie(status):
    mapping = {
        "gevonden": "DMU opzoeken",
        "dmu_zoeken": "Berichten genereren",
        "berichten_klaar": "LinkedIn bericht versturen",
        "linkedin_verstuurd": "Wacht op mail versturen (morgen)",
        "mail_verstuurd": "Wacht op reactie",
        "reactie": "BELLEN",
        "heet": "BELLEN – hete lead",
        "koud": "Archiveren",
        "gebeld": "Afspraak inplannen",
    }
    return mapping.get(status, "")

def _genereer_acties(status, basis_datum, naam):
    acties = []
    basis = datetime.strptime(basis_datum, "%Y-%m-%d %H:%M")
    acties.append(("gevonden", f"Bedrijf gevonden via leadfinder", basis_datum))
    if status in ["dmu_zoeken", "berichten_klaar", "linkedin_verstuurd", "mail_verstuurd", "reactie", "heet", "gebeld"]:
        acties.append(("dmu", f"Contactpersoon gevonden: {naam}", (basis + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")))
    if status in ["berichten_klaar", "linkedin_verstuurd", "mail_verstuurd", "reactie", "heet", "gebeld"]:
        acties.append(("bericht", "LinkedIn bericht en mail gegenereerd", (basis + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")))
    if status in ["linkedin_verstuurd", "mail_verstuurd", "reactie", "heet", "gebeld"]:
        acties.append(("linkedin", "LinkedIn bericht verstuurd", (basis + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")))
    if status in ["mail_verstuurd", "reactie", "heet", "gebeld"]:
        acties.append(("mail", "Eerste mail verstuurd", (basis + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")))
    if status in ["reactie", "heet"]:
        acties.append(("reactie", f"Reactie ontvangen van {naam}", (basis + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")))
    if status == "gebeld":
        acties.append(("reactie", f"Reactie ontvangen van {naam}", (basis + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")))
        acties.append(("gebeld", "Telefoongesprek gevoerd", (basis + timedelta(days=4)).strftime("%Y-%m-%d %H:%M")))
    return acties

# Hulpfuncties voor routes
def get_alle_leads(status_filter=None, regio_filter=None, sector_filter=None):
    conn = get_db()
    c = conn.cursor()
    query = "SELECT * FROM leads WHERE 1=1"
    params = []
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if regio_filter:
        query += " AND regio = ?"
        params.append(regio_filter)
    if sector_filter:
        query += " AND sector = ?"
        params.append(sector_filter)
    query += " ORDER BY datum_gevonden DESC"
    c.execute(query, params)
    leads = [dict(r) for r in c.fetchall()]
    conn.close()
    return leads

def get_lead(lead_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    lead = dict(c.fetchone())
    c.execute("SELECT * FROM contactpersonen WHERE lead_id = ?", (lead_id,))
    lead["contactpersonen"] = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM acties WHERE lead_id = ? ORDER BY datum ASC", (lead_id,))
    lead["acties"] = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM berichten WHERE lead_id = ? ORDER BY datum_aangemaakt ASC", (lead_id,))
    lead["berichten"] = [dict(r) for r in c.fetchall()]
    conn.close()
    return lead

def get_hete_leads():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT l.*, n.titel as notif_titel, n.bericht as notif_bericht, n.datum as notif_datum, n.id as notif_id
        FROM leads l
        LEFT JOIN notificaties n ON l.id = n.lead_id AND n.gelezen = 0
        WHERE l.status IN ('heet', 'reactie')
        ORDER BY n.datum DESC
    """)
    leads = [dict(r) for r in c.fetchall()]
    conn.close()
    return leads

def get_notificaties_count():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM notificaties WHERE gelezen = 0")
    count = c.fetchone()[0]
    conn.close()
    return count

def update_lead_status(lead_id, nieuwe_status):
    conn = get_db()
    c = conn.cursor()
    nu = datetime.now().strftime("%Y-%m-%d %H:%M")
    volgende = _volgende_actie(nieuwe_status)
    c.execute("UPDATE leads SET status = ?, laatste_actie = ?, volgende_actie = ? WHERE id = ?",
              (nieuwe_status, nu, volgende, lead_id))
    c.execute("INSERT INTO acties (lead_id, type, omschrijving, datum) VALUES (?, ?, ?, ?)",
              (lead_id, nieuwe_status, f"Status gewijzigd naar: {nieuwe_status}", nu))
    conn.commit()
    conn.close()

def markeer_notificatie_gelezen(notif_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE notificaties SET gelezen = 1 WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()

def get_unieke_waarden(kolom):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"SELECT DISTINCT {kolom} FROM leads ORDER BY {kolom}")
    waarden = [r[0] for r in c.fetchall() if r[0]]
    conn.close()
    return waarden
