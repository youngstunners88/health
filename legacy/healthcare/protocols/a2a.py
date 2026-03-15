import json
import base64
import hashlib
from datetime import datetime

def sign_message(payload: dict, agent_id: str) -> str:
    """Mock A2A message signing (replace with real crypto in prod)"""
    message = json.dumps(payload, sort_keys=True) + agent_id + datetime.utcnow().isoformat()
    signature = base64.b64encode(hashlib.sha256(message.encode())).digest().decode()
    return f"{agent_id}.{signature}"

def verify_message(signed: str, agent_id: str) -> bool:
    """Mock verification"""
    try:
        agent, sig = signed.split(".", 1)
        # In real implementation, verify signature
        return agent == agent_id
    except:
        return False

def route_message(message: dict, target_agent: str) -> dict:
    """Add routing info"""
    message["to"] = target_agent
    message["timestamp"] = datetime.utcnow().isoformat()
    return message

def send_a2a_message(payload: dict, agent_id: str, target_agent: str) -> dict:
    """Create, sign, and route an A2A message"""
    signed_payload = sign_message(payload, agent_id)
    routed = route_message({**payload, "signature": signed_payload, "from": agent_id}, target_agent)
    return routed