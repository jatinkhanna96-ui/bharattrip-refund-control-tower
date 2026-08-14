import streamlit as st,pandas as pd,re
from pathlib import Path
def n(x): return None if pd.isna(x) else re.sub(r'[\s-]','',str(x).upper())
st.set_page_config(layout='wide')
st.title('BharatTrip Refund Control Tower')
f=st.sidebar.text_input('Excel file','BharatTrip_Refund_Data_final(1).xlsx')
if not Path(f).exists(): st.warning('Place Excel beside app.py'); st.stop()
sup=pd.read_excel(f,'Support_Tracker'); fin=pd.read_excel(f,'Finance_Tracker'); esc=pd.read_excel(f,'Escalations')
sup['id']=sup['Ticket ID'].map(n); fin['id']=fin['Ref No'].map(n)
m=sup.merge(fin[['id','Payout Status','Amount Paid (INR)']],on='id',how='left')
def flag(r):
 if str(r.get('Status'))=='Closed' and pd.isna(r.get('Payout Status')): return 'Missing in Finance'
 if str(r.get('Status'))=='Closed' and str(r.get('Payout Status'))=='Pending Payout': return 'Closed but unpaid'
 return None
m['Issue']=m.apply(flag,axis=1)
c1,c2,c3=st.columns(3); c1.metric('Refunds',len(sup)); c2.metric('Escalations',len(esc)); c3.metric('Exceptions',m['Issue'].notna().sum())
tab1,tab2=st.tabs(['Exceptions','AI Analysis'])
with tab1: st.dataframe(m[m['Issue'].notna()][['id','Agent','Issue']],use_container_width=True)
with tab2:
 ids=list(m['id'].dropna().unique()); cid=st.selectbox('Case',ids)
 r=m[m['id']==cid].iloc[0]
 st.write('Issue:',r['Issue'])
 if st.button('Generate AI Response'):
  st.info('Root Cause: '+str(r['Issue']))
  st.success('Recommended Action: Investigate and send agent update.')
