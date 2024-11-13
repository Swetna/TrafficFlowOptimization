import asyncio
import websockets
import json

# The WebSocket server will update with real-time vehicle data
async def send_vehicle_data(websocket, path):
    try:
        while True:
            # Vehicle data to be sent from TrafficManager (mocked here for testing)
            vehicle_data = [
                {"id": "veh1", "lat": 34.052235, "lng": -118.243683},
                {"id": "veh2", "lat": 34.052335, "lng": -118.243783},
            ]
            await websocket.send(json.dumps(vehicle_data))
            await asyncio.sleep(1)  # Adjust the sending interval as needed
    except websockets.exceptions.ConnectionClosedOK:
        print("Client disconnected. Waiting for new connection...")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    print("Starting WebSocket server on ws://localhost:5678...")
    async with websockets.serve(send_vehicle_data, "localhost", 5678):
        await asyncio.Future()  # Keep server running indefinitely

asyncio.run(main())
