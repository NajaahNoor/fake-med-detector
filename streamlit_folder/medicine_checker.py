import streamlit as st
import requests
import base64
import json
from pathlib import Path

# ─────────────────────────────────────────────
#  Page config — must be first Streamlit call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MedVerify · DRAP Checker",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Root variables ── */
:root {
    --navy:      #0B1D3A;
    --teal:      #0F7B6C;
    --teal-lt:   #12A08E;
    --cream:     #F7F4EE;
    --sand:      #EDE8DF;
    --muted:     #8A8F9C;
    --danger:    #C0392B;
    --warn:      #D4891A;
    --ok:        #1A7A4A;
    --card-bg:   #FFFFFF;
    --radius:    14px;
    --shadow:    0 4px 28px rgba(11,29,58,0.09);
}

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--cream) !important;
    color: var(--navy);
}

/* Hide default Streamlit header/footer */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; max-width: 900px; }

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, var(--navy) 0%, #173060 60%, #0F4B6E 100%);
    border-radius: var(--radius);
    padding: 3rem 3.5rem 2.8rem;
    margin-bottom: 2.5rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    width: 340px; height: 340px;
    border-radius: 50%;
    background: rgba(15,123,108,.18);
    top: -80px; right: -60px;
}
.hero::after {
    content: '';
    position: absolute;
    width: 180px; height: 180px;
    border-radius: 50%;
    background: rgba(15,123,108,.12);
    bottom: -50px; left: 60px;
}
.hero-tag {
    display: inline-block;
    background: rgba(255,255,255,.12);
    color: rgba(255,255,255,.85);
    font-size: .75rem;
    font-weight: 600;
    letter-spacing: .12em;
    text-transform: uppercase;
    padding: .3rem .85rem;
    border-radius: 99px;
    margin-bottom: 1.1rem;
}
.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.8rem;
    color: #ffffff;
    line-height: 1.15;
    margin: 0 0 .7rem;
}
.hero-title span { color: #5DD8C8; }
.hero-sub {
    color: rgba(255,255,255,.7);
    font-size: 1.05rem;
    font-weight: 300;
    max-width: 540px;
    line-height: 1.65;
    margin: 0;
}

/* ── Step pills ── */
.steps-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 2.2rem;
    flex-wrap: wrap;
}
.step-pill {
    display: flex;
    align-items: center;
    gap: .6rem;
    background: var(--card-bg);
    border: 1.5px solid var(--sand);
    border-radius: 99px;
    padding: .55rem 1.1rem;
    font-size: .85rem;
    font-weight: 500;
    color: var(--navy);
    box-shadow: 0 2px 8px rgba(11,29,58,.06);
}
.step-num {
    width: 24px; height: 24px;
    background: var(--teal);
    color: #fff;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: .72rem;
    font-weight: 700;
    flex-shrink: 0;
}

/* ── Upload card ── */
.upload-card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 2.2rem 2.5rem;
    box-shadow: var(--shadow);
    border: 1.5px solid var(--sand);
    margin-bottom: 1.5rem;
}
.card-label {
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: .6rem;
}
.card-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.35rem;
    color: var(--navy);
    margin-bottom: .4rem;
}
.card-desc {
    font-size: .9rem;
    color: var(--muted);
    margin-bottom: 1.5rem;
    line-height: 1.6;
}

/* ── Streamlit uploader override ── */
[data-testid="stFileUploader"] {
    background: var(--cream) !important;
    border: 2px dashed #C8D3E0 !important;
    border-radius: 12px !important;
    transition: border-color .2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--teal) !important;
}
[data-testid="stFileUploadDropzone"] {
    background: transparent !important;
}

/* ── Text input override ── */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    border: 1.5px solid #D5DDE8 !important;
    border-radius: 10px !important;
    background: var(--cream) !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--navy) !important;
    padding: .65rem 1rem !important;
    font-size: .95rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 3px rgba(15,123,108,.12) !important;
}

/* ── Primary button ── */
.stButton > button {
    background: linear-gradient(135deg, var(--teal) 0%, var(--teal-lt) 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: .75rem 2.2rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: .02em !important;
    cursor: pointer !important;
    transition: opacity .2s, transform .15s !important;
    box-shadow: 0 4px 16px rgba(15,123,108,.3) !important;
    width: 100% !important;
}
.stButton > button:hover {
    opacity: .9 !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ── Result cards ── */
.result-wrap {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 2rem 2.5rem;
    box-shadow: var(--shadow);
    border: 1.5px solid var(--sand);
    margin-top: 1.8rem;
}
.verdict-badge {
    display: inline-flex;
    align-items: center;
    gap: .5rem;
    padding: .45rem 1.1rem;
    border-radius: 99px;
    font-weight: 700;
    font-size: .85rem;
    letter-spacing: .06em;
    text-transform: uppercase;
    margin-bottom: 1.2rem;
}
.verdict-ok    { background: #E6F6EE; color: var(--ok); }
.verdict-warn  { background: #FEF3E2; color: var(--warn); }
.verdict-bad   { background: #FBEAEA; color: var(--danger); }

.result-summary {
    font-size: 1rem;
    color: #3A4557;
    line-height: 1.75;
    white-space: pre-wrap;
}
.divider {
    border: none;
    border-top: 1.5px solid var(--sand);
    margin: 1.5rem 0;
}

/* ── Info box ── */
.info-box {
    background: #EBF5FB;
    border-left: 4px solid #2E86C1;
    border-radius: 0 10px 10px 0;
    padding: .9rem 1.2rem;
    font-size: .88rem;
    color: #1A4A6B;
    margin-top: 1.2rem;
    line-height: 1.6;
}

/* ── Footer ── */
.footer {
    text-align: center;
    color: var(--muted);
    font-size: .82rem;
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1.5px solid var(--sand);
}
.footer a { color: var(--teal); text-decoration: none; }

/* ── Spinner label ── */
[data-testid="stSpinner"] p { font-family: 'DM Sans', sans-serif; color: var(--teal); }

/* Image preview */
.img-preview {
    border-radius: 12px;
    overflow: hidden;
    border: 1.5px solid var(--sand);
    box-shadow: 0 2px 12px rgba(11,29,58,.08);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Session state
# ─────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "verdict" not in st.session_state:
    st.session_state.verdict = None

# ─────────────────────────────────────────────
#  Hero Section
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-tag">🔬 DRAP · Pakistan Drug Authority</div>
    <h1 class="hero-title">Med<span>Verify</span></h1>
    <p class="hero-sub">
        Upload a medicine label or packaging image to instantly verify
        its DRAP registration status and detect potential counterfeits.
    </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  How it works — step pills
# ─────────────────────────────────────────────
st.markdown("""
<div class="steps-row">
    <div class="step-pill"><div class="step-num">1</div> Upload medicine image</div>
    <div class="step-pill"><div class="step-num">2</div> AI extracts registration number</div>
    <div class="step-pill"><div class="step-num">3</div> Cross-check DRAP database</div>
    <div class="step-pill"><div class="step-num">4</div> Receive verification verdict</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Upload Card
# ─────────────────────────────────────────────
st.markdown('<div class="upload-card">', unsafe_allow_html=True)

st.markdown("""
<div class="card-label">Step 1 — Upload</div>
<div class="card-title">Medicine Label / Packaging</div>
<div class="card-desc">Upload a clear photo of the medicine box, strip, or label. Supported formats: JPG, PNG, WEBP.</div>
""", unsafe_allow_html=True)

col_up, col_prev = st.columns([1.6, 1], gap="large")

with col_up:
    uploaded_file = st.file_uploader(
        "Drag & drop or click to browse",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Optional manual reg. number
    st.markdown('<div class="card-label">Optional — Manual Entry</div>', unsafe_allow_html=True)
    manual_reg = st.text_input(
        "DRAP Registration Number",
        placeholder="e.g.  023587-001  (leave blank to use OCR)",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    submit = st.button("🔍 Verify Medicine", use_container_width=True)

with col_prev:
    if uploaded_file:
        st.markdown('<div class="img-preview">', unsafe_allow_html=True)
        st.image(uploaded_file, use_container_width=True, caption="Uploaded image")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            background: var(--sand);
            border-radius: 12px;
            height: 210px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--muted);
            font-size: .9rem;
            gap: .5rem;
        ">
            <span style="font-size:2.2rem;">📷</span>
            Image preview will appear here
        </div>
        """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # close upload-card

# ─────────────────────────────────────────────
#  Backend call + result display
# ─────────────────────────────────────────────
BACKEND_URL = "http://localhost:8000/verify"   # ← change to your deployed URL

def call_backend(image_bytes: bytes, filename: str, reg_number: str = "") -> dict:
    """
    POST to the backend.
    Expected JSON response shape:
    {
        "verdict": "Verified" | "Suspicious" | "Counterfeit",
        "summary": "<plain-text explanation>",
        "reg_number": "<extracted or provided reg number>",
        "risk_score": 0-100          # optional
    }
    """
    files   = {"image": (filename, image_bytes, "image/jpeg")}
    data    = {"reg_number": reg_number}
    response = requests.post(BACKEND_URL, files=files, data=data, timeout=60)
    response.raise_for_status()
    return response.json()


if submit:
    if not uploaded_file and not manual_reg.strip():
        st.warning("⚠️  Please upload a medicine image or enter a registration number before verifying.", icon="⚠️")
    else:
        with st.spinner("Analysing medicine label — this usually takes a few seconds…"):
            try:
                if uploaded_file:
                    img_bytes = uploaded_file.read()
                    fname     = uploaded_file.name
                else:
                    img_bytes = b""
                    fname     = "none.jpg"

                result = call_backend(img_bytes, fname, manual_reg.strip())
                st.session_state.result  = result
                st.session_state.verdict = result.get("verdict", "Unknown")

            except requests.exceptions.ConnectionError:
                st.session_state.result  = {
                    "verdict": "Error",
                    "summary": (
                        "Could not reach the verification server.\n\n"
                        "Make sure your backend is running at:\n"
                        f"  {BACKEND_URL}\n\n"
                        "Update the BACKEND_URL variable in this file to match your deployment."
                    ),
                    "reg_number": manual_reg or "—",
                }
                st.session_state.verdict = "Error"
            except Exception as e:
                st.session_state.result  = {
                    "verdict": "Error",
                    "summary": f"An unexpected error occurred:\n{str(e)}",
                    "reg_number": manual_reg or "—",
                }
                st.session_state.verdict = "Error"

# ─────── Show result ───────
if st.session_state.result:
    r       = st.session_state.result
    verdict = r.get("verdict", "Unknown")
    summary = r.get("summary", "No details returned from backend.")
    reg_no  = r.get("reg_number", manual_reg or "—")

    badge_map = {
        "Verified":    ("✅", "verdict-ok",   "Verified"),
        "Suspicious":  ("⚠️", "verdict-warn", "Suspicious"),
        "Counterfeit": ("🚨", "verdict-bad",  "Counterfeit"),
        "Error":       ("❌", "verdict-bad",  "Error"),
    }
    icon, cls, label = badge_map.get(verdict, ("❓", "verdict-warn", verdict))

    st.markdown(f"""
    <div class="result-wrap">
        <div class="card-label">Verification Result</div>

        <div class="verdict-badge {cls}">{icon} &nbsp;{label}</div>

        <hr class="divider">

        <div style="margin-bottom:.5rem; font-size:.8rem; color:var(--muted); font-weight:600; letter-spacing:.08em; text-transform:uppercase;">
            Registration Number Checked
        </div>
        <div style="font-size:1.05rem; font-weight:600; color:var(--navy); margin-bottom:1.4rem; font-family:monospace;">
            {reg_no}
        </div>

        <div style="margin-bottom:.5rem; font-size:.8rem; color:var(--muted); font-weight:600; letter-spacing:.08em; text-transform:uppercase;">
            Summary
        </div>
        <div class="result-summary">{summary}</div>
    </div>
    """, unsafe_allow_html=True)

    # Advice box for flagged drugs
    if verdict == "Counterfeit":
        st.markdown("""
        <div class="info-box">
            🚨 <strong>Action Required:</strong> This medicine appears to be counterfeit or unregistered.
            Do <em>not</em> consume it. You can report it to DRAP at
            <a href="https://www.dra.gov.pk" target="_blank">dra.gov.pk</a> or call their helpline
            <strong>051-9215903</strong>.
        </div>
        """, unsafe_allow_html=True)
    elif verdict == "Suspicious":
        st.markdown("""
        <div class="info-box">
            ⚠️ <strong>Caution:</strong> Some details about this medicine could not be fully verified.
            Consider consulting a licensed pharmacist before use and report any concerns to DRAP.
        </div>
        """, unsafe_allow_html=True)

    # Download complaint draft (if backend returns one)
    if r.get("complaint_draft"):
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📄 Download DRAP Complaint Draft",
            data=r["complaint_draft"],
            file_name="DRAP_Complaint.txt",
            mime="text/plain",
            use_container_width=True,
        )

# ─────────────────────────────────────────────
#  Footer
# ─────────────────────────────────────────────
st.markdown("""
<div class="footer">
    MedVerify is a research prototype. Always consult a licensed pharmacist for medical decisions.<br>
    Data sourced from <a href="https://www.dra.gov.pk" target="_blank">DRAP · Drug Registration Database</a> &nbsp;|&nbsp;
    Built for DRAP compliance under the <em>Drugs Act 1976 &amp; DRAP Ordinance 2012</em>
</div>
""", unsafe_allow_html=True)
