# BharatTrip Refund AI Control Tower

A working prototype for the BharatTrip AI Operations Associate case.

## What it does

1. Loads the supplied Support Tracker, Finance Tracker and Escalations tabs.
2. Normalises Refund IDs and dates.
3. Reconciles Support vs Finance.
4. Detects:
   - Support-only records
   - Finance-only records
   - Support Closed + Finance Pending Payout conflicts
   - amount variance > INR 100
   - duplicate Support IDs
   - duplicate Finance IDs
   - open escalations
5. Classifies records as High / Medium / Low risk.
6. Produces an evidence-backed finding and recommended human action.
7. Provides a Refund 360 view.
8. Optionally uses an OpenAI model to turn the structured finding into a short natural-language explanation. The LLM is explanatory only and never approves or executes a financial transaction.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser.

## Optional AI explanation

Set:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

Then restart Streamlit. The "Generate AI explanation" button will use the configured model.

If no key/model is configured, the core reconciliation still works. This makes the prototype deterministic, auditable and demoable without an API key.

## Suggested demo

1. Overview → show matched / one-sided / high-risk counts.
2. Exception Queue → filter High risk.
3. Refund 360 → open a flagged Refund ID.
4. Show the evidence and recommended action.
5. Generate the optional AI explanation.
6. Assign a human owner / next action.
7. Explain that AI flags and routes exceptions; humans retain financial judgement.

## Important design choice

The prototype deliberately does NOT automate refund approval or payout execution. That is the human control boundary.
