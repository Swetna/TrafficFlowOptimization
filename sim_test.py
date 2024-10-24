import traci
import sumolib

# Define SUMO binary and configuration file
sumo_binary = sumolib.checkBinary('sumo-gui')  # or 'sumo-gui' for graphical output
# sumo_cmd = [sumo_binary, "-c", "/Users/swetna/sumo/tests/complex/tutorial/circles/data/circles.sumocfg"]  # Path to your SUMO configuration file
sumo_cmd = [sumo_binary, "-c","/Users/swetna/sumo/tests/complex/tutorial/public_transport/data/run.sumocfg"]
# Start SUMO with TraCI
traci.start(sumo_cmd)

# Run the simulation step by step
for step in range(200):
    traci.simulationStep()  # Advance simulation by one step
    
    # Get data about the vehicles
    vehicle_ids = traci.vehicle.getIDList()  # Get list of all vehicles in the simulation
    for vehicle_id in vehicle_ids:
        position = traci.vehicle.getPosition(vehicle_id)  # Get vehicle position
        speed = traci.vehicle.getSpeed(vehicle_id)  # Get vehicle speed
        print(f"Vehicle {vehicle_id}: Position {position}, Speed {speed}")
        
    # Example: Change the speed of a vehicle
    if vehicle_ids:
        traci.vehicle.setSpeed(vehicle_ids[0], 10)  # Set speed of first vehicle to 10 m/s

# Close TraCI and SUMO
traci.close()
