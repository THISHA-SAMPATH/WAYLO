import os
import requests

NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "your_nebius_api_key_here")
NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1"  # Replace with exact endpoint from Nebius dashboard

def analyze_spatial_frame(image_payload, user_intent="align_doorway"):
    """
    Sends spatial frames to NVIDIA Nemotron/Cosmos on Nebius Token Factory
    to calculate dynamic clearance buffers and steering adjustments.
    """
    headers = {
        "Authorization": f"Bearer {NEBIUS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "nvidia/nemotron-3-ultra", # Or nvidia/cosmos for vision-spatial tasks
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are WAYLO, a shared-autonomy mobility copilot. Analyze room boundaries, "
                    "doorway alignment, and dynamic obstacles. Return JSON with 'clearance_left', "
                    "'clearance_right', 'steering_correction_deg', and 'emergency_stop'."
                )
            },
            {
                "role": "user",
                "content": f"User Intent: {user_intent}. Frame payload: {image_payload}"
            }
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(f"{NEBIUS_BASE_URL}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error calling Nebius API: {e}")
        return None

if __name__ == "__main__":
    print("Testing WAYLO Nebius Client...")
    res = analyze_spatial_frame(image_payload="mock_frame_data_001")
    print("Inference Result:", res)