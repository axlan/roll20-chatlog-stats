from dateutil import parser
from collections import defaultdict

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

df = pd.read_csv('data/rolls.zip', parse_dates=['time'])

with open('data/sessions.txt', 'r') as fd:
    sessions = [ line.strip() for line in fd.readlines() ]

players = ['Ney','Vinny Smoothbeard','Gobheart','Arden',
           'Orin','Sanna Mistbrace','Raika ','Albrecht Landershire',
           'Milos Stache']

ROLL_STAT_COLS = ['Num Rolls', 'Average Roll',
                  'Bad Rolls', 'Worst Streak',
                  'Good Rolls', 'Best Streak']

types = df['type'].unique().tolist()

OVERALL = 'Overall'

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

app.layout = dbc.Container([
    html.H1('Roll Filters'),
    dbc.Row([
        dbc.Col([dbc.Card([
            dbc.FormGroup([
                dbc.Label('Player'),
                dcc.Dropdown(
                    id="dropdown_player",
                    options=[{"label": x, "value": x}
                            for x in  [OVERALL] + players],
                    value=OVERALL
                )
            ]),
            dbc.FormGroup([
                dbc.Label('Session'),
                dcc.Dropdown(
                    id="dropdown_session",
                    options=[{"label": x, "value": x}
                            for x in [OVERALL] + sessions],
                    value=OVERALL
                ),
            ]),
            dbc.FormGroup([
                dbc.Label('Roll Type'),
                dcc.Dropdown(
                    id="dropdown_type",
                    options=[{"label": x, "value": x}
                            for x in [OVERALL] + types],
                    value=OVERALL
                ),
            ]),
        ])]),
        dbc.Col([dbc.Card([
            dbc.FormGroup([
                dbc.Label('"Good" Roll Threshold'),
                    dbc.Input(
                    id="input_good_roll",
                    type='number',
                    value=20
                )
            ]),
            dbc.FormGroup([
                dbc.Label('"Bad" Roll Threshold'),
                dbc.Input(
                    id="input_bad_roll",
                    type='number',
                    value=1
                )
            ]),
        ])]),
    ]),

    html.Br(),
    html.H1('Roll Stats'),
    html.P('Click on column arrows to sort'),
    dash_table.DataTable(
        id='roll_table',
        columns=[{"name": i, "id": i} for i in ['Player'] + ROLL_STAT_COLS],
        sort_action="native",
        data=None,
    ),
    html.Br(),
    html.H1('Graphs'),
    html.P('Click on legend items to enable/disable'),
    dcc.Graph(id="roll_graph"),
    dcc.Graph(id="type_graph"),
])

def filter_df(player=OVERALL, session=OVERALL, roll_type=OVERALL):
    df_filtered = df
    if player != OVERALL:
        df_filtered = df_filtered[df_filtered['character'] == player]
    if session != OVERALL:
        session_idx = sessions.index(session)
        df_filtered = df_filtered[df_filtered['session'] == session_idx]
    if roll_type != OVERALL:
        df_filtered = df_filtered[df_filtered['type'] == roll_type]
    return df_filtered

@app.callback(
    Output("type_graph", "figure"),
    [Input("dropdown_player", "value")])
def update_roll_types(player):
    df_filtered = filter_df(player=player)

    data = df_filtered.groupby(['session','type']).count()['value'].reset_index(level=[0,1])
    totals = df_filtered.groupby(['session']).count()['value']
    data['Session'] = data['session'].map( lambda i: sessions[i])

    data['Roll%'] = data['value'] / data['session'].map(lambda x: totals[x]) * 100.

    fig = px.line(data, x='Session', y='Roll%', color="type", title='Roll Types' )
    return fig


def count_streak(vals):
    max_streak = 0
    current_streak = 0
    for val in vals:
        if val:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            current_streak = 0
    return max_streak


def get_stats(df_filtered, good_thresh, bad_thresh):
    bad_idx = df_filtered["value"] <= bad_thresh
    good_idx = df_filtered["value"] >= good_thresh
    return {
        'Num Rolls': len(df_filtered["value"]),
        'Average Roll': df_filtered["value"].mean(),
        'Bad Rolls': sum(bad_idx),
        'Worst Streak': count_streak(bad_idx),
        'Good Rolls': sum(good_idx),
        'Best Streak': count_streak(good_idx)
    }

@app.callback(
    Output("roll_table", "data"),
    [Input("dropdown_session", "value"),
     Input("dropdown_type", "value"),
     Input("input_good_roll", "value"),
     Input("input_bad_roll", "value")])
def update_roll_table(session, roll_type, good_thresh, bad_thresh):
    df_filtered = filter_df(session=session, roll_type=roll_type)

    data = []

    stats = get_stats(df_filtered, good_thresh, bad_thresh)
    stats['Player'] = OVERALL
    data.append(stats)
    for player in players:
        stats = get_stats(df_filtered[df_filtered['character'] == player], good_thresh, bad_thresh)
        stats['Player'] = player
        data.append(stats)

    return data

@app.callback(
    Output("roll_graph", "figure"),
    [Input("dropdown_player", "value"),
     Input("dropdown_type", "value"),
     Input("input_good_roll", "value"),
     Input("input_bad_roll", "value")])
def update_roll_graph(player, roll_type, good_thresh, bad_thresh):
    df_filtered = filter_df(player=player, roll_type=roll_type)

    stats = defaultdict(list)

    for session in df_filtered['session'].unique():
        stat = get_stats(df_filtered[df_filtered['session'] == session], good_thresh, bad_thresh)
        for k,v in stat.items():

            stats['Stat'].append(k)
            stats['Roll Count'].append(v)
            stats['Session'].append(sessions[session])

    stat_df = pd.DataFrame(stats)

    fig = px.line(stat_df, x='Session', y='Roll Count', color="Stat", title='Roll Graph' )
    return fig

if __name__ == "__main__":
    app.run_server(host='0.0.0.0', port=8181, debug=True)
