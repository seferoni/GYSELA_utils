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
	return radial_time_series[:, radial_index].values;

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

# TODO: don't forget the radial averages
def radial_average_2D(quantity_xarray, jacobian_xr_dictionary, use_integrated_jacobian = False):
	# See flux-surface average methods.
	n_r = quantity_xarray.sizes["r"];
	naive_jacobian = jacobian_xr_dictionary["naive"];
	jacobian_integrated_over_r = jacobian_xr_dictionary["integrated_over_r"];
	dr_physical = 1 / n_r;

	numerator = (quantity_xarray * naive_jacobian).sum(dim = "r");
	denominator = naive_jacobian.sum(dim = "r");

	if use_integrated_jacobian:

		numerator = (quantity_xarray * naive_jacobian).sum(dim = "r") * dr_physical;
		denominator = jacobian_integrated_over_r;

	return numerator / denominator;

def radial_average_3D(quantity_xarray, jacobian_xr_dictionary, use_integrated_jacobian = False):
	# See above.
	n_r = quantity_xarray.sizes["r"];
	naive_jacobian = jacobian_xr_dictionary["naive"];
	jacobian_integrated_over_r_and_phi = jacobian_xr_dictionary["integrated_over_r_and_phi"];
	dr_physical = 1 / n_r;

	numerator = (quantity_xarray * naive_jacobian).sum(dim = ["r", "phi"]);
	denominator = naive_jacobian.sum(dim = ["r", "phi"]);

	if use_integrated_jacobian:

		numerator = (quantity_xarray * naive_jacobian).sum(dim = ["r", "phi"]) * dr_physical;
		denominator = jacobian_integrated_over_r_and_phi;

	return numerator / denominator;