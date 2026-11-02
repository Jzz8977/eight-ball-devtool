# pooltool attribution

Upstream: https://github.com/ekiefl/pooltool

Author: Evan Kiefl and contributors. License: Apache License 2.0.

The application uses pooltool-billiards 0.6.0 through an adapter. No physics
solver code was copied or reimplemented. The project's private configuration
loader redirects pooltool.config.paths to runtime/pooltool-config without
changing its physics source or the user's existing pooltool configuration.

The teaching experiments in computation/experiments.py adapt the setup and
analysis from upstream docs/examples/30_degree_rule.ipynb and straight_shot.ipynb:

- https://pooltool.readthedocs.io/en/latest/examples/30_degree_rule.html
- https://pooltool.readthedocs.io/en/latest/examples/straight_shot.html

Changes: standalone callable functions and CLI, explicit validation, array API
compatible with version 0.6.0, fixed random generator, CSV/JSON output, optional
Matplotlib plots, and a separate cue-scratch statistic for straight shots.

The 30-degree rule's ideal formula is provided only with its rolling/frictionless
assumptions. It is not hardcoded as a universal trajectory predictor.
