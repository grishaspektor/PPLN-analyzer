from tkinter import filedialog
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks

class ImageController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.calibration_region = []
        self.prominence_value = 10  # Initial prominence value, adjust as needed
        self.calibration_factor = None  # Store the calibration factor
        self.edge_exclusion = 20  # Number of edge pixels to exclude horizontally
        self.profile_region = []
        self.line_profile = None  # Store the line profile for analysis
        self.analysis_results = {}  # Store analysis results for future use

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("TIFF files", "*.tif"), ("All files", "*.*")])
        if file_path:
            image = self.model.load_image(file_path)
            if image:
                self.view.display_image(image)
                print(f"Image loaded and displayed: {file_path}")

    def rotate_image(self, angle):
        rotated_image = self.model.rotate_image(angle)
        if rotated_image:
            self.view.display_image(rotated_image)
            print(f"Image rotated by {angle} degrees")
        self.view.update_rotation_entry(angle)

    def update_rotation_slider(self, event):
        angle = self.view.rotation_entry.get()
        try:
            angle = float(angle)
            self.view.rotation_slider.set(angle)
        except ValueError:
            pass

    def select_poling_roi(self):
        # Clear previous lines
        self.view.clear_profile_lines()
        
        # Refresh display
        self.view.display_image(self.model.rotated_image)
        
        if self.view.mode_var.get():
            self.activate_roi_mode()
        else:
            self.activate_get_period()

    def activate_get_period(self):
        self.view.bind_canvas_click(self.get_line_profile)

    def get_line_profile(self, event):
        y = event.y
        self.view.update_profile_lines(y1=y, edge_exclusion=self.edge_exclusion)
        # Scale the y-coordinate to the original image's resolution
        scaled_y = int(y / self.view.canvas.winfo_height() * self.model.rotated_image.size[1])
        line_profile = self.model.get_line_profile(scaled_y)
        if line_profile is not None:
            # Exclude edge pixels horizontally
            self.line_profile = line_profile[self.edge_exclusion:-self.edge_exclusion]
            try:
                print(f"Line profile obtained at y={y}, scaled_y={scaled_y}")  # Debug statement
                self.plot_line_profile(self.line_profile)
            except Exception as e:
                print(f"Error plotting line profile: {e}")
        else:
            print("Line profile is None")  # Debug statement
        self.view.unbind_canvas_click()

    def activate_roi_mode(self):
        self.profile_region = []
        self.view.bind_canvas_click(self.define_profile_region)

    def define_profile_region(self, event):
        y = event.y
        self.profile_region.append(y)
        if len(self.profile_region) == 2:
            self.view.unbind_canvas_click()
            y1, y2 = sorted(self.profile_region)
            self.view.update_profile_lines(y1, y2, edge_exclusion=self.edge_exclusion)
            self.process_roi_profile()

    def process_roi_profile(self):
        y1, y2 = sorted(self.profile_region)
        scaled_y1 = int(y1 / self.view.canvas.winfo_height() * self.model.rotated_image.size[1])
        scaled_y2 = int(y2 / self.view.canvas.winfo_height() * self.model.rotated_image.size[1])
        roi_profile = np.mean(np.array(self.model.rotated_image)[scaled_y1:scaled_y2, self.edge_exclusion:-self.edge_exclusion], axis=0)
        self.line_profile = roi_profile
        self.plot_line_profile(self.line_profile)

    def plot_line_profile(self, line_profile):
        print("Entering plot_line_profile")
        try:
            print(f"Line profile length: {len(line_profile)}")
            plt.figure()
            # Convert pixel positions to micron positions if calibration factor is available
            if self.calibration_factor:
                x_axis = np.arange(len(line_profile)) * self.calibration_factor
                plt.xlabel("Position (microns)")
            else:
                x_axis = np.arange(len(line_profile))
                plt.xlabel("Pixel")
            plt.plot(x_axis, line_profile)
            plt.title("Line Profile")
            plt.ylabel("Intensity")
            plt.show()
            print("Plot displayed successfully")
        except Exception as e:
            print(f"Error during plotting: {e}")
        finally:
            print("Exiting plot_line_profile")

    def analyze_poling(self):
        if self.line_profile is not None:
            # Find the prominent minima in the line profile
            minima_indices, _ = find_peaks(-self.line_profile, prominence=self.prominence_value)
    
            # Calculate the width of each region in pixels
            region_widths_pixels = np.diff(minima_indices)
    
            # Convert region widths to microns using the calibration factor
            if self.calibration_factor:
                region_widths_microns = region_widths_pixels * self.calibration_factor
            else:
                region_widths_microns = region_widths_pixels  # If no calibration factor, keep it in pixels
    
            # Separate the widths into odd (actively poled) and even (passively poled) regions
            odd_region_widths = region_widths_microns[::2]
            even_region_widths = region_widths_microns[1::2]
    
            # Truncate to make sure odd and even regions have the same number of elements
            min_length = min(len(odd_region_widths), len(even_region_widths))
            odd_region_widths = odd_region_widths[:min_length]
            even_region_widths = even_region_widths[:min_length]
    
            # Calculate the mean and standard deviation of the region widths
            odd_mean = np.mean(odd_region_widths)
            odd_std = np.std(odd_region_widths)
            even_mean = np.mean(even_region_widths)
            even_std = np.std(even_region_widths)
    
            # Plot the widths of odd and even regions
            plt.figure()
            plt.plot(np.arange(1, len(odd_region_widths) + 1), odd_region_widths, 'bo-', 
                     label=r"Actively Poled (Odd) Regions" "\n" r"$\mathbf{Mean:}$ " f"{odd_mean:.2f} µm, " r"$\mathbf{Std:}$ " f"{odd_std:.2f} µm")
            plt.plot(np.arange(1, len(even_region_widths) + 1), even_region_widths, 'ro-', 
                     label=r"Passively Poled (Even) Regions" "\n" r"$\mathbf{Mean:}$ " f"{even_mean:.2f} µm, " r"$\mathbf{Std:}$ " f"{even_std:.2f} µm")
            plt.axhline(y=odd_mean, color='black', linestyle='--')
            plt.axhline(y=even_mean, color='black', linestyle='--')
            plt.title("Region Widths")
            plt.xlabel("Region Number")
            plt.ylabel("Width (Microns)" if self.calibration_factor else "Width (Pixels)")
            plt.legend()
            plt.show()
    
            # Redefine duty cycle as odd_region_width / (odd_region_width + even_region_width)
            duty_cycle = odd_region_widths / (odd_region_widths + even_region_widths)
    
            # Calculate the mean and standard deviation of the duty cycle
            duty_cycle_mean = np.mean(duty_cycle)
            duty_cycle_std = np.std(duty_cycle)
    
            # Plot the duty cycle
            plt.figure()
            plt.plot(np.arange(1, len(duty_cycle) + 1), duty_cycle, 'ko-', 
                     label=r"$\mathbf{Duty\ Cycle}$" "\n" r"$\mathbf{Mean:}$ " f"{duty_cycle_mean:.2f}, " r"$\mathbf{Std:}$ " f"{duty_cycle_std:.2f}")
            plt.axhline(y=duty_cycle_mean, color='black', linestyle='--')
            plt.title("Duty Cycle")
            plt.xlabel("Region Pair Number")
            plt.ylabel("Duty Cycle (Odd / (Odd + Even))")
            plt.legend()
            plt.show()
    
            # Plot the raw profile with minima marked
            plt.figure()
            x = np.arange(len(self.line_profile))
            if self.calibration_factor:
                x_axis = x * self.calibration_factor
                plt.xlabel("Position (Microns)")
            else:
                x_axis = x
                plt.xlabel("Pixel")
            plt.plot(x_axis, self.line_profile, label="Raw Line Profile")
            plt.plot(x_axis[minima_indices], self.line_profile[minima_indices], 'rx', label="Minima")
            plt.title("Raw Line Profile with Minima")
            plt.ylabel("Intensity")
            plt.legend()
            plt.show()
    
            print(f"Minima found at indices: {minima_indices}")
    
            # Store calculated quantities for future use
            self.analysis_results = {
                "odd_region_widths": odd_region_widths,
                "even_region_widths": even_region_widths,
                "odd_mean": odd_mean,
                "odd_std": odd_std,
                "even_mean": even_mean,
                "even_std": even_std,
                "duty_cycle": duty_cycle,
                "duty_cycle_mean": duty_cycle_mean,
                "duty_cycle_std": duty_cycle_std
            }
        else:
            print("No line profile available for analysis.")

    def choose_calibration_region(self):
        self.calibration_region = []
        self.view.bind_canvas_click(self.define_calibration_region)

    def define_calibration_region(self, event):
        y = event.y
        self.calibration_region.append(y)
        if len(self.calibration_region) == 2:
            self.view.unbind_canvas_click()
            y1, y2 = sorted(self.calibration_region)
            self.view.update_calibration_lines(y1, y2)
            self.process_calibration_region()

    def process_calibration_region(self):
        y1, y2 = sorted(self.calibration_region)
        scaled_y1 = int(y1 / self.view.canvas.winfo_height() * self.model.rotated_image.size[1])
        scaled_y2 = int(y2 / self.view.canvas.winfo_height() * self.model.rotated_image.size[1])
        calibration_data = np.mean(np.array(self.model.rotated_image)[scaled_y1:scaled_y2, self.edge_exclusion:-self.edge_exclusion], axis=0)
        self.plot_calibration_data(calibration_data)
        self.calculate_calibration_factor(calibration_data)

    def plot_calibration_data(self, calibration_data):
        min_value = np.min(calibration_data)
        minima_indices, properties = find_peaks(-calibration_data, prominence=self.prominence_value)

        plt.figure()
        plt.plot(calibration_data, label="Calibration Profile")
        plt.plot(minima_indices, calibration_data[minima_indices], 'rx', label="Minima")
        plt.title("Calibration Region Profile")
        plt.xlabel("Pixel")
        plt.ylabel("Intensity")
        plt.legend()
        plt.show()

    def calculate_calibration_factor(self, calibration_data):
        nominal_period = float(self.view.nominal_period_entry.get())
        minima_indices, properties = find_peaks(-calibration_data, prominence=self.prominence_value)
        num_periods = len(minima_indices) - 1
        if num_periods > 0:
            total_pixels = minima_indices[-1] - minima_indices[0]
            calibration_factor = (nominal_period * num_periods) / total_pixels
            self.calibration_factor = calibration_factor  # Store the calibration factor
            self.view.calibration_factor_value.set(f"{calibration_factor:.6f}")
            print(f"Calibration factor calculated: {calibration_factor:.6f} microns/pixel")
        else:
            self.calibration_factor = None
            self.view.calibration_factor_value.set("N/A")
            print("Insufficient number of periods detected for calibration.")
