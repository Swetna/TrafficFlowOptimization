import traci
import sumolib
import numpy as np
import networkx as nx
from collections import defaultdict
import requests
import asyncio
import websockets
import os
from dotenv import load_dotenv
import random
import json
import googlemaps
import firebase_admin
from firebase_admin import credentials, db , firestore

class TrafficManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.google_maps_api_key = "AIzaSyAcaHG4p9hs7nPuMAFFTNl3jNZC2x4KPyc"
        googlemaps.Client(self.google_maps_api_key)
        
        
        cred = credentials.Certificate("path/to/serviceAccountKey.json")
        firebase_admin.initialize_app(cred)

        self.db = firestore.client()  # Initialize Firestore


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

    async def send_vehicle_data_to_maps(self, websocket):
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            vehicle_positions = self.get_vehicle_positions()
            for vehicle_id, lat, lon in vehicle_positions:
                traffic_data = self.get_live_traffic_data(lat, lon)
                if traffic_data:
                    vehicle_data = {
                        "id": vehicle_id,
                        "lat": lat,
                        "lng": lon,
                        "traffic_speed": traffic_data["speed"]  # Adjust according to API response
                    }
                    await websocket.send(json.dumps(vehicle_data))
                    self.update_firebase(vehicle_data)  # Push to Firebase

    def update_firebase(self, vehicle_data):
        """Push vehicle data to Firebase Firestore"""
        for vehicle in vehicle_data:
            doc_ref = self.db.collection("vehicles").document(vehicle["id"])
            doc_ref.set(vehicle)
    
    def get_live_traffic_data(self, lat, lng):
        # Use the Roads API or Traffic Layer as appropriate for your needs.
        url = f"https://maps.googleapis.com/maps/api/trafficlayer/json?location={lat},{lng}&key={self.google_maps_api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()  # Parse as needed for your use case
        return None

    
    def build_network_graph(self):
        G = nx.DiGraph()
        edges = traci.edge.getIDList()
        
        for edge in edges:
            if edge in traci.edge.getIDList():
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

    async def connect_with_retry(self):
        while True:
            try:
                async with websockets.connect("ws://127.0.0.1:5678") as websocket:
                    print("Connected to WebSocket server")
                    await self.send_vehicle_data_to_maps(websocket)
                    break  # Exit the loop on successful connection
            except (ConnectionRefusedError, TimeoutError) as e:
                print(f"Connection failed: {e}. Retrying in 1 second...")
                await asyncio.sleep(1)

    def run_simulation_trial(self, congestion_threshold, L, strategy, k):
        traci.simulationStep()
        congested_roads = self.detect_congestion(congestion_threshold)
        
        if congested_roads:
            selected_vehicles = self.select_vehicles(congested_roads, L)
            self.reroute_vehicles(selected_vehicles, strategy, k)

        total_travel_time = np.mean([traci.edge.getTraveltime(edge) for edge in congested_roads])
        congestion_level = len(congested_roads) / len(self.network_graph.edges)
        
        return total_travel_time, congestion_level
    
    def monte_carlo_simulation(self, trials=100, congestion_threshold=10, L=5, k=3):
        results = {"average_travel_time": [], "congestion_levels": []}
        
        for i in range(trials):
            strategy = random.choice(['DSP', 'RkSP', 'EBkSP'])
            travel_time, congestion_level = self.run_simulation_trial(
                congestion_threshold, L, strategy, k
            )
            results["average_travel_time"].append(travel_time)
            results["congestion_levels"].append(congestion_level)
        
        avg_travel_time = np.mean(results["average_travel_time"])
        avg_congestion_level = np.mean(results["congestion_levels"])
        
        print(f"Monte Carlo Simulation Results:")
        print(f"Average Travel Time: {avg_travel_time}")
        print(f"Average Congestion Level: {avg_congestion_level}")

    async def main(self):
        await self.connect_with_retry()

    def run(self, congestion_threshold=10, L=5, strategy='EBkSP', k=3):
        self.monte_carlo_simulation(trials=100, congestion_threshold=congestion_threshold, L=L, k=k)
        asyncio.run(self.main())

if __name__ == "__main__":
    sumo_binary = sumolib.checkBinary('sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "/Users/swetna/sumo/tests/complex/tutorial/circles/data/circles.sumocfg"]
    traci.start(sumo_cmd)

    traffic_manager = TrafficManager()
    traffic_manager.run()

    traci.close()
