
import json
import herepy
import plotly
import datetime
import dateutil.parser
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# initial geocoder and read in NYTimes data
geocoderApi = herepy.GeocoderApi('VbY-MyI6ZT9U8h-Y5GP5W1YaOzQuvNnL4aSTulNEyEQ')

def lat_lon_of_address(addr):
    response = geocoderApi.free_form(addr)
    result = response.as_json_string()
    res = eval(result)
    (lat, lon) = (res['Response']['View'][0]['Result'][0]['Location']['DisplayPosition']['Latitude'],
                  res['Response']['View'][0]['Result'][0]['Location']['DisplayPosition']['Longitude'])
    return (lat, lon)

def county_state_of_address(addr):
    response = geocoderApi.free_form(addr)
    result = response.as_json_string()
    res = eval(result)
    state = res['Response']['View'][0]['Result'][0]['Location']['Address']['AdditionalData'][1]['value']
    county = res['Response']['View'][0]['Result'][0]['Location']['Address']['AdditionalData'][2]['value']
    return (county, state)

def process_most_recent_data():
    last_date = max([dateutil.parser.parse(d) for d in np.array(df_counties['date'])])
    most_recent_date = last_date.strftime("%Y-%m-%d")
    most_recent_date_long = last_date.strftime("%A %B %-d, %Y")
    print("covid19: Most recent NY Times data: %s" % most_recent_date_long)

    df_recent = df_counties[df_counties['date']==most_recent_date]
    df_recent = df_recent.sort_values('cases', ascending=False)
    df_recent = df_recent.reset_index().drop('index',1)

    df_recent = pd.merge(df_recent, df_geo)
    df_recent = pd.merge(df_recent, df_census, how='left', on=['county','state'])
    df_recent = df_recent[df_recent['county'] != 'Unknown']
    df_recent['population'] = np.array(df_recent['population'], dtype='int')

    cases = np.array(df_recent['cases'])
    population = np.array(df_recent['population'])
    cases_per_100k = np.round(100000*np.array(cases/population),1)
    df_recent['cases_per_100k'] = cases_per_100k

    return (df_recent, most_recent_date_long)


def process_data(date_str):
    date = dateutil.parser.parse(date_str)
    this_date = date.strftime("%Y-%m-%d")
    this_date_long = date.strftime("%B %-d, %Y")
    print("covid19: Processing NY Times data for %s" % this_date_long)

    df_recent = df_counties[df_counties['date']==this_date]
    df_recent = df_recent.sort_values('cases', ascending=False)
    df_recent = df_recent.reset_index().drop('index',1)

    df_recent = pd.merge(df_recent, df_geo)
    df_recent = pd.merge(df_recent, df_census, how='left', on=['county','state'])
    df_recent = df_recent[df_recent['county'] != 'Unknown']
    df_recent['population'] = np.array(df_recent['population'], dtype='int')

    cases = np.array(df_recent['cases'])
    population = np.array(df_recent['population'])
    cases_per_100k = np.round(100000*np.array(cases/population),1)
    df_recent['cases_per_100k'] = cases_per_100k

    return (df_recent, this_date, this_date_long)


def get_location_of_address(addr, df):
    try:
        response = geocoderApi.free_form(addr)
        result = response.as_json_string()
        res = eval(result)
        (lat, lon) = (res['Response']['View'][0]['Result'][0]['Location']['DisplayPosition']['Latitude'],
            res['Response']['View'][0]['Result'][0]['Location']['DisplayPosition']['Longitude'])
        state = res['Response']['View'][0]['Result'][0]['Location']['Address']['AdditionalData'][1]['value']
        county = res['Response']['View'][0]['Result'][0]['Location']['Address']['AdditionalData'][2]['value']
        if df[(df['county']==county) & (df['state']==state)].shape[0] == 0:
            raise Exception('InvalidStateCounty')
        return ((lat, lon), (county, state))
    except:
        raise Exception('InvalidAddress')

def plot_cases_for_addr(addr, color='r', alpha=.5, savePath=None, show=False):
    try:
        ((lat, lon), (county, state)) = get_location_of_address(addr, df_counties)
        df_county = df_counties[(df_counties['county']==county) & ((df_counties['state']==state))]
        dates = list(df_county['date'])
        dates = [dateutil.parser.parse(d) for d in dates]
        dates = [d.strftime("%B %-d") for d in dates]
        cases = list(df_county['cases'])

        fig = plt.figure()
        fig.suptitle('Cases in %s County, %s' % (county, state), fontsize=14)
        plt.xlabel('')
        plt.ylabel('')
        plt.xticks([0, len(cases)/2, len(cases)-1], rotation='horizontal', fontsize=12)
        plt.bar(x=dates, height=cases, color='r', alpha=alpha)

        if savePath != None:
            filename = savePath + '/' + "%s,%s.png" % (county, state)
            plt.savefig(filename, dpi=300)

        if not(show):
            plt.close(fig)
        if savePath != None:
            return filename
        else:
            return None

    except Exception as e:
        print(e)


def prepare_data_layout(df, address=None, mark='cases', min_cases=1, scale=3.0):
    df['text'] = df['county'] + ', ' + df['state'] + '<br>' + \
        (df['cases']).astype(str) + ' cases, ' + (df['deaths']).astype(str) + ' deaths<br>' + \
        (df['cases_per_100k']).astype(str) + ' cases per 100k people'
    df = df[df['cases'] >= min_cases]
    df = df[df['county']!='Unknown']
    df['type'] = np.zeros(len(df))

    if address != None:
        try:
            ((this_lat, this_lon), (this_county, this_state)) = get_location_of_address(address, df)
            county_record = df[(df['county']==this_county) & (df['state']==this_state)]
            this_text = '%s<br>County: %s' % (address, np.array(county_record['text'])[0])
            td = pd.DataFrame(county_record)
            cases = np.array([10000])
            population = np.array(county_record['population'])
            td['cases'] = cases
            cases_per_100k = np.round(100000*np.array(cases/population),1)
            td['cases_per_100k'] = cases_per_100k
            td['text'] = [this_text]
            td['type'] = [1]
            df = df.append(td)
        except:
            print("Invalid address: " + address)

    colors = ['rgba(255,0,0,0.2)', 'rgba(0,255,0,0.2)']
    if mark=='cases':
        sizes = df['cases']/scale
    else:
        sizes = df['cases_per_100k']/scale

    data = [dict(type = 'scattergeo',
            locationmode = 'USA-states',
            lon = df['lon'],
            lat = df['lat'],
            text = df['text'],
            marker = dict(
                size = sizes,
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

df_counties = pd.read_csv("https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv", dtype={"fips": str})
df_states = pd.read_csv("https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv", dtype={"fips": str})
df_geo = pd.read_csv("https://raw.githubusercontent.com/jdlafferty/covid-19/master/data/geo-counties.csv", dtype={"fips": str})
df_census = pd.read_csv("https://raw.githubusercontent.com/jdlafferty/covid-19/master/data/county_2019_census.csv")
df, most_recent_date = process_most_recent_data()
