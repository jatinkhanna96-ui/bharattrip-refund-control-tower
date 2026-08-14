# Deploy to Streamlit Community Cloud

## 1. Create the GitHub repository
Create a repository named `bharattrip-refund-ai-control-tower`.
For the case-study prototype, a **private repository** is recommended if the supplied workbook is not intended for public distribution.

Upload the contents of this folder to the repository root.

## 2. Files that must be in the repository root
- `app.py`
- `requirements.txt`
- `BharatTrip_Refund_Data_final.xlsx`
- `.streamlit/config.toml`
- `README.md`

Do not upload `.streamlit/secrets.toml`.

## 3. Deploy
Open Streamlit Community Cloud and choose **Create app** → **Yup, I have an app**.

Set:
- Repository: your GitHub repository
- Branch: `main`
- Main file path: `app.py`
- App URL: `bharattrip-refund-ai-control-tower` (if available)

Click **Deploy**.

## 4. Optional AI explanation
The prototype works without an LLM: deterministic reconciliation is the source of truth.

To enable the optional AI explanation, add these secrets in Streamlit's Advanced settings:

```toml
OPENAI_API_KEY = "your-key"
OPENAI_MODEL = "your-model"
```

Never commit secrets to GitHub.

## 5. Demo flow
1. Open **Overview**.
2. Show matched / Support-only / Finance-only counts.
3. Open **Exception Queue** and filter High risk.
4. Open a flagged Refund ID in **Refund 360**.
5. Show the evidence behind the exception.
6. Generate the optional AI explanation.
7. Assign a human owner and next action.
8. Emphasise: AI detects, explains and routes; it does not approve or execute financial transactions.
