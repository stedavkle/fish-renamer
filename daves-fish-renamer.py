'''
Here the TreeView widget is configured as a multi-column listbox
with adjustable column width and column-header-click sorting.
'''
import tkinter as tk
import tkinter.font as tkFont
import tkinter.ttk as ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import pandas as pd
from PIL import Image, ImageTk
import re
import numpy as np

# TODO using exifread instead of pyexiv2 because pyexiv2 does not work with pyinstaller
import exifread
#from pyexiv2 import Image as ImgMeta
import sys, os

from pathlib import Path


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)

def get_data_directory():
    """Determine the correct data directory based on execution context"""
    if getattr(sys, 'frozen', False):
        # Running in a bundle (PyInstaller)
        base_dir = Path(sys._MEIPASS)
    else:
        # Running in development
        base_dir = Path(__file__).parent.parent
    
    # Check common data directory locations
    possible_locations = [
        base_dir / 'config',
        Path.home() / '.daves-fish-renamer' / 'config',
        Path(os.getenv('APPDATA', '')) / 'Daves Fish Renamer' / 'config' if os.name == 'nt' else None
    ]
    
    for location in possible_locations:
        if location and location.exists():
            return location
            
    return base_dir  # Fallback

class MultiColumnListbox(TkinterDnD.Tk):
    """use a ttk.TreeView as a multicolumn ListBox"""

    def __init__(self):
        super().__init__()
        self.tree = None
        self._load_data()
        self._setup_widgets()
        self._build_tree()
        self._load_personal_config()

    def _setup_widgets(self):
        self.title("Dave's Fish Renamer")
        ico = Image.open(resource_path('config' + os.sep + 'icon.png'))
        photo = ImageTk.PhotoImage(ico)
        self.wm_iconphoto(False, photo)

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._dnd_files)
        
        main_container = self
        self.upper_frame = ttk.Frame(main_container)
        self.upper_frame.grid(row=0, column=0, sticky="nsew")
        self.upper_right_frame = ttk.Frame(main_container)
        self.upper_right_frame.grid(row=0, column=1, sticky="nsew")
        self.middle_frame = ttk.Frame(main_container)
        self.middle_frame.grid(row=1, column=0, sticky="nsew", columnspan=2)
        self.bottom_frame = ttk.Frame(main_container)
        self.bottom_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10, columnspan=2)

        self.menu = tk.Menu(self)
        filemenu = tk.Menu(self.menu, tearoff=0)
        filemenu.add_command(label="New", command=lambda x: x)
        self.config(menu=self.menu)
        
        self.search_field = ttk.Entry(self.middle_frame)
        self.search_field.pack(fill='x', padx=10, pady=10)
        self.search_field.bind("<Return>", self.search)

        main_container.grid_columnconfigure(0, weight=1)  # Treeview expands
        main_container.grid_columnconfigure(1, weight=0)  # Filters stay compact
        main_container.grid_rowconfigure(0, weight=1)

        # Configure Treeview and scrollbars
        self.tree = ttk.Treeview(self.upper_frame, columns=list(self.fish_df.columns), show="headings")
        vsb = ttk.Scrollbar(self.upper_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.upper_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.upper_frame.grid_columnconfigure(0, weight=1)
        self.upper_frame.grid_rowconfigure(0, weight=1)

        for col in range(3):
            self.bottom_frame.grid_columnconfigure(col, weight=1)
        self.tree.bind("<ButtonRelease-1>", self._row_selected)

        self.family_default = '0-Fam'
        ttk.Label(self.bottom_frame, text="Family").grid(row=0, column=0, padx=5, pady=2, sticky='ew')
        self.cb_family = ttk.Combobox(self.bottom_frame, values=[self.family_default] + sorted(self.fish_df['Family'].unique()), state='readonly')
        self.cb_family.grid(row=1, column=0, padx=5, pady=2, sticky='ew')
        self.cb_family.bind("<<ComboboxSelected>>", self.set_family)
        self.cb_family.current(0)
        self.cb_family.state(['disabled'])

        self.genus_default = 'genus'
        ttk.Label(self.bottom_frame, text="Genus").grid(row=0, column=1, padx=5, pady=2, sticky='ew')
        self.cb_genus = ttk.Combobox(self.bottom_frame, values=[self.genus_default] + sorted(self.fish_df['Genus'].unique()), state='readonly')
        self.cb_genus.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        self.cb_genus.bind("<<ComboboxSelected>>", self.set_genus)
        self.cb_genus.current(0)
        self.cb_genus.state(['disabled'])

        self.species_default = 'spec'
        ttk.Label(self.bottom_frame, text="Species").grid(row=0, column=2, padx=5, pady=2, sticky='ew')
        self.cb_species = ttk.Combobox(self.bottom_frame, values=[self.species_default] + sorted(self.fish_df['Species'].unique()), state='readonly')
        self.cb_species.grid(row=1, column=2, padx=5, pady=2, sticky='ew')
        self.cb_species.bind("<<ComboboxSelected>>", self.set_species)
        self.cb_species.current(0)
        self.cb_species.state(['disabled'])
        
        # create a new frame, put it in row1 col3. then put the om_mode into it
        self.edit_frame = ttk.Frame(self.bottom_frame)
        self.edit_frame.grid(row=1, column=3, sticky="nsew")

        self.mode = tk.StringVar()
        self.om_mode = tk.OptionMenu(self.edit_frame, self.mode, "Basic", "Identify", "Edit")
        self.om_mode.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        #self.om_mode.config(width=22)
        self.mode.set("Basic")
        # when optionmenu is modified, call toggle
        self.mode.trace_add('write', self._toggle_extended_info)

        self.bt_rename = tk.Button(self.edit_frame, text="Rename")
        self.bt_rename.grid(row=1, column=2, padx=5, pady=2, sticky='ew')
        self.bt_rename.grid_remove()
        self.bt_rename.bind("<Button-1>", self._edit_info)


        confidence = ["ok", "cf"]
        tk.Label(self.bottom_frame, text="Confidence").grid(row=2, column=0, padx=5, pady=2, sticky='ew')
        self.cb_confidence = ttk.Combobox(self.bottom_frame, values=confidence, state='readonly')
        self.cb_confidence.grid(row=3, column=0, padx=5, pady=2, sticky='ew')
        self.cb_confidence.current(0)
        self.cb_confidence.state(['disabled'])

        phase = ["ad", "IP", "F", "M", "TP", "juv", "pair", "subad", "trans"]
        tk.Label(self.bottom_frame, text="Phase").grid(row=2, column=1, padx=5, pady=2, sticky='ew')
        self.cb_phase = ttk.Combobox(self.bottom_frame, values=phase, state='readonly')
        self.cb_phase.grid(row=3, column=1, padx=5, pady=2, sticky='ew')
        self.cb_phase.current(0)
        self.cb_phase.state(['disabled'])

        self.colour_dict = {"typical colour": "ty", "aged": "aged", "banded": "band", "barred": "bar", "blotched": "blot", "brown": "brown", "dark": "dark", "dead": "dead", "diseased, deformed": "ill", "inds. w. different colours": "diverg", "white, pale, grey": "light", "lined": "line", "colour mutant": "mutant", "typical spot absent": "no-spot", "typical stripe absent": "no-stripe", "nocturnal": "noct", "nuptial colour": "nupt", "patterned": "pattern", "red": "red", "relaxed colour": "relax", "scarred, deformed": "scar", "speckled": "speck", "spotted": "spot", "striped": "strip", "tailspot": "tailspot", "bicolor": "two-tone", "variation": "vari", "yellow": "yell"}   
        tk.Label(self.bottom_frame, text="Colour").grid(row=2, column=2, padx=5, pady=2, sticky='ew')
        self.cb_colour = ttk.Combobox(self.bottom_frame, values=list(self.colour_dict.keys()), state='readonly')
        self.cb_colour.grid(row=3, column=2, padx=5, pady=2, sticky='ew')
        self.cb_colour.current(0)
        self.cb_colour.state(['disabled'])

        self.behaviour_dict = {"not specified": "zz", "agitated": "agit", "burried": "bur", "captured": "caught", "being cleaned": "cleaned", "cleaning client": "cleans", "colony": "col", "colour change (pic series)": "col-ch", "compeYng": "comp", "courYng": "court", "D. Act. Photoloc. suggesYve": "DAP", "exposed (e.g. out of sand)": "exp", "feeding": "feed", "fighYng": "fight", "hiding": "hide", "mouth-brooding": "mouth-b", "parenYng, family": "parent", "resYng": "rest", "schooling": "school", "spawning, oviposiYon": "spawn", "interspecific team": "team", "warning": "warn", "yawning": "yawn"}    
        
        tk.Label(self.bottom_frame, text="Behaviour").grid(row=2, column=3, padx=5, pady=2, sticky='ew')
        # set the default to the first behaviour[0]
        self.cb_behaviour = ttk.Combobox(self.bottom_frame, values=list(self.behaviour_dict.keys()), state='readonly')
        self.cb_behaviour.grid(row=3, column=3, padx=5, pady=2, sticky='ew')
        self.cb_behaviour.current(0)
        self.cb_behaviour.state(['disabled'])    

        ttk.Label(self.bottom_frame, text="Photographer").grid(row=4, column=0, padx=5, pady=2, sticky='ew')
        self.cb_author = ttk.Combobox(self.bottom_frame, values=self.users_df['Full name'].values.tolist(), state='readonly')
        self.cb_author.grid(row=5, column=0, padx=5, pady=2, sticky='ew')
        self.cb_author.bind("<<ComboboxSelected>>", self._save_personal_config)
        ttk.Label(self.bottom_frame, text="Site").grid(row=4, column=1, padx=5, pady=2, sticky='ew')
        # seperate location and site by a comma
        self.cb_site = ttk.Combobox(self.bottom_frame, values=self.divesites_df[['Location', 'Site']].apply(lambda x: ', '.join(x), axis=1).values.tolist(), state='readonly')
        self.cb_site.grid(row=5, column=1, padx=5, pady=2, sticky='ew')
        self.cb_site.bind("<<ComboboxSelected>>", self._save_personal_config)
        
        # create a clickable link to google maps
        self.link = tk.Label(self.bottom_frame, text="Google Maps", fg="blue", cursor="hand2")
        self.link.grid(row=6, column=1, padx=5, pady=2, sticky='ew')

        def __open_googlemaps(event):
            location, site = self.cb_site.get().split(", ")
            latitude, longitude = self.divesites_df[(self.divesites_df['Location'] == location) & (self.divesites_df['Site'] == site)][['latitude', 'longitude']].values[0]
            os.system(f"start https://maps.google.com/?q={latitude},{longitude}")

        self.link.bind("<Button-1>", __open_googlemaps)
        # https://maps.google.com/?q=<lat>,<lng>
        
        tk.Label(self.bottom_frame, text="Activity").grid(row=4, column=2, padx=5, pady=2, sticky='ew')
        self.cb_activity = ttk.Combobox(self.bottom_frame, values=self.activities_df['activity'].values.tolist(), state='readonly')
        self.cb_activity.grid(row=5, column=2, padx=5, pady=2, sticky='ew')
        #self.cb_activity.current(0)
        self.cb_activity.bind("<<ComboboxSelected>>", self._save_personal_config)

        # create a textblock that is used for displaying status messages
        self.status = tk.Text(self.bottom_frame, height=3, width=1, font=("Arial", 8))
        self.status.grid(row=4, column=3, padx=5, pady=2, sticky='ew', rowspan=3)
        self.status.insert(tk.END, "Ready")

    def _reset_info(self):
        self.cb_family.set(self.family_default)
        self.cb_genus.set(self.genus_default)
        self.cb_species.set(self.species_default)
        self.cb_confidence.set("ok")
        self.cb_phase.set("ad")
        self.cb_colour.set("typical colour")
        self.cb_behaviour.set("not specified")

    def _save_personal_config(self, event):
        with open("config/conf.conf", "w") as f:
            f.write(f"{self.cb_author.get()}\n")
            f.write(f"{self.cb_site.get()}\n")
            f.write(f"{self.cb_activity.get()}\n")

    def _load_personal_config(self):
        if os.path.exists("config/conf.conf"):
            with open("config/conf.conf", "r") as f:
                self.cb_author.set(f.readline().strip())
                self.cb_site.set(f.readline().strip())
                self.cb_activity.set(f.readline().strip())
        else:
            self

    def open_popup(self, content):
        top = tk.Toplevel(self)
        top.geometry("250x100")
        top.title("Alert")
        tk.Label(top, text=content).pack()
        # location should be in the middle of the top level window
        x = (top.winfo_screenwidth() - top.winfo_reqwidth()) / 2
        y = (top.winfo_screenheight() - top.winfo_reqheight()) / 2
        top.geometry("+%d+%d" % (x, y))
        top.after(5000, top.destroy)

    def _check_if_essential_info_set(self):
        if self.cb_author.get() == "":
            self.cb_author.focus()
            return False
        elif self.cb_site.get() == "":
            self.cb_site.focus()
            return False
        return True
            
    def _get_filedate_str(self, path):
        try:
            image = Image.open(path)
            exif = image._getexif()
            return exif[36867].replace(' ', '_').replace(':', '-')
        except:
            f = open(path, 'rb')
            tags = exifread.process_file(f)
            return tags['Image DateTime'].printable.replace(' ', '_').replace(':', '-')
        
    def _decdeg2dms(self, dd):
        mult = -1 if dd < 0 else 1
        mnt,sec = divmod(abs(dd)*3600, 60)
        deg,mnt = divmod(mnt, 60)

        d = mult*deg.as_integer_ratio()
        m = mult*mnt.as_integer_ratio()
        s = round(mult*sec).as_integer_ratio()
        return f"{d[0]}/{d[1]} {m[0]}/{m[1]} {s[0]}/{s[1]}"

    def _process_exif(self, path):
        # TODO excluding gps because pyexiv2 does not work with pyinstaller
        return self._get_filedate_str(path), False

        # img = ImgMeta(path)
        # exif = img.read_exif()
        # date = exif['Exif.Photo.DateTimeOriginal']
        # gps_set = False

        # extension = os.path.splitext(path)[1]
        # if extension.lower() != '.arw':
        #     location, site = self.cb_site.get().split(", ")
        #     lat, lon = self.divesites_df[(self.divesites_df['Location'] == location) & (self.divesites_df['Site'] == site)][['latitude', 'longitude']].values[0]
        #     lat_dms = self._decdeg2dms(lat)
        #     lon_dms = self._decdeg2dms(lon)
        #     exif["Exif.GPSInfo.GPSLatitude"] = lat_dms
        #     exif["Exif.GPSInfo.GPSLatitudeRef"] = "N"
        #     exif["Exif.GPSInfo.GPSLongitude"] = lon_dms
        #     exif["Exif.GPSInfo.GPSLongitudeRef"] = "E"
        #     exif["Exif.Image.GPSTag"] = 654
        #     exif["Exif.GPSInfo.GPSVersionID"] = '2 3 0 0'
        #     img.modify_exif(exif)
        #     gps_set = True
        # return date.replace(' ', '_').replace(':', '-'), gps_set
    def regex_match_basic_info(self, filename):
        return re.match(r'[A-Za-z]{5}_[A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3}_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_[A-Za-z]+_[A-Za-z0-9]+', filename)

    def regex_match_info(self, filename):
        # Family, Genus, species, confidence, phase, colour, behaviour, author, site, date, time, activity, original name
        return re.match(r'(0?\-?[A-Za-z]*)_([A-Za-z]+)_([a-z]+)_[A-Z]_([a-z]{2})_([A-Za-z]+)_([A-Za-z\-]+)_([A-Za-z\-]+)_([A-Za-z]{5})_([A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3})_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_([A-Za-z]+)_([A-Za-z0-9]+)', filename)

    def regex_match_datetime_filename(self, filename):
        return re.match(r'0?\-?[A-Za-z]*_[A-Za-z]+_[a-z]+_[A-Z]_[a-z]{2}_[A-Za-z]+_[A-Za-z\-]+_[A-Za-z\-]+_[A-Za-z]{5}_[A-Z]{3}-[A-Za-z]+-[A-Z0-9]{3}_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_[A-Za-z]+_([A-Za-z0-9]+)', filename)


    def _assemble_filename_name_site_datetime_activity(self, path):
        filepath, extension = os.path.splitext(path)
        filename = os.path.basename(filepath)
        
        if self.regex_match_basic_info(filename) or self.regex_match_info(filename):
            return None

        filename = filename.replace('_', '')
        filedate, gps_set = self._process_exif(path)

        author = self.cb_author.get()
        author_code = self.users_df[self.users_df['Full name'] == author]['Namecode'].values[0]
        site = self.cb_site.get()
        location, site = site.split(", ")
        site_string = self.divesites_df[(self.divesites_df['Location'] == location) & (self.divesites_df['Site'] == site)]['Site string'].values[0]
        activity = self.cb_activity.get()
        if gps_set:
            return f"{author_code}_{site_string}_{filedate}_{activity}_G_{filename}{extension}"
        return f"{author_code}_{site_string}_{filedate}_{activity}_{filename}{extension}"
    
    def _assemble_filename_family_genus_species_details(self, path):
        filepath, extension = os.path.splitext(path)
        filename = os.path.basename(filepath)

        if self.regex_match_info(filename) or not self.regex_match_basic_info(filename):
            return None

        family = self.cb_family.get()
        genus = self.cb_genus.get()
        species = self.cb_species.get()
        confidence = self.cb_confidence.get()
        phase = self.cb_phase.get()
        colour = self.colour_dict[self.cb_colour.get()]
        behaviour = self.behaviour_dict[self.cb_behaviour.get()]

        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour}_{behaviour}_{filename}{extension}"
    
    def _assemble_edited_filename(self, path):
        filepath, extension = os.path.splitext(path)
        info = self.regex_match_info(os.path.basename(filepath)).groups()
        # Family, Genus, species, confidence, phase, colour, behaviour, author, site, date, time, activity, original name

        family = self.cb_family.get() if self.editing_fields[0] else info[0]
        genus = self.cb_genus.get() if self.editing_fields[1] else info[1]
        species = self.cb_species.get() if self.editing_fields[2] else info[2]
        confidence = self.cb_confidence.get() if self.editing_fields[3] else info[3]
        phase = self.cb_phase.get() if self.editing_fields[4] else info[4]
        colour = self.colour_dict[self.cb_colour.get()] if self.editing_fields[5] else info[5]
        behaviour = self.behaviour_dict[self.cb_behaviour.get()] if self.editing_fields[6] else info[6]
        author = self.cb_author.get()
        author_code = self.users_df[self.users_df['Full name'] == author]['Namecode'].values[0] if self.editing_fields[7] else info[7]
        site = self.cb_site.get()
        location, site = site.split(", ")
        site_string = self.divesites_df[(self.divesites_df['Location'] == location) & (self.divesites_df['Site'] == site)]['Site string'].values[0] if self.editing_fields[8] else info[8]
        date = info[9]
        time = info[10]
        activity = self.cb_activity.get() if self.editing_fields[11] else info[11]
        filename = info[12]
        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour}_{behaviour}_{author_code}_{site_string}_{date}_{time}_{activity}_{filename}{extension}"

    def _edit_info(self, event):
        if len(self.editing_files) == 0:
            self._warn("No files selected")
            return
        
        renamed = 0
        for path in self.editing_files:
            new_filename = self._assemble_edited_filename(path)
            new_filepath = os.path.join(os.path.dirname(path), new_filename)
            if os.path.exists(new_filepath):
                continue
            os.rename(path, new_filepath)
            renamed += 1
        self._notice(f"{renamed}/{len(self.editing_files)} files were renamed successfully.")
        self._reset_info()
        self.editing_files = []

    def _check_if_same_info(self, files):
        # Family, Genus, species, confidence, phase, colour, behaviour, author, site, date, time, activity, original name
        info = np.array([self.regex_match_info(os.path.basename(os.path.splitext(file)[0])).groups() for file in files])
        is_same = (info[:, :] == info[0, :]).all(axis=0)
        values = np.array([info[0][i] if is_same[i] else None for i in range(info.shape[1])])
        return is_same, values

    def _warn(self, text):
        # set background of self.status to red and display the text
        self.status.delete(1.0, tk.END)
        self.status.insert(1.0, text)
        self.status.config(foreground="red")
    def _notice(self, text):
        # set background of self.status to green and display the text
        self.status.delete(1.0, tk.END)
        self.status.insert(1.0, text)
        self.status.config(foreground="black")

    def _toggle_checkboxes(self, family, genus, species, confidence, phase, colour, behaviour, author, site, activity):
        self.cb_family.state(['!disabled'] if family else ['disabled'])
        self.cb_genus.state(['!disabled'] if genus else ['disabled'])
        self.cb_species.state(['!disabled'] if species else ['disabled'])
        self.cb_confidence.state(['!disabled'] if confidence else ['disabled'])
        self.cb_phase.state(['!disabled'] if phase else ['disabled'])
        self.cb_colour.state(['!disabled'] if colour else ['disabled'])
        self.cb_behaviour.state(['!disabled'] if behaviour else ['disabled'])
        self.cb_author.state(['!disabled'] if author else ['disabled'])
        self.cb_site.state(['!disabled'] if site else ['disabled'])
        self.cb_activity.state(['!disabled'] if activity else ['disabled'])

    def _set_checkboxes(self, family, genus, species, confidence, phase, colour, behaviour, author, site, activity):
        if family: self.cb_family.set(family)
        if genus: self.cb_genus.set(genus)
        if species: self.cb_species.set(species)
        if confidence: self.cb_confidence.set(confidence)
        if phase: self.cb_phase.set(phase)
        # reverse lookup
        if colour: self.cb_colour.set(next((k for k, v in self.colour_dict.items() if v == colour), None))
        if behaviour: self.cb_behaviour.set(next((k for k, v in self.behaviour_dict.items() if v == behaviour), None))
        if author: self.cb_author.set(self.users_df[self.users_df['Namecode'] == author]['Full name'].values[0])
        if site: self.cb_site.set(self.divesites_df[self.divesites_df['Site string'] == site]['Location'].values[0] + ", " + self.divesites_df[self.divesites_df['Site string'] == site]['Site'].values[0])
        if activity: self.cb_activity.set(activity)

    def _dnd_files(self, event):
        files = self.splitlist(event.data)
        if not self._check_if_essential_info_set(): return

        not_renamed = 0
        if self.mode.get() == "Edit":
            is_same, values = self._check_if_same_info(files)
            if not any(is_same): self._warn("No Info can be edited on these files.")
            self._toggle_checkboxes(*is_same[[0, 1, 2, 3, 4, 5, 6, 7, 8, 11]])
            self._set_checkboxes(*values[[0, 1, 2, 3, 4, 5, 6, 7, 8, 11]])
            self.editing_files = files
            self.editing_fields = is_same
            self._notice(f'Loaded {len(files)} files.')
        
        else:
            for file in files:
                if self.mode.get() == "Basic":
                    filename = self._assemble_filename_name_site_datetime_activity(file)
                elif self.mode.get() == "Identify":
                    filename = self._assemble_filename_family_genus_species_details(file)
                if filename is None:
                    not_renamed += 1
                    continue

                new_filepath = os.path.join(os.path.dirname(file), filename)
                if os.path.exists(new_filepath):
                    not_renamed += 1
                    continue
                else:
                    os.rename(file, new_filepath)
            
            if not_renamed > 0:
                self._warn(f"{not_renamed}/{len(files)} files were not renamed.\nThey might have been renamed already.")
            else:
                self._notice(f"All files were renamed successfully.")
                #self.open_popup(f"{not_renamed} files were not renamed.\nThey might have been renamed already.")


    def _row_selected(self, event):
        item = self.tree.selection()[0]
        family, genus, species, common_name = self.tree.item(item, 'values')
        self.cb_family.set(family)
        self.cb_genus.set(genus)
        self.cb_species.set(species)
        # self._set_preview()

    def _toggle_extended_info(self, a, b, c):
        if self.mode.get() == 'Basic':
            self._toggle_checkboxes(False, False, False, False, False, False, False, True, True, True)
            self.bt_rename.grid_remove()
        elif self.mode.get() == 'Identify':
            self._toggle_checkboxes(True, True, True, True, True, True, True, False, False, False)
            self.bt_rename.grid_remove()
        elif self.mode.get() == 'Edit':
            self._toggle_checkboxes(False, False, False, False, False, False, False, False, False, False)
            self.bt_rename.grid()
        self._notice(f"Switched to \"{self.mode.get()}\" mode")

    def _set_preview(self):
        item = self.tree.selection()[0]
        family, genus, species = self.cb_family.get(), self.cb_genus.get(), self.cb_species.get()
        filename = f"config/preview/{family}_{genus}_{species}.jpg"
        if not os.path.exists(filename):
            filename = f"config/preview/dummy.jpg"
        img = Image.open(filename)
        img = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=img)
        self.preview_label.image = img

    def set_family(self, event):
        family = self.cb_family.get()
        filtered = self.fish_df[self.fish_df['Family'] == family]
        self.cb_family.set(family)
        self.cb_genus['values'] = [self.genus_default] + sorted(filtered['Genus'].unique())
        self.cb_genus.current(0)
        self.cb_species['values'] = [self.species_default] + sorted(filtered['Species'].unique())
        self.cb_species.current(0)
        self.clear_tree()
        self.fill_tree(filtered.values.tolist())

    def set_genus(self, event):
        genus = self.cb_genus.get()
        if genus == self.genus_default:
            filtered = self.fish_df[self.fish_df['Family'] == self.cb_family.get()]
        else:
            filtered = self.fish_df[self.fish_df['Genus'] == genus]
        family = filtered['Family'].iloc[0]
        self.cb_family.set(family)
        self.cb_genus.set(genus)
        self.cb_species['values'] = [self.species_default] + sorted(filtered['Species'].unique())
        self.cb_species.current(0)
        self.clear_tree()
        self.fill_tree(filtered.values.tolist())

    def set_species(self, event):
        species = self.cb_species.get()
        if species == self.species_default:
            filtered = self.fish_df[self.fish_df['Genus'] == self.cb_genus.get()]
        else:
            filtered = self.fish_df[self.fish_df['Species'] == species]
        genus = filtered['Genus'].iloc[0]
        family = filtered['Family'].iloc[0]
        self.cb_genus.set(genus)
        self.cb_family.set(family)
        self.clear_tree()
        self.fill_tree(filtered.values.tolist())
        # self._set_preview()

    def sort_fish_df(self, df):
        return df.sort_values(by=['Family', 'Genus', 'Species'])

    def _load_data(self):
        self.fish_df = pd.read_csv("config" + os.sep + "Species.csv", sep=';')
        # replace nan with ''
        self.fish_df = self.fish_df.fillna('')
           # print("config/Species.csv loaded")
        self.users_df = pd.read_csv("config" + os.sep + "Photographers.csv", sep=';')
            #print("config/Photographers.csv loaded")
        self.divesites_df = pd.read_csv("config" + os.sep + "Divesites.csv", sep=';')
            #print("config/Divesites.csv loaded")
        self.activities_df = pd.read_csv("config" + os.sep + "Activities.csv", sep=';')
            #print("config/Activities.csv loaded")


    def _build_tree(self):
        for col in list(self.fish_df.columns):
            self.tree.heading(col, text=col.title(),
                command=lambda c=col: self.sortby(self.tree, c, 0))
            # adjust the column's width to the header string
            self.tree.column(col,
                width=tkFont.Font().measure(col.title()))

        self.fill_tree(self.sort_fish_df(self.fish_df).values.tolist())

    def fill_tree(self, items):
        for item in items:
            self.tree.insert('', 'end', values=item)
            # adjust column's width if necessary to fit each value
            for ix, val in enumerate(item):
                col_w = tkFont.Font().measure(val)
                if self.tree.column(list(self.fish_df.columns)[ix], width=None)<col_w:
                    self.tree.column(list(self.fish_df.columns)[ix], width=col_w)

    def clear_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def search(self, event):
        self.clear_tree()
        # get the search string
        search_string = self.search_field.get()
        search_substrings = search_string.split()
        # get the data from the dataframe
        fish_filtered = self.fish_df[self.fish_df.apply(lambda row: all([any([substring.lower() in value.lower() for value in row.values]) for substring in search_substrings]), axis=1)]
        #print(fish_filtered)
        # insert the data into the tree
        self.fill_tree(self.sort_fish_df(fish_filtered).values.tolist())

    def sortby(tree, col, descending):
        """sort tree contents when a column header is clicked on"""
        data = [(tree.set(child, col), child) \
            for child in tree.get_children('')]
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        tree.heading(col, command=lambda col=col: sortby(tree, col, \
            int(not descending)))


if __name__ == '__main__':
    # root = tk.Tk()
    # root.title("Multicolumn Treeview/Listbox")
    listbox = MultiColumnListbox()
    listbox.mainloop()