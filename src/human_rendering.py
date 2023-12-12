import glob
import os
import time
import gymnasium as gym
import numpy as np
from azmcts import AlphaZeroMCTS
from mcts import MCTS

from model import AlphaZeroModel
from policies import PUCT, DefaultTreeEvaluator, PolicyDistribution


def run_vis(
    checkpoint_path,
    env_args,
    tree_eval_policy,
    compute_budget=1000,
    max_steps=1000,
    verbose=True,
    goal_obs=None,
    seed=None,
    sleep_time=0.0,
):
    env = gym.make(**env_args)
    render_env = gym.make(**env_args, render_mode="human")

    selection_policy = PUCT(c=1)
    # if checkpoint_path contains a wildcard, we need to expand it
    if "*" in checkpoint_path:
        matches = glob.glob(checkpoint_path)
        dir = max(matches)
        checkpoint_path = os.path.join(dir, "checkpoint.pth")


    model = AlphaZeroModel.load_model(checkpoint_path, env)
    agent = AlphaZeroMCTS(selection_policy=selection_policy, model=model)

    visualize_gameplay(
        agent,
        env,
        render_env,
        tree_eval_policy,
        compute_budget,
        max_steps,
        verbose,
        goal_obs,
        seed,
        sleep_time,
    )
    time.sleep(1)
    env.close()
    render_env.close()


def main_runviss():
    env_id = "CliffWalking-v0"
    env_args = {"id": env_id}
    run_vis(
        f"runs/{env_id}*",
        env_args,
        DefaultTreeEvaluator(),
        compute_budget=500,
        max_steps=1000,
        verbose=True,
        goal_obs=None,
        seed=1,
        sleep_time=0,
    )




def visualize_gameplay(solver: MCTS,
    env: gym.Env,
    render_env: gym.Env,
    tree_evaluation_policy: PolicyDistribution,
    compute_budget=1000,
    max_steps=1000,
    verbose=True,
    goal_obs=None,
    seed=None,
    sleep_time=.0):
    """Runs an episode using the given solver and environment."""
    assert isinstance(env.action_space, gym.spaces.Discrete)
    n = env.action_space.n
    observation, _ = env.reset(seed=seed)
    render_env.reset(seed=seed)

    for step in range(max_steps):
        tree = solver.search(env, compute_budget, observation, np.float32(0.0))
        policy_dist = tree_evaluation_policy.distribution(tree)
        action = policy_dist.sample()
        # res will now contain the obersevation, policy distribution, action, as well as the reward and terminal we got from executing the action
        observation, reward, terminated, truncated, _ = env.step(action.item())
        render_env.step(action.item())
        terminal = terminated or truncated
        time.sleep(sleep_time)

        if verbose:
            if goal_obs is not None:
                vis_counter = tree.state_visitation_counts()
                print(f"Visits to goal state: {vis_counter[goal_obs]}")
            norm_entropy = policy_dist.entropy() / np.log(n)
            print(f"Policy: {policy_dist.probs}, Norm Entropy: {norm_entropy: .2f}")
            print(f"{step}. O: {observation}, A: {action}, R: {reward}, T: {terminal}")

        if terminal:
            break


if __name__ == "__main__":
    main_runviss()