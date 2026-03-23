# Imports.
import numpy as np;
import matplotlib.pyplot as plt;
import IO_utilities as IO;
import gysela_utilities as utils;

# Styling.
plt.style.use("ggplot");

def plot_rosenbluth_hinton(phi2D_list, time_step, radial_index, filename, figure_title, start_index = 145, end_index = 1000):

	# Signal isolation and data processing.
	raw_time_series = utils.generate_poloidally_averaged_time_series(phi2D_list)[:, radial_index].values;
	processed_time_series = utils.butterworth_filter(raw_time_series, time_step, 2000);
	amplitude_envelope, residual_level = utils.generate_damping_envelope(processed_time_series);
	time_range = np.arange(len(processed_time_series));

	# Figure plotting logic.
	plt.figure(figsize=(10, 5));
	plt.plot(time_range[start_index : end_index], processed_time_series[start_index : end_index], color = "crimson", lw = 2.5);
	plt.axhline(0, color = "black", linestyle = "--", alpha = 0.3);
	plt.plot(time_range[start_index : end_index], amplitude_envelope[start_index : end_index], color = "black", linestyle = "--", label= "Damping envelope", lw = 2.0);
	plt.axhline(y = residual_level, color = "gray", linestyle = ":", label = "RH residual", lw = 2.5);
	plt.title(figure_title);
	plt.ylabel(r"$\delta \langle \Phi \rangle_\theta$ (high-pass filtered)");
	plt.xlabel("t [GYSELA timestep]");
	IO.save_figure(filename);

def main(phi2D_list, time_step, radial_index, filename, figure_title = "GAM damping & RH residual relaxation"):

	plot_rosenbluth_hinton(phi2D_list, time_step, radial_index, filename, figure_title);