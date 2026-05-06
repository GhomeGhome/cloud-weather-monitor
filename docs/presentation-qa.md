# Presentation Q&A Prep

## Architecture questions
- Why split into `device`, `cloud_api`, and `dashboard`?
- Why does Streamlit read from BigQuery instead of direct sensor calls?
- How is reboot resilience implemented?

## Data questions
- Explain each BigQuery table and what it stores.
- Explain partitioning/clustering choices.
- How are alert thresholds computed and stored?

## Reliability questions
- What happens when internet is down?
- How do you avoid voice spam?
- How do you change Wi-Fi credentials at runtime?

## Security questions
- How are secrets managed?
- Why avoid storing API keys in git?
- Which endpoint protection is implemented for ingestion?
