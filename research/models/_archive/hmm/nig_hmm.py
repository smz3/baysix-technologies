"""
NIG-HMM: Hidden Markov Model with Normal Inverse Gaussian emissions.
Baum-Welch (EM) estimation. Log-space forward-backward. Vectorised.

scipy NIG parameterisation: norminvgauss(a, b, loc, scale)
  a     > 0          tail-heaviness  (α in papers)
  |b|   < a          asymmetry       (β in papers)
  scale > 0          scale           (δ in papers)
  loc   unconstrained location       (μ in papers)

M-step uses unconstrained reparameterisation so the optimizer never
has to handle hard boundary violations:
  log_a   = log(a)              -> a  = exp(log_a)
  b_raw   = arctanh(b / a)      -> b  = tanh(b_raw) * a
  log_d   = log(scale)          -> scale = exp(log_d)
  mu      = loc                 (unchanged)
"""

import numpy as np
import scipy.stats as ss
import scipy.optimize as sopt
from tqdm import tqdm

_TINY = 1e-300


class NIGHMM:
    def __init__(self, n_states: int = 3, n_iter: int = 150, tol: float = 1e-5,
                 random_state: int = 42):
        self.n_states = n_states
        self.n_iter = n_iter
        self.tol = tol
        self._seed = random_state

        self.pi = None      # (K,)  initial state distribution
        self.A = None       # (K,K) row-stochastic transition matrix
        self.nig = None     # list of K dicts: {a, b, scale, loc}
        self.logL = -np.inf
        self.converged = False

    # ── Emission log-prob ─────────────────────────────────────────────────────

    def _log_B(self, X: np.ndarray) -> np.ndarray:
        """Return (T, K) log-emission matrix."""
        T = len(X)
        K = self.n_states
        out = np.empty((T, K))
        for k in range(K):
            p = self.nig[k]
            out[:, k] = ss.norminvgauss.logpdf(
                X, a=p['a'], b=p['b'], loc=p['loc'], scale=p['scale']
            )
        # Guard: replace -inf/nan with large negative (degenerate state detection)
        out = np.where(np.isfinite(out), out, -500.0)
        return out

    # ── Log-space forward-backward (vectorised) ───────────────────────────────

    @staticmethod
    def _logsumexp(arr: np.ndarray, axis: int) -> np.ndarray:
        m = arr.max(axis=axis, keepdims=True)
        return (m + np.log(np.sum(np.exp(arr - m), axis=axis, keepdims=True) + _TINY)).squeeze(axis)

    def _forward(self, log_B: np.ndarray) -> np.ndarray:
        T, K = log_B.shape
        log_A = np.log(self.A + _TINY)          # (K, K)
        log_alpha = np.empty((T, K))
        log_alpha[0] = np.log(self.pi + _TINY) + log_B[0]
        for t in range(1, T):
            # (K,) : for each destination k, logsumexp over source j
            mat = log_alpha[t - 1, :, None] + log_A   # (K_src, K_dst)
            log_alpha[t] = self._logsumexp(mat, axis=0) + log_B[t]
        return log_alpha

    def _backward(self, log_B: np.ndarray) -> np.ndarray:
        T, K = log_B.shape
        log_A = np.log(self.A + _TINY)          # (K, K)
        log_beta = np.zeros((T, K))
        for t in range(T - 2, -1, -1):
            # (K_src,): for each source j, logsumexp over destination k
            mat = log_A + log_B[t + 1][None, :] + log_beta[t + 1][None, :]  # (K_src, K_dst)
            log_beta[t] = self._logsumexp(mat, axis=1)
        return log_beta

    # ── E-step ────────────────────────────────────────────────────────────────

    def _e_step(self, X: np.ndarray):
        log_B = self._log_B(X)
        log_alpha = self._forward(log_B)
        log_beta = self._backward(log_B)
        T, K = log_B.shape

        # gamma (T, K)
        log_gamma = log_alpha + log_beta
        log_Z = self._logsumexp(log_gamma, axis=1)        # (T,)
        log_gamma -= log_Z[:, None]
        gamma = np.exp(log_gamma)

        # xi (T-1, K, K)
        log_A = np.log(self.A + _TINY)
        log_xi = (log_alpha[:-1, :, None]       # (T-1, K_src, 1)
                  + log_A[None, :, :]           # (1,   K_src, K_dst)
                  + log_B[1:, None, :]          # (T-1, 1,     K_dst)
                  + log_beta[1:, None, :])      # (T-1, 1,     K_dst)
        log_xi_flat = log_xi.reshape(T - 1, -1)
        log_Z_xi = self._logsumexp(log_xi_flat, axis=1)  # (T-1,)
        log_xi -= log_Z_xi[:, None, None]
        xi = np.exp(log_xi)

        # log_Z[t] == log P(X) for all t (constant) — take index 0
        logL = float(log_Z[0])
        return gamma, xi, logL

    # ── M-step ────────────────────────────────────────────────────────────────

    def _reinit_state(self, X: np.ndarray, k: int, seed: int) -> None:
        """Seagull restart: reinitialise a degenerate state from global data moments."""
        rng = np.random.RandomState(seed)
        self.nig[k] = {
            'a':     2.0 + rng.rand() * 1.5,
            'b':     rng.randn() * 0.05,
            'scale': float(X.std()) * (0.4 + rng.rand() * 0.8),
            'loc':   float(X.mean()) + rng.randn() * float(X.std()) * 0.15
        }
        # Reset this state's row in A to uniform (to let EM re-discover transitions)
        K = self.n_states
        self.A[k] = np.ones(K) / K

    def _fit_nig_state(self, X: np.ndarray, w: np.ndarray, k: int) -> None:
        """Weighted MLE for NIG params of state k. Updates self.nig[k] in-place.

        Seagull restart: if state posterior < 1% of T, reinitialise rather than
        fitting a degenerate distribution — prevents K=4+ phantom states from
        inflating logL with razor-sharp NIG spikes.
        """
        w_sum = w.sum()
        T = len(X)
        if w_sum < 0.01 * T:
            self._reinit_state(X, k, seed=k * 7919 + int(w_sum * 1000) % 997)
            return
        if w_sum < 1e-8:
            return
        w_norm = w / w_sum

        p = self.nig[k]
        a0, b0, d0, m0 = p['a'], p['b'], p['scale'], p['loc']

        # Unconstrained parameterisation
        la0 = np.log(max(a0, 1e-6))
        br0 = np.arctanh(np.clip(b0 / (a0 + 1e-12), -0.9999, 0.9999))
        ld0 = np.log(max(d0, 1e-6))

        def obj(params):
            la, br, ld, mu = params
            a = np.exp(la)
            b = np.tanh(br) * a
            scale = np.exp(ld)
            lls = ss.norminvgauss.logpdf(X, a=a, b=b, loc=mu, scale=scale)
            lls = np.where(np.isfinite(lls), lls, -500.0)
            return -float(np.dot(w_norm, lls))

        res = sopt.minimize(
            obj, x0=[la0, br0, ld0, m0],
            method='Nelder-Mead',
            options={'maxiter': 300, 'xatol': 1e-4, 'fatol': 1e-6, 'disp': False}
        )

        la, br, ld, mu = res.x
        a = np.exp(la)
        b = np.tanh(br) * a
        scale = np.exp(ld)
        if a > 0 and scale > 0 and abs(b) < a:
            self.nig[k] = {'a': a, 'b': b, 'scale': scale, 'loc': mu}

    def _m_step(self, X: np.ndarray, gamma: np.ndarray, xi: np.ndarray) -> None:
        K = self.n_states

        # Update pi
        self.pi = gamma[0] + 1e-10
        self.pi /= self.pi.sum()

        # Update A
        A_num = xi.sum(axis=0) + 1e-10   # (K, K) add tiny floor for stability
        self.A = A_num / A_num.sum(axis=1, keepdims=True)

        # Update NIG per state
        for k in range(K):
            self._fit_nig_state(X, gamma[:, k], k)

    # ── Initialisation ────────────────────────────────────────────────────────

    def _init_params(self, X: np.ndarray, seed: int) -> None:
        rng = np.random.RandomState(seed)
        K = self.n_states

        self.pi = rng.dirichlet(np.ones(K))

        # Sticky transition matrix — each row drawn from Dirichlet with high self-weight
        A_raw = np.array([
            rng.dirichlet(np.ones(K) * 0.3 + np.eye(K)[j] * 5)
            for j in range(K)
        ])
        self.A = A_raw / A_raw.sum(axis=1, keepdims=True)

        mu_g = float(X.mean())
        sig_g = float(X.std())

        self.nig = []
        for k in range(K):
            self.nig.append({
                'a':     2.0 + rng.rand() * 0.5,
                'b':     rng.randn() * 0.05,
                'scale': sig_g * (0.7 + rng.rand() * 0.6),
                'loc':   mu_g + rng.randn() * sig_g * 0.1
            })

    # ── Fit (single run) ─────────────────────────────────────────────────────

    def _fit_single(self, X: np.ndarray, seed: int) -> float:
        self._init_params(X, seed)
        prev_logL = -np.inf

        for i in range(self.n_iter):
            gamma, xi, logL = self._e_step(X)
            self._m_step(X, gamma, xi)
            delta = logL - prev_logL
            if abs(delta) < self.tol and i > 5:
                self.converged = True
                break
            prev_logL = logL

        self.logL = logL
        return logL

    # ── Public fit (multi-restart) ────────────────────────────────────────────

    def fit(self, X: np.ndarray, n_restarts: int = 10, pbar_desc: str = "") -> "NIGHMM":
        """Fit with multiple random restarts; keep best log-likelihood run."""
        best_logL = -np.inf
        best_state = None
        rng_meta = np.random.RandomState(self._seed)
        seeds = rng_meta.randint(0, 100_000, size=n_restarts)

        for r in tqdm(range(n_restarts), desc=pbar_desc or f"K={self.n_states} restarts", leave=False):
            try:
                logL = self._fit_single(X, int(seeds[r]))
                tqdm.write(f"  restart {r+1:2d}/{n_restarts}  logL={logL:.4f}  "
                           f"converged={self.converged}")
                if logL > best_logL:
                    best_logL = logL
                    best_state = {
                        'pi': self.pi.copy(),
                        'A': self.A.copy(),
                        'nig': [dict(p) for p in self.nig],
                        'converged': self.converged
                    }
            except Exception as exc:
                tqdm.write(f"  restart {r+1:2d} FAILED: {exc}")

        if best_state is None:
            raise RuntimeError(f"All {n_restarts} restarts failed for K={self.n_states}")

        self.pi = best_state['pi']
        self.A = best_state['A']
        self.nig = best_state['nig']
        self.logL = best_logL
        self.converged = best_state['converged']
        return self

    # ── Inference ────────────────────────────────────────────────────────────

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return (T, K) filtered state probabilities."""
        gamma, _, _ = self._e_step(X)
        return gamma

    def viterbi(self, X: np.ndarray) -> np.ndarray:
        """Return most-likely Viterbi state sequence (T,)."""
        log_B = self._log_B(X)
        T, K = log_B.shape
        log_A = np.log(self.A + _TINY)

        vit = np.empty((T, K))
        psi = np.zeros((T, K), dtype=int)
        vit[0] = np.log(self.pi + _TINY) + log_B[0]

        for t in range(1, T):
            trans = vit[t - 1, :, None] + log_A   # (K_src, K_dst)
            psi[t] = trans.argmax(axis=0)
            vit[t] = trans.max(axis=0) + log_B[t]

        path = np.empty(T, dtype=int)
        path[-1] = vit[-1].argmax()
        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1, path[t + 1]]
        return path

    def state_occupancy(self, X: np.ndarray) -> np.ndarray:
        """Return mean posterior probability per state (K,)."""
        return self.predict_proba(X).mean(axis=0)

    # ── Model selection ───────────────────────────────────────────────────────

    def n_free_params(self) -> int:
        """(K-1) startprob + K*(K-1) transmat + K*4 NIG params."""
        K = self.n_states
        return (K - 1) + K * (K - 1) + K * 4

    def bic(self, X: np.ndarray) -> float:
        return -2.0 * self.logL + self.n_free_params() * np.log(len(X))

    def aic(self, X: np.ndarray) -> float:
        return -2.0 * self.logL + 2.0 * self.n_free_params()
