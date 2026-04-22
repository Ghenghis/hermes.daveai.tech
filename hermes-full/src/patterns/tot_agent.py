# src/patterns/tot_agent.py
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum
import logging
import json
import uuid

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PRUNED = "pruned"
    FAILED = "failed"


@dataclass
class ThoughtNode:
    id: str
    content: str
    parent_id: Optional[str]
    children_ids: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.ACTIVE
    score: float = 0.0
    depth: int = 0
    reasoning: str = ""
    
    def is_leaf(self) -> bool:
        return len(self.children_ids) == 0


@dataclass
class TreeOfThoughtsAgent:
    name: str
    description: str = ""
    max_depth: int = 5
    max_breadth: int = 3
    num_workers: int = 3
    prune_threshold: float = 0.3
    llm_provider: Optional[Any] = field(default=None, repr=False)
    
    _nodes: Dict[str, ThoughtNode] = field(default_factory=dict, init=False)
    _root_id: Optional[str] = field(default=None, init=False)
    _active_nodes: Set[str] = field(default_factory=set, init=False)
    
    def _create_node(self, content: str, parent_id: Optional[str], depth: int) -> ThoughtNode:
        node = ThoughtNode(
            id=str(uuid.uuid4()),
            content=content,
            parent_id=parent_id,
            depth=depth
        )
        self._nodes[node.id] = node
        if parent_id:
            self._nodes[parent_id].children_ids.append(node.id)
        return node
    
    async def generate_thoughts(self, context: str, num_thoughts: int = 3) -> List[str]:
        prompt = f"""Generate {num_thoughts} different approaches for solving this problem:
{context}

Provide a JSON array of approach descriptions."""
        
        if self.llm_provider:
            response = await self.llm_provider.complete(prompt)
        else:
            response = json.dumps([f"Approach {i}: Systematic analysis" for i in range(num_thoughts)])
        
        return self._parse_thoughts(response)
    
    def _parse_thoughts(self, response: str) -> List[str]:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            lines = response.strip().split("\n")
            return [line for line in lines if line.strip()]
    
    async def evaluate_node(self, node: ThoughtNode) -> float:
        prompt = f"""Score this approach from 0.0 to 1.0:
{node.content}
Return only the numeric score."""
        
        if self.llm_provider:
            score_str = await self.llm_provider.complete(prompt)
        else:
            score_str = "0.5"
        
        try:
            return float(score_str.strip())
        except ValueError:
            return 0.5
    
    async def expand_node(self, node_id: str) -> List[ThoughtNode]:
        node = self._nodes[node_id]
        if node.depth >= self.max_depth:
            return []
        
        thoughts = await self.generate_thoughts(node.content, self.max_breadth)
        children = []
        
        for thought in thoughts:
            child = self._create_node(content=thought, parent_id=node_id, depth=node.depth + 1)
            child.score = await self.evaluate_node(child)
            children.append(child)
        
        node.status = NodeStatus.COMPLETED
        return children
    
    async def should_prune(self, node: ThoughtNode) -> bool:
        if node.parent_id is None:
            return False
        
        parent = self._nodes[node.parent_id]
        siblings = [self._nodes[cid] for cid in parent.children_ids]
        avg_sibling_score = sum(s.score for s in siblings) / len(siblings) if siblings else 0
        
        return node.score < avg_sibling_score * (1 - self.prune_threshold)
    
    def get_best_leaf(self) -> Optional[ThoughtNode]:
        leaves = [n for n in self._nodes.values() if n.is_leaf()]
        if not leaves:
            return None
        return max(leaves, key=lambda n: n.score)
    
    def get_best_path(self) -> List[ThoughtNode]:
        best_leaf = self.get_best_leaf()
        if not best_leaf:
            return []
        
        path = []
        current = best_leaf
        while current:
            path.insert(0, current)
            current = self._nodes[current.parent_id] if current.parent_id else None
        
        return path
    
    async def run(self, problem: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._nodes = {}
        self._active_nodes = set()
        
        root = self._create_node(problem, None, 0)
        self._root_id = root.id
        root.score = await self.evaluate_node(root)
        self._active_nodes.add(root.id)
        
        logger.info(f"Starting ToT with root node: {root.id}")
        
        while self._active_nodes:
            current_batch = list(self._active_nodes)[:self.num_workers]
            tasks = [self.expand_node(node_id) for node_id in current_batch]
            results = await asyncio.gather(*tasks)
            
            new_nodes = []
            for node_id, children in zip(current_batch, results):
                self._active_nodes.discard(node_id)
                new_nodes.extend(children)
            
            for node in new_nodes:
                self._active_nodes.add(node.id)
                if await self.should_prune(node):
                    node.status = NodeStatus.PRUNED
                    self._active_nodes.discard(node.id)
                    logger.info(f"Pruned node: {node.id} (score: {node.score})")
            
            await asyncio.sleep(0.1)
        
        best_path = self.get_best_path()
        best_leaf = self.get_best_leaf()
        
        return {
            "problem": problem,
            "best_solution": best_leaf.content if best_leaf else None,
            "best_score": best_leaf.score if best_leaf else 0,
            "total_nodes": len(self._nodes),
            "best_path": [n.content for n in best_path],
            "nodes_explored": len([n for n in self._nodes.values() if n.status == NodeStatus.COMPLETED])
        }


async def example_usage():
    agent = TreeOfThoughtsAgent(name="ProblemSolver", max_depth=4, max_breadth=2, num_workers=2)
    result = await agent.run("Find the most efficient sorting algorithm for nearly sorted data")
    print(f"Best solution: {result['best_solution']}")
    print(f"Best score: {result['best_score']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
