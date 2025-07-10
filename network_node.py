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
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(NetworkNode, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, node_id: str, host: str = '0.0.0.0', port: int = 0):
        if NetworkNode._initialized:
            return
            
        self.node_id = node_id
        self.host = host
        self.port = port if port else random.randint(50000, 60000)
        self.known_nodes = {}  # node_id -> (host, port, last_seen)
        self.message_queue = None  # Will be initialized in start()
        self.seen_messages = set()  # Track seen message IDs
        self.running = False
        self.server = None
        self.session = None
        self._loop = None
        self._lock = asyncio.Lock()
        
        NetworkNode._initialized = True
        
    async def start(self):
        """Start the network node"""
        if self.running:
            return
            
        self._loop = asyncio.get_running_loop()
        
        # Create the message queue in the current event loop
        self.message_queue = asyncio.Queue()
        self.running = True
        
        # Create a new ClientSession with the current event loop
        self.session = aiohttp.ClientSession(loop=self._loop)
        
        # Start the server
        self.server = await asyncio.start_server(
            self._handle_connection,
            host=self.host,
            port=self.port
        )
        asyncio.create_task(self._message_processor())
        print(f"Node {self.node_id} listening on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop the network node"""
        if not self.running:
            return
            
        self.running = False
        
        async with self._lock:
            # Cancel any pending tasks
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if tasks:
                done, pending = await asyncio.wait(tasks, timeout=1.0)
                for task in pending:
                    if not task.done():
                        task.cancel()
            
            # Close server and session
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                self.server = None
            
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
            
            # Clear the message queue
            if self.message_queue:
                # Create a new empty queue to replace the old one
                try:
                    self.message_queue = asyncio.Queue()
                except RuntimeError:
                    # If event loop is closed, we can't create a new queue
                    self.message_queue = None
        
        # Clear the singleton instance
        NetworkNode._instance = None
        NetworkNode._initialized = False
    
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
                await self._process_message(message)
            except Exception as e:
                print(f"Error processing message: {e}")
    
    async def send_message(self, node_id: str, message: NetworkMessage):
        """Send a message to a specific node"""
        if not self.running or not self.message_queue:
            print("Node is not running or message queue not initialized")
            return
            
        if node_id not in self.known_nodes:
            print(f"Unknown node: {node_id}")
            return
            
        host, port, _ = self.known_nodes[node_id]
        
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(json.dumps(message.to_dict()).encode() + b'\n')
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"Error sending message to {node_id}: {e}")
    
    async def broadcast(self, message: NetworkMessage):
        """Broadcast a message to all known nodes"""
        if not self.running or not self.message_queue:
            print("Node is not running or message queue not initialized")
            return
            
        tasks = []
        for node_id in list(self.known_nodes.keys()):
            if node_id != self.node_id:  # Don't send to self
                tasks.append(self.send_message(node_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def discover_nodes(self, initial_nodes: List[tuple] = None):
        """Discover other nodes in the network
        
        Args:
            initial_nodes: List of tuples where each tuple can be either
                         (node_id, host, port) or (node_id, host, port, capabilities)
        """
        if initial_nodes:
            for node_info in initial_nodes:
                if len(node_info) >= 3:  # Handle both (id, host, port) and (id, host, port, capabilities)
                    node_id, host, port = node_info[:3]
                    if node_id != self.node_id:
                        self.known_nodes[node_id] = (host, port, time.time())
        
        msg = NetworkMessage(
            sender_id=self.node_id,
            message_type="node_announce",
            payload={
                "node_id": self.node_id,
                "host": self.host,
                "port": self.port,
                "timestamp": time.time()
            }
        )
        await self.broadcast(msg)
    
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
            broadcast_msg = NetworkMessage(
                sender_id=self.node_id,
                message_type="node_announce",
                payload=message.payload
            )
            broadcast_msg.ttl = message.ttl
            await self.broadcast(broadcast_msg)
    
    async def _handle_chat_message(self, message: NetworkMessage):
        """Handle chat messages"""
        print(f"\n[CHAT from {message.sender_id}]: {message.payload.get('text', '')}")
        
        # Forward the message if TTL allows
        if message.ttl > 1:
            message.ttl -= 1
            chat_msg = NetworkMessage(
                sender_id=self.node_id,
                message_type="chat_message",
                payload=message.payload
            )
            chat_msg.ttl = message.ttl
            await self.broadcast(chat_msg)
    
    async def send_chat_message(self, text: str):
        """Send a chat message to the network"""
        message = NetworkMessage(
            sender_id=self.node_id,
            message_type="chat_message",
            payload={'text': text, 'timestamp': time.time()}
        )
        await self.broadcast(message)

# Example usage
if __name__ == "__main__":
    async def main():
        # Create a node with a unique ID
        node = NetworkNode("node1", "localhost", 50000)
        await node.start()
        
        try:
            # Discover other nodes (you would typically have a list of bootstrap nodes)
            await node.discover_nodes([
                ("node2", "localhost", 50001, {}),
                ("node3", "localhost", 50002, {})
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
    
    asyncio.run(main())
