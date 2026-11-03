"""Small CPU-only offline RL benchmark inspired by CleanRL + Minari.

The experiment intentionally uses a deterministic local dataset so it can be
reproduced without downloading a benchmark or calling a remote service.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class Dataset:
    observations: np.ndarray
    actions: np.ndarray
    next_observations: np.ndarray
    rewards: np.ndarray
    dones: np.ndarray


class ChainEnv:
    """Six-state sparse-reward environment with a deliberately biased buffer."""

    n_states = 6

    def reset(self, seed: int) -> np.ndarray:
        self.state = 0
        return self._obs()

    def _obs(self) -> np.ndarray:
        obs = np.zeros(self.n_states, dtype=np.float32)
        obs[self.state] = 1.0
        return obs

    def step(self, action: int) -> tuple[np.ndarray, float, bool]:
        self.state = min(self.n_states - 1, self.state + (1 if action == 1 else 0))
        done = self.state == self.n_states - 1
        return self._obs(), (1.0 if done else -0.01), done


def expert_action(obs: np.ndarray) -> int:
    return int(np.argmax(obs) < ChainEnv.n_states - 1)


def collect(seed: int, episodes: int = 80) -> Dataset:
    rng = np.random.default_rng(seed)
    env = ChainEnv()
    rows: list[tuple[np.ndarray, int, np.ndarray, float, bool]] = []
    for episode in range(episodes):
        obs = env.reset(seed * 1000 + episode)
        done = False
        steps = 0
        while not done and steps < 20:
            # Most episodes are bad demonstrations that never leave state 0.
            action = expert_action(obs) if episode % 4 == 0 else 0
            if episode % 4 == 0 and rng.random() < 0.10:
                action = 0
            next_obs, reward, done = env.step(action)
            rows.append((obs.astype(np.float32), action, next_obs.astype(np.float32), reward, done))
            obs = next_obs
            steps += 1
    return Dataset(
        observations=np.stack([r[0] for r in rows]),
        actions=np.asarray([r[1] for r in rows], dtype=np.int64),
        next_observations=np.stack([r[2] for r in rows]),
        rewards=np.asarray([r[3] for r in rows], dtype=np.float32),
        dones=np.asarray([r[4] for r in rows], dtype=np.float32),
    )


class Policy(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(ChainEnv.n_states, 32), nn.Tanh(), nn.Linear(32, 2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class QNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(ChainEnv.n_states, 64), nn.ReLU(), nn.Linear(64, 2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def evaluate(policy: nn.Module, seed: int, episodes: int = 20) -> float:
    env = ChainEnv()
    returns = []
    with torch.no_grad():
        for i in range(episodes):
            obs = env.reset(seed * 10000 + i)
            total, done = 0.0, False
            while not done:
                action = int(policy(torch.tensor(obs, dtype=torch.float32).unsqueeze(0)).argmax(1).item())
                obs, reward, terminated = env.step(action)
                total += reward
                done = terminated or total < -0.2
                if not done and total < -0.2:
                    done = True
            returns.append(total)
    return float(np.mean(returns))


def train_bc(data: Dataset, seed: int, steps: int = 900) -> float:
    torch.manual_seed(seed)
    model = Policy()
    opt = torch.optim.Adam(model.parameters(), lr=3e-3)
    x = torch.tensor(data.observations)
    y = torch.tensor(data.actions)
    for _ in range(steps):
        loss = F.cross_entropy(model(x), y)
        opt.zero_grad(); loss.backward(); opt.step()
    return evaluate(model, seed)


def train_cql(data: Dataset, seed: int, steps: int = 600, alpha: float = 0.01) -> float:
    torch.manual_seed(seed)
    q = QNet(); target = QNet(); target.load_state_dict(q.state_dict())
    opt = torch.optim.Adam(q.parameters(), lr=2e-3)
    obs = torch.tensor(data.observations); actions = torch.tensor(data.actions)
    nxt = torch.tensor(data.next_observations); rewards = torch.tensor(data.rewards); dones = torch.tensor(data.dones)
    for step in range(steps):
        values = q(obs)
        chosen = values.gather(1, actions[:, None]).squeeze(1)
        with torch.no_grad():
            bootstrap = target(nxt).max(1).values
            td_target = rewards + 0.99 * (1.0 - dones) * bootstrap
        bellman = F.smooth_l1_loss(chosen, td_target)
        conservative = torch.logsumexp(values, dim=1).mean() - chosen.mean()
        loss = bellman + alpha * conservative
        opt.zero_grad(); loss.backward(); opt.step()
        if (step + 1) % 100 == 0:
            target.load_state_dict(q.state_dict())
    return evaluate(q, seed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=80)
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 11, 21])
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results" / "metrics.json")
    args = parser.parse_args()
    rows = []
    for seed in args.seeds:
        random.seed(seed); np.random.seed(seed)
        data = collect(seed, args.episodes)
        bc = train_bc(data, seed)
        cql = train_cql(data, seed)
        rows.append({"seed": seed, "transitions": int(len(data.actions)), "bc_return": bc, "cql_return": cql})
    report = {
        "dataset": "ChainEnv biased offline buffer (Gymnasium-style, Minari-compatible schema)",
        "seeds": args.seeds,
        "runs": rows,
        "summary": {
            "bc_mean_return": float(np.mean([r["bc_return"] for r in rows])),
            "cql_mean_return": float(np.mean([r["cql_return"] for r in rows])),
            "cql_minus_bc": float(np.mean([r["cql_return"] - r["bc_return"] for r in rows])),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
