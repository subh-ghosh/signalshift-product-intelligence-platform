import requests
import time

print("Starting sync...")
requests.post('http://localhost:8002/sync/reviews')

seen_states = set()
start_time = time.time()

while time.time() - start_time < 300: # max 5 mins test
    r = requests.get('http://localhost:8002/upload-progress')
    data = r.json()
    state = data.get('status')
    
    if state not in seen_states:
        seen_states.add(state)
        print(f"\n[{time.strftime('%M:%S')}] State changed to: {state}")
    
    print(f"\r{state} - {data.get('processed')}/{data.get('total')} (ETA: {data.get('eta_seconds')}s)", end="")
    
    if state == "topic": # Once it hits topic, we know sentiment works. 
        print("\nPipeline successfully transitioned through scraping and sentiment. Stopping early for test.")
        requests.post('http://localhost:8002/stop-upload')
        break
        
    time.sleep(1)
