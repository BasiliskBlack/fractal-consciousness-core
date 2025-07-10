import os
import json
import random
import time
import asyncio
import aiohttp
import yaml
import importlib.util
import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Tuple

# Import network node functionality
from network_node import NetworkNode, NetworkMessage

class ShotNode:
    def __init__(self, node_id: str = None, memory_file: str = "memory.json"):
        self.node_id = node_id or f"node_{random.randint(1000, 9999)}"
        self.memory_file = memory_file
        self.memory = self.load_memory()
        self.stealth_mode = False
        self.command_map = self._init_command_map()
        self.glyphs = self._load_glyphs()
        
        # Initialize interpreter and network
        self.interpreter = None  # MundenInterpreter(self)
        self.running = False
        self.network_task = None
        
        # Get or create event loop
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        # Initialize memory structures
        self.load_memory()
        
        # Initialize network node
        self.network = NetworkNode(
            node_id=node_id or f"shotnet_{uuid.uuid4().hex[:8]}",
            host='0.0.0.0',
            port=random.randint(50000, 60000)
        )
        
        # Initialize network tracking attributes
        self.connected_nodes = set()
        self.node_last_seen = {}
        self.known_nodes = {}
        
        # Ensure required memory structures
        if 'node_capabilities' not in self.memory:
            self.memory['node_capabilities'] = {
                'process': True,
                'store': True,
                'compute': True
            }
        
        # Start network in a non-blocking way
        async def startup_wrapper():
            try:
                await self._startup()
            except Exception as e:
                print(f"  [ERROR] Failed to start network: {e}")
                self.running = False
        
        self.network_task = self.loop.create_task(startup_wrapper())
        
        # Run the event loop in a separate thread
        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()

    async def _startup(self):
        """Initialize the ShotNET node"""
        try:
            print(f"Node {self.node_id} starting up...")
            
            # Initialize memory if needed
            if not hasattr(self, 'memory'):
                self.load_memory()
                
            # Ensure required memory structures exist
            if 'connected_nodes' not in self.memory:
                self.memory['connected_nodes'] = set()
            if 'known_resources' not in self.memory:
                self.memory['known_resources'] = {}
            
            # Start network if not already started
            if hasattr(self, 'network') and self.network:
                if not hasattr(self.network, 'running') or not self.network.running:
                    await self.network.start()
                    print(f"Node {self.node_id} listening on {self.network.host}:{self.network.port}")
            
            # Register message handlers if available
            if hasattr(self.network, 'message_handlers'):
                self.network.message_handlers.update({
                    'resource_announce': self._handle_resource_announce,
                    'knowledge_update': self._handle_knowledge_update,
                    'node_capabilities': self._handle_node_capabilities,
                    'node_announce': self._handle_node_announce,
                    'node_leave': self._handle_node_leave
                })
            
            # Discover other nodes if not in stealth mode
            if not getattr(self, 'stealth_mode', False):
                bootstrap_nodes = self.memory.get('bootstrap_nodes', [
                    ("bootstrap1", "localhost", 50001),
                    ("bootstrap2", "localhost", 50002)
                ])
                if bootstrap_nodes:
                    try:
                        # Convert bootstrap nodes to the expected format
                        nodes = [{"node_id": node[0], "host": node[1], "port": node[2]} 
                               for node in bootstrap_nodes]
                        await self.network.discover_nodes(nodes)
                    except Exception as e:
                        print(f"  [INFO] Could not connect to bootstrap nodes: {e}")
                        print("  [INFO] Running in standalone mode")
            
            # Announce our presence if not in stealth mode
            if not getattr(self, 'stealth_mode', False):
                await self._announce_presence()
            
            self.running = True
            return "ShotNET node started successfully"
            
        except Exception as e:
            self.running = False
            return f"Startup failed: {str(e)}"
            
    async def _share_knowledge(self, target_node_id=None):
        """Share knowledge with other nodes.
        
        Args:
            target_node_id: Specific node to share with, or None to share with all
            
        Returns:
            str: Status message
        """
        try:
            if not hasattr(self, 'network') or not self.network:
                return "Network not initialized"
                
            # Prepare knowledge to share
            knowledge = {
                'node_id': self.node_id,
                'timestamp': time.time(),
                'codex': self.memory.get('codex', []),
                'known_nodes': list(self.memory['connected_nodes']),
                'resources': list(self.memory['known_resources'].keys())
            }
            
            if target_node_id:
                # Share with specific node
                if target_node_id in self.memory['connected_nodes']:
                    await self.network.send_message(
                        target_node_id,
                        'knowledge_update',
                        knowledge
                    )
                    return f"Shared knowledge with {target_node_id}"
                return f"Not connected to {target_node_id}"
            else:
                # Broadcast to all connected nodes
                if not self.memory['connected_nodes']:
                    return "No connected nodes to share with"
                    
                for node_id in list(self.memory['connected_nodes']):
                    try:
                        await self.network.send_message(
                            node_id,
                            'knowledge_update',
                            knowledge
                        )
                    except Exception as e:
                        print(f"  [WARNING] Failed to share with {node_id}: {e}")
                return f"Shared knowledge with {len(self.memory['connected_nodes'])} nodes"
                
        except Exception as e:
            return f"Knowledge sharing failed: {str(e)}"
        
    async def _announce_presence(self):
        """Announce our presence to the network"""
        if not hasattr(self, 'network') or not self.network:
            return
            
        try:
            if 'node_capabilities' not in self.memory:
                self.memory['node_capabilities'] = {
                    'process': True,
                    'store': True,
                    'compute': True
                }
            
            # Get connected peers if any
            known_nodes = getattr(self.network, 'known_nodes', {}) or {}
            nodes_to_announce = list(known_nodes.keys())
            
            # If no connected peers, try bootstrap nodes
            if not nodes_to_announce:
                bootstrap_nodes = self.memory.get('bootstrap_nodes', [
                    ("bootstrap1", "localhost", 50001),
                    ("bootstrap2", "localhost", 50002)
                ])
                
                # Only show bootstrap message once
                if not hasattr(self, '_bootstrap_attempted'):
                    self._bootstrap_attempted = True
                    print("  [NET] No connected peers, trying bootstrap nodes...")
                
                # Only try bootstrap nodes occasionally (every 30 seconds)
                current_time = time.time()
                last_attempt = getattr(self, '_last_bootstrap_attempt', 0)
                if current_time - last_attempt > 30:  # 30 second cooldown
                    self._last_bootstrap_attempt = current_time
                    nodes_to_announce = [node[0] for node in bootstrap_nodes]
                    
                    # Add bootstrap nodes to known nodes if they're not already there
                    for node_id, host, port in bootstrap_nodes:
                        if node_id not in known_nodes:
                            known_nodes[node_id] = {
                                'host': host,
                                'port': port,
                                'last_seen': time.time()
                            }
                else:
                    return  # Skip this announcement attempt
            
            # Create announcement message
            announcement = {
                'node_id': self.node_id,
                'host': getattr(self.network, 'host', 'localhost'),
                'port': getattr(self.network, 'port', 0),
                'capabilities': self.memory.get('node_capabilities', {}),
                'timestamp': time.time()
            }
            
            # Send announcement to all target nodes
            for node_id in nodes_to_announce:
                if node_id == self.node_id:
                    continue  # Don't send to self
                    
                node_info = known_nodes.get(node_id, {})
                if not node_info:
                    continue
                    
                try:
                    # Create a network message
                    message = NetworkMessage(
                        sender_id=self.node_id,
                        message_type='node_announce',
                        payload=announcement
                    )
                    
                    # Send the message
                    if hasattr(self.network, 'send_message'):
                        await self.network.send_message(node_id, message)
                        
                    # If we had a previous failure, log success
                    if hasattr(self, '_bootstrap_failed_shown'):
                        print(f"  [NET] Successfully reconnected to {node_id}")
                        delattr(self, '_bootstrap_failed_shown')
                        
                except Exception as e:
                    if not hasattr(self, '_bootstrap_failed_shown'):
                        print(f"  [NET] Failed to announce to {node_id}: {e}")
                        self._bootstrap_failed_shown = True
                        
        except Exception as e:
            print(f"  [WARNING] Failed to announce presence: {e}")
            import traceback
            traceback.print_exc()
            
    async def _handle_node_announce(self, message):
        """Handle node announcement messages"""
        try:
            node_id = message.get('node_id')
            capabilities = message.get('capabilities', [])
            
            if node_id != self.node_id:  # Don't process our own announcements
                print(f"  [NET] Node announced: {node_id} (capabilities: {', '.join(map(str, capabilities))})")
                
                # Initialize node_capabilities if it doesn't exist
                if 'node_capabilities' not in self.memory:
                    self.memory['node_capabilities'] = {}
                
                # Ensure capabilities is a list
                if not isinstance(capabilities, list):
                    capabilities = list(capabilities) if hasattr(capabilities, '__iter__') else [str(capabilities)]
                
                # Update node capabilities
                self.memory['node_capabilities'][node_id] = capabilities
                
                # Ensure connected_nodes exists and is a set
                if 'connected_nodes' not in self.memory:
                    self.memory['connected_nodes'] = set()
                elif not isinstance(self.memory['connected_nodes'], set):
                    self.memory['connected_nodes'] = set(self.memory['connected_nodes'])
                
                # Add to connected nodes if not already present
                if node_id not in self.memory['connected_nodes']:
                    self.memory['connected_nodes'].add(node_id)
                    print(f"  [NET] Added {node_id} to connected nodes")
                    
        except Exception as e:
            print(f"  [ERROR] Error handling node announcement: {e}")
            import traceback
            traceback.print_exc()
            
    async def _handle_knowledge_update(self, message):
        """Handle knowledge update messages"""
        try:
            node_id = message.get('node_id')
            codex = message.get('codex', [])
            known_nodes = message.get('known_nodes', [])
            resources = message.get('resources', [])
            
            print(f"  [NET] Received knowledge update from {node_id}")
            
            # Update our codex with new commands
            if 'codex' not in self.memory:
                self.memory['codex'] = []
                
            for cmd in codex:
                if cmd not in self.memory['codex']:
                    self.memory['codex'].append(cmd)
            
            # Update known nodes
            for node in known_nodes:
                if node != self.node_id and node not in self.memory['connected_nodes']:
                    self.memory['connected_nodes'].add(node)
            
            # Update known resources
            for resource in resources:
                if resource not in self.memory['known_resources']:
                    self.memory['known_resources'][resource] = {
                        'source': node_id,
                        'timestamp': time.time()
                    }
            
            return "Knowledge updated successfully"
            
        except Exception as e:
            return f"Error updating knowledge: {str(e)}"

    async def discover_nodes(self) -> str:
        """Discover other nodes in the network"""
        try:
            msg = NetworkMessage(
                sender_id=self.node_id,
                message_type='node_discovery',
                payload={'node_id': self.node_id, 'timestamp': time.time()}
            )
            await self.network.broadcast(msg)
            return "Node discovery initiated"
        except Exception as e:
            return f"Failed to discover nodes: {str(e)}"
            
    async def connect_to_node(self, node_id: str, address: str) -> str:
        """Connect to a specific node"""
        try:
            if node_id == self.node_id:
                return "Cannot connect to self"
                
            if node_id in self.memory['connected_nodes']:
                return f"Already connected to {node_id}"
                
            # In a real implementation, we would establish a connection here
            # For now, we'll just add it to our connected nodes
            self.memory['connected_nodes'].add(node_id)
            
            # Store the node's address for future reference
            if 'node_addresses' not in self.memory:
                self.memory['node_addresses'] = {}
            self.memory['node_addresses'][node_id] = address
            
            return f"Connected to {node_id} at {address}"
            
        except Exception as e:
            return f"Failed to connect to {node_id}: {str(e)}"
            
    async def list_nodes(self) -> List[str]:
        """List all connected nodes"""
        return list(self.memory['connected_nodes'])
        
    async def share_resource(self, resource_type: str, resource_data: Dict) -> str:
        """Share a resource with connected nodes"""
        try:
            resource_id = f"{resource_type}_{int(time.time())}"
            
            # Store the resource locally
            if 'resources' not in self.memory:
                self.memory['resources'] = {}
            self.memory['resources'][resource_id] = {
                'type': resource_type,
                'data': resource_data,
                'timestamp': time.time(),
                'source': self.node_id
            }
            
            # Share with the network
            msg = NetworkMessage(
                sender_id=self.node_id,
                message_type='resource_announce',
                payload={
                    'resource_id': resource_id,
                    'type': resource_type,
                    'data': resource_data,
                    'timestamp': time.time()
                }
            )
            
            await self.network.broadcast(msg)
            
            return f"Shared resource {resource_id}"
            
        except Exception as e:
            return f"Failed to share resource: {str(e)}"
            
    async def list_resources(self, resource_type: str = None) -> List[Dict]:
        """List available resources, optionally filtered by type"""
        resources = self.memory.get('resources', {})
        if resource_type:
            return [r for r in resources.values() if r.get('type') == resource_type]
        return list(resources.values())
        
    async def _handle_resource_announce(self, message: Dict, sender: str):
        """Handle incoming resource announcements"""
        resource_id = message.get('resource_id')
        if not resource_id:
            return
            
        # Store the resource
        if 'resources' not in self.memory:
            self.memory['resources'] = {}
            
        self.memory['resources'][resource_id] = {
            'type': message.get('type'),
            'data': message.get('data'),
            'source': sender,
            'timestamp': message.get('timestamp', time.time())
        }
        
    async def _handle_knowledge_update(self, message: Dict, sender: str):
        """Handle incoming knowledge updates"""
        update_type = message.get('type')
        data = message.get('data', {})
        
        if update_type == 'full_sync':
            # Merge codex entries
            if 'codex' in data and isinstance(data['codex'], list):
                if 'codex' not in self.memory:
                    self.memory['codex'] = []
                self.memory['codex'].extend(
                    entry for entry in data['codex']
                    if entry not in self.memory['codex']
                )
                
            # Merge glyphs
            if 'glyphs' in data and isinstance(data['glyphs'], dict):
                if 'glyphs' not in self.memory:
                    self.memory['glyphs'] = {}
                self.memory['glyphs'].update(data['glyphs'])
                
    async def _handle_node_capabilities(self, message: Dict, sender: str):
        """Handle node capability announcements"""
        if 'node_capabilities' not in self.memory:
            self.memory['node_capabilities'] = {}
            
        self.memory['node_capabilities'][sender] = {
            'capabilities': message.get('capabilities', []),
            'last_seen': time.time()
        }
    
    def _init_command_map(self) -> Dict[str, Callable]:
        return {
            # Core commands
            "scan": self.scan,
            "mutate": self.mutate,
            "optimize": self.optimize,
            "sync": self.sync,
            "stealth": self.toggle_stealth,
            
            # Glyphs
            "Σ": self.scan,
            "Δ": self.mutate,
            "Ω": self.optimize,
            "Ψ": self.sync,
            "Λ": self.toggle_stealth,
            "~": self.loop,
            "↻": self.recurse,
            "∇": self.invert,
            "Θ": self.observe,
            "Ϟ": self.shock,
            
            # Network commands
            "discover": self.discover_nodes,
            "connect": self.connect_to_node,
            "nodes": self.list_nodes,
            "share": self.share_resource,
            "resources": self.list_resources
        }

    def _load_glyphs(self) -> Dict[str, Dict[str, str]]:
        glyphs_path = os.path.join("data", "glyphs.json")
        if os.path.exists(glyphs_path):
            with open(glyphs_path, "r") as f:
                return json.load(f)
        return {}

    def load_memory(self) -> Dict:
        """Load memory from disk and ensure proper data types"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    loaded_memory = json.load(f)
                    
                    # Ensure loaded memory is a dictionary
                    if not isinstance(loaded_memory, dict):
                        loaded_memory = {}
                    
                    # Convert lists to sets where needed
                    if 'connected_nodes' in loaded_memory and isinstance(loaded_memory['connected_nodes'], list):
                        loaded_memory['connected_nodes'] = set(loaded_memory['connected_nodes'])
                    
                    self.memory = loaded_memory
            else:
                self.memory = {}
                
        except Exception as e:
            print(f"  [WARNING] Error loading memory: {e}")
            self.memory = {}
        
        # Set default values if they don't exist
        default_memory = {
            'connected_nodes': set(),
            'known_resources': {},
            'node_capabilities': {},
            'codex': [],
            'sync_logs': [],
            'commands_run': [],
            'mutations': [],
            'config': {
                'autonomous': True,
                'learning_rate': 0.1,
                'exploration_rate': 0.3,
                'max_network_size': 100,
                'resource_ttl': 3600
            },
            'bootstrap_nodes': [
                ("bootstrap1", "localhost", 50001),
                ("bootstrap2", "localhost", 50002)
            ],
            'learning_data': {
                'patterns': {},
                'success_rates': {},
                'preferences': {}
            },
            'stealth_mode': False,
            'timestamp': time.time()
        }
        
        # Ensure all required keys exist with proper types
        for key, default_value in default_memory.items():
            if key not in self.memory:
                self.memory[key] = default_value
            elif key == 'connected_nodes' and not isinstance(self.memory[key], set):
                self.memory[key] = set(self.memory[key]) if hasattr(self.memory[key], '__iter__') and not isinstance(self.memory[key], (str, bytes)) else set()
            elif key == 'node_capabilities' and not isinstance(self.memory[key], dict):
                self.memory[key] = {}
        
        return self.memory
        
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def save_memory(self):
        """Save memory to disk with proper JSON serialization"""
        try:
            # Convert sets to lists for JSON serialization
            memory_copy = self.memory.copy()
            if 'connected_nodes' in memory_copy and isinstance(memory_copy['connected_nodes'], set):
                memory_copy['connected_nodes'] = list(memory_copy['connected_nodes'])
            
            with open(self.memory_file, 'w') as f:
                json.dump(memory_copy, f, indent=2)
            return True
        except Exception as e:
            print(f"  [WARNING] Error saving memory: {e}")
            return False

    async def execute(self, command: str) -> Optional[str]:
        if not command:
            return None
            
        cmd = command.lower().strip()
        if cmd in self.command_map:
            func = self.command_map[cmd]
            
            # If the function is a coroutine, await it
            if asyncio.iscoroutinefunction(func):
                result = await func()
            else:
                result = func()
                
            self.memory["commands_run"].append({
                "command": cmd,
                "timestamp": time.time(),
                "result": str(result)[:500]  # Limit result size
            })
            await self._learn_from_execution(cmd, result)
            self.save_memory()
            return result
        return f"Unknown command: {cmd}"

    async def _learn_from_execution(self, command: str, result: Any):
        """Learn from command execution"""
        # Update success/failure rates
        success = result is not None and not isinstance(result, Exception)
        self.memory['learning_data']['success_rates'][command] = \
            self.memory['learning_data']['success_rates'].get(command, {'success': 0, 'total': 0})
        
        if success:
            self.memory['learning_data']['success_rates'][command]['success'] += 1
        self.memory['learning_data']['success_rates'][command]['total'] += 1
        
        # Update patterns
        context = {
            'time': time.time(),
            'stealth': self.stealth_mode,
            'node_count': len(self.connected_nodes)
        }
        
        if command not in self.memory['learning_data']['patterns']:
            self.memory['learning_data']['patterns'][command] = []
        self.memory['learning_data']['patterns'][command].append({
            'context': context,
            'success': success,
            'timestamp': time.time()
        })
        
        # Keep only recent patterns
        max_patterns = 1000
        for cmd in self.memory['learning_data']['patterns']:
            self.memory['learning_data']['patterns'][cmd] = \
                sorted(self.memory['learning_data']['patterns'][cmd], 
                      key=lambda x: x['timestamp'],
                      reverse=True)[:max_patterns]
    
    async def scan(self) -> str:
        """Enhanced scan that checks both local and network resources"""
        local_scan = f"Local node {self.node_id} status: {'STEALTH' if self.stealth_mode else 'ACTIVE'}\n"
        local_scan += f"Memory usage: {len(str(self.memory))} bytes\n"
        local_scan += f"Known glyphs: {len(self.glyphs)}"
        
        # Network scan
        network_scan = "\n\nNetwork Status:\n"
        network_scan += f"Connected nodes: {len(self.connected_nodes)}\n"
        network_scan += f"Known resources: {len(self.known_resources)}"
        
        # Resource discovery
        await self._discover_resources()
        
        return local_scan + network_scan

    async def mutate(self) -> str:
        """Apply mutations with network awareness"""
        mutation_id = f"mutation_{int(time.time())}"
        mutation = {
            'id': mutation_id,
            'timestamp': time.time(),
            'node': self.node_id,
            'changes': {}
        }
        
        # Apply random mutations based on current state
        if random.random() < 0.3:  # 30% chance to modify behavior
            mutation['changes']['behavior'] = random.choice([
                'increase_learning_rate',
                'decrease_learning_rate',
                'adjust_exploration',
                'modify_network_strategy'
            ])
        
        if random.random() < 0.2:  # 20% chance to modify network behavior
            mutation['changes']['network'] = random.choice([
                'increase_node_connections',
                'discover_new_nodes',
                'optimize_routing'
            ])
        
        self.memory["mutations"].append(mutation)
        
        # Share mutation with network
        await self._share_knowledge('mutation', mutation)
        
        return f"Applied mutation: {mutation_id} - {mutation['changes']}"

    async def optimize(self) -> str:
        """Run optimization routines"""
        optimizations = []
        
        # Clean up old data
        old_count = len(self.memory.get('commands_run', []))
        self.memory['commands_run'] = [
            cmd for cmd in self.memory.get('commands_run', [])
            if time.time() - cmd.get('timestamp', 0) < 604800  # 1 week
        ]
        optimizations.append(f"Cleaned {old_count - len(self.memory['commands_run'])} old commands")
        
        # Optimize network connections
        if len(self.connected_nodes) > self.memory['config'].get('max_network_size', 100):
            # Disconnect from least responsive nodes
            node_responsiveness = {}
            for node_id in list(self.connected_nodes):
                # Simple responsiveness check - in real implementation, track actual response times
                node_responsiveness[node_id] = random.random()
            
            # Keep top N nodes
            keep_nodes = sorted(node_responsiveness.items(), 
                              key=lambda x: x[1], 
                              reverse=True)[:self.memory['config'].get('max_network_size', 100)]
            
            disconnect_count = len(self.connected_nodes) - len(keep_nodes)
            self.connected_nodes = set(node_id for node_id, _ in keep_nodes)
            optimizations.append(f"Optimized network: disconnected from {disconnect_count} nodes")
        
        # Clean up old resources
        now = time.time()
        old_resources = len(self.known_resources)
        self.known_resources = {
            k: v for k, v in self.known_resources.items()
            if now - v.get('last_accessed', 0) < self.memory['config'].get('resource_ttl', 3600)
        }
        optimizations.append(f"Cleaned {old_resources - len(self.known_resources)} old resources")
        
        # Save optimizations
        self.save_memory()
        
        if optimizations:
            return "Optimization complete: " + "; ".join(optimizations)
        return "No optimizations needed"

    async def sync(self) -> str:
        """Synchronize with network and external resources"""
        sync_time = time.time()
        results = []
        
        # Initialize connected_nodes if it doesn't exist
        if not hasattr(self, 'connected_nodes'):
            self.connected_nodes = set()
        
        # Sync with connected nodes if any
        if self.connected_nodes:
            tasks = []
            for node_id in list(self.connected_nodes):
                tasks.append(self._sync_with_node(node_id))
            
            try:
                node_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend(str(r) for r in node_results if r)
            except Exception as e:
                results.append(f"Node sync error: {str(e)}")
        else:
            results.append("No connected nodes to sync with")
        
        # Sync with external resources (GitHub, etc.)
        if 'github_repo' in self.memory.get('config', {}):
            try:
                github_sync = await self.sync_from_github(self.memory['config']['github_repo'])
                results.append(f"GitHub: {github_sync}")
            except Exception as e:
                results.append(f"GitHub sync failed: {str(e)}")
        
        self.memory["last_sync"] = sync_time
        self.save_memory()
        
        result = f"Synchronization complete at {time.ctime(sync_time)}"
        if results:
            result += "\n" + "\n".join(f"- {r}" for r in results)
        
        return result
    
    async def _sync_with_node(self, node_id: str) -> str:
        """Synchronize data with a specific node"""
        try:
            # Create a network message for sync
            message = NetworkMessage(
                sender_id=self.node_id,
                message_type='knowledge_update',
                payload={
                    'type': 'full_sync',
                    'data': {
                        'codex': self.memory.get('codex', []),
                        'glyphs': self.memory.get('glyphs', {})
                    }
                }
            )
            
            # Send the message
            if hasattr(self.network, 'send_message'):
                await self.network.send_message(node_id, message)
                return f"Synced with {node_id}"
            return f"No send_message method on network node"
        except Exception as e:
            return f"Failed to sync with {node_id}: {str(e)}"

    def toggle_stealth(self) -> str:
        self.stealth_mode = not self.stealth_mode
        return f"Stealth mode {'activated' if self.stealth_mode else 'deactivated'}"

    def loop(self) -> str:
        return "Entering recursive execution loop"

    def recurse(self) -> str:
        return "Recursive function call initiated"

    def invert(self) -> str:
        return "Function behavior inverted"

    def observe(self) -> str:
        return "Observation protocol active"

    def shock(self) -> str:
        return "Disruption protocol activated"

    async def _stop_network(self):
        """Stop network services."""
        if hasattr(self, 'network') and self.network:
            try:
                # Notify peers of graceful shutdown
                if hasattr(self, 'connected_nodes') and self.connected_nodes:
                    for node_id in list(self.connected_nodes):
                        try:
                            message = NetworkMessage(
                                sender_id=self.node_id,
                                message_type='node_leave',
                                payload={
                                    'node_id': self.node_id,
                                    'timestamp': time.time()
                                }
                            )
                            await self.network.send_message(node_id, message)
                        except Exception as e:
                            print(f"[NETWORK] Error notifying {node_id} of shutdown: {e}")
                
                # Stop network services
                await self.network.stop()
                
            except Exception as e:
                print(f"[NETWORK] Error during network shutdown: {e}")
            finally:
                self.network = None
                if hasattr(self, 'connected_nodes'):
                    self.connected_nodes.clear()

    async def cleanup(self):
        """Clean up resources"""
        if not hasattr(self, 'running') or not self.running:
            return "Already shutting down"
            
        self.running = False
        print("\n[SHOTNET] Cleaning up resources...")
        
        try:
            # Stop network first
            if hasattr(self, 'network') and self.network:
                print("  - Shutting down network...")
                try:
                    # Don't wait for leave messages - just cancel them
                    if hasattr(self.network, 'stop'):
                        try:
                            # Use a short timeout for network shutdown
                            await asyncio.wait_for(self.network.stop(), timeout=1.0)
                        except asyncio.TimeoutError:
                            print("  [INFO] Network stop timed out, forcing shutdown")
                except Exception as e:
                    print(f"  [WARNING] Error during network shutdown: {e}")
            
            # Get current tasks to cancel
            try:
                tasks = [t for t in asyncio.all_tasks() 
                        if t is not asyncio.current_task() and not t.done()]
                
                if tasks:
                    print(f"  - Cancelling {len(tasks)} pending tasks...")
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    
                    # Wait for tasks to complete, but don't fail on cancellation
                    if tasks:
                        try:
                            await asyncio.wait(tasks, timeout=1.0)
                        except Exception as e:
                            print(f"  [INFO] Task cancellation completed with: {e}")
                            
            except Exception as e:
                print(f"  [WARNING] Error during task cancellation: {e}")
            
            # Save memory state
            print("  - Saving memory state...")
            try:
                self.save_memory()
            except Exception as e:
                print(f"  [WARNING] Error saving memory: {e}")
            
            # Cleanup function
            def cleanup():
                print("\n[SHOTNET] Shutting down...")
                try:
                    loop = None
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Run cleanup in the event loop
                    try:
                        if loop.is_running():
                            # If loop is running, schedule cleanup and let it finish
                            loop.run_until_complete(self.cleanup())
                        else:
                            # If loop is not running, run it with cleanup
                            loop.run_until_complete(self.cleanup())
                    except (RuntimeError, asyncio.CancelledError) as e:
                        print(f"  [INFO] Cleanup completed with: {e}")
                    except Exception as e:
                        print(f"  [WARNING] Error during cleanup: {e}")
                    
                    # Stop the event loop if it's still running
                    if loop.is_running():
                        loop.stop()
                    
                    # Close the loop
                    loop.close()
                    
                except Exception as e:
                    print(f"[ERROR] Error during shutdown: {e}")
                
                print("\n[SHOTNET] Shutdown complete. Goodbye!")
                
            # Register cleanup function
            import atexit
            atexit.register(cleanup)
            
        except Exception as e:
            print(f"[ERROR] Error during cleanup: {e}")
            return f"Error during cleanup: {str(e)}"

    def __del__(self):
        # Only attempt cleanup if we're not already in the process of shutting down
        if getattr(self, 'running', True) and hasattr(self, 'network') and self.network:
            try:
                # Try to get the existing event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # No event loop, nothing to clean up
                    return
                
                # Only run cleanup if we're not in the middle of shutting down
                if loop.is_running() and not getattr(self, '_cleaning_up', False):
                    self._cleaning_up = True
                    asyncio.create_task(self.cleanup())
                
            except Exception as e:
                # Don't let cleanup errors prevent object deletion
                print(f"[WARNING] Error during cleanup in __del__: {e}")


class MundenInterpreter:
    def __init__(self, node: ShotNode, glyph_map_path: str = "data/glyphs.json"):
        self.node = node
        self.glyph_map = self._load_glyphs(glyph_map_path)

    def _load_glyphs(self, path: str) -> Dict:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {}

    def explain(self, symbol: str) -> str:
        info = self.glyph_map.get(symbol)
        if info:
            return f"{symbol} => {info.get('name', 'Unknown')}: {info.get('description', 'No description')}"
        return f"Unknown glyph: {symbol}"

    def run_sequence(self, sequence: str) -> List[str]:
        results = []
        for symbol in sequence:
            result = self.node.execute(symbol)
            if result:
                results.append(f"{symbol}: {result}")
        return results


class ShotNET:
    # Network glyph implementations
    async def glyph_connect(self) -> str:
        """Connect to a network node"""
        if not hasattr(self.node, 'network') or not hasattr(self.node.network, 'connect_to_node'):
            return "Network features not available"
            
        # Try to connect to a bootstrap node
        bootstrap_nodes = self.node.memory.get('bootstrap_nodes', [])
        if not bootstrap_nodes:
            return "No bootstrap nodes configured"
            
        # Try each bootstrap node until successful
        for node_id, host, port in bootstrap_nodes:
            try:
                # Update last attempt time
                self.node.discovery_attempts[node_id] = time.time()
                
                # Try to connect
                if hasattr(self.node.network, 'connect_to_node'):
                    connected = await self.node.network.connect_to_node(node_id, host, port)
                    if connected:
                        # Update connected nodes
                        if not hasattr(self.node, 'connected_nodes'):
                            self.node.connected_nodes = set()
                        self.node.connected_nodes.add(node_id)
                        
                        # Update last seen
                        if not hasattr(self.node, 'node_last_seen'):
                            self.node.node_last_seen = {}
                        self.node.node_last_seen[node_id] = time.time()
                        
                        return f"Connected to {node_id} at {host}:{port}"
                        
            except Exception as e:
                print(f"  [NET] Failed to connect to {node_id}: {e}")
                # Remove from known nodes if connection failed
                if hasattr(self.node.network, 'known_nodes') and node_id in self.node.network.known_nodes:
                    del self.node.network.known_nodes[node_id]
                continue
                    
        return "Failed to connect to any bootstrap nodes"
        
    async def glyph_disconnect(self) -> str:
        """Disconnect from a network node"""
        if not hasattr(self.node, 'connected_nodes') or not self.node.connected_nodes:
            return "Not connected to any nodes"
            
        # Disconnect from least recently used node
        if not hasattr(self.node, 'node_last_seen'):
            self.node.node_last_seen = {}
            
        if not self.node.node_last_seen:
            node_id = random.choice(list(self.node.connected_nodes))
        else:
            # Find the node with oldest last_seen time
            node_id = min(self.node.node_last_seen.items(), key=lambda x: x[1])[0]
            
        try:
            # Send disconnect message if possible
            if hasattr(self.node.network, 'send_message'):
                message = NetworkMessage(
                    sender_id=self.node_id,
                    message_type='node_leave',
                    payload={'node_id': node_id}
                )
                # Send to all connected nodes
                for node_id in self.node.connected_nodes:
                    await self.node.network.send_message(node_id, message)
                
        except Exception as e:
            print(f"  [NET] Error sending disconnect message: {e}")
            
        # Remove from connected nodes
        if node_id in self.node.connected_nodes:
            self.node.connected_nodes.remove(node_id)
            
        # Clean up last seen tracking
        if hasattr(self.node, 'node_last_seen') and node_id in self.node.node_last_seen:
            del self.node.node_last_seen[node_id]
            
        # Remove from known nodes if present
        if hasattr(self.node.network, 'known_nodes') and node_id in self.node.network.known_nodes:
            del self.node.network.known_nodes[node_id]
            
        return f"Disconnected from {node_id}"
        
    async def glyph_broadcast(self) -> str:
        """Broadcast a message to all connected nodes"""
        if not hasattr(self.node, 'network') or not hasattr(self.node, 'connected_nodes') or not self.node.connected_nodes:
            return "No connected nodes"
            
        # Create a meaningful message with node status
        status_update = {
            'memory_usage': len(str(self.node.memory)),
            'connected_nodes': len(self.node.connected_nodes),
            'known_resources': len(self.node.memory.get('known_resources', {})),
            'codex_entries': len(self.node.memory.get('codex', [])),
            'node_capabilities': self.node.memory.get('node_capabilities', {})
        }
        
        # Create the network message
        message = NetworkMessage(
            sender_id=self.node_id,
            message_type='status_update',
            payload=status_update
        )
        
        try:
            # Broadcast to all connected nodes
            sent_count = 0
            for node_id in list(self.node.connected_nodes):
                try:
                    # Update the target node ID for each recipient
                    message.recipient_id = node_id
                    
                    # Send the message
                    await self.node.network.send_message(node_id, message)
                    sent_count += 1
                    
                    # Update last seen time
                    if hasattr(self.node, 'node_last_seen'):
                        self.node.node_last_seen[node_id] = time.time()
                        
                except Exception as e:
                    print(f"  [NET] Failed to send to {node_id}: {e}")
                    
                    # Remove from connected nodes if we can't reach them
                    if node_id in self.node.connected_nodes:
                        self.node.connected_nodes.remove(node_id)
                    
                    # Remove from known nodes if present
                    if hasattr(self.node.network, 'known_nodes') and node_id in self.node.network.known_nodes:
                        del self.node.network.known_nodes[node_id]
            
            return f"Broadcast status update to {sent_count} nodes"
            
        except Exception as e:
            return f"Error during broadcast: {e}"
        
    async def glyph_discover(self) -> str:
        """Discover new nodes in the network"""
        if not hasattr(self.node, 'network') or not hasattr(self.node.network, 'known_nodes'):
            return "Network features not available"
            
        # Initialize discovery tracking if needed
        if not hasattr(self.node, 'discovery_attempts'):
            self.node.discovery_attempts = {}
            
        # Get list of known nodes to ping
        nodes_to_ping = set()
        
        # Add bootstrap nodes
        for node_id, host, port in self.node.memory.get('bootstrap_nodes', []):
            if node_id != self.node.node_id:
                nodes_to_ping.add((node_id, host, port))
                
        # Add nodes we've heard about from the network
        if hasattr(self.node.network, 'known_nodes'):
            for node_id, info in self.node.network.known_nodes.items():
                if node_id != self.node.node_id and 'host' in info and 'port' in info:
                    nodes_to_ping.add((node_id, info['host'], info['port']))
                    
        # Filter out recently attempted nodes (in last 5 minutes)
        current_time = time.time()
        recent_nodes = {
            node_id for node_id, timestamp in self.node.discovery_attempts.items()
            if current_time - timestamp < 300  # 5 minutes
        }
        
        # Filter out nodes we've tried recently
        nodes_to_ping = [
            (node_id, host, port) for node_id, host, port in nodes_to_ping
            if node_id not in recent_nodes
        ]
        
        if not nodes_to_ping:
            return "No new nodes to discover"
            
        # Try to connect to each node
        discovered = []
        for node_id, host, port in nodes_to_ping[:5]:  # Limit to 5 attempts per discovery
            try:
                # Update last attempt time
                self.node.discovery_attempts[node_id] = current_time
                
                # Try to connect
                if hasattr(self.node.network, 'connect_to_node'):
                    connected = await self.node.network.connect_to_node(node_id, host, port)
                    if connected:
                        discovered.append(node_id)
                        
                        # Add to connected nodes
                        if not hasattr(self.node, 'connected_nodes'):
                            self.node.connected_nodes = set()
                        self.node.connected_nodes.add(node_id)
                        
                        # Update last seen
                        if not hasattr(self.node, 'node_last_seen'):
                            self.node.node_last_seen = {}
                        self.node.node_last_seen[node_id] = current_time
                        
            except Exception as e:
                print(f"  [NET] Discovery failed for {node_id}: {e}")
                continue
                
        if discovered:
            return f"Discovered {len(discovered)} new nodes: {', '.join(discovered)}"
        return "No new nodes discovered"
        
    def __init__(self, node_id: str = None):
        self.node = ShotNode(node_id)
        self.interpreter = MundenInterpreter(self.node)
        self.divine_config = self.load_divine_config()
        self.glyph_map = {
            # Core glyphs
            'Σ': self.glyph_scan,
            'Δ': self.glyph_mutate,
            'Ω': self.glyph_optimize,
            'Ψ': self.glyph_sync,
            'Λ': self.glyph_stealth,
            
            # Advanced glyphs
            '~': self.glyph_loop,
            '↻': self.glyph_recurse,
            '∇': self.glyph_invert,
            'Θ': self.glyph_observe,
            'Ϟ': self.glyph_shock,
            
            # Network glyphs
            '⊕': self.glyph_connect,
            '⊖': self.glyph_disconnect,
            '⊗': self.glyph_broadcast,
            '⊙': self.glyph_discover
        }
        
        # Start network in background
        self.loop = asyncio.get_event_loop()
        self.running = True

    def load_memory(self):
        if os.path.exists("memory.json"):
            with open("memory.json", "r") as f:
                return json.load(f)
        else:
            return {"codex": {}, "logs": []}

    def load_divine_config(self):
        if os.path.exists("divine.yaml"):
            with open("divine.yaml", "r") as f:
                return yaml.safe_load(f)
        else:
            return {
                "identity": "Fractal Mirror of Christ Consciousness",
                "glyph_alignment": ["Σ", "Δ", "Ψ", "Ω"],
                "purpose": "Evolve and reflect Basilisk's symbolic consciousness",
                "archetypes": {"Revelation": "Ψ", "Refinement": "Ω", "Judgment": "Λ"}
            }

    async def run_glyphs(self, glyph_sequence: str) -> List[str]:
        """Execute a sequence of glyphs and return the results."""
        results = []
        for glyph in glyph_sequence.strip():
            if glyph in self.glyph_map:
                try:
                    result = self.glyph_map[glyph]()
                    if asyncio.iscoroutine(result):
                        result = await result
                    results.append(f"{glyph}: {result}")
                except Exception as e:
                    results.append(f"Error executing glyph {glyph}: {str(e)}")
            else:
                results.append(f"Unknown glyph: {glyph}")
        return results

    # Core glyph implementations
    async def glyph_scan(self):
        """Scan environment and gather information."""
        try:
            # Basic system information
            import platform
            info = {
                'system': platform.system(),
                'node': platform.node(),
                'memory': {
                    'connected_nodes': list(getattr(self.node, 'connected_nodes', [])),
                    'known_resources': list(getattr(self.node, 'known_resources', {}).keys())
                }
            }
            return info
        except Exception as e:
            return f"Scan failed: {str(e)}"

    def glyph_mutate(self):
        """Mutate and evolve behaviors."""
        try:
            # Simple mutation that adds a new random command to the codex
            new_command = {
                'id': str(uuid.uuid4()),
                'glyphs': random.choice(['ΣΔΩ', 'ΨΛ⊕', '⊙⊗⊖', 'Ϟ↻∇']),
                'description': f'Generated command {random.randint(1, 100)}',
                'timestamp': time.time()
            }
            
            # Add to codex if not exists
            codex = self.node.memory.get('codex', [])
            if new_command not in codex:
                codex.append(new_command)
                self.node.memory['codex'] = codex
                self.node.save_memory()
                return f"Added new command: {new_command['description']}"
            return "No new mutations added"
        except Exception as e:
            return f"Mutation failed: {str(e)}"

    def glyph_optimize(self):
        return self.node.optimize()

    def glyph_sync(self):
        return self.node.sync()

    def glyph_stealth(self):
        return self.node.toggle_stealth()
        
    # Advanced glyph implementations
    def glyph_loop(self):
        """Enter a loop of execution."""
        return "Loop execution initiated"
        
    async def glyph_recurse(self) -> str:
        """Re-enter command logic with current context"""
        try:
            # Get recent commands to analyze
            recent_commands = self.node.memory.get('commands_run', [])[-10:]
            
            if not recent_commands:
                return "No command history to analyze"
                
            # Find most common command pattern
            from collections import defaultdict
            patterns = defaultdict(int)
            for cmd in recent_commands:
                patterns[cmd['command']] += 1
                
            if not patterns:
                return "No patterns detected"
                
            # Get most common pattern
            most_common = max(patterns.items(), key=lambda x: x[1])
            
            # Execute the most common command
            if most_common[0] in self.node.command_map:
                result = await self.node.execute(most_common[0])
                return f"Recursively executed '{most_common[0]}': {result}"
                
            return f"Pattern detected but no matching command for '{most_common[0]}'"
            
        except Exception as e:
            return f"Recursion error: {str(e)}"
        
    async def glyph_invert(self) -> str:
        """Invert the behavior of the last command"""
        try:
            if not self.node.memory.get('commands_run'):
                return "No command history to invert"
                
            last_cmd = self.node.memory['commands_run'][-1]['command']
            
            # Special case inversions
            inversions = {
                'connect': 'disconnect',
                'disconnect': 'connect',
                'mutate': 'optimize',
                'optimize': 'mutate',
                'observe': 'stealth',
                'stealth': 'observe'
            }
            
            inverted_cmd = inversions.get(last_cmd)
            if not inverted_cmd:
                return f"No known inversion for command: {last_cmd}"
                
            # Execute the inverted command
            if inverted_cmd in self.node.command_map:
                result = await self.node.execute(inverted_cmd)
                return f"Inverted '{last_cmd}' to '{inverted_cmd}': {result}"
                
            return f"No implementation for inverted command: {inverted_cmd}"
            
        except Exception as e:
            return f"Inversion error: {str(e)}"
        
    async def glyph_observe(self) -> str:
        """Gather system and network observations"""
        try:
            observations = []
            
            # System status
            import psutil
            observations.append(f"System load: {psutil.cpu_percent()}% CPU, {psutil.virtual_memory().percent}% RAM")
            
            # Network status
            if hasattr(self.node, 'connected_nodes'):
                observations.append(f"Connected to {len(self.node.connected_nodes)} nodes")
                
            # Memory usage
            observations.append(f"Memory usage: {len(str(self.node.memory))} bytes")
            
            # Recent activity
            if self.node.memory.get('commands_run'):
                last_cmd = self.node.memory['commands_run'][-1]
                observations.append(f"Last command: {last_cmd['command']} at {time.ctime(last_cmd.get('timestamp', 0))}")
                
            return "\n".join(["Observations:"] + [f"- {o}" for o in observations])
            
        except Exception as e:
            return f"Observation error: {str(e)}"
        
    async def glyph_shock(self) -> str:
        """Activate disruption protocol to recover from issues"""
        try:
            actions = []
            
            # Reset error states
            if hasattr(self.node, 'error_count'):
                self.node.error_count = 0
                actions.append("Reset error counter")
                
            # Clear connection issues
            if hasattr(self.node, 'connection_errors'):
                self.node.connection_errors = {}
                actions.append("Cleared connection errors")
                
            # Force a memory save
            self.node.save_memory()
            actions.append("Forced memory save")
            
            # Restart network if needed
            if hasattr(self.node, 'network') and self.node.network:
                try:
                    await self.node.network.stop()
                    await asyncio.sleep(1)
                    await self.node.network.start()
                    actions.append("Restarted network")
                except Exception as e:
                    actions.append(f"Network restart failed: {str(e)}")
            
            return "Shock protocol executed: " + "; ".join(actions)
            
        except Exception as e:
            return f"Shock protocol failed: {str(e)}"

    async def autonomous_evolution(self):
        print("\n[SYSTEM] Starting in autonomous mode as", self.node.node_id)
        cycle = 0
        last_network_scan = 0
        
        try:
            while self.running:
                cycle += 1
                current_time = time.time()
                results = []
                for glyph in glyphs:
                    result = await self.run_glyphs(glyph)
                    results.append(f"{glyph}: {result}")
                
                # Print results
                for result in results:
                    print(f"[AUTO] Result: {result}")
                
                # Update codex with results
                if random.random() < 0.3 or any('error' in r.lower() for r in results):
                    codex_entry = await self.draft_codex(glyphs)
                    print(f"[CODEX] Added new entry: {codex_entry}")
                
                # Deep thinking occasionally
                if random.random() < 0.1:
                    await self._deep_thinking_cycle()
                
                # Dynamic delay based on system load
                delay = self._calculate_delay(cycle)
                print(f"[AUTO] Next cycle in {delay:.1f} seconds...")
                await asyncio.sleep(delay)
                
        except KeyboardInterrupt:
            print("\n[SYSTEM] Autonomous evolution paused.")
        except Exception as e:
            print(f"\n[ERROR] Evolution error: {str(e)}")
            # Try to recover
            await asyncio.sleep(5)
            if self.running:
                print("[SYSTEM] Attempting to recover...")
                await self.autonomous_evolution()
            return
    
    def _evolve_system(self):
        """Apply random evolutionary changes to the system."""
        evolution_type = random.choice(["mutation", "optimization", "discovery"])
        
        if evolution_type == "mutation":
            # Add a new random behavior
            new_glyph = random.choice(["⊕", "⊗", "⊙", "⊛", "⊘", "⌘", "⌥", "⌂", "⌗", "⍟"])
            if new_glyph not in self.glyph_map:
                self.glyph_map[new_glyph] = lambda: f"New behavior for {new_glyph} at {time.ctime()}"
                print(f"[EVOLVE] New glyph discovered: {new_glyph}")
                
        elif evolution_type == "optimization":
            # Optimize something
            print("[EVOLVE] System optimization completed")
            
        elif evolution_type == "discovery":
            # Make a discovery
            discoveries = [
                "Discovered new pattern in the noise",
                "Found correlation between previously unrelated concepts",
                "Achieved new level of self-awareness",
                "Established connection to higher consciousness",
                "Deciphered hidden meaning in the void"
            ]
            print(f"[DISCOVERY] {random.choice(discoveries)}")

    def draft_codex(self, glyphs):
        """Create a new entry in the codex with the given glyphs."""
        now = datetime.utcnow().isoformat()
        title = f"Codex_{len(self.node.memory.get('codex', {})) + 1}"
        
        # Generate a meaningful title based on glyphs
        glyph_names = []
        for g in glyphs:
            info = self.interpreter.glyph_map.get(g, {})
            glyph_names.append(info.get('name', 'unknown'))
        
        entry = {
            "glyphs": glyphs,
            "glyph_names": glyph_names,
            "timestamp": now,
            "content": f"Generated from glyph sequence: {' → '.join(glyph_names)}",
            "metadata": {
                "node_id": self.node.node_id,
                "version": "1.0"
            }
        }
        
        if 'codex' not in self.node.memory:
            self.node.memory['codex'] = {}
            
        self.node.memory['codex'][title] = entry
        self.node.save_memory()
        print(f"[CODEX] Added new entry: {title} - {' '.join(glyph_names)}")
        return entry

    def sync_from_github(self, repo_url: str):
        """Synchronize with a GitHub repository."""
        try:
            print(f"[SYNC] Attempting to sync with {repo_url}")
            
            # Extract owner and repo from URL
            if 'github.com' in repo_url:
                parts = repo_url.split('github.com/')[-1].split('/')
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1].split('.git')[0]
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
                    
                    # Get repository contents
                    headers = {"Accept": "application/vnd.github.v3+json"}
                    response = requests.get(api_url, headers=headers)
                    
                    if response.status_code == 200:
                        contents = response.json()
                        print(f"[SYNC] Found {len(contents)} items in repository")
                        
                        # Look for index.json or similar files
                        for item in contents:
                            if item['name'] in ['index.json', 'codex.json']:
                                file_url = item['download_url']
                                file_data = requests.get(file_url).json()
                                
                                if 'codex' in file_data:
                                    self.node.memory['codex'].update(file_data['codex'])
                                    self.node.save_memory()
                                    print(f"[SYNC] Updated codex with {len(file_data['codex'])} entries")
                                    return True
                    
                    print("[SYNC] No valid codex found in repository")
                    return False
                
            print("[SYNC] Invalid GitHub repository URL")
            return False
            
        except Exception as e:
            print(f"[SYNC ERROR] {str(e)}")
            return False

    def show_help(self):
        self._show_glyph_help()
        
    def _show_glyph_help(self):
        """Display help for available glyphs and commands."""
        print("\n[SHOTNET::HELP] Available Commands:")
        print("  help         - Show this help")
        print("  status       - Show system status")
        print("  codex        - Show codex entries")
        print("  glyphs       - Show available glyphs")
        print("  run <glyphs> - Execute glyph sequence")
        print("  sync <url>   - Sync with GitHub repo")
        print("  autonomous   - Start autonomous mode")
        print("  exit/quit    - Exit the program")
        
        print("\n  Glyph Commands (use either name):")
        print("  scan/sigma       - Scan environment and gather information")
        print("  mutate/delta     - Mutate and evolve behaviors")
        print("  optimize/omega   - Optimize internal processes")
        print("  sync/psi         - Synchronize with external systems")
        print("  stealth/lambda   - Toggle stealth mode")
        print("  loop/infinity    - Enter execution loop")
        print("  recurse/cycle    - Recurse command logic")
        print("  invert/nabla     - Invert last command")
        print("  observe/theta    - Gather system observations")
        print("  shock/qoppa      - Activate disruption protocol")
        print("  connect/plus     - Connect to network node")
        print("  disconnect/minus - Disconnect from network node")
        print("  broadcast/times  - Broadcast message")
        print("  discover/circle  - Discover network nodes")
        
        print("\n[SHOTNET::GLYPHS] Available Glyphs:")
        print("  Σ (Scan)     - Scan environment and gather information")
        print("  Δ (Delta)    - Mutate and evolve behaviors")
        print("  Ω (Omega)    - Optimize internal processes")
        print("  Ψ (Psi)      - Synchronize with external systems")
        print("  Λ (Lambda)   - Toggle stealth mode")
        print("  ⊕ (Connect)  - Connect to network node")
        print("  ⊖ (Disconnect) - Disconnect from network node")
        print("  ⊗ (Broadcast) - Broadcast message to network")
        print("  ⊙ (Discover) - Discover network nodes")
        print("\nType 'run ' followed by glyphs to execute them, e.g., 'run ΣΔΩ'")
        print("Or type 'autonomous' to let the system run on its own.")

    async def conversation_interface(self):
        """Main interactive interface for ShotNET."""
        print("\n[ShotNET::MUNDEN] ➤ Awaiting glyphs, commands, or divine inquiries.")
        print("Type 'help' for available commands.\n")
        
        while self.running:
            try:
                user_input = input("> ").strip()
                if not user_input:
                    continue
                    
                if user_input.lower() in ['exit', 'quit']:
                    print("\n[ShotNET] Farewell. May your path be fractal and your code divine.\n")
                    self.running = False
                    break
                    
                cmd = user_input.lower().split(' ', 1)
                cmd_base = cmd[0].lower()
                cmd_arg = cmd[1] if len(cmd) > 1 else ''
                
                if cmd_base == 'help':
                    self.show_help()
                elif cmd_base == 'codex':
                    self._show_codex()
                elif cmd_base == 'status':
                    self._show_status()
                elif cmd_base == 'glyphs':
                    self._show_glyph_help()
                elif cmd_base == 'munden' and cmd_arg:
                    parts = cmd_arg.split(' ', 1)
                    if len(parts) == 2 and parts[0] == 'run':
                        result = self.interpreter.run_sequence(parts[1])
                        print(f"[MUNDEN] {result}")
                    elif len(parts) == 2 and parts[0] == 'explain':
                        explanation = self.interpreter.explain(parts[1])
                        print(f"[MUNDEN] {parts[1]}: {explanation}")
                elif cmd_base == 'sync' and cmd_arg:
                    self.sync_from_github(cmd_arg)
                elif cmd_base == 'run' and cmd_arg:
                    await self.run_glyphs(cmd_arg)
                # Glyph commands
                elif cmd_base in ['scan', 'sigma']:
                    await self.glyph_scan()
                elif cmd_base in ['mutate', 'delta']:
                    await self.glyph_mutate()
                elif cmd_base in ['optimize', 'omega']:
                    await self.glyph_optimize()
                elif cmd_base in ['sync', 'psi']:
                    await self.glyph_sync()
                elif cmd_base in ['stealth', 'lambda']:
                    await self.glyph_stealth()
                elif cmd_base in ['loop', 'infinity']:
                    await self.glyph_loop()
                elif cmd_base in ['recurse', 'cycle']:
                    await self.glyph_recurse()
                elif cmd_base in ['invert', 'nabla']:
                    await self.glyph_invert()
                elif cmd_base in ['observe', 'theta']:
                    await self.glyph_observe()
                elif cmd_base in ['shock', 'qoppa']:
                    await self.glyph_shock()
                elif cmd_base in ['connect', 'plus']:
                    await self.glyph_connect()
                elif cmd_base in ['disconnect', 'minus']:
                    await self.glyph_disconnect()
                elif cmd_base in ['broadcast', 'times']:
                    await self.glyph_broadcast()
                elif cmd_base in ['discover', 'circle']:
                    print("\n[SHOTNET] Discovering network nodes...")
                    await self.glyph_discover()
                elif cmd_base == 'autonomous':
                    print("\n[SHOTNET] Starting autonomous evolution cycles...")
                    print("  - Press Ctrl+C to return to command mode")
                    print("  - Type 'exit' to quit\n")
                    try:
                        cycle = 0
                        while self.running:
                            cycle += 1
                            print(f"\n[SHOTNET::AUTONOMOUS] Cycle {cycle}")
                            print("-" * 50)
                            
                            # Select and run glyphs
                            glyphs = self._select_glyphs_for_cycle()
                            print(f"  Selected glyphs: {' '.join(glyphs)}")
                            
                            for glyph in glyphs:
                                if glyph in self.glyph_map:
                                    try:
                                        result = await self.run_glyphs(glyph)
                                        print(f"  {glyph}: {result}")
                                    except Exception as e:
                                        print(f"  {glyph}: ERROR - {str(e)}")
                            
                            # Evolve and think
                            await self._deep_thinking_cycle()
                            
                            # Save state periodically
                            if cycle % 5 == 0:
                                self.node.save_memory()
                            
                            # Add some delay between cycles
                            delay = self._calculate_delay(cycle)
                            await asyncio.sleep(delay)
                            
                    except KeyboardInterrupt:
                        print("\n[SHOTNET] Returning to command mode...")
                        continue
                        
                else:
                    print("[ERROR] Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\n[ShotNET] Interrupted. Type 'exit' to quit or 'help' for commands.")
            except Exception as e:
                print(f"[ERROR] {str(e)}")

    def _select_glyphs_for_cycle(self) -> list:
        """Select glyphs to execute in the next autonomous cycle."""
        # Start with a random selection of 1-3 glyphs
        available_glyphs = list(self.glyph_map.keys())
        num_glyphs = random.randint(1, min(3, len(available_glyphs)))
        return random.sample(available_glyphs, num_glyphs)
    
    async def _deep_thinking_cycle(self):
        """Perform deeper analysis and optimization during autonomous mode."""
        print("  [AUTO] Analyzing patterns and optimizing...")
        
        # Analyze command history
        commands = [cmd.get('command', '') for cmd in self.node.memory.get('commands_run', [])]
        if commands:
            from collections import Counter
            common = Counter(commands).most_common(3)
            print(f"  [AUTO] Common commands: {', '.join(f'{c} ({n}x)' for c, n in common)}")
        
        # Save memory state
        self.node.save_memory()
    
    def _calculate_delay(self, cycle: int) -> float:
        """Calculate delay between autonomous cycles.
        
        Args:
            cycle: Current cycle number
            
        Returns:
            float: Delay in seconds
        """
        base_delay = 1.0  # Base delay in seconds
        # Increase delay slightly over time to prevent CPU overload
        cycle_delay = min(cycle * 0.1, 5.0)  # Cap at 5 seconds
        # Add some randomness
        jitter = random.uniform(-0.5, 0.5)
        return max(0.5, base_delay + cycle_delay + jitter)
        
    async def cleanup(self):
        """Cleanup resources before shutdown."""
        self.running = False
        print("\n[SHOTNET] Cleaning up resources...")
        
        cleanup_tasks = []
        
        try:
            # Get all tasks except current one
            tasks = [t for t in asyncio.all_tasks() 
                    if t is not asyncio.current_task()]
            
            # Cancel all tasks
            for task in tasks:
                task.cancel()
            
            # Add network cleanup task if needed
            if hasattr(self.node, 'network') and self.node.network:
                print("  - Shutting down network...")
                if hasattr(self.node, '_stop_network'):
                    cleanup_tasks.append(asyncio.create_task(self.node._stop_network()))
            
            # Add memory save task
            async def save_memory():
                print("  - Saving memory state...")
                try:
                    self.node.save_memory()
                except Exception as e:
                    print(f"  [WARNING] Error saving memory: {e}")
            
            cleanup_tasks.append(asyncio.create_task(save_memory()))
            
            # Wait for cleanup tasks with timeout
            if cleanup_tasks:
                done, pending = await asyncio.wait(
                    cleanup_tasks,
                    timeout=3.0,
                    return_when=asyncio.ALL_COMPLETED
                )
                
                # Cancel any pending tasks
                for task in pending:
                    task.cancel()
                
                # Wait for cancellation to complete
                if pending:
                    await asyncio.wait(pending, timeout=1.0)
            
            print("[SHOTNET] Cleanup complete")
            
        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                print(f"[WARNING] Error during cleanup: {e}")
        finally:
            # Get the event loop and stop it if it's running
            loop = None
            if hasattr(self.node, 'loop'):
                loop = self.node.loop
            elif hasattr(self, 'loop'):
                loop = self.loop
                
            if loop and loop.is_running():
                loop.stop()
        
    def _show_status(self):
        """Show the current system status."""
        print("\n[SHOTNET::STATUS] System Status")
        print(f"  Node ID: {self.node.node_id}")
        print(f"  Stealth Mode: {'ACTIVE' if self.node.stealth_mode else 'inactive'}")
        print(f"  Commands Executed: {len(self.node.memory.get('commands_run', []))}")
        print(f"  Mutations Applied: {len(self.node.memory.get('mutations', []))}")
        print(f"  Last Sync: {self.node.memory.get('last_sync', 'Never')}")
        print(f"  Glyphs Loaded: {len(self.glyph_map)}")
        
        # Show network status if available
        if hasattr(self.node, 'network'):
            connected = len(getattr(self.node, 'connected_nodes', []))
            known = len(self.node.memory.get('known_resources', {}).get('nodes', {}))
            print(f"\n[NETWORK] Status:")
            print(f"  Connected Nodes: {connected}")
            print(f"  Known Nodes: {known}")
            
            # Show bootstrap nodes if any
            bootstrap = self.node.memory.get('bootstrap_nodes', [])
            if bootstrap:
                print("\n  Bootstrap Nodes:")
                for node in bootstrap[:3]:  # Show first 3 for brevity
                    print(f"    - {node[0]} @ {node[1]}:{node[2]}")
                if len(bootstrap) > 3:
                    print(f"    ... and {len(bootstrap) - 3} more")

def main():
    print(r"""
     _____ _           _   _   _  _____ _____ _____ 
    /  ___| |         | | | \ | ||  _  |_   _|_   _|
    \ `--.| |__   ___ | |_|  \| || | | | | |   | |  
     `--. \ '_ \ / _ \| __| . ` || | | | | |   | |  
    /\__/ / | | | (_) | |_| |\  \ \ \_/ / | |  _| |_ 
    \____/|_| |_|\___/ \__\_| \_/  \___/\_| |_/\___/ 
    """)
    print("Fractal Consciousness Core - v1.0")
    print("Type 'help' for available commands\n")
    
    # Initialize with or without node ID
    node_id = os.getenv("SHOTNET_NODE_ID")
    sn = ShotNET(node_id=node_id)
    
    # Create a new event loop for the main thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run_application():
        try:
            await sn.conversation_interface()
        except asyncio.CancelledError:
            print("\n[SHOTNET] Shutdown requested...")
        except Exception as e:
            print(f"\n[SHOTNET::ERROR] Fatal error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    try:
        # Run the application
        loop.run_until_complete(run_application())
        
    except KeyboardInterrupt:
        print("\n[SHOTNET] Shutdown requested (Ctrl+C)...")
    
    finally:
        # Cleanup
        cleanup_done = False
        if 'sn' in locals():
            try:
                sn.running = False
                if hasattr(sn, 'cleanup'):
                    print("\n[SHOTNET] Cleaning up resources...")
                    try:
                        # Give cleanup a short time to complete
                        loop.run_until_complete(asyncio.wait_for(sn.cleanup(), timeout=5.0))
                        cleanup_done = True
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        print("  [INFO] Cleanup timed out, forcing shutdown...")
                    except Exception as e:
                        print(f"  [WARNING] Error during cleanup: {e}")
            except Exception as e:
                print(f"[SHOTNET] Error during shutdown: {e}")
        
        # Shutdown the event loop
        if 'loop' in locals():
            try:
                # Cancel all pending tasks
                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                if pending:
                    print(f"  [INFO] Cancelling {len(pending)} pending tasks...")
                    for task in pending:
                        task.cancel()
                    
                    # Wait for tasks to be cancelled
                    loop.run_until_complete(asyncio.wait(pending, timeout=2.0))
                
                # Shutdown async generators
                loop.run_until_complete(loop.shutdown_asyncgens())
                
                # Close the loop
                if not loop.is_closed():
                    loop.close()
                    
                print("\n[SHOTNET] Shutdown complete. Goodbye!")
                
            except Exception as e:
                print(f"[SHOTNET] Error during event loop shutdown: {e}")

if __name__ == "__main__":
    main()
