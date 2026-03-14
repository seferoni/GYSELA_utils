# Imports.
import numpy as np;
import matplotlib.pyplot as plt;
import IO_utilities as IO;
import gysela_utilities as utils;

# Styling.
plt.style.use("ggplot");

def plot_rosenbluth_hinton(phi2D_list, radial_index, filename, figure_title):

	# Signal isolation and data processing.
	time_series = utils.generate_poloidally_averaged_time_series(phi2D_list)[:, radial_index].values;
	time_range = np.arange(len(time_series));
	amplitude_envelope, residual_level = utils.generate_residual_envelope(time_series);

	# Figure plotting logic.
	plt.figure(figsize = (10, 5));
	# Ignore first hundred-or-so entries.
	plt.plot(time_range[145:], time_series[145:], color = "red", lw = 2.5);
	plt.plot(time_range[145:], amplitude_envelope[145:], color = "black", linestyle = "--", label= "Damping envelope", lw = 2.0);
	plt.axhline(y = residual_level, color = "gray", linestyle = ":", label = "RH residual", lw = 2.5);
	plt.xlabel("t [GYSELA timestep]");
	plt.ylabel(r"$\langle \Phi \rangle_\theta$");
	plt.title(figure_title);
	plt.legend(frameon = True, loc = "upper right");
	IO.save_figure(filename);

def main(phi2D_list, radial_index, filename, figure_title = "GAM damping & RH residual relaxation"):

	plot_rosenbluth_hinton(phi2D_list, radial_index, filename, figure_title);