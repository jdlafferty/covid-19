## Mapping the New York Times Data

This notebook is a first attempt to pull and plot the Covid-19 data collected by the New York Times.
See [The Times github repository](https://github.com/nytimes/covid-19-data).

I render the plot using a [plotly](https://plotly.com/python/) style that is very similar to that used in the [maps published on the Times site](https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html). I add an interface that allows a user to type in an address, and show the most recent Covid-19 statistics of the US county of that address. The idea is to allow people to get an idea of what's going on nearby family and friends, without having to know what county they live in. This uses a geocoding API from [HERE.com](https://www.here.com/).

Next, I'd like to add timelines and forecasts of the cases and deaths over the coming days, incorporating some basic statistical modelling. 

John Lafferty<br>3-20-20
