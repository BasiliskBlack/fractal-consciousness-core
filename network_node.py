import asyncio
import json
import random
import time
from typing import Dict, List, Optional, Any
import aiohttp
from dataclasses import dataclass, asdict
import hashlib
import uuid

@dataclass
class NetworkMessage:
    sender_id: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: float = None
    message_id: str = None
    ttl: int = 5  # Time-to-live for message forwarding
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NetworkMessage':
        return cls(**data)

class NetworkNode:
    def __init__(self, node_id: str, host: str = '0.0.0.0', port: int = 0):
        self.node_id = node_id
        self.host = host
        self.port = port if port else random.randint(50000, 60000)
        self.known_nodes = {}  # node_id -> (host, port, last_seen)
        self.message_queue = asyncio.Queue()
        self.seen_messages = set()  # Track seen message IDs
        self.running = False
        self.server = None
        self.session = None
        
    async def start(self):
        """Start the network node"""
        self.running = True
        self.session = aiohttp.ClientSession()
        self.server = await asyncio.start_server(
            self._handle_connection,
            host=self.host,
            port=self.port
        )
        asyncio.create_task(self._message_processor())
        print(f"Node {self.node_id} listening on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop the network node"""
        self.running = False
        
        # Cancel any pending tasks
        tasks = [t for t in asyncio.all_tasks() 
                if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if tasks:
            await asyncio.wait(tasks, timeout=1.0)
            
        # Close server and session
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _handle_connection(self, reader, writer):
        """Handle incoming connections"""
        try:
            data = await reader.read(4096)
            message = json.loads(data.decode())
            await self._process_message(NetworkMessage.from_dict(message))
        except Exception as e:
            print(f"Error handling connection: {e}")
        finally:
            writer.close()
    
    async def _process_message(self, message: NetworkMessage):
        """Process incoming messages"""
        # Skip if we've seen this message before
        if message.message_id in self.seen_messages:
            return
        
        self.seen_messages.add(message.message_id)
        
        # Update last seen for the sender
        if message.sender_id != self.node_id:
            self.known_nodes[message.sender_id] = (
                message.payload.get('sender_host', 'unknown'),
                message.payload.get('sender_port', 0),
                time.time()
            )
        
        # Process message based on type
        handler_name = f"_handle_{message.message_type}"
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            await handler(message)
        else:
            # Default handling
            await self.message_queue.put(message)
    
    async def _message_processor(self):
        """Process messages from the queue"""
        while self.running:
            try:
                message = await self.message_queue.get()
                # Process message here
                print(f"Processing message: {message.message_type} from {message.sender_id}")
            except Exception as e:
                print(f"Error processing message: {e}")
    
    async def send_message(self, target_id: str, message_type: str, payload: Dict):
        """Send a message to a specific node"""
        if target_id not in self.known_nodes:
            # Only log this once per target to reduce noise
            if not hasattr(self, '_unknown_targets'):
                self._unknown_targets = set()
            if target_id not in self._unknown_targets:
                self._unknown_targets.add(target_id)
                print(f"  [NET] Unknown target node: {target_id} (this warning won't repeat)")
            return False
            
        target_host, target_port, _ = self.known_nodes[target_id]
        
        # Skip bootstrap nodes that are known to be unavailable
        if 'bootstrap' in target_id and hasattr(self, '_bootstrap_failed'):
            return False
        
        message = NetworkMessage(
            sender_id=self.node_id,
            message_type=message_type,
            payload=payload
        )
        
        try:
            # Use a short timeout for connections
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(target_host, target_port),
                timeout=2.0
            )
            try:
                writer.write(json.dumps(message.to_dict()).encode())
                await asyncio.wait_for(writer.drain(), timeout=2.0)
                return True
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                # Only log bootstrap connection errors once
                if 'bootstrap' in target_id and not hasattr(self, '_bootstrap_failed'):
                    self._bootstrap_failed = True
                return False
            finally:
                if not writer.is_closing():
                    writer.close()
                    try:
                        await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
                    except (asyncio.TimeoutError, ConnectionError, OSError):
                        pass
                        
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            # Don't log connection errors for bootstrap nodes after first failure
            if 'bootstrap' not in target_id:
                print(f"  [NET] Error connecting to {target_id}: {e}")
            return False
        except Exception as e:
            # Only log unexpected errors
            if not any(err in str(e) for err in ['Cannot connect to host', 'Connect call failed']):
                print(f"  [NET] Unexpected error sending to {target_id}: {e}")
            return False
    
    async def broadcast(self, message_type: str, payload: Dict, ttl: int = 5):
        """Broadcast a message to all known nodes"""
        message = NetworkMessage(
            sender_id=self.node_id,
            message_type=message_type,
            payload={
                **payload,
                'sender_host': self.host,
                'sender_port': self.port
            },
            ttl=ttl
        )
        
        tasks = []
        for node_id in list(self.known_nodes.keys()):
            if node_id != self.node_id:  # Don't send to self
                tasks.append(self.send_message(node_id, message_type, payload))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def discover_nodes(self, initial_nodes: List[tuple] = None):
        """Discover other nodes in the network"""
        if initial_nodes:
            for node_id, host, port in initial_nodes:
                if node_id != self.node_id:
                    self.known_nodes[node_id] = (host, port, time.time())
        
        # Broadcast our presence
        await self.broadcast(
            "node_announce",
            {
                'node_id': self.node_id,
                'host': self.host,
                'port': self.port,
                'capabilities': ['chat', 'file_share', 'compute']
            }
        )
    
    # Message handlers
    async def _handle_node_announce(self, message: NetworkMessage):
        """Handle node announcement messages"""
        if message.sender_id not in self.known_nodes:
            print(f"Discovered new node: {message.sender_id} at {message.payload.get('host')}:{message.payload.get('port')}")
        
        self.known_nodes[message.sender_id] = (
            message.payload.get('host'),
            message.payload.get('port'),
            time.time()
        )
        
        # Forward the announcement with reduced TTL
        if message.ttl > 1:
            message.ttl -= 1
            await self.broadcast("node_announce", message.payload, message.ttl)
    
    async def _handle_chat_message(self, message: NetworkMessage):
        """Handle chat messages"""
        print(f"\n[CHAT from {message.sender_id}]: {message.payload.get('text', '')}")
        
        # Forward the message if TTL allows
        if message.ttl > 1:
            message.ttl -= 1
            await self.broadcast("chat_message", message.payload, message.ttl)
    
    async def send_chat_message(self, text: str):
        """Send a chat message to the network"""
        await self.broadcast(
            "chat_message",
            {
                'text': text,
                'timestamp': time.time()
            }
        )

# Example usage
async def main():
    # Create and start a node
    node = NetworkNode(node_id="node1")
    await node.start()
    
    try:
        # Discover other nodes (you would typically have a list of bootstrap nodes)
        await node.discover_nodes([
            ("node2", "localhost", 50001),
            ("node3", "localhost", 50002)
        ])
        
        # Send a chat message
        await node.send_chat_message("Hello from node1!")
        
        # Keep the node running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await node.stop()

if __name__ == "__main__":
    asyncio.run(main())
