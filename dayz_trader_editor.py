import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, colorchooser, simpledialog
import json
import os
import sys
import copy
import xml.etree.ElementTree as ET
import re
from pathlib import Path
from typing import Dict, List, Any


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running as script, use the directory of this file
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class MarketEditor:
    """Editor for Market JSON files (items in categories)"""
    
    def __init__(self, parent_frame: ttk.Frame, file_path: str = None, types_folder: str = None):
        self.parent_frame = parent_frame
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        self.current_item_index = None
        self.meta_entries = {}
        self.meta_widgets = {}
        self.types_folder = types_folder
        
        self.setup_ui()
        if file_path:
            self.load_file(file_path)
    
    def setup_ui(self):
        # Top panel: Market metadata with improved spacing
        meta_frame = ttk.LabelFrame(self.parent_frame, text="Market Metadata")
        meta_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.meta_entries = {}
        self.meta_widgets = {}
        
        # DisplayName
        row1 = ttk.Frame(meta_frame)
        row1.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row1, text="DisplayName:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        display_entry = ttk.Entry(row1, width=40)
        display_entry.pack(side=tk.LEFT, padx=5)
        self.meta_entries["DisplayName"] = display_entry
        
        # Icon
        row2 = ttk.Frame(meta_frame)
        row2.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row2, text="Icon:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        icon_combo = ttk.Combobox(row2, width=37, state="readonly")
        icon_combo.pack(side=tk.LEFT, padx=5)
        self.meta_entries["Icon"] = icon_combo
        # Load icon list immediately (from program directory)
        self.load_icon_list()
        
        # Color
        color_row = ttk.Frame(meta_frame)
        color_row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(color_row, text="Color:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        color_frame = ttk.Frame(color_row)
        color_frame.pack(side=tk.LEFT, padx=5)
        color_entry = ttk.Entry(color_frame, width=15)
        color_entry.pack(side=tk.LEFT, padx=2)
        color_button = ttk.Button(color_frame, text="Pick Color", command=lambda: self.pick_color(color_entry))
        color_button.pack(side=tk.LEFT, padx=2)
        self.meta_entries["Color"] = color_entry
        
        # IsExchange and InitStockPercent row
        row4 = ttk.Frame(meta_frame)
        row4.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row4, text="IsExchange:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        is_exchange_var = tk.BooleanVar()
        is_exchange_check = ttk.Checkbutton(row4, variable=is_exchange_var)
        is_exchange_check.pack(side=tk.LEFT, padx=5)
        self.meta_widgets["IsExchange"] = is_exchange_var
        
        ttk.Label(row4, text="InitStockPercent:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=20)
        stock_slider_frame = ttk.Frame(row4)
        stock_slider_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        stock_slider = tk.Scale(stock_slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                 resolution=0.1, width=15)
        stock_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        stock_label = ttk.Label(stock_slider_frame, text="0.0%", width=8)
        stock_label.pack(side=tk.LEFT, padx=5)
        
        def update_stock_label(val):
            stock_label.config(text=f"{float(val):.1f}%")
        
        stock_slider.config(command=update_stock_label)
        self.meta_widgets["InitStockPercent"] = stock_slider
        self.meta_widgets["InitStockPercent_label"] = stock_label
        
        # Left panel: Item list with modern styling
        list_frame = ttk.LabelFrame(self.parent_frame, text="Items")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(10, 5), pady=10)
        
        # Listbox with scrollbar
        listbox_container = ttk.Frame(list_frame)
        listbox_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.item_listbox = tk.Listbox(listbox_container, width=35, height=25, selectmode=tk.EXTENDED,
                                       font=("Segoe UI", 9), 
                                       bg="white",
                                       selectbackground="#4a90e2",
                                       selectforeground="white",
                                       borderwidth=1,
                                       relief=tk.SOLID,
                                       highlightthickness=1,
                                       highlightcolor="#4a90e2")
        self.item_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.item_listbox.bind('<<ListboxSelect>>', self.on_item_select)
        
        list_scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL, command=self.item_listbox.yview)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.item_listbox.config(yscrollcommand=list_scrollbar.set)
        
        # Add/Remove/Bulk Edit buttons with improved layout
        item_btn_frame = ttk.Frame(list_frame)
        item_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(item_btn_frame, text="➕ Add", command=self.add_item, style="Primary.TButton").pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(item_btn_frame, text="➖ Remove", command=self.remove_item).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(item_btn_frame, text="📝 Bulk Edit", command=self.bulk_edit_items).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # Right panel: Item editor
        editor_frame = ttk.LabelFrame(self.parent_frame, text="Item Properties")
        editor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=10)
        
        # Scrollable frame for properties
        canvas = tk.Canvas(editor_frame)
        scrollbar = ttk.Scrollbar(editor_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Property entries (will be populated when item is selected)
        self.property_entries = {}
        self.property_labels = {}
        
        # Common properties for Market items
        self.property_order = [
            "ClassName", "MaxPriceThreshold", "MinPriceThreshold", 
            "SellPricePercent", "MaxStockThreshold", "MinStockThreshold",
            "QuantityPercent"
        ]
        
        for prop in self.property_order:
            self.create_property_field(prop)
        
        # Arrays section
        arrays_frame = ttk.LabelFrame(self.scrollable_frame, text="Arrays")
        arrays_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # SpawnAttachments
        ttk.Label(arrays_frame, text="SpawnAttachments:").pack(anchor=tk.W)
        self.spawn_attachments_text = scrolledtext.ScrolledText(arrays_frame, height=3, width=50)
        self.spawn_attachments_text.pack(fill=tk.X, padx=5, pady=2)
        
        # Variants
        ttk.Label(arrays_frame, text="Variants:").pack(anchor=tk.W)
        self.variants_text = scrolledtext.ScrolledText(arrays_frame, height=3, width=50)
        self.variants_text.pack(fill=tk.X, padx=5, pady=2)
        
        # Save item button with primary styling
        save_btn_frame = ttk.Frame(self.scrollable_frame)
        save_btn_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Button(save_btn_frame, text="💾 Save Current Item", command=self.save_current_item, 
                  style="Primary.TButton").pack(fill=tk.X)
    
    def create_property_field(self, prop_name: str):
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        label = ttk.Label(frame, text=f"{prop_name}:", width=20, anchor=tk.W)
        label.pack(side=tk.LEFT)
        
        entry = ttk.Entry(frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add Replace button for ClassName field
        if prop_name == "ClassName":
            replace_btn = ttk.Button(frame, text="Replace", command=lambda: self.replace_classname(entry))
            replace_btn.pack(side=tk.LEFT, padx=5)
        
        self.property_labels[prop_name] = label
        self.property_entries[prop_name] = entry
    
    def load_file(self, file_path: str):
        self.file_path = file_path
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # Deep copy items to ensure no shared references
            self.data = copy.deepcopy(loaded_data)
            
            # Ensure each item has its own copy of arrays (redundant with deepcopy, but extra safety)
            if "Items" in self.data:
                for item in self.data["Items"]:
                    if "SpawnAttachments" in item:
                        item["SpawnAttachments"] = list(item["SpawnAttachments"])
                    if "Variants" in item:
                        item["Variants"] = list(item["Variants"])
            self.refresh_item_list()
            self.current_item_index = None  # Reset selection
            self.load_icon_list()  # Load icon list (always loads from program directory)
            self.load_metadata()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
    
    def load_icon_list(self):
        """Load icon list from icon.txt file in the program directory"""
        icon_file = get_resource_path("icon.txt")
        
        if os.path.isfile(icon_file):
            try:
                with open(icon_file, 'r', encoding='utf-8') as f:
                    icons = [line.strip() for line in f if line.strip()]
                if "Icon" in self.meta_entries:
                    self.meta_entries["Icon"]['values'] = sorted(icons)
            except Exception as e:
                pass  # Silently fail if icon file can't be read
    
    def replace_classname(self, classname_entry):
        """Open dialog to select a type name from types folder to replace ClassName"""
        if not self.types_folder or not os.path.isdir(self.types_folder):
            messagebox.showwarning("No Types Folder", "Please set the Types folder first.")
            return
        
        # Collect all class names from all XML files in types folder
        all_class_names = []
        
        xml_files = [f for f in os.listdir(self.types_folder) if f.endswith('.xml')]
        for xml_file in xml_files:
            file_path = os.path.join(self.types_folder, xml_file)
            try:
                # Try parsing as XML first
                try:
                    tree = ET.parse(file_path)
                    root = tree.getroot()
                    
                    # Find all type elements with name attribute
                    for elem in root.iter():
                        if 'name' in elem.attrib:
                            all_class_names.append(elem.attrib['name'])
                except ET.ParseError:
                    # If XML parsing fails, try regex extraction
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Match <type name="CLASSNAME"> pattern
                        pattern = r'<type\s+name="([^"]+)"'
                        matches = re.findall(pattern, content)
                        all_class_names.extend(matches)
            except Exception:
                continue  # Skip files that can't be read
        
        if not all_class_names:
            messagebox.showinfo("No Types", "No class names found in Types folder XML files.")
            return
        
        # Remove duplicates and sort
        all_class_names = sorted(list(set(all_class_names)))
        
        # Create selection dialog
        dialog = tk.Toplevel(self.parent_frame.winfo_toplevel())
        dialog.title("Select Class Name")
        dialog.geometry("400x500")
        dialog.transient(self.parent_frame.winfo_toplevel())
        dialog.grab_set()
        
        # Search/filter frame
        search_frame = ttk.Frame(dialog, padding=10)
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        search_entry.focus()
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(dialog, padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        listbox = tk.Listbox(list_frame, height=20)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate listbox
        def populate_listbox(filter_text=""):
            listbox.delete(0, tk.END)
            filter_lower = filter_text.lower()
            for name in all_class_names:
                if not filter_text or filter_lower in name.lower():
                    listbox.insert(tk.END, name)
        
        populate_listbox()
        
        # Search functionality
        def on_search_change(*args):
            populate_listbox(search_var.get())
        
        search_var.trace('w', on_search_change)
        
        # Double-click to select
        def on_double_click(event):
            selection = listbox.curselection()
            if selection:
                selected_name = listbox.get(selection[0])
                classname_entry.delete(0, tk.END)
                classname_entry.insert(0, selected_name)
                dialog.destroy()
        
        listbox.bind('<Double-Button-1>', on_double_click)
        
        # Enter key to select
        def on_enter(event):
            selection = listbox.curselection()
            if selection:
                selected_name = listbox.get(selection[0])
                classname_entry.delete(0, tk.END)
                classname_entry.insert(0, selected_name)
                dialog.destroy()
        
        listbox.bind('<Return>', on_enter)
        search_entry.bind('<Return>', lambda e: listbox.focus())
        
        # Buttons
        btn_frame = ttk.Frame(dialog, padding=10)
        btn_frame.pack(fill=tk.X)
        
        def select_and_close():
            selection = listbox.curselection()
            if selection:
                selected_name = listbox.get(selection[0])
                classname_entry.delete(0, tk.END)
                classname_entry.insert(0, selected_name)
                dialog.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select a class name.")
        
        ttk.Button(btn_frame, text="Select", command=select_and_close).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def pick_color(self, color_entry):
        """Open color picker and convert to HEX format (RGB + Alpha)"""
        color = colorchooser.askcolor(title="Pick Color")
        if color[1]:  # color[1] is the hex string like #RRGGBB
            # Convert from #RRGGBB to RRGGBBFF format (add alpha FF)
            hex_color = color[1][1:].upper() + "FF"  # Remove #, uppercase, add FF for alpha
            color_entry.delete(0, tk.END)
            color_entry.insert(0, hex_color)
    
    def load_metadata(self):
        """Load metadata fields from data"""
        if "DisplayName" in self.meta_entries:
            self.meta_entries["DisplayName"].delete(0, tk.END)
            self.meta_entries["DisplayName"].insert(0, self.data.get("DisplayName", ""))
        
        if "Icon" in self.meta_entries:
            self.meta_entries["Icon"].set(self.data.get("Icon", ""))
        
        if "Color" in self.meta_entries:
            self.meta_entries["Color"].delete(0, tk.END)
            self.meta_entries["Color"].insert(0, self.data.get("Color", ""))
        
        if "IsExchange" in self.meta_widgets:
            is_exchange = self.data.get("IsExchange", 0)
            self.meta_widgets["IsExchange"].set(bool(is_exchange))
        
        if "InitStockPercent" in self.meta_widgets:
            init_stock = self.data.get("InitStockPercent", 75.0)
            self.meta_widgets["InitStockPercent"].set(float(init_stock))
            # Update label
            if "InitStockPercent_label" in self.meta_widgets:
                self.meta_widgets["InitStockPercent_label"].config(text=f"{float(init_stock):.1f}%")
    
    def refresh_item_list(self):
        self.item_listbox.delete(0, tk.END)
        if "Items" in self.data:
            for item in self.data["Items"]:
                class_name = item.get("ClassName", "Unknown")
                self.item_listbox.insert(tk.END, class_name)
    
    def on_item_select(self, event):
        # Get the new selection first
        selection = self.item_listbox.curselection()
        if not selection:
            # If selection was cleared, don't update but don't save either
            return
        
        new_index = selection[0]
        
        # Only save the previous item if we're switching to a different item
        # Don't update listbox during switch to avoid interfering with selection
        if self.current_item_index is not None and self.current_item_index != new_index:
            self.save_current_item(update_listbox=False)
        
        # Now set the new selection
        index = new_index
        self.current_item_index = index
        
        # Make sure index is valid
        if index >= len(self.data["Items"]):
            return
        
        item = self.data["Items"][index]
        
        # Populate property fields
        for prop in self.property_order:
            value = item.get(prop, "")
            if value is None:
                value = ""
            self.property_entries[prop].delete(0, tk.END)
            self.property_entries[prop].insert(0, str(value))
        
        # Populate arrays - ensure we're working with a copy
        self.spawn_attachments_text.delete(1.0, tk.END)
        attachments = item.get("SpawnAttachments", [])
        if attachments:
            self.spawn_attachments_text.insert(1.0, "\n".join(attachments))
        
        self.variants_text.delete(1.0, tk.END)
        variants = item.get("Variants", [])
        if variants:
            self.variants_text.insert(1.0, "\n".join(variants))
    
    def add_item(self):
        # Create a completely new item dictionary (not a reference)
        new_item = {
            "ClassName": "new_item",
            "MaxPriceThreshold": 1000,
            "MinPriceThreshold": 500,
            "SellPricePercent": -1.0,
            "MaxStockThreshold": 500,
            "MinStockThreshold": 1,
            "QuantityPercent": -1,
            "SpawnAttachments": [],  # New list
            "Variants": []  # New list
        }
        
        if "Items" not in self.data:
            self.data["Items"] = []
        
        self.data["Items"].append(new_item)
        self.refresh_item_list()
        self.item_listbox.selection_set(len(self.data["Items"]) - 1)
        self.item_listbox.event_generate("<<ListboxSelect>>")
    
    def remove_item(self):
        if self.current_item_index is None:
            return
        
        if messagebox.askyesno("Confirm", "Delete this item?"):
            self.data["Items"].pop(self.current_item_index)
            self.current_item_index = None
            self.refresh_item_list()
            # Clear fields
            for entry in self.property_entries.values():
                entry.delete(0, tk.END)
            self.spawn_attachments_text.delete(1.0, tk.END)
            self.variants_text.delete(1.0, tk.END)
    
    def bulk_edit_items(self):
        """Open bulk edit dialog for selected items"""
        selections = self.item_listbox.curselection()
        if not selections:
            messagebox.showwarning("No Selection", "Please select one or more items to edit.")
            return
        
        if len(selections) == 1:
            messagebox.showinfo("Info", "Please select multiple items for bulk edit (Ctrl+Click or Shift+Click).")
            return
        
        # Create bulk edit dialog
        dialog = tk.Toplevel(self.parent_frame.winfo_toplevel())
        dialog.title("Bulk Edit Items")
        dialog.geometry("500x600")
        dialog.transient(self.parent_frame.winfo_toplevel())
        dialog.grab_set()
        
        # Frame for content
        content_frame = ttk.Frame(dialog, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(content_frame, text=f"Editing {len(selections)} item(s)", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Label(content_frame, text="Leave fields empty to keep current values.", font=("Arial", 9)).pack(anchor=tk.W, pady=2)
        
        # Scrollable frame for property fields
        canvas = tk.Canvas(content_frame)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bulk edit property entries
        bulk_entries = {}
        editable_props = ["MaxPriceThreshold", "MinPriceThreshold", "SellPricePercent", 
                         "MaxStockThreshold", "MinStockThreshold", "QuantityPercent"]
        
        # Special handling for SellPricePercent (slider) and QuantityPercent (prefilled)
        sell_price_slider = None
        sell_price_label = None
        
        for prop in editable_props:
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            
            label = ttk.Label(frame, text=f"{prop}:", width=20, anchor=tk.W)
            label.pack(side=tk.LEFT)
            
            if prop == "SellPricePercent":
                # Use a slider for SellPricePercent
                slider_frame = ttk.Frame(frame)
                slider_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                # Slider from 0 to 100 - constrain width so it doesn't drag off UI
                slider = tk.Scale(slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                  resolution=1, width=15)
                slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                slider.set(0)  # Default to 0 (which maps to -1)
                
                # Label to show current value
                sell_price_label = ttk.Label(slider_frame, text="0% (-1.0)", width=15)
                sell_price_label.pack(side=tk.LEFT, padx=5)
                
                # Update label when slider changes
                def update_sell_price_label(val):
                    slider_val = int(float(val))
                    if slider_val == 0:
                        sell_price_label.config(text="0% (-1.0)")
                    else:
                        # Map 1-100 to 0.1-1.0
                        # Linear mapping: 1% = 0.1, 100% = 1.0
                        mapped_value = 0.1 + (slider_val - 1) * (1.0 - 0.1) / (100 - 1)
                        sell_price_label.config(text=f"{slider_val}% ({mapped_value:.2f})")
                
                slider.config(command=update_sell_price_label)
                bulk_entries[prop] = slider
                sell_price_slider = slider
            else:
                entry = ttk.Entry(frame)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                # Prefill QuantityPercent with -1
                if prop == "QuantityPercent":
                    entry.insert(0, "-1")
                
                bulk_entries[prop] = entry
        
        # Buttons
        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        def apply_bulk_edit():
            # Save current item first (don't update listbox, we'll refresh after)
            if self.current_item_index is not None:
                self.save_current_item(update_listbox=False)
            
            # Apply changes to all selected items
            items_modified = 0
            for index in selections:
                item = self.data["Items"][index]
                item_modified = False
                
                for prop, widget in bulk_entries.items():
                    if prop == "SellPricePercent":
                        # Handle slider: 0 = -1, 1-100 = 0.1 to 1.0
                        slider_val = int(float(widget.get()))
                        if slider_val == 0:
                            item[prop] = -1.0
                        else:
                            # Map 1-100 to 0.1-1.0 (linear mapping: 1% = 0.1, 100% = 1.0)
                            item[prop] = 0.1 + (slider_val - 1) * (1.0 - 0.1) / (100 - 1)
                        item_modified = True
                    else:
                        # Handle text entries
                        value = widget.get().strip()
                        if value:  # Only update if value provided
                            try:
                                if prop in ["MaxPriceThreshold", "MinPriceThreshold", "MaxStockThreshold", 
                                           "MinStockThreshold"]:
                                    item[prop] = int(value)
                                elif prop == "QuantityPercent":
                                    item[prop] = int(float(value))
                                item_modified = True
                            except ValueError:
                                pass  # Skip invalid values
                
                if item_modified:
                    items_modified += 1
            
            # Clear current selection to prevent confusion
            self.current_item_index = None
            self.refresh_item_list()
            dialog.destroy()
            if items_modified > 0:
                messagebox.showinfo("Success", f"Bulk edit applied to {items_modified} item(s).")
            else:
                messagebox.showinfo("Info", "No changes were applied. Make sure to enter values in the fields.")
        
        ttk.Button(btn_frame, text="Apply", command=apply_bulk_edit).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def save_current_item(self, update_listbox=True):
        """Save current item being edited
        
        Args:
            update_listbox: If False, don't update listbox display (useful when switching items)
        """
        if self.current_item_index is None:
            return
        
        # Make sure we're working with the correct item index
        if self.current_item_index >= len(self.data["Items"]):
            return
        
        item = self.data["Items"][self.current_item_index]
        
        # Save properties - always update with what's in the Entry widget
        for prop in self.property_order:
            value = self.property_entries[prop].get().strip()
            # Try to convert to appropriate type
            try:
                if prop in ["MaxPriceThreshold", "MinPriceThreshold", "MaxStockThreshold", 
                           "MinStockThreshold"]:
                    # For integers, use 0 if empty
                    item[prop] = int(value) if value else 0
                elif prop == "SellPricePercent":
                    # For floats, use -1.0 if empty (common default)
                    item[prop] = float(value) if value else -1.0
                elif prop == "QuantityPercent":
                    # For integers, use -1 if empty (common default)
                    item[prop] = int(float(value)) if value else -1
                else:
                    # For strings like ClassName, use empty string if empty
                    item[prop] = value
            except ValueError:
                # If conversion fails, keep as string or default
                if prop in ["MaxPriceThreshold", "MinPriceThreshold", "MaxStockThreshold", 
                           "MinStockThreshold"]:
                    item[prop] = 0
                elif prop == "SellPricePercent":
                    item[prop] = -1.0
                elif prop == "QuantityPercent":
                    item[prop] = -1
                else:
                    item[prop] = value
        
        # Save arrays - create new lists to avoid shared references
        attachments_text = self.spawn_attachments_text.get(1.0, tk.END).strip()
        item["SpawnAttachments"] = [a.strip() for a in attachments_text.split("\n") if a.strip()]
        
        variants_text = self.variants_text.get(1.0, tk.END).strip()
        item["Variants"] = [v.strip() for v in variants_text.split("\n") if v.strip()]
        
        # Update the listbox display if ClassName changed (but don't interfere with selection)
        # Only update if we have a valid index and the name actually changed
        if update_listbox and "ClassName" in item and self.current_item_index is not None:
            class_name = item["ClassName"]
            # Check if the displayed name needs updating
            if self.current_item_index < self.item_listbox.size():
                try:
                    current_display = self.item_listbox.get(self.current_item_index)
                    if current_display != class_name:
                        # Temporarily unbind to prevent event recursion during update
                        self.item_listbox.unbind('<<ListboxSelect>>')
                        # Store current selection to restore it
                        current_selection = self.item_listbox.curselection()
                        self.item_listbox.delete(self.current_item_index)
                        self.item_listbox.insert(self.current_item_index, class_name)
                        # Restore the selection
                        if current_selection:
                            self.item_listbox.selection_set(current_selection[0])
                        # Rebind the event handler
                        self.item_listbox.bind('<<ListboxSelect>>', self.on_item_select)
                except tk.TclError:
                    # If listbox was destroyed or index is invalid, just rebind
                    self.item_listbox.bind('<<ListboxSelect>>', self.on_item_select)
    
    def save_file(self):
        """Save the entire file"""
        if not self.file_path:
            return False
        
        # Save current item first (and update listbox display)
        if self.current_item_index is not None:
            self.save_current_item(update_listbox=True)
        
        # Save metadata
        if "DisplayName" in self.meta_entries:
            self.data["DisplayName"] = self.meta_entries["DisplayName"].get().strip()
        
        if "Icon" in self.meta_entries:
            self.data["Icon"] = self.meta_entries["Icon"].get().strip()
        
        if "Color" in self.meta_entries:
            self.data["Color"] = self.meta_entries["Color"].get().strip().upper()
        
        if "IsExchange" in self.meta_widgets:
            self.data["IsExchange"] = 1 if self.meta_widgets["IsExchange"].get() else 0
        
        if "InitStockPercent" in self.meta_widgets:
            self.data["InitStockPercent"] = float(self.meta_widgets["InitStockPercent"].get())
        
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
            return False


class TraderEditor:
    """Editor for Trader JSON files (categories and items)"""
    
    def __init__(self, parent_frame: ttk.Frame, file_path: str = None, market_folder: str = None):
        self.parent_frame = parent_frame
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        self.market_folder = market_folder
        
        self.setup_ui()
        if file_path:
            self.load_file(file_path)
    
    def setup_ui(self):
        # Top frame for metadata
        meta_frame = ttk.LabelFrame(self.parent_frame, text="Trader Metadata")
        meta_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.meta_entries = {}
        meta_fields = [
            "DisplayName", "MinRequiredReputation", "MaxRequiredReputation",
            "RequiredFaction", "RequiredCompletedQuestID", "TraderIcon"
        ]
        
        for i, field in enumerate(meta_fields):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(meta_frame, text=f"{field}:").grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(meta_frame, width=30)
            entry.grid(row=row, column=col+1, sticky=tk.EW, padx=5, pady=2)
            self.meta_entries[field] = entry
        
        meta_frame.grid_columnconfigure(1, weight=1)
        meta_frame.grid_columnconfigure(3, weight=1)
        
        # Categories frame
        categories_frame = ttk.LabelFrame(self.parent_frame, text="Categories")
        categories_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(categories_frame, text="Category List:").pack(anchor=tk.W)
        
        cat_list_frame = ttk.Frame(categories_frame)
        cat_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.categories_listbox = tk.Listbox(cat_list_frame, height=10)
        self.categories_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        cat_scrollbar = ttk.Scrollbar(cat_list_frame, orient=tk.VERTICAL, command=self.categories_listbox.yview)
        cat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.categories_listbox.config(yscrollcommand=cat_scrollbar.set)
        
        cat_btn_frame = ttk.Frame(categories_frame)
        cat_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(cat_btn_frame, text="Add Category:").pack(side=tk.LEFT, padx=2)
        self.category_combo = ttk.Combobox(cat_btn_frame, width=28, state="readonly")
        self.category_combo.pack(side=tk.LEFT, padx=2)
        self.refresh_category_list()
        ttk.Button(cat_btn_frame, text="Add", command=self.add_category).pack(side=tk.LEFT, padx=2)
        ttk.Button(cat_btn_frame, text="Remove Selected", command=self.remove_category).pack(side=tk.LEFT, padx=2)
        
        # Items frame
        items_frame = ttk.LabelFrame(self.parent_frame, text="Items (Optional)")
        items_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(items_frame, text="Item ClassName: Value (one per line, format: className:value)").pack(anchor=tk.W)
        
        self.items_text = scrolledtext.ScrolledText(items_frame, height=8, width=60)
        self.items_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def load_file(self, file_path: str):
        self.file_path = file_path
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.refresh_ui()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
    
    def refresh_ui(self):
        # Refresh category dropdown
        self.refresh_category_list()
        
        # Load metadata
        for field, entry in self.meta_entries.items():
            value = self.data.get(field, "")
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
        
        # Load categories
        self.categories_listbox.delete(0, tk.END)
        if "Categories" in self.data:
            for cat in self.data["Categories"]:
                self.categories_listbox.insert(tk.END, cat)
        
        # Load items
        self.items_text.delete(1.0, tk.END)
        if "Items" in self.data and isinstance(self.data["Items"], dict):
            items_lines = [f"{k}: {v}" for k, v in self.data["Items"].items()]
            self.items_text.insert(1.0, "\n".join(items_lines))
    
    def refresh_category_list(self):
        """Refresh the category dropdown with available market files"""
        if not self.market_folder or not os.path.isdir(self.market_folder):
            self.category_combo['values'] = []
            return
        
        json_files = [f for f in os.listdir(self.market_folder) if f.endswith('.json')]
        # Remove .json extension and sort
        categories = sorted([f[:-5] for f in json_files])
        self.category_combo['values'] = categories
    
    def add_category(self):
        category = self.category_combo.get().strip()
        if not category:
            return
        
        if "Categories" not in self.data:
            self.data["Categories"] = []
        
        if category not in self.data["Categories"]:
            self.data["Categories"].append(category)
            self.categories_listbox.insert(tk.END, category)
            self.category_combo.set("")
    
    def remove_category(self):
        selection = self.categories_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        category = self.categories_listbox.get(index)
        
        if "Categories" in self.data:
            if category in self.data["Categories"]:
                self.data["Categories"].remove(category)
                self.categories_listbox.delete(index)
    
    def save_file(self):
        """Save the entire file"""
        if not self.file_path:
            return False
        
        try:
            # Save metadata
            for field, entry in self.meta_entries.items():
                value = entry.get().strip()
                if field in ["MinRequiredReputation", "MaxRequiredReputation", "RequiredCompletedQuestID"]:
                    try:
                        self.data[field] = int(value) if value else 0
                    except ValueError:
                        self.data[field] = value
                else:
                    self.data[field] = value
            
            # Save categories (already in data)
            
            # Save items
            items_text = self.items_text.get(1.0, tk.END).strip()
            if items_text:
                items_dict = {}
                for line in items_text.split("\n"):
                    if ":" in line:
                        parts = line.split(":", 1)
                        key = parts[0].strip()
                        value = parts[1].strip()
                        try:
                            items_dict[key] = int(value)
                        except ValueError:
                            items_dict[key] = value
                self.data["Items"] = items_dict
            elif "Items" in self.data:
                # Keep existing items if text is empty
                pass
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
            return False


class DayZTraderEditor:
    """Main application window"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("DayZ Trader Editor")
        self.root.geometry("1200x800")
        
        # Set application icon
        self.set_icon()
        
        # Configure modern styling
        self.setup_style()
        
        self.market_folder = None
        self.traders_folder = None
        self.types_folder = None
        self.all_types_class_names = []  # Store all class names for filtering
        self.current_market_editor = None
        self.current_trader_editor = None
        self.project_file_path = None
        
        self.setup_ui()
        
        # Try to load default project file if it exists
        self.load_default_project()
    
    def set_icon(self):
        """Load and set the application icon"""
        try:
            icon_path = get_resource_path("icon.png")
            
            if os.path.isfile(icon_path):
                # Load icon using PhotoImage for PNG files
                icon_image = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon_image)
                # Keep a reference to prevent garbage collection
                self.icon_image = icon_image
        except Exception as e:
            # Silently fail if icon can't be loaded
            pass
    
    def setup_style(self):
        """Configure modern, snazzy styling for the application"""
        style = ttk.Style()
        
        # Use 'clam' theme as it supports more customization
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'vista' in available_themes:
            style.theme_use('vista')
        
        # Modern color scheme - subtle blues and grays
        bg_color = "#f0f0f0"
        frame_bg = "#ffffff"
        accent_color = "#5dade2"
        
        # Configure root window background
        self.root.configure(bg=bg_color)
        
        # Configure Frame styles
        style.configure("TFrame", background=bg_color)
        style.configure("Card.TFrame", background=frame_bg, relief=tk.RAISED, borderwidth=1)
        
        # Configure LabelFrame styles
        style.configure("TLabelframe", background=frame_bg, bordervidth=1)
        style.configure("TLabelframe.Label", background=frame_bg, 
                       font=("Segoe UI", 10, "bold"), foreground="#2c3e50")
        
        # Configure Button styles - use theme colors but ensure readability
        style.configure("TButton", 
                       padding=(12, 6),
                       font=("Segoe UI", 9, "normal"))
        
        # Primary action button style with green color
        style.configure("Primary.TButton",
                       background="#27ae60",
                       foreground="white",
                       padding=(12, 6),
                       font=("Segoe UI", 9, "bold"))
        style.map("Primary.TButton",
                 background=[("active", "#229954"), ("pressed", "#1e8449")],
                 foreground=[("active", "white"), ("pressed", "white")])
        
        # Configure Label styles - don't set background, let it inherit from parent frame
        style.configure("TLabel", foreground="#2c3e50", 
                       font=("Segoe UI", 9))
        style.configure("Heading.TLabel", foreground="#34495e",
                       font=("Segoe UI", 11, "bold"))
        style.configure("Info.TLabel", foreground="#7f8c8d",
                       font=("Segoe UI", 8))
        
        # Configure Entry styles
        style.configure("TEntry",
                       fieldbackground="white",
                       borderwidth=1,
                       relief=tk.SOLID,
                       padding=5)
        style.map("TEntry",
                 fieldbackground=[("focus", "#f8f9fa")],
                 bordercolor=[("focus", accent_color)])
        
        # Configure Combobox styles
        style.configure("TCombobox",
                       fieldbackground="white",
                       borderwidth=1,
                       padding=5)
        style.map("TCombobox",
                 fieldbackground=[("focus", "#f8f9fa")],
                 bordercolor=[("focus", accent_color)])
        
        # Configure Notebook (tabs) styles
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure("TNotebook.Tab",
                       padding=(20, 10),
                       background="#e8e8e8",
                       foreground="#555555",
                       font=("Segoe UI", 9, "normal"))
        style.map("TNotebook.Tab",
                 background=[("selected", frame_bg), ("active", "#d0d0d0")],
                 foreground=[("selected", "#2c3e50"), ("active", "#333333")],
                 expand=[("selected", (1, 1, 1, 0))])
        
        # Configure Listbox - we'll style tk.Listbox separately via root config
        # Since tk.Listbox doesn't use ttk.Style, we configure it via options
        
        # Configure Scrollbar styles
        style.configure("TScrollbar",
                       background="#d0d0d0",
                       troughcolor=bg_color,
                       borderwidth=0,
                       arrowcolor="#666666",
                       width=12)
        style.map("TScrollbar",
                 background=[("active", "#b0b0b0")])
        
        # Configure Checkbutton styles - let background inherit
        style.configure("TCheckbutton",
                       foreground="#2c3e50",
                       font=("Segoe UI", 9))
        
        # Configure Scale (slider) styles
        style.configure("TScale",
                       background=bg_color,
                       troughcolor="#d0d0d0",
                       sliderthickness=20)
    
    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Set Market Folder", command=self.set_market_folder)
        file_menu.add_command(label="Set Traders Folder", command=self.set_traders_folder)
        file_menu.add_command(label="Set Types Folder", command=self.set_types_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Save Project", command=self.save_project)
        file_menu.add_command(label="Load Project", command=self.load_project)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Remove Duplicates", command=self.remove_duplicates)
        
        # Top frame for folder selection with card-style background
        folder_frame = ttk.Frame(self.root, style="Card.TFrame")
        folder_frame.pack(fill=tk.X, padx=10, pady=10, ipady=10)
        
        # Button container
        button_frame = ttk.Frame(folder_frame)
        button_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(button_frame, text="📁 Market", command=self.set_market_folder).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="📁 Traders", command=self.set_traders_folder).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="📁 Types", command=self.set_types_folder).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="💾 Save", command=self.save_current, style="Primary.TButton").pack(side=tk.LEFT, padx=3)
        
        # Status labels with better styling
        status_frame = ttk.Frame(folder_frame)
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15)
        
        self.market_label = ttk.Label(status_frame, text="Market: Not set", style="Info.TLabel")
        self.market_label.pack(side=tk.LEFT, padx=8)
        
        self.traders_label = ttk.Label(status_frame, text="Traders: Not set", style="Info.TLabel")
        self.traders_label.pack(side=tk.LEFT, padx=8)
        
        self.types_label = ttk.Label(status_frame, text="Types: Not set", style="Info.TLabel")
        self.types_label.pack(side=tk.LEFT, padx=8)
        
        # Notebook for tabs with modern styling
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Market tab
        self.market_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.market_frame, text="Market Editor")
        
        market_select_frame = ttk.Frame(self.market_frame)
        market_select_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(market_select_frame, text="Market File:", style="Heading.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        self.market_file_var = tk.StringVar()
        self.market_file_combo = ttk.Combobox(market_select_frame, textvariable=self.market_file_var, 
                                               state="readonly", width=45)
        self.market_file_combo.pack(side=tk.LEFT, padx=5)
        self.market_file_combo.bind("<<ComboboxSelected>>", self.load_market_file)
        
        ttk.Button(market_select_frame, text="🔄 Refresh", command=self.refresh_market_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(market_select_frame, text="➕ New File", command=self.new_market_file, style="Primary.TButton").pack(side=tk.LEFT, padx=5)
        
        self.market_editor_frame = ttk.Frame(self.market_frame)
        self.market_editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Trader tab
        self.trader_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.trader_frame, text="Trader Editor")
        
        trader_select_frame = ttk.Frame(self.trader_frame)
        trader_select_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(trader_select_frame, text="Trader File:", style="Heading.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        self.trader_file_var = tk.StringVar()
        self.trader_file_combo = ttk.Combobox(trader_select_frame, textvariable=self.trader_file_var,
                                               state="readonly", width=45)
        self.trader_file_combo.pack(side=tk.LEFT, padx=5)
        self.trader_file_combo.bind("<<ComboboxSelected>>", self.load_trader_file)
        
        ttk.Button(trader_select_frame, text="🔄 Refresh", command=self.refresh_trader_files).pack(side=tk.LEFT, padx=5)
        
        self.trader_editor_frame = ttk.Frame(self.trader_frame)
        self.trader_editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Types tab
        self.types_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.types_frame, text="Types Viewer")
        
        types_select_frame = ttk.Frame(self.types_frame)
        types_select_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(types_select_frame, text="XML File:", style="Heading.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        self.types_file_var = tk.StringVar()
        self.types_file_combo = ttk.Combobox(types_select_frame, textvariable=self.types_file_var,
                                               state="readonly", width=40)
        self.types_file_combo.pack(side=tk.LEFT, padx=5)
        self.types_file_combo.bind("<<ComboboxSelected>>", self.load_types_file)
        
        ttk.Button(types_select_frame, text="🔄 Refresh", command=self.refresh_types_files).pack(side=tk.LEFT, padx=5)
        
        # Add to market file section
        add_frame = ttk.Frame(self.types_frame)
        add_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(add_frame, text="Add To:", style="Heading.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        self.types_market_file_var = tk.StringVar()
        self.types_market_file_combo = ttk.Combobox(add_frame, textvariable=self.types_market_file_var,
                                                      state="readonly", width=40)
        self.types_market_file_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(add_frame, text="➕ Add", command=self.add_types_to_market, style="Primary.TButton").pack(side=tk.LEFT, padx=5)
        
        # Filter section
        filter_frame = ttk.Frame(self.types_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(filter_frame, text="🔍 Filter:", style="Heading.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        self.types_filter_var = tk.StringVar()
        self.types_filter_entry = ttk.Entry(filter_frame, textvariable=self.types_filter_var, width=50)
        self.types_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.types_filter_var.trace('w', lambda *args: self.filter_types_list())
        
        ttk.Button(filter_frame, text="Clear", command=self.clear_types_filter).pack(side=tk.LEFT, padx=5)
        
        # Class names list (with extended selection for bulk selection)
        types_list_frame = ttk.LabelFrame(self.types_frame, text="Class Names (Double-click to copy, Ctrl+Click/Shift+Click to select multiple)")
        types_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        listbox_container = ttk.Frame(types_list_frame)
        listbox_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.types_listbox = tk.Listbox(listbox_container, height=25, selectmode=tk.EXTENDED,
                                        font=("Segoe UI", 9),
                                        bg="white",
                                        selectbackground="#4a90e2",
                                        selectforeground="white",
                                        borderwidth=1,
                                        relief=tk.SOLID,
                                        highlightthickness=1,
                                        highlightcolor="#4a90e2")
        self.types_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.types_listbox.bind('<Double-Button-1>', self.copy_type_name)
        
        types_scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL, command=self.types_listbox.yview)
        types_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.types_listbox.config(yscrollcommand=types_scrollbar.set)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def set_market_folder(self):
        folder = filedialog.askdirectory(title="Select Market Folder")
        if folder:
            self.market_folder = folder
            self.market_label.config(text=f"Market Folder: {os.path.basename(folder)}")
            self.refresh_market_files()
            self.refresh_types_market_files()  # Refresh market dropdown in Types tab
            self.status_var.set(f"Market folder set: {folder}")
            # Refresh trader editor category list if it exists
            if self.current_trader_editor:
                self.current_trader_editor.market_folder = folder
                self.current_trader_editor.refresh_category_list()
            # Auto-save to project file if one is set
            if self.project_file_path:
                self.save_project(silent=True)
    
    def set_traders_folder(self):
        folder = filedialog.askdirectory(title="Select Traders Folder")
        if folder:
            self.traders_folder = folder
            self.traders_label.config(text=f"Traders Folder: {os.path.basename(folder)}")
            self.refresh_trader_files()
            self.status_var.set(f"Traders folder set: {folder}")
            # Auto-save to project file if one is set
            if self.project_file_path:
                self.save_project(silent=True)
    
    def set_types_folder(self):
        folder = filedialog.askdirectory(title="Select Types Folder")
        if folder:
            self.types_folder = folder
            self.types_label.config(text=f"Types Folder: {os.path.basename(folder)}")
            self.refresh_types_files()
            self.status_var.set(f"Types folder set: {folder}")
            # Update market editor's types folder if it exists
            if self.current_market_editor:
                self.current_market_editor.types_folder = folder
            # Auto-save to project file if one is set
            if self.project_file_path:
                self.save_project(silent=True)
    
    def refresh_types_files(self):
        """Refresh the list of XML files in the Types folder"""
        if not self.types_folder or not os.path.isdir(self.types_folder):
            self.types_file_combo['values'] = []
            return
        
        xml_files = [f for f in os.listdir(self.types_folder) if f.endswith('.xml')]
        xml_files.sort()
        self.types_file_combo['values'] = xml_files
        
        if xml_files and not self.types_file_var.get():
            self.types_file_var.set(xml_files[0])
            self.load_types_file()
    
    def load_types_file(self, event=None):
        """Load and parse XML file to extract type names"""
        if not self.types_folder or not self.types_file_var.get():
            return
        
        file_path = os.path.join(self.types_folder, self.types_file_var.get())
        
        try:
            # Clear existing items
            self.types_listbox.delete(0, tk.END)
            
            # Parse XML file
            class_names = []
            
            # Try parsing as XML first
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                # Find all type elements with name attribute
                for elem in root.iter():
                    if 'name' in elem.attrib:
                        class_names.append(elem.attrib['name'])
            except ET.ParseError:
                # If XML parsing fails, try regex extraction
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Match <type name="CLASSNAME"> pattern
                    pattern = r'<type\s+name="([^"]+)"'
                    matches = re.findall(pattern, content)
                    class_names.extend(matches)
            
            # Remove duplicates and sort
            class_names = sorted(list(set(class_names)))
            
            # Store all class names for filtering
            self.all_types_class_names = class_names
            
            # Apply current filter or show all
            self.filter_types_list()
            
            self.status_var.set(f"Loaded {len(class_names)} class names from {self.types_file_var.get()}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load types file: {str(e)}")
            self.status_var.set(f"Error loading types file: {str(e)}")
    
    def filter_types_list(self):
        """Filter the types listbox based on filter text"""
        if not hasattr(self, 'all_types_class_names'):
            return
        
        filter_text = self.types_filter_var.get().strip().lower()
        
        # Clear listbox
        self.types_listbox.delete(0, tk.END)
        
        # Filter class names
        if filter_text:
            filtered_names = [name for name in self.all_types_class_names if filter_text in name.lower()]
        else:
            filtered_names = self.all_types_class_names
        
        # Add filtered names to listbox
        for name in filtered_names:
            self.types_listbox.insert(tk.END, name)
        
        # Update status
        if filter_text:
            self.status_var.set(f"Showing {len(filtered_names)} of {len(self.all_types_class_names)} class names (filtered by '{filter_text}')")
        else:
            self.status_var.set(f"Showing {len(filtered_names)} class names")
    
    def clear_types_filter(self):
        """Clear the filter and show all class names"""
        self.types_filter_var.set("")
        # filter_types_list will be called automatically via trace
    
    def copy_type_name(self, event):
        """Copy selected type name to clipboard"""
        selection = self.types_listbox.curselection()
        if selection:
            type_name = self.types_listbox.get(selection[0])
            self.root.clipboard_clear()
            self.root.clipboard_append(type_name)
            self.status_var.set(f"Copied '{type_name}' to clipboard")
    
    def add_types_to_market(self):
        """Add selected type names to the selected market file"""
        # Get selected market file
        if not self.types_market_file_var.get():
            messagebox.showwarning("No Market File", "Please select a market file to add items to.")
            return
        
        if not self.market_folder:
            messagebox.showwarning("No Market Folder", "Please set the Market folder first.")
            return
        
        # Get selected class names
        selections = self.types_listbox.curselection()
        if not selections:
            messagebox.showwarning("No Selection", "Please select one or more class names to add.")
            return
        
        selected_class_names = [self.types_listbox.get(index) for index in selections]
        
        # Load the market file
        market_file_path = os.path.join(self.market_folder, self.types_market_file_var.get())
        
        try:
            # Read the market file
            with open(market_file_path, 'r', encoding='utf-8') as f:
                market_data = json.load(f)
            
            # Ensure Items array exists
            if "Items" not in market_data:
                market_data["Items"] = []
            
            # Get existing class names to avoid duplicates
            existing_class_names = {item.get("ClassName", "") for item in market_data["Items"]}
            
            # Add new items (skip if already exists)
            items_added = 0
            items_skipped = 0
            
            for class_name in selected_class_names:
                if class_name in existing_class_names:
                    items_skipped += 1
                    continue
                
                new_item = {
                    "ClassName": class_name,
                    "MaxPriceThreshold": 1000,
                    "MinPriceThreshold": 500,
                    "SellPricePercent": -1.0,
                    "MaxStockThreshold": 500,
                    "MinStockThreshold": 1,
                    "QuantityPercent": -1,
                    "SpawnAttachments": [],
                    "Variants": []
                }
                market_data["Items"].append(new_item)
                existing_class_names.add(class_name)
                items_added += 1
            
            # Save the market file
            with open(market_file_path, 'w', encoding='utf-8') as f:
                json.dump(market_data, f, indent=4, ensure_ascii=False)
            
            # Show result message
            msg = f"Added {items_added} item(s) to {self.types_market_file_var.get()}"
            if items_skipped > 0:
                msg += f"\nSkipped {items_skipped} duplicate(s)"
            messagebox.showinfo("Success", msg)
            self.status_var.set(msg)
            
            # Refresh market editor if it's viewing this file
            if self.current_market_editor and self.market_file_var.get() == self.types_market_file_var.get():
                self.load_market_file()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add items to market file: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
    
    def save_project(self, silent=False):
        """Save current folder selections to a project file
        
        Args:
            silent: If True, don't show success/error dialogs (for auto-save)
        """
        if not self.market_folder and not self.traders_folder:
            if not silent:
                messagebox.showwarning("Warning", "No folders selected to save in project.")
            return
        
        # If no project file path set, ask user where to save
        if not self.project_file_path:
            file_path = filedialog.asksaveasfilename(
                title="Save Project",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if not file_path:
                return
            self.project_file_path = file_path
        
        try:
            project_data = {
                "market_folder": self.market_folder or "",
                "traders_folder": self.traders_folder or "",
                "types_folder": self.types_folder or ""
            }
            
            with open(self.project_file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=4, ensure_ascii=False)
            
            self.status_var.set(f"Project saved: {os.path.basename(self.project_file_path)}")
            if not silent:
                messagebox.showinfo("Success", f"Project saved to:\n{self.project_file_path}")
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to save project: {str(e)}")
            else:
                # Still update status even in silent mode on error
                self.status_var.set(f"Error saving project: {str(e)}")
    
    def load_project(self):
        """Load folder selections from a project file"""
        file_path = filedialog.askopenfilename(
            title="Load Project",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # Load market folder
            if "market_folder" in project_data and project_data["market_folder"]:
                market_folder = project_data["market_folder"]
                if os.path.isdir(market_folder):
                    self.market_folder = market_folder
                    self.market_label.config(text=f"Market Folder: {os.path.basename(market_folder)}")
                    self.refresh_market_files()
                    self.refresh_types_market_files()
                    self.refresh_types_market_files()
                else:
                    messagebox.showwarning("Warning", f"Market folder not found:\n{market_folder}")
            
            # Load traders folder
            if "traders_folder" in project_data and project_data["traders_folder"]:
                traders_folder = project_data["traders_folder"]
                if os.path.isdir(traders_folder):
                    self.traders_folder = traders_folder
                    self.traders_label.config(text=f"Traders Folder: {os.path.basename(traders_folder)}")
                    self.refresh_trader_files()
                else:
                    messagebox.showwarning("Warning", f"Traders folder not found:\n{traders_folder}")
            
            # Load types folder
            if "types_folder" in project_data and project_data["types_folder"]:
                types_folder = project_data["types_folder"]
                if os.path.isdir(types_folder):
                    self.types_folder = types_folder
                    self.types_label.config(text=f"Types Folder: {os.path.basename(types_folder)}")
                    self.refresh_types_files()
                    # Update market editor's types folder if it exists
                    if self.current_market_editor:
                        self.current_market_editor.types_folder = types_folder
                else:
                    messagebox.showwarning("Warning", f"Types folder not found:\n{types_folder}")
            
            self.project_file_path = file_path
            self.status_var.set(f"Project loaded: {os.path.basename(file_path)}")
            messagebox.showinfo("Success", "Project loaded successfully!")
            
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid project file format.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project: {str(e)}")
    
    def load_default_project(self):
        """Try to load a default project file if it exists"""
        default_project = "dayz_trader_project.json"
        if os.path.isfile(default_project):
            try:
                with open(default_project, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                
                # Load market folder
                if "market_folder" in project_data and project_data["market_folder"]:
                    market_folder = project_data["market_folder"]
                    if os.path.isdir(market_folder):
                        self.market_folder = market_folder
                        self.market_label.config(text=f"Market Folder: {os.path.basename(market_folder)}")
                        self.refresh_market_files()
                
                # Load traders folder
                if "traders_folder" in project_data and project_data["traders_folder"]:
                    traders_folder = project_data["traders_folder"]
                    if os.path.isdir(traders_folder):
                        self.traders_folder = traders_folder
                        self.traders_label.config(text=f"Traders Folder: {os.path.basename(traders_folder)}")
                        self.refresh_trader_files()
                
                # Load types folder
                if "types_folder" in project_data and project_data["types_folder"]:
                    types_folder = project_data["types_folder"]
                    if os.path.isdir(types_folder):
                        self.types_folder = types_folder
                        self.types_label.config(text=f"Types Folder: {os.path.basename(types_folder)}")
                        self.refresh_types_files()
                        # Update market editor's types folder if it exists
                        if self.current_market_editor:
                            self.current_market_editor.types_folder = types_folder
                
                self.project_file_path = default_project
                self.status_var.set(f"Default project loaded: {default_project}")
            except Exception:
                # Silently fail if default project can't be loaded
                pass
    
    def new_market_file(self):
        """Create a new market file based on example.json template"""
        if not self.market_folder:
            messagebox.showwarning("No Market Folder", "Please set the Market folder first.")
            return
        
        # Prompt for filename
        filename = simpledialog.askstring("New Market File", "Enter filename (without .json extension):")
        if not filename:
            return
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Check if file already exists
        file_path = os.path.join(self.market_folder, filename)
        if os.path.isfile(file_path):
            if not messagebox.askyesno("File Exists", f"File '{filename}' already exists. Overwrite?"):
                return
        
        # Get example.json from program directory
        example_file = get_resource_path("example.json")
        
        if not os.path.isfile(example_file):
            messagebox.showerror("Error", f"example.json not found in program directory")
            return
        
        try:
            # Load example.json
            with open(example_file, 'r', encoding='utf-8') as f:
                example_data = json.load(f)
            
            # Create a deep copy to avoid modifying the original
            new_data = copy.deepcopy(example_data)
            
            # Save to new file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=4, ensure_ascii=False)
            
            # Refresh file list and load the new file
            self.refresh_market_files()
            self.refresh_types_market_files()  # Update Types Viewer dropdown
            self.market_file_var.set(filename)
            self.load_market_file()
            
            self.status_var.set(f"Created new market file: {filename}")
            messagebox.showinfo("Success", f"New market file '{filename}' created successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create new market file: {str(e)}")
            self.status_var.set(f"Error creating file: {str(e)}")
    
    def refresh_market_files(self):
        if not self.market_folder:
            return
        
        json_files = [f for f in os.listdir(self.market_folder) if f.endswith('.json')]
        json_files.sort()
        self.market_file_combo['values'] = json_files
        
        if json_files and not self.market_file_var.get():
            self.market_file_var.set(json_files[0])
            self.load_market_file()
    
    def refresh_types_market_files(self):
        """Refresh the market file dropdown in Types Viewer tab"""
        if not self.market_folder or not os.path.isdir(self.market_folder):
            if hasattr(self, 'types_market_file_combo'):
                self.types_market_file_combo['values'] = []
            return
        
        json_files = [f for f in os.listdir(self.market_folder) if f.endswith('.json')]
        json_files.sort()
        if hasattr(self, 'types_market_file_combo'):
            self.types_market_file_combo['values'] = json_files
    
    def refresh_trader_files(self):
        if not self.traders_folder:
            return
        
        json_files = [f for f in os.listdir(self.traders_folder) if f.endswith('.json')]
        json_files.sort()
        self.trader_file_combo['values'] = json_files
        
        if json_files and not self.trader_file_var.get():
            self.trader_file_var.set(json_files[0])
            self.load_trader_file()
    
    def load_market_file(self, event=None):
        if not self.market_folder or not self.market_file_var.get():
            return
        
        file_path = os.path.join(self.market_folder, self.market_file_var.get())
        
        # Clear existing editor
        for widget in self.market_editor_frame.winfo_children():
            widget.destroy()
        
        self.current_market_editor = MarketEditor(self.market_editor_frame, file_path, self.types_folder)
        self.status_var.set(f"Loaded: {self.market_file_var.get()}")
    
    def load_trader_file(self, event=None):
        if not self.traders_folder or not self.trader_file_var.get():
            return
        
        file_path = os.path.join(self.traders_folder, self.trader_file_var.get())
        
        # Clear existing editor
        for widget in self.trader_editor_frame.winfo_children():
            widget.destroy()
        
        self.current_trader_editor = TraderEditor(self.trader_editor_frame, file_path, self.market_folder)
        self.status_var.set(f"Loaded: {self.trader_file_var.get()}")
    
    def save_current(self):
        # Save button handler - saves based on current tab
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 0:  # Market tab
            if self.current_market_editor:
                if self.current_market_editor.save_file():
                    self.status_var.set("Market file saved successfully")
                    messagebox.showinfo("Success", "Market file saved successfully!")
        elif current_tab == 1:  # Trader tab
            if self.current_trader_editor:
                if self.current_trader_editor.save_file():
                    self.status_var.set("Trader file saved successfully")
                    messagebox.showinfo("Success", "Trader file saved successfully!")
    
    def remove_duplicates(self):
        """Scan all Market and Trader files for duplicates and prompt to remove them"""
        if not self.market_folder and not self.traders_folder:
            messagebox.showwarning("Warning", "Please set Market and/or Traders folders first.")
            return
        
        all_duplicates = []
        files_processed = []
        
        # Scan Market files
        if self.market_folder and os.path.isdir(self.market_folder):
            json_files = [f for f in os.listdir(self.market_folder) if f.endswith('.json')]
            for json_file in json_files:
                file_path = os.path.join(self.market_folder, json_file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if "Items" in data and isinstance(data["Items"], list):
                        seen_classnames = {}  # Maps class_name to first occurrence index
                        duplicates = []
                        
                        for index, item in enumerate(data["Items"]):
                            class_name = item.get("ClassName", "")
                            if class_name:
                                if class_name in seen_classnames:
                                    # This is a duplicate (we've seen this class_name before)
                                    duplicates.append({
                                        "index": index,
                                        "class_name": class_name,
                                        "file": json_file,
                                        "file_path": file_path,
                                        "type": "market"
                                    })
                                else:
                                    # First occurrence - keep this one
                                    seen_classnames[class_name] = index
                        
                        if duplicates:
                            all_duplicates.extend(duplicates)
                            files_processed.append((file_path, data, duplicates))
                except Exception as e:
                    self.status_var.set(f"Error processing {json_file}: {str(e)}")
        
        # Scan Trader files
        if self.traders_folder and os.path.isdir(self.traders_folder):
            json_files = [f for f in os.listdir(self.traders_folder) if f.endswith('.json')]
            for json_file in json_files:
                file_path = os.path.join(self.traders_folder, json_file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if "Categories" in data and isinstance(data["Categories"], list):
                        seen_categories = {}  # Maps category to first occurrence index
                        duplicates = []
                        
                        for index, category in enumerate(data["Categories"]):
                            if category in seen_categories:
                                # This is a duplicate (we've seen this category before)
                                duplicates.append({
                                    "index": index,
                                    "category": category,
                                    "file": json_file,
                                    "file_path": file_path,
                                    "type": "trader"
                                })
                            else:
                                # First occurrence - keep this one
                                seen_categories[category] = index
                        
                        if duplicates:
                            all_duplicates.extend(duplicates)
                            files_processed.append((file_path, data, duplicates))
                except Exception as e:
                    self.status_var.set(f"Error processing {json_file}: {str(e)}")
        
        # Show results and prompt for removal
        if not all_duplicates:
            messagebox.showinfo("No Duplicates", "No duplicates found in any files!")
            self.status_var.set("No duplicates found")
            return
        
        # Build summary message
        summary_lines = [f"Found {len(all_duplicates)} duplicate(s) in {len(files_processed)} file(s):\n"]
        
        # Group by file
        by_file = {}
        for dup in all_duplicates:
            file_name = dup["file"]
            if file_name not in by_file:
                by_file[file_name] = []
            by_file[file_name].append(dup)
        
        for file_name, dups in by_file.items():
            summary_lines.append(f"\n{file_name} ({len(dups)} duplicate(s)):")
            for dup in dups[:10]:  # Show first 10 per file
                if dup["type"] == "market":
                    summary_lines.append(f"  - ClassName: {dup['class_name']} (index {dup['index']})")
                else:
                    summary_lines.append(f"  - Category: {dup['category']} (index {dup['index']})")
            if len(dups) > 10:
                summary_lines.append(f"  ... and {len(dups) - 10} more")
        
        summary = "\n".join(summary_lines)
        summary += "\n\nRemove all duplicates? (First occurrence will be kept)"
        
        if messagebox.askyesno("Remove Duplicates", summary):
            removed_count = 0
            files_saved = 0
            
            for file_path, data, duplicates in files_processed:
                try:
                    # Sort duplicates by index in reverse order so we can remove from end to start
                    sorted_dups = sorted(duplicates, key=lambda x: x["index"], reverse=True)
                    
                    # Get the type from first duplicate
                    dup_type = sorted_dups[0]["type"]
                    
                    if dup_type == "market":
                        # Remove duplicate items from Items array
                        for dup in sorted_dups:
                            data["Items"].pop(dup["index"])
                            removed_count += 1
                    else:
                        # Remove duplicate categories
                        for dup in sorted_dups:
                            data["Categories"].pop(dup["index"])
                            removed_count += 1
                    
                    # Save the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    files_saved += 1
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save {os.path.basename(file_path)}: {str(e)}")
            
            messagebox.showinfo("Success", 
                              f"Removed {removed_count} duplicate(s) from {files_saved} file(s).\n\n"
                              "Please refresh the file lists if needed.")
            self.status_var.set(f"Removed {removed_count} duplicate(s) from {files_saved} file(s)")
            
            # Refresh current editors if they're open
            if self.current_market_editor and self.market_file_var.get():
                self.load_market_file()
            if self.current_trader_editor and self.trader_file_var.get():
                self.load_trader_file()


def main():
    root = tk.Tk()
    app = DayZTraderEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()

