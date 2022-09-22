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
wormhill = 'https://p.fne.com.au/rg/cgi-bin/SelectResultFileForSplitsBrowserFiltered.cgi?act=fileToSplitsBrowser&eventName=ScoreResults_Wormhill%20Race%204%20PZ%20PXAS%20ScoreV120.csv'

events = {'Danebridge': danebridge,
          'Winster': winster,
          'Hartington': hartington,
          'Wormhill': wormhill}
to_concat = []

for event in events:
    data = requests.get(url=events[event]).content
    df = pd.read_html(io.StringIO(data.decode('utf-8')))[0]
    print(f'Downloaded {event}')
    df['Event'] = event
    df['Age Category'] = df['AgeCat Position'].str.replace(r'\:.+', '', regex=True)
    df['Points'] = df['Points'].astype(str).str.replace(r'\s.+', '', regex=True).astype(int)
    df['Time'] = pd.to_timedelta(df['Time'])
    df = df.sort_values(['Name', 'Age Category', 'Event', 'Points'], ascending=False)
    df = df.drop_duplicates(subset=['Name', 'Age Category', 'Event'], keep='first')
    df = df[['Name', 'Age Category', 'Event', 'Points', 'Time']]
    to_concat.append(df)

df_danebridge = to_concat[0]
df_winster = to_concat[1]
df_hartington = to_concat[2]
df_wormhill = to_concat[3]

# MERGE RESULTS

l = len(to_concat)
df = to_concat[0]

for i in range(l-1):
    df = df.merge(to_concat[i+1], how='outer', on=['Name', 'Age Category'], suffixes=(f'_{i}', f'_{i+1}'))

points_cols = [x for x in df.columns if 'Points' in x]
time_cols = [x for x in df.columns if 'Time' in x]

df['Total Points'] = df[points_cols].fillna(0).sum(axis=1)
df['Total Time'] = df[time_cols].fillna(pd.Timedelta(seconds=0)).sum(axis=1)

df = df.sort_values(['Total Points', 'Total Time'], ascending=[False, True])

# ADD POSITION RANKS

def points_time_tuple(row):

    """
    Args:
        row (pd.Series): row of dataframe including columns 'Total Points' and 'Total Time'
    Returns:
        t (tuple): (Total points, -Total time)
    """

    t = (row['Total Points'], -row['Total Time'])
    return t

def points_time_rank(df):

    """
    Args:
        df (pd.DataFrame): Dataframe including columns 'Total Points' and 'Total Time'
    Returns:
        ranks (pd.Series): Ranked using 'min' method (eg 1, 2, 2, 4, 5, 5, 7) on points (desc) then time (asc)
    """
    ranks = df[['Total Points', 'Total Time']].apply(points_time_tuple, axis=1).rank(method='min', ascending=False).astype(int).astype(str)
    return ranks

df['Pos'] = points_time_rank(df)
df['Age/Cat Pos'] = df.groupby('Age Category').apply(points_time_rank).reset_index(level=0)[0]

# REORDER COLUMNS

cols = df.columns.tolist()
cols = cols[-2:] + cols[:-2]
df = df[cols]

# SET COLUMN DTYPES AND NAMES FOR EXPORT

events_cols = [x for x in df.columns if 'Event' in x]
df[events_cols] = df[events_cols].apply(lambda x: x.astype(str).str.replace('NaN', '', case=False))

points_cols = [x for x in df.columns if 'Points' in x]
df[points_cols] = df[points_cols].apply(lambda x: x.astype(str).replace(r'\..+', '', regex=True).str.lower().str.replace('nan', '', case=False))

time_cols = [x for x in df.columns if 'Time' in x]
df[time_cols] = df[time_cols].apply(lambda x: x.astype(str).replace(r'.+\s', '', regex=True).str.lower().str.replace('nat', '', case=False))

begin = ['Pos', 'Age/Cat Pos', 'Name', 'Age Category']
middle = ['Event', 'Points', 'Time']
end = ['Total Points', 'Total Time']

df.columns = begin + len(to_concat)*middle + end

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
