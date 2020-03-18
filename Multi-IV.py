#Similar to the previous version but adds the ability to do multiple IV's at different temperatures by controlling the voltage to a heater in the cryostat.
#Note in multi IV mode the data will all be saved automatically rather than you having to select it. 
#Plotting of multi IVs currently not supported.

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
        self.NoIVs=tk.IntVar()
        self.NoIVs.set(1)
        self.HeaterLowerV = tk.DoubleVar()
        self.HeaterUpperV = tk.DoubleVar()
        self.HeaterSlot = tk.StringVar()
        self.ThermSlot = tk.StringVar()
        self.LIS = tk.StringVar()

        self.IV_dict = {}

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
        ttk.Label(self, text="Number IVs:").grid(row=5,column=1)
        self.Num_IV_entry=ttk.Entry(self, textvariable=controller.NoIVs)
        self.Num_IV_entry.grid(row=5, column=2)
        ttk.Label(self, text="Heater VSrc slot:").grid(row=6,column=1)
        self.Heater_slot_entry=ttk.Entry(self, textvariable=controller.HeaterSlot)
        self.Heater_slot_entry.grid(row=6, column=2)
        ttk.Label(self, text="Therm slot:").grid(row=7,column=1)
        self.Therm_slot_entry=ttk.Entry(self, textvariable=controller.ThermSlot)
        self.Therm_slot_entry.grid(row=7, column=2)

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
        ttk.Label(self, text="Heater lower V:").grid(row=5,column=3)
        self.lowerV_entry=ttk.Entry(self, textvariable=controller.HeaterLowerV)
        self.lowerV_entry.grid(row=5, column=4)
        ttk.Label(self, text="Heater upper V:").grid(row=6,column=3)
        self.upperV_entry=ttk.Entry(self, textvariable=controller.HeaterUpperV)
        self.upperV_entry.grid(row=6, column=4)
        ttk.Label(self, text="Lock-In Scale (V):").grid(row=7,column=3)
        self.LIS_entry=ttk.Entry(self, textvariable=controller.LIS)
        self.LIS_entry.grid(row=7, column=4)

        self.go_butt=ttk.Button(self, text='Perform IV', command=lambda:self.do_IV(controller))
        self.go_butt.grid(row=8, column=1, columnspan=2)
        self.save_butt=ttk.Button(self, text='Save it', command=lambda:self.save_IV(controller))
        self.save_butt.grid(row=9, column=1, columnspan=2)
        self.plot_butt=ttk.Button(self, text='Plot it', command=lambda:self.plot_IV(controller))
        self.plot_butt.grid(row=10, column=1, columnspan=2)
        ttk.Label(self, text="Progress:").grid(row=9,column=3, columnspan=2)
        self.progress = ttk.Progressbar(self, orient='horizontal', length=250, mode='determinate') 
        self.progress.grid(row=10, column=3, columnspan=2)

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
        self.grid_rowconfigure(8,weight=1)
        self.grid_rowconfigure(9,weight=1)
        self.grid_rowconfigure(10,weight=1)


    def get_devices(self, controller):
        self.dev_list = controller.rm.list_resources()

    def do_IV(self, controller):
        #isSaved to False for new IV
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
        self.LockInSig = []
        #Do the IV
        if controller.NoIVs.get() == 1: #if just doing the one
            self.take_IV_data(controller, self.Voltage_ID)
        else: #multi IV and save
            self.heating_points = np.linspace(controller.HeaterLowerV.get(), controller.HeaterUpperV.get(),controller.NoIVs.get())
            self.heater_point_id = 0
            controller.sim900.write(controller.HeaterSlot.get(),'OPON')
            controller.sim900.write(controller.HeaterSlot.get(), 'VOLT {}'.format(round(self.heating_points[self.heater_point_id],2)))
            #wait for temo to settle and start taking data (5 mins)
            controller.after(300000, self.take_IV_data, controller, self.Voltage_ID)
                   
    def take_IV_data(self, controller, voltage_id):
        controller.sim900.write(controller.VSrcSlot.get(),'OPON')
        controller.sim900.write(controller.VSrcSlot.get(), 'VOLT {}'.format(round(self.Voltages[voltage_id],2)))
        self.TimeStamps.append(time.time()-self.timeStart)
        self.Voltage1.append(controller.sim900.ask(controller.VMeasSlot.get(),'VOLT? 1,1').strip())
        self.Voltage2.append(controller.sim900.ask(controller.VMeasSlot.get(),'VOLT? 2,1').strip())
        self.LockInSig.append(controller.sim900.ask(controller.VMeasSlot.get(),'VOLT? 3,1').strip())
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
            if controller.LIS.get() != '':
                self.LockInSigArr=np.asarray(self.LockInSig, dtype='float')
            controller.dataTaken=True
            if controller.NoIVs.get() == 1:
                messagebox.showinfo("Success!", "IV completed")
            else:
                Stage = controller.sim900.ask(controller.ThermSlot.get(), 'TVAL? 1').strip()
                Plate = controller.sim900.ask(controller.ThermSlot.get(), 'TVAL? 2').strip()
                Finger = controller.sim900.ask(controller.ThermSlot.get(), 'TVAL? 3').strip()
                if controller.LIS.get() == '':
                    to_write=zip(self.TimeStamps, self.SupplyVoltage, self.DevVoltage, self.BiasCurrent, self.DevCurrent)
                    fname = 'IV_{}_{}_{}.txt'.format(Stage.replace('.','p'), Plate.replace('.','p'), Finger.replace('.','p'))
                else:
                    to_write=zip(self.TimeStamps, self.SupplyVoltage, self.DevVoltage, self.BiasCurrent, self.DevCurrent, self.LockInSigArr)
                    fname = 'IV_{}_{}_{}_LockInScale_{}.txt'.format(Stage.replace('.','p'), Plate.replace('.','p'), Finger.replace('.','p'),controller.LIS.get())
                controller.IV_dict[Finger] = fname
                with open(fname, 'w') as filename:
                    writer_obj=csv.writer(filename, delimiter=',')
                    if controller.LIS.get() == '':
                        writer_obj.writerow(['Timestamp (s)', 'Supply Voltage (V)', 'Device Voltage (V)', 'Bias Current (A)', 'Device Current (A)'])
                    else:
                        writer_obj.writerow(['Timestamp (s)', 'Supply Voltage (V)', 'Device Voltage (V)', 'Bias Current (A)', 'Device Current (A)', 'Lock In Signal'])
                    for item in to_write:
                        writer_obj.writerow(item)
                self.heater_point_id+=1
                if self.heater_point_id < len(self.heating_points):
                    self.Voltage_ID=0
                    self.Voltage1=[]
                    self.Voltage2=[]
                    self.TimeStamps=[]
                    self.LockInSig = []
                    self.timeStart=time.time()
                    #increase heater V
                    controller.sim900.write(controller.HeaterSlot.get(),'OPON')
                    controller.sim900.write(controller.HeaterSlot.get(), 'VOLT {}'.format(round(self.heating_points[self.heater_point_id],2)))
                    #wait for temo to settle and take data (5 mins)
                    controller.after(300000, self.take_IV_data, controller, self.Voltage_ID)
                else:
                    controller.isSaved=True
                    messagebox.showinfo("Success!", "IVs done and saved")
        
    def plot_IV(self, controller):
        if controller.dataTaken == False:
            messagebox.showerror("Error", "No data taken")
        elif controller.NoIVs == 1:           
            plt.plot(self.DevVoltage, (self.DevCurrent*1e6)) #convert to uA
            plt.title('IV plot, Shunt of {} Ohm, BiasR of {} ohm'.format(controller.Shunt.get(), controller.R.get()))
            plt.xlabel('Voltage over device(V)')
            plt.ylabel('Current over device(uA)')
            plt.grid()
            plt.show()
        else:
            legends=[]
            for k, v in controller.IV_dict.items():
                legends.append(k)
                dev_I=[]
                dev_V=[]
                with open(v) as file:
                    reader_obj=csv.reader(file, delimiter=',')
                    for row in reader_obj:
                        dev_I.append(row[4])
                        dev_V.append(row[2])
                dev_I_arr=np.asarray(dev_I, dtype='float')*1e6
                dev_V_arr=np.asarray(dev_V, dtype='float')
                plt.plot(dev_V_arr, dev_I_arr)
            plt.title('IVs')
            plt.xlabel('Voltage over device(V)')
            plt.ylabel('Current over device(uA)')
            plt.grid()
            plt.legend(legends)
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
    app.geometry("580x230")
    app.mainloop()

if __name__ == '__main__':
    main()

