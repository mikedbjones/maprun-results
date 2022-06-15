import requests
import pandas as pd
import io
import os
from datetime import datetime
from ftplib import FTP_TLS

# DOWNLOAD LATEST RESULTS

print(f'-------------------------\nStarting at {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')

danebridge = 'https://p.fne.com.au/rg/cgi-bin/SelectResultFileForSplitsBrowserFiltered.cgi?act=fileToSplitsBrowser&eventName=ScoreResults_Danebridge%20Race%201%20PZ%20PXAS%20ScoreV120.csv'
winster = 'https://p.fne.com.au/rg/cgi-bin/SelectResultFileForSplitsBrowserFiltered.cgi?act=fileToSplitsBrowser&eventName=ScoreResults_Winster%20Race%202%20PZ%20PXAS%20ScoreV120.csv'
hartington = 'https://p.fne.com.au/rg/cgi-bin/SelectResultFileForSplitsBrowserFiltered.cgi?act=fileToSplitsBrowser&eventName=ScoreResults_Hartington%20Alstonefield%20Race%203%20PZ%20PXAS%20ScoreV120.csv'

events = {'Danebridge': danebridge, 'Winster': winster, 'Hartington': hartington}
to_concat = []

for event in events:
    data = requests.get(url=events[event]).content
    df = pd.read_html(io.StringIO(data.decode('utf-8')))[0]
    print(f'Downloaded {event}')
    df['Event'] = event
    df['Age Category'] = df['AgeCat Position'].str.replace(r'\:.+', '', regex=True)
    df['Points'] = df['Points'].str.replace(r'\s.+', '', regex=True).astype(int)
    df['Time'] = pd.to_timedelta(df['Time'])
    df = df.sort_values(['Name', 'Age Category', 'Event', 'Points'], ascending=False)
    df = df.drop_duplicates(subset=['Name', 'Age Category', 'Event'], keep='first')
    df = df[['Name', 'Age Category', 'Event', 'Points', 'Time']]
    to_concat.append(df)

df_danebridge = to_concat[0]
df_winster = to_concat[1]
df_hartington = to_concat[2]

# MERGE RESULTS

df = df_danebridge.merge(df_winster, how='outer', on=['Name', 'Age Category'])
df = df.merge(df_hartington, how='outer', on=['Name', 'Age Category'])

points_cols = [x for x in df.columns if 'Points' in x]
time_cols = [x for x in df.columns if 'Time' in x]

df['Total Points'] = df[points_cols].fillna(0).sum(axis=1)
df['Total Time'] = df[time_cols].fillna(pd.Timedelta(seconds=0)).sum(axis=1)

df = df.sort_values(['Total Points', 'Total Time'], ascending=[False, True])

events_cols = [x for x in df.columns if 'Event' in x]
df[events_cols] = df[events_cols].apply(lambda x: x.astype(str).str.replace('NaN', '', case=False))

points_cols = [x for x in df.columns if 'Points' in x]
df[points_cols] = df[points_cols].apply(lambda x: x.astype(str).replace(r'\..+', '', regex=True).str.lower().str.replace('nan', '', case=False))

time_cols = [x for x in df.columns if 'Time' in x]
df[time_cols] = df[time_cols].apply(lambda x: x.astype(str).replace(r'.+\s', '', regex=True).str.lower().str.replace('nat', '', case=False))

df.columns = ['Name', 'Age Category', 'Event', 'Points', 'Time', 'Event', 'Points', 'Time', 'Event', 'Points', 'Time',
              'Total Points', 'Total Time']

# ADD BOTTOM ROW WITH UPDATED DATE AND TIME

df.loc[df.shape[0], 'Name'] = f'Latest update at: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'

print('Merged results')

# EXPORT CSV AND HTML FILES

csv_file = 'peak_raid_maprun_2022_results.csv'
html_file = 'peak_raid_maprun_2022_results.html'

df.to_csv(csv_file, index=False)
df.to_html(html_file, justify='left', index=False, na_rep='')

print('Exported CSV and HTML files')

# UPLOAD TO qdata.uk

IP = os.environ.get('Q_DATA_IP')
USERNAME = os.environ.get('Q_DATA_USERNAME')
PASSWORD = os.environ.get('Q_DATA_PASSWORD')

ftp = FTP_TLS(IP)
ftp.login(USERNAME, PASSWORD)
ftp.prot_p()
ftp.cwd('/public_html/')

for f in [csv_file, html_file]:
    file = open(f,'rb')
    ftp.storbinary('STOR '+f, file)
    file.close()

ftp.quit()

print(f'Uploaded files to qdata.uk at {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}\n-------------------------')
