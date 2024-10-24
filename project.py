import traci
import sumolib
import numpy as np
import networkx as nx
from collections import defaultdict

class TrafficManager:
    def __init__(self):
        self.footprint_counter = defaultdict(int)
        self.vehicle_counts = defaultdict(int)
        self.network_graph = self.build_network_graph()

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

if __name__ == "__main__":
    # sumoCmd = ["sumo", "-c", "/Users/swetna/sumo/tests/complex/tutorial/circles/data/circles.sumocfg"]  
    
    
    sumo_binary = sumolib.checkBinary('sumo-gui')  # or 'sumo-gui' for graphical output
    sumo_cmd = [sumo_binary, "-c", "/Users/swetna/sumo/tests/complex/tutorial/circles/data/circles.sumocfg"]  # Path to your SUMO configuration file
    traci.start(sumo_cmd)

    traffic_manager = TrafficManager()
    traffic_manager.run(congestion_threshold=5, L=1, strategy='EBkSP', k=3)

    traci.close()
