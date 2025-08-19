import io
import base64
import streamlit as st
import pandas as pd

st.set_page_config(page_title="PV-Aufgabenplaner • v2", layout="wide")

# ==============================
# Branding (Logo + Farben)
# ==============================
with st.sidebar:
    st.image("assets/qrauts_logo.png", caption="Brand/Logo (änderbar)", use_column_width=True)
    st.write("**Branding**")
    primary = st.text_input("Primärfarbe (HEX)", value="#0F6FFF")
    accent = st.text_input("Akzentfarbe (HEX)", value="#111827")

    css = f"""
    <style>
    :root {{
        --primary: {primary};
        --accent: {accent};
    }}
    .stButton>button {{
        border-radius: 6px;
        border: 1px solid var(--primary);
        color: white !important;
        background: var(--primary);
    }}
    .stDownloadButton>button {{
        border-radius: 6px;
        border: 1px solid var(--accent);
        color: white !important;
        background: var(--accent);
    }}
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        border-bottom: 3px solid var(--primary);
    }}
    h1, h2, h3 {{ color: var(--accent); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    uploaded_logo = st.file_uploader("Eigenes Logo hochladen (PNG)", type=["png"])
    if uploaded_logo is not None:
        # Persist hochgeladenes Logo unter gleichem Pfad
        with open("assets/qrauts_logo.png", "wb") as f:
            f.write(uploaded_logo.read())
        st.rerun()

st.title("PV-Aufgabenplaner • Stromverkauf an Dritte (v2)")
st.caption(
    "Filtert RACI-Aufgaben abhängig von **Anlagengröße**, **Betreibermodell** und **Mess-/Steuerkonzept**. "
    "Optional: Excel-Upload zur Erweiterung/Überschreibung."
)

# ==============================
# Basis-Aufgaben (inkl. §14a/WP)
# ==============================
BASE_TASKS = [
    # Rechtlich & regulatorisch
    {"Aufgabe":"Gewerbeanmeldung / Unternehmensform prüfen","Kategorie":"Rechtlich","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Steuerberater","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Anmeldung im Marktstammdatenregister (BNetzA)","Kategorie":"Rechtlich","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Netzbetreiber","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Anmeldung beim Netzbetreiber (Inbetriebnahme, Lieferbeziehungen)","Kategorie":"Rechtlich","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Netzbetreiber","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Prüfung EEG/EnWG-Einordnung (Eigenversorgung, gGV, Mieterstrom, Direktlieferung, Kundenanlage)","Kategorie":"Rechtlich","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Jurist/Consultant","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Lieferantenrahmenvertrag mit Netzbetreiber (bei Netzdurchleitung)","Kategorie":"Rechtlich","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Netzbetreiber","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},

    # Steuern & Abgaben
    {"Aufgabe":"Umsatzsteuerliche Behandlung klären (Regelbesteuerung, Rechnungsstellung)","Kategorie":"Steuern","Pflicht/Optional":"Pflicht","R":"Steuerberater","ACI":"Eigentümer","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Einkommen-/Körperschaftsteuer & Gewerbesteuer berücksichtigen","Kategorie":"Steuern","Pflicht/Optional":"Pflicht","R":"Steuerberater","ACI":"Eigentümer","Zeitachse":"Jährlich","Priorität":"Hoch"},
    {"Aufgabe":"Stromsteuer: Registrierung/Anmeldung beim Hauptzollamt (bei Lieferung an Dritte)","Kategorie":"Steuern","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Steuerberater","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"EEG-Umlage-/Besonderheiten bei Lieferung an Dritte prüfen","Kategorie":"Steuern","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Steuerberater","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},

    # Vertraglich
    {"Aufgabe":"Stromlieferverträge mit Abnehmern (Mieter/Kunden) erstellen","Kategorie":"Vertraglich","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Jurist","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"AGB/Transparenzpflichten prüfen (z. B. StromGVV-Bezug)","Kategorie":"Vertraglich","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Jurist","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Datenschutz (DSGVO) für Mess-/Abrechnungsdaten sicherstellen","Kategorie":"Vertraglich","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"DSB","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},

    # Technisch / Messung / Steuerung
    {"Aufgabe":"Messkonzept erstellen (Summenzähler, Untermessung, Drittmengenabgrenzung)","Kategorie":"Technisch","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Messstellenbetreiber","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Installation von Zählern / iMSys (Pflichtfälle beachten)","Kategorie":"Technisch","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Messstellenbetreiber","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Registrierende Lastgangmessung (RLM) bei Pflichtfällen","Kategorie":"Technisch","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Messstellenbetreiber","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Netzanschluss-/Einspeisekonzept abstimmen","Kategorie":"Technisch","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Netzbetreiber","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"Redispatch 2.0 umsetzen (i. d. R. ab ≥100 kW installierte Leistung)","Kategorie":"Technisch","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Direktvermarkter/EVU","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},

    # §14a / Wärmepumpe
    {"Aufgabe":"§14a-Teilnahme prüfen und steuern (steuerbare Verbrauchseinrichtungen)","Kategorie":"Technisch","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Netzbetreiber/MSB","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},
    {"Aufgabe":"WP-Tarif-/Steuerkonzept (Wärmepumpe) definieren und vertraglich abbilden","Kategorie":"Vertraglich","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"EVU/Jurist","Zeitachse":"Vor Inbetriebnahme","Priorität":"Hoch"},

    # Abrechnung & Verwaltung
    {"Aufgabe":"Verbrauchserfassung & Abrechnung (inkl. Drittmengenabgrenzung)","Kategorie":"Verwaltung","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Dienstleister","Zeitachse":"Laufender Betrieb","Priorität":"Mittel"},
    {"Aufgabe":"Rechnungsstellung (mit USt) an Abnehmer","Kategorie":"Verwaltung","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Steuerberater","Zeitachse":"Laufender Betrieb","Priorität":"Mittel"},
    {"Aufgabe":"EEG-/Energiemengenmeldungen an Netzbetreiber","Kategorie":"Verwaltung","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Netzbetreiber","Zeitachse":"Jährlich","Priorität":"Mittel"},
    {"Aufgabe":"Jahresmeldungen beim Hauptzollamt (Stromsteuer, falls relevant)","Kategorie":"Verwaltung","Pflicht/Optional":"Pflicht","R":"Eigentümer","ACI":"Steuerberater","Zeitachse":"Jährlich","Priorität":"Mittel"},

    # Strategisch/Optional
    {"Aufgabe":"Bilanzkreis-/Direktvermarktungs-/Abrechnungsdienstleister beauftragen","Kategorie":"Strategisch","Pflicht/Optional":"Optional","R":"Eigentümer","ACI":"Dienstleister","Zeitachse":"Vor Inbetriebnahme","Priorität":"Niedrig"},
    {"Aufgabe":"Mieterstromförderung prüfen (falls Mieterstrommodell)","Kategorie":"Strategisch","Pflicht/Optional":"Optional","R":"Eigentümer","ACI":"Steuerberater","Zeitachse":"Vor Inbetriebnahme","Priorität":"Niedrig"},
    {"Aufgabe":"Versicherung (Ertragsausfall/Haftpflicht) optimieren","Kategorie":"Strategisch","Pflicht/Optional":"Optional","R":"Eigentümer","ACI":"Versicherung","Zeitachse":"Vor Inbetriebnahme","Priorität":"Niedrig"},
    {"Aufgabe":"IT-/Plattformlösung für Abrechnung & Portale","Kategorie":"Strategisch","Pflicht/Optional":"Optional","R":"Eigentümer","ACI":"IT-Dienstleister","Zeitachse":"Vor Inbetriebnahme","Priorität":"Niedrig"},
]

MODELS = [
    "Gemeinschaftliche Gebäudeversorgung (gGV)",
    "Mieterstrom",
    "Direktlieferung an Dritte (Netzdurchleitung)",
    "Kundenanlage / geschlossenes Verteilernetz",
    "PV + Wärmepumpe (§14a)"
]

MESSKONZEPTE = [
    "Summenzählerkonzept",
    "Untermessung (Drittmengenabgrenzung)",
    "iMSys (Smart Meter)",
    "RLM (Lastgangmessung)",
    "§14a-Management"
]

# ==============================
# Excel-Upload & Zusammenführen
# ==============================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "aufgabe": "Aufgabe",
        "kategorie": "Kategorie",
        "pflicht/optional": "Pflicht/Optional",
        "verantwortlich (r)": "R",
        "r": "R",
        "unterstützung (a/c/i)": "ACI",
        "aci": "ACI",
        "priorität": "Priorität",
        "zeitachse": "Zeitachse",
        "begründung": "Begründung",
    }
    cols = {}
    for c in df.columns:
        key = c.strip().lower()
        cols[c] = mapping.get(key, c)
    return df.rename(columns=cols)

uploaded_df = None
with st.expander("🔼 Optional: Eigene Excel-Aufgabenmatrix hochladen (wird mit Basisdaten zusammengeführt)"):
    file = st.file_uploader("Excel (*.xlsx)", type=["xlsx"])
    if file is not None:
        try:
            tmp = pd.read_excel(file)
            tmp = normalize_columns(tmp)
            required = {"Aufgabe", "Kategorie", "Pflicht/Optional", "R", "ACI"}
            missing = required - set(tmp.columns)
            if missing:
                st.error(f"Fehlende Spalten in Upload: {', '.join(sorted(missing))}")
            else:
                uploaded_df = tmp
                st.success(f"Upload gelesen: {tmp.shape[0]} Zeilen.")
                st.dataframe(tmp.head(20), use_container_width=True)
        except Exception as e:
            st.error(f"Fehler beim Lesen: {e}")

# ==============================
# Regel-Engine
# ==============================
def apply_rules(df: pd.DataFrame, size_kwp: int, model: str, messkonzepte: list, nur_pflicht: bool) -> pd.DataFrame:
    df = df.copy()
    if "Begründung" not in df.columns:
        df["Begründung"] = ""
    df["Gilt"] = False

    for idx, row in df.iterrows():
        reason = []
        applies = False

        # Grundpflichten
        if row.get("Kategorie") in ["Rechtlich", "Vertraglich", "Technisch", "Steuern", "Verwaltung"]:
            applies = True
            reason.append("Grundpflichten bei Lieferung an Dritte")

        # Modellabhängig
        aufgabe = str(row.get("Aufgabe", ""))
        if model == "Mieterstrom":
            if "Mieterstrom" in aufgabe:
                applies = True; reason.append("Spezifisch für Mieterstrom")
            if "Lieferantenrahmenvertrag" in aufgabe:
                applies = False; reason.append("Kein Lieferantenrahmenvertrag bei reinem Mieterstrom üblich")
        elif model == "Gemeinschaftliche Gebäudeversorgung (gGV)":
            if "Messkonzept" in aufgabe or "Drittmengenabgrenzung" in aufgabe:
                applies = True; reason.append("gGV erfordert sauberes Mess-/Abgrenzkonzept")
            if "Lieferantenrahmenvertrag" in aufgabe:
                applies = False; reason.append("gGV: i. d. R. keine Netzdurchleitung")
        elif model == "Direktlieferung an Dritte (Netzdurchleitung)":
            if "Lieferantenrahmenvertrag" in aufgabe:
                applies = True; reason.append("Netzdurchleitung erfordert Lieferantenrahmenvertrag")
        elif model == "Kundenanlage / geschlossenes Verteilernetz":
            if "Prüfung EEG/EnWG" in aufgabe:
                applies = True; reason.append("Kundenanlage/GV: EnWG-Abgrenzung zwingend")
        elif model == "PV + Wärmepumpe (§14a)":
            if ("§14a" in aufgabe) or ("WP-" in aufgabe) or ("Wärmepumpe" in aufgabe):
                applies = True; reason.append("§14a-/WP-spezifische Aufgabe")

        # Mess-/Steuerkonzepte
        joined = " ".join(messkonzepte)
        if "iMSys" in joined and "iMSys" in aufgabe:
            applies = True; reason.append("iMSys ausgewählt")
        if "RLM (Lastgangmessung)" in messkonzepte and ("RLM" in aufgabe or "Lastgang" in aufgabe):
            applies = True; reason.append("RLM ausgewählt")
        if "§14a-Management" in messkonzepte and "§14a" in aufgabe:
            applies = True; reason.append("§14a-Management ausgewählt")
        if any(k in joined for k in ["Summenzählerkonzept", "Untermessung (Drittmengenabgrenzung)"]):
            if "Messkonzept" in aufgabe or "Drittmengenabgrenzung" in aufgabe:
                applies = True; reason.append("Messkonzept ausgewählt")

        # Schwellen (Heuristik)
        if size_kwp >= 100:
            if "Redispatch 2.0" in aufgabe:
                applies = True; reason.append("≥100 kWp → Redispatch 2.0 wahrscheinlich")
        else:
            if "Redispatch 2.0" in aufgabe:
                applies = False; reason.append("<100 kWp → Redispatch i. d. R. nicht erforderlich")

        # Pflichtfilter
        if nur_pflicht and str(row.get("Pflicht/Optional", "")).strip() != "Pflicht":
            applies = False; reason.append("Nur Pflichtaufgaben gefiltert")

        df.at[idx, "Gilt"] = applies
        # De-duplicate reasons (stabile Reihenfolge)
        df.at[idx, "Begründung"] = "; ".join(dict.fromkeys(reason))

    return df[df["Gilt"]].drop(columns=["Gilt"])

# ==============================
# Parameter (Sidebar)
# ==============================
with st.sidebar:
    st.markdown("---")
    st.header("Parameter")
    size_kwp = st.number_input("Anlagengröße (kWp)", min_value=1, max_value=20000, value=120, step=1)
    model = st.selectbox("Betreibermodell", MODELS, index=0)
    messkonzepte = st.multiselect("Mess-/Steuerkonzept(e)", MESSKONZEPTE, default=["Summenzählerkonzept","Untermessung (Drittmengenabgrenzung)"])
    nur_pflicht = st.checkbox("Nur Pflichtaufgaben anzeigen", value=True)

# ==============================
# Datenbasis zusammenführen
# ==============================
base_df = pd.DataFrame(BASE_TASKS)
if uploaded_df is not None:
    merged = pd.concat([uploaded_df, base_df], ignore_index=True)

    # Sicherstellen, dass optionale Spalten existieren
    for col in ["Begründung", "Priorität", "Zeitachse"]:
        if col not in merged.columns:
            merged[col] = ""

    # Deduplizieren nach Aufgabe – Upload hat Vorrang
    merged = merged.sort_values(by=["Aufgabe"]).drop_duplicates(subset=["Aufgabe"], keep="first").reset_index(drop=True)
    tasks_df = merged
else:
    tasks_df = base_df

filtered = apply_rules(tasks_df, size_kwp, model, messkonzepte, nur_pflicht)

# Spaltenreihenfolge
cols = ["Aufgabe","Kategorie","Pflicht/Optional","Priorität","Zeitachse","R","ACI","Begründung"]
filtered = filtered[[c for c in cols if c in filtered.columns]]

# ==============================
# Anzeige + Export
# ==============================
st.subheader("Gefilterte Aufgaben")
st.dataframe(filtered, use_container_width=True, height=420)

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Aufgaben")
    return output.getvalue()

col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "Export als Excel",
        data=to_excel_bytes(filtered),
        file_name=f"PV_Aufgaben_{size_kwp}kWp_{model.replace(' ','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
with col2:
    st.download_button(
        "Export als CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name=f"PV_Aufgaben_{size_kwp}kWp_{model.replace(' ','_')}.csv",
        mime="text/csv"
    )

st.markdown("---")
with st.expander("ℹ️ Regel-Logik (Kurzüberblick)"):
    st.write("""
    **Modell-Logik:**
    - *Mieterstrom:* Mieterstrom-spezifische Aufgaben; i. d. R. **kein** Lieferantenrahmenvertrag.
    - *gGV:* Fokus auf Mess-/Drittmengenabgrenzung.
    - *Direktlieferung (Netzdurchleitung):* Lieferantenrahmenvertrag **erforderlich**.
    - *Kundenanlage/GV:* EnWG-Einordnung besonders zu prüfen.
    - *PV + Wärmepumpe (§14a):* §14a-/WP-spezifische Aufgaben greifen.

    **Schwellen/Heuristiken:**
    - Redispatch 2.0 **ab ca. ≥100 kWp** (vorab mit NB/DV klären).
    - iMSys, RLM, §14a je nach Auswahl.
    """)
