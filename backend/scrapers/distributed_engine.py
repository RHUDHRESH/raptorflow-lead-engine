"""
Distributed Request System for geographic distribution and IP rotation.
Manages request distribution across different networks and timing patterns.
"""
import logging
import time
import random
import asyncio
import hashlib
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse
import aiohttp
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class GeographicRegion(Enum):
    """Geographic regions for request distribution"""
    NORTH_AMERICA = "north_america"
    SOUTH_AMERICA = "south_america"
    EUROPE = "europe"
    ASIA = "asia"
    AFRICA = "africa"
    OCEANIA = "oceania"
    GLOBAL = "global"

class NetworkType(Enum):
    """Network types for IP distribution"""
    RESIDENTIAL = "residential"
    DATACENTER = "datacenter"
    MOBILE = "mobile"
    CORPORATE = "corporate"

@dataclass
class RequestNode:
    """A node capable of making requests"""
    node_id: str
    region: GeographicRegion
    network_type: NetworkType
    ip_address: str
    success_rate: float
    last_used: float
    active_requests: int
    max_concurrent: int
    capabilities: Set[str]  # e.g., 'headless', 'api', 'mobile'

@dataclass
class RequestDistribution:
    """Distribution strategy for a request"""
    primary_nodes: List[RequestNode]
    backup_nodes: List[RequestNode]
    timing_strategy: str
    max_attempts: int
    timeout_per_attempt: int

class DistributedRequestEngine:
    """
    Engine for distributing requests across geographic regions and networks
    """
    
    def __init__(self, max_concurrent_requests: int = 10):
        self.max_concurrent = max_concurrent_requests
        self.nodes: Dict[str, RequestNode] = {}
        self.region_nodes: Dict[GeographicRegion, List[RequestNode]] = {}
        self.network_nodes: Dict[NetworkType, List[RequestNode]] = {}
        
        # Request queues and scheduling
        self.request_queue = asyncio.Queue()
        self.active_requests: Dict[str, asyncio.Task] = {}
        self.request_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Geographic and network preferences
        self.geographic_weights = {
            GeographicRegion.NORTH_AMERICA: 0.4,
            GeographicRegion.EUROPE: 0.3,
            GeographicRegion.ASIA: 0.2,
            GeographicRegion.SOUTH_AMERICA: 0.05,
            GeographicRegion.AFRICA: 0.03,
            GeographicRegion.OCEANIA: 0.02
        }
        
        self.network_weights = {
            NetworkType.RESIDENTIAL: 0.5,
            NetworkType.DATACENTER: 0.3,
            NetworkType.MOBILE: 0.15,
            NetworkType.CORPORATE: 0.05
        }
        
        # Initialize with some default nodes
        self._initialize_default_nodes()
        
        # Start request processor
        self.running = True
        self.processor_task = None
    
    def _initialize_default_nodes(self):
        """Initialize default request nodes"""
        default_nodes = [
            # North America - Residential
            RequestNode("na_res_1", GeographicRegion.NORTH_AMERICA, NetworkType.RESIDENTIAL, "192.168.1.1", 0.95, 0, 0, 5, {"headless", "api"}),
            RequestNode("na_res_2", GeographicRegion.NORTH_AMERICA, NetworkType.RESIDENTIAL, "192.168.1.2", 0.93, 0, 0, 5, {"headless", "api"}),
            
            # North America - Datacenter
            RequestNode("na_dc_1", GeographicRegion.NORTH_AMERICA, NetworkType.DATACENTER, "10.0.1.1", 0.98, 0, 0, 10, {"headless", "api", "fast"}),
            
            # Europe - Residential
            RequestNode("eu_res_1", GeographicRegion.EUROPE, NetworkType.RESIDENTIAL, "192.168.2.1", 0.94, 0, 0, 5, {"headless", "api"}),
            
            # Europe - Datacenter
            RequestNode("eu_dc_1", GeographicRegion.EUROPE, NetworkType.DATACENTER, "10.0.2.1", 0.97, 0, 0, 10, {"headless", "api", "fast"}),
            
            # Asia - Residential
            RequestNode("asia_res_1", GeographicRegion.ASIA, NetworkType.RESIDENTIAL, "192.168.3.1", 0.92, 0, 0, 5, {"headless", "api"}),
            
            # Mobile nodes
            RequestNode("mobile_1", GeographicRegion.NORTH_AMERICA, NetworkType.MOBILE, "192.168.4.1", 0.90, 0, 0, 3, {"headless", "mobile", "api"}),
            RequestNode("mobile_2", GeographicRegion.EUROPE, NetworkType.MOBILE, "192.168.4.2", 0.88, 0, 0, 3, {"headless", "mobile", "api"}),
        ]
        
        for node in default_nodes:
            self.add_node(node)
    
    def add_node(self, node: RequestNode):
        """Add a request node to the system"""
        self.nodes[node.node_id] = node
        
        # Add to region index
        if node.region not in self.region_nodes:
            self.region_nodes[node.region] = []
        self.region_nodes[node.region].append(node)
        
        # Add to network index
        if node.network_type not in self.network_nodes:
            self.network_nodes[node.network_type] = []
        self.network_nodes[node.network_type].append(node)
        
        logger.info(f"Added request node: {node.node_id} ({node.region.value}/{node.network_type.value})")
    
    def remove_node(self, node_id: str):
        """Remove a request node"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            
            # Remove from indexes
            if node.region in self.region_nodes:
                self.region_nodes[node.region] = [n for n in self.region_nodes[node.region] if n.node_id != node_id]
            
            if node.network_type in self.network_nodes:
                self.network_nodes[node.network_type] = [n for n in self.network_nodes[node.network_type] if n.node_id != node_id]
            
            del self.nodes[node_id]
            logger.info(f"Removed request node: {node_id}")
    
    def plan_request_distribution(self, url: str, requirements: Dict[str, Any] = None) -> RequestDistribution:
        """
        Plan how to distribute a request across available nodes
        
        Args:
            url: Target URL
            requirements: Specific requirements (region, network_type, etc.)
            
        Returns:
            RequestDistribution strategy
        """
        requirements = requirements or {}
        domain = self._extract_domain(url)
        
        # Determine target preferences
        target_region = self._determine_target_region(domain, requirements)
        target_network = self._determine_target_network(domain, requirements)
        
        # Select primary nodes
        primary_nodes = self._select_nodes(
            region=target_region,
            network_type=target_network,
            min_success_rate=requirements.get('min_success_rate', 0.8),
            required_capabilities=requirements.get('capabilities', set()),
            count=requirements.get('primary_count', 3)
        )
        
        # Select backup nodes (different regions/networks for resilience)
        backup_nodes = self._select_backup_nodes(
            primary_nodes,
            target_region,
            target_network,
            requirements.get('backup_count', 2)
        )
        
        # Determine timing strategy
        timing_strategy = self._determine_timing_strategy(domain, requirements)
        
        # Calculate attempt limits
        max_attempts = min(len(primary_nodes) + len(backup_nodes), requirements.get('max_attempts', 5))
        
        distribution = RequestDistribution(
            primary_nodes=primary_nodes,
            backup_nodes=backup_nodes,
            timing_strategy=timing_strategy,
            max_attempts=max_attempts,
            timeout_per_attempt=requirements.get('timeout', 30)
        )
        
        logger.info(f"Planned distribution for {url}: {len(primary_nodes)} primary, {len(backup_nodes)} backup nodes")
        return distribution
    
    def _determine_target_region(self, domain: str, requirements: Dict[str, Any]) -> GeographicRegion:
        """Determine the best target region for a domain"""
        if 'region' in requirements:
            return requirements['region']
        
        # Domain-specific region preferences
        domain_regions = {
            'linkedin.com': GeographicRegion.NORTH_AMERICA,
            'indeed.com': GeographicRegion.NORTH_AMERICA,
            'naukri.com': GeographicRegion.ASIA,
            'xing.com': GeographicRegion.EUROPE,
            'monster.com': GeographicRegion.GLOBAL,
            'glassdoor.com': GeographicRegion.GLOBAL
        }
        
        if domain in domain_regions:
            return domain_regions[domain]
        
        # Default to weighted random selection
        regions = list(self.geographic_weights.keys())
        weights = list(self.geographic_weights.values())
        return random.choices(regions, weights=weights)[0]
    
    def _determine_target_network(self, domain: str, requirements: Dict[str, Any]) -> NetworkType:
        """Determine the best network type for a domain"""
        if 'network_type' in requirements:
            return requirements['network_type']
        
        # Domain-specific network preferences
        domain_networks = {
            'linkedin.com': NetworkType.RESIDENTIAL,  # LinkedIn blocks datacenter IPs
            'facebook.com': NetworkType.RESIDENTIAL,
            'twitter.com': NetworkType.RESIDENTIAL,
            'indeed.com': NetworkType.DATACENTER,  # Indeed allows datacenter
            'naukri.com': NetworkType.DATACENTER
        }
        
        if domain in domain_networks:
            return domain_networks[domain]
        
        # Default to residential for better success rate
        return NetworkType.RESIDENTIAL
    
    def _select_nodes(self, region: GeographicRegion, network_type: NetworkType,
                     min_success_rate: float = 0.8, required_capabilities: Set[str] = None,
                     count: int = 3) -> List[RequestNode]:
        """Select suitable nodes based on criteria"""
        required_capabilities = required_capabilities or set()
        
        candidates = []
        
        # Get nodes by region and network
        region_nodes = self.region_nodes.get(region, [])
        network_nodes = self.network_nodes.get(network_type, [])
        
        # Find intersection
        for node in region_nodes:
            if (node in network_nodes and
                node.success_rate >= min_success_rate and
                node.active_requests < node.max_concurrent and
                required_capabilities.issubset(node.capabilities)):
                candidates.append(node)
        
        if not candidates:
            # Fallback: any available nodes with required capabilities
            candidates = [
                node for node in self.nodes.values()
                if (node.success_rate >= min_success_rate and
                    node.active_requests < node.max_concurrent and
                    required_capabilities.issubset(node.capabilities))
            ]
        
        # Sort by success rate and load
        candidates.sort(key=lambda x: (-x.success_rate, x.active_requests))
        
        return candidates[:count]
    
    def _select_backup_nodes(self, primary_nodes: List[RequestNode],
                           target_region: GeographicRegion, target_network: NetworkType,
                           count: int = 2) -> List[RequestNode]:
        """Select backup nodes with different characteristics for resilience"""
        backup_candidates = []
        
        # Avoid same nodes as primary
        primary_ids = {node.node_id for node in primary_nodes}
        
        # Prefer different regions/networks for backup
        alternative_regions = [r for r in GeographicRegion if r != target_region]
        alternative_networks = [n for n in NetworkType if n != target_network]
        
        for region in alternative_regions[:2]:  # Try 2 alternative regions
            region_nodes = self.region_nodes.get(region, [])
            for node in region_nodes:
                if (node.node_id not in primary_ids and
                    node.active_requests < node.max_concurrent):
                    backup_candidates.append(node)
                    if len(backup_candidates) >= count:
                        return backup_candidates
        
        for network in alternative_networks[:2]:  # Try 2 alternative networks
            network_nodes = self.network_nodes.get(network, [])
            for node in network_nodes:
                if (node.node_id not in primary_ids and
                    node.active_requests < node.max_concurrent):
                    backup_candidates.append(node)
                    if len(backup_candidates) >= count:
                        return backup_candidates
        
        return backup_candidates[:count]
    
    def _determine_timing_strategy(self, domain: str, requirements: Dict[str, Any]) -> str:
        """Determine timing strategy for requests"""
        if 'timing_strategy' in requirements:
            return requirements['timing_strategy']
        
        # Domain-specific timing
        if domain in ['linkedin.com', 'facebook.com', 'twitter.com']:
            return 'aggressive_delay'  # Longer delays for strict sites
        elif domain in ['indeed.com', 'naukri.com']:
            return 'moderate_delay'  # Moderate delays for job sites
        else:
            return 'normal_delay'
    
    async def execute_distributed_request(self, url: str, distribution: RequestDistribution,
                                        request_func: callable, *args, **kwargs) -> Optional[Any]:
        """
        Execute a request using distributed strategy
        
        Args:
            url: Target URL
            distribution: Request distribution plan
            request_func: Function to execute the request
            *args, **kwargs: Arguments for request function
            
        Returns:
            Request result or None if all attempts failed
        """
        all_nodes = distribution.primary_nodes + distribution.backup_nodes
        attempt = 0
        
        for node in all_nodes:
            if attempt >= distribution.max_attempts:
                break
            
            attempt += 1
            logger.info(f"Attempting request {attempt}/{distribution.max_attempts} on node {node.node_id}")
            
            try:
                # Mark node as active
                node.active_requests += 1
                
                # Apply timing strategy
                await self._apply_timing_strategy(distribution.timing_strategy, attempt)
                
                # Execute request with node context
                result = await self._execute_on_node(node, request_func, url, *args, **kwargs)
                
                if result:
                    # Record success
                    self._record_request_result(url, node, True, attempt)
                    node.active_requests -= 1
                    return result
                
            except Exception as e:
                logger.warning(f"Request failed on node {node.node_id}: {e}")
                self._record_request_result(url, node, False, attempt, str(e))
            
            finally:
                node.active_requests -= 1
        
        logger.error(f"All distributed request attempts failed for {url}")
        return None
    
    async def _execute_on_node(self, node: RequestNode, request_func: callable, url: str, *args, **kwargs) -> Optional[Any]:
        """Execute request function on a specific node"""
        # Add node-specific configuration
        node_config = {
            'proxy': f"http://{node.ip_address}:8080",  # Simulated proxy
            'headers': {
                'X-Request-Node': node.node_id,
                'X-Request-Region': node.region.value,
                'X-Request-Network': node.network_type.value
            }
        }
        
        # Merge with existing kwargs
        kwargs = {**kwargs, **node_config}
        
        # Execute with timeout
        timeout = kwargs.get('timeout', 30)
        try:
            result = await asyncio.wait_for(
                request_func(url, *args, **kwargs),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            raise Exception(f"Request timed out after {timeout}s")
    
    async def _apply_timing_strategy(self, strategy: str, attempt: int):
        """Apply timing strategy between requests"""
        base_delays = {
            'aggressive_delay': [5, 10, 15, 20],  # Longer delays
            'moderate_delay': [2, 4, 6, 8],
            'normal_delay': [1, 2, 3, 4],
            'fast_delay': [0.5, 1, 1.5, 2]
        }
        
        delays = base_delays.get(strategy, base_delays['normal_delay'])
        delay_index = min(attempt - 1, len(delays) - 1)
        delay = delays[delay_index]
        
        # Add jitter
        jitter = random.uniform(-0.5, 0.5) * delay * 0.2
        actual_delay = max(0.1, delay + jitter)
        
        await asyncio.sleep(actual_delay)
    
    def _record_request_result(self, url: str, node: RequestNode, success: bool, attempt: int, error: str = None):
        """Record the result of a request attempt"""
        domain = self._extract_domain(url)
        
        if domain not in self.request_history:
            self.request_history[domain] = []
        
        record = {
            'timestamp': time.time(),
            'node_id': node.node_id,
            'region': node.region.value,
            'network': node.network_type.value,
            'success': success,
            'attempt': attempt,
            'error': error
        }
        
        self.request_history[domain].append(record)
        
        # Update node success rate
        if success:
            # Increase success rate
            node.success_rate = min(1.0, node.success_rate + 0.02)
        else:
            # Decrease success rate
            node.success_rate = max(0.0, node.success_rate - 0.05)
        
        # Keep only recent history (last 1000 records per domain)
        if len(self.request_history[domain]) > 1000:
            self.request_history[domain] = self.request_history[domain][-1000:]
    
    def get_request_stats(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """Get request statistics"""
        if domain:
            history = self.request_history.get(domain, [])
        else:
            # Aggregate all domains
            history = []
            for domain_history in self.request_history.values():
                history.extend(domain_history)
        
        if not history:
            return {'total_requests': 0, 'success_rate': 0.0}
        
        total_requests = len(history)
        successful_requests = len([r for r in history if r['success']])
        success_rate = successful_requests / total_requests if total_requests > 0 else 0.0
        
        # Recent performance (last 100 requests)
        recent = history[-100:] if len(history) >= 100 else history
        recent_successful = len([r for r in recent if r['success']])
        recent_success_rate = recent_successful / len(recent) if recent else 0.0
        
        return {
            'total_requests': total_requests,
            'success_rate': success_rate,
            'recent_success_rate': recent_success_rate,
            'successful_requests': successful_requests,
            'failed_requests': total_requests - successful_requests
        }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    async def start_request_processor(self):
        """Start the distributed request processor"""
        self.running = True
        self.processor_task = asyncio.create_task(self._process_request_queue())
        logger.info("Started distributed request processor")
    
    async def stop_request_processor(self):
        """Stop the distributed request processor"""
        self.running = False
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped distributed request processor")
    
    async def _process_request_queue(self):
        """Process queued requests"""
        while self.running:
            try:
                # Get next request from queue
                request_data = await asyncio.wait_for(self.request_queue.get(), timeout=1.0)
                
                # Process request
                task = asyncio.create_task(self._execute_queued_request(request_data))
                self.active_requests[request_data['request_id']] = task
                
                # Clean up completed tasks
                completed_tasks = [rid for rid, task in self.active_requests.items() if task.done()]
                for rid in completed_tasks:
                    del self.active_requests[rid]
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing request queue: {e}")
    
    async def _execute_queued_request(self, request_data: Dict[str, Any]):
        """Execute a queued request"""
        try:
            url = request_data['url']
            distribution = request_data['distribution']
            request_func = request_data['request_func']
            args = request_data.get('args', [])
            kwargs = request_data.get('kwargs', {})
            
            result = await self.execute_distributed_request(
                url, distribution, request_func, *args, **kwargs
            )
            
            # Handle result (could store in database, send to callback, etc.)
            if result:
                logger.info(f"Distributed request successful for {url}")
            else:
                logger.warning(f"Distributed request failed for {url}")
                
        except Exception as e:
            logger.error(f"Error executing queued request: {e}")

# Global instance
distributed_engine = DistributedRequestEngine()
