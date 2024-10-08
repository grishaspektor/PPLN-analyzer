from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import numpy as np
import csv
import os
from scipy.signal import find_peaks
from datetime import datetime
import configparser
from skimage import io, color, feature, transform


class ImageController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.calibration_region = []
        self.prominence_value = 10  # Initial prominence value, adjust as needed
        self.calibration_factor = None  # Store the calibration factor
        self.profile_region = []
        self.line_profile = None  # Store the line profile for analysis
        self.analysis_results = {}  # Store analysis results for future use
        self.csv_file = "analysis_results.csv"  # Default CSV file
        self.image_file_name = None  # Store the image file name
        self.rotation_angle = 0  # Store the current rotation angle
        self.image_dir = None  # Directory where the image is located
        self.config_file = "config.ini"  # Configuration file to store settings
        self.csv_file = self.load_database_location()  # Load the stored database location

    
    def load_database_location(self):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):  # Check if the config file exists
            config.read(self.config_file)
        if "Database" in config and "file" in config["Database"]:
            return config["Database"]["file"]
        else:
            return "analysis_results.csv"  # Default file name

    def save_database_location(self, file_path):
        config = configparser.ConfigParser()
        config["Database"] = {"file": file_path}
        with open(self.config_file, 'w') as configfile:
            config.write(configfile)
        self.csv_file = file_path

    def select_database_location(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if file_path:
            self.save_database_location(file_path)
            messagebox.showinfo("Database Location", f"Database location set to: {file_path}")

    
    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("TIFF files", "*.tif"), ("All files", "*.*")])
        if file_path:
            self.image_file_name = os.path.basename(file_path)  # Save the image file name
            self.image_dir = os.path.dirname(file_path)  # Save the directory of the image file
            image = self.model.load_image(file_path)
            if image:
                self.view.display_image(image)
                print(f"Image loaded and displayed: {file_path}")

    def rotate_image(self, angle):
        self.rotation_angle = angle  # Save the rotation angle
        rotated_image = self.model.rotate_image(angle)
        if rotated_image:
            self.view.display_image(rotated_image)
            print(f"Image rotated by {angle} degrees")
        self.view.update_rotation_entry(angle)

    def update_rotation_slider(self, event):
        angle = self.view.rotation_entry.get()
        try:
            angle = float(angle)
            self.rotation_angle = angle  # Save the rotation angle
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
        self.view.update_profile_lines(y1=y)
        # Scale the y-coordinate to the original image's resolution
        scaled_y = int(y / self.view.canvas.winfo_height() * self.model.rotated_image.size[1])
        line_profile = self.model.get_line_profile(scaled_y)
        if line_profile is not None:
            # Get the edge exclusion values from the view
            start_exclusion = int(self.view.start_exclusion_entry.get())
            end_exclusion = int(self.view.end_exclusion_entry.get())

            # Exclude edge pixels horizontally
            self.line_profile = line_profile[start_exclusion:-end_exclusion]
            try:
                print(f"Line profile obtained at y={y}, scaled_y={scaled_y}")  # Debug statement
                self.plot_line_profile(self.line_profile)
                # Store the number of lines averaged in the ROI
                self.analysis_results['lines_averaged'] = 1  # Since it's a single line
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
            self.view.update_profile_lines(y1, y2)
            self.process_roi_profile()

    def process_roi_profile(self):
        y1, y2 = sorted(self.profile_region)
        scaled_y1 = int(y1 / self.view.canvas.winfo_height() * self.model.rotated_image.size[1])
        scaled_y2 = int(y2 / self.view.canvas.winfo_height() * self.model.rotated_image.size[1])
        
        # Calculate the number of lines (pixels) in the ROI
        lines_averaged = scaled_y2 - scaled_y1
        print(f" The number of vertical pixels in ROI is: {lines_averaged}")
        
        # Get the edge exclusion values from the view
        start_exclusion = int(self.view.start_exclusion_entry.get())
        end_exclusion = int(self.view.end_exclusion_entry.get())
    
        roi_profile = np.mean(np.array(self.model.rotated_image)[scaled_y1:scaled_y2, start_exclusion:-end_exclusion], axis=0)
        self.line_profile = roi_profile
        
        # Store the number of lines averaged
        self.lines_averaged_in_ROI = lines_averaged
        
        self.plot_line_profile(self.line_profile)
        
        # sanity check:
        import matplotlib.pyplot as plt
        plt.imshow(self.model.rotated_image,cmap='gray')
        plt.plot([start_exclusion, self.model.rotated_image.size[0]-end_exclusion], [scaled_y1, scaled_y1], color='green', linestyle='-', linewidth=1)  # Line at y1
        plt.plot([start_exclusion, self.model.rotated_image.size[0]-end_exclusion], [scaled_y2, scaled_y2], color='red', linestyle='-', linewidth=1)  # Line at y2


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
            plt.grid(True)  # Add grid
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
    
            # Plot the line profile with minima marked
            self.line_profile_fig = plt.figure()
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
            plt.grid(True)
            plt.show()
    
            # Plot the widths of odd and even regions
            self.widths_fig = plt.figure()  # Store the figure reference
            plt.plot(np.arange(1, len(odd_region_widths) + 1), odd_region_widths, 'ro-', 
                     label=r"Actively Poled (Odd) Regions" "\n" r"$\mathbf{Mean:}$ " f"{odd_mean:.2f} µm, " r"$\mathbf{Std:}$ " f"{odd_std:.2f} µm")
            plt.plot(np.arange(1, len(even_region_widths) + 1), even_region_widths, 'bo-', 
                     label=r"Passively Poled (Even) Regions" "\n" r"$\mathbf{Mean:}$ " f"{even_mean:.2f} µm, " r"$\mathbf{Std:}$ " f"{even_std:.2f} µm")
            plt.axhline(y=odd_mean, color='black', linestyle='--')
            plt.axhline(y=even_mean, color='black', linestyle='--')
            plt.title("Region Widths")
            plt.xlabel("Region Number")
            plt.ylabel("Width (Microns)" if self.calibration_factor else "Width (Pixels)")
            plt.grid(True)
            plt.legend()
            plt.show()
    
            # Redefine duty cycle as odd_region_width / (odd_region_width + even_region_width)
            duty_cycle = odd_region_widths / (odd_region_widths + even_region_widths)
    
            # Calculate the mean and standard deviation of the duty cycle
            duty_cycle_mean = np.mean(duty_cycle)
            duty_cycle_std = np.std(duty_cycle)
    
            # Plot the duty cycle
            self.duty_cycle_fig = plt.figure()  # Store the figure reference
            plt.plot(np.arange(1, len(duty_cycle) + 1), duty_cycle, 'mo-',  # Change to purple
                     label=r"$\mathbf{Duty\ Cycle}$" "\n" r"$\mathbf{Mean:}$ " f"{duty_cycle_mean:.2f}, " r"$\mathbf{Std:}$ " f"{duty_cycle_std:.2f}")
            plt.axhline(y=duty_cycle_mean, color='black', linestyle='--')
            plt.axhline(y=0.5, color='red', linestyle='--')  # Add a red dashed line at 0.5
            plt.ylim(0, 1)
            plt.title("Duty Cycle")
            plt.xlabel("Region Pair Number")
            plt.ylabel("Duty Cycle (Odd / (Odd + Even))")
            plt.grid(True)
            plt.legend()
            plt.show()
    
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
                "duty_cycle_std": duty_cycle_std,
                "lines_averaged": self.lines_averaged_in_ROI
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
        
        # Get the edge exclusion values from the view
        start_exclusion = int(self.view.start_exclusion_entry.get())
        end_exclusion = int(self.view.end_exclusion_entry.get())

        calibration_data = np.mean(np.array(self.model.rotated_image)[scaled_y1:scaled_y2, start_exclusion:-end_exclusion], axis=0)
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
        plt.grid(True)  # Add grid
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

    def save_results(self):
        # Paths for the plots and analysis data
        widths_plot_path = os.path.join(self.image_dir, f"{os.path.splitext(self.image_file_name)[0]}_widths.png")
        duty_cycle_plot_path = os.path.join(self.image_dir, f"{os.path.splitext(self.image_file_name)[0]}_duty_cycle.png")
        analysis_data_path = os.path.join(self.image_dir, f"{os.path.splitext(self.image_file_name)[0]}_analysis_data.csv")
        
        # Check if files already exist for the current image
        if os.path.exists(widths_plot_path) or os.path.exists(duty_cycle_plot_path) or os.path.exists(analysis_data_path):
            overwrite = messagebox.askyesno("File Exists", "The file for this image has already been processed. Do you want to overwrite?")
            if not overwrite:
                return  # If user chooses not to overwrite, return early
        
        # Extract data from text boxes (excluding Description for now)
        data = {label: entry.get() for label, entry in self.view.text_entries.items() if label != "Description"}
        
        # Add additional data
        data["Rotation Angle"] = self.rotation_angle
        data["Image File Name"] = self.image_file_name
        data["Analysis Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Add analysis date
        
        # Extract analysis results
        if self.analysis_results:
            data.update({
                "Mean Odd Region Width (µm)": self.analysis_results["odd_mean"],
                "Std Odd Region Width (µm)": self.analysis_results["odd_std"],
                "Mean Even Region Width (µm)": self.analysis_results["even_mean"],
                "Std Even Region Width (µm)": self.analysis_results["even_std"],
                "Mean Duty Cycle": self.analysis_results["duty_cycle_mean"],
                "Std Duty Cycle": self.analysis_results["duty_cycle_std"],
                "Lines Averaged in ROI": self.analysis_results["lines_averaged"]
            })
        else:
            print("No analysis results to save.")
            return
        
        # Add the Description field last
        data["Description"] = self.view.text_entries["Description"].get()
        
        # Write the detailed analysis data (region widths and duty cycle) to a CSV file in the image directory
        with open(analysis_data_path, 'w', newline='') as csvfile:
            fieldnames = ["Region Number", "Odd Region Width (µm)", "Even Region Width (µm)", "Duty Cycle"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for i in range(len(self.analysis_results["odd_region_widths"])):
                writer.writerow({
                    "Region Number": i + 1,
                    "Odd Region Width (µm)": self.analysis_results["odd_region_widths"][i],
                    "Even Region Width (µm)": self.analysis_results["even_region_widths"][i],
                    "Duty Cycle": self.analysis_results["duty_cycle"][i]
                })
            # Write the summary stats at the end of the CSV
            writer.writerow({})
            writer.writerow({"Region Number": "Mean Odd Region Width (µm)", "Odd Region Width (µm)": self.analysis_results["odd_mean"]})
            writer.writerow({"Region Number": "Std Odd Region Width (µm)", "Odd Region Width (µm)": self.analysis_results["odd_std"]})
            writer.writerow({"Region Number": "Mean Even Region Width (µm)", "Even Region Width (µm)": self.analysis_results["even_mean"]})
            writer.writerow({"Region Number": "Std Even Region Width (µm)", "Even Region Width (µm)": self.analysis_results["even_std"]})
            writer.writerow({"Region Number": "Mean Duty Cycle", "Duty Cycle": self.analysis_results["duty_cycle_mean"]})
            writer.writerow({"Region Number": "Std Duty Cycle", "Duty Cycle": self.analysis_results["duty_cycle_std"]})
        print(f"Analysis data saved to {analysis_data_path}")
        
        # Save the already plotted figures
        self.widths_fig.savefig(widths_plot_path)
        print(f"Widths plot saved to {widths_plot_path}")
        
        self.duty_cycle_fig.savefig(duty_cycle_plot_path)
        print(f"Duty cycle plot saved to {duty_cycle_plot_path}")
        
        # Write to the main CSV database
        if not os.path.exists(self.csv_file):
            write_header = True  # File doesn't exist, so write the header
            mode = 'w'  # Create the file
        else:
            write_header = False  # File exists, no need to write header
            mode = 'a'  # Open in append mode
        
        with open(self.csv_file, mode, newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data.keys())
            if write_header:
                writer.writeheader()
            writer.writerow(data)
        
        print("Results saved to", self.csv_file)
 
    def auto_rotate_image(self):
        # Convert the original image to a NumPy array
        image_array = np.array(self.model.rotated_image)
        
        # Check if the image is already grayscale
        if image_array.ndim == 2:  # Image is already grayscale
            gray_image = image_array
        else:
            gray_image = color.rgb2gray(image_array)
        
        # Use Canny edge detection
        edges = feature.canny(gray_image, sigma=2.0)
        
        # Perform Hough transform to detect lines
        hough_lines = transform.probabilistic_hough_line(edges, threshold=10, line_length=100, line_gap=3)
        
        # Calculate angles of the lines
        angles = []
        for line in hough_lines:
            p0, p1 = line
            angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
            angles.append(angle)
        
        # Normalize angles to the [-45, 45] range
        angles = [angle - 90 if angle > 45 else angle + 90 if angle < -45 else angle for angle in angles]
        
        # Compute the median angle
        if angles:
            median_angle = np.median(angles)
        else:
            median_angle = 0
        
        # Update the rotation angle and trigger the update
        self.rotation_angle = median_angle
        self.view.update_rotation_entry(median_angle)
        
        # Synchronize the slider with the textbox
        self.view.rotation_slider.set(median_angle)
        
        self.rotate_image(median_angle)
    
