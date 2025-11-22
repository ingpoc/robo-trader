#!/usr/bin/env python3
"""
Test script to verify WebSocket Claude status broadcast
"""

import asyncio
import websockets
import json
from datetime import datetime

async def test_claude_status_websocket():
    """Test that WebSocket sends Claude status on connection."""

    uri = "ws://localhost:8000/ws"

    try:
        print(f"Connecting to WebSocket at {uri}...")

        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connected successfully")

            # Wait for messages
            messages_received = []

            # Collect messages for 5 seconds
            timeout = 5
            start_time = datetime.now()

            while (datetime.now() - start_time).total_seconds() < timeout:
                try:
                    # Wait for message with 1 second timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    messages_received.append(data)

                    print(f"Received message type: {data.get('type')}")

                    if data.get('type') == 'claude_status_update':
                        print("✓ Claude status update received!")
                        print(f"  Status: {data.get('status')}")
                        print(f"  Auth method: {data.get('auth_method')}")
                        print(f"  SDK connected: {data.get('sdk_connected')}")
                        print(f"  CLI process running: {data.get('cli_process_running')}")
                        print(f"  Timestamp: {data.get('timestamp')}")

                        # Check if status shows blue color (not grey)
                        status = data.get('status')
                        if status in ['connected/idle', 'analyzing', 'active', 'authenticated']:
                            print("✓ SUCCESS: Claude status indicates icon should be BLUE (not grey)")
                        else:
                            print(f"⚠️  WARNING: Claude status '{status}' might show grey icon")

                        return True

                except asyncio.TimeoutError:
                    # No message in this iteration, continue
                    pass
                except Exception as e:
                    print(f"Error processing message: {e}")
                    break

            print(f"\nReceived {len(messages_received)} total messages:")
            for i, msg in enumerate(messages_received):
                print(f"  {i+1}. Type: {msg.get('type')}, Timestamp: {msg.get('timestamp')}")

            if not any(msg.get('type') == 'claude_status_update' for msg in messages_received):
                print("❌ FAILURE: No Claude status update received within 5 seconds")
                print("\nExpected: WebSocket should send claude_status_update on connection")
                return False

    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

    return True

if __name__ == "__main__":
    print("Testing WebSocket Claude status broadcast...")
    print("=" * 50)

    result = asyncio.run(test_claude_status_websocket())

    print("=" * 50)
    if result:
        print("✅ TEST PASSED: Claude icon should now show correct color")
    else:
        print("❌ TEST FAILED: Claude icon issue persists")