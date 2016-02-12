# -*- coding:utf-8 -*-

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
debug_monitor.py

Usage:
debug_monitor  [--option=<option>] <serial_port>
debug_monitor -h | --help
debug_monitor -v | --version

Options:
--option=<option>               option
<serial_port>                   port name for serial input
-h --help                       Show this screen.
-v --version                    Show version.
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
from __future__ import unicode_literals
import re
import sys, time
import serial
import curses
import csv
from   docopt import docopt
from   glob import glob
from collections import deque
#import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

__author__  = "Miura Daichi"
__NAME__    = "debug_monitor"
__status__  = "experimental"
__version__ = "0.0.1"
__date__    = "February 10, 2016"

class CommonParam:
    vad_max = 5.25
    div_num = 256.0
    mcp_vref = 0.5
    mcp_temp_coef = 0.01 # [V/℃]
    @classmethod
    def convert_temp(cls, ad):
        vout = ad * CommonParam.vad_max/CommonParam.div_num
        return (vout - CommonParam.mcp_vref) / CommonParam.mcp_temp_coef

class Battery:
    def __init__(self, v, c, t1, t2, t_avg):
        self.v = v
        self.c = c
        self.t1 = t1
        self.t2 = t2
        self.t_avg = t_avg
        self.vref = 1.47
        self.gain = 100.0
        self.rshunt = 0.022
    def supply(self):
        return (self.c*CommonParam.vad_max/CommonParam.div_num-self.vref)/(self.gain*self.rshunt) \
                *self.v*2.0*CommonParam.vad_max/CommonParam.div_num
    def voltage(self):
        return self.v * 2.0 * CommonParam.vad_max / CommonParam.div_num
    def temp_t1(self):
        return CommonParam.convert_temp(self.t1)
    def temp_t2(self):
        return CommonParam.convert_temp(self.t2)
    def temp_t_avg(self):
        return CommonParam.convert_temp(self.t_avg)

class PV:
    def __init__(self, v, c):
        self.v = v
        self.c = c
        self.vref = 0.0
        self.gain = 100.0
        self.rshunt = 0.062
    def supply(self):
        return (self.c*CommonParam.vad_max/CommonParam.div_num-self.vref)/(self.gain*self.rshunt) \
                *self.v*CommonParam.vad_max/CommonParam.div_num

class PowPic:
    def __init__(self, c):
        self.c = c
        self.vref = 0.0
        self.gain = 100.0
        self.rshunt = 0.15
    def consumption(self):
        return (self.c*CommonParam.vad_max/CommonParam.div_num-self.vref)/ \
                (self.gain*self.rshunt)*CommonParam.vad_max

class Main:
    def __init__(self, c, sel):
        self.c = c
        self.sel = sel
        self.rshunt = 0.56
        self.rext = 180.0
    def consumption(self):
        return (self.c*CommonParam.vad_max/CommonParam.div_num)/ \
                (self.rshunt*20.0*self.rext/(self.rext-100))*CommonParam.vad_max

class ComPic:
    def __init__(self, c, sel):
        self.c = c
        self.sel = sel
        self.rshunt = 0.56
        self.rext = 180.0
    def consumption(self):
        return (self.c*CommonParam.vad_max/CommonParam.div_num)/ \
                (self.rshunt*20.0*self.rext/(self.rext-100))*CommonParam.vad_max

class Pannel:
    def __init__(self, px, nx, py, ny, pz, nz):
        self.px = px
        self.nx = nx        
        self.py = py
        self.ny = ny
        self.pz = pz
        self.nz = nz
    def temp_py(self):
        return CommonParam.convert_temp(self.py)
    def temp_ny(self):
        return CommonParam.convert_temp(self.ny)
    def temp_pz(self):
        return CommonParam.convert_temp(self.pz)
    def temp_nz(self):
        return CommonParam.convert_temp(self.nz)

class ComA:
    def __init__(self, v, c):
        self.v = v
        self.c = c
        self.rshunt = 0.1
        self.rext = 180.0
    def consumption(self):
        return (self.c*CommonParam.vad_max/CommonParam.div_num)/ \
                (self.rshunt*20.0*self.rext/(self.rext-100))*    \
                (2.0*self.v*CommonParam.vad_max/CommonParam.div_num)

class ComB:
    def __init__(self, v, tx_c, rx_c):
        self.v = v
        self.tx_c = tx_c
        self.rx_c = rx_c
        self.rshunt = 0.1
        self.rext = 180.0
    def consumption_tx(self):
        return (self.tx_c*CommonParam.vad_max/CommonParam.div_num)/ \
                (self.rshunt*20.0*self.rext/(self.rext-100))*    \
                (2.0*self.v*CommonParam.vad_max/CommonParam.div_num)

    def consumption_rx(self):
        return (self.rx_c*CommonParam.vad_max/CommonParam.div_num)/ \
                (self.rshunt*20.0*self.rext/(self.rext-100))*CommonParam.vad_max

class InputData:
    def __init__(self, serial_input):
        self.timestamp, self.comsys, self.antA, self.bat, self.pv, self.powp, self.main,\
        self.comp, self.pannel, self.comA, self.comB = self.__parse(serial_input)
    def __parse(self, serial_input):
        sep = serial_input.split(",")
        timestamp = sep[0]
        sep = map(lambda x: float(x), sep[1:])
        return [timestamp, sep[0], sep[1],
                Battery(sep[2],sep[3],sep[4],sep[5],sep[6]),
                PV(sep[7],sep[8]), PowPic(sep[9]),
                Main(sep[10],sep[11]), ComPic(sep[12],sep[13]),
                Pannel(sep[14],sep[15],sep[16],sep[17],sep[18],sep[19]),
                ComA(sep[20],sep[21]), ComB(sep[22],sep[23],sep[24])]
    def members(self):
        members = [self.timestamp, self.comsys, self.antA, self.bat.v, self.bat.c, self.bat.t1,
                   self.bat.t2, self.bat.t_avg, self.pv.v, self.pv.c, self.powp.c,
                   self.main.c, self.main.sel, self.comp.c, self.comp.sel,
                   self.pannel.px, self.pannel.nx,self.pannel.py, self.pannel.ny,
                   self.pannel.pz, self.pannel.nz,
                   self.comA.v, self.comA.c, self.comB.v, self.comB.tx_c, self.comB.rx_c]
        return members
    def total_supply(self):
        return self.pv.supply() + self.bat.supply()
    def total_consumption(self):
        return self.powp.consumption() + self.main.consumption() + self.comp.consumption() + \
                self.comA.consumption() + self.comB.consumption_tx() + self.comB.consumption_rx()
    def power_balance(self):
        return self.total_supply() - self.total_consumption()

class DebugStatus:
    def __init__(self):
        self.hist_maxlen = 100
        self.history = deque([], maxlen=self.hist_maxlen)
        init_input = "16/1/1/1:1:1,0,0,0,0,0,0,0,0,0,0," + \
                            "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0"        
        init_data = InputData(init_input)
        self.history.extend([init_data]*self.hist_maxlen)
    def append(self, data):
        self.history.appendleft(data)
    def pv_hist(self):
        return [x.pv.supply() for x in self.history][::-1]
    def bat_voltage_hist(self):
        return [x.bat.voltage() for x in self.history][::-1]
    def bat_temp_t1_hist(self):
        return [x.bat.temp_t1() for x in self.history][::-1]
    def bat_temp_t2_hist(self):
        return [x.bat.temp_t2() for x in self.history][::-1]
    def bat_temp_t_avg_hist(self):
        return [x.bat.temp_t_avg() for x in self.history][::-1]
    def pannel_temp_py_hist(self):
        return [x.pannel.temp_py() for x in self.history][::-1]
    def pannel_temp_ny_hist(self):
        return [x.pannel.temp_ny() for x in self.history][::-1]
    def pannel_temp_pz_hist(self):
        return [x.pannel.temp_pz() for x in self.history][::-1]
    def pannel_temp_nz_hist(self):
        return [x.pannel.temp_nz() for x in self.history][::-1]

class DebugMonitor:
    def __init__(self, serial_port):
        self.sig_num = 26
        self.screen = curses.initscr()
        self.subwin = self.screen.subwin(10, 10, 30, 0)
        self.subwin.box()
        self.subwin.nodelay(1)
        self.serial = None
        self.serial_port = serial_port
        self.fig = plt.figure()
        self.last_reset_time = time.time()
        self.log_count = 0;
        self.command_ch = None
        self.output_file = open("log/"+"_".join(time.ctime().split(" ")[1:4])+".csv", "w")
        self.output_writer = csv.writer(self.output_file, lineterminator='\n')
        self.output_file_birthtime = time.time()
        self.output_file_ttl = 3600 # time to live [sec]
    def __enter__(self):
        curses.noecho()
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        curses.echo()
        curses.endwin()
        self.output_file.close()
        return True
    def __debug_print(self, input_data):
        self.screen.refresh()
        self.screen.clrtobot()
        self.subwin.refresh()
        self.log_count = self.log_count + 1
        def printline(pos, string):
            self.screen.addstr(pos, 0, string)
        printline(0, "comsys : A") if input_data.comsys == 255 else printline(0, "comsys : B")
        printline(1, "antenna : open") if input_data.antA == 255 else printline(1, "antenna : closed")
        printline(2, "pv supply[W]                 = %s" % str(input_data.pv.supply()))
        printline(3, "battery supply[W]            = %s" % str(input_data.bat.supply()))
        printline(4, "total supply[W]              = %s" % str(input_data.total_supply()))
        printline(5, "powp consumption[W]          = %s" % str(input_data.powp.consumption()))
        printline(6, "main consumption[W]          = %s" % str(input_data.main.consumption()))
        printline(7, "comp consumption[W]          = %s" % str(input_data.comp.consumption()))
        printline(8, "comA consumption[W]          = %s" % str(input_data.comA.consumption()))
        printline(9, "comB consumption_tx[W]       = %s" % str(input_data.comB.consumption_tx()))
        printline(10, "comB consumption_rx[W]       = %s" % str(input_data.comB.consumption_rx()))
        printline(11, "total consumption[W]         = %s" % str(input_data.total_consumption()))
        printline(12, "power balance[W]             = %s"% str(input_data.power_balance()))
        printline(13, "battery voltage[V]           = %s" % str(input_data.bat.voltage()))
        printline(14, "battery t1 temperature[C]    = %s" % str(input_data.bat.temp_t1()))
        printline(15, "battery t2 temperature[C]    = %s" % str(input_data.bat.temp_t2()))
        printline(16, "battery t_avg temperature[C] = %s" % str(input_data.bat.temp_t_avg()))
        printline(17, "pannel py temperature[C]     = %s" % str(input_data.pannel.temp_py()))
        printline(18, "pannel ny temperature[C]     = %s" % str(input_data.pannel.temp_ny()))
        printline(19, "pannel pz temperature[C]     = %s" % str(input_data.pannel.temp_pz()))
        printline(20, "pannel nz temperature[C]     = %s" % str(input_data.pannel.temp_nz()))
        printline(21, "elapsed from last reset[sec] = %s" % str(time.time()-self.last_reset_time))
        printline(22, "log count = %s" % str(self.log_count))
        curses.echo()
        command = self.subwin.getch()
        self.sendCommand(command)
        curses.noecho()
    def __draw_graphs(self, status):
        ax1 = self.fig.add_subplot(421)
        ax2 = self.fig.add_subplot(422)
        ax3 = self.fig.add_subplot(423)
        ax4 = self.fig.add_subplot(424)
        ax5 = self.fig.add_subplot(425)
        ax6 = self.fig.add_subplot(426)
        ax7 = self.fig.add_subplot(427)
        ax8 = self.fig.add_subplot(428)
        def draw(ax, data, name, ylabel, ylim):
            ax.plot(np.arange(0, status.hist_maxlen, 1), data, 'r-',label=name)
            ax.set_title(name)
            #ax.set_xlabel("Time")
            ax.set_ylabel(ylabel)
            #ax.legend()
            ax.grid()
            ax.set_xlim([1,100])
            ax.set_ylim(ylim)
        draw(ax1, status.bat_voltage_hist(), "Battery Voltage", "Voltage[V]", [0, 5])
        draw(ax3, status.bat_temp_t1_hist(), "Battery Temperature(t1)", "Temperature[°C]", [-10, 100])
        draw(ax5, status.bat_temp_t2_hist(), "Battery Temperature(t2)", "Temperature[°C]", [-10, 100])
        draw(ax7, status.bat_temp_t_avg_hist(), "Battery Temperature(t_avg)", "Temperature[°C]", [-10, 100])
        draw(ax2, status.pannel_temp_py_hist(), "Pannel Temperature(py)", "Temperature[°C]", [-50, 100])
        draw(ax4, status.pannel_temp_py_hist(), "Pannel Temperature(ny)", "Temperature[°C]", [-50, 100])
        draw(ax6, status.pannel_temp_py_hist(), "Pannel Temperature(pz)", "Temperature[°C]", [-50, 100])
        draw(ax8, status.pannel_temp_py_hist(), "Pannel Temperature(nz)", "Temperature[°C]", [-50, 100])
        plt.tight_layout()
        plt.pause(.001)
        plt.clf()
    def recordData(self, data):
        self.output_writer.writerow( ["[%s]"%time.ctime()]+data.members() )
        if time.time() - self.output_file_birthtime > self.output_file_ttl:
            self.output_file.close()
            self.output_file = open("log/"+"_".join(time.ctime().split(" ")[1:4])+".csv", "w")
            self.output_writer = csv.writer(self.output_file, lineterminator='\n')
            self.output_file_birthtime = time.time()
    def sendCommand(self, ch):
        if ch == ord("a"):
            self.command_ch = "a"
        if ch == ord("b"):
            self.command_ch = "b"
        if ch == ord("c"):
            self.command_ch = "c"
        if ch == ord("\n"):
            if self.command_ch == "a":
                self.serial.write("dbgmaicou1")
            if self.command_ch == "b":
                self.serial.write("dbgmaicd2")
            if self.command_ch == "c":
                self.serial.write("dbgmaicob1")  
        
    def run(self):
        #self.serial = serial.Serial(self.serial_port, 38400)
        status = DebugStatus()
        while True:
            #serial_input = self.serial.readline()
            serial_input = "16/1/1/1:12:0,255,255,79,69,33,34,33,176,118,7," + \
                            "110,0,1,0,27,3,36,37,36,37,128,32,21,0,7"
            if serial_input[:5] == "start":
                self.last_reset_time = time.time()
                continue
            if len(serial_input.split(",")) != self.sig_num:
                continue
            input_data = InputData(serial_input)
            status.append(input_data)
            self.recordData(input_data)
            self.__debug_print(input_data)
            self.__draw_graphs(status)

if __name__ == "__main__":
    args = docopt(__doc__, version="{0} {1}".format(__NAME__, __version__))
    serial_port = args[b"<serial_port>"]
    #option = int(args[b"--option"])
    plt.ion()
    with DebugMonitor(serial_port) as monitor:
        monitor.run()
    
