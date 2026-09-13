# TracePulse models

A model artifact is loadable only when its reviewed metadata names the exact feature schema, dataset SHA-256, positive sample count, metrics, training library versions, and artifact hash. Until an offline review activates the artifact, every adapter returns MODEL_NOT_READY and the decision engine uses deterministic security checks.