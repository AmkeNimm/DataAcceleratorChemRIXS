import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as st

from chemrixs.utils import *


def proc_TT(proc):
    expected_count = st.mode(proc.data.integrating.axis_svls.count, keepdims=False)[0]

    mask_on = ((proc.data.integrating.axis_svls.eventcodes[:,proc.data.yaml['evc'][True]]/proc.data.integrating.axis_svls.count) >0.5).squeeze()# (data.integrating.axis_svls.eventcodes[:,272]==1)# np.asarray([data.integrating.axis_svls.eventcodes[:,data.yaml['evc'][True]]/expected_count>0.5]).squeeze()
    mask_off = ((proc.data.integrating.axis_svls.eventcodes[:,proc.data.yaml['evc'][False]]/proc.data.integrating.axis_svls.count) >0.5).squeeze() #(data.integrating.axis_svls.eventcodes[:,273]==1)#
    piranha = np.flip(proc.data.integrating.axis_svls.piranha)
    piranha_on = np.flip(proc.data.integrating.axis_svls.piranha[mask_on,:])
    piranha_off = np.flip(proc.data.integrating.axis_svls.piranha[mask_off,:])

    x = np.arange(len(piranha_on))

    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot((np.nanmean(piranha_on,axis=0))-(np.mean(piranha_off,axis=0)),label='laser on-laser off')
    ax.plot(((np.nanmean(piranha_on,axis=0))/(np.mean(piranha_off,axis=0))-1)*2e5,label='laser on/laser off')
    ax.legend()
    ax.set_title("Drag lines to select ROI. Press Enter to confirm.")

    # Initial ROI guess (center region)
    x1 = len(x) * 0.3
    x2 = len(x) * 0.7

    line1 = ax.axvline(x1, color='blue', linestyle='--')
    line2 = ax.axvline(x2, color='blue', linestyle='--')

    selected_line = {'line': None}

    def on_click(event):
        if event.inaxes != ax:
            return
        # select closest line
        if abs(event.xdata - line1.get_xdata()[0]) < abs(event.xdata - line2.get_xdata()[0]):
            selected_line['line'] = line1
        else:
            selected_line['line'] = line2

    def on_motion(event):
        if selected_line['line'] is None:
            return
        if event.inaxes != ax:
            return
        selected_line['line'].set_xdata([event.xdata])
        fig.canvas.draw_idle()

    def on_release(event):
        selected_line['line'] = None

    confirmed = {'done': False}

    def on_key(event):
        if event.key == 'enter':
            confirmed['done'] = True
            plt.close(fig)

    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('motion_notify_event', on_motion)
    fig.canvas.mpl_connect('button_release_event', on_release)
    fig.canvas.mpl_connect('key_press_event', on_key)

    plt.show()

    # Wait until user presses Enter
    while not confirmed['done']:
        plt.pause(0.1)

    ROI = sorted([line1.get_xdata()[0], line2.get_xdata()[0]])

    print("Selected ROI:", ROI)

    # Continue processing using ROI here if desired

    return ROI