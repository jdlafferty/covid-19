import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.graph_objs as go

import numpy as np
import json
import herepy
import datetime
import dateutil.parser

# initial geocoder and read in NYTimes data
geocoderApi = herepy.GeocoderApi('VbY-MyI6ZT9U8h-Y5GP5W1YaOzQuvNnL4aSTulNEyEQ')

def lat_lon_of_address(addr):
    response = geocoderApi.free_form(addr)
    type(response)
    result = response.as_json_string()
    res = eval(result)
    (lat, lon) = (res['Response']['View'][0]['Result'][0]['Location']['DisplayPosition']['Latitude'],
                  res['Response']['View'][0]['Result'][0]['Location']['DisplayPosition']['Longitude'])
    return (lat, lon)

def county_state_of_address(addr):
    response = geocoderApi.free_form(addr)
    type(response)
    result = response.as_json_string()
    res = eval(result)
    state = res['Response']['View'][0]['Result'][0]['Location']['Address']['AdditionalData'][1]['value']
    county = res['Response']['View'][0]['Result'][0]['Location']['Address']['AdditionalData'][2]['value']
    return (county, state)

def process_most_recent_data():
    df_counties = pd.read_csv("https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv", dtype={"fips": str})
    df_states = pd.read_csv("https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv", dtype={"fips": str})

    # determine most recent update
    last_date = max([dateutil.parser.parse(d) for d in np.array(df_counties['date'])])
    most_recent_date = last_date.strftime("%Y-%m-%d")
    most_recent_date_long = last_date.strftime("%A %B %d, %Y")
    print("Most recent data: %s" % most_recent_date_long)

    # create data frames
    df_recent = df_counties[df_counties['date']==most_recent_date]
    df_recent = df_recent.sort_values('cases', ascending=False)
    df_recent = df_recent.reset_index().drop('index',1)

    df_geo = pd.read_csv("https://raw.githubusercontent.com/jdlafferty/covid-19/master/geo-counties.csv", dtype={"fips": str})
    df_recent = pd.merge(df_recent, df_geo)
    return (df_recent, most_recent_date_long)

df, most_recent_date = process_most_recent_data()
df.head()

def prepare_data_layout(df, address=None, min_cases=1, scale=3.0):
    df['text'] = df['county'] + ', ' + df['state'] + '<br>' + \
        (df['cases']).astype(str) + ' cases, ' + (df['deaths']).astype(str) + ' deaths'
    df = df[df['cases'] >= min_cases]
    df = df[df['county']!='Unknown']
    df['type'] = np.zeros(len(df))


    if address != None:
        this_lat, this_lon = lat_lon_of_address(address)
        this_county, this_state = county_state_of_address(address)
        county_record = df[(df['county']==this_county) & (df['state']==this_state)]
        this_text = '%s<br>County: %s' % (address, np.array(county_record['text'])[0])
        td = pd.DataFrame(county_record)
        td['cases'] = [10000]
        td['text'] = [this_text]
        td['type'] = [1]
        df = df.append(td)

    colors = ['rgba(255,0,0,0.2)', 'rgba(0,255,0,0.2)']

    data = [dict(type = 'scattergeo',
            locationmode = 'USA-states',
            lon = df['lon'],
            lat = df['lat'],
            text = df['text'],
            marker = dict(
                size = df['cases']/scale,
                color = pd.Series([colors[int(t)] for t in df['type']]),
                line = dict(width = 0.5, color = 'black'),
                sizemode = 'area'
            ))
        ]

    layout = dict(
        width = 1400,
        height = 800,
        margin={"r":0,"t":0,"l":0,"b":0},
        showlegend = False,
        title = dict(
            text = '',
            y = 0.20,
            x = 0.80,
            xanchor = 'left',
            yanchor = 'bottom',
            font=dict(
                family="Times New Roman",
                size=14,
                color="#7f7f7f"
            )
        ),
        geo = dict(
            scope = 'usa',
            showland = True,
            landcolor = 'rgb(240, 240, 240)'
        )
    )
    return (data, layout)

data, layout = prepare_data_layout(df)
fig = dict(data=data, layout=layout)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout  = html.Div(
    [dcc.Graph(id='graph', figure=fig),
     html.Div(
        [dcc.Input(id='input_address', value=None, type='text', maxLength=60, size='50'),
        html.Button(id='submit-button', type='submit', children='Submit address')],
        style=dict(display='flex', justifyContent='center'))
    ]
)

@app.callback(
    Output(component_id='graph', component_property='figure'),
    [Input(component_id='submit-button', component_property='n_clicks')],
    [State(component_id='input_address', component_property='value')],
)
def update_output_figure(clicks, input_value):
    data, layout = prepare_data_layout(df, input_value)
    fig = dict(data=data, layout=layout)
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
