var map, autocomplete, place;
var prevClusterId = -1, prevInfoWindow = -1, newSearch = true;
var marker_default, marker_cluster, marker_pin, marker_interest;
var clusterSet = new Set();
var clusterWiseMarker = {};

// initialise the markers with their respective icon
var initData = function() {
    marker_default = new google.maps.MarkerImage('../static/images/red-pin.png', new google.maps.Size(30, 30), null, null, new google.maps.Size(30, 30));
    marker_cluster = new google.maps.MarkerImage('../static/images/marker_cluster.png', new google.maps.Size(35, 35), null, null, new google.maps.Size(35, 35));
    marker_pin = new google.maps.MarkerImage('../static/images/blue-pin.png', new google.maps.Size(50, 50),null, null, new google.maps.Size(50, 50));
};

// initialise the google map
var initMap = function() {
    initData();
    var initialLocation = {
        lat: 46.5653,
        lng: -66.4619
    };
    map = new google.maps.Map(
        document.getElementById('mapid'), {
            zoom: 7,
            streetViewControl: false,
            center: initialLocation
        });
    autocomplete = new google.maps.places.Autocomplete((
        document.getElementById('autocomplete')), {});
    autocomplete.addListener('place_changed', onPlaceChanged);
};

// Listener function called when user enters the place of interest
var onPlaceChanged = function() {
    place= autocomplete.getPlace();
    if (place.geometry) {
        map.panTo(place.geometry.location);
        map.setZoom(15);
        clearMarkers();
        createPlaceOfInterest(place.geometry.location);
    } else {
        document.getElementById('autocomplete').placeholder = 'Enter place of interest';
    }
};

// create content for the marker pop-up.
// it has name of the airbnb, room-type, distance, time taken and price
var popContent = function(airbnbObj){
    return '<h5>'+airbnbObj.name+'</h5>'+
    '</br><span>Room type :</span>&nbsp;<span>'+airbnbObj.roomType+'</span>'+
    '</br><span>Distance :</span>&nbsp;<span>'+airbnbObj.distance+' km</span>'+
    '</br><span>Time taken :</span>&nbsp;<span>'+airbnbObj.timeTaken+' s</span>'+
    '</br><span>Price :</span>&nbsp;<span>'+airbnbObj.price+' CAD</span>'
};

// Sets the map on all markers in the array.
var clearMarkers = function () {
    if(newSearch){
        return;
    }
    clusterSet.forEach(clusterId=>{
        clusterWiseMarker[clusterId].forEach(marker => {
            marker.setMap(null);
        });
    });
    marker_interest.setMap(null);
}

// creates the place of interest and then gets the clustered data from the backend.
var createPlaceOfInterest = function(placeObj){
    newSearch = false;
    clusterDetails = $('#cluster-details');
    clusterDetails.empty();
    console.log(clusterDetails);
    marker_interest = new google.maps.Marker({
        position: {
            lat: placeObj.lat(),
            lng: placeObj.lng()
        },
        map: map,
        icon: marker_pin
    });

    $.get("/getData?lat="+placeObj.lat()+"&lng="+placeObj.lng(), function(data, status){
        clusterSet = new Set();
        clusterWiseMarker = {};

        var jsonData = JSON.parse(data);
        jsonData.forEach(data => {

            if (!clusterSet.has(data.cluster)) {
                clusterSet.add(data.cluster);
                clusterWiseMarker[data.cluster] = [];
            }
            var clusterId = data.cluster;

            var marker = new google.maps.Marker({
                position: {
                    lat: data.latitude,
                    lng: data.longitude
                },
                map: map,
                icon: marker_default
            });

            // highlight cluster on mouse click
            // remove previous cluster highlight and pop up.
            google.maps.event.addDomListener(marker, 'click', function() {
                if(prevClusterId !== -1){
                    clusterWiseMarker[prevClusterId].forEach(marker => {
                        marker.setIcon(marker_default);
                    });
                    prevInfoWindow.close();
                }

                // pop up
                var infowindow = new google.maps.InfoWindow({
                  content: popContent(data)
                });
                prevInfoWindow = infowindow;
                infowindow.open(map, marker);
                prevClusterId = clusterId;
                clusterWiseMarker[clusterId].forEach(marker => {
                    marker.setIcon(marker_cluster);
                });
                createAirbnbDetails(jsonData, clusterId);
            });

            clusterWiseMarker[data.cluster].push(marker);
        });
    });
};

// shows Airbnb summary on the right side of the cluster page.
// on selecting an Airbnb, it will get highlighted on the map.
var clusterDetails;
var createAirbnbDetails = function(jsonData, clusterId){
    clusterDetails = $('#cluster-details');
    clusterDetails.empty();
    var airbnbs = jsonData.filter(data=>{
        return data.cluster === clusterId;
    });
    airbnbs.forEach(airbnb=>{
        var div = document.createElement("DIV");
        var name = document.createElement("h5");
        var distance = document.createElement("p");
        var time = document.createElement("p");
        var price = document.createElement("p");

        distance.innerText = 'Distance :  '+ airbnb.distance + 'km';
        time.innerText = 'Time : '+ parseInt(airbnb.timeTaken/60) + 'min';
        price.innerText = 'Price :  '+ airbnb.price + ' CAD';
        name.innerText = airbnb.name;
        div.className = 'similar-airbnb-border';
        div.onclick = function(){
            pooUpSelectedAirbnb(airbnb,clusterId);

        };
        div.appendChild(name);
        div.appendChild(distance);
        div.appendChild(time);
        div.appendChild(price);
        clusterDetails.append(div);
    });
};

// makes the Airbnb marker to be highlighted on map when user selects Airbnb from the Recommendations
var pooUpSelectedAirbnb = function(airbnb,clusterId){
    clusterWiseMarker[clusterId].forEach(marker => {
        if(roundOff(marker.position.lat()) === roundOff(airbnb.latitude) && roundOff(marker.position.lng()) === roundOff(airbnb.longitude)){
            var infowindow = new google.maps.InfoWindow({
              content: popContent(airbnb)
            });
            prevInfoWindow.close();
            prevInfoWindow = infowindow;
            infowindow.open(map, marker);
        }
    });
};

// function to roundoff to 5 decimal places
var roundOff = function(value){
    return Math.round(value * 100000) / 100000;
};

// loads the initial google map
var loadUrl = function() {
    $('#googleMaps').attr('src', 'https://maps.googleapis.com/maps/api/js?key=' + googleMapAPIKey + '&libraries=places&callback=initMap');
};