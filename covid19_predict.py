import pandas as pd
import numpy as np
import covid19 as cvd
import datetime
import dateutil.parser
import matplotlib.pyplot as plt


def process_recent_data(days_back=7):
    date = [dateutil.parser.parse(d) for d in np.array(cvd.df_counties['date'])]
    last_date = max(date)
    most_recent_date_long = last_date.strftime("%A %B %-d, %Y")

    days = np.array([(last_date - d).days for d in date])
    df_recent = cvd.df_counties[days < days_back]
    df_recent = df_recent.sort_values('cases', ascending=False)
    df_recent = df_recent.reset_index().drop('index', 1)

    df_recent = pd.merge(df_recent, cvd.df_geo)
    df_recent = pd.merge(df_recent, cvd.df_census,
                         how='left', on=['county', 'state'])
    df_recent = df_recent[df_recent['county'] != 'Unknown']
    df_recent['population'] = np.array(df_recent['population'], dtype='int')

    cases = np.array(df_recent['cases'])
    population = np.array(df_recent['population'])
    cases_per_100k = np.round(100000*np.array(cases/population), 1)
    df_recent['cases_per_100k'] = cases_per_100k

    return (df_recent, most_recent_date_long)


def compute_deltas(df, days_back=30):
    nd = pd.DataFrame()
    counties = list(df['county'])
    states = list(df['state'])
    state_county = set([sc for sc in zip(states, counties)])
    for (state, county) in state_county:
        this_county = pd.DataFrame(df[(df['county']==county) & (df['state']==state)])
        cp100k = np.array(this_county['cases_per_100k'])
        delta = np.append(np.maximum(-np.diff(cp100k), 0), np.nan)
        this_county['delta'] = delta
        nd = nd.append(this_county)

    date = [dateutil.parser.parse(d) for d in np.array(nd['date'])]
    last_date = max(date)
    days = np.array([(last_date - d).days for d in date])
    nd = nd[days < days_back]
    nd = nd.sort_values(['cases', 'state', 'county'], ascending = (False, True, True))
    return nd


def initialize_for_simulation(df_delta):
    print('covid19_predict: initializing for simulation')
    df = df_delta.drop(['lat', 'lon', 'fips'], axis=1)
    df = df[df['delta'] > 0]
    df = pd.DataFrame(df)
    df['z'] = np.log(np.array(df['delta'])/1e5) - np.log(1-np.array(df['delta'])/1e5)
    df['psi'] = df['z']
    df['var'] = 1/(np.array(df['delta'])*(1-np.array(df['delta'])/1e5))
    df['d'] = 1/(1+1/np.array(df['var']))
    df = df.reset_index().drop('index', 1)
    return df

def run_gibbs_sampler(df, B=10000, burn=1000):
    k = df.shape[0]
    v = np.sqrt(1/k)
    n = df.shape[0]
    print('covid19_predict: running Gibbs sampler: n=%d, B=%d' % (n, B))
    psi = np.matrix(np.zeros(n*B)).reshape((B, n))
    psi[0, :] = df['psi']
    scale = np.sqrt(df['d'])
    for b in np.arange(B-1):
        loc = np.mean(psi[b, :])
        mu = np.random.normal(loc=loc, scale=v)
        e = df['d']*(mu + df['z']/df['var'])
        psi[b+1, :] = np.random.normal(loc=e, scale=scale)
    return psi[np.arange(burn, B), :]


def make_predictions(df, psi):
    # compute posterior and mean and credible interval
    print('covid19_predict: making predictions')
    psi_95 = np.percentile(psi, 95, axis=0)
    psi_05 = np.percentile(psi, 5, axis=0)
    psi_bar = np.array(np.mean(psi, axis=0))[0]
    delta_bar = 1e5*np.exp(psi_bar)/(1+np.exp(psi_bar))
    delta_95 = 1e5*np.exp(psi_95)/(1+np.exp(psi_95))
    delta_05 = 1e5*np.exp(psi_05)/(1+np.exp(psi_05))
    df['delta_bar'] = np.round(delta_bar, 2)
    df['delta_95'] = np.round(delta_95, 2)
    df['delta_05'] = np.round(delta_05, 2)
    df = df.drop(['z', 'psi', 'd', 'var'], axis=1)

    date = [dateutil.parser.parse(d) for d in np.array(df['date'])]
    most_recent_date = max(date).strftime("%Y-%m-%d")
    df = df[df['date'] == most_recent_date]

    # make Bayes predictions for the most recent date
    cases_predicted = (df['population']/100000)*(df['cases_per_100k']+df['delta_bar'])
    cases_predicted = cases_predicted.astype(int)
    df['cases_predicted'] = cases_predicted
    cases_95_credible = (df['population']/100000)*(df['cases_per_100k']+df['delta_95'])
    cases_95_credible = cases_95_credible.astype(int)
    cases_05_credible = (df['population']/100000)*(df['cases_per_100k']+df['delta_05'])
    cases_05_credible = cases_05_credible.astype(int)
    df['cases_95_credible'] = cases_95_credible
    df['cases_05_credible'] = cases_05_credible

    return df



def plot_predictions_for_addr(addr, days_back=21, days_ahead=3, color='r', opacity=.6,
                              savePath=None, show=False):
    try:
        ((lat, lon), (county, state)) = cvd.get_location_of_address(addr, cvd.df_counties)
        df_county = cvd.df_counties[(cvd.df_counties['county']==county) & ((cvd.df_counties['state']==state))]
        dates = list(df_county['date'])
        dates = [dateutil.parser.parse(d) for d in dates]
        latest_date = max(dates)
        dates = [d.strftime("%B %-d") for d in dates]
        cases = list(df_county['cases'])

        this_df = df[(df['county']==county) & ((df['state']==state))]
        dates1 = [dates[d] for d in np.arange(max(0,len(dates)-days_back), len(dates))]
        cases1 = [cases[d] for d in np.arange(max(0,len(dates)-days_back), len(dates))]

        next_dates = [latest_date + datetime.timedelta(days=i) for i in range(1, days_ahead+1)]
        dates2 = [d.strftime("%B %-d") for d in next_dates]
        cases2 = [int((this_df['population']/100000)*(this_df['cases_per_100k'] + i*this_df['delta_bar']))
                      for i in range(1,days_ahead+1)]
        up = [float((this_df['population']/100000)*this_df['delta_95']) for i in range(1,days_ahead+1)]
        dn = [float((this_df['population']/100000)*this_df['delta_05']) for i in range(1,days_ahead+1)]
        std = np.array([dn, up])

        fig, ax = plt.subplots(figsize=(7,5))
        cases_plt = plt.bar(x=dates1, height=cases1, color='r', alpha=opacity, label='cases')
        preds_plt = plt.bar(x=dates2, height=cases2, color='r', alpha=.3, label='predicted')
        err_plt = plt.errorbar(x=dates2, y=cases2, yerr=std, fmt='none', elinewidth=.75, capsize=1)
        fig.suptitle('%s County, %s' % (county, state), fontsize=18)
        plt.xlabel('')
        plt.ylabel('')
        plt.xticks([0, (len(dates1)-1)/2, len(dates1)-1], fontsize=14)
        plt.legend(loc='upper left', frameon=False)

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

df_recent, recent_date = process_recent_data(days_back=7)
df_delta = compute_deltas(df_recent, days_back=3)
df = initialize_for_simulation(df_delta)
psi = run_gibbs_sampler(df)
df = make_predictions(df, psi)
