import os
import re
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title='BharatTrip | Refund AI Control Tower', page_icon='✦', layout='wide', initial_sidebar_state='expanded')

# -------------------- Styling --------------------
st.markdown('''
<style>
:root { --bg:#0b111e; --panel:#141d2f; --panel2:#192439; --text:#f5f8fc; --muted:#a6b5c9; --cyan:#30cdff; --purple:#9768ff; --green:#41d89d; --red:#ff697d; --amber:#ffc153; }
.stApp { background:var(--bg); color:var(--text); }
[data-testid="stSidebar"] { background:#101827; border-right:1px solid #26344d; }
[data-testid="stSidebar"] * { color:var(--text); }
.block-container { padding-top:1.2rem; padding-bottom:2rem; max-width:1450px; }
.hero { background:linear-gradient(135deg,#121d31 0%,#0f1727 60%,#15152c 100%); border:1px solid #2a3a55; border-radius:18px; padding:26px 30px; margin-bottom:18px; }
.eyebrow { color:var(--cyan); font-size:12px; font-weight:800; letter-spacing:.14em; }
.hero h1 { margin:.35rem 0 .4rem; font-size:36px; letter-spacing:-.03em; }
.hero p { color:var(--muted); margin:0; font-size:15px; }
.metric { background:var(--panel); border:1px solid #293954; border-radius:15px; padding:18px 20px; min-height:120px; }
.metric .value { font-size:31px; font-weight:800; margin-top:6px; }
.metric .label { color:var(--muted); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
.metric .sub { color:var(--muted); font-size:11px; margin-top:6px; }
.card { background:var(--panel); border:1px solid #293954; border-radius:15px; padding:18px 20px; }
.card2 { background:var(--panel2); border:1px solid #30425f; border-radius:15px; padding:18px 20px; }
.section-title { font-size:18px; font-weight:800; margin-bottom:3px; }
.section-sub { color:var(--muted); font-size:12px; margin-bottom:14px; }
.badge { display:inline-block; padding:4px 9px; border-radius:999px; font-size:11px; font-weight:800; margin-right:5px; }
.high { background:#4a1f2b; color:#ff9aaa; } .medium { background:#493916; color:#ffd889; } .low { background:#143b30; color:#83edc1; }
.flow { display:flex; align-items:center; gap:8px; margin-top:12px; flex-wrap:wrap; }
.flowbox { background:#111b2c; border:1px solid #2d405e; padding:11px 15px; border-radius:10px; font-size:12px; font-weight:700; }
.arrow { color:#6d809d; font-size:18px; }
.insight { border-left:4px solid var(--cyan); background:#111b2c; padding:14px 16px; border-radius:0 10px 10px 0; }
.insight strong { color:var(--text); }
.small { color:var(--muted); font-size:11px; }
hr { border-color:#26344d; }
.stButton > button { border-radius:9px; font-weight:700; }
div[data-testid="stDataFrame"] { border:1px solid #293954; border-radius:12px; overflow:hidden; }
</style>
''', unsafe_allow_html=True)

DATA_CANDIDATES = [
    Path('BharatTrip_Refund_Data_final.xlsx'),
    Path('BharatTrip_Refund_Data_final(1).xlsx'),
    Path('/mnt/data/BharatTrip_Refund_Data_final.xlsx'),
]

@st.cache_data(show_spinner=False)
def load_data(path_str):
    p = Path(path_str)
    support = pd.read_excel(p, sheet_name='Support_Tracker')
    finance = pd.read_excel(p, sheet_name='Finance_Tracker')
    escal = pd.read_excel(p, sheet_name='Escalations')
    for df, col in [(support,'Ticket ID'),(finance,'Ref No'),(escal,'Related Ticket / Ref')]:
        df['id'] = df[col].astype(str).str.strip().str.upper()
    support['Status'] = support['Status'].astype(str).str.strip()
    finance['Payout Status'] = finance['Payout Status'].astype(str).str.strip()
    escal['Status'] = escal['Status'].astype(str).str.strip()
    return support, finance, escal

DATA_PATH = next((p for p in DATA_CANDIDATES if p.exists()), None)
if DATA_PATH is None:
    st.error('Data file not found. Put BharatTrip_Refund_Data_final.xlsx beside app.py.')
    st.stop()

support, finance, escal = load_data(str(DATA_PATH))

# -------------------- Reconciliation engine --------------------
support_dup_ids = set(support.loc[support['id'].duplicated(False), 'id'])
finance_dup_ids = set(finance.loc[finance['id'].duplicated(False), 'id'])

sup = support.groupby('id').agg(
    agent=('Agent','first'), route=('Route','first'), support_amount=('Refund Amount (INR)','sum'),
    request_date=('Request Date','min'), last_updated=('Last Updated','max'),
    support_status=('Status', lambda x:' | '.join(sorted(set(x.dropna().astype(str))))),
    handled_by=('Handled By','first'), channel=('Channel','first'), notes=('Notes', lambda x:' | '.join(x.dropna().astype(str)))
).reset_index()
fin = finance.groupby('id').agg(
    finance_agent=('Agent Name','first'), sector=('Sector','first'), amount_paid=('Amount Paid (INR)','sum'),
    deduction=('Deduction (INR)','sum'), received_on=('Received On','min'), processed_on=('Processed On','max'),
    finance_status=('Payout Status', lambda x:' | '.join(sorted(set(x.dropna().astype(str))))),
    approved_by=('Approved By','first'), remarks=('Remarks', lambda x:' | '.join(x.dropna().astype(str)))
).reset_index()
esc = escal.groupby('id').agg(
    escalation_count=('id','size'), open_escalations=('Status', lambda x:(x=='Open').sum()),
    max_days_open=('Days Open','max'), latest_complaint=('Complaint','last')
).reset_index()

recon = sup.merge(fin, on='id', how='outer').merge(esc, on='id', how='left')
for c in ['escalation_count','open_escalations','max_days_open']:
    recon[c] = recon[c].fillna(0)


def flags_for(row):
    flags=[]
    ss=str(row.get('support_status','')); fs=str(row.get('finance_status',''))
    sa=row.get('support_amount'); pa=row.get('amount_paid')
    if pd.notna(sa) and pd.notna(pa) and abs(float(sa)-float(pa))>1: flags.append('Amount mismatch')
    if pd.notna(sa) and pd.isna(row.get('finance_status')): flags.append('Missing in Finance')
    if pd.isna(sa) and pd.notna(row.get('finance_status')): flags.append('Missing in Support')
    if 'Closed' in ss and 'Pending Payout' in fs: flags.append('Closed but unpaid')
    if 'Closed' in ss and 'Declined' in fs: flags.append('Closed but declined')
    if row['id'] in support_dup_ids: flags.append('Duplicate Support')
    if row['id'] in finance_dup_ids: flags.append('Duplicate Finance')
    if row['open_escalations'] > 0: flags.append('Open escalation')
    return flags

recon['flags'] = recon.apply(flags_for, axis=1)
recon['exception'] = recon['flags'].apply(bool)

def priority(row):
    f=row['flags']
    score=0
    if 'Closed but unpaid' in f: score+=5
    if 'Closed but declined' in f: score+=5
    if 'Open escalation' in f: score+=3
    if 'Missing in Finance' in f: score+=3
    if 'Amount mismatch' in f: score+=3
    if 'Missing in Support' in f: score+=2
    if 'Duplicate Support' in f or 'Duplicate Finance' in f: score+=1
    if row['max_days_open'] >= 30: score+=2
    if score>=6: return 'HIGH'
    if score>=3: return 'MEDIUM'
    return 'LOW'

recon['priority'] = recon.apply(priority, axis=1)


def owner(row):
    f=row['flags']
    if any(x in f for x in ['Closed but unpaid','Missing in Finance','Closed but declined','Amount mismatch']): return 'Finance'
    if 'Missing in Support' in f: return 'Support'
    if 'Open escalation' in f: return 'Support'
    return 'Operations'
recon['owner'] = recon.apply(owner, axis=1)


def action(row):
    f=row['flags']
    if 'Closed but unpaid' in f: return 'Finance: verify payout before closure'
    if 'Closed but declined' in f: return 'Support + Finance: validate eligibility and closure'
    if 'Missing in Finance' in f: return 'Finance: locate or create matching payout record'
    if 'Missing in Support' in f: return 'Support: create / link the refund record'
    if 'Amount mismatch' in f: return 'Finance: reconcile refund amount and deduction'
    if 'Duplicate Support' in f or 'Duplicate Finance' in f: return 'Operations: merge duplicate records'
    if 'Open escalation' in f: return 'Support: update owner and next action'
    return 'Review'
recon['action'] = recon.apply(action, axis=1)

# -------------------- AI-style explanation --------------------
def explain(row):
    f=row['flags']
    if not f:
        return ('No material exception detected', 'Support and Finance records are aligned and there is no open escalation attached to this refund.', 'No action required unless new evidence arrives.')
    if 'Closed but unpaid' in f:
        return ('Status conflict: closed but payout not confirmed', 'Support shows the refund as closed while Finance shows a pending payout. This can make the customer-facing status appear complete before money is actually paid.', 'Route to Finance, confirm payout status, update the shared record, then close the case.')
    if 'Missing in Finance' in f:
        return ('Handoff gap: refund exists in Support but not Finance', 'The refund cannot be reliably traced into the payout process from the Finance tracker.', 'Finance should locate or create the matching record and confirm receipt.')
    if 'Amount mismatch' in f:
        return ('Amount mismatch detected', 'The Support refund amount and Finance paid amount differ beyond the matching tolerance.', 'Finance should reconcile the refund amount and deduction before closure.')
    if 'Open escalation' in f:
        return ('Open customer/agent escalation', 'The refund has an unresolved escalation and therefore needs an explicit owner and next action.', 'Keep the escalation open until the next action is completed and documented.')
    return ('Data quality exception', 'The records contain a reconciliation or duplication issue that reduces confidence in the refund status.', 'Assign an owner to clean the record before closure.')

# -------------------- Sidebar navigation --------------------
st.sidebar.markdown('<div class="eyebrow">BHARATTRIP</div>', unsafe_allow_html=True)
st.sidebar.markdown('### Refund AI Control Tower')
st.sidebar.caption('AI-assisted reconciliation and exception management')
page = st.sidebar.radio('NAVIGATION', ['Overview','Exception Queue','Refund 360','Message Intake','Reconciliation','Demo'])
st.sidebar.divider()
st.sidebar.markdown('**SYSTEM**')
st.sidebar.caption(f'Data source: {DATA_PATH.name}')
st.sidebar.caption(f'Records: {len(support):,} Support · {len(finance):,} Finance · {len(escal):,} Escalations')
st.sidebar.caption('Snapshot: 30 June 2026')

# -------------------- Header --------------------
st.markdown('''<div class="hero"><div class="eyebrow">AI OPERATIONS ASSOCIATE · REFUND CONTROL</div><h1>BharatTrip Refund AI Control Tower</h1><p>One refund → one record → one owner → one status. The prototype reconciles Support and Finance, surfaces exceptions, and keeps human judgement in the loop.</p></div>''', unsafe_allow_html=True)

# -------------------- Overview --------------------
if page == 'Overview':
    matched = len(set(support.id) & set(finance.id)); support_only=len(set(support.id)-set(finance.id)); finance_only=len(set(finance.id)-set(support.id))
    exceptions=int(recon.exception.sum()); open_esc=int((escal.Status=='Open').sum()); rate=exceptions/max(len(support),1)*100
    cols=st.columns(5)
    metrics=[('755','REFUND REQUESTS','Support tracker'),(str(open_esc),'OPEN ESCALATIONS',f'{len(escal)} total'),(str(exceptions),'AI EXCEPTIONS',f'{rate:.1f}% of Support'),(str(matched),'MATCHED IDS','Support ↔ Finance'),(str(support_only+finance_only),'ONE-SIDED IDS','Records needing trace')]
    for c,(v,l,sub) in zip(cols,metrics):
        c.markdown(f'<div class="metric"><div class="label">{l}</div><div class="value">{v}</div><div class="sub">{sub}</div></div>',unsafe_allow_html=True)
    st.write('')
    left,right=st.columns([1.2,1])
    with left:
        st.markdown('<div class="card"><div class="section-title">Exception queue</div><div class="section-sub">Highest-priority records surfaced by the reconciliation engine.</div></div>',unsafe_allow_html=True)
        view=recon[recon.exception].copy().sort_values(['priority','open_escalations','max_days_open'],key=lambda s:s.map({'HIGH':0,'MEDIUM':1,'LOW':2}) if s.name=='priority' else s, ascending=True).head(8)
        disp=view[['priority','id','agent','flags','owner']].copy()
        disp['flags']=disp['flags'].apply(lambda x:', '.join(x))
        disp.columns=['Priority','Refund ID','Agent','AI Finding','Owner']
        st.dataframe(disp, use_container_width=True, hide_index=True)
    with right:
        st.markdown('<div class="card"><div class="section-title">Control tower logic</div><div class="section-sub">The operating model behind the prototype.</div><div class="flow"><span class="flowbox">REQUEST</span><span class="arrow">→</span><span class="flowbox">SUPPORT</span><span class="arrow">→</span><span class="flowbox">RECONCILE</span><span class="arrow">→</span><span class="flowbox">AI EXCEPTION</span><span class="arrow">→</span><span class="flowbox">HUMAN ACTION</span><span class="arrow">→</span><span class="flowbox">CLOSE</span></div></div>',unsafe_allow_html=True)
        st.write('')
        st.markdown('<div class="insight"><strong>Design principle</strong><br><span class="small">AI detects, explains, prioritises and routes. Humans approve financial decisions and close exceptions.</span></div>',unsafe_allow_html=True)
    st.write('')
    st.markdown('### What the data says')
    c1,c2,c3=st.columns(3)
    c1.metric('Support-only IDs', support_only, help='Present in Support but not Finance')
    c2.metric('Finance-only IDs', finance_only, help='Present in Finance but not Support')
    c3.metric('Closed + pending payout', int(recon['flags'].apply(lambda x:'Closed but unpaid' in x).sum()), help='Potential customer-facing status conflict')

# -------------------- Exception Queue --------------------
elif page == 'Exception Queue':
    st.markdown('### Exception Queue')
    st.caption('This is the work queue: the prototype reduces the search space and tells an operator what to do next.')
    f1,f2,f3=st.columns([1,1,2])
    psel=f1.multiselect('Priority',['HIGH','MEDIUM','LOW'],default=['HIGH','MEDIUM'])
    owner_sel=f2.multiselect('Owner',sorted(recon.owner.dropna().unique()),default=[])
    search=f3.text_input('Search refund / agent / issue','')
    q=recon[recon.exception].copy()
    if psel: q=q[q.priority.isin(psel)]
    if owner_sel: q=q[q.owner.isin(owner_sel)]
    if search:
        term=search.lower(); q=q[q.apply(lambda r: term in str(r.id).lower() or term in str(r.agent).lower() or term in ' '.join(r.flags).lower(),axis=1)]
    q=q.sort_values(['priority','open_escalations','max_days_open'],key=lambda s:s.map({'HIGH':0,'MEDIUM':1,'LOW':2}) if s.name=='priority' else s, ascending=True)
    st.markdown(f'**{len(q):,} exceptions shown**')
    show=q[['priority','id','agent','route','support_status','finance_status','owner','flags','action']].copy()
    show['flags']=show['flags'].apply(lambda x:', '.join(x))
    show.columns=['Priority','Refund ID','Agent','Route','Support Status','Finance Status','Owner','AI Finding','Recommended Action']
    st.dataframe(show,use_container_width=True,hide_index=True,height=500)
    st.info('Tip for the interview: click Refund 360 and inspect one HIGH-priority case to show the complete reasoning chain.')

# -------------------- Refund 360 --------------------
elif page == 'Refund 360':
    st.markdown('### Refund 360')
    st.caption('A single operational record assembled from Support, Finance and Escalations.')
    ids=sorted(recon.id.dropna().unique())
    selected=st.selectbox('Select Refund ID',ids,index=ids.index('RF-1757') if 'RF-1757' in ids else 0)
    row=recon[recon.id==selected].iloc[0]
    priority=row.priority
    badge='high' if priority=='HIGH' else ('medium' if priority=='MEDIUM' else 'low')
    st.markdown(f'<span class="badge {badge}">{priority} PRIORITY</span> <span class="small">Owner: {row.owner}</span>',unsafe_allow_html=True)
    st.markdown(f'## {row.id} · {row.agent if pd.notna(row.agent) else row.finance_agent}')
    a,b,c,d=st.columns(4)
    a.metric('Refund amount', f"₹{row.support_amount:,.0f}" if pd.notna(row.support_amount) else '—')
    b.metric('Finance paid', f"₹{row.amount_paid:,.0f}" if pd.notna(row.amount_paid) else '—')
    c.metric('Open escalations', int(row.open_escalations))
    d.metric('Days open', int(row.max_days_open))
    l,r=st.columns(2)
    with l:
        st.markdown('<div class="card"><div class="section-title">Support</div>',unsafe_allow_html=True)
        st.write(f"**Status:** {row.support_status or '—'}")
        st.write(f"**Route:** {row.route or '—'}")
        st.write(f"**Channel:** {row.channel or '—'}")
        st.write(f"**Handled by:** {row.handled_by or '—'}")
        st.write(f"**Last updated:** {row.last_updated if pd.notna(row.last_updated) else '—'}")
        st.markdown('</div>',unsafe_allow_html=True)
    with r:
        st.markdown('<div class="card"><div class="section-title">Finance</div>',unsafe_allow_html=True)
        st.write(f"**Status:** {row.finance_status or '—'}")
        st.write(f"**Received:** {row.received_on or '—'}")
        st.write(f"**Processed:** {row.processed_on or '—'}")
        st.write(f"**Approved by:** {row.approved_by or '—'}")
        st.write(f"**Remarks:** {row.remarks or '—'}")
        st.markdown('</div>',unsafe_allow_html=True)
    st.write('')
    title,why,act=explain(row)
    st.markdown(f'<div class="card2"><div class="eyebrow">AI ANALYSIS</div><h3>{title}</h3><p><strong>Why it matters:</strong> {why}</p><p><strong>Recommended action:</strong> {act}</p></div>',unsafe_allow_html=True)
    st.write('')
    if row.flags:
        st.write('**Detected signals:** ' + ' · '.join(row.flags))
    st.caption('AI boundary: the prototype can identify and explain exceptions, but it does not approve refunds or execute payouts.')

# -------------------- Message Intake --------------------
elif page == 'Message Intake':
    st.markdown('### Message Intake')
    st.caption('Demonstrates the unstructured-to-structured step from the case brief: informal requests can arrive outside the trackers.')
    samples={
        'Peak Journeys · 5 June (RF-1099)': 'Hi, I cancelled booking for DEL-DXB last week and was told I\'d get a refund. I haven\'t received anything and I don\'t have any reference number. Please help, my client is asking.',
        'Nomad Travel · 8 June (RF-1098)': 'Bhai refund ka kya hua? BLR-MAA wala. 2 hafte ho gaye, koi jawab nahi.',
        'Internal Support note · 11 June': 'Finance says they never received several of the refunds I closed last month. I marked them done on my side. Not sure where they went.'
    }
    choice=st.selectbox('Demo message',list(samples.keys()))
    message=st.text_area('Incoming message',samples[choice],height=130)
    if st.button('✦ Extract & Analyse',type='primary',use_container_width=True):
        ids=re.findall(r'RF[- ]?\d{3,5}',message.upper())
        route_match=re.search(r'([A-Z]{3})[-–]([A-Z]{3})',message.upper())
        refund_id=ids[0].replace(' ','-') if ids else 'Not provided'
        route=f'{route_match.group(1)}-{route_match.group(2)}' if route_match else 'Not provided'
        urgency='HIGH' if any(x in message.lower() for x in ["urgent","2 hafte","haven't received","not received","never received"]) else 'MEDIUM'
        st.markdown('#### AI extraction')
        c1,c2,c3=st.columns(3)
        c1.metric('Refund ID',refund_id)
        c2.metric('Route',route)
        c3.metric('Urgency',urgency)
        if refund_id!='Not provided' and refund_id in set(recon.id):
            row=recon[recon.id==refund_id].iloc[0]
            title,why,act=explain(row)
            st.markdown(f'<div class="card2"><div class="eyebrow">MATCH FOUND</div><h3>{title}</h3><p>{why}</p><p><strong>Next:</strong> {act}</p></div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="card2"><div class="eyebrow">NO DIRECT MATCH</div><h3>Create an intake record</h3><p>The message contains a refund issue but the current tracker cannot confidently match it to a record.</p><p><strong>Next:</strong> create a provisional refund ID, assign Support, and reconcile once a reference becomes available.</p></div>',unsafe_allow_html=True)
    st.info('Why this matters: the brief explicitly says some refund requests arrive by email or messaging app and are handled off-tracker. The prototype makes that intake visible before it becomes an escalation.')

# -------------------- Reconciliation --------------------
elif page == 'Reconciliation':
    st.markdown('### Reconciliation')
    st.caption('Support and Finance were built independently. This view shows where they agree, disagree or fall silent.')
    matched=len(set(support.id)&set(finance.id)); support_only=len(set(support.id)-set(finance.id)); finance_only=len(set(finance.id)-set(support.id))
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Matched',matched); c2.metric('Support only',support_only); c3.metric('Finance only',finance_only); c4.metric('Support duplicates',len(support_dup_ids))
    st.write('')
    st.markdown('<div class="card"><div class="section-title">Exception types</div><div class="section-sub">A refund may have more than one signal.</div></div>',unsafe_allow_html=True)
    counts={}
    for flags in recon.flags:
        for flag in flags: counts[flag]=counts.get(flag,0)+1
    chart=pd.Series(counts).sort_values(ascending=False).head(10)
    st.bar_chart(chart)
    st.write('')
    st.markdown('#### High-priority reconciliation records')
    q=recon[recon.priority=='HIGH'].sort_values(['open_escalations','max_days_open'],ascending=False).head(15)
    out=q[['id','agent','support_status','finance_status','flags','owner','action']].copy(); out['flags']=out.flags.apply(lambda x:', '.join(x))
    out.columns=['Refund ID','Agent','Support','Finance','Signals','Owner','Next action']
    st.dataframe(out,use_container_width=True,hide_index=True)

# -------------------- Demo --------------------
elif page == 'Demo':
    st.markdown('### 90-second interview demo')
    st.caption('A guided sequence designed to show judgement, not just software.')
    steps=[
        ('01','Overview','Start with the mismatch: Support and Finance do not provide one reliable operational view.'),
        ('02','Exception Queue','Filter HIGH priority and show that the tool surfaces a small set of cases worth human attention.'),
        ('03','Refund 360','Open RF-1757 and explain the Support/Finance status conflict and the recommended owner.'),
        ('04','Message Intake','Paste the Peak Journeys or Nomad Travel message and show extraction before reconciliation.'),
        ('05','Human action','End with the boundary: AI detects, explains and routes; a person approves financial decisions and closes the exception.')]
    for n,title,desc in steps:
        st.markdown(f'<div class="card" style="margin-bottom:10px"><span class="badge low">{n}</span><strong>{title}</strong><div class="small" style="margin-top:6px">{desc}</div></div>',unsafe_allow_html=True)
    st.success('Suggested closing line: “I did not try to automate the refund decision. I automated the reconciliation and exception-finding work around it, so the same headcount can act earlier and with better evidence.”')
    st.markdown('### Prototype boundary')
    st.markdown('<div class="insight"><strong>What is real in this prototype</strong><br><span class="small">The workbook is loaded and reconciled at runtime; exception rules are derived from the actual Support, Finance and Escalations tabs; the informal messages are taken from the case brief.</span></div>',unsafe_allow_html=True)
    st.write('')
    st.markdown('<div class="insight"><strong>What is intentionally not automated</strong><br><span class="small">Refund approval, payout execution and ambiguous financial judgement remain human decisions.</span></div>',unsafe_allow_html=True)
