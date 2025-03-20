'''
Here the TreeView widget is configured as a multi-column listbox
with adjustable column width and column-header-click sorting.
'''
import tkinter as tk
import tkinter.font as tkFont
import tkinter.ttk as ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import exifread.classes
import pandas as pd
from PIL import Image, ImageTk
import exifread



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

        # self.preview_label = ttk.Label(self.upper_right_frame)
        # self.preview_label.pack(fill='both', expand=True)

        for col in range(3):
            self.bottom_frame.grid_columnconfigure(col, weight=1)
        self.tree.bind("<ButtonRelease-1>", self._row_selected)

        self.family_defalt = ['0-Fam']
        ttk.Label(self.bottom_frame, text="Family").grid(row=0, column=0, padx=5, pady=2, sticky='ew')
        self.cb_family = ttk.Combobox(self.bottom_frame, values=self.family_defalt + sorted(self.fish_df['Family'].unique()), state='readonly')
        self.cb_family.grid(row=1, column=0, padx=5, pady=2, sticky='ew')
        self.cb_family.bind("<<ComboboxSelected>>", self.set_family)
        self.cb_family.current(0)
        self.cb_family.state(['disabled'])

        self.genus_default = ['genus']
        ttk.Label(self.bottom_frame, text="Genus").grid(row=0, column=1, padx=5, pady=2, sticky='ew')
        self.cb_genus = ttk.Combobox(self.bottom_frame, values=self.genus_default + sorted(self.fish_df['Genus'].unique()), state='readonly')
        self.cb_genus.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        self.cb_genus.bind("<<ComboboxSelected>>", self.set_genus)
        self.cb_genus.current(0)
        self.cb_genus.state(['disabled'])

        self.species_default = ['spec']
        ttk.Label(self.bottom_frame, text="Species").grid(row=0, column=2, padx=5, pady=2, sticky='ew')
        self.cb_species = ttk.Combobox(self.bottom_frame, values=self.species_default + sorted(self.fish_df['Species'].unique()), state='readonly')
        self.cb_species.grid(row=1, column=2, padx=5, pady=2, sticky='ew')
        self.cb_species.bind("<<ComboboxSelected>>", self.set_species)
        self.cb_species.current(0)
        self.cb_species.state(['disabled'])

        self.fish_identification = tk.IntVar()
        self.cb_extended_info = ttk.Checkbutton(self.bottom_frame, text="Identify Fish", variable=self.fish_identification, onvalue=1, offvalue=0)
        self.cb_extended_info.grid(row=0, column=3, padx=5, pady=2, sticky='ew', rowspan=2)
        self.cb_extended_info.bind("<Button-1>", self._toggle_extended_info)
        self.fish_identification.set(0)

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
        self.cb_area = ttk.Combobox(self.bottom_frame, values=self.divesites_df[['Location', 'Site']].apply(lambda x: ', '.join(x), axis=1).values.tolist(), state='readonly')
        self.cb_area.grid(row=5, column=1, padx=5, pady=2, sticky='ew')
        self.cb_area.bind("<<ComboboxSelected>>", self._save_personal_config)
        
        # create a clickable link to google maps
        self.link = tk.Label(self.bottom_frame, text="Google Maps", fg="blue", cursor="hand2")
        self.link.grid(row=6, column=1, padx=5, pady=2, sticky='ew')
        def __open_googlemaps(event):
            location, site = self.cb_area.get().split(", ")
            latitude, longitude = self.divesites_df[(self.divesites_df['Location'] == location) & (self.divesites_df['Site'] == site)][['latitude', 'longitude']].values[0]
            os.system(f"start https://maps.google.com/?q={latitude},{longitude}")
        self.link.bind("<Button-1>", __open_googlemaps)
        # https://maps.google.com/?q=<lat>,<lng>
        
        tk.Label(self.bottom_frame, text="Activity").grid(row=4, column=2, padx=5, pady=2, sticky='ew')
        self.cb_activity = ttk.Combobox(self.bottom_frame, values=self.activities_df['activity'].values.tolist(), state='readonly')
        self.cb_activity.grid(row=5, column=2, padx=5, pady=2, sticky='ew')
        #self.cb_activity.current(0)
        self.cb_activity.bind("<<ComboboxSelected>>", self._save_personal_config)

    def _save_personal_config(self, event):
        with open("config/conf.conf", "w") as f:
            f.write(f"{self.cb_author.get()}\n")
            f.write(f"{self.cb_area.get()}\n")
            f.write(f"{self.cb_activity.get()}\n")

    def _load_personal_config(self):
        if os.path.exists("config/conf.conf"):
            with open("config/conf.conf", "r") as f:
                self.cb_author.set(f.readline().strip())
                self.cb_area.set(f.readline().strip())
                self.cb_activity.set(f.readline().strip())
        else:
            self

    def open_popup(self):
        top = tk.Toplevel(self)
        top.geometry("200x100")
        top.title("Alert")
        tk.Label(top, text= "Please enter\nAuthor and Site", font=("Arial", 20)).pack()
        # location should be in the middle of the top level window
        x = (top.winfo_screenwidth() - top.winfo_reqwidth()) / 2
        y = (top.winfo_screenheight() - top.winfo_reqheight()) / 2
        top.geometry("+%d+%d" % (x, y))
        top.after(5000, top.destroy)

    def _check_if_essential_info_set(self):
        if self.cb_author.get() == "":
            self.cb_author.focus()
            return False
        elif self.cb_area.get() == "":
            self.cb_area.focus()
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
                
    def _assemble_filename_name_site_datetime_activity(self, path):
        filepath, extension = os.path.splitext(path)
        filename = os.path.basename(filepath).replace('_', '')
        filedate = self._get_filedate_str(path)
        author = self.cb_author.get()
        author_code = self.users_df[self.users_df['Full name'] == author]['Namecode'].values[0]
        site = self.cb_area.get()
        location, site = site.split(", ")
        site_string = self.divesites_df[(self.divesites_df['Location'] == location) & (self.divesites_df['Site'] == site)]['Site string'].values[0]
        activity = self.cb_activity.get()
        return f"{author_code}_{site_string}_{filedate}_{activity}_{filename}{extension}"
    
    def _assemble_filename_family_genus_species_details(self, path):
        filepath, extension = os.path.splitext(path)
        filename = os.path.basename(filepath)
        family = self.cb_family.get()
        genus = self.cb_genus.get()
        species = self.cb_species.get()
        confidence = self.cb_confidence.get()
        phase = self.cb_phase.get()
        colour = self.colour_dict[self.cb_colour.get()]
        behaviour = self.behaviour_dict[self.cb_behaviour.get()]

        return f"{family}_{genus}_{species}_B_{confidence}_{phase}_{colour}_{behaviour}_{filename}{extension}"


    def _dnd_files(self, event):
        files = self.splitlist(event.data)
        if not self._check_if_essential_info_set(): return
        for file in files:
            if self.fish_identification.get() == 0:
                filename = self._assemble_filename_name_site_datetime_activity(file)
            else:
                filename = self._assemble_filename_family_genus_species_details(file)
            os.rename(file, os.path.join(os.path.dirname(file), filename))

    def _row_selected(self, event):
        item = self.tree.selection()[0]
        family, genus, species, common_name = self.tree.item(item, 'values')
        self.cb_family.set(family)
        self.cb_genus.set(genus)
        self.cb_species.set(species)
        # self._set_preview()


    def _toggle_extended_info(self, event=None):
        unactive = self.fish_identification.get()
        self.cb_family.state(['disabled' if unactive else '!disabled'])
        self.cb_genus.state(['disabled' if unactive else '!disabled'])
        self.cb_species.state(['disabled' if unactive else '!disabled'])
        self.cb_confidence.state(['disabled' if unactive else '!disabled'])
        self.cb_phase.state(['disabled' if unactive else '!disabled'])
        self.cb_colour.state(['disabled' if unactive else '!disabled'])
        self.cb_behaviour.state(['disabled' if unactive else '!disabled'])

        self.cb_author.state(['!disabled' if unactive else 'disabled'])
        self.cb_area.state(['!disabled' if unactive else 'disabled'])
        self.cb_activity.state(['!disabled' if unactive else 'disabled'])

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
        self.cb_genus['values'] = self.genus_default + sorted(filtered['Genus'].unique())
        self.cb_genus.current(0)
        self.cb_species['values'] = self.species_default + sorted(filtered['Species'].unique())
        self.cb_species.current(0)
        self.clear_tree()
        self.fill_tree(filtered.values.tolist())

    def set_genus(self, event):
        genus = self.cb_genus.get()
        filtered = self.fish_df[self.fish_df['Genus'] == genus]
        family = filtered['Family'].iloc[0]
        self.cb_family.set(family)
        self.cb_genus.set(genus)
        self.cb_species['values'] = self.species_default + sorted(filtered['Species'].unique())
        self.cb_species.current(0)
        self.clear_tree()
        self.fill_tree(filtered.values.tolist())

    def set_species(self, event):
        species = self.cb_species.get()
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
        if os.path.exists("config/Species.csv"):
            self.fish_df = pd.read_csv('config/Species.csv', sep=';')
            # replace nan with ''
            self.fish_df = self.fish_df.fillna('')
           # print("config/Species.csv loaded")
        if os.path.exists("config/Photographers.csv"):
            self.users_df = pd.read_csv('config/Photographers.csv', sep=';')
            #print("config/Photographers.csv loaded")
        if os.path.exists("config/Divesites.csv"):
            self.divesites_df = pd.read_csv('config/Divesites.csv', sep=';')
            #print("config/Divesites.csv loaded")
        if os.path.exists("config/Activities.csv"):
            self.activities_df = pd.read_csv('config/Activities.csv', sep=';')
            #print("config/Activities.csv loaded")


    def _build_tree(self):
        for col in list(self.fish_df.columns):
            self.tree.heading(col, text=col.title(),
                command=lambda c=col: sortby(self.tree, c, 0))
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
        # get the data from the dataframe
        fish_filtered = self.fish_df[self.fish_df.apply(lambda row: any([search_string.lower() in value.lower() for value in row.values]), axis=1)]
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