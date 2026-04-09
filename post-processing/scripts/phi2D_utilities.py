# Imports.
import numpy as np;
import xarray as xr;
import pandas as pd;
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
		return np.mean(damping_envelope[-100:]);

	# Get time-index corresponding to first minimum, which should mark the end of the physical signal.
	end_index = np.argmin(damping_envelope[search_start_index :]);

	if (residual_window > end_index):
		print(f"Error: Residual window value {residual_window} is greater than the number of indices before the first minima occurs {end_index}.");
		return None;

	start_index = end_index - residual_window;
	residual_level = np.median(damping_envelope[start_index : end_index]);
	return residual_level;

def calculate_stride(delta_t, dt_diag):

	# The logic is this: for a dt_diag of 50, and a delta_t of 25, we have a stride of 2.
	# Stride is also the diagnostic interval; for every two simulation time-steps (50 code units), we have one Phi2D sample.
	# This still retains the normalisation interred within GYSELA itself.
	return dt_diag / delta_t;

def convert_to_real_frequency(frequency_term):

	dimensionless_normalisation_coeff = normalisation_parameters["normalisation_coeff_gys"];
	real_normalisation_coeff = normalisation_parameters["thermal_velocity"] / geometry["major_radius"];
	return frequency_term * dimensionless_normalisation_coeff * real_normalisation_coeff;

def extract_gam_frequency(phi2D_list, delta_t, effective_radius = 0.7, real_frequency = False):

	radial_time_series = generate_poloidally_averaged_time_series(phi2D_list, effective_radius);
	frequencies, power_spectrum_density = map_power_spectrum(radial_time_series, delta_t);
	frequencies = convert_to_real_frequency(frequencies) if real_frequency else frequencies;
	GAM_peak_index = isolate_GAM_peak_index(power_spectrum_density, frequencies);
	# We assume here that the peak corresponding to the GAM is the most prominent peak within the power spectrum.
	# This assumption holds valid provided we have omitted the ZFZF peak!
	# This gets a little fishy when we're analysing a spectrum with a low SNR... need robust, sometimes aggressive frequency cut-off/masking.
	GAM_frequency = frequencies[GAM_peak_index];
	return GAM_frequency;

def extract_gam_growth_rate(phi2D_list, delta_t, dt_diag, frequency, effective_radius = 0.7, residual_window = 100, noise_threshold = 0.05):

	radially_localised_time_series = generate_poloidally_averaged_time_series(phi2D_list, effective_radius);
	stride = calculate_stride(delta_t, dt_diag);

	envelope = generate_damping_envelope(radially_localised_time_series, frequency, dt_diag);
	# Scale up to GYSELA time-steps, which matters strictly for the output value of the growth rate.
	time_range = np.arange(len(radially_localised_time_series)) * stride;

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

def extract_gam_growth_rate_filtered(phi2D_list, delta_t, dt_diag, frequency, effective_radius = 0.7, cutoff_frequencies = [0.0005, 0.0025]):

	radially_localised_time_series = generate_poloidally_averaged_time_series(phi2D_list, effective_radius);
	filtered_signal = butterworth_band_pass_filter(radially_localised_time_series, dt_diag, cutoff_frequencies[0], cutoff_frequencies[1]);
	stride = calculate_stride(delta_t, dt_diag);

	envelope = generate_damping_envelope(filtered_signal, frequency, dt_diag);
	# Scale up to GYSELA time-steps, which matters strictly for the output value of the growth rate.
	time_range = np.arange(len(filtered_signal)) * stride;

	# Mitigate cases where the band-pass produces an envelope that dips below the zero-line.
	# This should not generally be possible but is kept as a safeguard.
	log_signal = np.log(envelope[envelope > 0]);
	time_range = time_range[envelope > 0];

	# Polyfit returns the slope and intercept as its first and second return values, respectively.
	growth_rate, _ = np.polyfit(time_range, log_signal, 1);
	return growth_rate;

def map_power_spectrum(radial_time_series, dt_diag, padding_factor = 5):

	signal_steps = len(radial_time_series);

	# Isolate the GAM signal from the stationary ZF.
	# Apply Hanning window to mitigate spectral leakage.
	signal = (radial_time_series - np.mean(radial_time_series)) * np.hanning(signal_steps);

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

def generate_damping_envelope(radial_time_series, frequency, dt_diag):

	# The GAM period is first converted into diagonostic time-steps (corresponding strictly to indices)...
	# and then halved for the peak-to-peak distance. We remain in index-space always, not time-steps.
	minimum_distance = 0.5 * (1 / frequency) * (1 / dt_diag);
	peak_indices, _ = signal.find_peaks(radial_time_series, distance = minimum_distance, prominence = np.max(radial_time_series) * 0.01);
	peaks = radial_time_series[peak_indices];
	# This is so-called 'virtual' because it corresponds to the diagnostic time-scale (by which Phi2D files are sampled).
	# Interpolation is agnostic as to whether we cast our time series in actual simulation time-steps or otherwise.
	virtual_peak_times = np.arange(len(radial_time_series));
	envelope = interp1d(peak_indices, peaks, kind = "linear", bounds_error = False, fill_value = (peaks[0], peaks[-1]))(virtual_peak_times);
	return envelope;

def generate_time_range_by_series(radial_time_series, dt_diag):

	naive_range = np.arange(len(radial_time_series));
	return naive_range * dt_diag;

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

def slice_at_effective_radius(radial_time_series, effective_radius = 0.7):

	total_radial_size = radial_time_series.sizes["r"] - 1;
	radial_index = round(effective_radius * total_radial_size);
	return radial_time_series[:, radial_index].values;

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

# -------------------------------------------------------------------
# ------------------- Batch/parameter scan logic. -------------------
# -------------------------------------------------------------------

def parameter_scan_analysis_phi2D(base_directory, folder_prefix, dt_diag, effective_radius, cutoff_frequencies = None):
	# TODO: this is inefficient
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
		phi2D_list = reader.fetch_phi2D_data(directory);
		delta_t = reader.fetch_delta_t(directory);
	
		# Process Phi2D data. We preserve GYSELA's normalisation convention (to the ion cyclotron frequency).
		gam_frequency = extract_gam_frequency(phi2D_list, delta_t, effective_radius);
		
		if cutoff_frequencies is not None:
			gam_growth_rate = extract_gam_growth_rate_filtered(phi2D_list, delta_t, dt_diag, gam_frequency, effective_radius, cutoff_frequencies);
		else:
			gam_growth_rate = extract_gam_growth_rate(phi2D_list, delta_t, dt_diag, effective_radius, gam_frequency);
	
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

def isolate_m1_component(phi2D_xarray):

	theta = np.linspace(0, 2 * np.pi, len(phi2D_xarray.theta));
	
	# Take note that the m = 1 can be isolated by projecting phi unto sin(theta).
	# This is permitted due to Fourier decomposition & orthogonality properties.
	# Exactly commensurate with what we do analytically re decomposition into poloidal harmonics.
	# Should note that this gets a bit dicey for shaped equilibria, because coupling is no longer strictly sin(theta)-based!
	phi_m1 = (phi2D_xarray * np.sin(theta)[:, None]).mean(dim = "theta");
	return phi_m1;

def generate_poloidally_averaged_time_series(phi2D_list, effective_radius = None, m1 = False):

	# Poloidal averaging, equivalent in function to flux-surface averaging. This isolates the m = 0 zonal component.
	# Intuitively speaking, this also 'folds' the circular geometry into one-dimensional radial strips.
	operation = lambda entry : entry.mean(dim = "theta") if not m1 else isolate_m1_component(entry);
	radial_strips = [operation(phi2D_xarray) for phi2D_xarray in phi2D_list];

	# The following produces a two-dimensional x-array of shape (time, radial coordinate).
	time_series = xr.concat(radial_strips, dim = "time");

	if not effective_radius is None:
		time_series = slice_at_effective_radius(time_series, effective_radius);

	return time_series;

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