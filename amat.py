"""
Apple Messages Analytics Toolbox

Main repository can be found [here](https://github.com/parkersruth/amat)

## DataFrame Fields

Each row of the DataFrame corresponds to an individual message. The DataFrame
contains the same columns as the original Apple Messages SQLite database, in
addition to some added columns for convenience. Below is a selection of
particularly useful fields.

- `chat_id` - a unique ID for each chat dialogue
- `contact` - the display name listed in the chat ID map file
- `date_utc` - a datetime object for the send date/time of the message in UTC
- `date_local` - a datetime object for the send date/time of the message in the local timezone
- `weekday` - the day of the week the message was sent (0 = Mon, 1 = Tue, ..., 6 = Sun)
- `hour` - the hour of the day the message was sent (military time)
- `timestamp` - a human-readable timestamp of when the message was sent in the local timezone
- `length` - the total number of characters in the message
- `is_from_me` - 1 if I sent this message, 0 if I received it from someone else
- `ioicon` - 💬 if I sent this message, 📢 if I received it from someone else

"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yaml
from dateutil.parser import parse
import textwrap as tw
import re


def load_data(data_file, id_file=None, tz='Etc/UTC'):
    """Loads chat data from pickled DataFrame, optionally adds chat ID mapping,
    and optionally configures the local timezone.

    Args:
        data_file: the file path of a pickled DataFrame
        id_file: the file path of a YAML id map. Any chat IDs not mapped in the
            YAML file default to "other".
        tz: the local timezone (see full list [here](https://stackoverflow.com/q/13866926))

    Returns:
        df: A pandas DataFrame object containing the Messages data

    Example:
        ```python
        df = load_data("chat_df.pkl", "id_map.yaml", "US/Pacific")
        ```
    """

    try:
        df = pd.read_pickle(data_file)
    except:
        print("Couldn't open", data_file, "as pickled pandas DataFrame")

    df['date_local'] = df['date_utc'].dt.tz_localize('utc').dt.tz_convert(tz).dt.tz_localize(None)
    df['timestamp'] = df['date_local'].dt.strftime('%Y.%m.%d %r')

    weekdays = df['date_local'].apply(lambda x: x.weekday())
    hours = df['date_local'].apply(lambda x: x.hour)
    df = df.assign(weekday = weekdays)
    df = df.assign(hour = hours)

    if id_file is None:
        return df

    try:
        with open(id_file, 'r') as stream:
            id_map = yaml.safe_load(stream)
    except:
        print("Couldn't open", id_file, "as YAML file")

    df['contact'] = df.apply(lambda x: id_map.get(x['chat_id'], 'other'), axis=1)
    return df


def filt_date(df, start='Jan 1, 1900', end='Jan 1, 2200'):
    """Filters only the messages between the given dates.

    Args:
        df: a chat DataFrame
        start: the start date as a human-readable string (defaults to 1/1/1900)
        end: the end date as a human-readable string (defaults to 1/1/2200)

    Returns:
        df: filtered chat DataFrame

    Example:
        ```python
        new_texts = filt_date(df, start="Jan 1, 2019")
        old_texts = filt_date(df, end="July 7, 2018")
        summer = filt_date(df, start="Jun 21, 2019", end="Sept 23, 2019")
        ```
    """

    return df[(df['date_local'] > parse(start)) & (df['date_local'] < parse(end))]


def filt_any(df, by, *vals):
    """Filters messages with the given field equal to any of the given vals.

    Args:
        df: a chat DataFrame
        by: the DataFrame field to filter by
        *vals: variable length args for allowable values

    Returns:
        df: filtered chat DataFrame

    Example:
        ```python
        from_mom = filt_any(df, 'contact', 'Mom')
        from_parents = filt_any(df, 'contact', 'Mom', 'Dad', 'Mom and Dad')
        ```
    """

    return df[df[by].isin(vals)]


def filt_func(df, by, func):
    """Filters messages where the given field are mapped by True by the given
    function.

    Args:
        df: a chat DataFrame
        by: the DataFrame field to filter by
        func: a function mapping values to booleans

    Returns:
        df: filtered chat DataFrame

    Example:
        ```python
        def selector(weekday):
            if weekday in (0, 2, 4):
                return True
            else:
                return False
        mwf = filt_func(df, 'weekday', selector)
        # returns all texts sent on Mondays, Wednesdays, and Fridays

        frabjous = filt_func(df, 'text', lambda x: 'frabjous' in x.lower())
        # returns all texts containing the word frabjous (not case-sensitive)

        from_parents = filt_func(df, 'contact', lambda x: 'Mom' in x or 'Dad' in x)
        # equivalent to the following:
        # from_parents = filt_any(df, 'contact', 'Mom', 'Dad', 'Mom and Dad')
        ```
    """

    return df[(df[by].apply(func))]


def plot_count(df, freq, by='contact', **kwargs):
    """Plots the total number of messages over time

    Args:
        df: a chat DataFrame
        freq: frequency bin size (see full list [here](https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects))

            - "D" to plot per day
            - "W" to plot per week
            - "M" to plot per month
            - "Y" to plot per yearl
            - "3D" for three days, "6M" for six months, etc.
        by: field to group by (defaults to contact)
        **kwargs: additional plotting configurations (see full list [here](https://pandas.pydata.org/pandas-docs/version/0.23/generated/pandas.DataFrame.plot.html))

            - figsize: a tuple (width, height) in inches (default is 10 by 5)
            - kind: "line" or "area" (defaults to "area")
            - stacked: boolean determining whether to stack lines/areas
            - legend: boolean determining whether to displa a legend (defualts True)
            - title: a string title for the plot (defaults None)
            - cmap: a colormap object (see full list [here](https://matplotlib.org/3.1.0/tutorials/colors/colormaps.html))

    Example:
        ```python
        plot_count(df, 'Y', legend=False)
        # plots number of messages per year by contact

        plot_count(df, 'M', by='weekday', kind='line', stacked=False, cmap='rainbow')
        # plots number of messages per month by weekday as a rainbow line graph
        ```
    """
    df.groupby(by).resample('D', on='date_local').count() \
        .unstack(level=0).resample(freq).sum() \
        .plot(y='guid',
              figsize=kwargs.pop('figsize', (15,5)),
              kind=kwargs.pop('kind', 'area'),
              **kwargs)


def plot_length(df, freq, by='contact', **kwargs):
    """Plots the net length of messages sent (total characters) over time"

    Args:
        df: a chat DataFrame
        freq: see `amat.plot_count`
        by: field to group by (defaults to contact)
        **kwargs: see `amat.plot_count`

    Example:
        ```python
        plot_length(df, 'Y', legend=False)
        # plots length of messages per year by contact

        plot_length(df, 'M', by='weekday', kind='line', stacked=False, cmap='rainbow')
        # plots length of messages per month by weekday as a rainbow line graph
        ```
    """
    df.groupby(by).resample('D', on='date_local').sum() \
        .unstack(level=0).resample(freq).sum() \
        .plot(y='length',
              figsize=kwargs.pop('figsize', (15,5)),
              kind=kwargs.pop('kind', 'area'),
              **kwargs)


def breakdown(df, slivers=[2], by='contact', **kwargs):
    """Plots a pie chart breakdown with the given minimum sliver sizes

    Args:
        df: a chat DataFrame
        slivers: an array of minimum slice sizes as percents. For example,
            slivers=[3, 5] will plot two pie charts; the first will label any
            slices less than 3% of the area as "other", the second pie chart
            will break down the other category, labeling any slices less than
            5% of the remaining pie size as "other"
        by: the field to group messages by
        **kwargs: additional plotting configurations (see full list [here](https://pandas.pydata.org/pandas-docs/version/0.23/generated/pandas.DataFrame.plot.html))

    Example:
        ```python
        breakdown(df)
        # displays pie chart showing percentages of messages with each contact

        breakdown(df, by='chat_id', slivers[2, 4, 3])
        # displays pie chart breakdown by chat_id
        ```
    """

    totals = df.groupby(by).count().copy()
    totals = totals['guid'].reset_index()
    total = totals['guid'].sum()
    totals['pcnt'] = totals['guid'].div(total).mul(100)
    totals.sort_values(by='pcnt', inplace=True, ascending=False)


    for i in range(len(slivers)):
        k = kwargs.copy()
        temp = totals.copy()
        temp[by] = temp.apply(
            lambda x: x[by] if x['pcnt'] > slivers[i] else 'other', axis=1)
        temp = temp.groupby(by).sum()
        ax = temp.plot.pie(y='pcnt',
                legend=k.pop('legend', False),
                figsize=k.pop('figsize', (6, 6)),
                title=k.pop('title', "total: "+str(total)),
                **k)
        ax.set_ylabel('')

        totals = totals[totals['pcnt'] < slivers[i]].copy()
        if totals.size == 0:
            break
        total = totals['guid'].sum()
        totals['pcnt'] = totals['guid'].div(total).mul(100)


def __highlight(string):
    return '\u001b[43m{}\u001b[0m'.format(string)


def __highlight_re(string, query, case=True):
    if case:
        pattern = re.compile(re.escape(query))
    else:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
    for match in re.finditer(pattern, string):
        start, end = match.span()
        string = string[:start] + __highlight(string[start:end]) + string[end:]
    return string


def search(df, query, case=False):
    """Filters messages containing the given string

    Args:
        df: a chat DataFrame
        query: a string to search for
        case: a boolean marking case sensitivity (defualts True)

    Returns:
        df: DataFrame of messages containing the given query

    Example:
        ```python
        search(df, "frabjous", True)
        # returns messages containing frabjous (case-sensitive)
        ```
    """
    return df[df['text'].str.contains(query, case=case)]


def context_search(df, query, case=False, radius=5):
    """Prints messages containing the query, with some messages before and after

    Args:
        df: a chat DataFrame
        query: a string to search for
        case: a boolean marking case sensitivity (defualts True)
        radiu: the number of messages to print before and after each result

    Example:
        ```python
        search_context(df, "frabjous", True, 3)
        # prints messages containing "frabjous" with context radius of three
        ```
    """
    r = search(df, query, case)
    for _, row in r.iterrows():
        pal, date = row['contact'], row['date_local']
        chat = filt_any(df, 'contact', pal).reset_index()
        i = chat.index[chat['date_local'] == date].tolist()[0]
        start, end = max(0, i-radius), min(chat.shape[0]-1, i+radius+1)
        around = chat.iloc[start:end]
        hltext = around['text'].apply(lambda x: __highlight_re(x, query, case))
        around = around.assign(hltext = hltext)
        print(pal)
        for _, line in around.iterrows():
            text = '{} {} {}'.format(line['timestamp'], line['ioicon'], line['hltext'])
            print(tw.fill(text, width=90, initial_indent='', subsequent_indent=' '*27))
        print()


def weekly_heatmap(df, figsize=(15,10), **kwargs):
    """Displays a heatmap of message counts over days of the week

    Args:
        df: a chat DataFrame
        figsize: a tuple (width, height) in inches (default is 10 by 5)
        **kwargs: additional plotting configurations (see full list [here](https://matplotlib.org/3.1.1/api/_as_gen/matplotlib.pyplot.imshow.html))

    Example:
        ```python
        weekly_heatmap(df, cmap="Blues")
        # displays a heatmap of weekly activity with blue colormap
        ```
    """
    timesheet = df.groupby(['weekday', 'hour']).count()['guid'].unstack(level=1)
    heatmap = timesheet.reindex(np.arange(7)).reindex(np.arange(24), axis=1).fillna(0).to_numpy()

    weekdaynames = ['M', 'T', 'W', 'R', 'F', 'A', 'U']
    hournames = [str(x) for x in range(25)]
    hournames = ['12am'] + [str(x) + 'am' for x in range(1, 13)] + [str(x) + 'pm' for x in range(1, 13)]

    heatmap = np.roll(heatmap, -4)
    hournames = np.roll(np.array(hournames), -4)

    fig, ax = plt.subplots(figsize=figsize)
    plt.imshow(heatmap, cmap=kwargs.pop('cmap', 'viridis'), **kwargs)

    ax.set_yticks(np.arange(len(weekdaynames) + 1) - 0.5)
    ax.set_xticks(np.arange(len(hournames)) - 0.5)
    ax.set_yticklabels(weekdaynames)
    ax.set_xticklabels(hournames)
    ax.grid()

    plt.show()

