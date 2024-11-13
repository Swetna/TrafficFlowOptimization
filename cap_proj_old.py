# import traci
# import sumolib
# import numpy as np
# import networkx as nx
# from collections import defaultdict
# import requests
# from dotenv import load_dotenv
# import os
# import websockets


# class TrafficManager:
#     def __init__(self):
#         # Load environment variables
#         load_dotenv()
#         self.google_maps_api_key = "AIzaSyAcaHG4p9hs7nPuMAFFTNl3jNZC2x4KPyc"

#         # Validate API key
#         if not self.google_maps_api_key:
#             raise ValueError("API key not found. Check your .env file.")

#         # Initialize properties
#         self.footprint_counter = defaultdict(int)
#         self.vehicle_counts = defaultdict(int)
        
#         # Ensure SUMO connection is active before building the network graph
        
#         self.network_graph = self.build_network_graph()

#     def get_vehicle_positions(self):
#             vehicle_positions = []
#             for vehicle_id in traci.vehicle.getIDList():
#                 x, y = traci.vehicle.getPosition(vehicle_id)
#                 lon, lat = traci.simulation.convertGeo(x, y)
#                 vehicle_positions.append((vehicle_id, lat, lon))
#             return vehicle_positions

#     def send_vehicle_data_to_maps(self):
#         while traci.simulation.getMinExpectedNumber() > 0:
#             traci.simulationStep()
#             vehicle_positions = self.get_vehicle_positions()
#             for vehicle_id, lat, lon in vehicle_positions:
#                 road_data = self.get_road_data(f"{lat},{lon}")
#                 if road_data:
#                     snapped_lat, snapped_lng = road_data['snappedPoints'][0]['location'].values()
#                     # Assuming WebSocket or REST call to send `snapped_lat`, `snapped_lng` to front-end
#                     self.update_google_map(vehicle_id, snapped_lat, snapped_lng)
#             # time.sleep(0.5)  # Adjust frequency as needed

    
#     async def update_google_map(self, vehicle_data):
#         async with websockets.connect("ws://localhost:5678") as websocket:
#             await websocket.send(json.dumps(vehicle_data))
    
    
#     def build_network_graph(self):
#         G = nx.DiGraph()
#         edges = traci.edge.getIDList()
        
#         for edge in edges:
#             if edge in traci.edge.getIDList():  # Ensure edge is valid
#                 length = traci.edge.getLastStepLength(edge)
#                 travel_time = traci.edge.getTraveltime(edge)
#                 G.add_edge(edge, edge, travel_time=travel_time, length=length)

#         return G

#     def detect_congestion(self, threshold):
#         congested_roads = []
#         for edge in self.network_graph.edges(data=True):
#             vehicle_count = traci.edge.getLastStepVehicleNumber(edge[0])
#             if vehicle_count > threshold:
#                 congested_roads.append(edge[0])
#         return congested_roads

#     def select_vehicles(self, congested_roads, L):
#         selected_vehicles = []
#         for road in congested_roads:
#             selected_vehicles.extend(traci.edge.getLastStepVehicleIDs(road))
#         return selected_vehicles

#     def compute_k_shortest_paths(self, origin, destination, k):
#         return list(nx.shortest_simple_paths(self.network_graph, origin, destination, weight='travel_time'))[:k]

#     def reroute_vehicles(self, selected_vehicles, strategy='EBkSP', k=3):
#         for vehicle in selected_vehicles:
#             current_edge = traci.vehicle.getRoadID(vehicle)
#             destination = traci.vehicle.getDestination(vehicle)
#             if strategy == 'DSP':
#                 new_path = self.dynamic_shortest_path(current_edge, destination)
#             elif strategy == 'RkSP':
#                 new_path = self.random_k_shortest_paths(current_edge, destination, k)
#             elif strategy == 'EBkSP':
#                 k_paths = self.compute_k_shortest_paths(current_edge, destination, k)
#                 new_path = min(k_paths, key=lambda p: self.calculate_path_popularity([p])[p])
#             else:
#                 continue
            
#             self.set_route(vehicle, new_path)
            
#     def get_road_data(self,path):
#         url = f"https://roads.googleapis.com/v1/snapToRoads?path={path}&key={self.google_maps_api_key}"
#         response = requests.get(url)
#         if response.status_code == 200:
#             return response.json()
#         else:
#             print("Error:", response.status_code, response.text)
#             return None


#     def set_route(self, vehicle, new_path):
#         traci.vehicle.setRoute(vehicle, new_path)

#     def run(self, congestion_threshold, L, strategy='EBkSP', k=3):
#         step = 0
#         while step < 1000:  # Run for a defined number of steps
#             traci.simulationStep()
#             congested_roads = self.detect_congestion(congestion_threshold)
#             if congested_roads:
#                 selected_vehicles = self.select_vehicles(congested_roads, L)
#                 self.reroute_vehicles(selected_vehicles, strategy, k)
#             step += 1
            
# if __name__ == "__main__":
#     path = "34.0938,-118.3612|34.0635,-118.4455"  

#     sumo_binary = sumolib.checkBinary('sumo-gui')
#     sumo_cmd = [sumo_binary, "-c", "/Users/swetna/sumo/tests/complex/tutorial/circles/data/circles.sumocfg"]
#     traci.start(sumo_cmd)

#     traffic_manager = TrafficManager()
#     traffic_manager.send_vehicle_data_to_maps()
    
#     traci.close()


import traci
import sumolib
import numpy as np
import networkx as nx
from collections import defaultdict
import requests
import json
from dotenv import load_dotenv
import os
import asyncio
import websockets

class TrafficManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.google_maps_api_key = "AIzaSyAcaHG4p9hs7nPuMAFFTNl3jNZC2x4KPyc"

        # Validate API key
        if not self.google_maps_api_key:
            raise ValueError("API key not found. Check your .env file.")

        # Initialize properties
        self.footprint_counter = defaultdict(int)
        self.vehicle_counts = defaultdict(int)
        
        # Ensure SUMO connection is active before building the network graph
        self.network_graph = self.build_network_graph()

    def get_vehicle_positions(self):
        vehicle_positions = []
        for vehicle_id in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vehicle_id)
            lon, lat = traci.simulation.convertGeo(x, y)
            vehicle_positions.append((vehicle_id, lat, lon))
        return vehicle_positions

    def send_vehicle_data_to_maps(self, websocket):
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            vehicle_positions = self.get_vehicle_positions()
            for vehicle_id, lat, lon in vehicle_positions:
                road_data = self.get_road_data(f"{lat},{lon}")
                if road_data:
                    snapped_lat, snapped_lng = road_data['snappedPoints'][0]['location'].values()
                    # Assuming WebSocket or REST call to send `snapped_lat`, `snapped_lng` to front-end
                    self.update_google_map(websocket, vehicle_id, snapped_lat, snapped_lng)
            # time.sleep(0.5)  # Adjust frequency as needed

    async def update_google_map(self, websocket, vehicle_id, lat, lng):
        vehicle_data = {
            "id": vehicle_id,
            "lat": lat,
            "lng": lng
        }
        await websocket.send(json.dumps(vehicle_data))

    def build_network_graph(self):
        G = nx.DiGraph()
        edges = traci.edge.getIDList()
        
        for edge in edges:
            if edge in traci.edge.getIDList():  # Ensure edge is valid
                length = traci.edge.getLastStepLength(edge)
                travel_time = traci.edge.getTraveltime(edge)
                G.add_edge(edge, edge, travel_time=travel_time, length=length)

        return G

    def detect_congestion(self, threshold):
        congested_roads = []
        for edge in self.network_graph.edges(data=True):
            vehicle_count = traci.edge.getLastStepVehicleNumber(edge[0])
            if vehicle_count > threshold:
                congested_roads.append(edge[0])
        return congested_roads

    def select_vehicles(self, congested_roads, L):
        selected_vehicles = []
        for road in congested_roads:
            selected_vehicles.extend(traci.edge.getLastStepVehicleIDs(road))
        return selected_vehicles

    def compute_k_shortest_paths(self, origin, destination, k):
        return list(nx.shortest_simple_paths(self.network_graph, origin, destination, weight='travel_time'))[:k]

    def reroute_vehicles(self, selected_vehicles, strategy='EBkSP', k=3):
        for vehicle in selected_vehicles:
            current_edge = traci.vehicle.getRoadID(vehicle)
            destination = traci.vehicle.getDestination(vehicle)
            if strategy == 'DSP':
                new_path = self.dynamic_shortest_path(current_edge, destination)
            elif strategy == 'RkSP':
                new_path = self.random_k_shortest_paths(current_edge, destination, k)
            elif strategy == 'EBkSP':
                k_paths = self.compute_k_shortest_paths(current_edge, destination, k)
                new_path = min(k_paths, key=lambda p: self.calculate_path_popularity([p])[p])
            else:
                continue
            
            self.set_route(vehicle, new_path)

    def get_road_data(self, path):
        url = f"https://roads.googleapis.com/v1/snapToRoads?path={path}&key={self.google_maps_api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print("Error:", response.status_code, response.text)
            return None

    def set_route(self, vehicle, new_path):
        traci.vehicle.setRoute(vehicle, new_path)

    def run(self, congestion_threshold, L, strategy='EBkSP', k=3):
        step = 0
        while step < 1000:  # Run for a defined number of steps
            traci.simulationStep()
            congested_roads = self.detect_congestion(congestion_threshold)
            if congested_roads:
                selected_vehicles = self.select_vehicles(congested_roads, L)
                self.reroute_vehicles(selected_vehicles, strategy, k)
            step += 1

    async def connect_with_retry():
        while True:
            try:
                # Attempt to connect to the WebSocket server
                async with websockets.connect("ws://127.0.0.1:5678") as websocket:
                    print("Connected to WebSocket server")
                    traffic_manager = TrafficManager()
                    traffic_manager.send_vehicle_data_to_maps(websocket)
                    break  # Connection successful, exit the loop
            except (ConnectionRefusedError, TimeoutError) as e:
                print(f"Connection failed: {e}. Retrying in 1 second...")
                await asyncio.sleep(1)  # Retry after 1 second
            
    async def send_vehicle_data_to_maps(self, websocket):
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            vehicle_positions = self.get_vehicle_positions()
            for vehicle_id, lat, lon in vehicle_positions:
                road_data = self.get_road_data(f"{lat},{lon}")
                if road_data:
                    snapped_lat, snapped_lng = road_data['snappedPoints'][0]['location'].values()
                    vehicle_data = {"id": vehicle_id, "lat": snapped_lat, "lng": snapped_lng}
                    await websocket.send(json.dumps(vehicle_data))
    
    def run_simulation_trial(self, congestion_threshold, L, strategy, k):
        """
        Run a single simulation trial to evaluate a rerouting strategy.
        Returns: metrics like average travel time and congestion level.
        """
        traci.simulationStep()  # Initialize the simulation
        congested_roads = self.detect_congestion(congestion_threshold)
        
        if congested_roads:
            selected_vehicles = self.select_vehicles(congested_roads, L)
            self.reroute_vehicles(selected_vehicles, strategy, k)

        # Calculate average travel time and congestion level
        total_travel_time = np.mean([traci.edge.getTraveltime(edge) for edge in congested_roads])
        congestion_level = len(congested_roads) / len(self.network_graph.edges)
        
        return total_travel_time, congestion_level
    
    def monte_carlo_simulation(self, trials=100, congestion_threshold=10, L=5, k=3):
        """
        Perform Monte Carlo simulations to assess different rerouting strategies.
        Parameters:
        - trials: Number of Monte Carlo trials
        - congestion_threshold: Threshold for considering a road as congested
        - L: Limit on the number of vehicles to reroute per congested road
        - k: Number of shortest paths to consider for rerouting
        """
        results = {"average_travel_time": [], "congestion_levels": []}
        
        for i in range(trials):
            strategy = random.choice(['DSP', 'RkSP', 'EBkSP'])  # Randomly pick a strategy
            travel_time, congestion_level = self.run_simulation_trial(
                congestion_threshold, L, strategy, k
            )
            results["average_travel_time"].append(travel_time)
            results["congestion_levels"].append(congestion_level)
        
        # Calculate Monte Carlo results
        avg_travel_time = np.mean(results["average_travel_time"])
        avg_congestion_level = np.mean(results["congestion_levels"])
        
        print(f"Monte Carlo Simulation Results:")
        print(f"Average Travel Time: {avg_travel_time}")
        print(f"Average Congestion Level: {avg_congestion_level}")

    async def main(self):
        async with websockets.connect("ws://localhost:5678") as websocket:
            await self.send_vehicle_data_to_maps(websocket)
    
    def run(self, congestion_threshold=10, L=5, strategy='EBkSP', k=3):
        # Run Monte Carlo simulation
        self.monte_carlo_simulation(trials=100, congestion_threshold=congestion_threshold, L=L, k=k)
        
        # Run the main WebSocket function
        asyncio.run(self.main())

if __name__ == "__main__":
    sumo_binary = sumolib.checkBinary('sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "/Users/swetna/sumo/tests/complex/tutorial/circles/data/circles.sumocfg"]
    traci.start(sumo_cmd)

    traffic_manager = TrafficManager()
    traffic_manager.run()  # Run the Monte Carlo simulation and WebSocket connection

    traci.close()

# if __name__ == "__main__":
#     path = "34.0938,-118.3612|34.0635,-118.4455"  

#     sumo_binary = sumolib.checkBinary('sumo-gui')
#     sumo_cmd = [sumo_binary, "-c", "/Users/swetna/sumo/tests/complex/tutorial/circles/data/circles.sumocfg"]
#     traci.start(sumo_cmd)

#     # Start the WebSocket connection with retry logic
#     asyncio.run(connect_with_retry())

#     traci.close()
