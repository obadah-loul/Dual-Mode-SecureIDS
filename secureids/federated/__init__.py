"""Federated learning planning utilities.

Task 9B exposes configuration validation and dry-run split planning only. Real
federated training is intentionally not implemented here.
"""

from secureids.federated.config import FederatedConfig, FederatedConfigError

__all__ = ["FederatedConfig", "FederatedConfigError"]
