# Imports.
import numpy as np;
import xarray as xr;
from scipy import signal;
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
	"electron_temperature_joules" : simulation_parameters_raw["electron_temperature"]  * 1000. * physical_constants["electron_volt"],
	"ion_mass" : 2.0 * physical_constants["proton_mass"], # Presuming deuterium.
	"rhostar_gys" : 1./float(geometry["minor_radius_gys"]),
};

normalisation_parameters = {
	"thermal_velocity" : np.sqrt(simulation_parameters["ion_temperature_joules"]/simulation_parameters["ion_mass"]),
	"normalisation_coeff_gys" : geometry["aspect_ratio_gys"]/(simulation_parameters["rhostar_gys"] * np.sqrt(2.))
};

# -------------------------------------------------------------------
# -------- Radial propagation/PSD & FFT helper functions. -----------
# -------------------------------------------------------------------

def extract_gam_frequency(phi2D_list, time_step):

	radial_time_series = generate_poloidally_averaged_time_series(phi2D_list);
	frequencies, power_spectrum_density = map_power_spectrum(radial_time_series, 40, time_step.flatten()[0]);
	# The division by 2 * pi is necessary to convert from angular frequency to linear frequency, as the former is what the FFT yields.
	frequencies = convert_to_real_frequency(frequencies)/(2 * np.pi);
	GAM_peak_index = isolate_GAM_peak_index(power_spectrum_density);
	# We assume here that the peak corresponding to the GAM is the most prominent peak within the power spectrum.
	# This assumption holds valid provided we have omitted the ZFZF peak!
	GAM_frequency = frequencies[GAM_peak_index];
	return GAM_frequency;

def extract_gam_growth_rate(phi2D_list, radial_index = 40):

	radially_localised_time_series = generate_poloidally_averaged_time_series(phi2D_list)[:, radial_index].values;
	time_range = np.arange(len(radially_localised_time_series));
	envelope, residual_level = generate_residual_envelope(radially_localised_time_series);

	# The residual level behaves as a static vertical offset. By subtracting it from the envelope, we can isolate the pure decay signal.
	pure_decay_signal = envelope - residual_level;
	# Take only positive signal values prior to the tail of the signal to ensure well-behaved logarithmic fitting.
	mask = pure_decay_signal > (0.05 * np.max(pure_decay_signal));
	log_signal = convert_to_real_frequency(np.log(pure_decay_signal[mask]));
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
	# Pad signal with 0s to improve resolution.
	padded_signal_steps = signal_steps * padding_factor;
	signal_fourier = np.array(fft(signal, n = padded_signal_steps));
	power_spectrum_density = np.abs(signal_fourier) ** 2;
	
	# Generate actual frequency data.
	frequencies = fftfreq(padded_signal_steps, time_step);

	# Preserve positive frequencies.
	mask = frequencies > 0;
	return frequencies[mask], power_spectrum_density[mask];

def convert_to_real_frequency(frequency_term):

	dimensionless_normalisation_coeff = normalisation_parameters["normalisation_coeff_gys"];
	real_normalisation_coeff = normalisation_parameters["thermal_velocity"]/geometry["major_radius"];
	return frequency_term * dimensionless_normalisation_coeff * real_normalisation_coeff;

def generate_residual_envelope(radial_time_series):

	# Isolate last one hundred entries in the time series as the residual.
	residual_level = np.mean(radial_time_series[-100:]);
	
	# Isolate peaks.
	peak_indices, _ = signal.find_peaks(radial_time_series, distance = 20);
	peaks = radial_time_series[peak_indices];
	peak_times = np.arange(len(radial_time_series));

	# Interpolate envelope. Chosen cubic here to better approximate Landau damping.
	envelope = interp1d(peak_indices, peaks, kind = "cubic", bounds_error = False, fill_value = (peaks[0], peaks[-1]))(peak_times);
	return envelope, residual_level;

def isolate_GAM_peak_index(power_spectrum_density):

	# NB: `peak_indices` corresponds to peaks in `power_spectrum_density`.
	# Prominence is calibrated to ensure a ZFZF power spike, if present, is ignored.
	peak_indices, _ = signal.find_peaks(power_spectrum_density, prominence = power_spectrum_density.max() * 0.1);
	peaks = power_spectrum_density[peak_indices];
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
# ------------------- Auxiliary methods. ----------------------------
# -------------------------------------------------------------------

def isolate_m1_component(phirth_xarray):

	theta = np.linspace(0, 2 * np.pi, len(phirth_xarray.theta));
	
	# Take note that the m = 1 can be isolated by projecting phi unto sin(theta).
	# This is permitted due to Fourier decomposition & orthogonality properties.
	phi_m1 = (phirth_xarray * np.sin(theta)[:, None]).mean(dim = "theta");
	return phi_m1;

def generate_poloidally_averaged_time_series(phirth_list, m1 = False):

	# Poloidal averaging, equivalent in function to flux-surface averaging. This isolates the m = 0 zonal component.
	# Intuitively speaking, this also 'truncates' the circular geometry into one-dimensional radial strips.
	operation = lambda entry : entry.mean(dim = "theta") if not m1 else isolate_m1_component(entry);
	radial_strips = [operation(phirth_xarray) for phirth_xarray in phirth_list];

	# The following produces a two-dimensional x-array of shape (time, radial coordinate).
	time_series = xr.concat(radial_strips, dim = "time");
	return time_series;