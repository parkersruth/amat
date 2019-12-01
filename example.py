from amat import *

# load DataFrame, add chat ID mapping, and set local timezone
df = load_data("chat_df.pkl", "id_map.yaml", "US/Pacific")

# preview the most recent 10 messages
df.tail(10)[['text', 'contact', 'chat_id', 'timestamp']]

# plot total texts per month
plot_count(df, 'M', legend=False, cmap="Blues")

# plot length of texts from family since Jan 1, 2019 as rainbow line graph
family = filt_func(df, 'contact', lambda x : 'Mom' in x or 'Dad' in x or 'Wombat' in x)
plot_length(filt_date(family, start='Jan 1, 2019'), '3W', cmap='rainbow', kind='line')

# pie chart breakdown of message activity per contact
breakdown(df, (2,1), by='contact', cmap='nipy_spectral')

# heatmap of activity per weekday with blue colormap
weekly_heatmap(df, cmap='Blues')

# weekly heatmap of recent texts from me to Mom
recent = filt_date(df, 'September 25, 2019')
weekly_heatmap(filt_any(filt_any(recent, 'contact', 'Mom'), 'is_from_me', False))

# all texts containing the word frabjous (case-insensitive)
context_search(df, 'frabjous', False, 3)

# print last ten messages from unmapped chat IDs
filt_any(df, 'contact', 'other').tail(10)[['date_local', 'text', 'chat_id', 'contact']]

