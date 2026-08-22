"""Numerically check the 2-D polar-coordinate Laplacian.

Example:
    f(r, theta) = r**2 * cos(2*theta) = x**2 - y**2

Its analytical Laplacian is zero.
"""

import numpy as np
import matplotlib.pyplot as plt


def field(r: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Return f(r, theta) = r^2 cos(2 theta)."""
    return r**2 * np.cos(2.0 * theta)


def polar_laplacian(
    values: np.ndarray,
    radii: np.ndarray,
    angles: np.ndarray,
) -> np.ndarray:
    """Approximate ∇²f = f_rr + f_r/r + f_tt/r² with finite differences."""
    edge_order = 2
    f_r = np.gradient(values, radii, axis=0, edge_order=edge_order)
    f_rr = np.gradient(f_r, radii, axis=0, edge_order=edge_order)
    f_t = np.gradient(values, angles, axis=1, edge_order=edge_order)
    f_tt = np.gradient(f_t, angles, axis=1, edge_order=edge_order)

    r_grid = radii[:, None]
    return f_rr + f_r / r_grid + f_tt / r_grid**2


def main() -> None:
    # Avoid r=0 because polar coordinates are singular at the origin.
    radii = np.linspace(0.1, 2.0, 300)
    angles = np.linspace(0.0, 2.0 * np.pi, 600, endpoint=False)
    r_grid, theta_grid = np.meshgrid(radii, angles, indexing="ij")

    values = field(r_grid, theta_grid)
    laplacian = polar_laplacian(values, radii, angles)

    # Exclude boundary cells, where one-sided finite differences are less accurate.
    interior = laplacian[2:-2, 2:-2]
    print(f"Maximum interior absolute error: {np.max(np.abs(interior)):.6e}")
    print("Analytical value: 0")

    x = r_grid * np.cos(theta_grid)
    y = r_grid * np.sin(theta_grid)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    field_plot = axes[0].pcolormesh(x, y, values, shading="auto", cmap="coolwarm")
    axes[0].set_title(r"$f(r,\theta)=r^2\cos(2\theta)$")
    fig.colorbar(field_plot, ax=axes[0])

    lap_plot = axes[1].pcolormesh(x, y, laplacian, shading="auto", cmap="coolwarm")
    axes[1].set_title(r"Numerical $\nabla^2 f$ (expected: 0)")
    fig.colorbar(lap_plot, ax=axes[1])

    for axis in axes:
        axis.set_aspect("equal")
        axis.set_xlabel("x")
        axis.set_ylabel("y")

    plt.show()


if __name__ == "__main__":
    main()
