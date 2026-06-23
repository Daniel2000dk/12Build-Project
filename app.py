import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from database import init_db, laad_mock_data, get_alle_leads, get_lead, get_hete_leads, get_notificaties_count, update_lead_status, markeer_notificatie_gelezen, get_unieke_waarden

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-vervang-dit")

@app.context_processor
def inject_notif_count():
    return {"notif_count": get_notificaties_count()}

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

@app.route("/notificaties")
def notificaties():
    leads = get_hete_leads()
    return render_template("notificaties.html", leads=leads)

@app.route("/notificatie/<int:notif_id>/gelezen", methods=["POST"])
def markeer_gelezen(notif_id):
    markeer_notificatie_gelezen(notif_id)
    return redirect(url_for("notificaties"))

@app.route("/scanner")
def scanner():
    return render_template("scanner.html")

@app.route("/instellingen")
def instellingen():
    return render_template("instellingen.html")

@app.route("/api/leads")
def api_leads():
    leads = get_alle_leads()
    return jsonify(leads)

if __name__ == "__main__":
    init_db()
    laad_mock_data()
    app.run(debug=True, port=5000)
