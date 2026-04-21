"""
Integration Layer - Wires all contract kit components together.

This module provides the main entry point that starts all services
in the correct order and wires RuntimeCoreAPI, EventBus, HermesOrchestrator,
and other components together into a working system.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from runtime.core import RuntimeCoreAPI, EventBus, ProviderRouter
from hermes.orchestrator import HermesOrchestrator, ZeroClawAdapter
from zeroclaw.adapters import ZeroClawGateway

logger = logging.getLogger(__name__)


class ContractKitIntegration:
    """
    Main integration class that wires all components together.
    
    This class initializes and starts all services in the correct order:
    1. EventBus (for messaging)
    2. ProviderRouter (for provider selection)
    3. RuntimeCoreAPI (for settings and health)
    4. ZeroClawGateway (for adapter management)
    5. HermesOrchestrator (for task orchestration)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the contract kit integration.
        
        Args:
            config: Configuration dictionary containing:
                - nats_url: NATS server URL (default: nats://localhost:4222)
                - runtime_port: Runtime API port (default: 8080)
                - providers: List of provider names (default: ["siliconflow", "minimax", "openrouter"])
                - working_directory: Working directory for adapters
        """
        self.config = config or {}
        self.nats_url = self.config.get("nats_url", "nats://localhost:4222")
        self.runtime_port = self.config.get("runtime_port", 8080)
        self.providers = self.config.get("providers", ["siliconflow", "minimax", "openrouter"])
        self.working_directory = self.config.get("working_directory")
        
        # Component instances
        self.event_bus: Optional[EventBus] = None
        self.provider_router: Optional[ProviderRouter] = None
        self.runtime_api: Optional[RuntimeCoreAPI] = None
        self.zeroclaw_gateway: Optional[ZeroClawGateway] = None
        self.hermes_orchestrator: Optional[HermesOrchestrator] = None
        self.zeroclaw_adapter: Optional[ZeroClawAdapter] = None
        
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize all components in the correct order."""
        logger.info("Initializing Contract Kit Integration...")
        
        # Step 1: Initialize EventBus
        logger.info("Step 1: Initializing EventBus...")
        self.event_bus = EventBus(nats_url=self.nats_url)
        await self.event_bus.connect()
        logger.info(f"EventBus connected to {self.nats_url}")
        
        # Step 2: Initialize ProviderRouter
        logger.info("Step 2: Initializing ProviderRouter...")
        self.provider_router = ProviderRouter(
            providers=self.providers,
            event_bus=self.event_bus
        )
        logger.info(f"ProviderRouter initialized with providers: {self.providers}")
        
        # Step 3: Initialize RuntimeCoreAPI
        logger.info("Step 3: Initializing RuntimeCoreAPI...")
        self.runtime_api = RuntimeCoreAPI(
            title="Contract Kit Runtime",
            version="1.0.0"
        )
        self.runtime_api.event_bus = self.event_bus
        logger.info(f"RuntimeCoreAPI initialized on port {self.runtime_port}")
        
        # Step 4: Initialize ZeroClawGateway
        logger.info("Step 4: Initializing ZeroClawGateway...")
        gateway_config = {}
        if self.working_directory:
            gateway_config["working_directory"] = self.working_directory
        self.zeroclaw_gateway = ZeroClawGateway(config=gateway_config)
        logger.info("ZeroClawGateway initialized with default adapters")
        
        # Step 5: Initialize HermesOrchestrator
        logger.info("Step 5: Initializing HermesOrchestrator...")
        self.hermes_orchestrator = HermesOrchestrator(
            runtime_api=self.runtime_api,
            event_bus=self.event_bus,
            provider_router=self.provider_router
        )
        logger.info("HermesOrchestrator initialized")
        
        # Step 6: Initialize ZeroClawAdapter for Hermes
        logger.info("Step 6: Initializing ZeroClawAdapter...")
        self.zeroclaw_adapter = ZeroClawAdapter(config=gateway_config)
        self.hermes_orchestrator.zeroclaw_adapter = self.zeroclaw_adapter
        logger.info("ZeroClawAdapter initialized and wired to HermesOrchestrator")
        
        logger.info("Contract Kit Integration initialized successfully")
    
    async def start(self) -> None:
        """Start all services."""
        if not self.event_bus:
            await self.initialize()
        
        logger.info("Starting Contract Kit services...")
        self._running = True
        
        # Start RuntimeCoreAPI (runs in background)
        logger.info(f"Starting RuntimeCoreAPI on port {self.runtime_port}...")
        import uvicorn
        asyncio.create_task(
            uvicorn.run(
                self.runtime_api.app,
                host="0.0.0.0",
                port=self.runtime_port,
                log_level="info"
            )
        )
        
        # Wait a moment for API to start
        await asyncio.sleep(2)
        
        logger.info("Contract Kit services started successfully")
        logger.info(f"Runtime API available at http://0.0.0.0:{self.runtime_port}")
    
    async def stop(self) -> None:
        """Stop all services."""
        logger.info("Stopping Contract Kit services...")
        self._running = False
        
        # Disconnect EventBus
        if self.event_bus:
            await self.event_bus.disconnect()
            logger.info("EventBus disconnected")
        
        logger.info("Contract Kit services stopped")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components.
        
        Returns:
            Health status of all components.
        """
        health = {
            "integration_running": self._running,
            "components": {}
        }
        
        # EventBus health
        health["components"]["event_bus"] = {
            "connected": self.event_bus.connected if self.event_bus else False,
            "url": self.nats_url
        }
        
        # RuntimeCoreAPI health
        if self.runtime_api:
            try:
                runtime_health = await self.runtime_api.health_check()
                health["components"]["runtime_api"] = runtime_health
            except Exception as e:
                health["components"]["runtime_api"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # ProviderRouter health
        if self.provider_router:
            health["components"]["provider_router"] = {
                "providers": self.providers,
                "status": "healthy"
            }
        
        # ZeroClawGateway health
        if self.zeroclaw_gateway:
            health["components"]["zeroclaw_gateway"] = {
                "adapters_registered": list(self.zeroclaw_gateway._adapters.keys()),
                "status": "healthy"
            }
        
        # HermesOrchestrator health
        if self.hermes_orchestrator:
            health["components"]["hermes_orchestrator"] = {
                "contracts_count": len(self.hermes_orchestrator.contracts),
                "tasks_count": len(self.hermes_orchestrator.tasks),
                "status": "healthy"
            }
        
        return health
    
    async def process_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task through the full pipeline.
        
        Args:
            task_input: Task input dictionary with description, acceptance_criteria, etc.
            
        Returns:
            Task processing result.
        """
        if not self.hermes_orchestrator:
            raise RuntimeError("HermesOrchestrator not initialized")
        
        logger.info(f"Processing task: {task_input.get('description', 'unknown')}")
        
        # Step 1: Intake
        intake_result = await self.hermes_orchestrator.intake(task_input)
        
        if intake_result.get("status") == "error":
            return intake_result
        
        # Step 2: Create contract
        contract_id = intake_result.get("contract_id")
        if contract_id:
            contract_result = await self.hermes_orchestrator.create_contract(
                contract_id=contract_id,
                task_packet=intake_result.get("task_packet")
            )
            
            if contract_result.get("status") == "error":
                return contract_result
            
            # Step 3: Fanout tasks
            fanout_result = await self.hermes_orchestrator.fanout_tasks(
                contract_id=contract_id
            )
            
            return {
                "status": "success",
                "contract_id": contract_id,
                "intake": intake_result,
                "contract": contract_result,
                "fanout": fanout_result
            }
        
        return intake_result


async def main(config: Optional[Dict[str, Any]] = None) -> None:
    """
    Main entry point for the contract kit integration.
    
    Args:
        config: Configuration dictionary.
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    integration = ContractKitIntegration(config=config)
    
    try:
        await integration.initialize()
        await integration.start()
        
        # Keep running
        logger.info("Contract Kit Integration running. Press Ctrl+C to stop.")
        while integration._running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await integration.stop()


if __name__ == "__main__":
    import sys
    
    config = {}
    if len(sys.argv) > 1:
        import json
        config = json.loads(sys.argv[1])
    
    asyncio.run(main(config))
