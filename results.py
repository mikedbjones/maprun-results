import requests
import pandas as pd
import io
import os
from datetime import datetime, timezone
import pytz
from ftplib import FTP
import json

def get_uk_time_now():
    # Get the current datetime in UTC
    utc_now = datetime.now(timezone.utc)
    # Convert to the UK timezone
    uk_tz = pytz.timezone('Europe/London')
    uk_now = utc_now.astimezone(uk_tz)
    return uk_now

def convert_timedelta_format(timedelta):
    parts = timedelta.split(':')
    if len(parts) == 3:
        # Format is hh:mm:ss
        converted_timedelta = timedelta
    elif len(parts) == 2:
        # Format is mm:ss
        converted_timedelta = ('0:' + timedelta)
    else:
        # Handle invalid format or empty string
        raise ValueError('time not of format hh:mm:ss or mm:ss')

    return converted_timedelta

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

def download_process_results(events_info):

    events_file = events_info['file']
    events_html_name = events_info['html_name']
    events_html_title = events_info['html_title']

    # DOWNLOAD LATEST RESULTS
    print(f'-------------------------\nStarting at {get_uk_time_now().strftime("%d/%m/%Y %H:%M:%S %Z")}')
    with open(events_file, 'r') as f:
        events = json.load(f)

    to_concat = []

    for event in events:
        data = requests.get(url=events[event]).content
        df = pd.read_html(io.StringIO(data.decode('utf-8')))[0]
        df = df.dropna(subset=['Time', 'Points'])
        print(f'Downloaded {event}')
        df['Event'] = event
        df['Age Category'] = df['AgeCat Position'].str.replace(r'\:.+', '', regex=True)
        df['Points'] = df['Points'].astype(str).str.replace(r'\s.+', '', regex=True).astype(int)
        df['Time'] = df['Time'].apply(convert_timedelta_format) # handle instances where time is mm:ss instead of hh:mm:ss
        df['Time'] = pd.to_timedelta(df['Time'])
        df = df.sort_values(['Name', 'Age Category', 'Event', 'Points'], ascending=False)
        df = df.drop_duplicates(subset=['Name', 'Age Category', 'Event'], keep='first')
        df = df[['Name', 'Age Category', 'Event', 'Points', 'Time']]
        to_concat.append(df)

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
    df.loc[df.shape[0], 'Name'] = f'Latest update at: {get_uk_time_now().strftime("%d/%m/%Y %H:%M:%S %Z")}'
    print('Merged results')

    # EXPORT CSV AND HTML FILES
    curr_dir = os.path.dirname(__file__)
    tmp_dir = '/tmp/'
    tmp_path = os.path.join(curr_dir, tmp_dir)
    csv_name = f'{events_html_name}.csv'
    html_name = f'{events_html_name}.html'
    
    csv_file = f'{tmp_path}{csv_name}'
    html_file = f'{tmp_path}{html_name}'

    df.to_csv(csv_file, index=False)

    pd.set_option('colheader_justify', 'center')   # FOR TABLE <th>

    html_string = f'''
    <html>
    <head><title>{events_html_title}</title></head>
    <link rel="stylesheet" type="text/css" href="df_style.css"/>
    <body>
        {{table}}
    </body>
    </html>.
    '''

    # OUTPUT AN HTML FILE
    with open(html_file, 'w') as f:
        f.write(html_string.format(table=df.to_html(justify='left', index=False, na_rep='', classes='mystyle')))

    print('Exported CSV and HTML files')

    # UPLOAD

    try:
        UPLOAD_ADDRESS = os.environ['UPLOAD_ADDRESS']
        UPLOAD_DIRECTORY = os.environ['UPLOAD_DIRECTORY']
        UPLOAD_USERNAME = os.environ['UPLOAD_USERNAME']
        UPLOAD_PASSWORD = os.environ['UPLOAD_PASSWORD']

        ftp = FTP(UPLOAD_ADDRESS)
        ftp.login(UPLOAD_USERNAME, UPLOAD_PASSWORD)
        ftp.cwd(UPLOAD_DIRECTORY)

        for f in [csv_name, html_name]:
            file = open(f'{tmp_path}{f}','rb')
            ftp.storbinary('STOR '+f, file)
            file.close()

        ftp.quit()

        print(f'Uploaded files to {UPLOAD_ADDRESS} at {get_uk_time_now().strftime("%d/%m/%Y %H:%M:%S %Z")}\n-------------------------')

    except KeyError:
        print('Upload details not configured; skipping upload\n-------------------------')


def lambda_handler(event, context):

    download_process_results(event)

    return {
        'statusCode': 200,
        'body': 'Maprun results run successfully'
    }

if __name__ == "__main__":

    with open('events_info.json', 'r') as f:
        events_info_json = f.read()

    events_info_dict = json.loads(events_info_json)
    
    lambda_handler(event=events_info_dict, context=None)