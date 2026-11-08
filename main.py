import threading
import time
import webbrowser
import random
import math
from flask import Flask, request, jsonify

location_data = {}
ride_store = {}
driver_store = {}
ride_counter = 0
state_lock = threading.Lock()

# ---------------- GPS PERMISSION PAGE ----------------
location_page = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RideRadar GPS</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b1120;color:#f8fafc;font-family:Arial,sans-serif;
display:grid;place-items:center;min-height:100vh;padding:20px}
.card{background:#151f32;border:1px solid #273449;padding:36px;border-radius:22px;
max-width:480px;width:100%;text-align:center;box-shadow:0 20px 60px #0005}
.logo{font-size:30px;color:#22c55e;font-weight:800}
button{background:#22c55e;color:#052e16;border:0;padding:14px 22px;border-radius:10px;
font-size:16px;font-weight:bold;cursor:pointer}
button:hover{background:#16a34a}
#status{color:#a7f3d0;min-height:24px}
</style>
</head>
<body>
<div class="card">
<div class="logo">🚘 RideRadar</div>
<h2>Location Access</h2>
<p>Allow RideRadar to use your current location for the pickup point.</p>
<button onclick="getLocation()">Allow Location</button>
<p id="status"></p>
</div>
<script>
function getLocation(){
 const status=document.getElementById("status");
 if(!navigator.geolocation){status.innerText="Geolocation is not supported.";return;}
 status.innerText="Waiting for location permission...";
 navigator.geolocation.getCurrentPosition(async p=>{
   status.innerText="Location detected! Opening dashboard...";
   try{
     await fetch("/location",{method:"POST",headers:{"Content-Type":"application/json"},
       body:JSON.stringify({lat:p.coords.latitude,lon:p.coords.longitude})});
     window.location.href="/dashboard";
   }catch(e){status.innerText="Could not connect to RideRadar server.";}
 },e=>{
   status.innerText=e.code===1 ? "Permission denied. Allow location in browser settings and refresh." :
   "Location unavailable. Try again or check browser location settings.";
 },{enableHighAccuracy:true,timeout:15000,maximumAge:0});
}
</script>
</body>
</html>
"""


# ---------------- DASHBOARD ----------------
dashboard_html = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>RideRadar Dashboard</title>

<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 15% 10%,#18365a 0%,#0b1120 42%,#070b14 100%);color:#eaf2ff;font-family:Inter,Segoe UI,Arial,sans-serif}
header{padding:18px 26px;background:rgba(10,18,32,.62);border-bottom:1px solid rgba(255,255,255,.13);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;box-shadow:0 8px 32px #0003}
.logo{font-size:25px;font-weight:800;color:#5df2b3;text-shadow:0 0 22px #22c55e55}.container{max-width:1600px;margin:auto;padding:22px}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.card,.panel{background:linear-gradient(135deg,rgba(255,255,255,.10),rgba(255,255,255,.035));border:1px solid rgba(255,255,255,.16);border-radius:18px;padding:18px;min-width:0;backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);box-shadow:0 12px 36px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.08)}
.stat-label{color:#94a3b8;font-size:13px}.stat-value{font-size:24px;color:#22c55e;font-weight:bold;margin-top:8px}
.layout{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(280px,.8fr);gap:15px;margin-top:15px}
h2{font-size:19px;margin:0 0 8px}.sub{font-size:13px;color:#94a3b8;margin:0 0 12px}
#map{height:520px;width:100%;border-radius:14px;border:1px solid rgba(255,255,255,.16);box-shadow:0 12px 30px #0003}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
button{background:linear-gradient(135deg,#5df2b3,#22c55e);color:#052e16;border:1px solid #ffffff25;border-radius:10px;padding:10px 14px;font-weight:750;cursor:pointer;box-shadow:0 5px 18px #22c55e22;transition:transform .18s,filter .18s}
button:hover{filter:brightness(1.08);transform:translateY(-1px)}button.secondary{background:rgba(148,163,184,.16);border:1px solid rgba(255,255,255,.15);color:#f8fafc}button:disabled{opacity:.4;cursor:not-allowed;transform:none}
.status{color:#a7f3d0;min-height:22px;font-size:13px}.row{padding:10px 0;border-bottom:1px solid #273449;font-size:14px}
.fare{font-size:30px;color:#22c55e;font-weight:bold;margin:12px 0}
.graphs{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-top:15px}.plot{height:380px;width:100%}
.drivers-list{display:grid;gap:8px;margin-top:10px}.driver-option{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px;background:#0b1120;border:1px solid #334155;border-radius:9px}
.driver-option small{color:#94a3b8;display:block;margin-top:3px}.note{color:#94a3b8;font-size:12px}

.row{border-bottom:1px solid rgba(255,255,255,.10);padding:12px 0}
.stat-value{text-shadow:0 0 18px #22c55e33}
.driver-option{background:rgba(5,12,25,.45)!important;border:1px solid rgba(255,255,255,.13)!important;border-radius:12px!important}
.fare{text-shadow:0 0 24px #22c55e44}
@media(max-width:1000px){.layout,.graphs{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}
@media(max-width:560px){.container{padding:9px}.stats{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<header><div class="logo">🚘 RideRadar</div><div>Map-based Pickup & Ride Confirmation</div><div style="color:#4ade80">● Demo mode · <a href="/driver" style="color:#5df2b3">Driver Dashboard ↗</a></div></header>
<div class="container">
<div class="stats">
<div class="card"><div class="stat-label">Drivers generated</div><div class="stat-value" id="totalDrivers">--</div></div>
<div class="card"><div class="stat-label">Available within 5 km</div><div class="stat-value" id="nearbyDrivers">--</div></div>
<div class="card"><div class="stat-label">Search radius</div><div class="stat-value">5 km</div></div>
<div class="card"><div class="stat-label">GPS starting point</div><div class="stat-value" style="font-size:14px;line-height:1.7" id="gpsDisplay"><span>Latitude:</span> --<br><span>Longitude:</span> --</div></div>
</div>

<div class="layout">
<section class="panel">
<h2>🗺️ Select locations directly on map</h2>
<p class="sub">GPS location is only a starting point and may be approximate. Click the map to choose exact pickup/destination.</p>
<div class="controls">
<button id="pickupMode" onclick="setMode('pickup')">1. Select Pickup on Map</button>
<button class="secondary" id="destinationMode" onclick="setMode('destination')" disabled>2. Select Destination</button>
<button class="secondary" onclick="useGps()">Use GPS again</button>
</div>
<div class="controls">
<button id="confirmPickup" onclick="confirmPickup()" disabled>Confirm Pickup</button>
<button id="confirmDestination" onclick="confirmDestination()" disabled>Confirm Destination</button>
<button id="confirmRide" onclick="confirmRide()" disabled>Confirm Ride</button>
</div>
<div id="status" class="status">Click “Select Pickup on Map”, then click the map and confirm your pickup.</div>
<div id="map"></div>
<p class="note">Map © Google Maps. Drivers are simulated for the assignment.</p>
</section>

<aside class="panel">
<h2>Ride summary</h2>
<div class="row"><b>Pickup coordinates</b><br><span class="note">Latitude:</span> <span id="pickupLat">--</span><br><span class="note">Longitude:</span> <span id="pickupLon">--</span><br><span id="pickupLabel" class="note">Not confirmed</span></div>
<div class="row"><b>Destination coordinates</b><br><span class="note">Latitude:</span> <span id="destinationLat">--</span><br><span class="note">Longitude:</span> <span id="destinationLon">--</span><br><span id="destinationLabel" class="note">Not selected</span></div>
<div class="row"><b>Road distance:</b> <span id="distance">--</span></div>
<div class="row"><b>Estimated travel time:</b> <span id="duration">--</span></div>
<div class="fare" id="fare">PKR --</div>
<p class="note">Demo fare formula: Rs. 150 base + Rs. 50/km. Not an official Uber/Careem fare.</p>
<hr style="border-color:#273449;margin:18px 0">
<h2>Driver selection</h2>
<div id="driverStatus" class="status">Confirm pickup and destination first.</div>
<div id="driverList" class="drivers-list"></div>
<div id="acceptedDriver"></div>
<div class="controls"><button class="secondary" id="cancelRide" onclick="cancelRide()" style="display:none">Cancel Ride</button></div>
<p class="note">Driver responses and movement are simulated for this project.</p>
</aside>
</div>

<div class="graphs">
<div class="panel"><h2>Cartesian Driver Plot</h2><p class="sub">X/Y coordinates relative to the confirmed pickup point.</p>
<div class="controls"><button onclick="zoomPlot('cartesian',1.2)">＋ Zoom In</button><button class="secondary" onclick="zoomPlot('cartesian',.8)">− Zoom Out</button><button class="secondary" onclick="resetZoom('cartesian')">Reset</button></div><div id="cartesian" class="plot"></div></div>
<div class="panel"><h2>Polar Coordinates</h2><p class="sub">Driver distance and angle from pickup.</p>
<div class="controls"><button onclick="zoomPlot('polar',1.2)">＋ Zoom In</button><button class="secondary" onclick="zoomPlot('polar',.8)">− Zoom Out</button><button class="secondary" onclick="resetZoom('polar')">Reset</button></div><div id="polar" class="plot"></div></div>
</div>
</div>

<script>
const initialLat=INITIAL_LAT, initialLon=INITIAL_LON;
let map=null, RouteClass=null;
async function initPassengerMap(){
 map=new google.maps.Map(document.getElementById("map"),{
  center:{lat:initialLat,lng:initialLon},zoom:14,mapTypeControl:true,streetViewControl:false
 });
 const routesLibrary=await google.maps.importLibrary("routes");
 RouteClass=routesLibrary.Route;
 map.addListener("click",e=>{
  const point={lat:e.latLng.lat(),lon:e.latLng.lng()};
  if(mode==="pickup"){
   pickup=point;if(pickupMarker)pickupMarker.setMap(null);
   pickupMarker=new google.maps.Marker({map,position:{lat:point.lat,lng:point.lon},draggable:true,label:"P",title:"Selected pickup"});
   pickupMarker.addListener("dragend",()=>{const p=pickupMarker.getPosition();pickup={lat:p.lat(),lon:p.lng()};document.getElementById("status").textContent="Pickup marker moved. Confirm pickup again.";document.getElementById("confirmPickup").disabled=false;});
   document.getElementById("confirmPickup").disabled=false;document.getElementById("status").textContent="Pickup selected. Press Confirm Pickup.";
  }else{
   if(!pickup){document.getElementById("status").textContent="Confirm pickup first.";return;}
   destination=point;if(destinationMarker)destinationMarker.setMap(null);
   destinationMarker=new google.maps.Marker({map,position:{lat:point.lat,lng:point.lon},draggable:true,label:"D",title:"Selected destination"});
   destinationMarker.addListener("dragend",()=>{const p=destinationMarker.getPosition();destination={lat:p.lat(),lon:p.lng()};document.getElementById("confirmDestination").disabled=false;document.getElementById("status").textContent="Destination moved. Confirm destination again.";});
   document.getElementById("confirmDestination").disabled=false;document.getElementById("status").textContent="Destination selected. Press Confirm Destination.";
  }
 });
}
async function getGoogleRoute(origin,destination){
 const result=await RouteClass.computeRoutes({
  origin:{lat:origin.lat,lng:origin.lon},
  destination:{lat:destination.lat,lng:destination.lon},
  travelMode:"DRIVING",
  fields:["path","distanceMeters","durationMillis"]
 });
 if(!result.routes||!result.routes.length)throw new Error("Google Routes API returned no route");
 return result.routes[0];
}

let mode="pickup",pickup=null,destination=null,pickupMarker=null,destinationMarker=null,
 radiusCircle=null,routeLayer=null,driverMarkers=[],drivers=[],rideAccepted=false,routeData=null,
matching=false,matchingQueue=[],matchingIndex=0,requestTimer=null,driverMoveTimer=null,assignedDriverMarker=null;
document.getElementById("gpsDisplay").innerHTML="<span>Latitude:</span> "+initialLat.toFixed(6)+"<br><span>Longitude:</span> "+initialLon.toFixed(6);

function setMode(m){
 mode=m;
 document.getElementById("status").textContent=m==="pickup"?
 "Pickup mode: click the map to place your pickup marker.":
 "Destination mode: click the map to place your destination marker.";
 document.getElementById("pickupMode").classList.toggle("secondary",m!=="pickup");
 document.getElementById("destinationMode").classList.toggle("secondary",m!=="destination");
}

function useGps(){
 document.getElementById("status").textContent="Requesting GPS...";
 navigator.geolocation.getCurrentPosition(pos=>{
  map.setCenter({lat:pos.coords.latitude,lng:pos.coords.longitude});map.setZoom(16);
  document.getElementById("status").textContent="GPS recentered map. Select pickup manually if this location is inaccurate.";
 },()=>document.getElementById("status").textContent="GPS unavailable; use map click to choose pickup.",{enableHighAccuracy:true,timeout:12000});
}
async function confirmPickup(){
 if(!pickup){return;}
 document.getElementById("pickupLat").textContent=pickup.lat.toFixed(6);
  document.getElementById("pickupLon").textContent=pickup.lon.toFixed(6);
  document.getElementById("pickupLabel").textContent="Pickup confirmed";
 pickupMarker.setTitle("Confirmed pickup");
 if(radiusCircle)radiusCircle.setMap(null);
  radiusCircle=new google.maps.Circle({map,center:{lat:pickup.lat,lng:pickup.lon},radius:5000,
   strokeColor:"#3b82f6",strokeOpacity:.8,strokeWeight:2,fillColor:"#3b82f6",fillOpacity:.05});
 document.getElementById("destinationMode").disabled=false;
 document.getElementById("confirmPickup").disabled=true;
 document.getElementById("confirmDestination").disabled=true;
 document.getElementById("confirmRide").disabled=true;
 destination=null;routeData=null;rideAccepted=false;
 document.getElementById("destinationLabel").textContent="Not selected";
  document.getElementById("pickupLat").textContent=pickup.lat.toFixed(6);
  document.getElementById("pickupLon").textContent=pickup.lon.toFixed(6);
  document.getElementById("destinationLat").textContent="--";
  document.getElementById("destinationLon").textContent="--";
 document.getElementById("distance").textContent="--";document.getElementById("duration").textContent="--";document.getElementById("fare").textContent="PKR --";
 document.getElementById("driverList").innerHTML="";document.getElementById("acceptedDriver").innerHTML="";
 document.getElementById("status").textContent="Pickup confirmed. Now select destination on map.";
 const res=await fetch("/drivers",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(pickup)});
 drivers=await res.json();
 renderDrivers();
 document.getElementById("totalDrivers").textContent=drivers.length;
 document.getElementById("nearbyDrivers").textContent=drivers.filter(d=>d.nearby).length;
 setMode("destination");
}
function renderDrivers(){
  driverMarkers.forEach(m=>m.setMap(null));driverMarkers=[];
  drivers.forEach(d=>{
   const marker=new google.maps.Marker({map,position:{lat:d.lat,lng:d.lon},title:d.name+" · "+d.car,
    icon:{path:google.maps.SymbolPath.CIRCLE,scale:7,fillColor:d.nearby?"#22c55e":"#f59e0b",fillOpacity:1,strokeColor:"#fff",strokeWeight:1}});
   const info=new google.maps.InfoWindow({content:`<b>${d.name}</b> · ${d.car}<br>⭐ ${d.rating}<br>${d.distance.toFixed(2)} km from pickup<br>${d.nearby?"Available within radius":"Outside radius"}`});
   marker.addListener("click",()=>{info.open({map,anchor:marker});showDriver(d);});driverMarkers.push(marker);
  });
  drawGraphs();
}
async function confirmDestination(){
 if(!pickup||!destination)return;
 document.getElementById("destinationLat").textContent=destination.lat.toFixed(6);
 document.getElementById("destinationLon").textContent=destination.lon.toFixed(6);
 document.getElementById("destinationLabel").textContent="Destination confirmed";
 destinationMarker.setTitle("Confirmed destination");
 document.getElementById("confirmDestination").disabled=true;
 document.getElementById("status").textContent="Destination confirmed. Calculating Google Maps route...";
 try{
  routeData=await getGoogleRoute(pickup,destination);
  const km=routeData.distanceMeters/1000,mins=routeData.durationMillis/60000;
  if(routeLayer)routeLayer.setMap(null);
  routeLayer=new google.maps.Polyline({map,path:routeData.path,strokeColor:"#22c55e",strokeOpacity:1,strokeWeight:5});
  const routeBounds=new google.maps.LatLngBounds();routeData.path.forEach(p=>routeBounds.extend(p));map.fitBounds(routeBounds);
  document.getElementById("distance").textContent=km.toFixed(2)+" km";
  document.getElementById("duration").textContent=Math.round(mins)+" min (Google Maps estimate)";
  document.getElementById("fare").textContent="PKR "+Math.round(150+50*km).toLocaleString("en-PK");
  document.getElementById("confirmRide").disabled=false;
  document.getElementById("status").textContent="Google Maps route ready. Press Confirm Ride to view available drivers.";
 }catch(err){console.error(err);document.getElementById("status").textContent="Google Maps route failed. Check that Directions API is enabled for your key.";}
}
let activeRideId=null,rideStatusTimer=null,passengerDriverMarker=null,passengerApproachTimer=null,approachStarted=false,tripAnimationStarted=false;
async function confirmRide(){
 if(!pickup||!destination||!routeData||matching||rideAccepted)return;
 const km=routeData.distance/1000,total=Math.round(150+50*km);
 const response=await fetch('/api/ride/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pickup,destination,distance_km:km,total_fare:total})});
 const result=await response.json();
 if(!response.ok){document.getElementById("driverStatus").textContent=result.message;return;}
 activeRideId=result.ride_id;matching=true;matchingQueue=[];matchingIndex=0;
 document.getElementById("driverList").innerHTML="";document.getElementById("acceptedDriver").innerHTML="";
 document.getElementById("cancelRide").style.display="inline-block";
 document.getElementById("driverStatus").textContent="Request sent to nearest online driver. Waiting for a real dashboard response...";
 document.getElementById("status").textContent="Ride request created. Open /driver in another tab to accept or reject.";
 clearInterval(rideStatusTimer);rideStatusTimer=setInterval(refreshPassengerRide,2000);refreshPassengerRide();
}
async function refreshPassengerRide(){
 if(!activeRideId)return;const r=await fetch('/api/ride/'+activeRideId+'/passenger');if(!r.ok)return;const d=await r.json();
 const labels={searching:'Searching for driver',arriving:'Driver accepted — arriving at pickup',in_trip:'Trip in progress',completed:'Ride completed',no_driver:'No driver available',cancelled:'Ride cancelled'};
 document.getElementById('driverStatus').textContent=labels[d.status]||d.status;
 document.getElementById('status').textContent=labels[d.status]||d.status;
 if(d.driver){document.getElementById('acceptedDriver').innerHTML=`<div class="card" style="margin-top:10px"><b>${d.driver.name||'Driver'} · ${d.driver.car||''}</b><div class="row">${d.driver.plate||''} · ⭐ ${d.driver.rating||'--'}</div>${d.status==='arriving'?'<div class="row">Pickup OTP: <b>'+d.otp+'</b> — share this code with your driver.</div>':''}</div>`;if(d.status==='arriving'&&!approachStarted&&d.driver.lat!=null)animateDriverToPickup(d.driver.lat,d.driver.lon);if(d.status==='in_trip'&&!tripAnimationStarted)animatePassengerTrip();}
 if(['completed','cancelled','no_driver'].includes(d.status)){clearInterval(rideStatusTimer);matching=false;}
}
async function animateDriverToPickup(driverLat,driverLon){
 approachStarted=true;
 try{
  const r=await getGoogleRoute({lat:driverLat,lon:driverLon},pickup);
  const coords=r.path.map(p=>({lat:p.lat,lng:p.lng}));
  const line=new google.maps.Polyline({map,path:coords,strokeColor:"#38bdf8",strokeOpacity:1,strokeWeight:4});
  if(passengerDriverMarker)passengerDriverMarker.setMap(null);
  passengerDriverMarker=new google.maps.Marker({map,position:coords[0],title:"Assigned driver"});
  let i=0;clearInterval(passengerApproachTimer);
  passengerApproachTimer=setInterval(()=>{i=Math.min(i+1,coords.length-1);passengerDriverMarker.setPosition(coords[i]);if(i>=coords.length-1){clearInterval(passengerApproachTimer);document.getElementById("driverStatus").textContent="Driver arrived at pickup. OTP verification is required to start the trip."; }},Math.max(80,Math.min(450,12000/Math.max(coords.length,1))));
  const bounds=new google.maps.LatLngBounds();coords.forEach(c=>bounds.extend(c));map.fitBounds(bounds);
 }catch(e){approachStarted=false;document.getElementById("driverStatus").textContent="Driver accepted. Google Maps road animation unavailable; check Directions API access.";}
}
async function animatePassengerTrip(){
 tripAnimationStarted=true;clearInterval(passengerApproachTimer);
 try{
  const r=await getGoogleRoute(pickup,destination),coords=r.path.map(p=>({lat:p.lat,lng:p.lng}));
  const line=new google.maps.Polyline({map,path:coords,strokeColor:"#22c55e",strokeOpacity:1,strokeWeight:6});
  if(passengerDriverMarker)passengerDriverMarker.setMap(null);
  passengerDriverMarker=new google.maps.Marker({map,position:coords[0],title:"Ride in progress"});
  let i=0;passengerApproachTimer=setInterval(()=>{i=Math.min(i+1,coords.length-1);passengerDriverMarker.setPosition(coords[i]);if(i>=coords.length-1)clearInterval(passengerApproachTimer);},Math.max(80,Math.min(450,18000/Math.max(coords.length,1))));
  const bounds=new google.maps.LatLngBounds();coords.forEach(c=>bounds.extend(c));map.fitBounds(bounds);
 }catch(e){tripAnimationStarted=false;console.error(e);}
}
async function cancelRide(){
 if(activeRideId){await fetch('/api/ride/'+activeRideId+'/cancel',{method:'POST'});activeRideId=null;}clearInterval(rideStatusTimer);clearInterval(passengerApproachTimer);approachStarted=false;tripAnimationStarted=false;if(passengerDriverMarker){passengerDriverMarker.setMap(null);passengerDriverMarker=null;}
 matching=false;rideAccepted=false;clearTimeout(requestTimer);clearInterval(driverMoveTimer);
 if(assignedDriverMarker){assignedDriverMarker.setMap(null);assignedDriverMarker=null;}
 document.getElementById("driverStatus").textContent="Ride cancelled.";
 document.getElementById("acceptedDriver").innerHTML="";
 document.getElementById("driverList").innerHTML="";
 document.getElementById("cancelRide").style.display="none";
 document.getElementById("status").textContent="Ride request cancelled.";
}
function showDriver(d){document.getElementById("driverStatus").textContent=`${d.id}: ${d.distance.toFixed(2)} km from pickup, ${d.nearby?"available":"outside radius"}.`;}

function drawGraphs(){
 const near=drivers.filter(d=>d.nearby),far=drivers.filter(d=>!d.nearby),xx=[],yy=[];
 for(let i=0;i<=360;i++){let a=i*Math.PI/180;xx.push(5*Math.cos(a));yy.push(5*Math.sin(a));}
 const radiusTrace={x:xx,y:yy,mode:"lines",name:"5 km radius",line:{color:"#3b82f6",dash:"dash"},hoverinfo:"skip"};
 function trace(ds,name,color){return {x:ds.map(d=>d.x),y:ds.map(d=>d.y),customdata:ds,mode:"markers",type:"scatter",name,
 marker:{color,size:12},hovertemplate:"<b>%{customdata.id}</b><br>Distance %{customdata.distance:.2f} km<extra></extra>"};}
 const passengerTrace={x:[0],y:[0],mode:"markers",type:"scatter",name:"Pickup",marker:{color:"#3b82f6",size:18,symbol:"star"},hovertemplate:"Pickup (0,0)<extra></extra>"};
 Plotly.newPlot("cartesian",[radiusTrace,trace(far,"Outside 5 km","#f59e0b"),trace(near,"Available drivers","#22c55e"),passengerTrace],
 {paper_bgcolor:"#151f32",plot_bgcolor:"#151f32",font:{color:"#e5e7eb"},xaxis:{title:"X (km)",range:[-10,10],gridcolor:"#273449"},yaxis:{title:"Y (km)",range:[-10,10],scaleanchor:"x",gridcolor:"#273449"},legend:{orientation:"h"},margin:{t:15,b:45,l:45,r:10}},
 {responsive:true,displaylogo:false});
 document.getElementById("cartesian").on("plotly_click",ev=>{const d=ev.points[0].customdata;if(d?.id)showDriver(d);});
 Plotly.newPlot("polar",[
 {type:"scatterpolar",mode:"markers",name:"Drivers",r:drivers.map(d=>d.distance),theta:drivers.map(d=>d.angle),customdata:drivers,marker:{color:drivers.map(d=>d.nearby?"#22c55e":"#f59e0b"),size:10},hovertemplate:"%{customdata.id}<br>r=%{r:.2f} km, θ=%{theta:.1f}°<extra></extra>"},
 {type:"scatterpolar",mode:"lines",name:"5 km radius",r:Array(361).fill(5),theta:Array.from({length:361},(_,i)=>i),line:{color:"#3b82f6",dash:"dash"},hoverinfo:"skip"}
 ],{paper_bgcolor:"#151f32",font:{color:"#e5e7eb"},polar:{bgcolor:"#151f32",radialaxis:{range:[0,12],gridcolor:"#273449"},angularaxis:{gridcolor:"#273449"}},legend:{orientation:"h"},margin:{t:15,b:25,l:30,r:30}},{responsive:true,displaylogo:false});
}
function zoomPlot(id,factor){
 const el=document.getElementById(id);
 if(id==="cartesian"){
  const xr=el.layout.xaxis.range,yr=el.layout.yaxis.range,cx=(xr[0]+xr[1])/2,cy=(yr[0]+yr[1])/2;
  const hx=(xr[1]-xr[0])/(2*factor),hy=(yr[1]-yr[0])/(2*factor);
  Plotly.relayout(el,{"xaxis.range":[cx-hx,cx+hx],"yaxis.range":[cy-hy,cy+hy]});
 }else{const max=el.layout.polar.radialaxis.range[1]/factor;Plotly.relayout(el,{"polar.radialaxis.range":[0,Math.max(2,max)]});}
}
function resetZoom(id){if(id==="cartesian")Plotly.relayout(id,{"xaxis.range":[-10,10],"yaxis.range":[-10,10]});else Plotly.relayout(id,{"polar.radialaxis.range":[0,12]});}
</script>
<script async defer src="https://maps.googleapis.com/maps/api/js?key=AIzaSyBPV_rzbbB1hf2liRmoIfio0AbZ8NDQd6I&callback=initPassengerMap"></script>
</body></html>
"""

# ---------------- DRIVER DASHBOARD ----------------
driver_dashboard_html = r"""
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RideRadar Driver</title>

<style>*{box-sizing:border-box}body{margin:0;background:#0b1120;color:#eaf2ff;font-family:Segoe UI,Arial;padding:22px}.wrap{max-width:1100px;margin:auto}.panel{background:#172338;border:1px solid #334155;border-radius:16px;padding:20px;margin-bottom:15px}h1{color:#5df2b3}button{padding:11px 16px;border:0;border-radius:9px;font-weight:bold;cursor:pointer;background:#5df2b3;color:#052e16;margin:5px}button.no{background:#475569;color:white}#map{height:430px;border-radius:12px}.muted{color:#94a3b8}.request{padding:15px;border:1px solid #475569;border-radius:12px;margin:10px 0}</style></head>
<body><div class="wrap"><h1>🚘 RideRadar — Driver Dashboard</h1><p class="muted">Select your demo driver profile and manage incoming ride requests.</p>
<div class="panel"><label>Driver profile: <select id="driver" onchange="load()"></select></label> <button onclick="setOnline(true)">Go Online</button><button class="no" onclick="setOnline(false)">Go Offline</button><span id="online" class="muted"></span></div>
<div class="panel"><h2>Incoming requests</h2><div id="requests">Loading...</div></div><div class="panel"><h2>Active ride</h2><div id="active">No active ride.</div><div id="otpBox"></div></div><div class="panel"><h2>Ride map</h2><div id="map"></div></div></div>
<script>
const $=id=>document.getElementById(id);let current=null,map=null,RouteClass=null,routeRenderer=null,marker=null;
async function initDriverMap(){
 map=new google.maps.Map($('map'),{center:{lat:24.8607,lng:67.0011},zoom:13,mapTypeControl:true,streetViewControl:false});
 const routesLibrary=await google.maps.importLibrary("routes");RouteClass=routesLibrary.Route;
}
async function getDriverRoute(o,d){
 const result=await RouteClass.computeRoutes({origin:{lat:o.lat,lng:o.lon},destination:{lat:d.lat,lng:d.lon},travelMode:"DRIVING",fields:["path","distanceMeters","durationMillis"]});
 if(!result.routes||!result.routes.length)throw new Error("No route returned");return result.routes[0];
}
async function api(url,body){let r=await fetch(url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return r.json()}
async function load(){let ds=await api('/api/drivers');$('driver').innerHTML=ds.map(d=>`<option value="${d.id}">${d.name} · ${d.car} (${d.plate})</option>`).join('');current=+$('driver').value;await refresh()}
async function setOnline(value){current=+$('driver').value;let x=await api('/api/driver/online',{driver_id:current,online:value});$('online').textContent=x.message;refresh()}
async function act(id,action){let x=await api('/api/ride/'+id+'/'+action,{driver_id:current});$('online').textContent=x.message;refresh()}
async function startTrip(id){let code=$('otp').value;let x=await api('/api/ride/'+id+'/start',{driver_id:current,otp:code});$('online').textContent=x.message;refresh()}
async function complete(id){let x=await api('/api/ride/'+id+'/complete',{driver_id:current});$('online').textContent=x.message;refresh()}
async function refresh(){if(!current)return;let x=await api('/api/driver/'+current+'/requests');$('requests').innerHTML=x.requests.length?x.requests.map(r=>`<div class="request"><b>Ride #${r.id}</b><p>Pickup: ${r.pickup_lat.toFixed(5)}, ${r.pickup_lon.toFixed(5)}</p><p>Destination: ${r.destination_lat.toFixed(5)}, ${r.destination_lon.toFixed(5)}</p><p>${r.distance_km.toFixed(2)} km · PKR ${Math.round(r.total_fare)}</p><button onclick="act(${r.id},'accept')">Accept</button><button class="no" onclick="act(${r.id},'reject')">Reject</button></div>`).join(''):'No incoming requests.';
let a=x.active;if(a){$('active').innerHTML=`<b>Ride #${a.id}: ${a.status}</b><p>OTP is shared with passenger. Ask passenger to provide it before starting trip.</p>${a.status==='arriving'?`<input id="otp" placeholder="Enter 4-digit OTP" maxlength="4"><button onclick="startTrip(${a.id})">Verify OTP & Start Trip</button>`:''}${a.status==='in_trip'?`<button onclick="complete(${a.id})">Complete ride</button>`:''}`;showRoute(a)}else{$('active').textContent='No active ride.';$('otpBox').innerHTML=''} }
async function showRoute(a){
 if(!map||!RouteClass)return;
 let o,d;if(a.status==='in_trip'){o={lat:a.pickup_lat,lon:a.pickup_lon};d={lat:a.destination_lat,lon:a.destination_lon};}
 else{o={lat:a.driver_lat,lon:a.driver_lon};d={lat:a.pickup_lat,lon:a.pickup_lon};}
 try{const r=await getDriverRoute(o,d);if(routeRenderer)routeRenderer.setMap(null);
 routeRenderer=new google.maps.Polyline({map,path:r.path,strokeColor:'#22c55e',strokeOpacity:1,strokeWeight:5});
 const bounds=new google.maps.LatLngBounds();r.path.forEach(p=>bounds.extend(p));map.fitBounds(bounds);
 }catch(e){console.error(e);$('online').textContent="Google Maps route unavailable. Check Directions API access.";}
}
load();setInterval(refresh,2500);
</script><script async defer src="https://maps.googleapis.com/maps/api/js?key=AIzaSyBPV_rzbbB1hf2liRmoIfio0AbZ8NDQd6I&callback=initDriverMap"></script></body></html>
"""

# ---------------- FLASK ROUTES ----------------
from flask import Flask

app = Flask(__name__)
@app.route("/")
def home():
    return location_page

@app.route("/location", methods=["POST"])
def receive_location():
    global location_data
    location_data=request.get_json(force=True)
    return jsonify({"status":"ok"})

# Saved pool of 12 realistic demo driver profiles. Profile details persist between requests.
DRIVER_POOL = [
 {"name":"Hassan","car":"Toyota Corolla","rating":"4.9","plate":"KHI-4821"},
 {"name":"Ahmed","car":"Honda City","rating":"4.8","plate":"KHI-1937"},
 {"name":"Ali","car":"Suzuki Cultus","rating":"4.7","plate":"KHI-6284"},
 {"name":"Usman","car":"Toyota Yaris","rating":"4.9","plate":"KHI-7352"},
 {"name":"Bilal","car":"Honda Civic","rating":"4.8","plate":"KHI-2946"},
 {"name":"Hamza","car":"Suzuki Swift","rating":"4.9","plate":"KHI-5108"},
 {"name":"Saad","car":"Toyota Corolla","rating":"4.7","plate":"KHI-8463"},
 {"name":"Zain","car":"Honda City","rating":"4.8","plate":"KHI-3729"},
 {"name":"Danish","car":"Suzuki Alto","rating":"4.6","plate":"KHI-9081"},
 {"name":"Ayan","car":"Toyota Yaris","rating":"4.9","plate":"KHI-4156"},
 {"name":"Fahad","car":"Honda BR-V","rating":"4.7","plate":"KHI-6720"},
 {"name":"Muneeb","car":"Toyota Corolla","rating":"4.8","plate":"KHI-2519"},
]

@app.route("/drivers", methods=["POST"])
def generate_drivers():
    data=request.get_json(force=True)
    lat=float(data["lat"]);lon=float(data["lon"])
    selected=random.sample(DRIVER_POOL, random.randint(10,12))
    generated=[]
    for i,profile in enumerate(selected):
        x=random.uniform(-8,8);y=random.uniform(-8,8)
        dist=math.hypot(x,y);angle=math.degrees(math.atan2(y,x))
        dlat=y/111.0
        cos_lat=max(0.01,abs(math.cos(math.radians(lat))))
        dlon=x/(111.0*cos_lat)*(1 if lat>=0 else -1)
        generated.append({**profile,"id":f"Driver {i+1:02d}","x":x,"y":y,"distance":dist,"angle":angle,
                          "nearby":dist<=5,"lat":lat+dlat,"lon":lon+dlon})
    with state_lock:
        driver_store.clear()
        for i, d in enumerate(generated, start=1):
            d["id"] = i
            d["online"] = True
            d["lat"] = lat + (d["y"] / 111.0)
            d["lon"] = lon + (d["x"] / (111.0 * max(0.01, abs(math.cos(math.radians(lat))))))
            driver_store[i] = d
    return jsonify(generated)

@app.route("/driver")
def driver_dashboard():
    return driver_dashboard_html

@app.route("/api/drivers")
def api_drivers():
    with state_lock:
        return jsonify([{k:d[k] for k in ("id","name","car","plate","rating","online")} for d in driver_store.values()])

@app.route("/api/driver/online", methods=["POST"])
def driver_online():
    data=request.get_json(force=True); did=int(data["driver_id"])
    with state_lock:
        if did not in driver_store:return jsonify(message="Driver profile not found."),404
        driver_store[did]["online"]=bool(data.get("online"))
    return jsonify(message="You are online." if data.get("online") else "You are offline.")

@app.route("/api/driver/<int:did>/requests")
def driver_requests(did):
    with state_lock:
        incoming=[dict(r) for r in ride_store.values() if r["status"]=="searching" and r.get("driver_id")==did]
        active=next((dict(r) for r in ride_store.values() if r.get("driver_id")==did and r["status"] in ("accepted","arriving","in_trip")),None)
        if active and did in driver_store:
            active["driver_lat"]=driver_store[did].get("lat",active["pickup_lat"]);active["driver_lon"]=driver_store[did].get("lon",active["pickup_lon"])
    return jsonify(requests=incoming,active=active)

@app.route("/api/ride/request", methods=["POST"])
def create_ride():
    global ride_counter
    data=request.get_json(force=True)
    with state_lock:
        eligible=[d for d in driver_store.values() if d.get("online") and d.get("distance",999)<=5]
        eligible.sort(key=lambda d:d["distance"])
        if not eligible:return jsonify(message="No online drivers within 5 km."),409
        ride_counter+=1;did=eligible[0]["id"];code=f"{random.randint(0,9999):04d}"
        ride={"id":ride_counter,"pickup_lat":data["pickup"]["lat"],"pickup_lon":data["pickup"]["lon"],"destination_lat":data["destination"]["lat"],"destination_lon":data["destination"]["lon"],"distance_km":data["distance_km"],"total_fare":data["total_fare"],"status":"searching","driver_id":did,"otp":code,"created_at":time.time()}
        ride_store[ride_counter]=ride
    return jsonify(message="Request sent to nearest driver.",ride_id=ride_counter)

@app.route("/api/ride/<int:rid>/<action>", methods=["POST"])
def ride_action(rid,action):
    data=request.get_json(force=True);did=int(data["driver_id"])
    with state_lock:
        ride=ride_store.get(rid)
        if not ride:return jsonify(message="Ride not found."),404
        if ride.get("driver_id")!=did:return jsonify(message="This request is not assigned to your profile."),403
        if action=="accept":
            if ride["status"]!="searching":return jsonify(message="This request is no longer available."),409
            ride["status"]="arriving"
        elif action=="reject":
            if ride["status"]!="searching":return jsonify(message="This request is no longer available."),409
            rejected=ride.setdefault("rejected",set());rejected.add(did)
            candidates=[d for d in driver_store.values() if d.get("online") and d.get("distance",999)<=5 and d["id"] not in rejected]
            candidates.sort(key=lambda d:d["distance"])
            if not candidates:ride["status"]="no_driver";return jsonify(message="No other online driver within 5 km.")
            ride["driver_id"]=candidates[0]["id"];ride["status"]="searching"
        elif action=="start":
            if ride["status"]!="arriving":return jsonify(message="Driver must accept the ride first."),409
            if data.get("otp")!=ride["otp"]:return jsonify(message="Incorrect OTP."),400
            ride["status"]="in_trip"
        elif action=="complete":
            if ride["status"]!="in_trip":return jsonify(message="Trip has not started."),409
            ride["status"]="completed"
        else:return jsonify(message="Unknown action."),400
    return jsonify(message={"accept":"Ride accepted. Proceed to pickup.","reject":"Request passed to the next nearby driver.","start":"OTP verified. Trip started.","complete":"Ride completed."}[action])

@app.route("/api/ride/<int:rid>/cancel",methods=["POST"])
def cancel_ride(rid):
    with state_lock:
        if rid not in ride_store:return jsonify(message="Ride not found."),404
        ride_store[rid]["status"]="cancelled"
    return jsonify(message="Ride cancelled.")

@app.route("/api/ride/<int:rid>/passenger")
def passenger_ride(rid):
    with state_lock:
        r=ride_store.get(rid)
        if not r:return jsonify(message="Ride not found."),404
        safe={k:v for k,v in r.items() if k!="rejected"}
        safe["driver"]={k:driver_store.get(r["driver_id"],{}).get(k) for k in ("name","car","plate","rating","lat","lon")}
    return jsonify(safe)

@app.route("/dashboard")
def dashboard():
    lat=float(location_data.get("lat",24.8607))
    lon=float(location_data.get("lon",67.0011))
    return dashboard_html.replace("INITIAL_LAT",str(lat)).replace("INITIAL_LON",str(lon))

def start_server():
    app.run(host="127.0.0.1",port=5000,debug=False,use_reloader=False)

if __name__=="__main__":
    threading.Thread(target=start_server,daemon=True).start()
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")
    print("RideRadar started. GPS is only used to center the initial map.")
    input("Keep terminal open; press Enter to stop.")
