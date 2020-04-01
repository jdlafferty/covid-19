from flask import Flask, render_template, request

import json
import herepy
import plotly
import datetime
import dateutil.parser

import pandas as pd
import numpy as np

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
    return (df_recent, df_counties, most_recent_date_long)

df, df_counties, most_recent_date = process_most_recent_data()
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

    title_text = "Data from The New York Times<br>github.com/nytimes/covid-19-data<br>%s" % most_recent_date

    layout = dict(
        width = 1400,
        height = 800,
        margin={"r":0,"t":0,"l":0,"b":0},
        showlegend = False,
        title = dict(
            text = title_text,
            y = 0.05,
            x = 0.85,
            xanchor = 'left',
            yanchor = 'bottom',
            font=dict(
                family="Times New Roman",
                size=10,
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


def histograms_for_address(addr,max_to_show=20):
    this_lat, this_lon = lat_lon_of_address(addr)
    this_county, this_state = county_state_of_address(addr)
    df_county = df_counties[(df_counties['county']==this_county) & (df_counties['state']==this_state)]
    df_county = df_county.tail(max_to_show)
    county_name = "%s County, %s" % (this_county, this_state)

    dates = list(df_county['date'])
    cases = list(df_county['cases'])
    deaths = list(df_county['deaths'])
    num_entries = len(dates)

    cases_dict = dict(
        data = [dict(type = 'bar',
            name = 'cases',
            x = dates,
            y = cases,
            marker = dict(
                color = 'rgba(255,0,0,0.5)'
            )),
            dict(type = 'bar',
                    name = 'cases',
                    x = dates,
                    y = deaths,
                    marker = dict(
                        color = 'rgba(55,55,55,0.5)'
                    ))
        ],
        layout = dict(
            height = 200,
            width = num_entries*15,
            margin={"r":0,"t":0,"l":0,"b":0},
            barmode='stack',
            showlegend=False,
            yaxis=dict(tickformat=',d'),
            font=dict(
                family="Times New Roman",
                size=20,
                color="#7f7f7f"),
            )
    )
    deaths_dict = dict(
        data = [dict(type = 'bar',
            name = 'deaths',
            x = dates,
            y = deaths,
            marker = dict(
                color = 'rgba(55,55,55,0.5)'
            )),
            dict(type = 'bar',
                    name = 'deaths',
                    x = dates,
                    y = deaths,
                    marker = dict(
                        color = 'rgba(55,55,55,0.5)'
                    ))
        ],
        layout = dict(
            height = 100,
            width = num_entries*15,
            margin={"r":0,"t":0,"l":0,"b":0},
            showlegend=False,
            barmode='stack',
            yaxis=dict(tickformat=',d'),
            font=dict(
                family="Times New Roman",
                size=20,
                color="#7f7f7f"),
            )
    )

    return (cases_dict, deaths_dict, county_name)

addr = 'Emerald Street, Corpus Christi, TX'

# run flask server
app = Flask(__name__)
app.debug = True

@app.route('/')
def index():
  addr = request.args.get('address')
  print(addr)
  data, layout = prepare_data_layout(df, addr)
  map_dict = dict(data=data, layout=layout)
  if (addr != None):
      cases_dict, deaths_dict, county_name = histograms_for_address(addr)
      graphs = [map_dict, cases_dict, deaths_dict]
      ids = ['map', 'Cases in %s' % county_name, 'Deaths in %s' % county_name]
  else:
      graphs = [map_dict]
      ids = ['map']
  graphs_json = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
  return render_template('3graphs.html', ids=ids, graphs_json=graphs_json)
