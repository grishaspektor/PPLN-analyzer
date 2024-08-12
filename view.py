import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import ImageTk, Image, ImageDraw

class ImageView:
    def __init__(self, root, controller):
        self.controller = controller
        self.root = root
        self.root.title("Image Processing App")

        # Create a frame for the text boxes (new section)
        self.info_frame = tk.Frame(root)
        self.info_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Text box labels and default values
        labels = ["RUN#", "Chip#", "Device", "Electrode Separation (um)", "Electrode Period (um)",
                  "Electrode Width (um)", "Applied Voltage (mV)"]
        defaults = ["LN3", "", "", "", "", "", ""]

        # Create and pack text boxes horizontally, allowing wrapping to new lines
        self.text_entries = {}
        for label, default in zip(labels, defaults):
            frame = tk.Frame(self.info_frame)
            frame.pack(side=tk.LEFT, padx=5, pady=5)

            lbl = tk.Label(frame, text=label)
            lbl.pack(side=tk.TOP, anchor=tk.W)

            entry = tk.Entry(frame, width=20)
            entry.insert(0, default)
            entry.pack(side=tk.TOP, fill=tk.X)
            
            self.text_entries[label] = entry

        # Canvas to display the image
        self.canvas = tk.Canvas(root, width=600, height=400)
        self.canvas.pack()

        # Frame to hold the buttons horizontally
        self.button_frame = tk.Frame(root)
        self.button_frame.pack()

        # Button to load an image
        self.load_button = tk.Button(self.button_frame, text="Load Image", command=self.controller.load_image)
        self.load_button.pack(side=tk.LEFT)

        # Button to choose calibration region
        self.calibration_button = tk.Button(self.button_frame, text="Choose Calibration Region", command=self.controller.choose_calibration_region)
        self.calibration_button.pack(side=tk.LEFT)

        # Button to select poling ROI
        self.analyze_button = tk.Button(self.button_frame, text="Select Poling ROI", command=self.controller.select_poling_roi)
        self.analyze_button.pack(side=tk.LEFT)

        # Button to analyze poling
        self.analyze_poling_button = tk.Button(self.button_frame, text="Analyze Poling", command=self.controller.analyze_poling)
        self.analyze_poling_button.pack(side=tk.LEFT)

        # Frame to hold checkboxes and nominal period text box horizontally
        self.settings_frame = tk.Frame(root)
        self.settings_frame.pack()

        # Checkbox to toggle grid
        self.show_grid_var = tk.BooleanVar()
        self.grid_checkbox = tk.Checkbutton(self.settings_frame, text="Show Grid", variable=self.show_grid_var, command=self.toggle_grid)
        self.grid_checkbox.pack(side=tk.LEFT)

        # Checkbox to toggle between Single Line and ROI mode
        self.mode_var = tk.BooleanVar()
        self.mode_checkbox = tk.Checkbutton(self.settings_frame, text="Use ROI", variable=self.mode_var)
        self.mode_checkbox.pack(side=tk.LEFT)

        # Text box for nominal electrode period
        self.nominal_period_label = tk.Label(self.settings_frame, text="Nominal Electrode Period (microns):")
        self.nominal_period_label.pack(side=tk.LEFT)
        self.nominal_period_entry = tk.Entry(self.settings_frame, width=10)
        self.nominal_period_entry.pack(side=tk.LEFT)
        self.nominal_period_entry.insert(0, "2.8")  # Default value

        # Text box for calibration factor
        self.calibration_factor_label = tk.Label(self.settings_frame, text="Calibration Factor (microns/pixel):")
        self.calibration_factor_label.pack(side=tk.LEFT)
        self.calibration_factor_value = tk.StringVar()
        self.calibration_factor_entry = tk.Entry(self.settings_frame, textvariable=self.calibration_factor_value, state='readonly', width=10)
        self.calibration_factor_entry.pack(side=tk.LEFT)

        # Frame to hold edge exclusion settings
        self.exclusion_frame = tk.Frame(root)
        self.exclusion_frame.pack()

        # Text boxes for edge exclusion
        self.start_exclusion_label = tk.Label(self.exclusion_frame, text="Start Exclusion (pixels):")
        self.start_exclusion_label.pack(side=tk.LEFT)
        self.start_exclusion_entry = tk.Entry(self.exclusion_frame, width=5)
        self.start_exclusion_entry.pack(side=tk.LEFT)
        self.start_exclusion_entry.insert(0, "20")  # Default value
        self.start_exclusion_entry.bind("<KeyRelease>", self.update_edge_exclusion)

        self.end_exclusion_label = tk.Label(self.exclusion_frame, text="End Exclusion (pixels):")
        self.end_exclusion_label.pack(side=tk.LEFT)
        self.end_exclusion_entry = tk.Entry(self.exclusion_frame, width=5)
        self.end_exclusion_entry.pack(side=tk.LEFT)
        self.end_exclusion_entry.insert(0, "20")  # Default value
        self.end_exclusion_entry.bind("<KeyRelease>", self.update_edge_exclusion)

        # Slider and entry box for rotation
        self.rotation_frame = tk.Frame(root)
        self.rotation_frame.pack()
        self.rotation_label = tk.Label(self.rotation_frame, text="Rotate Image:")
        self.rotation_label.pack(side=tk.LEFT)
        self.rotation_slider = tk.Scale(self.rotation_frame, from_=-180, to=180, resolution=0.1, length=400, orient=tk.HORIZONTAL, command=self.controller.rotate_image)
        self.rotation_slider.pack(side=tk.LEFT)
        self.rotation_entry = tk.Entry(self.rotation_frame, width=5)
        self.rotation_entry.pack(side=tk.LEFT)
        self.rotation_entry.bind("<Return>", self.controller.update_rotation_slider)

        # Add a save button at the bottom right
        self.save_button = tk.Button(root, text="Save Results", command=self.controller.save_results)
        self.save_button.pack(side=tk.BOTTOM, anchor=tk.SE, padx=10, pady=10)

        self.tk_image = None
        self.original_image = None  # Store the original image separately
        self.grid_image = None
        self.grid_active = False
        self.calibration_lines = []
        self.profile_lines = []

    def display_image(self, image):
        # Maximum dimensions for the image
        max_width = 800
        max_height = 600

        # Calculate the scaling factor to maintain aspect ratio
        width, height = image.size
        scaling_factor = min(max_width / width, max_height / height, 1)
        new_width = int(width * scaling_factor)
        new_height = int(height * scaling_factor)

        # Resize the image for display purposes only
        display_image = image.resize((new_width, new_height), Image.LANCZOS)
        
        self.original_image = image  # Save the original image

        self.tk_image = ImageTk.PhotoImage(display_image)
        self.canvas.config(width=new_width, height=new_height)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.image = self.tk_image

        if self.grid_active:
            self.draw_grid()

        if self.calibration_lines:
            self.draw_calibration_lines()

        print(f"Image displayed with size: {display_image.size}")

    def draw_grid(self):
        self.grid_image = self.original_image.copy()  # Copy the original image for grid overlay
        draw = ImageDraw.Draw(self.grid_image)
        width, height = self.grid_image.size

        # Draw vertical and horizontal dashed lines
        for i in range(0, width, 50):
            self._draw_dashed_line(draw, (i, 0, i, height), "white")
        for i in range(0, height, 50):
            self._draw_dashed_line(draw, (0, i, width, i), "white")

        display_image = self.grid_image.resize((self.canvas.winfo_width(), self.canvas.winfo_height()), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display_image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.image = self.tk_image

    def _draw_dashed_line(self, draw, coordinates, color, dash_length=5):
        x1, y1, x2, y2 = coordinates
        if x1 == x2:  # Vertical line
            for y in range(y1, y2, dash_length * 2):
                draw.line((x1, y, x2, min(y + dash_length, y2)), fill=color)
        elif y1 == y2:  # Horizontal line
            for x in range(x1, x2, dash_length * 2):
                draw.line((x, y1, min(x + dash_length, x2), y2), fill=color)

    def toggle_grid(self):
        self.grid_active = not self.grid_active
        self.clear_profile_lines()
        self.display_image(self.original_image)
        if self.grid_active:
            self.draw_grid()
        if self.calibration_lines:
            self.draw_calibration_lines()

    def clear_profile_lines(self):
        self.profile_lines = []
        self.canvas.delete("all")  # Clears the canvas to remove previous lines

    def update_rotation_entry(self, angle):
        self.rotation_entry.delete(0, tk.END)
        self.rotation_entry.insert(0, str(angle))

    def bind_canvas_click(self, callback):
        self.canvas.bind("<Button-1>", callback)

    def unbind_canvas_click(self):
        self.canvas.unbind("<Button-1>")

    def draw_calibration_lines(self):
        for line in self.calibration_lines:
            self.canvas.create_line(line[0], line[1], line[2], line[3], fill="yellow", dash=(4, 4))

    def update_calibration_lines(self, y1, y2):
        self.calibration_lines = [
            (20, y1, self.canvas.winfo_width() - 20, y1),
            (20, y2, self.canvas.winfo_width() - 20, y2)
        ]
        self.draw_calibration_lines()

    def draw_profile_lines(self):
        for line in self.profile_lines:
            self.canvas.create_line(line[0], line[1], line[2], line[3], fill="red")

    def update_profile_lines(self, y1, y2=None):
        canvas_width = self.canvas.winfo_width()
        start_exclusion = int(self.start_exclusion_entry.get())
        end_exclusion = int(self.end_exclusion_entry.get())
        if y2 is None:
            self.profile_lines = [
                (start_exclusion, y1, canvas_width - end_exclusion, y1)
            ]
        else:
            self.profile_lines = [
                (start_exclusion, y1, canvas_width - end_exclusion, y1),
                (start_exclusion, y2, canvas_width - end_exclusion, y2)
            ]
        self.draw_profile_lines()

    def update_edge_exclusion(self, event):
        # Update the profile lines based on new edge exclusion values
        if self.profile_lines:
            y1 = self.profile_lines[0][1]
            y2 = self.profile_lines[1][1] if len(self.profile_lines) > 1 else None
            self.update_profile_lines(y1, y2)
