# Imports.
import numpy as np;
import xarray as xr;
from scipy.fft import fft, fftfreq

# -------------------------------------------------------------------
# --------------------------Parameters. -----------------------------
# -------------------------------------------------------------------

# The variables below are nominally private - not to be altered during run-time!
# Sourced from GAM_analytical.py.
private_minor_radius_gys = 160;
private_rhostar_gys = 1./float(private_minor_radius_gys);
private_aspect_ratio_gys = 0.5;
private_normalisation_coeff_gys = private_aspect_ratio_gys/(private_rhostar_gys * np.sqrt(2.));


# -------------------------------------------------------------------
# -------- Radial propagation/PSD & FFT helper functions. -----------
# -------------------------------------------------------------------

def generate_poloidally_averaged_time_series(phirth_list):

	# Poloidal averaging, equivalent in function to flux-surface averaging. This isolates the m = 0 zonal component.
	# Intuitively speaking, this also 'truncates' the circular geometry into one-dimensional radial strips.
	radial_strips = [phirth_xarray.mean(dim = "theta") for phirth_xarray in phirth_list];

	# The following produces a two-dimensional x-array of shape (time, radial coordinate).
	hovmoller_matrix = xr.concat(radial_strips, dim = "time");
	return hovmoller_matrix;

def map_power_spectrum(hovmoller_matrix, radial_index, time_step):
	# Slice at radial index to isolate a strong signal.
	signal = hovmoller_matrix.sel(r = radial_index);
	signal_steps = len(signal);

	# Isolate the GAM signal from the stationary ZF.
	# Apply Hanning window to prevent spectral leakage.
	signal = (signal - np.mean(signal)) * np.hanning(signal_steps);

	# Fourier transform from time-domain to frequency-domain.
	signal_fourier = np.array(fft(signal));
	power_spectrum_density = np.abs(signal_fourier) ** 2;
	
	# Generate actual frequency data. TODO: what's going on here?
	frequencies = fftfreq(signal_steps, time_step.flatten()[0]);

	# Preserve positive frequencies. TODO: why?
	mask = frequencies > 0;
	return frequencies[mask], power_spectrum_density[mask];

def convert_to_real_time(time_step):
	# TODO:

# -------------------------------------------------------------------
# ------------------- Mesh grid generation. -------------------------
# -------------------------------------------------------------------

def convert_to_cartesian(r, theta):
	# Standard convention.
	x = r * np.cos(theta);
	y = r * np.sin(theta);
	return x, y;

def normalise_theta(phi2D_dataset):
	
	return np.linspace(0, 2 * np.pi, phi2D_dataset.dims["theta"]);

def normalise_radius(phi2D_dataset, minor_radius = 160):

	return np.linspace(0, minor_radius, phi2D_dataset.dims["r"]);

def generate_xy_grid(phi2D_dataset):
	
	theta_coords_naive = normalise_theta(phi2D_dataset);
	r_coords_naive = normalise_radius(phi2D_dataset);
	theta_coords, r_coords = np.meshgrid(theta_coords_naive, r_coords_naive, indexing="ij");
	x = r_coords * np.cos(theta_coords);
	y = r_coords * np.sin(theta_coords);
	return x, y;