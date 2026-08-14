# BharatTrip Refund AI Control Tower — Interview Demo Edition

A Streamlit prototype for the BharatTrip AI Operations Associate take-home task.

## What it demonstrates
- Reconciliation of Support and Finance refund trackers
- Explainable exception detection and prioritisation
- Refund 360 investigation view
- Informal message intake for the cases described in the brief (RF-1098 / RF-1099)
- Human-in-the-loop operating model
- A guided 90-second demo flow

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment
Deploy `app.py` from GitHub using Streamlit Community Cloud. Keep the workbook in the same repository path as `app.py`.

## AI boundary
The prototype uses deterministic reconciliation logic as its factual control layer and generates structured operational explanations from those signals. It does not approve refunds or execute payouts.
