"""
Strategy Evolution Engine for Robo Trader

Implements strategy mutation, optimization, A/B testing framework,
and automated strategy discovery through evolutionary algorithms.
"""

import asyncio
import json
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from statistics import mean, stdev
from copy import deepcopy

from loguru import logger
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..core.learning_engine import LearningEngine


@dataclass
class StrategyGenome:
    """Genetic representation of a trading strategy."""
    strategy_id: str
    parameters: Dict[str, Any]  # Strategy parameters (entry/exit thresholds, position sizing, etc.)
    rules: List[Dict[str, Any]]  # Trading rules and conditions
    fitness_score: float = 0.0
    generation: int = 0
    parent_strategies: List[str] = None
    performance_metrics: Dict[str, float] = None
    created_at: str = ""

    def __post_init__(self):
        if self.parent_strategies is None:
            self.parent_strategies = []
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "StrategyGenome":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ABTest:
    """A/B testing configuration for strategy comparison."""
    test_id: str
    strategy_a: StrategyGenome
    strategy_b: StrategyGenome
    test_period_days: int
    start_date: str
    end_date: str
    status: str = "running"  # "running", "completed", "failed"
    results: Dict[str, Any] = None
    winner: Optional[str] = None  # "A", "B", or "tie"
    confidence_level: float = 0.0
    created_at: str = ""

    def __post_init__(self):
        if self.results is None:
            self.results = {}
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "ABTest":
        if 'strategy_a' in data:
            data['strategy_a'] = StrategyGenome.from_dict(data['strategy_a'])
        if 'strategy_b' in data:
            data['strategy_b'] = StrategyGenome.from_dict(data['strategy_b'])
        return cls(**data)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['strategy_a'] = self.strategy_a.to_dict()
        data['strategy_b'] = self.strategy_b.to_dict()
        return data


@dataclass
class EvolutionPopulation:
    """Population of strategies undergoing evolution."""
    population_id: str
    generation: int
    strategies: List[StrategyGenome]
    best_strategy: Optional[StrategyGenome] = None
    average_fitness: float = 0.0
    diversity_score: float = 0.0
    convergence_threshold: float = 0.95
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "EvolutionPopulation":
        if 'strategies' in data:
            data['strategies'] = [StrategyGenome.from_dict(s) for s in data['strategies']]
        if 'best_strategy' in data and data['best_strategy']:
            data['best_strategy'] = StrategyGenome.from_dict(data['best_strategy'])
        return cls(**data)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['strategies'] = [s.to_dict() for s in self.strategies]
        if self.best_strategy:
            data['best_strategy'] = self.best_strategy.to_dict()
        return data


class StrategyEvolutionEngine:
    """
    Evolutionary algorithm engine for strategy optimization and discovery.

    Key capabilities:
    - Genetic algorithm-based strategy evolution
    - A/B testing framework for strategy comparison
    - Automated strategy mutation and crossover
    - Performance-based strategy selection
    - Fitness function optimization
    """

    def __init__(self, config: Config, state_manager: DatabaseStateManager, learning_engine: LearningEngine):
        self.config = config
        self.state_manager = state_manager
        self.learning_engine = learning_engine
        self.client: Optional[ClaudeSDKClient] = None

        # Evolution parameters
        self.population_size = 20
        self.mutation_rate = 0.1
        self.crossover_rate = 0.8
        self.elitism_rate = 0.1  # Keep top 10% unchanged
        self.max_generations = 50
        self.convergence_threshold = 0.95

    async def initialize(self) -> None:
        """Initialize the strategy evolution engine."""
        logger.info("Initializing Strategy Evolution Engine")
        logger.info("Strategy Evolution Engine initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup evolution engine resources."""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up evolution client: {e}")

    async def evolve_strategy_population(
        self,
        base_strategy: Dict[str, Any],
        evolution_criteria: Dict[str, Any]
    ) -> Optional[EvolutionPopulation]:
        """
        Evolve a population of strategies using genetic algorithms.

        Args:
            base_strategy: Base strategy to evolve from
            evolution_criteria: Criteria for evolution (fitness function, constraints)

        Returns:
            Evolved population with optimized strategies
        """
        try:
            # Initialize population
            population = await self._initialize_population(base_strategy)

            # Evolutionary loop
            for generation in range(self.max_generations):
                logger.info(f"Evolution generation {generation + 1}/{self.max_generations}")

                # Evaluate fitness
                await self._evaluate_population_fitness(population, evolution_criteria)

                # Check convergence
                if await self._check_convergence(population):
                    logger.info(f"Population converged at generation {generation + 1}")
                    break

                # Create next generation
                population = await self._create_next_generation(population)

            # Final evaluation
            await self._evaluate_population_fitness(population, evolution_criteria)

            # Store evolved population
            await self._store_evolution_results(population)

            logger.info(f"Evolution completed. Best fitness: {population.best_strategy.fitness_score if population.best_strategy else 'N/A'}")
            return population

        except Exception as e:
            logger.error(f"Strategy evolution failed: {e}")
            return None

    async def run_ab_test(
        self,
        strategy_a: StrategyGenome,
        strategy_b: StrategyGenome,
        test_period_days: int = 30
    ) -> Optional[ABTest]:
        """
        Run A/B test between two strategies.

        Args:
            strategy_a: First strategy to test
            strategy_b: Second strategy to test
            test_period_days: Duration of test in days

        Returns:
            A/B test results
        """
        try:
            test_id = f"ab_test_{int(datetime.now(timezone.utc).timestamp())}"

            ab_test = ABTest(
                test_id=test_id,
                strategy_a=strategy_a,
                strategy_b=strategy_b,
                test_period_days=test_period_days,
                start_date=datetime.now(timezone.utc).date().isoformat(),
                end_date=(datetime.now(timezone.utc) + timedelta(days=test_period_days)).date().isoformat()
            )

            # Store test configuration
            await self.state_manager.save_ab_test(ab_test.to_dict())

            # Run the test (in practice, this would be scheduled)
            await self._execute_ab_test(ab_test)

            logger.info(f"A/B test {test_id} initiated between strategies")
            return ab_test

        except Exception as e:
            logger.error(f"A/B test setup failed: {e}")
            return None

    async def discover_new_strategies(self, market_conditions: Dict[str, Any]) -> List[StrategyGenome]:
        """
        Discover new trading strategies using AI and evolutionary principles.

        Args:
            market_conditions: Current market context for strategy discovery

        Returns:
            List of newly discovered strategies
        """
        try:
            if self.client is None:
                await self._ensure_client()

            # Use Claude to generate novel strategy ideas
            strategy_ideas = await self._generate_strategy_ideas(market_conditions)

            # Convert ideas to strategy genomes
            new_strategies = []
            for idea in strategy_ideas:
                genome = await self._idea_to_genome(idea)
                if genome:
                    new_strategies.append(genome)

            # Evaluate initial fitness
            for strategy in new_strategies:
                strategy.fitness_score = await self._calculate_fitness_score(strategy)

            # Store discovered strategies
            for strategy in new_strategies:
                await self._store_discovered_strategy(strategy)

            logger.info(f"Discovered {len(new_strategies)} new strategies")
            return new_strategies

        except Exception as e:
            logger.error(f"Strategy discovery failed: {e}")
            return []

    async def optimize_strategy_parameters(
        self,
        strategy: StrategyGenome,
        optimization_target: str = "sharpe_ratio"
    ) -> Optional[StrategyGenome]:
        """
        Optimize parameters of an existing strategy.

        Args:
            strategy: Strategy to optimize
            optimization_target: Metric to optimize for

        Returns:
            Optimized strategy
        """
        try:
            # Create parameter variations
            parameter_variations = await self._generate_parameter_variations(strategy)

            # Evaluate each variation
            best_strategy = strategy
            best_score = strategy.fitness_score

            for variation in parameter_variations:
                score = await self._calculate_fitness_score(variation)
                variation.fitness_score = score

                if score > best_score:
                    best_score = score
                    best_strategy = variation

            # Store optimization results
            await self._store_optimization_results(strategy, best_strategy)

            improvement = ((best_score - strategy.fitness_score) / strategy.fitness_score) * 100
            logger.info(f"Strategy optimization completed. Improvement: {improvement:.1f}%")

            return best_strategy

        except Exception as e:
            logger.error(f"Strategy parameter optimization failed: {e}")
            return None

    async def _initialize_population(self, base_strategy: Dict[str, Any]) -> EvolutionPopulation:
        """Initialize evolution population from base strategy."""
        population_id = f"pop_{int(datetime.now(timezone.utc).timestamp())}"

        # Create initial population with mutations of base strategy
        strategies = []
        base_genome = await self._strategy_dict_to_genome(base_strategy)

        # Add base strategy
        strategies.append(base_genome)

        # Generate mutated variations
        for i in range(self.population_size - 1):
            mutated = await self._mutate_strategy(base_genome)
            mutated.strategy_id = f"{population_id}_gen0_{i}"
            strategies.append(mutated)

        population = EvolutionPopulation(
            population_id=population_id,
            generation=0,
            strategies=strategies
        )

        return population

    async def _evaluate_population_fitness(
        self,
        population: EvolutionPopulation,
        criteria: Dict[str, Any]
    ) -> None:
        """Evaluate fitness of all strategies in population."""
        fitness_scores = []

        for strategy in population.strategies:
            score = await self._calculate_fitness_score(strategy)
            strategy.fitness_score = score
            fitness_scores.append(score)

        # Update population statistics
        population.average_fitness = mean(fitness_scores) if fitness_scores else 0.0
        population.best_strategy = max(population.strategies, key=lambda s: s.fitness_score)

        # Calculate diversity (simplified)
        if len(fitness_scores) > 1:
            population.diversity_score = stdev(fitness_scores) / mean(fitness_scores) if mean(fitness_scores) > 0 else 0.0

    async def _check_convergence(self, population: EvolutionPopulation) -> bool:
        """Check if population has converged."""
        if not population.strategies:
            return True

        # Check if best strategy dominates (fitness > average + 2*std)
        best_fitness = population.best_strategy.fitness_score
        convergence_score = best_fitness / population.average_fitness if population.average_fitness > 0 else 1.0

        return convergence_score >= self.convergence_threshold

    async def _create_next_generation(self, population: EvolutionPopulation) -> EvolutionPopulation:
        """Create next generation through selection, crossover, and mutation."""
        # Sort by fitness (descending)
        sorted_strategies = sorted(population.strategies, key=lambda s: s.fitness_score, reverse=True)

        # Elitism - keep top performers
        elite_count = int(self.population_size * self.elitism_rate)
        next_generation = sorted_strategies[:elite_count]

        # Generate offspring through crossover and mutation
        while len(next_generation) < self.population_size:
            # Tournament selection
            parent1 = await self._tournament_selection(sorted_strategies)
            parent2 = await self._tournament_selection(sorted_strategies)

            # Crossover
            if random.random() < self.crossover_rate:
                offspring1, offspring2 = await self._crossover_strategies(parent1, parent2)
            else:
                offspring1, offspring2 = parent1, parent2

            # Mutation
            offspring1 = await self._mutate_strategy(offspring1)
            offspring2 = await self._mutate_strategy(offspring2)

            # Update generation info
            offspring1.generation = population.generation + 1
            offspring2.generation = population.generation + 1
            offspring1.parent_strategies = [parent1.strategy_id, parent2.strategy_id]
            offspring2.parent_strategies = [parent1.strategy_id, parent2.strategy_id]

            next_generation.extend([offspring1, offspring2])

        # Trim to population size
        next_generation = next_generation[:self.population_size]

        return EvolutionPopulation(
            population_id=population.population_id,
            generation=population.generation + 1,
            strategies=next_generation
        )

    async def _calculate_fitness_score(self, strategy: StrategyGenome) -> float:
        """Calculate fitness score for a strategy."""
        # This would run backtesting or use historical performance
        # For now, use a simplified scoring based on parameters

        score = 0.0

        # Reward reasonable parameter ranges
        params = strategy.parameters

        # Example scoring logic (would be much more sophisticated)
        if 0.1 <= params.get("entry_threshold", 0) <= 0.5:
            score += 0.2
        if 0.05 <= params.get("stop_loss", 0) <= 0.2:
            score += 0.2
        if 0.1 <= params.get("take_profit", 0) <= 0.3:
            score += 0.2
        if params.get("max_positions", 5) <= 10:
            score += 0.2
        if params.get("risk_per_trade", 0.02) <= 0.05:
            score += 0.2

        # Add some randomness to simulate real performance variation
        score += random.uniform(-0.1, 0.1)
        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

        return score

    async def _mutate_strategy(self, strategy: StrategyGenome) -> StrategyGenome:
        """Apply random mutations to strategy parameters."""
        mutated = deepcopy(strategy)
        mutated.strategy_id = f"mut_{strategy.strategy_id}_{int(datetime.now(timezone.utc).timestamp())}"

        if random.random() < self.mutation_rate:
            # Mutate parameters
            params = mutated.parameters

            # Example mutations (would be strategy-specific)
            if "entry_threshold" in params:
                params["entry_threshold"] = max(0.05, min(0.8, params["entry_threshold"] * random.uniform(0.8, 1.2)))
            if "stop_loss" in params:
                params["stop_loss"] = max(0.02, min(0.3, params["stop_loss"] * random.uniform(0.9, 1.1)))
            if "take_profit" in params:
                params["take_profit"] = max(0.05, min(0.5, params["take_profit"] * random.uniform(0.9, 1.1)))

        return mutated

    async def _crossover_strategies(self, parent1: StrategyGenome, parent2: StrategyGenome) -> tuple:
        """Perform crossover between two parent strategies."""
        child1 = deepcopy(parent1)
        child2 = deepcopy(parent2)

        child1.strategy_id = f"crossover_{parent1.strategy_id}_{parent2.strategy_id}_1"
        child2.strategy_id = f"crossover_{parent1.strategy_id}_{parent2.strategy_id}_2"

        # Parameter crossover
        for key in set(child1.parameters.keys()) & set(child2.parameters.keys()):
            if random.random() < 0.5:
                # Swap this parameter
                child1.parameters[key], child2.parameters[key] = child2.parameters[key], child1.parameters[key]

        return child1, child2

    async def _tournament_selection(self, strategies: List[StrategyGenome], tournament_size: int = 3) -> StrategyGenome:
        """Tournament selection for parent selection."""
        # Randomly select tournament participants
        tournament = random.sample(strategies, min(tournament_size, len(strategies)))

        # Return the best from tournament
        return max(tournament, key=lambda s: s.fitness_score)

    async def _execute_ab_test(self, ab_test: ABTest) -> None:
        """Execute A/B test (simplified implementation)."""
        # In practice, this would schedule actual trading with both strategies
        # For now, simulate results
        await asyncio.sleep(0.1)  # Simulate processing

        # Simulate test results
        strategy_a_return = random.uniform(0.05, 0.15)
        strategy_b_return = random.uniform(0.05, 0.15)

        ab_test.results = {
            "strategy_a_return": strategy_a_return,
            "strategy_b_return": strategy_b_return,
            "test_duration_days": ab_test.test_period_days,
            "confidence_interval": 0.95
        }

        if strategy_a_return > strategy_b_return:
            ab_test.winner = "A"
            ab_test.confidence_level = min((strategy_a_return - strategy_b_return) / strategy_a_return, 0.95)
        elif strategy_b_return > strategy_a_return:
            ab_test.winner = "B"
            ab_test.confidence_level = min((strategy_b_return - strategy_a_return) / strategy_b_return, 0.95)
        else:
            ab_test.winner = "tie"
            ab_test.confidence_level = 0.5

        ab_test.status = "completed"

    async def _generate_strategy_ideas(self, market_conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate novel strategy ideas using Claude."""
        if not self.client:
            await self._ensure_client()

        query = f"""
        Generate 3-5 novel trading strategy ideas based on current market conditions.

        MARKET CONDITIONS:
        {json.dumps(market_conditions, indent=2)}

        Generate innovative strategy concepts that could work in the current environment.
        Each idea should include:
        1. Strategy name and concept
        2. Key parameters (entry/exit rules, position sizing, risk management)
        3. Why it might work in current conditions
        4. Potential risks and challenges

        Return as JSON array of strategy ideas.
        """

        try:
            await asyncio.wait_for(self.client.query(query), timeout=45.0)
        except asyncio.TimeoutError:
            logger.error("Strategy idea generation timed out")
            return []

        async for message in self.client.receive_response():
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        try:
                            return json.loads(block.text)
                        except json.JSONDecodeError:
                            continue

        return []

    async def _idea_to_genome(self, idea: Dict[str, Any]) -> Optional[StrategyGenome]:
        """Convert strategy idea to genome representation."""
        try:
            genome = StrategyGenome(
                strategy_id=f"discovered_{int(datetime.now(timezone.utc).timestamp())}_{random.randint(1000, 9999)}",
                parameters=idea.get("parameters", {}),
                rules=idea.get("rules", [])
            )
            return genome
        except Exception as e:
            logger.error(f"Failed to convert idea to genome: {e}")
            return None

    async def _generate_parameter_variations(self, strategy: StrategyGenome) -> List[StrategyGenome]:
        """Generate parameter variations for optimization."""
        variations = []

        # Create variations by tweaking parameters
        base_params = strategy.parameters

        for param_name in base_params.keys():
            if isinstance(base_params[param_name], (int, float)):
                # Create 3 variations: -10%, base, +10%
                base_value = base_params[param_name]

                for multiplier in [0.9, 1.0, 1.1]:
                    new_params = base_params.copy()
                    new_params[param_name] = base_value * multiplier

                    variation = StrategyGenome(
                        strategy_id=f"var_{strategy.strategy_id}_{param_name}_{multiplier}",
                        parameters=new_params,
                        rules=strategy.rules.copy()
                    )
                    variations.append(variation)

        return variations

    async def _ensure_client(self) -> None:
        """Lazy initialization of Claude SDK client."""
        if self.client is None:
            options = ClaudeAgentOptions(
                allowed_tools=[],
                system_prompt=self._get_evolution_prompt(),
                max_turns=15
            )
            self.client = ClaudeSDKClient(options=options)
            await self.client.__aenter__()
            logger.info("Strategy Evolution Engine Claude client initialized")

    async def _strategy_dict_to_genome(self, strategy_dict: Dict[str, Any]) -> StrategyGenome:
        """Convert strategy dictionary to genome."""
        return StrategyGenome(
            strategy_id=strategy_dict.get("id", f"strategy_{int(datetime.now(timezone.utc).timestamp())}"),
            parameters=strategy_dict.get("parameters", {}),
            rules=strategy_dict.get("rules", [])
        )

    async def _store_evolution_results(self, population: EvolutionPopulation) -> None:
        """Store evolution results."""
        await self.state_manager.save_evolution_results(population.to_dict())

    async def _store_discovered_strategy(self, strategy: StrategyGenome) -> None:
        """Store discovered strategy."""
        await self.state_manager.save_discovered_strategy(strategy.to_dict())

    async def _store_optimization_results(self, original: StrategyGenome, optimized: StrategyGenome) -> None:
        """Store optimization results."""
        results = {
            "original_strategy": original.to_dict(),
            "optimized_strategy": optimized.to_dict(),
            "improvement": optimized.fitness_score - original.fitness_score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.state_manager.save_optimization_results(results)

    def _get_evolution_prompt(self) -> str:
        """Get the system prompt for strategy evolution."""
        return """
        You are an expert trading strategy researcher and evolutionary algorithm designer.

        Your role is to generate novel trading strategies and optimize existing ones through:
        - Creative strategy ideation
        - Parameter optimization
        - Evolutionary algorithm design
        - Market condition adaptation

        Focus on strategies that are:
        - Systematically implementable
        - Risk-managed
        - Adaptable to changing market conditions
        - Backtestable with historical data

        Always consider risk management as the highest priority.
        """