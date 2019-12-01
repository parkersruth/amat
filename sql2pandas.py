import sqlite3
import pandas as pd
import datetime as dt
import html
import yaml
import os, errno

outfolder = "preview/"

id_map = yaml.load(open('id_map.yaml', 'r'), Loader=yaml.FullLoader)

conn = sqlite3.connect('chat.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

qry_one_msg = '''
SELECT * FROM message T1
INNER JOIN chat_message_join T2
  ON T1.ROWID=T2.message_id
LIMIT 1
'''

qry_msgs = '''
SELECT * FROM message T1
INNER JOIN chat_message_join T2
  ON T1.ROWID=T2.message_id
'''

# qry_msgs_by_chat_id = '''
# SELECT * FROM message T1
# INNER JOIN chat_message_join T2
#   ON T2.chat_id=?
#   AND T1.ROWID=T2.message_id
# ORDER BY T1.date
# '''

c.execute(qry_one_msg)
keys = c.fetchone().keys()

c.execute(qry_msgs)
df = pd.DataFrame(c.fetchall(), columns=keys)

date_parser = lambda date : dt.datetime(2001, 1, 1, 0) + \
                            dt.timedelta(seconds=date/1e9)
df['date_utc'] = df['date'].apply(date_parser)
df.sort_values('date', inplace=True)

def to_html(df, chat_id):
    df_id = df.loc[df['chat_id'] == chat_id]

    body = ''
    for index, row in df_id.iterrows():

        htmlformat = '\t<p><span class="{}">{}</span></p>\n'
        text = html.escape(row['text'] or '')
        source = 'from-me' if row['is_from_me'] else 'from-them'
        line = htmlformat.format(source, text)
        body += line
        #if index > 25230:
            #break

    return body


template = '''
<!DOCTYPE html>
<html>
<head>

    <link rel='stylesheet' href='../chat_style.css'>
    <title> {} </title>
	<meta charset="UTF-8">
    <meta name="description" content="TODO description">
    <meta name="author" content="Parker Ruth">
    <!-- <meta name="viewport" content="width=device-width, initial-scale=1.0"> -->

</head>
<body>

{}

</body>
</html>
'''

if not os.path.exists(os.path.dirname(outfolder)):
    try:
        os.makedirs(os.path.dirname(outfolder))
    except OSError as exc: # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise

chat_ids = df.chat_id.unique()
for chat_id in chat_ids:

    body = to_html(df, chat_id)

    f = open(outfolder+'chat_{}.html'.format(chat_id), 'w')
    f.write(template.format(id_map.get(chat_id, chat_id), body))
    f.close()

df['length'] = df['text'].apply(lambda x: len(x) if isinstance(x, str) else 0)
df['ioicon'] = df['is_from_me'].apply(lambda x: '💬' if x else '📢')
df = df.astype({'text':'str'})

df.sort_values(by='date_utc', inplace=True)

df.to_pickle('chat_df.pkl')
