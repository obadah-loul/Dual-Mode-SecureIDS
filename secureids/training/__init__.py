"""Training entry points for SecureIDS V2.

Only the torch-free config types are re-exported here so that importing
``secureids.training`` stays lightweight (config validation does not require
torch). The training/dataset/checkpoint modules are imported explicitly from
their submodules, e.g. ``from secureids.training.centralized import
run_centralized_training``.
"""

from secureids.training.config import (
    TrainingConfig,
    TrainingConfigError,
    load_training_config,
)

__all__ = [
    "TrainingConfig",
    "TrainingConfigError",
    "load_training_config",
]
