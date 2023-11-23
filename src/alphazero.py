from abc import ABC, abstractmethod
from typing import Generic, Optional, Tuple, TypeVar, Callable, Any
import numpy as np
import gymnasium as gym
import copy
import graphviz


ActionType = TypeVar("ActionType")
ObservationType = TypeVar("ObservationType")


class Node(Generic[ObservationType, ActionType]):
    parent: Optional["Node[ObservationType, ActionType]"]
    # Since we have to use Discrete action space the ActionType is an integer so we could also use a list
    children: dict[ActionType, "Node[ObservationType, ActionType]"]
    visits: int = 1
    subtree_value: float = 0.0
    value_evaluation: float = 0.0
    reward: float
    # Discrete action space
    action_space: gym.spaces.Discrete
    observation: Optional[ObservationType]

    def __init__(
        self,
        parent: Optional["Node[ObservationType, ActionType]"],
        reward: float,
        action_space: gym.spaces.Discrete,
        observaton: Optional[ObservationType] = None,
        terminal: bool = False,
    ):
        # TODO: lazy init
        self.children = {}
        self.action_space = action_space
        self.reward = reward
        self.parent = parent
        self.terminal = terminal
        self.observation = observaton

    def is_terminal(self) -> bool:
        return self.terminal

    def step(self, action: ActionType) -> "Node[ObservationType, ActionType]":
        # steps into the action and returns that node
        child = self.children[action]
        child.visits += 1
        return child

    def backprop(self, value: float) -> None:
        self.value_evaluation = value
        node: Node[ObservationType, ActionType] | None = self
        while node is not None:
            node.subtree_value += self.value_evaluation + self.reward
            node = node.parent

    def default_value(self) -> float:
        return self.subtree_value / self.visits

    def is_fully_expanded(self) -> bool:
        return len(self.children) == self.action_space.n

    def sample_unexplored_action(self) -> np.int64:
        """
        mask – An optional mask for if an action can be selected. Expected np.ndarray of shape (n,) and dtype np.int8 where 1 represents valid actions and 0 invalid / infeasible actions. If there are no possible actions (i.e. np.all(mask == 0)) then space.start will be returned.
        """
        mask = np.ones(self.action_space.n, dtype=np.int8)
        for action in self.children:
            mask[action] = 0
        return self.action_space.sample(mask=mask)

    def visualize(
        self,
        var_fn: Optional[Callable[["Node[ObservationType, ActionType]"], Any]] = None,
        max_depth: int = 10,
    ) -> None:
        dot = graphviz.Digraph(comment="MCTS Tree")
        self._add_node_to_graph(dot, var_fn, max_depth=max_depth)
        dot.render(filename="mcts_tree.gv", view=True)

    def _add_node_to_graph(
        self,
        dot: graphviz.Digraph,
        var_fn: Optional[Callable[["Node[ObservationType, ActionType]"], Any]] = None,
        max_depth: int = 30,
    ) -> None:
        if max_depth == 0:
            return
        label = f"R: {self.reward}, SS: {self.subtree_value: .2f}, V: {self.value_evaluation: .2f}\nVisit: {self.visits}, T: {int(self.terminal)}"
        if var_fn is not None:
            label += f", Var: {var_fn(self)}"
        dot.node(str(id(self)), label=label)
        for action, child in self.children.items():
            child._add_node_to_graph(dot, var_fn, max_depth=max_depth - 1)

            dot.edge(str(id(self)), str(id(child)), label=f"Action: {action}")

    def __str__(self):
        return f"Visits: {self.visits}, ter: {int(self.terminal)}\nR: {self.reward}\nSub_sum: {self.subtree_value}\nRollout: {self.default_value()}"

    def __repr__(self):
        return self.__str__()


class Policy(ABC, Generic[ObservationType, ActionType]):
    @abstractmethod
    def __call__(self, node: Node[ObservationType, ActionType]) -> ActionType:
        pass


class SelectionPolicy(ABC, Generic[ObservationType, ActionType]):
    @abstractmethod
    def __call__(self, node: Node[ObservationType, ActionType]) -> ActionType | None:
        pass


class UCB(SelectionPolicy[ObservationType, ActionType]):
    def __init__(self, c: float):
        self.c = c

    def __call__(self, node: Node[ObservationType, ActionType]) -> ActionType | None:
        # if not fully expanded, return None
        if not node.is_fully_expanded():
            return None

        # if fully expanded, return the action with the highest UCB value
        # Idea: potentially mess around with making this stochastic
        return max(node.children, key=lambda action: self.ucb(node, action))

    def ucb(self, node: Node[ObservationType, ActionType], action: ActionType) -> float:
        child = node.children[action]
        return child.default_value() + self.c * (node.visits / child.visits) ** 0.5


class RandomPolicy(Policy[ObservationType, np.int64]):
    def __call__(self, node: Node[ObservationType, np.int64]) -> np.int64:
        return node.action_space.sample()


class DefaultExpansionPolicy(Policy[ObservationType, np.int64]):
    def __call__(self, node: Node[ObservationType, np.int64]) -> np.int64:
        # returns a uniformly random unexpanded action
        return node.sample_unexplored_action()


class DefaultTreeEvaluator(Policy[ObservationType, np.int64]):
    # the default tree evaluator selects the action with the most visits
    def __call__(self, node: Node[ObservationType, np.int64]) -> np.int64:
        return max(node.children, key=lambda action: node.children[action].visits)


class MCTS(Generic[ObservationType, ActionType]):
    env: gym.Env[ObservationType, ActionType]
    selection_policy: SelectionPolicy[ObservationType, ActionType]
    expansion_policy: Policy[
        ObservationType, ActionType
    ]  # the expansion policy is usually "pick uniform non explored action"

    def __init__(
        self,
        selection_policy: SelectionPolicy[ObservationType, ActionType],
        expansion_policy: Policy[ObservationType, ActionType] = DefaultExpansionPolicy[
            ObservationType
        ](),
    ):
        self.selection_policy = selection_policy  # the selection policy should return None if the input node should be expanded
        self.expansion_policy = expansion_policy

    def search(self, env: gym.Env[ObservationType, ActionType], iterations: int):
        # the env should be in the state we want to search from
        self.env = env
        # assert that the type of the action space is discrete
        assert isinstance(env.action_space, gym.spaces.Discrete)
        root_node = Node[ObservationType, ActionType](
            parent=None, reward=0.0, action_space=env.action_space
        )
        return self.build_tree(root_node, iterations)

    def build_tree(self, from_node: Node[ObservationType, ActionType], iterations: int):
        for _ in range(iterations):
            selected_node_for_expansion, env = self.select_node_to_expand(from_node)
            # check if the node is terminal
            if selected_node_for_expansion.is_terminal():
                eval_node = selected_node_for_expansion
            else:
                # expand the node
                eval_node = self.expand(selected_node_for_expansion, env)
            # evaluate the node
            value = self.value_function(eval_node, env)
            # backpropagate the value
            eval_node.backprop(value)
        return from_node

    def value_function(
        self,
        node: Node[ObservationType, ActionType],
        env: gym.Env[ObservationType, ActionType],
        rollout_budget = 40,
    ) -> float:

        # if the node is terminal, return the reward
        if node.is_terminal():
            return node.reward

        # if the node is not terminal, simulate the enviroment with random actions and return the accumulated reward until termination
        accumulated_reward = 0.0
        for _ in range(rollout_budget):
            _, reward, terminated, truncated, _ = env.step(env.action_space.sample())
            accumulated_reward += float(reward)
            if terminated or truncated:
                break

        return accumulated_reward

    def select_node_to_expand(
        self, from_node: Node[ObservationType, ActionType]
    ) -> Tuple[Node[ObservationType, ActionType], gym.Env[ObservationType, ActionType]]:
        """
        Returns the node to be expanded next.
        Returns None if the node is terminal.
        The selection policy returns None if the input node should be expanded.
        """

        node = from_node
        # increase the visits of the root node (why not)
        node.visits += 1

        env = copy.deepcopy(self.env)
        while not node.is_terminal():
            action = self.selection_policy(node)
            if action is None:
                return node, env
            node = node.step(action)
            # also step the environment
            env.step(action)

        return node, env

    def expand(
        self,
        node: Node[ObservationType, ActionType],
        env: gym.Env[ObservationType, ActionType],
    ) -> Node[ObservationType, ActionType]:
        """
        Expands the node and returns the expanded node.
        """
        action = self.expansion_policy(node)
        # step the environment
        observation, reward, terminated, truncated, _ = env.step(action)
        terminal = terminated or truncated
        # create the node
        new_child = Node[ObservationType, ActionType](
            parent=node,
            reward=float(reward),
            action_space=node.action_space,
            terminal=terminal,
            observaton=observation,
        )
        node.children[action] = new_child
        return new_child


def run_episode(
    solver: MCTS,
    env: gym.Env,
    tree_evaluation_policy: Policy,
    compute_budget=1000,
    max_steps=1000,
    render_env=None,
    verbose=False,
):
    total_reward = 0.0

    for step in range(max_steps):
        tree = solver.search(env, compute_budget)
        print(f"Found {tree.default_value()}")
        action = tree_evaluation_policy(tree)
        observation, reward, terminated, truncated, _ = env.step(action)
        total_reward += float(reward)
        if render_env is not None:
            render_env.step(action)
        if verbose:
            print(
                f"{step}. A: {action}, R: {reward}, T: {terminated}, Tr: {truncated}, total_reward: {total_reward}"
            )
        if terminated or truncated:
            break

    return total_reward


def vis_tree(solver: MCTS, env: gym.Env, compute_budget=100, max_depth=5):
    tree = solver.search(env, compute_budget)
    return tree.visualize(max_depth=max_depth)


if __name__ == "__main__":
    seed = 0
    actType = np.int64
    # env_id = "CartPole-v1"
    env_id = "FrozenLake-v1"
    # env_id = "Taxi-v3"
    env: gym.Env[Any, actType] = gym.make(env_id)
    env.reset(seed=seed)
    render_env: gym.Env[Any, actType] = gym.make(env_id, render_mode="human")
    render_env.reset(seed=seed)
    selection_policy = UCB[Any, actType](c=5.0)
    tree_evaluation_policy = DefaultTreeEvaluator[Any]()

    mcts = MCTS[Any, actType](selection_policy=selection_policy)
    # vis_tree(mcts, env, compute_budget=1000, max_depth=3)
    total_reward = run_episode(mcts, env, tree_evaluation_policy, compute_budget=5000, render_env=render_env, verbose=True)
    print(f"Total reward: {total_reward}")
    env.close()
    render_env.close()
