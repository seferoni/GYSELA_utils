# Imports.
import numpy as np;
import matplotlib.pyplot as plt;
import IO_utilities as IO;
import phi2D_utilities as utils;

# Styling.
plt.style.use("ggplot");

def plot_power_spectrum_density(phi2D_list, delta_t, effective_radius, figure_title, filename):

	# Signal isolation and data processing.
	# Logic here is similar to that of `extract_GAM_frequency` in the utilities.
	radial_time_series = utils.generate_poloidally_averaged_time_series(phi2D_list, effective_radius);
	frequencies, power_spectrum_density = utils.map_power_spectrum(radial_time_series, delta_t);
	frequencies = utils.convert_to_real_frequency(frequencies);
	GAM_peak_index = utils.isolate_GAM_peak_index(power_spectrum_density, frequencies);
	GAM_frequency = frequencies[GAM_peak_index];
	GAM_power = float(power_spectrum_density[GAM_peak_index]);
	
	# Figure plotting logic.
	plt.figure(figsize = (10, 6));
	plt.loglog(frequencies, power_spectrum_density, label = "PSD", color = "red", lw = 2.5);
	plt.vlines(GAM_frequency, GAM_power, 0, colors = "black", linestyles = "dotted");
	plt.plot(GAM_frequency, power_spectrum_density[GAM_peak_index], "ro");
	plt.annotate(f"GAM peak: {GAM_frequency / 1e3 : .2f} kHz", xy = (GAM_frequency, GAM_power), xytext = (GAM_frequency * 1.1, GAM_power * 1.5));
	plt.xlim(10, 15000);
	plt.xlabel("Frequency [Hz]");	
	plt.ylabel("Power (arb)");
	plt.title(figure_title);
	IO.save_figure(filename);

def main(phi2D_list, delta_t, effective_radius, filename, figure_title = r"PSD of $\langle \Phi \rangle_\theta$ ($m = n = 0$)"):

	# Entry point for `diagnostics_main.py`.
	plot_power_spectrum_density(phi2D_list, delta_t, effective_radius, figure_title, filename);