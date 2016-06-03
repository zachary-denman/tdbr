
#!/usr/bin/env python2
"""
tdbr.py: This module contains the GUI for viewing unprocessed tunnel data. It
is the successor to the popular TDBrowser program written by Dr. Peter 
Jacobs, which was originally meant as a demonstration of how one could examine
shot data.

Author: Zachary J. Denman

Date: 26-May-2016
"""

# Features to add
#
# 1. Shock timing calculation (click a button and it returns a shock speed
# based on the current x bounds and distance in the config file)
# 2. Buttons for channel list
# 3. Wildcard plotting (with a limit). For printing groups e.g., P_IB*

from __future__ import print_function
import ConfigParser as configparser
import gzip
import matplotlib
matplotlib.use("tkagg", warn=False)
import matplotlib.pyplot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy
import os
import sys
import Tkinter as tk

class Application(tk.Frame):

    VERSION = 0.1

    def __init__(self, master):
        tk.Frame.__init__(self, master)

        self.print_welcome()

        # Set configuration options
        self.config = configparser.ConfigParser()
        self.config.read("tdbr.ini")
        
        if self.config.has_section("tdbr"):
            self.data_directory = self.config.get("tdbr","data_directory")
            self.facility = self.config.get("tdbr","facility")
            self.shot_number = self.config.get("tdbr","shot_number")
            self.channel = self.config.get("tdbr","channel")
            self.save_file = self.config.get("tdbr","save_file")
            self.data = []
            # For setting bounds
            self.x1 = [None, None]; self.x2 = [None, None]
            self.y1 = [None, None]; self.y2 = [None, None]
        else:
            print("No configuration file found. The configuration file must")
            print("placed in the same directory as tdbr.py.")
            print("Exiting.")
            sys.exit()
        
        self.startup_messages()
        self.create_widgets()
        self.bind_actions()

        return

    def print_welcome(self):
        """Prints a pretty welcome message."""

        print("==============================================================")
        print("|                                                            |")
        print("|          tdbr.py - tunnel data browser, reloaded           |")
        print("|                                                            |")
        print("|                                          Zachary J. Denman |")
        print("==============================================================")

        return

    def startup_messages(self):
        """Prints a few startup messages for the user."""

        print("Version:", Application.VERSION, sep=" ")
        print("Data directory:", self.data_directory, sep=" ")
        print("Facility:", self.facility, sep=" ")
        print("Ready.")

        return

    def quit(self):
        """Destroys the root frame after printing a message for the user."""
        
        self.master.quit()
        print("Exiting.")
        
        return

    def change_directory(self):
        """Changes the data directory i.e., where shot data is stored. If the
        current directory has not been changed, nothing happens.
        """

        new_directory = self.ddE.get()
        if new_directory == self.data_directory:
            print("Data directory already set.")
        else:
            self.data_directory = new_directory
            print("Changing data directory.")
            print("Data directory:", self.data_directory, sep=" ")

        return

    def current_cursor_position(self, event):
        """Stores the current cursor position inside the plot window."""
        if event.inaxes is not None:
            self.ccpxSV.set("x = %.6f" % event.xdata)
            self.ccpySV.set("y = %.6f" % event.ydata)

        return

    def set_bounds_on_click(self, event):
        """Used to set left and right bounds for zooming, calculating averages
        etc. 
        """

        # Don't set bounds (and then draw them) if there is no data.
        if self.data == []:
            return

        x, y = event.xdata, event.ydata
        
        if event.inaxes is not None:
            # Left click
            if event.button == 1:
                # Extra check for None needed as Python treats None funny when
                # checking greater/less than.
                if x > self.x2[0] and self.x2[0] is not None:
                    print("LEFT bound needs to be less than RIGHT bound.")
                    return
                else:
                    print("Changing left bound.")
                    self.x1[0] = x
                    self.mrx1eSV.set("%2.4e" % x)
            # Right click
            elif event.button == 3:
                if x < self.x1[0]:
                    print("RIGHT bound needs to be greater than LEFT bound.")
                    return
                else:
                    print("Changing right bound.")
                    self.x2[0] = x
                    self.mrx2eSV.set("%2.4e" % x)

            
        self.draw_bounds()
        self.calculate_stats()

        return

    def draw_bounds(self):
        """Draws the bounds set in either of the set bounds functions."""
        
        # Left bound
        if self.x1[1] is None:
            self.x1[1] = self.axes.axvline(self.x1[0], color="black")
        else:
            self.axes.lines.remove(self.x1[1])
            self.x1[1] = self.axes.axvline(self.x1[0], color="black")

        # Right bound
        if self.x2[1] is None:
            self.x2[1] = self.axes.axvline(self.x2[0], color="red")
        else:
            self.axes.lines.remove(self.x2[1])
            self.x2[1] = self.axes.axvline(self.x2[0], color="red")

        self.canvas.show()

        return

    def calculate_stats(self):
        """Calculates the range, mean, and standard deviation of the last
        channel plotted, if both x1 and x2 have been selected.
        """

        if (self.x1[0] is not None) and (self.x2[0] is not None):
            rng = self.x2[0] - self.x1[0]
            avg = self.data[-1].average_between_times(self.x1[0], self.x2[0])
            # dev = 5   

            self.mrx2x1lSV.set("x2-x1    = %.6f" % rng)
            self.mravglSV.set("Average = %.6f" % avg)
            # self.mrstdlSV.set("Std. Dev. = %2.4e" % dev)

        return

    def reset_bounds(self):
        """Resets the left and right bounds to None following the plotting of
        a channel, or clearing of the plot.
        """

        self.x1 = [None, None]; self.x2 = [None, None]
        self.y1 = [None, None]; self.y2 = [None, None]
        self.mrx1eSV.set("")
        self.mrx2eSV.set("")
        self.mrx2x1lSV.set("x2-x1    = 0.000000")
        self.mravglSV.set("Average = 0.000000")

        return

    def fetch_data(self, event=None):
        """Plots the data that the user has specified."""
        
        self.facility = self.feSV.get()
        self.shot_number = self.seSV.get()
        self.channel = self.ceSV.get()

        self.ifT.delete(1.0,tk.END)

        if self.channel == "":
            print("No channel specified. List of channels printed below.")
            self.data.append(TunnelData(self.shot_number, 
                self.data_directory, None))
            channel_names = self.data.pop(-1).channels
            self.ifT.insert(1.0, "\n".join(channel_names))
        else:
            print("Fetching facility", self.facility, sep=" ", end=",")
            print(" shot", self.shot_number, sep=" ", end=",")
            print(" channel", self.channel, sep=" ")

            # Add the channel we want to the list of data
            self.data.append(TunnelData(self.shot_number, 
                self.data_directory, self.channel).channels[0])

            self.plot_data()
            self.reset_bounds()

        return

    def get_help(self, event):
        """Opens a pop-up with instructions on how to use the program."""

        print("Showing help screen.")

        return

    def create_new_canvas(self):
        """Deletes current canvas and creates a new one. Actions are also
        rebound as they are lost when the old canvas is deleted.
        """

        if self.data != []:
            self.canvas.get_tk_widget().delete("all")

        self.figure = plt.figure(dpi=100, facecolor="white")
        self.axes = self.figure.add_subplot(111)
        # self.axes.set_autoscale_on(False)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.pF)
        self.canvas.show()
        self.canvas.get_tk_widget().grid(row=0, column=0, 
            sticky=tk.N+tk.S+tk.E+tk.W, padx=5, pady=5)

        # Need to rebind canvas actions as this is a new canvas
        self.bind_canvas_actions()

        return

    def plot_data(self):
        """Plots all of the data stored in self.data. This function is
        called as part of fetch_data.
        """

        self.create_new_canvas()

        for ch in self.data:
            label_str = ":".join([self.shot_number, self.channel])
            self.axes.plot(ch.times, ch.data, label=label_str)

        # self.axes.legend(loc="best")

        self.create_legend()
        self.canvas.show()
        
        return

    def create_legend(self):
        """Creates a legend object and places it in the legend frame."""

        self.legfigure = plt.figure(facecolor="white" ,figsize=(1,1))
        lines = self.axes.get_lines()
        labels = []
        for line in lines:
            labels.append(line.get_label())
        legend = plt.figlegend(lines, labels, loc="upper center")

        self.legcanvas = FigureCanvasTkAgg(self.legfigure, master=self.legF)
        self.legcanvas.get_tk_widget().grid(row=0, column=0,
            sticky=tk.N+tk.S+tk.E+tk.W)

        self.legF.rowconfigure(0, weight=1)
        self.legF.columnconfigure(0, weight=1)

        return

    def set_axes(self, event):
        """Function to set the axes of the plot frame based on object 
        attributes x1, x2, y1, and y2.
        """
        
        print("Setting axes.")
        self.axes.set_xlim([self.x1[0], self.x2[0]])
        
        # Rescale y-axis based on visible data.
        # Get the min, max y values in the channels plotted so far
        # THIS


        self.canvas.show()
        # self.axes.set_ylim([self.y1, self.y2])

        return

    def reset_axes(self, event):
        """Resets the axes to the max values in all stored channels."""

        print("Resetting axes.")
        min_x = self.x1[0]; max_x = self.x2[0]

        for ch in self.data:
            if min_x > min(ch.times): min_x = min(ch.times)
            if max_x < max(ch.times): max_x = max(ch.times)

        self.axes.set_xlim([min_x, max_x])

        # self.set_axes(event)
        self.canvas.show()

        return

    def clear_last_data(self):
        """Clear last data added to plot."""

        if len(self.data) > 0:
            print("Clearing last plotted channel.")
            del self.data[-1]
            self.reset_bounds()
            self.plot_data()
        else:
            print("Nothing to clear.")

        return

    def clear_data(self):
        """Deletes currently plotted data. Sets plotted data to empty list,
        creates a blank canvas for plotting, and resets the left/right bounds.
        """
        if len(self.data) > 0:
            print("Clearing all data.")
            self.data = []
            self.create_new_canvas()
            self.reset_bounds()
        else:
            print("Nothing to clear.")

        return

    def save_data(self):
        """Saves the data in a format ready for plotting in Gnuplot. It should
        be noted that the x value of the first plotted channel is used for all
        saved channels."""

        if self.data == []:
            print("Nothing to save.")
        else:
            print("Saving data.")
            print("Save file:", self.save_file, sep=" ")
            with open(self.save_file, "wt") as fp:
                # Create a header for the file
                header = []
                first_channel = True
                for ch in self.data:
                    if first_channel:
                        header.append("# " + ch.dataset + ":" + "time(s)")
                        first_channel = False
                    header.append(ch.dataset + ":" + ch.name + "(" + ch.units + ")")
                header.append("\n")
                fp.write(" ".join(header))
                # Create rows of data
                for i in range(self.data[0].number_data_points):
                    row_data = []
                    first_channel = True
                    for ch in self.data:
                        if first_channel:
                            row_data.append(str(ch.times[i]))
                            first_channel = False
                        row_data.append(str(ch.data[i]))
                    row_data.append("\n")
                    fp.write(" ".join(row_data))

        return

    def create_widgets(self):
        """Controls the creation of all widgets that form the GUI"""

        # The main frame which holds everything. This is the only widget that
        # is placed in the master (root) frame.
        self.mainframe = tk.Frame(root)

        # Packing the main window. 5 frames placed using the grid manager
        # 1. Data Selection
        # 2. Information Frame
        # 3. Plot Frame
        # 4. Status Frame
        # 5. Legend Frame
        # 6. Other Frame
        #
        # These frames may also contain further frames to aid with packing. 
        # The grid() geometry manage is used for a majority of the layout
        # management.

        # 1. Data Selection Frame
        self.dsF = tk.LabelFrame(self.mainframe, text="Data Selection")
        self.fL = tk.Label(self.dsF, text="Facility:")
        self.feSV = tk.StringVar()
        self.feSV.set(self.facility)
        self.fE = tk.Entry(self.dsF, textvariable=self.feSV, justify=tk.CENTER,
            width=10)
        self.sL = tk.Label(self.dsF, text="Shot:")
        self.seSV = tk.StringVar()
        self.seSV.set(self.shot_number)
        self.sE = tk.Entry(self.dsF, textvariable=self.seSV,justify=tk.CENTER,
            width=10)
        self.cL = tk.Label(self.dsF, text="Channel:")
        self.ceSV = tk.StringVar()
        self.ceSV.set(self.channel)
        self.cE = tk.Entry(self.dsF, textvariable=self.ceSV, justify=tk.CENTER,
            width=10)
        self.fB = tk.Button(self.dsF, text="Fetch", width=10, bg="lime green",
            activebackground="forest green", command=self.fetch_data)
        self.clB = tk.Button(self.dsF, text="Clear Last", width=10, bg="grey",
            activebackground="dim grey", command=self.clear_last_data)
        self.caB = tk.Button(self.dsF, text="Clear All", width=10, bg="grey",
            activebackground="dim grey", command=self.clear_data)
        self.ddL = tk.Label(self.dsF, text="Data Directory")
        self.ddeSV = tk.StringVar()
        self.ddeSV.set(self.data_directory)
        self.ddE = tk.Entry(self.dsF, textvariable=self.ddeSV, justify="left",
            width=25)
        self.cddB = tk.Button(self.dsF, text="Change", width=10,
            command=self.change_directory, bg="lime green",
            activebackground="forest green")
        self.sdL = tk.Label(self.dsF, text="Save File")
        self.sdeSV = tk.StringVar()
        self.sdE = tk.Entry(self.dsF, textvariable=self.sdeSV, justify="left",
            width=25)
        self.sdeSV.set(self.save_file)
        self.sdB = tk.Button(self.dsF, text="Save", width=10, bg="lime green",
            activebackground="forest green", command=self.save_data)

        # Layout for Data Selection frame
        self.fL.grid(row=0, column=0, sticky=tk.E)
        self.fE.grid(row=0, column=1, sticky=tk.W)
        self.sL.grid(row=1, column=0, sticky=tk.E)
        self.sE.grid(row=1, column=1, sticky=tk.W)
        self.cL.grid(row=2, column=0, sticky=tk.E)
        self.cE.grid(row=2, column=1, sticky=tk.W)
        self.fB.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        self.clB.grid(row=4, column=0, padx=5, pady=5, sticky=tk.E)
        self.caB.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
        self.ddL.grid(row=5, column=0, padx=5, sticky=tk.W)
        self.ddE.grid(row=6, column=0, columnspan=2, padx=5, sticky=tk.E+tk.W)
        self.cddB.grid(row=7, column=0, columnspan=2, padx=5, pady=5)
        self.sdL.grid(row=8, column=0, columnspan=2, padx=5, sticky=tk.W)
        self.sdE.grid(row=9, column=0, columnspan=2, padx=5, sticky=tk.E+tk.W)
        self.sdB.grid(row=10, column=0, columnspan=2, padx=5, pady=5)

        self.dsF.rowconfigure(0, weight=1)
        self.dsF.rowconfigure(1, weight=1)
        self.dsF.rowconfigure(2, weight=1)
        self.dsF.rowconfigure(3, weight=1)
        self.dsF.rowconfigure(4, weight=1)
        self.dsF.rowconfigure(5, weight=1)
        self.dsF.columnconfigure(0, weight=1)
        self.dsF.columnconfigure(1, weight=1)
        
        # 2. Information Frame
        self.iF  = tk.LabelFrame(self.mainframe, text="Information")

        self.ifT = tk.Text(self.iF, width=40)

        self.iftSB = tk.Scrollbar(self.iF)
        self.iftSB.grid(row=0, column=1, sticky=tk.N+tk.S+tk.E+tk.W)
        self.ifT.configure(yscrollcommand=self.iftSB.set)
        self.iftSB.config(command=self.ifT.yview)
        self.ifT.grid(row=0, column=0, sticky=tk.N+tk.S)

        self.iF.rowconfigure(0, weight=1)

        # 3. Plot Frame
        self.pF   = tk.LabelFrame(self.mainframe, text="Plot")

        self.create_new_canvas()

        self.pF.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        
        self.pF.rowconfigure(0, weight=1)
        self.pF.columnconfigure(0, weight=1)

        
        # 4. Legend Frame
        self.legF = tk.LabelFrame(self.mainframe, text="Legend", width=200)

        # 5. Status Frame
        self.sF = tk.Frame(self.mainframe)
        self.ccpLF = tk.LabelFrame(self.sF, text="Cursor Position")
        self.mrLF = tk.LabelFrame(self.sF, text="Marked Range")

        self.ccpLF.grid(row=0, column=0, sticky=tk.N+tk.S)
        self.mrLF.grid(row=0, column=1, sticky=tk.N+tk.S)

        self.ccpxSV = tk.StringVar(); self.ccpxSV.set("x = 0.000000")
        self.ccpxL = tk.Label(self.ccpLF, textvariable=self.ccpxSV, 
            anchor=tk.W, width=15)
        self.ccpySV = tk.StringVar(); self.ccpySV.set("y = 0.000000")
        self.ccpyL = tk.Label(self.ccpLF, textvariable=self.ccpySV,
            anchor=tk.W, width=15)

        self.mrx1L = tk.Label(self.mrLF, text="x1 =")
        self.mrx1eSV = tk.StringVar()
        self.mrx1E = tk.Entry(self.mrLF, width=10, textvariable=self.mrx1eSV)
        self.mrx2L = tk.Label(self.mrLF, text="x2 =")
        self.mrx2eSV = tk.StringVar()
        self.mrx2E = tk.Entry(self.mrLF, width=10, textvariable=self.mrx2eSV)
        self.mrx2x1lSV = tk.StringVar()
        self.mrx2x1lSV.set("x2-x1    = 0.000000")
        self.mrx2x1L = tk.Label(self.mrLF, textvariable=self.mrx2x1lSV,
            anchor=tk.W, width=20)
        self.mravglSV = tk.StringVar()
        self.mravglSV.set("Average = 0.000000")
        self.mravgL = tk.Label(self.mrLF, textvariable=self.mravglSV,
            anchor=tk.W)
        # self.mrstdlSV = tk.StringVar()
        # self.mrstdL = tk.Label(self.mrLF, text="StdDev = 0.0000",
        #     textvariable=self.mrstdlSV)

        self.ccpxL.grid(row=0, column=0, sticky=tk.W)
        self.ccpyL.grid(row=1, column=0, sticky=tk.W)

        self.mrx1L.grid(row=1, column=1, sticky=tk.E)
        self.mrx1E.grid(row=1, column=2, sticky=tk.W)
        self.mrx2L.grid(row=2, column=1, sticky=tk.E)
        self.mrx2E.grid(row=2, column=2, sticky=tk.W)
        self.mrx2x1L.grid(row=1, column=3, sticky=tk.W)
        self.mravgL.grid(row=2, column=3, sticky=tk.W)
        # self.mrstdL.grid(row=1, column=5, rowspan=2)

        self.ccpLF.rowconfigure(0, weight=1)
        self.ccpLF.columnconfigure(0, weight=1)

        self.mrLF.columnconfigure(0, weight=1)
        self.mrLF.columnconfigure(1, weight=1)
        self.mrLF.columnconfigure(2, weight=1)
        self.mrLF.columnconfigure(3, weight=1)
        self.mrLF.columnconfigure(4, weight=1)

        # 6. Other Frame
        self.oF = tk.Frame(self.mainframe)

        self.hB = tk.Button(self.oF, text="HELP", width=10, bg="dodger blue",
            activebackground="blue")
        self.qB = tk.Button(self.oF, text="QUIT", width=10, command=self.quit,
            bg="tomato", activebackground="red")

        self.hB.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N+tk.S)
        self.qB.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N+tk.S)

        self.oF.rowconfigure(0, weight=1)

        # Packing the self.mainframe's subframes
        self.dsF.grid(row=0, column=0, sticky=tk.E+tk.W)
        self.iF.grid(row=1, column=0, rowspan=2, sticky=tk.N+tk.S)
        self.pF.grid(row=0, column=1, rowspan=2, sticky=tk.N+tk.S+tk.E+tk.W) 
        self.legF.grid(row=0, column=2, rowspan=2, sticky=tk.N+tk.S+tk.E+tk.W)
        self.sF.grid(row=2, column=1, columnspan=1, sticky=tk.E+tk.W)
        self.oF.grid(row=2, column=2, columnspan=1, sticky=tk.E+tk.N+tk.S)

        # Configuring the grid geometry
        # An excessive weight is used for row/column 1 as this ensures that
        # the plot, is the the only widget that is effectively resized
        # Rows
        self.mainframe.rowconfigure(0, weight=1)
        self.mainframe.rowconfigure(1, weight=1000)
        self.mainframe.rowconfigure(2, weight=1)
        # Columns
        self.mainframe.columnconfigure(0, weight=1)
        self.mainframe.columnconfigure(1, weight=1000)
        self.mainframe.columnconfigure(2, weight=50)

        # Packing the self.mainframe and providing weights so that it expands 
        # to fill the root (root) frame.
        self.mainframe.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        return

    def bind_actions(self):
        
        self.master.protocol("WM_DELETE_WINDOW", self.quit)
        # self.fB.bind("<Button-1>", self.fetch_data)
        self.sE.bind("<Return>", self.fetch_data)
        self.sE.bind("<KP_Enter>", self.fetch_data)
        self.cE.bind("<Return>", self.fetch_data)
        # self.cE.bind("<KP_Enter>", self.fetch_data)
        # self.clB.bind("<Button-1>", self.clear_last_data)
        # self.caB.bind("<Button-1>", self.clear_data)
        self.hB.bind("<Button-1>", self.get_help)
        # self.qB.bind("<Button-1>", self.quit_button)
        self.master.bind("<F3>", self.set_axes)
        self.master.bind("<Shift-F3>", self.reset_axes)
        self.master.bind("<F4>", self.clear_last_data)
        self.master.bind("<Shift-F4>", self.clear_data)

        return

    def bind_canvas_actions(self):
        """Binds the canvas events. This is called whenever the plot canvas is
        drawn.
        """
        
        self.canvas.callbacks.connect('motion_notify_event',
            self.current_cursor_position)
        self.canvas.callbacks.connect('button_press_event',
            self.set_bounds_on_click)
        
        return 


class TunnelData:
    """This class contains all of the necessary functions used to load a dataset
    produced by the T4NIDAQ program into memory. This class does no 
    *processing* of data, just loading. A :py:class:`TunnelData` object is
    loaded based on the .config file in the directory of provided when
    creating it.
    """

    def __init__(self, name, directory, load="all"):
        """
        When a :py:class:`~.TunnelData` object is created, the config file for
        the dataset is read, and :py:class:`~.Channel` objects are created.

        :param str name: Name of the dataset. This could be a shot number or a
            calibration run.
        :param str directory: Directory containing data produced by T4NIDAQ 
            program; directory changes with each shot or calibration.
        :param list channels: List of :py:class:`~.Channel` objects.

        """

        self.name         = name
        self.directory    = directory

        # Sets what to load. By default, a channel.Channel object is created
        # for each channel in the config file. A single channel can also be
        # specified. If load is set to None, the names of the channels are 
        # loaded into the channels attribute. Useful for checking what is in
        # a certain shot e.g., for tdbr.py
        self.load         = load

        # List of channels read from .config file for specified shot_number.
        # This is actually a list of Channel objects.
        self.channels  = []
        
        # Read data for all channels listed in config file.
        self._read_data()

        return

        
    def _read_data(self, suffix=".config"):

        # Create the filename with absolute path to the config file. The
        # structure of the filename is: directory/name/name.config
        fname = os.path.join(self.directory, self.name, self.name + suffix)

        try:
            with open(fname, "r") as fp:
                line_number = 1
                for line in fp.readlines():
                    if line[0] == "#": # number of header lines in config file
                        pass
                    else:
                        line = line.split()
                        # Create a channel for each line in .config file
                        name, card_id, channel_id =\
                            line[0], int(line[1]),int(line[2])
                        if self.load == "all":
                            self.channels.append(Channel(self.name, name, 
                                self.directory, card_id, channel_id))
                        elif self.load == name:
                                self.channels.append(Channel(self.name, name, 
                                    self.directory, card_id, channel_id))
                        elif self.load == None:
                            self.channels.append(name)
        except EnvironmentError:
            print("Cannot find .config file. Path searched:", fname, sep=" ")

        return


class Channel:
    """
    This class is used to represent a single channel for each signal that is 
    recorded using the T4 data acquisition system. At least a shot_number, 
    name, card and card channel must be provided to create a 
    :py:class:`~.Channel` object.

    Other parameters that are not required for the initialisation are set for
    use in other parts of the program e.g., calibrations.

    :param int dataset: Name of dataset that the recorded channel is a part of.
        This could be a shot or a calibration dataset.
    :param str name: Name of channel
    :param int card: Card number
    :param int channel_id: Channel ID on card (0-7)
    :param int subchannel_id: Sub-channel ID. This was originally used for
        multiplexing. Assigned during initialisation. There should be no
        reason to be using this c. 2014.
    :param float external_gain: Gain of external amplifier e.g., 1E+2 for 
        Kulite pressure transducers
    :param float sensitivity: Sensitivity of transducer, V/unit
    :param str units: Units for sensitivity of transducer
    :param float position: Position of transducer (mm)
    :param str serial_no: Serial number of transducer. This is used to 
        identify the transducer in the database. **LINK**
    :param str transducer_type: Type of transducer e.g., pressure, temperature
    :param float min_volts: Minimum range of transducer (V)
    :param float max_volts: Maximum range of transducer (V)
    """

    def __init__(self, dataset, name, directory, card_id, channel_id):
        """
        Stuff here
        """
        # Config file values
        # self.shot_number     = shot_number
        self.dataset         = dataset # Name of dataset (shot or calibration name)
        self.name            = name # Name of channel in .config file
        self.directory       = directory 
        self.card_id         = card_id
        self.channel_id      = channel_id

        self.subchannel_id   = 0 # Used for multiplexing, should not be used
                                 # c. 2014 (actually well before this)

        # These values are read from the data file, not the .config file. They
        # are overwritten as each channel reads its data. Not assigned values
        # from .config file to make other pyshot functions easier.       
        self.external_gain   = 1E+0
        self.sensitivity     = 1E+0 #V/unit
        self.units           = "" #various
        self.position        = 0.0 #metres
        self.serial_no       = ""
        self.transducer_type = ""
        self.min_volts       = -10.0 #V
        self.max_volts       =  10.0 #V

        # Extra values read from the data file associated with the channel, or
        # other attributes that will be useful for data manipulations
        self.id                 = 100*int(self.card_id) +\
                                   10*int(self.channel_id)
        self.number_data_points = 0
        self.data               = None
        self.avg                = 0.0
        self.times              = None
        self.start_time         = 0.0
        self.dt                 = 0.0
        self.status             = True
        self.shifted            = False
        self.shift              = 0.0 #seconds

        self.read_channel_data()

        return None

    def read_channel_data(self):
        """
        Read in the data associated with this channel. This function is a
        rewrite of Rainer Kirchhartz's MATLAB function. 

        There is no need to read the .timing file now, as we are processing
        channels individually. The number of data points for each channel can
        be easily read from the header of each channel's data file.
        """

        fname = os.path.join(self.directory, 
                             self.dataset,
                            str(self.dataset) + "A." + str(self.id) + ".gz")
        fp = gzip.open(fname, "r")
        # print(fp)

        content = fp.read();  lines = content.split("\n"); fp.close()

        header = lines[0:22] # First 21 lines of each data file is the header
        datapoints = lines[23:-1] # Remainder is the actual recorded values
                                # in units determined by sensitivity

        # Process the header
        channel_dict = {}
        for line in header:
            line = line.strip().split()
            channel_dict[line[1]] = line[2]

        # Now process the dictionary items and assign the relevant ones to
        # their corresponding attribute.
        for key, value in channel_dict.items():
            if key == "gain":
                self.gain = float(value)
            elif key == "transducerSensitivity":
                self.sensitivity = float(value)
            elif key == "dataUnits":
                self.units = value
            elif key == "transducerLocation":
                self.position = value
            elif key == "transducerSerialNumber":
                self.serial_no = value
            elif key == "transducerType":
                self.transducer_type = value
            elif key == "dataPoints":
                self.number_data_points = int(value)
            elif key == "timeStart":
                self.start_time = float(value)
            elif key == "timeInterval":
                self.dt = float(value)

        # Remove trailing whitespace/newline characters and convert to float
        # Also, create a self.times object that contains the corresponding
        # time for that data point.
        times = []
        for i in range(len(datapoints)):
            datapoints[i] = float(datapoints[i].strip())
            times.append(self.start_time + i*self.dt)

        self.data = numpy.array(datapoints, dtype=float)
        self.times = numpy.array(times, dtype=float)

        fp.close()

        return

    def average_between_times(self, start, end):
        """
        Returns the average value of a set of data between start and end.

        :param float start: Start time e.g., start of test
        :param float end: End time e.g., end of test
        """
        
        start_index = self.find_nearest_index(self.times, start)
        end_index = self.find_nearest_index(self.times, end)

        average = numpy.average(self.data[start_index:end_index])

        return average

    def find_nearest_index(self, array,value):
        """
        Returns the index of the value nearest to value.

        :param numpy.array array: Numpy array of data
        :param float value: Value whose index you want to find
        """

        idx = (numpy.abs(array-value)).argmin()

        return idx

    def __str__(self):
        return str(self.dataset) + ": " + str(self.name)


if __name__ == '__main__':
    # Create an instance of the application
    root = tk.Tk()
    root.wm_title("TDBr v0.1")
    app = Application(master=root)

    # Run the applications
    app.mainloop()