## Sergio W. Peterson

ML engineer in San Francisco, moving into robot learning.

I am building toward robotics ML / research-engineering roles: vision policies, imitation learning, RL refinement, viewpoint robustness, VLM trajectory evaluation, and sim-to-real sanity checks.

Current focus:

- Robot-learning flagship: camera-viewpoint robustness for vision-only manipulation policies.
- Experiment spine: fixed-camera BC baseline -> camera-shift degradation curve -> camera-randomization sweep -> BC + SAC/PPO refinement -> VLM failure evaluator -> small hardware check.
- Near-term output: reproducible configs, rollout videos, robustness curves, failure taxonomy, and a clean technical writeup.

## Background

- UC Berkeley, B.A. Data Science, 2024.
- BAIR research: LLM decision systems, SFT, retrieval, solver-backed evaluation.
- Berkeley ROAR: autonomous racing simulation infrastructure, opponent modeling, telemetry / safety analysis.
- Founding Engineer at Mars Accounting / Minerva Intelligence: production AI agents, LLM routing, workflow automation, evals, backend systems.
- AI Engineer at BrightLight Health: VLM / OCR clinical intake, PHI-safe agent workflows, deterministic scoring systems.
- Former ML/CV intern at Lexius: video models, action recognition, PyTorch training infrastructure.

## Featured Work

### Robot Viewpoint Robustness Study

Active flagship project. A manipulation-policy study asking:

> How much camera randomization helps, when it hurts, and where RL refinement can recover robustness after imitation learning fails.

Current scaffold:

- Robosuite / MuJoCo project structure.
- Timestamped run artifacts.
- Config snapshots.
- TensorBoard smoke logging.
- 225-pose camera evaluation grid.
- Random-rollout and camera-grid scripts.

### taskcli

SWE-Bench-style verifiable-reward harness:

- Imports coding tasks.
- Builds isolated Docker environments.
- Separates solver containers from grading containers.
- Extracts only `solution.patch`.
- Grades against fail-to-pass / pass-to-pass tests.
- Logs runs and artifacts with SQLite.

This is the RL-environment / eval-harness side of my work.

### VLM Procedural Assistant

Real-time VLM system for procedural step and error detection over technician video.

- Streaming video-language pipeline.
- Step / error state machine.
- F1 + latency scoring.
- 140+ logged experiments.

This informs the VLM trajectory-evaluator layer of my robot-learning work.

## Technical Reports

Non-peer-reviewed Berkeley technical reports and course research projects:

- Safety Critical Edgecase Testing for High Speed Autonomy.
- Grasp Planning with Sawyer.
- State Estimation with dead reckoning, Kalman filters, and EKFs.
- Nonholonomic Control with optimization, RRT, and sinusoidal steering.
- Visual Servoing for Sawyer control.

I include these as evidence of robotics fundamentals: control, estimation, planning, manipulation, telemetry, and safety evaluation.

## Learning Notes

I am keeping small RL reading artifacts lightweight and separate from the flagship:

- Sutton & Barto Chapter 2: multi-arm bandits visual simulator.
- Sutton & Barto Chapter 3: finite MDP visual simulator.
- Current study path: Sutton & Barto, CS285, robot-learning / VLA papers, RLHF / GRPO references.

## Stack

Python, PyTorch, NumPy, OpenCV, Robosuite, MuJoCo, ROS, Docker, Terraform, AWS, Azure, TypeScript, NestJS, FastAPI, Postgres, Redis.

ML / robotics interests:

- Imitation learning.
- Reinforcement learning.
- Vision-language-action policies.
- Robot manipulation.
- Sim-to-real evaluation.
- VLM reward / trajectory evaluators.
- Verifiable eval harnesses.

## Links

- Website: [sergiopeterson.dev](https://sergiopeterson.dev)
- LinkedIn: [linkedin.com/in/sergio-w-peterson](https://www.linkedin.com/in/sergio-w-peterson)
- Email: [sergiopeterson.dev@gmail.com](mailto:sergiopeterson.dev@gmail.com)
