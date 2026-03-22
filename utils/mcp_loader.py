import os 
import json

def load_mcp_config(server_name: list[str] = None) -> dict:
    config_path = os.path.join(os.getcwd(), 'config/mcp_config.json')
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    if server_name:
        config = {key: value for key, value in config.items() if key in server_name}
        
    return config

if __name__ == "__main__":
    config = load_mcp_config(["web-search"])
    print(config)