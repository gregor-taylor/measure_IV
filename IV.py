import numpy as np
import tkinter as tk
from tkinter import Tk, Frame, ttk, messagebox
from tkinter.filedialog import asksaveasfile
from hardware import SIM900
import matplotlib.pyplot as plt
from visa import *
import time
import csv

class IVMeasure(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        Tk.wm_title(self, "IV")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        container=ttk.Frame(self)
        container.pack(side='top', fill='both', expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.rm = ResourceManager()
        self.VSrcSlot=tk.StringVar()
        self.VMeasSlot=tk.StringVar()
        self.VLower=tk.DoubleVar()
        self.VUpper=tk.DoubleVar()
        self.VStep=tk.DoubleVar()
        self.R=tk.DoubleVar()
        self.R.set(100000)
        self.Shunt=tk.DoubleVar()
        self.Shunt.set(50)
        self.isSaved=False
        self.dataTaken=False

        self.frames={}
        self.frames[MainPage]=MainPage(container, self)
        self.frames[MainPage].grid(row=0, column=0, sticky='nsew')

        self.show_frame(MainPage)

    def show_frame(self, cont):
        #Raises the chosen page to the top.
        frame = self.frames[cont]
        frame.tkraise()

    def on_close(self):
        if self.isSaved==False:
            if messagebox.askokcancel("Quit", "Data is not saved! Quit anyway?"):
                self.destroy()
        else:
            self.destroy()


class MainPage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.get_devices(controller)
        self.grid()

        ttk.Label(self, text="SIM address:").grid(row=1,column=1)
        self.SIM900_add_entry=ttk.Combobox(self, values=self.dev_list)
        self.SIM900_add_entry.grid(row=1,column=2)
        ttk.Label(self, text="Voltage source slot:").grid(row=2,column=1)
        self.V_src_entry=ttk.Entry(self, textvariable=controller.VSrcSlot)
        self.V_src_entry.grid(row=2, column=2)
        ttk.Label(self, text="Voltage measurement slot:").grid(row=3,column=1)
        self.V_meas_entry=ttk.Entry(self, textvariable=controller.VMeasSlot)
        self.V_meas_entry.grid(row=3, column=2)
        ttk.Label(self, text="Shunt (Ohm):").grid(row=4,column=1)
        self.Shunt_entry=ttk.Entry(self, textvariable=controller.Shunt)
        self.Shunt_entry.grid(row=4, column=2)

        ttk.Label(self, text="Lower voltage:").grid(row=1,column=3)
        self.V_lower_entry=ttk.Entry(self, textvariable=controller.VLower)
        self.V_lower_entry.grid(row=1, column=4)
        ttk.Label(self, text="Upper voltage:").grid(row=2,column=3)
        self.V_upper_entry=ttk.Entry(self, textvariable=controller.VUpper)
        self.V_upper_entry.grid(row=2, column=4)
        ttk.Label(self, text="Voltage step:").grid(row=3,column=3)
        self.V_step_entry=ttk.Entry(self, textvariable=controller.VStep)
        self.V_step_entry.grid(row=3, column=4)
        ttk.Label(self, text="Resistor (Ohm):").grid(row=4,column=3)
        self.R_entry=ttk.Entry(self, textvariable=controller.R)
        self.R_entry.grid(row=4, column=4)

        self.go_butt=ttk.Button(self, text='Perform IV', command=lambda:self.do_IV(controller))
        self.go_butt.grid(row=5, column=1, columnspan=2)
        self.save_butt=ttk.Button(self, text='Save it', command=lambda:self.save_IV(controller))
        self.save_butt.grid(row=6, column=1, columnspan=2)
        self.plot_butt=ttk.Button(self, text='Plot it', command=lambda:self.plot_IV(controller))
        self.plot_butt.grid(row=7, column=1, columnspan=2)
        ttk.Label(self, text="Progress:").grid(row=6,column=3, columnspan=2)
        self.progress = ttk.Progressbar(self, orient='horizontal', length=250, mode='determinate') 
        self.progress.grid(row=7, column=3, columnspan=2)

        #This is such an irritating way of making Tkinter widgets resize...
        self.grid_columnconfigure(1,weight=1)
        self.grid_columnconfigure(2,weight=1)
        self.grid_columnconfigure(3,weight=1)
        self.grid_columnconfigure(4,weight=1)
        self.grid_rowconfigure(1,weight=1)
        self.grid_rowconfigure(2,weight=1)
        self.grid_rowconfigure(3,weight=1)
        self.grid_rowconfigure(4,weight=1)
        self.grid_rowconfigure(5,weight=1)
        self.grid_rowconfigure(6,weight=1)
        self.grid_rowconfigure(7,weight=1)

    def get_devices(self, controller):
        self.dev_list = controller.rm.list_resources()

    def do_IV(self, controller):
        #Sets isSaved to False for new IV
        controller.isSaved = False
        controller.dataTaken=False
        #Sets up SIM
        controller.sim900 = SIM900(self.SIM900_add_entry.get())
        #Calculate parameters for IV
        VLower=controller.VLower.get()
        VUpper=controller.VUpper.get()
        VStep=controller.VStep.get()
        self.SupplyResistor=controller.R.get()
        self.numberDatapoints=len(np.arange(VLower,VUpper+VStep,VStep))*2
        self.progressInterval=100/(self.numberDatapoints+1)
        #Voltages - probably a better way to do this?
        self.Voltages=[]
        self.Voltage_ID=0
        #0 to upper
        for i in np.arange(0,(VUpper+VStep),VStep):
            self.Voltages.append(i)
        #Back to 0
        for i in np.arange(VUpper,(0-VStep),-VStep):
            self.Voltages.append(i)
        #0 to lower
        for i in np.arange(0,(VLower-VStep),-VStep):
            self.Voltages.append(i)
        #back to 0
        for i in np.arange(VLower,(0+VStep),VStep):
            self.Voltages.append(i)
        #Time started
        self.timeStart=time.time()
        #Data holders
        self.Voltage1=[]
        self.Voltage2=[]
        self.TimeStamps=[]
        #Do the IV
        self.take_IV_data(controller, self.Voltage_ID)
        
    def take_IV_data(self, controller, voltage_id):
        controller.sim900.write(controller.VSrcSlot.get(),'OPON')
        controller.sim900.write(controller.VSrcSlot.get(), 'VOLT {}'.format(round(self.Voltages[voltage_id],2)))
        self.TimeStamps.append(time.time()-self.timeStart)
        self.Voltage1.append(controller.sim900.ask(controller.VMeasSlot.get(),'VOLT? 1,1').strip())
        self.Voltage2.append(controller.sim900.ask(controller.VMeasSlot.get(),'VOLT? 2,1').strip())
        self.Voltage_ID+=1
        if self.Voltage_ID<len(self.Voltages):
            self.progress.step(self.progressInterval)
            controller.after(1000, self.take_IV_data, controller, self.Voltage_ID)
        else:
            #Process the data into useful arrays
            controller.sim900.write(controller.VSrcSlot.get(),'OPOFF')
            self.SupplyVoltage=np.asarray(self.Voltage1, dtype='float')
            self.DevVoltage=np.asarray(self.Voltage2, dtype='float')
            self.BiasCurrent=self.SupplyVoltage/self.SupplyResistor
            self.DevCurrent=(self.SupplyVoltage-self.DevVoltage)/self.SupplyResistor
            controller.dataTaken=True
            messagebox.showinfo("Success!", "IV completed")
        
    def plot_IV(self, controller):
        if controller.dataTaken == False:
            messagebox.showerror("Error", "No data taken")
        else:           
            plt.plot(self.DevVoltage, (self.DevCurrent*1e6)) #convert to uA
            plt.title('IV plot, Shunt of {} Ohm, BiasR of {} ohm'.format(controller.Shunt.get(), controller.R.get()))
            plt.xlabel('Voltage over device(V)')
            plt.ylabel('Current over device(uA)')
            plt.grid()
            plt.show()
    def save_IV(self, controller):
        if controller.dataTaken == False:
            messagebox.showerror("Error", "No data taken")
        else:
            #put into csv
            to_write=zip(self.TimeStamps, self.SupplyVoltage, self.DevVoltage, self.BiasCurrent, self.DevCurrent)
            fname=asksaveasfile(mode='w', defaultextension='.txt')
            writer_obj=csv.writer(fname, delimiter=',')
            writer_obj.writerow(['Timestamp (s)', 'Supply Voltage (V)', 'Device Voltage (V)', 'Bias Current (A)', 'Device Current (A)'])
            for item in to_write:
                writer_obj.writerow(item)
            controller.isSaved=True
            messagebox.showinfo("Success!", "Data saved")

def main():
    app = IVMeasure()
    app.geometry("580x190")
    app.mainloop()

if __name__ == '__main__':
    main()

