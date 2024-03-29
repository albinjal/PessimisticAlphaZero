from abc import ABC, abstractmethod
import torch as th
import numpy as np
from core.node import Node
from policies.value_transforms import IdentityValueTransform, ValueTransform





class Policy(ABC):
    def __call__(self, node: Node) -> int:
        return self.sample(node)

    @abstractmethod
    def sample(self, node: Node) -> int:
        """Take a node and return an action"""


class PolicyDistribution(Policy):
    """Also lets us view the full distribution of the policy, not only sample from it.
    When we have the distribution, we can choose how to sample from it.
    We can either sample stochasticly from distribution or deterministically choose the action with the highest probability.
    We can also apply softmax with temperature to the distribution.
    """
    temperature: float
    value_transform: ValueTransform
    def __init__(self, temperature: float = None, value_transform: ValueTransform = IdentityValueTransform) -> None:
        super().__init__()
        self.temperature = temperature
        self.value_transform = value_transform


    def sample(self, node: Node) -> int:
        """
        Returns a random action from the distribution
        """
        return int(self.softmaxed_distribution(node).sample().item())

    @abstractmethod
    def _probs(self, node: Node) -> th.Tensor:
        """
        Returns the relative probabilities of the actions (excluding the special action)
        """
        pass

    def self_prob(self, node: Node, probs: th.Tensor) -> float:
        """
        Returns the relative probability of selecting the node itself
        """
        return probs.sum() / (node.visits - 1)


    def add_self_to_probs(self, node: Node, probs: th.Tensor) -> th.Tensor:
        """
        Takes the current policy and adds one extra value to it, which is the probability of selecting the node itself.
        Should return a tensor with one extra value at the end
        The default choice is to set it to 1/visits
        Note that policy is not yet normalized, so we can't just add 1/visits to the last value
        """
        self_prob = self.self_prob(node, probs)
        return th.cat([probs, th.tensor([self_prob])])


    def softmaxed_distribution(self, node: Node, include_self=False, **kwargs) -> th.distributions.Categorical:
        """
        Relative probabilities with self handling
        """
        # policy for leaf nodes
        if include_self and len(node.children) == 0:
            probs = th.zeros(int(node.action_space.n) + include_self, dtype=th.float32)
            probs[-1] = 1.0
            return th.distributions.Categorical(probs=probs)

        probs = self._probs(node)

        # softmax with temperature
        if self.temperature is None:
            if include_self:
                probs = self.add_self_to_probs(node, probs)
            return th.distributions.Categorical(probs=probs)
        elif self.temperature == 0.0 :
            # return a uniform distribution over the actions with the highest probability
            max_logits = th.max(probs)
            probs = (probs == max_logits).float()
            if include_self:
                probs = self.add_self_to_probs(node, probs)
            return th.distributions.Categorical(probs=probs)
        else:
            dist = th.distributions.Categorical(logits=probs / self.temperature)
            # add the probability of selecting the node itself
            if include_self:
                dist = th.distributions.Categorical(probs=self.add_self_to_probs(node, dist.probs))
            return dist



class RandomPolicy(Policy):
    def sample(self, node: Node) -> int:
        return node.action_space.sample()
