# Imports.
import numpy as np;


# -------------------------------------------------------------------
# --------------------------Relaxation. -----------------------------
# -------------------------------------------------------------------

def residual_XiaoCatto2006(inverse_aspect_ratio, safety_factor, k_rho = 0):
	# For the GAM, we can typically set k_rho = 0.
	gdtheta = (1.6 * inverse_aspect_ratio**1.5 + 0.5 * inverse_aspect_ratio**2 + 0.36 * inverse_aspect_ratio**2.5) - 2.44 * inverse_aspect_ratio**0.5 * (k_rho * safety_factor)**2
	actual_residual = 1. / (1. + gdtheta * safety_factor**2 / inverse_aspect_ratio**2);
	return actual_residual;