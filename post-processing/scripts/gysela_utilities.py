# Imports.
import numpy as np;
import pandas as pd;
import h5_reader_xr as reader;

# -------------------------------------------------------------------
# -------- -------------------Generic. ------------------------------
# -------------------------------------------------------------------

def slice_at_effective_radius(radial_time_series, effective_radius = 0.7):

	total_radial_size = radial_time_series.sizes["r"] - 1;
	radial_index = round(effective_radius * total_radial_size);
	return radial_time_series[:, radial_index];

def generate_time_range_by_series(radial_time_series, dt_diag):

	naive_range = np.arange(len(radial_time_series));
	return naive_range * dt_diag;

def flux_surface_average_2D(quantity_xarray, jacobian_xr_dictionary, use_integrated_jacobian = False):
	# The analytical formulation of a flux-surface average is the integral of the quantity over theta multiplied by the Jacobian, divided by the integral of the Jacobian over theta.
	# `sum(dim = ["theta"])` provides the sum over A * Js, which is fine if the denominator is also the sum of Js over theta.
	# HOWEVER, if the denominator is a proper integral, we are missing a factor of dtheta in the numerator, which is bad news bears.
	n_theta = quantity_xarray.sizes["theta"];
	naive_jacobian = jacobian_xr_dictionary["naive"];
	jacobian_integrated_over_theta = jacobian_xr_dictionary["integrated_over_theta"];
	dtheta_physical = (2 * np.pi) / n_theta;

	numerator = (quantity_xarray * naive_jacobian).sum(dim = "theta");
	denominator = naive_jacobian.sum(dim = "theta");

	if use_integrated_jacobian:
		# In general, you have no good reason to use this. You will not get unity for the flux surface average of 1, for example, which is pretty bad.
		# You will inject radially-scaling errors into your calculations.
		numerator = (quantity_xarray * naive_jacobian).sum(dim = "theta") * dtheta_physical;
		denominator = jacobian_integrated_over_theta;

	return numerator / denominator;

def flux_surface_average_3D(quantity_xarray, jacobian_xr_dictionary, use_integrated_jacobian = False):
	# See above.
	n_theta = quantity_xarray.sizes["theta"];
	naive_jacobian = jacobian_xr_dictionary["naive"];
	jacobian_integrated_over_theta_and_phi = jacobian_xr_dictionary["integrated_over_theta_and_phi"];
	dtheta_physical = (2 * np.pi) / n_theta;

	numerator = (quantity_xarray * naive_jacobian).sum(dim = ["theta", "phi"]);
	denominator = naive_jacobian.sum(dim = ["theta", "phi"]);

	if use_integrated_jacobian:

		numerator = (quantity_xarray * naive_jacobian).sum(dim = ["theta", "phi"]) * dtheta_physical;
		denominator = jacobian_integrated_over_theta_and_phi;

	return numerator / denominator;

def radial_average_1D(quantity_xarray, jacobian_xr_dictionary):
	# NB: quantity_xarray should be already flux-surface averaged.
	naive_jacobian = jacobian_xr_dictionary["naive"]
	# Cast the Jacobian in 'r' only.
	radial_weight = naive_jacobian.sum(dim = "theta");
	numerator = (quantity_xarray * radial_weight).sum(dim = "r");
	denominator = radial_weight.sum(dim = "r");
	return numerator / denominator;

def radial_average_2D(quantity_xarray, jacobian_xr_dictionary):
	# See flux-surface average methods.
	naive_jacobian = jacobian_xr_dictionary["naive"];
	numerator = (quantity_xarray * naive_jacobian).sum(dim = "r");
	denominator = naive_jacobian.sum(dim = "r");
	return numerator / denominator;

def radial_average_3D(quantity_xarray, jacobian_xr_dictionary, use_integrated_jacobian = False):
	# See above.
	naive_jacobian = jacobian_xr_dictionary["naive"];
	numerator = (quantity_xarray * naive_jacobian).sum(dim = ["r", "phi"]);
	denominator = naive_jacobian.sum(dim = ["r", "phi"]);
	return numerator / denominator;