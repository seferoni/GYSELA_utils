# Imports.
import numpy as np;
import xarray as xr;
import pandas as pd;
import gysela_utilities as gys_utils;
import h5_reader_xr as reader;
import os;
import glob;
from scipy import signal;
from scipy import stats;
from scipy.interpolate import interp1d;
from scipy.fft import fft, fftfreq;

# -------------------------------------------------------------------
# --------------------------Parameters. -----------------------------
# -------------------------------------------------------------------

# The variables below are nominally private - not to be altered during run-time!
# Sourced from GAM_analytical.py.

physical_constants = {
	"electron_volt" : 1.602176634e-19, # In Joules.
	"proton_mass" : 1.67262192369e-27,
};

geometry = {
	"minor_radius" : 0.13,
	"major_radius" : 1.3,
	"minor_radius_gys" : 160,
	"aspect_ratio_gys" : 0.5,
};

simulation_parameters_raw = {
	"ion_temperature" : 1,
	"electron_temperature" : 1,
};

simulation_parameters = {
	"ion_temperature_joules" : simulation_parameters_raw["ion_temperature"] * 1000. * physical_constants["electron_volt"],
	"electron_temperature_joules" : simulation_parameters_raw["electron_temperature"] * 1000. * physical_constants["electron_volt"],
	"ion_mass" : 2.0 * physical_constants["proton_mass"], # Presuming deuterium.
	"rhostar_gys" : 1. / float(geometry["minor_radius_gys"]),
};

normalisation_parameters = {
	"thermal_velocity" : np.sqrt(simulation_parameters["ion_temperature_joules"] / simulation_parameters["ion_mass"]),
	"normalisation_coeff_gys" : geometry["aspect_ratio_gys"] / (simulation_parameters["rhostar_gys"] * np.sqrt(2.))
};

convenience_parameters = {
	"GAM_cutoff_frequencies_template" : [0.0005, 0.0025]
};

# -------------------------------------------------------------------
# -------- Radial propagation/PSD & FFT helper functions. -----------
# -------------------------------------------------------------------

def calculate_residual_level(damping_envelope, residual_window = 100, search_start_index = 100, use_heuristic_approach = False):

	if use_heuristic_approach:
		return np.mean(damping_envelope[-residual_window:]);

	# Get time-index corresponding to first minimum, which should mark the end of the physical signal.
	end_index = np.argmin(damping_envelope[search_start_index :]);

	if (residual_window > end_index):
		print(f"Error: Residual window value {residual_window} is greater than the number of indices before the first minima occurs {end_index}.");
		return None;

	start_index = end_index - residual_window;
	residual_level = np.median(damping_envelope[start_index : end_index]);
	return residual_level;

def convert_to_real_frequency(frequency_term):

	dimensionless_normalisation_coeff = normalisation_parameters["normalisation_coeff_gys"];
	real_normalisation_coeff = normalisation_parameters["thermal_velocity"] / geometry["major_radius"];
	return frequency_term * dimensionless_normalisation_coeff * real_normalisation_coeff;

def extract_gam_frequency(phi2D_list, dt_diag, jacobian_dictionary, effective_radius = 0.7, real_frequency = False):

	time_series = generate_poloidally_averaged_time_series(phi2D_list, jacobian_dictionary, effective_radius);
	frequencies, power_spectrum_density = map_power_spectrum(time_series, dt_diag);
	frequencies = convert_to_real_frequency(frequencies) if real_frequency else frequencies;
	GAM_peak_index = isolate_GAM_peak_index(power_spectrum_density, frequencies);
	# We assume here that the peak corresponding to the GAM is the most prominent peak within the power spectrum.
	# This assumption holds valid provided we have omitted the ZFZF peak!
	# This gets a little fishy when we're analysing a spectrum with a low SNR... need robust, sometimes aggressive frequency cut-off/masking.
	GAM_frequency = frequencies[GAM_peak_index];
	return GAM_frequency;

def extract_gam_growth_rate(phi2D_list, dt_diag, jacobian_dictionary, frequency, effective_radius = 0.7, residual_window = 100, noise_threshold = 0.05):

	time_series = generate_poloidally_averaged_time_series(phi2D_list, jacobian_dictionary, effective_radius);

	envelope = generate_damping_envelope(time_series, frequency, dt_diag);
	# Scale up to GYSELA time-steps, which matters strictly for the output value of the growth rate.
	time_range = gys_utils.generate_time_range_by_series(time_series, dt_diag);

	# The residual level (should) behave as a static vertical offset. 
	residual_level = calculate_residual_level(envelope, residual_window);
	# By subtracting it from the envelope, we can isolate the pure decay signal.
	pure_decay_signal = envelope - residual_level;
	# Take only positive signal values prior to the tail of the signal to ensure well-behaved logarithmic fitting.
	mask = pure_decay_signal > (noise_threshold * np.max(pure_decay_signal));
	# This signal was originally converted to real frequency units (Hz). Here, we keep code units.
	log_signal = np.log(pure_decay_signal[mask]);

	# Polyfit returns the slope and intercept as its first and second return values, respectively.
	growth_rate, _ = np.polyfit(time_range, log_signal, 1);
	return growth_rate;

def extract_gam_growth_rate_filtered(phi2D_list, dt_diag, jacobian_dictionary, frequency, effective_radius = 0.7, cutoff_frequencies = [0.0005, 0.0025]):

	time_series = generate_poloidally_averaged_time_series(phi2D_list, jacobian_dictionary, effective_radius);
	filtered_signal = butterworth_band_pass_filter(time_series, dt_diag, cutoff_frequencies[0], cutoff_frequencies[1]);

	envelope = generate_damping_envelope(filtered_signal, frequency, dt_diag);
	# Scale up to GYSELA code units, which matters strictly for the output value of the growth rate.
	time_range = gys_utils.generate_time_range_by_series(time_series, dt_diag);

	# Mitigate cases where the band-pass produces an envelope that dips below the zero-line.
	# This should not generally be possible but is kept as a safeguard.
	log_signal = np.log(envelope[envelope > 0]);
	time_range = time_range[envelope > 0];

	# Polyfit returns the slope and intercept as its first and second return values, respectively.
	growth_rate, _ = np.polyfit(time_range, log_signal, 1);
	return growth_rate;

def map_power_spectrum(time_series, dt_diag, padding_factor = 5):
	# NB: this returns f_GAM, not omega_GAM.
	signal_steps = len(time_series);

	# Isolate the GAM signal from the stationary ZF.
	# Apply Hanning window to mitigate spectral leakage.
	signal = (time_series - np.mean(time_series)) * np.hanning(signal_steps);

	# Fourier transform from time-domain to frequency-domain.
	# Pad signal with 0s to improve resolution. This can exacerbate the appearance of spectral leakage artefacts.
	padded_signal_steps = signal_steps * padding_factor;
	signal_fourier = np.array(fft(signal, n = padded_signal_steps));
	power_spectrum_density = np.abs(signal_fourier) ** 2;
	
	# Generate actual frequency data.
	frequencies = fftfreq(padded_signal_steps, dt_diag);

	# Preserve positive frequencies.
	mask = frequencies > 0;
	return frequencies[mask], power_spectrum_density[mask];

def generate_damping_envelope(time_series, frequency, dt_diag):

	# The GAM period is first converted into diagonostic time-steps (corresponding strictly to indices)...
	# and then halved for the peak-to-peak distance. We remain in index-space always, not time-steps.
	minimum_distance = 0.5 * (1 / frequency) * (1 / dt_diag);
	peak_indices, _ = signal.find_peaks(time_series, distance = minimum_distance, prominence = np.max(time_series) * 0.01);
	peaks = time_series[peak_indices];
	# This is so-called 'virtual' because it corresponds to the diagnostic time-scale (by which Phi2D files are sampled).
	# Interpolation is agnostic as to whether we cast our time series in actual simulation time-steps or otherwise.
	virtual_peak_times = np.arange(len(time_series));
	envelope = interp1d(peak_indices, peaks, kind = "linear", bounds_error = False, fill_value = (peaks[0], peaks[-1]))(virtual_peak_times);
	return envelope;

def isolate_GAM_peak_index(power_spectrum_density, frequency_array, cutoff = 0.0005):

	frequency_mask = frequency_array > cutoff;
	# Vacates the indexed value when the frequency is below the cutoff, effectively ignoring low frequency (ZFZF) peaks.
	high_frequency_psd = np.where(frequency_mask, power_spectrum_density, 0);
	# This may need a little fine-tuning, prominence-wise, depending on the intensity of turbulence in the system.
	peak_indices, _ = signal.find_peaks(high_frequency_psd, prominence = high_frequency_psd.max() * 0.2);

	if len(peak_indices) == 0:

		print(f"No peaks detected above the designated cutoff: {cutoff}.");
		return None;

	peaks = high_frequency_psd[peak_indices];
	GAM_peak_index = peak_indices[np.argmax(peaks)];
	return GAM_peak_index;

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
	theta_coords, r_coords = np.meshgrid(theta_coords_naive, r_coords_naive, indexing = "ij");
	x = r_coords * np.cos(theta_coords);
	y = r_coords * np.sin(theta_coords);
	return x, y;

# -------------------------------------------------------------------
# ------------------- Batch/parameter scan logic. -------------------
# -------------------------------------------------------------------

def parameter_scan_analysis_phi2D(base_directory, folder_prefix, effective_radius, cutoff_frequencies = None):

	# `folder_prefix` should be of the form "DN_*_*_[parameter value]" (DN is the standard GYSELA format, not necessarily invoked here).
	search_pattern = os.path.join(base_directory, f"{folder_prefix}_*");
	# Match search pattern, return list in ascending order.
	matching_directories = sorted(glob.glob(search_pattern));

	if not matching_directories:

		print(f"No directories found matching pattern: {search_pattern}");
		return;
	
	# Wrap in pandas dataframe later.
	results = [];

	for directory in matching_directories:

		folder_basename = os.path.basename(directory);
		# Split the folder name, taking the last entry as that corresponding to the parameter value.
		parameter_value_string = folder_basename.split("_")[-1];
		parameter_value = float(parameter_value_string);
		print(f"Processing {folder_basename} with parameter value: {parameter_value}");
	
		# Load phi2D data.
		perturbed_phi2D_list = reader.fetch_phi2D_data(directory, parallelise = True);
		jacobian_dictionary = reader.fetch_jacobian(directory);
		dt_diag = reader.fetch_dt_diag(directory);
	
		# Process Phi2D data. We preserve GYSELA's normalisation convention (to the ion cyclotron frequency).
		gam_frequency = extract_gam_frequency(perturbed_phi2D_list, dt_diag, jacobian_dictionary, effective_radius);
		
		if cutoff_frequencies is not None:
			gam_growth_rate = extract_gam_growth_rate_filtered(perturbed_phi2D_list, dt_diag, gam_frequency, effective_radius, cutoff_frequencies);
		else:
			gam_growth_rate = extract_gam_growth_rate(perturbed_phi2D_list, dt_diag, effective_radius, gam_frequency);
	
		# Store results as a table.
		results.append({
			"parameter_value": parameter_value,
			"gam_frequency": gam_frequency,
			"gam_growth_rate": gam_growth_rate,
			"folder_name": folder_basename
		});

	dataframe_results = pd.DataFrame(results).sort_values(by = "parameter_value");
	return dataframe_results;

# -------------------------------------------------------------------
# ------------------- Auxiliary methods. ----------------------------
# -------------------------------------------------------------------

def butterworth_band_pass_filter(time_series, dt_diag, low_cutoff = 0.0005, high_cutoff = 0.0025):

	# Determine sampling rate and Nyquist frequency in normalised units.
	# Note that cutoff frequencies also therefore become normalised...
	sampling_rate = 1 / dt_diag;
	nyquist_frequency = 0.5 * sampling_rate;
	normalised_cutoff_frequencies = [low_cutoff / nyquist_frequency, high_cutoff / nyquist_frequency];

	# Denominator and numerator of the impulse response filter, respectively.
	# We choose here a fourth order band-pass filter.
	b, a = signal.butter(N = 4, Wn = normalised_cutoff_frequencies, btype = "band");
	filtered_signal = signal.filtfilt(b, a, time_series);
	return filtered_signal;

def extract_fourier_modes(phi2D_list, modes_list):

	time_series = xr.concat(phi2D_list, dim = "time");
	n_theta = len(time_series.theta);
	n_phi = len(time_series.phi);
	# For a theta transform, we normalise by 1/n_theta. For a phi transform, we similarly normalise by 1/n_phi.
	# When transforming in 2D, we normalise by the product of both mesh lengths.
	mesh_normalisation = n_theta * n_phi;

	amplitudes = {};
	fourier_sum = np.fft.fft2(time_series.values) / mesh_normalisation;

	for (m, n) in modes_list:

		amplitudes[(m, n)] = np.abs(fourier_sum[:, m, n]);

	return amplitudes;

def find_gam_effective_radius_simple(phi2D_list, jacobian_dictionary, quiescent_phi2D_list = None, skip_initial_entries = 0.1, valid_bounds = [0.1, 0.9]):

	fs_average_time_series = generate_poloidally_averaged_time_series(phi2D_list, jacobian_dictionary);

	if quiescent_phi2D_list is not None:
		fs_average_time_series_quiescent = generate_poloidally_averaged_time_series(quiescent_phi2D_list, jacobian_dictionary);
		fs_average_time_series = fs_average_time_series - fs_average_time_series_quiescent;
	
	# Drop initial transient.
	entries_skipped = int(skip_initial_entries * fs_average_time_series.sizes["time"]);
	fs_average_time_series = fs_average_time_series.isel(time = slice(entries_skipped, None));

	# Isolate oscillatory signal.
	oscillatory_signal = fs_average_time_series - fs_average_time_series.mean(dim = "time");
	root_mean_square_at_all_r = np.sqrt((oscillatory_signal ** 2).mean(dim = "time"));

	radial_coordinates = root_mean_square_at_all_r["r"].values;
	r_min, r_max = radial_coordinates.min(), radial_coordinates.max();
	r_span = r_max - r_min;
	floor, ceiling = r_min + (valid_bounds[0] * r_span), r_min + (valid_bounds[1] * r_span);
	root_mean_square_at_all_r = root_mean_square_at_all_r.assign_coords(r = radial_coordinates);
	root_mean_square_at_all_r = root_mean_square_at_all_r.sel(r = slice(floor, ceiling));
	print(root_mean_square_at_all_r)
	# NB: this presumes that rhomin = 0, rhomax = 1. Be careful!
	return root_mean_square_at_all_r.idxmax().values / r_max;

def isolate_m1_component(phi2D_xarray):
	# Note that this method is only applicable in circular geometry!
	theta = np.linspace(0, 2 * np.pi, len(phi2D_xarray.theta));
	
	# Take note that the m = 1 can be isolated by projecting phi unto sin(theta).
	# This is permitted due to Fourier decomposition & orthogonality properties.
	# Exactly commensurate with what we do analytically re decomposition into poloidal harmonics.
	# Should note that this gets a bit dicey for shaped equilibria, because coupling is no longer strictly sin(theta)-based!
	phi_m1 = (phi2D_xarray * np.sin(theta)[:, None]).mean(dim = "theta");
	return phi_m1;

def generate_poloidally_averaged_time_series(phi2D_list, jacobian_dictionary = None, effective_radius = None, m1 = False):

	operation = lambda entry : gys_utils.flux_surface_average_2D(entry, jacobian_dictionary) if not m1 else isolate_m1_component(entry);
	radial_strips = [operation(phi2D_xarray) for phi2D_xarray in phi2D_list];

	# The following produces a two-dimensional x-array of shape (time, radial coordinate).
	time_series = xr.concat(radial_strips, dim = "time");

	if not effective_radius is None:
		time_series = gys_utils.slice_at_effective_radius(time_series, effective_radius);

	return time_series;

def generate_turbulent_variance_time_series(phi2D_list, jacobian_dictionary = None, effective_radius = None):

	# Cull zonal component to extract turbulence intensity.
	operation = lambda entry: ((entry - gys_utils.flux_surface_average_2D(entry, jacobian_dictionary)) ** 2).mean(dim="theta");
	radial_strips = [operation(phi2D_xarray) for phi2D_xarray in phi2D_list];
	variance_series = xr.concat(radial_strips, dim = "time");

	if not effective_radius is None:
		variance_series = gys_utils.slice_at_effective_radius(variance_series, effective_radius);

	return variance_series;

def generate_zonal_variance_time_series(phi2D_list, jacobian_dictionary = None, effective_radius = None):

	# Take a simple poloidal average and square to isolate zonal mode intensities.
	operation = lambda entry: gys_utils.flux_surface_average_2D(entry, jacobian_dictionary) ** 2;
	radial_strips = [operation(phi2D_xarray) for phi2D_xarray in phi2D_list];
	zonal_series = xr.concat(radial_strips, dim = "time");

	if not effective_radius is None:
		zonal_series = gys_utils.slice_at_effective_radius(zonal_series, effective_radius);

	return zonal_series;

def generate_phi_dictionary(phi2D_dataset, jacobian_dictionary):

	phi_FS_avg = gys_utils.flux_surface_average_2D(phi2D_dataset["Phirth"], jacobian_dictionary);
	phi_rth_minus_phi_FS_avg = phi2D_dataset["Phirth"] - phi_FS_avg;
	phi_rth_minus_phi_n0 = phi2D_dataset["Phirth"] - phi2D_dataset["Phirth_n0"];
	return {
		"broadband": {"data": phi2D_dataset["Phirth"], "title": r"Total Potential ($\Phi$)"},
		"zonal": {"data": phi2D_dataset["Phirth_n0"], "title": r"Zonal Potential ($\Phi_{n=0}$)"},
		"non-zonal": {"data": phi_rth_minus_phi_FS_avg, "title": r"Non-zonal Potential ($\Phi - \Phi_{00}$)"},
		"turbulence": {"data": phi_rth_minus_phi_n0, "title": r"Turbulence Potential ($\Phi - \Phi_{n=0}$)"}
	};
