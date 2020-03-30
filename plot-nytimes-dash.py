import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import pandas as pd
import plotly.graph_objs as go

import numpy as np
import json
import herepy
import datetime
import dateutil.parser

# initial geocoder and read in NYTimes data
geocoderApi = herepy.GeocoderApi('VbY-MyI6ZT9U8h-Y5GP5W1YaOzQuvNnL4aSTulNEyEQ')
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

df_geo = pd.read_csv("https://raw.githubusercontent.com/jdlafferty/covid-19/master/geo-counties.csv", dtype={"fips": str})
df_recent = pd.merge(df_recent, df_geo)

def render_map(min_cases=1, scale=3.0):
    df = df_recent

    df['text'] = df['county'] + ', ' + df['state'] + '<br>' + \
        (df['cases']).astype(str) + ' cases, ' + (df['deaths']).astype(str) + ' deaths'
    df_top = df[df['cases'] >= min_cases]
    df_top = df_top[df_top['county']!='Unknown']

    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
        locationmode = 'USA-states',
        lon = df_top['lon'],
        lat = df_top['lat'],
        text = df_top['text'],
        name = '',
        marker = dict(
            size = df_top['cases']/scale,
            color = 'rgba(255, 0, 0, 0.2)',
            line_color='black',
            line_width=0.5,
            sizemode = 'area'
        ),
    ))

    fig.update_layout(
            width = 1500,
            height = 900,
            margin={"r":0,"t":0,"l":0,"b":0},
            showlegend = False,
            geo = dict(
                scope = 'usa',
                landcolor = 'rgb(230, 230, 230)',
            )
    )
    return(fig)


def render_map_with_address(addr=None, scale=3.0):
    fig = render_map()

    this_lat, this_lon = lat_lon_of_address(addr)
    this_county, this_state = county_state_of_address(addr)
    county_record = df_recent[(df_recent['county']==this_county) & (df_recent['state']==this_state)]
    this_text = '%s<br>County: %s' % (addr, np.array(county_record['text'])[0])

    td = pd.DataFrame()
    td['lat']=np.array([this_lat])
    td['lon']=np.array([this_lon])
    td['text']=np.array([this_text])
    fig.add_trace(go.Scattergeo(
        locationmode = 'USA-states',
        lon = td['lon'],
        lat = td['lat'],
        text = td['text'],
        name = '',
        marker = dict(
            size = 100/scale,
            color = 'rgba(0,255,0,0.2)',
            line_color='black',
            line_width=0.5,
            sizemode = 'area'
        ),
    ))

    fig.update_layout(
            width = 1500,
            height = 900,
            margin={"r":0,"t":0,"l":0,"b":0},
            showlegend = False,
            geo = dict(
                scope = 'usa',
                landcolor = 'rgb(230, 230, 230)',
            )
    )

    fig.update_layout(
        title={
            'text': "Data from The New York Times<br>https://github.com/nytimes/covid-19-data<br>%s" % most_recent_date_long,
            'y':0.05,
            'x':0.80,
            'xanchor': 'left',
            'yanchor': 'bottom'},
       font=dict(
            family="Times New Roman",
            size=8,
            color="#7f7f7f")
    )
    return(fig)

# create the map
fig = render_map_with_address('Emerald St, Corpus Christi, TX')

# Launch the application and create layout
app = dash.Dash()
app.layout = html.Div([
                # add the plot
                dcc.Graph(id = 'plot', figure = fig),
                ])

# start the server
if __name__ == '__main__':
    app.run_server(debug = True)
