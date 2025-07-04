import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import re
import base64

class UnitModifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Unit Parameter Modifier")
        self.root.geometry("1200x900")  # Increased width for comparison view
        
        # Initialize data structures
        self.translation_data = {}
        self.unit_data = []  # (display_text, unit_id, name)
        self.current_unit_params = {}
        self.original_unit_params = {}  # Store original parameters for comparison
        self.current_unit_id = None
        self.modifications = {}
        self.unit_files_path = "units"
        self.complex_params = ["customparams", "featuredefs", "sfxtypes", "sounds"]
        self.added_parameters = set()  # Track parameters added via import
        self.comparison_mode = False  # Track if we're in comparison view
        
        # Create custom styles for comparison highlighting
        self.style = ttk.Style()
        self.style.configure('New.TFrame', background='#e0f7fa')  # Light blue for new params
        self.style.configure('Modified.TFrame', background='#e8f5e9')  # Light green for modified params
        
        # Create UI
        self.create_widgets()
        
        # Load data
        self.load_translation_data()
        
        # Load existing export data if available
        self.load_export_data()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File selection
        file_frame = ttk.LabelFrame(main_frame, text="Configuration Files", padding=10)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Translation File:").grid(row=0, column=0, sticky="w")
        self.translation_file = tk.StringVar(value="units.json")
        ttk.Entry(file_frame, textvariable=self.translation_file, width=40).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="Browse", command=self.browse_translation).grid(row=0, column=2)
        
        ttk.Label(file_frame, text="Unit Files Path:").grid(row=1, column=0, sticky="w")
        self.unit_files_path_var = tk.StringVar(value=self.unit_files_path)
        ttk.Entry(file_frame, textvariable=self.unit_files_path_var, width=40).grid(row=1, column=1, padx=5)
        ttk.Button(file_frame, text="Browse", command=self.browse_unit_path).grid(row=1, column=2)
        
        ttk.Button(file_frame, text="Reload Data", command=self.reload_data).grid(row=2, column=0, columnspan=3, pady=10)
        
        # Create a frame for the right side (log and unit selection)
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Log area (smaller and in upper right corner)
        log_frame = ttk.LabelFrame(right_frame, text="Log", padding=10)
        log_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        
        self.log_text = tk.Text(log_frame, height=4, width=50, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=self.log_scroll.set)
        
        # Unit selection with search
        unit_frame = ttk.LabelFrame(main_frame, text="Unit Selection", padding=10)
        unit_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(unit_frame, text="Search:").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(unit_frame, textvariable=self.search_var, width=40)
        search_entry.grid(row=0, column=1, padx=5, sticky="ew")
        search_entry.bind("<KeyRelease>", self.filter_units)
        
        # Unit list with scrollbar
        list_frame = ttk.Frame(unit_frame)
        list_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=5)
        
        self.unit_list = tk.Listbox(list_frame, height=10)
        self.unit_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.unit_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.unit_list.config(yscrollcommand=scrollbar.set)
        self.unit_list.bind("<<ListboxSelect>>", self.unit_selected)
        
        # Selected unit info
        self.selected_info = tk.StringVar(value="No unit selected")
        ttk.Label(unit_frame, textvariable=self.selected_info).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)
        
        # Parameter entries
        param_frame = ttk.LabelFrame(main_frame, text="Unit Parameters", padding=10)
        param_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Button frame
        param_button_frame = ttk.Frame(param_frame)
        param_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add Import Parameters button
        ttk.Button(param_button_frame, text="Import Parameters from Parameters.txt", 
                  command=self.import_parameters).pack(side=tk.LEFT, padx=5)
        
        # Add Compare button
        self.compare_button = ttk.Button(param_button_frame, text="Revert to original", 
                                       command=self.toggle_comparison)
        self.compare_button.pack(side=tk.LEFT, padx=5)
        
        # Parameter container with scrollable frame
        self.param_container = ttk.Frame(param_frame)
        self.param_container.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable area for parameters
        self.canvas = tk.Canvas(self.param_container)
        scrollbar = ttk.Scrollbar(self.param_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Export and Clear buttons (with more space)
        button_frame = ttk.Frame(main_frame, padding=10)
        button_frame.pack(fill=tk.X, padx=5, pady=20)  # Extra padding for visibility
        
        # Add Clear button
        ttk.Button(button_frame, text="Clear Modifications", command=self.clear_modifications).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Save Modifications", command=self.export_modifications).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Export to Base64 clipboard", command=self.export_to_base64).pack(side=tk.RIGHT, padx=10)

    def log_message(self, message):
        """Add a message to the log area"""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        self.log_text.configure(state=tk.DISABLED)
    
    def toggle_comparison(self):
        """Toggle comparison view"""
        self.comparison_mode = not self.comparison_mode
        
        if self.comparison_mode:
            self.compare_button.config(text="Exit Comparison")
            self.log_message("Entered comparison view")
        else:
            self.compare_button.config(text="Compare with Original")
            self.log_message("Exited comparison view")
        
        # Refresh the parameter view
        if self.current_unit_id:
            self.create_parameter_fields(self.current_unit_params)

    def browse_translation(self):
        file = filedialog.askopenfilename(
            title="Select Translation File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file:
            self.translation_file.set(file)
            self.load_translation_data()

    def browse_unit_path(self):
        directory = filedialog.askdirectory(
            title="Select Unit Files Directory"
        )
        if directory:
            self.unit_files_path_var.set(directory)
            self.unit_files_path = directory
            self.log_message(f"Unit path set to: {directory}")

    def reload_data(self):
        self.load_translation_data()
        self.log_message("Data reloaded")

    def load_translation_data(self):
        file_path = self.translation_file.get()
        if not os.path.exists(file_path):
            self.log_message(f"Error: File not found: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translation_data = json.load(f)
            
            # Extract unit names and IDs
            self.unit_data = []
            units = self.translation_data.get("units", {}).get("names", {})
            
            for unit_id, name in units.items():
                # Create display text that includes both name and ID
                display_text = f"{name} ({unit_id})"
                # Store tuple: (display_text, unit_id, name)
                self.unit_data.append((display_text, unit_id, name))
            
            # Sort by name then ID
            self.unit_data.sort(key=lambda x: (x[2].lower(), x[1]))
            
            # Update unit list
            self.filter_units()
            self.log_message(f"Loaded translation data from: {file_path}")
            
        except Exception as e:
            self.log_message(f"Error: Failed to load translation file: {str(e)}")

    def filter_units(self, event=None):
        search_term = self.search_var.get().lower()
        
        self.unit_list.delete(0, tk.END)
        
        # Split search term into tokens
        tokens = search_term.split()
        
        for display_text, unit_id, name in self.unit_data:
            # Create a search string that combines name and ID
            search_string = f"{name.lower()} {unit_id.lower()}"
            
            # Check if all tokens are present in either name or ID
            match = True
            for token in tokens:
                if token not in search_string:
                    match = False
                    break
            
            if match:
                self.unit_list.insert(tk.END, display_text)
        
        if self.unit_list.size() > 0:
            self.unit_list.selection_set(0)
            self.unit_list.see(0)
            self.unit_selected()
        else:
            self.log_message(f"No units match search: '{search_term}'")

    def find_unit_file(self, unit_id):
        """Search for a unit file recursively in the unit directory"""
        for root, dirs, files in os.walk(self.unit_files_path):
            for file in files:
                if file.lower().endswith(".lua") and file.lower().startswith(unit_id.lower()):
                    return os.path.join(root, file)
        return None

    def extract_balanced_block(self, content, start_index):
        """Extract a balanced Lua block starting from the given index"""
        level = 1
        current_index = start_index + 1
        while current_index < len(content) and level > 0:
            if content[current_index] == '{':
                level += 1
            elif content[current_index] == '}':
                level -= 1
            current_index += 1
        return content[start_index:current_index].strip()

    def parse_lua_file(self, file_path):
        """Parse a Lua file to extract parameters with proper handling of complex structures"""
        parameters = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Create a working copy to remove complex blocks
                working_content = content
                complex_blocks = {}
                
                # First, extract complex parameters
                for complex_param in self.complex_params:
                    pattern = rf'{complex_param}\s*=\s*{{'
                    match = re.search(pattern, working_content, re.DOTALL | re.IGNORECASE)
                    if match:
                        start_index = match.end() - 1  # Position of the opening brace
                        complex_block = self.extract_balanced_block(working_content, start_index)
                        complex_blocks[complex_param] = complex_block
                        # Remove the complex block from the working content
                        working_content = working_content.replace(complex_block, "", 1)
                
                # Now extract top-level parameters from the modified content
                pattern = r'^\s*(\w+)\s*=\s*([^,\n{]+),?$'
                matches = re.findall(pattern, working_content, re.MULTILINE)
                
                for param, value in matches:
                    # Skip parameters that are part of complex blocks
                    if param in self.complex_params:
                        continue
                        
                    # Remove trailing comma if present
                    value = value.strip().rstrip(',')
                    
                    # Skip if value contains '{' (likely a complex structure)
                    if '{' in value:
                        continue
                    
                    # Try to convert to appropriate type
                    try:
                        if value.lower() == 'true':
                            parameters[param] = True
                        elif value.lower() == 'false':
                            parameters[param] = False
                        elif '.' in value:
                            parameters[param] = float(value)
                        else:
                            parameters[param] = int(value)
                    except ValueError:
                        # Handle string values (remove quotes)
                        if value.startswith('"') and value.endswith('"'):
                            parameters[param] = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            parameters[param] = value[1:-1]
                        else:
                            parameters[param] = value
                
                # Add the complex blocks back
                for param, block in complex_blocks.items():
                    parameters[param] = block
                
                return parameters
                
        except Exception as e:
            self.log_message(f"Error: Failed to parse unit file: {str(e)}")
            return {}

    def create_parameter_fields(self, parameters):
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Sort parameters alphabetically
        sorted_params = sorted(parameters.keys())
        
        # Create new fields
        self.entry_vars = {}
        for i, param in enumerate(sorted_params):
            # Determine frame style based on comparison
            frame_style = ""
            if self.comparison_mode:
                # Check if parameter is new or modified
                if param not in self.original_unit_params:
                    frame_style = 'New.TFrame'
                elif self.current_unit_params[param] != self.original_unit_params[param]:
                    frame_style = 'Modified.TFrame'
            
            # Create the frame for this parameter
            frame = ttk.Frame(self.scrollable_frame, padding=5, style=frame_style)
            frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Parameter name label
            param_label = ttk.Label(frame, text=f"{param}:", width=20, anchor="e")
            param_label.pack(side=tk.LEFT, padx=5)
            
            # Value display - create a frame for value widgets
            value_frame = ttk.Frame(frame)
            value_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # Use Text widget for complex parameters to handle multiline content
            if param in self.complex_params:
                # Create a frame for the text widget and button
                complex_frame = ttk.Frame(value_frame)
                complex_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
                
                # Create text widget
                text = tk.Text(complex_frame, height=8, width=60, wrap=tk.NONE)
                text.insert("1.0", parameters[param])
                text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
                
                # Create vertical scrollbar for the text widget
                text_scroll = ttk.Scrollbar(complex_frame, orient="vertical", command=text.yview)
                text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
                text.config(yscrollcommand=text_scroll.set)
                
                # Create horizontal scrollbar for the text widget
                text_scroll_h = ttk.Scrollbar(complex_frame, orient="horizontal", command=text.xview)
                text_scroll_h.pack(side=tk.BOTTOM, fill=tk.X)
                text.config(xscrollcommand=text_scroll_h.set)
                
                # Create format button
                format_btn = ttk.Button(frame, text="Format", 
                                       command=lambda p=param, t=text: self.format_complex_param(p, t))
                format_btn.pack(side=tk.RIGHT, padx=5)
                
                self.entry_vars[param] = text
            else:
                self.entry_vars[param] = tk.StringVar(value=str(parameters[param]))
                entry = ttk.Entry(value_frame, textvariable=self.entry_vars[param])
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # Add original value display in comparison mode
            if self.comparison_mode:
                # Create frame for original value display
                orig_frame = ttk.Frame(frame)
                orig_frame.pack(side=tk.RIGHT, padx=10)
                
                # Get original value
                orig_value = self.original_unit_params.get(param, "N/A")
                
                # Create label for original value
                orig_label = ttk.Label(orig_frame, text="Original:", width=8, anchor="e")
                orig_label.pack(side=tk.LEFT, padx=(10, 0))
                
                # Create display for original value
                if param in self.complex_params:
                    # For complex parameters, show a preview
                    preview = orig_value[:50] + "..." if len(str(orig_value)) > 50 else str(orig_value)
                    orig_value_label = ttk.Label(orig_frame, text=preview, width=30, 
                                               wraplength=200, foreground="gray")
                    orig_value_label.pack(side=tk.LEFT)
                else:
                    orig_value_label = ttk.Label(orig_frame, text=str(orig_value), 
                                               width=20, foreground="gray")
                    orig_value_label.pack(side=tk.LEFT)

    def format_complex_param(self, param, text_widget):
        """Format complex parameters with proper Lua indentation"""
        try:
            content = text_widget.get("1.0", tk.END).strip()
            
            # Basic formatting: add indentation and newlines
            formatted = ""
            indent_level = 0
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Handle closing braces
                if line.startswith('}'):
                    indent_level = max(0, indent_level - 1)
                
                # Add indentation
                indent = '\t' * indent_level
                formatted += f"{indent}{line}\n"
                
                # Handle opening braces
                if line.endswith('{'):
                    indent_level += 1
                # Handle closing braces in the middle of the line
                if '}' in line and not line.startswith('}'):
                    # Adjust indent level for inner braces
                    indent_level -= line.count('}')
            
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", formatted)
        except Exception as e:
            self.log_message(f"Format Error: Could not format parameter: {str(e)}")

    def unit_selected(self, event=None):
        selected_index = self.unit_list.curselection()
        if not selected_index:
            return
            
        display_text = self.unit_list.get(selected_index[0])
        
        # Find the unit ID for this display text
        for item in self.unit_data:
            if item[0] == display_text:
                self.current_unit_id = item[1]
                self.current_unit_name = item[2]
                break
        else:
            self.current_unit_id = None
        
        if not self.current_unit_id:
            self.log_message("Error: ID not found for selected unit")
            return
        
        # Update selected unit info
        self.selected_info.set(f"Selected Unit: {self.current_unit_name} (ID: {self.current_unit_id})")
        self.log_message(f"Selected unit: {self.current_unit_name} ({self.current_unit_id})")
        
        # Find and parse unit file
        unit_file = self.find_unit_file(self.current_unit_id)
        if not unit_file:
            self.log_message(f"Error: Unit file not found for: {self.current_unit_id}")
            return
            
        # Parse parameters from the unit file
        self.original_unit_params = self.parse_lua_file(unit_file)
        if not self.original_unit_params:
            self.log_message(f"Error: Failed to parse unit file: {unit_file}")
            return
            
        # Start with original parameters
        self.current_unit_params = self.original_unit_params.copy()
        self.create_parameter_fields(self.current_unit_params)
        
        # Load existing modifications if any
        if self.current_unit_id in self.modifications:
            for param, value in self.modifications[self.current_unit_id].items():
                if param in self.entry_vars:
                    if isinstance(self.entry_vars[param], tk.Text):
                        self.entry_vars[param].delete("1.0", tk.END)
                        self.entry_vars[param].insert("1.0", str(value))
                    else:
                        self.entry_vars[param].set(str(value))
                    # Update current unit params with modified value
                    self.current_unit_params[param] = value

    def load_export_data(self):
        """Load existing modifications from Export.txt if available"""
        if not os.path.exists("Export.txt"):
            self.log_message("No Export.txt file found")
            return
            
        try:
            with open("Export.txt", "r") as f:
                content = f.read()
                
            # Parse the Lua table format
            pattern = r'(\d+)\s*=\s*{([^}]*)'
            matches = re.findall(pattern, content, re.DOTALL)
            
            for unit_id, params_str in matches:
                unit_mods = {}
                
                # First, extract complex parameters
                complex_params = {}
                for complex_param in self.complex_params:
                    complex_pattern = rf'{complex_param}\s*=\s*({{.*?}})'
                    complex_match = re.search(complex_pattern, params_str, re.DOTALL)
                    if complex_match:
                        complex_value = complex_match.group(1).strip()
                        complex_params[complex_param] = complex_value
                        # Remove complex parameter from params_str
                        params_str = params_str.replace(complex_value, "", 1)
                
                # Now parse simple parameters
                param_pattern = r'(\w+)\s*=\s*([^,}]+)'
                param_matches = re.findall(param_pattern, params_str)
                
                for param, value in param_matches:
                    # Skip complex parameters we already handled
                    if param in self.complex_params:
                        continue
                        
                    # Convert to appropriate type
                    try:
                        if value.lower() == 'true':
                            unit_mods[param] = True
                        elif value.lower() == 'false':
                            unit_mods[param] = False
                        elif '.' in value:
                            unit_mods[param] = float(value)
                        else:
                            unit_mods[param] = int(value)
                    except ValueError:
                        # Handle string values
                        if value.startswith('"') and value.endswith('"'):
                            unit_mods[param] = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            unit_mods[param] = value[1:-1]
                        else:
                            unit_mods[param] = value
                
                # Add complex parameters back in
                unit_mods.update(complex_params)
                
                # Store in modifications dictionary
                self.modifications[unit_id] = unit_mods
                
            self.log_message(f"Loaded {len(matches)} unit modifications from Export.txt")
            
        except Exception as e:
            self.log_message(f"Import Error: Failed to load export data: {str(e)}")

    def clear_modifications(self):
        """Clear all modifications and delete Export.txt"""
        # Confirm with user
        if not messagebox.askyesno("Confirm Clear", "This will delete all modifications and Export.txt. Continue?"):
            return
            
        try:
            # Clear in-memory data
            self.modifications = {}
            self.added_parameters = set()
            
            # Clear current unit fields
            if self.current_unit_id:
                for param in self.current_unit_params:
                    if param in self.entry_vars:
                        if isinstance(self.entry_vars[param], tk.Text):
                            self.entry_vars[param].delete("1.0", tk.END)
                            self.entry_vars[param].insert("1.0", str(self.original_unit_params.get(param, "")))
                        else:
                            self.entry_vars[param].set(str(self.original_unit_params.get(param, "")))
            
            # Delete export file
            if os.path.exists("Export.txt"):
                os.remove("Export.txt")
                self.log_message("All modifications cleared and Export.txt deleted")
                messagebox.showinfo("Cleared", "All modifications cleared and Export.txt deleted")
            else:
                self.log_message("All modifications cleared")
                messagebox.showinfo("Cleared", "All modifications cleared")
                
        except Exception as e:
            self.log_message(f"Clear Error: Failed to clear: {str(e)}")
            messagebox.showerror("Clear Error", f"Failed to clear: {str(e)}")

    def import_parameters(self):
        """Import additional parameters from Parameters.txt"""
        if not self.current_unit_id:
            self.log_message("Error: Please select a unit first")
            messagebox.showerror("Error", "Please select a unit first")
            return
            
        file_path = filedialog.askopenfilename(
            title="Select Parameters File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                new_params = [line.strip() for line in f.readlines() if line.strip()]
                
            # Get current parameters
            current_params = set(self.current_unit_params.keys())
            
            # Find new parameters to add
            params_to_add = []
            for param in new_params:
                # Skip complex parameters and parameters that already exist
                if param in self.complex_params or param in current_params or param in self.added_parameters:
                    continue
                params_to_add.append(param)
                self.added_parameters.add(param)
                
            if not params_to_add:
                self.log_message("No new parameters to add")
                messagebox.showinfo("No New Parameters", "No new parameters to add")
                return
                
            # Add new parameters with default value 0
            for param in params_to_add:
                self.current_unit_params[param] = 0
                
            # Recreate fields to include new parameters
            self.create_parameter_fields(self.current_unit_params)
            
            # Load existing modifications if any
            if self.current_unit_id in self.modifications:
                for param, value in self.modifications[self.current_unit_id].items():
                    if param in self.entry_vars:
                        if isinstance(self.entry_vars[param], tk.Text):
                            self.entry_vars[param].delete("1.0", tk.END)
                            self.entry_vars[param].insert("1.0", str(value))
                        else:
                            self.entry_vars[param].set(str(value))
            
            self.log_message(f"Added {len(params_to_add)} new parameters")
            messagebox.showinfo("Parameters Added", f"Added {len(params_to_add)} new parameters")
            
        except Exception as e:
            self.log_message(f"Import Error: Failed to import parameters: {str(e)}")
            messagebox.showerror("Import Error", f"Failed to import parameters: {str(e)}")

    def export_modifications(self):
        if not self.current_unit_id:
            self.log_message("Error: Please select a unit first")
            messagebox.showerror("Error", "Please select a unit first")
            return
        
        # Collect modifications
        unit_mods = {}
        for param, widget in self.entry_vars.items():
            # Get current value from UI
            if isinstance(widget, tk.Text):
                current_value = widget.get("1.0", tk.END).strip()
            else:
                current_value = widget.get().strip()
                
            # Skip empty values
            if not current_value:
                continue
                
            # Get original value
            original_value = self.original_unit_params.get(param, "")
            
            # Handle complex parameters
            if param in self.complex_params:
                # Normalize whitespace for comparison
                norm_current = re.sub(r'\s+', ' ', current_value)
                norm_original = re.sub(r'\s+', ' ', str(original_value))
                if norm_current != norm_original:
                    unit_mods[param] = current_value
            else:
                # Handle simple parameters
                try:
                    # Try to convert to original type for comparison
                    if isinstance(original_value, bool):
                        # Handle boolean comparison
                        if original_value:
                            orig_str = "true"
                        else:
                            orig_str = "false"
                        if current_value.lower() != orig_str.lower():
                            unit_mods[param] = current_value
                    elif isinstance(original_value, (int, float)):
                        # Compare numerically
                        if '.' in current_value:
                            current_num = float(current_value)
                        else:
                            current_num = int(current_value)
                        if current_num != original_value:
                            unit_mods[param] = current_value
                    else:
                        # String comparison
                        if current_value != str(original_value):
                            unit_mods[param] = current_value
                except:
                    # Fallback to string comparison if conversion fails
                    if current_value != str(original_value):
                        unit_mods[param] = current_value
        
        # Check if we have any changes
        if not unit_mods:
            self.log_message("No changes to export")
            messagebox.showinfo("No Changes", "No modifications to export")
            return
        
        # Save to modifications dictionary
        self.modifications[self.current_unit_id] = unit_mods
        
        # Generate Lua output with proper formatting
        lua_output = "{\n"
        for i, (unit_id, params) in enumerate(self.modifications.items()):
            param_lines = []
            for param, value in params.items():
                if param in self.complex_params:
                    # Complex parameters are already formatted Lua blocks
                    param_lines.append(f"{param} = {value}")
                elif value in [True, False]:
                    # Boolean values
                    value_str = "true" if value else "false"
                    param_lines.append(f"{param} = {value_str}")
                elif isinstance(value, (int, float)):
                    # Numeric values
                    param_lines.append(f"{param} = {value}")
                elif value.lower() in ['true', 'false']:
                    # String representations of booleans
                    param_lines.append(f"{param} = {value}")
                elif value.replace('.', '', 1).isdigit() or (value.startswith('-') and value[1:].replace('.', '', 1).isdigit()):
                    # Numeric strings
                    param_lines.append(f"{param} = {value}")
                else:
                    # String values
                    if '"' in value:
                        value_str = f"'{value}'"
                    else:
                        value_str = f'"{value}"'
                    param_lines.append(f"{param} = {value_str}")
                
            param_str = ",\n\t\t".join(param_lines)
            lua_output += f"  {unit_id} = {{\n\t\t{param_str}\n\t}}"
            if i < len(self.modifications) - 1:
                lua_output += ","
            lua_output += "\n"
        lua_output += "}"
        
        # Write to file
        try:
            with open("Export.txt", "w") as f:
                f.write(lua_output)
            self.log_message("Modifications exported to Export.txt")
            messagebox.showinfo("Success", "Modifications exported to Export.txt")
        except Exception as e:
            self.log_message(f"Error: Failed to export: {str(e)}")
            messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def export_to_base64(self):
        """Export to Base64 with URL-safe encoding and CRLF newlines"""
        # First, ensure Export.txt exists
        if not os.path.exists("Export.txt"):
            # Try to export modifications first
            self.export_modifications()
            if not os.path.exists("Export.txt"):
                self.log_message("Error: No Export.txt file to encode")
                messagebox.showerror("Error", "No Export.txt file to encode")
                return
        
        try:
            # Read the content of Export.txt
            with open("Export.txt", "r", encoding="utf-8") as f:
                content = f.read()
            
            # Convert to CRLF line endings
            content = content.replace("\n", "\r\n")
            
            # Encode to Base64 URL-safe
            content_bytes = content.encode("utf-8")
            base64_bytes = base64.urlsafe_b64encode(content_bytes)
            base64_str = base64_bytes.decode("utf-8")
            
            # Remove padding (optional for URL safety)
            base64_str = base64_str.rstrip('=')
            
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(base64_str)
            
            self.log_message("Export.txt encoded to Base64 and copied to clipboard")
            messagebox.showinfo("Base64 Encoded", 
                               "Export.txt has been encoded to Base64 (URL-safe) and copied to clipboard!")
        
        except Exception as e:
            self.log_message(f"Encoding Error: Failed to encode to Base64: {str(e)}")
            messagebox.showerror("Encoding Error", f"Failed to encode to Base64: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = UnitModifierApp(root)
    root.mainloop()