import osmnx as ox
import networkx as nx
import folium
from geopy.distance import geodesic
import folium




def get_nearest_node(lat, lon, G):
    return ox.distance.nearest_nodes(G, X=lon, Y=lat)



def calculate_shortest_path(G, origin_lat, origin_lon, dest_lat, dest_lon):
    origin_node = get_nearest_node(origin_lat, origin_lon, G)
    dest_node = get_nearest_node(dest_lat, dest_lon, G)
    shortest_path = nx.shortest_path(G, origin_node, dest_node, weight='length')
    return shortest_path

# Example route
location = "Rochester, New York, USA" 
G = ox.graph_from_place(location, network_type='drive')

    # Simplify the graph for easier computation
G = ox.simplify_graph(G)

vehicle_lat, vehicle_lon = 43.16103, -77.61092
nearest_node = get_nearest_node(vehicle_lat, vehicle_lon, G)


    # Define your location and retrieve the network graph
 # Change to your area of interest

    # Optionally, plot the graph
fig, ax = ox.plot_graph(G)
origin_lat, origin_lon = 43.16103, -77.61092  # Replace with actual data
dest_lat, dest_lon = 43.15658, -77.60884
route = calculate_shortest_path(G, origin_lat, origin_lon, dest_lat, dest_lon)


# Define the base map centered around your area
m = folium.Map(location=[43.16103, -77.61092], zoom_start=14)

# Add the route to the map
route_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
folium.PolyLine(route_coords, color='blue', weight=5, opacity=0.7).add_to(m)

# Display map with vehicle locations, routes, etc.
m.save("traffic_map.html")
