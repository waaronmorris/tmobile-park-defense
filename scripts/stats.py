"""
Interval estimates for everything the visualization draws.

Three different quantities are on those charts and they do not share an error model:

  proportions   batting average, hit-type rates -- bounded in [0,1], and several of
                the interesting cells sit at .02 or .99 where the textbook
                p +/- z*sqrt(p(1-p)/n) runs off the end of the scale and produces
                impossible bounds. Wilson score intervals instead.
  means         BA - xBA, carry residual -- ordinary standard error of the mean.
  ratios        strikeout park factor, hit-type rate vs league -- a ratio of two
                proportions, which is skewed; the interval is built on log(ratio)
                by the delta method and exponentiated back, so it is asymmetric in
                the right direction and cannot go negative.

All intervals are 95% two-sided unless a caller says otherwise.
"""
import numpy as np

Z95 = 1.959963984540054


def wilson(k, n, z=Z95):
    """
    Wilson score interval for a proportion.

    Correct at the boundaries, where the normal approximation is not: 0 successes in
    50 gives [0, .071] rather than the degenerate [0, 0].
    """
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    out_lo = np.full(n.shape, np.nan)
    out_hi = np.full(n.shape, np.nan)
    ok = n > 0
    if not np.any(ok):
        return out_lo, out_hi
    p = np.where(ok, k / np.where(ok, n, 1), np.nan)
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    out_lo = np.where(ok, np.clip(centre - half, 0, 1), np.nan)
    out_hi = np.where(ok, np.clip(centre + half, 0, 1), np.nan)
    return out_lo, out_hi


def mean_ci(mean, sem, z=Z95):
    """Symmetric interval for a sample mean."""
    mean = np.asarray(mean, dtype=float)
    sem = np.asarray(sem, dtype=float)
    return mean - z * sem, mean + z * sem


def ratio_ci(k1, n1, k2, n2, z=Z95):
    """
    Interval for the ratio of two independent proportions, via the delta method on
    the log ratio.

        Var(log(p1/p2)) ~= (1-p1)/(n1 p1) + (1-p2)/(n2 p2)

    Returns (ratio, lo, hi). Undefined where either numerator is zero, since log(0)
    has no interval to give -- those come back NaN rather than a fabricated bound.
    """
    k1, n1, k2, n2 = (np.asarray(a, dtype=float) for a in (k1, n1, k2, n2))
    with np.errstate(divide="ignore", invalid="ignore"):
        p1, p2 = k1 / n1, k2 / n2
        ratio = p1 / p2
        var = (1 - p1) / (n1 * p1) + (1 - p2) / (n2 * p2)
        half = z * np.sqrt(var)
        lo, hi = ratio * np.exp(-half), ratio * np.exp(half)
    bad = (k1 <= 0) | (k2 <= 0) | ~np.isfinite(ratio)
    return (np.where(bad, np.nan, ratio),
            np.where(bad, np.nan, lo),
            np.where(bad, np.nan, hi))


def moe_for_proportion(p, n, z=Z95):
    """Half-width of the normal interval -- the headline 'plus or minus' figure."""
    p = np.asarray(p, dtype=float)
    n = np.asarray(n, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(n > 0, z * np.sqrt(p * (1 - p) / n), np.nan)


def n_needed(effect, p=0.32, z=Z95):
    """
    Balls in play required to resolve an effect of this size on a rate near p.

    Answers the question the charts keep raising: a park sits .004 off the league,
    is that measurable at all? Two-sided, one-sample, no power term -- this is the
    n at which the effect equals its own margin of error, i.e. the floor below which
    it cannot be seen regardless of how real it is.
    """
    effect = np.asarray(effect, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(effect > 0, (z**2 * p * (1 - p)) / effect**2, np.nan)
