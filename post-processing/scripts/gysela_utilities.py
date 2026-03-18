# Imports.
import numpy as np;
import xarray as xr;
import pandas as pd;
import h5_reader_xr as reader;
import os;
import glob;
from scipy import signal;
from scipy.interpolate import interp1d;
from scipy.fft import fft, fftfreq;

# -------------------------------------------------------------------
# --------------------------Parameters. -----------------------------
# -------------------------------------------------------------------

# The variables below are nominally private - not to be altered during run-time!
# Sourced from GAM_analytical.py. Veracity is... dubious. Should double-check at some point...

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
	# TODO: using these normalisation parameters, we get GAM frequencies an order of magnitude smaller than we should. Bad.
	"thermal_velocity" : np.sqrt(simulation_parameters["ion_temperature_joules"] / simulation_parameters["ion_mass"]),
	"normalisation_coeff_gys" : geometry["aspect_ratio_gys"] / (simulation_parameters["rhostar_gys"] * np.sqrt(2.))
};

# -------------------------------------------------------------------
# -------- Radial propagation/PSD & FFT helper functions. -----------
# -------------------------------------------------------------------

def calculate_sampling_frequency(output_stride = 2, time_step = 25):

	# The logic is this: we have 1 Phi2D file for every two time-steps (GSTEPS).
	# So the diagnostic interval is two time-steps.
	# `time_step` is simply delta_t. This can be read off from the simulation input file or from the output Phi2D files.
	# This still retains the normalisation interred within GYSELA itself.
	diagnostic_time_step = time_step * output_stride;
	return 1 / diagnostic_time_step;

def extract_gam_frequency(phi2D_list, time_step, radial_index, convert_to_real_frequency = False):

	radial_time_series = generate_poloidally_averaged_time_series(phi2D_list);
	frequencies, power_spectrum_density = map_power_spectrum(radial_time_series, radial_index, time_step);
	frequencies = convert_to_real_frequency(frequencies) if convert_to_real_frequency else frequencies;
	GAM_peak_index = isolate_GAM_peak_index(power_spectrum_density, frequencies);
	# We assume here that the peak corresponding to the GAM is the most prominent peak within the power spectrum.
	# This assumption holds valid provided we have omitted the ZFZF peak!
	# This gets a little fishy when we're analysing a spectrum with a low SNR... need robust, sometimes aggressive frequency cut-off/masking.
	GAM_frequency = frequencies[GAM_peak_index];
	return GAM_frequency;

def extract_gam_growth_rate(phi2D_list, time_step, radial_index, noise_threshold = 0.05, output_stride = 2):

	radially_localised_time_series = generate_poloidally_averaged_time_series(phi2D_list)[:, radial_index].values;

	# Eventually we may need to modify this method's signature to accommodate different sampling frequencies.
	sampling_frequency = calculate_sampling_frequency(output_stride, time_step);
	time_range = np.arange(len(radially_localised_time_series)) / sampling_frequency;
	envelope, residual_level = generate_residual_envelope(radially_localised_time_series);

	# The residual level (should) behave as a static vertical offset. 
	# By subtracting it from the envelope, we can isolate the pure decay signal.
	pure_decay_signal = envelope - residual_level;
	# Take only positive signal values prior to the tail of the signal to ensure well-behaved logarithmic fitting.
	mask = pure_decay_signal > (noise_threshold * np.max(pure_decay_signal));
	# This signal was originally converted to real frequency units (Hz). Here, we keep code units.
	log_signal = np.log(pure_decay_signal[mask]);
	time_range_masked = time_range[mask];

	# Fit a line to the logarithm of the envelope to extract the growth rate.
	growth_rate, _ = np.polyfit(time_range_masked, log_signal, 1);
	return growth_rate;

def map_power_spectrum(time_series, radial_index, time_step, padding_factor = 5):

	# Slice at radial index to isolate a strong signal.
	signal = time_series.sel(r = radial_index);
	signal_steps = len(signal);

	# Isolate the GAM signal from the stationary ZF.
	# Apply Hanning window to mitigate spectral leakage.
	signal = (signal - np.mean(signal)) * np.hanning(signal_steps);

	# Fourier transform from time-domain to frequency-domain.
	# ...and pad signal with 0s to improve resolution. This CAN exacerbate the appearance of spectral leakage artefacts!
	# Sucks for you if your signal is already highly corrugated, as in very turbulent regimes...
	padded_signal_steps = signal_steps * padding_factor;
	signal_fourier = np.array(fft(signal, n = padded_signal_steps));
	power_spectrum_density = np.abs(signal_fourier) ** 2;
	
	# Generate actual frequency data.
	frequencies = fftfreq(padded_signal_steps, time_step);

	# Preserve positive frequencies.
	mask = frequencies > 0;
	return frequencies[mask], power_spectrum_density[mask];

def convert_to_real_frequency(frequency_term):
	# TODO: see comment above on normalisation_parameters.
	dimensionless_normalisation_coeff = normalisation_parameters["normalisation_coeff_gys"];
	real_normalisation_coeff = normalisation_parameters["thermal_velocity"] / geometry["major_radius"];
	return frequency_term * dimensionless_normalisation_coeff * real_normalisation_coeff;

def generate_residual_envelope(radial_time_series, residual_window = 100, minimum_peak_distance = 20):

	# Isolate a given number of entries in the time series as the residual. Arbitrary.
	residual_level = np.mean(radial_time_series[-residual_window:]);
	
	# Isolate peaks.
	# The minimum distance between peaks here should actually be rigorously calculated using the sampling frequency.
	# But in practice, we can post-hoc validate, with some ease, that this value works via the RH diagnostic.
	# TODO: we must fix this at some point...
	peak_indices, _ = signal.find_peaks(radial_time_series, distance = minimum_peak_distance);

	# Nonetheless, we can add a simple sanity check to make sure our lazy approach is still sensible...
	if (len(peak_indices) < 5):

		print(f"Only {len(peak_indices)} were found. You may wish to change the 'minimum_peak_distance' parameter.");

	peaks = radial_time_series[peak_indices];
	peak_times = np.arange(len(radial_time_series));
	envelope = interp1d(peak_indices, peaks, kind = "linear", bounds_error = False, fill_value = (peaks[0], peaks[-1]))(peak_times);
	return envelope, residual_level;

def isolate_GAM_peak_index(power_spectrum_density, frequency_array, cutoff = 1000):

	frequency_mask = frequency_array > cutoff;
	# Vacates the indexed value when the frequency is below the cutoff, effectively ignoring low frequency (ZFZF) peaks.
	high_frequency_psd = np.where(frequency_mask, power_spectrum_density, 0);
	# This may need a little fine-tuning, prominence-wise, depending on the intensity of turbulence in the system.
	peak_indices, _ = signal.find_peaks(high_frequency_psd, prominence = high_frequency_psd.max() * 0.2);

	if not peak_indices:

		print(f"No peaks detected above the designated cutoff: {cutoff} Hz.");
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
	theta_coords, r_coords = np.meshgrid(theta_coords_naive, r_coords_naive, indexing="ij");
	x = r_coords * np.cos(theta_coords);
	y = r_coords * np.sin(theta_coords);
	return x, y;

# -------------------------------------------------------------------
# ------------------- Batch/parameter scan logic. -------------------
# -------------------------------------------------------------------

def parameter_scan_analysis_phi2D(base_directory, folder_prefix, radial_index, signal_high_pass = False):

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
		phi2D_list = reader.compile_data_from_directory("Phirth_n0", f"{directory}/sp0/Phi2D");
		time_step = reader.fetch_data_from_h5(f"{directory}/sp0/Phi2D/Phi2D_d00000.h5")["deltat"].values;
	
		# Process Phi2D data. We preserve GYSELA's normalisation convention (to the ion cyclotron frequency).
		gam_frequency = extract_gam_frequency(phi2D_list, time_step, radial_index);
		gam_growth_rate = extract_gam_growth_rate(phi2D_list, time_step, radial_index);
	
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

def isolate_m1_component(phirth_xarray):

	theta = np.linspace(0, 2 * np.pi, len(phirth_xarray.theta));
	
	# Take note that the m = 1 can be isolated by projecting phi unto sin(theta).
	# This is permitted due to Fourier decomposition & orthogonality properties.
	# Exactly commensurate with what we do analytically re decomposition into poloidal harmonics.
	# Should note that this gets a bit dicey for shaped equilibria, because coupling is no longer strictly sin(theta)-based!
	phi_m1 = (phirth_xarray * np.sin(theta)[:, None]).mean(dim = "theta");
	return phi_m1;

def generate_poloidally_averaged_time_series(phirth_list, m1 = False):

	# Poloidal averaging, equivalent in function to flux-surface averaging. This isolates the m = 0 zonal component.
	# Intuitively speaking, this also 'folds' the circular geometry into one-dimensional radial strips.
	operation = lambda entry : entry.mean(dim = "theta") if not m1 else isolate_m1_component(entry);
	radial_strips = [operation(phirth_xarray) for phirth_xarray in phirth_list];

	# The following produces a two-dimensional x-array of shape (time, radial coordinate).
	time_series = xr.concat(radial_strips, dim = "time");
	return time_series;

def butterworth_band_pass_filter(time_series, time_step, low_cutoff = 0.1, high_cutoff = 0.4, output_stride = 2):

	# Determine sampling rate and Nyquist frequency in normalised units.
	# Note that cutoff frequencies also therefore becomes normalised...
	sampling_rate = calculate_sampling_frequency(output_stride, time_step);
	nyquist_frequency = 0.5 * sampling_rate;
	normalised_cutoff_frequencies = [low_cutoff / nyquist_frequency, high_cutoff / nyquist_frequency];

	# Denominator and numerator of the impulse response filter, respectively.
	# We choose here a fourth order high-pass filter.
	b, a = signal.butter(N = 4, Wn = normalised_cutoff_frequencies, btype = "band");
	filtered_signal = signal.filtfilt(b, a, time_series);
	return filtered_signal;