import os
import threading
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from database import (
    init_db, laad_mock_data, init_kandidaten_tabel,
    get_alle_leads, get_lead, get_hete_leads, get_notificaties_count,
    update_lead_status, markeer_notificatie_gelezen, get_unieke_waarden,
    get_alle_kandidaten, get_kandidaten_count, sla_kandidaten_op,
    keur_kandidaat_goed, wijs_kandidaat_af, verwijder_alle_kandidaten,
    voeg_contactpersoon_toe, verwijder_automatische_contactpersonen, sla_kvk_info_op
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-vervang-dit")

# Scan status bijhouden (in-memory, verdwijnt bij herstart)
scan_status = {"actief": False, "bericht": "", "gevonden": 0}

@app.context_processor
def inject_globals():
    return {
        "notif_count": get_notificaties_count(),
        "kandidaten_count": get_kandidaten_count()
    }

# ─── Dashboard ───────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    status_filter = request.args.get("status")
    regio_filter = request.args.get("regio")
    sector_filter = request.args.get("sector")
    leads = get_alle_leads(status_filter, regio_filter, sector_filter)
    regio_opties = get_unieke_waarden("regio")
    sector_opties = get_unieke_waarden("sector")
    return render_template("index.html", leads=leads, regio_opties=regio_opties,
                           sector_opties=sector_opties, actief_status=status_filter,
                           actief_regio=regio_filter, actief_sector=sector_filter)

# ─── Lead detail ─────────────────────────────────────────────────────────────

@app.route("/lead/<int:lead_id>")
def lead_detail(lead_id):
    lead = get_lead(lead_id)
    return render_template("lead_detail.html", lead=lead)

@app.route("/lead/<int:lead_id>/status", methods=["POST"])
def wijzig_status(lead_id):
    nieuwe_status = request.form.get("status")
    if nieuwe_status:
        update_lead_status(lead_id, nieuwe_status)
    return redirect(url_for("lead_detail", lead_id=lead_id))

# ─── Notificaties ────────────────────────────────────────────────────────────

@app.route("/notificaties")
def notificaties():
    leads = get_hete_leads()
    return render_template("notificaties.html", leads=leads)

@app.route("/notificatie/<int:notif_id>/gelezen", methods=["POST"])
def markeer_gelezen(notif_id):
    markeer_notificatie_gelezen(notif_id)
    return redirect(url_for("notificaties"))

# ─── Scanner (Fase 2) ────────────────────────────────────────────────────────

@app.route("/scanner")
def scanner():
    kandidaten = get_alle_kandidaten()
    return render_template("scanner.html", kandidaten=kandidaten, scan_status=scan_status)

@app.route("/api/scanner/start", methods=["POST"])
def start_scan():
    global scan_status
    if scan_status["actief"]:
        return jsonify({"ok": False, "bericht": "Scan is al bezig"})

    max_zoekopdrachten = int(request.json.get("max_zoekopdrachten", 3))

    def voer_scan_uit():
        global scan_status
        scan_status = {"actief": True, "bericht": "Scan gestart...", "gevonden": 0}
        try:
            from modules.leadfinder import run_leadfinder
            scan_status["bericht"] = "Zoeken naar bouwbedrijven..."
            resultaten = run_leadfinder(max_zoekopdrachten=max_zoekopdrachten)
            toegevoegd = sla_kandidaten_op(resultaten)
            scan_status["gevonden"] = toegevoegd
            scan_status["bericht"] = f"Klaar – {toegevoegd} nieuwe kandidaten gevonden"
        except Exception as e:
            logger.error(f"Scan fout: {e}")
            scan_status["bericht"] = f"Fout tijdens scan: {str(e)[:100]}"
        finally:
            scan_status["actief"] = False

    t = threading.Thread(target=voer_scan_uit, daemon=True)
    t.start()
    return jsonify({"ok": True, "bericht": "Scan gestart"})

@app.route("/api/scanner/status")
def scan_status_api():
    return jsonify(scan_status)

@app.route("/api/scanner/goedkeuren/<int:kandidaat_id>", methods=["POST"])
def goedkeuren(kandidaat_id):
    lead_id = keur_kandidaat_goed(kandidaat_id)
    if lead_id:
        return jsonify({"ok": True, "lead_id": lead_id})
    return jsonify({"ok": False}), 404

@app.route("/api/scanner/afwijzen/<int:kandidaat_id>", methods=["POST"])
def afwijzen(kandidaat_id):
    wijs_kandidaat_af(kandidaat_id)
    return jsonify({"ok": True})

@app.route("/api/scanner/alles-afwijzen", methods=["POST"])
def alles_afwijzen():
    verwijder_alle_kandidaten()
    return jsonify({"ok": True})

# ─── DMU Finder (Fase 3) ─────────────────────────────────────────────────────

dmu_status = {}

@app.route("/api/dmu/zoek/<int:lead_id>", methods=["POST"])
def start_dmu(lead_id):
    global dmu_status
    if dmu_status.get(lead_id, {}).get("actief"):
        return jsonify({"ok": False, "bericht": "DMU scan al bezig"})

    lead = get_lead(lead_id)
    if not lead:
        return jsonify({"ok": False}), 404

    dmu_status[lead_id] = {"actief": True, "bericht": "Zoeken...", "contacten": [], "kvk_info": {}, "linkedin_bedrijf_url": ""}

    def zoek_dmu():
        try:
            from modules.dmu_finder import run_dmu_finder
            dmu_status[lead_id]["bericht"] = "Website scrapen..."
            resultaat = run_dmu_finder(lead["bedrijfsnaam"], lead.get("website", ""))

            # Bestaande automatische contacten verwijderen en nieuwe opslaan
            verwijder_automatische_contactpersonen(lead_id)
            for c in resultaat["contacten"]:
                voeg_contactpersoon_toe(
                    lead_id,
                    naam=c["naam"],
                    functie=c.get("functie", ""),
                    linkedin_url=c.get("linkedin_zoek_url", ""),
                    email=c.get("email", ""),
                    vertrouwen=c.get("vertrouwen", "onzeker"),
                    bron=c.get("bron", "website")
                )

            # KVK info opslaan
            if resultaat.get("kvk_info"):
                sla_kvk_info_op(lead_id, resultaat["kvk_info"])

            # Status updaten naar dmu_zoeken
            update_lead_status(lead_id, "dmu_zoeken")

            dmu_status[lead_id].update({
                "actief": False,
                "bericht": f"{len(resultaat['contacten'])} contacten gevonden",
                "contacten": resultaat["contacten"],
                "kvk_info": resultaat.get("kvk_info", {}),
                "linkedin_bedrijf_url": resultaat.get("linkedin_bedrijf_url", ""),
            })
        except Exception as e:
            logger.error(f"DMU fout voor lead {lead_id}: {e}")
            dmu_status[lead_id] = {"actief": False, "bericht": f"Fout: {str(e)[:100]}", "contacten": [], "kvk_info": {}, "linkedin_bedrijf_url": ""}

    t = threading.Thread(target=zoek_dmu, daemon=True)
    t.start()
    return jsonify({"ok": True})

@app.route("/api/dmu/status/<int:lead_id>")
def dmu_status_api(lead_id):
    return jsonify(dmu_status.get(lead_id, {"actief": False, "bericht": "", "contacten": []}))

@app.route("/api/contact/toevoegen", methods=["POST"])
def contact_toevoegen():
    data = request.json
    lead_id = data.get("lead_id")
    naam = data.get("naam", "").strip()
    if not lead_id or not naam:
        return jsonify({"ok": False, "bericht": "Naam en lead_id zijn verplicht"}), 400
    voeg_contactpersoon_toe(
        lead_id=lead_id,
        naam=naam,
        functie=data.get("functie", ""),
        linkedin_url=data.get("linkedin_url", ""),
        email=data.get("email", ""),
        telefoon=data.get("telefoon", ""),
        vertrouwen=data.get("vertrouwen", "waarschijnlijk"),
        bron="handmatig"
    )
    update_lead_status(lead_id, "dmu_zoeken")
    return jsonify({"ok": True})

# ─── Instellingen ────────────────────────────────────────────────────────────

@app.route("/instellingen")
def instellingen():
    gmail_ok = bool(os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD"))
    anthropic_ok = bool(os.getenv("ANTHROPIC_API_KEY"))
    return render_template("instellingen.html", gmail_ok=gmail_ok, anthropic_ok=anthropic_ok)

# ─── API ─────────────────────────────────────────────────────────────────────

@app.route("/api/leads")
def api_leads():
    leads = get_alle_leads()
    return jsonify(leads)

if __name__ == "__main__":
    init_db()
    init_kandidaten_tabel()
    laad_mock_data()
    app.run(debug=True, port=5000)
