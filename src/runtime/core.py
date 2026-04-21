"""
Runtime Core - FastAPI-based runtime API and event infrastructure.

This module provides the core runtime API for contract kit,
including settings management, event bus, provider routing
with circuit breakers, and interactive settings flows.
"""

import asyncio
import json
import time
import uuid
from typing import Optional, Dict, Any, Callable, List, Tuple
from enum import Enum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class SettingsModel(BaseModel):
    """Model for settings data."""
    key: str
    value: Any
    description: Optional[str] = None


class RuntimeCoreAPI:
    """
    FastAPI-based core runtime API.
    
    Provides REST endpoints for settings management, event subscriptions,
    health monitoring, and runtime operations.
    """
    
    def __init__(self, title: str = "Contract Kit Runtime", version: str = "1.0.0"):
        """
        Initialize the Runtime Core API.
        
        Args:
            title: API title.
            version: API version string.
        """
        self.app = FastAPI(title=title, version=version)
        self.settings: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self.event_bus: Optional[EventBus] = None
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Set up API routes for settings, events, and health."""
        @self.app.get("/settings")
        async def get_settings_endpoint(key: Optional[str] = None) -> Dict[str, Any]:
            return await self.get_settings(key)
        
        @self.app.put("/settings/{key}")
        async def update_setting_endpoint(key: str, value: Any) -> Dict[str, Any]:
            return await self.update_setting(key, value)
        
        @self.app.get("/events")
        async def get_events_endpoint(
            event_type: Optional[str] = None,
            limit: int = 100
        ) -> List[Dict[str, Any]]:
            return await self.get_events(event_type, limit)
        
        @self.app.post("/events")
        async def publish_event_endpoint(
            event_type: str,
            payload: Dict[str, Any]
        ) -> Dict[str, Any]:
            return await self.publish_event(event_type, payload)
        
        @self.app.get("/health")
        async def health_check_endpoint() -> Dict[str, Any]:
            return await self.health_check()
    
    async def get_settings(self, key: Optional[str] = None) -> Dict[str, Any]:
        """
        GET /settings - Retrieve runtime settings.
        
        Args:
            key: Optional specific setting key to retrieve.
            
        Returns:
            Dictionary of settings, or specific setting if key provided.
        """
        if key is not None:
            if key in self.settings:
                return {"key": key, "value": self.settings[key]}
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        return self.settings
    
    async def update_setting(self, key: str, value: Any) -> Dict[str, Any]:
        """
        PUT /settings/{key} - Update a specific setting.
        
        Args:
            key: The setting key to update.
            value: The new value for the setting.
            
        Returns:
            Updated setting information.
        """
        old_value = self.settings.get(key)
        self.settings[key] = value
        
        await self.publish_event(
            event_type="setting.updated",
            payload={"key": key, "old_value": old_value, "new_value": value}
        )
        
        return {"key": key, "value": value, "updated": True}
    
    async def get_events(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        GET /events - Retrieve recent events.
        
        Args:
            event_type: Optional filter by event type.
            limit: Maximum number of events to return.
            
        Returns:
            List of event dictionaries.
        """
        events = self.events[-limit:] if self.events else []
        
        if event_type is not None:
            events = [e for e in events if e.get("type") == event_type]
        
        return events
    
    async def publish_event(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        POST /events - Publish a new event.
        
        Args:
            event_type: Type of the event.
            payload: Event payload data.
            
        Returns:
            Published event information.
        """
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "payload": payload,
            "timestamp": time.time()
        }
        
        self.events.append(event)
        
        if len(self.events) > 10000:
            self.events = self.events[-5000:]
        
        if self.event_bus:
            try:
                await self.event_bus.publish(f"events.{event_type}", event)
            except Exception:
                pass
        
        return event
    
    async def health_check(self) -> Dict[str, Any]:
        """
        GET /health - Perform health check.
        
        Returns:
            Health status information including component statuses.
        """
        components = {}
        
        components["settings"] = {
            "status": HealthStatus.HEALTHY.value,
            "settings_count": len(self.settings)
        }
        
        components["events"] = {
            "status": HealthStatus.HEALTHY.value,
            "events_count": len(self.events)
        }
        
        if self.event_bus:
            components["event_bus"] = {
                "status": HealthStatus.HEALTHY.value if self.event_bus.connected else HealthStatus.DEGRADED.value,
                "connected": self.event_bus.connected
            }
        else:
            components["event_bus"] = {
                "status": HealthStatus.UNKNOWN.value,
                "connected": False
            }
        
        overall_status = HealthStatus.HEALTHY.value
        for comp in components.values():
            if comp.get("status") == HealthStatus.UNHEALTHY.value:
                overall_status = HealthStatus.UNHEALTHY.value
                break
            elif comp.get("status") == HealthStatus.DEGRADED.value:
                overall_status = HealthStatus.DEGRADED.value
        
        return {
            "status": overall_status,
            "components": components
        }


class EventBus:
    """
    NATS-based event bus for runtime messaging.
    
    Provides publish/subscribe functionality for inter-component
    communication using NATS as the message broker.
    """
    
    def __init__(self, nats_url: Optional[str] = None):
        """
        Initialize the EventBus.
        
        Args:
            nats_url: NATS server URL. Defaults to 'nats://localhost:4222'.
        """
        self.nats_url = nats_url or "nats://localhost:4222"
        self.subscribers: Dict[str, List[Callable]] = {}
        self.subscription_callbacks: Dict[str, Tuple[str, Callable]] = {}
        self.connected = False
        self._nats_client = None
        self._subscription_id_counter = 0
    
    async def connect(self) -> None:
        """Establish connection to NATS server."""
        try:
            import nats
            
            self._nats_client = await nats.connect(self.nats_url)
            self.connected = True
        except ImportError:
            self._nats_client = None
            self.connected = False
        except Exception:
            self._nats_client = None
            self.connected = False
    
    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self._nats_client:
            try:
                await self._nats_client.close()
            except Exception:
                pass
            finally:
                self._nats_client = None
        self.connected = False
        self.subscribers.clear()
        self.subscription_callbacks.clear()
    
    async def publish(self, subject: str, payload: Dict[str, Any]) -> None:
        """
        Publish an event to a subject.
        
        Args:
            subject: The NATS subject to publish to.
            payload: Event payload dictionary.
        """
        if self._nats_client and self.connected:
            try:
                data = json.dumps(payload).encode()
                await self._nats_client.publish(subject, data)
            except Exception:
                pass
        
        if subject in self.subscribers:
            for callback in self.subscribers[subject]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(payload)
                    else:
                        callback(payload)
                except Exception:
                    pass
    
    async def subscribe(
        self,
        subject: str,
        callback: Callable[[Dict[str, Any]], None]
    ) -> str:
        """
        Subscribe to a subject.
        
        Args:
            subject: The NATS subject to subscribe to.
            callback: Callback function to handle messages.
            
        Returns:
            Subscription ID.
        """
        self._subscription_id_counter += 1
        subscription_id = f"sub_{self._subscription_id_counter}"
        
        if subject not in self.subscribers:
            self.subscribers[subject] = []
            if self._nats_client and self.connected:
                try:
                    async def nats_callback(msg):
                        try:
                            data = json.loads(msg.data.decode())
                            for cb in self.subscribers.get(subject, []):
                                try:
                                    if asyncio.iscoroutinefunction(cb):
                                        await cb(data)
                                    else:
                                        cb(data)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    
                    await self._nats_client.subscribe(subject, cb=nats_callback)
                except Exception:
                    pass
        
        self.subscribers[subject].append(callback)
        self.subscription_callbacks[subscription_id] = (subject, callback)
        
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from a subject.
        
        Args:
            subscription_id: The subscription ID to cancel.
        """
        if subscription_id in self.subscription_callbacks:
            subject, callback = self.subscription_callbacks.pop(subscription_id)
            
            if subject in self.subscribers:
                try:
                    self.subscribers[subject].remove(callback)
                except ValueError:
                    pass


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker for provider fault tolerance.
    
    Monitors provider health and opens the circuit when
    failure thresholds are exceeded.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit.
            recovery_timeout: Seconds before attempting recovery.
            half_open_max_calls: Max calls in half-open state.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0
        self.last_failure_time: Optional[float] = None
    
    def record_success(self) -> None:
        """Record a successful call."""
        self.failure_count = 0
        self.half_open_calls = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self.last_failure_time is None:
                return True
            
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False


class ProviderRouter:
    """
    Provider routing with circuit breaker support.
    
    Routes requests to providers with automatic failover
    and circuit breaker protection.
    """
    
    def __init__(self, providers: List[str], event_bus: Optional[EventBus] = None):
        """
        Initialize ProviderRouter.
        
        Args:
            providers: List of provider names.
            event_bus: Optional EventBus for health events.
        """
        self.providers = providers
        self.event_bus = event_bus
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            provider: CircuitBreaker() for provider in providers
        }
        self.current_provider_index = 0
        self.provider_stats: Dict[str, Dict[str, Any]] = {
            provider: {"successes": 0, "failures": 0, "last_success": None, "last_failure": None}
            for provider in providers
        }
    
    async def route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a request to an available provider.
        
        Args:
            payload: Request payload to route.
            
        Returns:
            Response from the provider.
        """
        available_providers = []
        
        for provider in self.providers:
            cb = self.circuit_breakers.get(provider, CircuitBreaker())
            if cb.can_execute():
                available_providers.append(provider)
        
        if not available_providers:
            return {
                "error": "No available providers",
                "all_circuits_open": True
            }
        
        selected_provider = available_providers[self.current_provider_index % len(available_providers)]
        self.current_provider_index += 1
        
        return {
            "provider": selected_provider,
            "payload": payload,
            "routed": True
        }
    
    async def get_provider_health(self, provider: str) -> Dict[str, Any]:
        """
        Get health status of a specific provider.
        
        Args:
            provider: Provider name.
            
        Returns:
            Health information for the provider.
        """
        if provider not in self.providers:
            return {
                "provider": provider,
                "status": HealthStatus.UNKNOWN.value,
                "error": "Provider not found"
            }
        
        cb = self.circuit_breakers.get(provider, CircuitBreaker())
        stats = self.provider_stats.get(provider, {})
        
        return {
            "provider": provider,
            "circuit_state": cb.state.value,
            "failure_count": cb.failure_count,
            "last_failure_time": cb.last_failure_time,
            "stats": stats
        }
    
    async def record_success(self, provider: str) -> None:
        """Record successful call for a provider."""
        if provider in self.circuit_breakers:
            self.circuit_breakers[provider].record_success()
        
        if provider in self.provider_stats:
            self.provider_stats[provider]["successes"] += 1
            self.provider_stats[provider]["last_success"] = time.time()
    
    async def record_failure(self, provider: str) -> None:
        """Record failed call for a provider."""
        if provider in self.circuit_breakers:
            self.circuit_breakers[provider].record_failure()
        
        if provider in self.provider_stats:
            self.provider_stats[provider]["failures"] += 1
            self.provider_stats[provider]["last_failure"] = time.time()
    
    def get_circuit_state(self, provider: str) -> CircuitState:
        """
        Get circuit breaker state for a provider.
        
        Args:
            provider: Provider name.
            
        Returns:
            Current circuit state.
        """
        if provider not in self.circuit_breakers:
            return CircuitState.CLOSED
        
        return self.circuit_breakers[provider].state


class SettingsQuestionFlow:
    """
    Interactive settings question flow.
    
    Guides users through settings configuration by asking
    questions and applying answers to the runtime settings.
    """
    
    def __init__(self, settings_api: RuntimeCoreAPI):
        """
        Initialize SettingsQuestionFlow.
        
        Args:
            settings_api: RuntimeCoreAPI instance for settings operations.
        """
        self.settings_api = settings_api
        self.questions: List[Dict[str, Any]] = []
        self.answers: Dict[str, Any] = {}
    
    def add_question(
        self,
        key: str,
        question: str,
        default: Any = None,
        choices: Optional[List[Any]] = None
    ) -> str:
        """
        Add a question to the flow.
        
        Args:
            key: Settings key this question configures.
            question: The question text.
            default: Default value if no answer provided.
            choices: Optional list of valid choices.
            
        Returns:
            Question ID.
        """
        question_id = str(uuid.uuid4())
        
        self.questions.append({
            "id": question_id,
            "key": key,
            "question": question,
            "default": default,
            "choices": choices
        })
        
        return question_id
    
    async def run(
        self,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the question flow.
        
        Args:
            initial_context: Initial context for autofilling answers.
            
        Returns:
            Dictionary of answers collected from the flow.
        """
        collected_answers = {}
        context = initial_context or {}
        
        for q in self.questions:
            key = q["key"]
            question_text = q["question"]
            default = q.get("default")
            choices = q.get("choices")
            
            if key in context:
                collected_answers[key] = context[key]
                continue
            
            if default is not None:
                collected_answers[key] = default
                continue
            
            collected_answers[key] = None
        
        self.answers = collected_answers
        return collected_answers
    
    async def apply_answers(self) -> Dict[str, Any]:
        """Apply collected answers to runtime settings."""
        applied = {}
        
        for key, value in self.answers.items():
            if value is not None:
                try:
                    await self.settings_api.update_setting(key, value)
                    applied[key] = value
                except Exception as e:
                    applied[key] = {"error": str(e)}
        
        return {
            "applied": applied,
            "count": len(applied)
        }
