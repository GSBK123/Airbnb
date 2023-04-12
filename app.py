import base64
import io
import json

import folium
import matplotlib.pyplot as plt
import pandas as pd
import plotly
import plotly.graph_objs as go
import requests
import xgboost as xgb
from flask import Flask, render_template, request, jsonify
from folium.plugins import FastMarkerCluster
from geopy.distance import great_circle
from sklearn import preprocessing
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from yellowbrick.regressor import ResidualsPlot

app = Flask(__name__)

# this is to find columns required for clustering
df_entire = pd.read_csv('listings.csv')
oneHotColumns = ['room_type']
requiredColummns = oneHotColumns + ['name', 'latitude', 'longitude', 'price']
jsonData = []


if __name__ == '__main__':
    app.run(debug=True)


class MainClass:
    def __init__(self):
        self.cleaned_df = pd.read_csv("cleaned_df.csv")


class PricePrediction:
    def __init__(self):
        self.preprocessed_df = pd.read_csv("preprocessed_df.csv")


main_class_obj = MainClass()
# **************************************************** Dashboard page **************************************************


# route for home page
@app.route('/', methods=['GET'])
def render_home():
    neighbourhood_groups = []
    neighborhoods = []
    # accessing cleaned csv file
    df = main_class_obj.cleaned_df
    lats2019 = df['latitude'].tolist()
    lons2019 = df['longitude'].tolist()
    locations = list(zip(lats2019, lons2019))

    # generating folium map with fast marker clusters using latitudes and longitudes
    map1 = folium.Map(location=[55.585901, -105.750596], zoom_start=3.3)
    FastMarkerCluster(data=locations).add_to(map1)

    # saving the html to render it on webpage
    map1.save(outfile="./static/dashboard-map5.html")
    return render_template('index.html', neighbourhood_groups=neighbourhood_groups, neighborhoods=neighborhoods)

# ****************************************************** Trends page ***************************************************


# route for trends page
@app.route('/Trends', methods=['GET'])
def render_trends():
    df = main_class_obj.cleaned_df
    # fill drop downs for default option "New Brunswick"
    provinces = df.province.unique()
    x = "bedrooms"
    y = "room_type"
    dfg = df[df.province == provinces[0]]

    # generate plot for default options
    plot_generated = get_plot(df, dfg, x, y, provinces[0])
    return render_template('trends.html', provinces=provinces, plot=plot_generated)


# this is to generate plot for selected user parameters
def get_plot(df, dfg, x, y, selected_province):
    y_values = list(getattr(df, y).unique())
    x_values = list(getattr(df, x).unique())
    dataa = []
    for val in y_values:
        df_temp = dfg[(getattr(dfg, y)) == val]
        ls = []
        for r in x_values:
            ls.append(len(df_temp[getattr(dfg, x) == r]))
        item = go.Bar(name=str(val), x=x_values, y=ls)
        dataa.append(item)
    fig = go.Figure(data=dataa)
    y_title = 'Number of Airbnbs by ' + y
    plot_title = "Number of Airbnbs by " + x + " and " + \
        y + " parameters of " + selected_province
    # Change the bar mode
    fig.update_layout(barmode='stack', title=plot_title, width=1100, height=500,
                      xaxis_title=x,
                      yaxis_title=y_title)
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graph_json


# route to generate chart in runtime using the selected parameters
@app.route('/GenerateChart', methods=['GET', 'POST'])
def generate_plot():
    selected_province = request.form.get('provinceID')
    x = request.form.get('xParams')
    y = request.form.get('yParams')
    df = main_class_obj.cleaned_df
    provinces = df.province.unique()
    dfg = df[df.province == selected_province]

    # generate plot
    plot_generated = get_plot(df, dfg, x, y, selected_province)
    return render_template('trends.html', plot=plot_generated, provinces=provinces, sel_x=x, sel_y=y,
                           sel_province=selected_province)

# ************************************************ Find Airbnbs page ***************************************************

# to land on to Find airbnbs page with default options


@app.route('/FindAirbnbs', methods=['GET'])
def render_airbnbs():
    provinces = []
    neighborhoods = []
    df = main_class_obj.cleaned_df
    # fill drop downs for default option "New Brunswick"
    provinces = df.province.unique()

    # filtering province
    p_df = df.loc[df.province == provinces[0]]
    neighborhoods = p_df.neighbourhood.unique()

    # filtering neighbourhood
    n_df = p_df.loc[p_df.neighbourhood == neighborhoods[0]]
    roomtypes = n_df.room_type.unique()

    # filtering room type
    r_df = n_df[(n_df.room_type == roomtypes[0])]

    # generate folium map using default options
    response_map = generate_marker_latlong(r_df)
    return render_template('find-airbnbs.html', provinces=provinces, neighborhoods=neighborhoods, roomtypes=roomtypes, response_map=response_map)


# this is to generate folium map using list of airbnbs
def generate_marker_latlong(r_df):
    latitudes_list = list(r_df.latitude)
    longitudes_list = list(r_df.longitude)
    map2 = folium.Map(location=[latitudes_list[0], longitudes_list[0]],
                      zoom_start='12', width='100%', height='75%')
    for index, row in r_df.iterrows():
        tooltip = 'Click here to know more!'
        pop_string = "<b>Name: </b>" + str(row['name']) + "<br><br>" + \
                     "<b>Minimum nights: </b>" + str(row['minimum_nights']) + "<br><br>" + \
                     "<b>Ratings: </b>" + str(row['ratings']) + "<br><br>" + \
                     "<b>Bedrooms: </b>" + str(row['bedrooms']) + "<br><br>" + \
                     "<b>Bathrooms: </b>" + str(row['bathrooms']) + "<br><br>" + \
                     "<b>Amenities: </b>" + str(row['amenities'])
        folium.Marker([row['latitude'], row['longitude']], icon=folium.Icon(color='red', icon='map-marker'),
                      popup=pop_string, tooltip=tooltip).add_to(map2)
    return map2


# this is to generate map using selected user options runtime
@app.route('/GenerateMarkers', methods=['GET', 'POST'])
def generate_markers():
    selected_province = request.form.get('provinceID')
    selected_neighbourhood = request.form.get('neighbourhoods')
    selected_roomtype = request.form.get('roomtypes')

    output = get_filtered_df()
    r_df = output[0]
    provinces = output[1]
    neighborhoods = output[2]
    roomtypes = output[3]
    response_map = generate_marker_latlong(r_df)
    return render_template('find-airbnbs.html', provinces=provinces, neighborhoods=neighborhoods, roomtypes=roomtypes, response_map=response_map, sel_province=selected_province, sel_neighbourhood=selected_neighbourhood,
                           sel_roomtype=selected_roomtype)


# get filtered options based on selected user parameters
def get_filtered_df():
    df = main_class_obj.cleaned_df

    selected_province = request.form.get('provinceID')
    selected_neighbourhood = request.form.get('neighbourhoods')
    selected_roomtype = request.form.get('roomtypes')

    provinces = df.province.unique()

    # filtering province
    p_df = df.loc[df.province == selected_province]
    neighborhoods = p_df.neighbourhood.unique()

    # filtering neighbourhood
    n_df = p_df.loc[p_df.neighbourhood == selected_neighbourhood]
    roomtypes = n_df.room_type.unique()

    # filtering room type
    r_df = n_df[(n_df.room_type == selected_roomtype)]
    return r_df, provinces, neighborhoods, roomtypes


# handling Ajax request and response to take user selected province and provide corresponding neighbourhoods
@app.route('/get_neighbourhood/<provinceID>')
def get_neighbourhood(provinceID):
    df = main_class_obj.cleaned_df
    p_df = df.loc[df.province == provinceID]
    neighborhoods = list(p_df.neighbourhood.unique())
    return jsonify(neighborhoods)


# handling Ajax request and response to take user selected neighborhood and provide corresponding room types available
@app.route('/get_roomtypes/<neighbourhoodID>')
def get_roomtypes(neighbourhoodID):
    df = main_class_obj.cleaned_df
    p_df = df.loc[df.neighbourhood == neighbourhoodID]
    roomtypes = list(p_df.room_type.unique())
    return jsonify(roomtypes)

# *********************************************** Predict price page ***************************************************


# this is to fill dropdowns in predict price page using preprocessed df
@app.route('/PricePrediction', methods=['GET'])
def render_price_prediction():
    # get pre processed df
    price_prediction_obj = PricePrediction()
    ndf = price_prediction_obj.preprocessed_df

    # fill dropdowns
    provinces = ndf.province.unique()
    accommodates = sorted(ndf.accommodates.unique())
    bedrooms = sorted(ndf.bedrooms.unique())
    minimum_nights = sorted(ndf.minimum_nights.unique())
    return render_template('predict-price.html', provinces=provinces, accommodates=accommodates, bedrooms=bedrooms,
                           minimum_nights=minimum_nights, plot_generated_neigh='NA', plot_generated_room='NA', price='')


# this is to perform price prediction functionality on click of predict price button
@app.route('/PredictPrice', methods=['GET', 'POST'])
def predict_price():
    # to refill the dropdown values
    price_prediction_obj = PricePrediction()
    ndf = price_prediction_obj.preprocessed_df
    provinces = ndf.province.unique()
    accommodates = sorted(ndf.accommodates.unique())
    bedrooms = sorted(ndf.bedrooms.unique())
    minimum_nights = sorted(ndf.minimum_nights.unique())

    # to predict the price
    selected_province = request.form.get('provinceID')
    selected_neighbourhood = request.form.get('neighbourhoodID')
    selected_roomtype = request.form.get('roomtypeID')
    selected_accommodates = request.form.get('accommodateID')
    selected_bedrooms = request.form.get('bedroomsID')
    selected_min_nights = request.form.get('minimumID')

    # filtering province
    p_df = ndf.loc[ndf.province == selected_province]
    neighborhoods = p_df.neighbourhood.unique()
    sel_neighbourhood = selected_neighbourhood

    # filtering neighbourhood
    n_df = p_df.loc[p_df.neighbourhood == selected_neighbourhood]
    roomtypes = n_df.room_type.unique()
    sel_roomtype = selected_roomtype

    # label encode provinces
    label_encoder = preprocessing.LabelEncoder()
    label_encoder.fit(ndf['province'])
    le_province_mapping = dict(
        zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))
    selected_province = le_province_mapping[str(selected_province)]
    ndf['province'] = label_encoder.transform(ndf['province'])

    # label encode room types
    label_encoder = preprocessing.LabelEncoder()
    label_encoder.fit(ndf['room_type'])
    le_room_type_mapping = dict(
        zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))
    selected_roomtype = le_room_type_mapping[selected_roomtype]
    ndf['room_type'] = label_encoder.transform(ndf['room_type'])

    # label encode neighbourhoods
    label_encoder = preprocessing.LabelEncoder()
    label_encoder.fit(ndf['neighbourhood'])
    le_neighbourhood_mapping = dict(
        zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))
    selected_neighbourhood = le_neighbourhood_mapping[selected_neighbourhood]
    ndf['neighbourhood'] = label_encoder.transform(ndf['neighbourhood'])

    data = {}
    tdf = pd.DataFrame(data)

    # filter dataframe using selected user parameters
    neighbourhood_list = (
        ndf[ndf.province == selected_province].neighbourhood.unique())
    # for all other neighborhoods along with selected neighborhood
    for val in neighbourhood_list:
        data = {'neighbourhood': [val], 'province': [selected_province], 'room_type': [selected_roomtype],
                'accommodates': [int(selected_accommodates)]}
        tdf = tdf.append(pd.DataFrame(data), ignore_index=True)

    # for all other roomtypes along with selected roomtype
    for val in roomtypes:
        if val != sel_roomtype:
            data = {'neighbourhood': [selected_neighbourhood], 'province': [selected_province],
                    'room_type': [le_room_type_mapping[val]], 'accommodates': [int(selected_accommodates)]}
            tdf = tdf.append(pd.DataFrame(data), ignore_index=True)

    # handling optional parameters - minimum_nights, bedrooms
    sel_min = ''
    sel_bedrooms = ''
    if selected_bedrooms != 'b0' and selected_min_nights != 'm0':
        tdf['minimum_nights'] = int(selected_min_nights)
        tdf['bedrooms'] = int(selected_bedrooms)
        sel_min = int(selected_min_nights)
        sel_bedrooms = int(selected_bedrooms)

    elif selected_bedrooms != 'b0' and selected_min_nights == 'm0':
        tdf['bedrooms'] = int(selected_bedrooms)
        sel_bedrooms = int(selected_bedrooms)

    elif selected_bedrooms == 'b0' and selected_min_nights != 'm0':
        tdf['minimum_nights'] = int(selected_min_nights)
        sel_min = int(selected_min_nights)

    # performing XgBoost
    xgb_reg = xgb.XGBRegressor(max_depth=5, min_child_weight=24)

    # to plot regression line
    img2 = io.BytesIO()
    d = ndf[ndf.price <= 200]
    d_X_train, d_X_test, d_y_train, d_y_test = train_test_split(d.loc[:, d.columns != 'price'], d.price, test_size=0.3,
                                                                random_state=10)
    xgb_reg = xgb.XGBRegressor(max_depth=5, min_child_weight=24)
    xgb_reg.fit(d_X_train, d_y_train)
    y_pred = xgb_reg.predict(d_X_test)
    fig, ax = plt.subplots()
    ax.scatter(d_y_test, y_pred, edgecolors=(0, 0, 0))
    ax.plot([d_y_test.min(), d_y_test.max()], [
            d_y_test.min(), d_y_test.max()], 'k--', lw=4)
    ax.set_xlabel('Actual')
    ax.set_ylabel('Predicted')
    ax.set_title("Actual price Vs Predicted Price")
    fig.savefig(img2, format='png')
    img2.seek(0)
    regression_line = 'data:image/png;base64,{}'.format(
        base64.b64encode(img2.getvalue()).decode())

    # Xgboost on only selected parameters to predict price
    xgb_reg = xgb.XGBRegressor(max_depth=5, min_child_weight=24)
    xgb_reg.fit(ndf[tdf.columns], ndf.price)
    tdf['price'] = xgb_reg.predict(tdf)
    output = tdf.loc[(tdf.neighbourhood == selected_neighbourhood) & (
        tdf.room_type == selected_roomtype), 'price'].iloc[0]

    # to generate feature importance plot
    img1 = io.BytesIO()
    features = list(ndf[tdf.columns])
    # features = ['neighbourhood', 'province', 'room_type',
    #             'accommodates', 'minimum_nights', 'bedrooms', 'price']
    regression_imp = xgb_reg.feature_importances_
    fig, ax = plt.subplots()
    ax.bar(range(len(regression_imp)), regression_imp,
           align='center', color='green')
    plt.xticks(range(len(regression_imp) + 1), features, rotation='horizontal')
    plt.title('Feature Importance')
    ax.set_ylabel('Importance')
    fig.savefig(img1, format='png')
    img1.seek(0)
    feature_importance_plot = 'data:image/png;base64,{}'.format(
        base64.b64encode(img1.getvalue()).decode())

    # to plot other neighbourhoods with similar price range
    ls1 = (tdf[(tdf.price <= output) & (tdf.room_type ==
           selected_roomtype)]).nlargest(5, "price")
    ls2 = (tdf[(tdf.price > output) & (tdf.room_type ==
           selected_roomtype)]).nsmallest(5, "price")
    ls = ls1.append(ls2)
    recommended_neighbourhoods = {}
    for row in ls.iterrows():
        for key, value in le_neighbourhood_mapping.items():
            if value == int(row[1].neighbourhood):
                recommended_neighbourhoods[key] = round(row[1].price, 2)
    plot_generated_neigh = get_price_plots(
        recommended_neighbourhoods, "Neighbourhood")

    # to plot for other room types
    recommended_roomtypes = {}
    ls = tdf.loc[(tdf.neighbourhood == selected_neighbourhood)]
    for row in ls.iterrows():
        for key, value in le_room_type_mapping.items():
            if value == int(row[1].room_type):
                recommended_roomtypes[key] = round(row[1].price, 2)
    plot_generated_room = get_price_plots(recommended_roomtypes, "Room type")

    return render_template('predict-price.html', provinces=provinces, neighbourhoods=neighborhoods,
                           roomtypes=roomtypes, accommodates=accommodates, bedrooms=bedrooms,
                           minimum_nights=minimum_nights, price=round(
                               output, 2),
                           recommended_neighbourhoods=recommended_neighbourhoods, plot_generated_neigh=plot_generated_neigh,
                           plot_generated_room=plot_generated_room, sel_province=request.form.get(
                               'provinceID'),
                           sel_neighbourhood=sel_neighbourhood, sel_roomtype=sel_roomtype, sel_min=sel_min,
                           sel_bedrooms=sel_bedrooms, sel_accommodates=int(
                               request.form.get('accommodateID')),
                           feature_importance_plot=feature_importance_plot,
                           regression_line=regression_line)


# this is to generate plots for other neighborhoods and other roomtypes
def get_price_plots(recommended, plot_type):
    x = list(recommended.keys())
    y = list(recommended.values())

    fig = go.Figure(data=[go.Bar(
        x=x, y=y,
        width=0.7,
        text=y,
        textposition='auto',
    )])

    if plot_type == 'Neighbourhood':
        fig.update_traces(marker_color='blue', marker_line_color='rgb(8,48,107)',
                          marker_line_width=0.3, opacity=0.8)
        fig.update_layout(title="Other neighbourhoods of similar price range:", width=1000, height=700,
                          xaxis_title=plot_type, yaxis_title="Price")

    if plot_type == "Room type":
        fig.update_traces(marker_color='crimson', marker_line_color='rgb(8,48,107)',
                          marker_line_width=0.3, opacity=0.8)
        fig.update_layout(title="If you want to go for any other room type:", width=600, height=700,
                          xaxis_title=plot_type, yaxis_title="Price")

    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graph_json

# *********************************************** Clustering page ***************************************************


# route to return clustering page
@app.route('/Clustering', methods=['GET'])
def render_clustering():
    return render_template('clustering.html')


# calculate the distance of given airbnb from point of interest location
def calcDistance(lat, lon, pointOfInterest):
    airbnb = (lat, lon)
    return great_circle(pointOfInterest, airbnb).km


# does one hot encoding using pandas get_dummies
def oneHotEncoding(dataFrame):
    ohe_df = dataFrame
    for column in oneHotColumns:
        temp_df = pd.get_dummies(ohe_df[column], prefix=column)
        ohe_df = ohe_df.drop(column, axis=1)
        ohe_df = pd.concat([ohe_df, temp_df], axis=1)
    return ohe_df


# construct distance matrix api url
def constructDistanceMatrixUrl(dataFrame, latitude, longitude):
    url = 'https://maps.googleapis.com/maps/api/distancematrix/json?'
    url += 'units=imperial'
    origin = ''
    for (index, row) in dataFrame.iterrows():
        if origin != '':
            origin += '|'
        origin += str(row['latitude']) + ',' + str(row['longitude'])
    url += '&origins=' + origin
    url += '&destinations=' + str(latitude) + ',' + str(longitude)
    url += '&key=AIzaSyDPfqXnMS3gq-kGceSKgBs1rcoaqYYVJag'
    return url


# function that clusters the nearest aibnbs.
def clusterData(latitude, longitude, pointOfInterest):
    df_entire = main_class_obj.cleaned_df
    timeList = []
    distanceList = []
    df = df_entire[requiredColummns]
    df['distance'] = df_entire.apply(lambda x: calcDistance(
        x.latitude, x.longitude, pointOfInterest), axis=1)
    df_sort = df.sort_values(by='distance', ascending=True).head(50)

    X = oneHotEncoding(df_sort[oneHotColumns])
    url = constructDistanceMatrixUrl(df_sort, latitude, longitude)
    response = requests.get(url)
    json_data = json.loads(response.text)
    for row in json_data['rows']:
        elements = row['elements']
        distanceList.append(elements[0]['distance']['value']/1000)
        timeList.append(elements[0]['duration']['value'])

    X['timeTaken'] = timeList
    X['distance'] = distanceList
    kmeans = KMeans(n_clusters=10, random_state=0).fit(X)
    pred = kmeans.predict(X)
    X['clusterId'] = pred

    df_cluster = pd.DataFrame(columns=[
                              'name', 'latitude', 'longitude', 'cluster', 'distance', 'timeTaken', 'price', 'roomType'])
    df_cluster['name'] = df_sort['name']
    df_cluster['latitude'] = df_sort['latitude']
    df_cluster['longitude'] = df_sort['longitude']
    df_cluster['roomType'] = df_sort['room_type']
    df_cluster['cluster'] = X['clusterId']
    df_cluster['distance'] = X['distance']
    df_cluster['timeTaken'] = X['timeTaken']
    df_cluster['price'] = df_sort['price']
    jsonData = df_cluster.to_json(orient='records')
    return jsonData


# this endpoint will be called when a user selects the point of interest
@app.route('/getData')
def get_data():
    latitude = request.args.get('lat')
    longitude = request.args.get('lng')
    latitude = float(latitude)
    longitude = float(longitude)
    pointOfInterest = (latitude, longitude)
    outputData = clusterData(latitude, longitude, pointOfInterest)
    # with open('json.json', 'w') as f:
    #     f.write(outputData)
    return outputData
