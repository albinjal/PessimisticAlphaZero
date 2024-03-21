

base_parameters = {
    "model_type": "seperated",
    "observation_embedding": "default",
    "activation_fn": "relu",
    "norm_layer": "none",
    "dir_epsilon": 0.25,
    "dir_alpha": 2.0,
    "selection_policy": 'PUCT',
    "puct_c": 1.0,
    "selection_value_transform": 'identity',
    "use_visit_count": True,
    "regularization_weight": 1e-4,
    "tree_evaluation_policy": "visit",
    "eval_param": 1.0,
    "tree_temperature": None,
    "tree_value_transform": 'identity',
    "hidden_dim": 64,
    "learning_rate": 1e-3,
    "sample_batch_ratio": 1,
    "n_steps_learning": 1,
    "training_epochs": 8,
    "planning_budget": 32,
    "layers": 5,
    "replay_buffer_multiplier": 10,
    "discount_factor": 1.0,
    "lr_gamma": 1.0,
    "iterations": 40,
    "policy_loss_weight": 0.3,
    "value_loss_weight": 0.7,
    "max_episode_length": 200,
    "episodes_per_iteration": 6,
}

lake_config ={
    "max_episode_length": 100,
    "discount_factor": 0.9,
    "iterations": 30,
    "observation_embedding": "coordinate",
    "eval_param": 1.0,
    'training_epochs': 2,
    }

env_challenges = [
    {
        "env_description": "CartPole-v1",
        "max_episode_length": 300,
        "iterations": 40,
        "env_params": dict(id="CartPole-v1", max_episode_steps=1000000000),
        "observation_embedding": "default",
        "ncols": None,
    },
    {
        "env_description": "CliffWalking-v0",
        "max_episode_length": 100,
        "iterations": 30,
        "env_params": dict(id="CliffWalking-v0", max_episode_steps=1000000000),
        "ncols": 12,
    },
    {**lake_config,
        "env_description": "FrozenLake-v1-4x4",
        "ncols": 4,
        "env_params": dict(
            id="FrozenLake-v1",
            desc=None,
            map_name="4x4",
            is_slippery=False,
            max_episode_steps=1000000000,
        ),
    },
    {**lake_config,
        "env_description": "FrozenLake-v1-8x8",
        "ncols": 8,
        "env_params": dict(
            id="FrozenLake-v1",
            desc=None,
            map_name="8x8",
            is_slippery=False,
            max_episode_steps=1000000000,
        )

    },
]