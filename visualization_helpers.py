from random import randint
import plotly.express as px
import streamlit as st
import numpy as np
from utils import fspectra, signaltonoise_dB, signaltonoise
import plotly.graph_objects as go
import tempfile
from streamlit_image_comparison import image_comparison


class VISUALIZATION:
    """The class for 2D/3D visualization
        includes main ui implemented in streamlit
        as viz_seismic_3D, viz_seismic_2D and viz_sidebyside_3D
    """
    def __init__(self, _seismic_data, seismic_type):
        self._seismic_type = seismic_type
        self._vm = _seismic_data.get_vm()
        self._n_samples = _seismic_data.get_n_zslices()
        self._n_il = _seismic_data.get_n_ilines()
        self._n_xl = _seismic_data.get_n_xlines()
        self._sample_rate = _seismic_data.get_sample_rate()
        self._cmap_option = "RdBu"


    def plot_slice(self, data, indx_old, indx_new, last_section, cmap, vmin, vmax):
        """The function that calculated which 
            direction to visualize and viz it

        Args:
            data (SeismicData): Data to viz
            indx_old (int): Previous viz control
            indx_new (int): Current viz control
            last_section (int): Previous viz section 0,1, or 2
            cmap (str): Colormap from px.colors.named_colorscales()
            vmin (float): min range
            vmax (float): max range

        Returns:
            _type_: returns seis - current section, seis_plt - viz plot, 
            indx_old - updated control, last_section - viz section
        """
        seis = np.array([[[255, 0, 0], [0, 255, 0], [0, 0, 255]],
                        [[0, 255, 0], [0, 0, 255], [255, 0, 0]]
                    ], dtype=np.uint8)
        seis_plt = px.imshow(seis)
        difference = np.abs(indx_old - indx_new)

        if np.any(difference):
            find_indx = np.nonzero(difference)[0]
        else:
            find_indx = [last_section]
        
        if find_indx[0] == 0:
            seis = data.get_iline(indx_new[0]).T
            seis_plt = plot_inl(seis, cmap, vmin, vmax)
            last_section = 0
        elif find_indx[0] == 1:
            seis = data.get_xline(indx_new[1]).T
            seis_plt =  plot_xln(seis, cmap, vmin, vmax)
            last_section = 1
        elif find_indx[0] == 2:
            seis = data.get_zslice(indx_new[2]).T
            seis_plt = plot_top(seis,  cmap, vmin, vmax)
            last_section = 2
        seis_plt.update_layout(
            plot_bgcolor='rgba(0,0,0,0)')
        # seis_plt.update_layout(yaxis = dict(scaleanchor = 'x'))
        indx_old = indx_new
        
        return seis, seis_plt, indx_old, last_section
    
    def plotly_color_select(self, key, index=1):
        """ Lists available colormaps

        Returns:
            str: selected colormap
        """
        colorscales = ["gray", "Greys", "RdBu", "RdGy", "Blues", "Reds"] #px.colors.named_colorscales()
        option = st.selectbox(
            'Color Map',
            (colorscales), index=index, key=key)
        return option
    

    def viz_data_3d(self, data, is_fspect, key=0, is_show_metrics=True):
        """Viz data in 3D with slider in 3 direction from streamlit
            + show metrics of the data
            + show freq spectrum plot

        Args:
            data (SeismicData): Data for viz
            is_fspect (bool): if to show freq spectrum plot
            key (int, optional): Unique identifier. Defaults to 0.
            is_show_metrics (bool, optional): if to show data metrics. Defaults to True.
        """
        vm, n_samples, n_il, n_xl = self._vm, self._n_samples, self._n_il, self._n_xl

        if 'viz_'+str(key) not in st.session_state:
            st.session_state['viz_'+str(key)] = {"iline_old": 0, "xline_old" : 0,
                "t_old" : 0, "last_section" : 0}

        if is_show_metrics:
            col1, col2, col3, col4, col5 = st.columns(5)
            col2.metric("Number of Samples", n_samples)
            col3.metric("Number of Inline", n_il)
            col4.metric("Number of Xline", n_xl)
            col5.metric("Sample Rate", self._sample_rate)
            with col1:
                self._cmap_option = self.plotly_color_select(key+1)

        states = st.session_state['viz_'+str(key)]
        col1, col2, col3 = st.columns(3)
        with col1:
            inline_indx = st.slider('Inline', 0, n_il-1, n_il//2, key=key+2)
        with col2:
            xline_indx = st.slider('Xline', 0, n_xl-1, n_xl//2, key=key+3)
        with col3:
            time_indx = st.slider('Time', 0, n_samples-1, n_samples//2, key=key+4)


        index_old = np.array([states['iline_old'], states['xline_old'], states['t_old']])
        

        index_new = np.array([inline_indx, xline_indx, time_indx])
        seis, seis_3d_plot, index_old, last_section = \
        self.plot_slice(data, index_old, index_new, states['last_section'], cmap=self._cmap_option, vmin=-vm, vmax=vm)

        states.update({"iline_old": index_old[0], "xline_old" : index_old[1],
        "t_old" : index_old[2], "last_section" : last_section})

        st.write(seis_3d_plot)
        if is_fspect:
            fspect_plt = self.plot_fspectra(seis, 'Original')
            st.write(fspect_plt)

    def viz_sidebyside_3d(self, data, data2, minmax=False, key=0):
        """Viz 2 sets of data in 3D in side-by-side fashion
            with shared sliders
        Args:
            data (_type_): Data1 to viz
            data2 (_type_): Data2 to viz
            key (int, optional): Unique identifier. Defaults to 0.
        """
        vm, n_samples, n_il, n_xl = self._vm, self._n_samples, self._n_il, self._n_xl
        vmin, vmax = -vm, vm
        vmin2, vmax2 = vmin, vmax
        if not minmax:
            vmin2 = 0
            vmax2 = 100
        if 'viz_'+str(key) not in st.session_state:
            st.session_state['viz_'+str(key)] = {"iline_old": 0, "xline_old" : 0,
                "t_old" : 0, "last_section" : 0}

        states = st.session_state['viz_'+str(key)]
        col1, col2, col3 = st.columns(3)
        with col1:
            inline_indx = st.slider('Inline', 0, n_il-1, n_il//2, key=key+2)
        with col2:
            xline_indx = st.slider('Xline', 0, n_xl-1, n_xl//2, key=key+3)
        with col3:
            time_indx = st.slider('Time', 0, n_samples-1, n_samples//2, key=key+4)

        index_old = np.array([states['iline_old'], states['xline_old'], states['t_old']])

        index_new = np.array([inline_indx, xline_indx, time_indx])

        col1, col2 = st.columns(2)
        with col1:
            self._cmap_option = self.plotly_color_select(key+1)
            _ , seis_3d_plot, _ , _ = \
            self.plot_slice(data, index_old, index_new, states['last_section'], cmap=self._cmap_option, vmin=vmin, vmax=vmax)
            seis_3d_plot.update(layout_coloraxis_showscale=False)
            st.write(seis_3d_plot)
        with col2:
            self._cmap_option = self.plotly_color_select(key+5)
            _ , attr_3d_plot, index_old, last_section = \
            self.plot_slice(data2, index_old, index_new, states['last_section'], cmap=self._cmap_option, vmin=vmin2, vmax=vmax2)
            st.write(attr_3d_plot)

        states.update({"iline_old": index_old[0], "xline_old" : index_old[1],
        "t_old" : index_old[2], "last_section" : last_section})
       
    def viz_data_2d(self, data, is_fspect, key=0, is_show_metrics=True):
        """Viz data in 2D
            + show metrics of the data
            + show freq spectrum plot

        Args:
            data (SeismicData): Data for viz
            is_fspect (bool): if to show freq spectrum plot
            key (int, optional): Unique identifier. Defaults to 0.
            is_show_metrics (bool, optional): if to show data metrics. Defaults to True.
        """
        vm, n_samples, n_il, n_xl = self._vm, self._n_samples, self._n_il, self._n_xl

        if is_show_metrics:
            col1, col2, col3, col4 = st.columns(4)
            col2.metric("Number of Samples", n_samples)
            col3.metric("Number of Inline", n_il)
            col4.metric("Number of Xline", n_xl)
            with col1:
                self._cmap_option = self.plotly_color_select(key+1)

        seis_plt = plot_seis(data,cmap=self._cmap_option, vmin=-vm, vmax=vm)
        st.write(seis_plt)
        if is_fspect:
            with st.expander("Amplitude spectra"):
                fspect_plt = self.plot_fspectra(data, 'Original')
                st.write(fspect_plt)

    def viz_sidebyside_2d(self, data1, data2, is_fspect, minmax = False, key=0, is_show_metrics=True):
        """Viz data in 2D
            + show metrics of the data
            + show freq spectrum plot

        Args:
            data1 (SeismicData): Data for viz
            data2 (SeismicData): Data for viz
            is_fspect (bool): if to show freq spectrum plot
            minmax (bool): min-max normalization
            key (int, optional): Unique identifier. Defaults to 0.
            is_show_metrics (bool, optional): if to show data metrics. Defaults to True.
        """
        vm, n_samples, n_il, n_xl = self._vm, self._n_samples, self._n_il, self._n_xl
        vmin, vmax = -vm, vm
        if minmax:
            vmin = np.min(data1) if np.min(data1) < np.min(data2) else np.min(data2)
            vmax = np.max(data1) if np.max(data1) > np.max(data2) else np.max(data2)
        if is_show_metrics:
            col1, col2, col3, col4 = st.columns(4)
            col2.metric("Number of Samples", n_samples)
            col3.metric("Number of Inline", n_il)
            col4.metric("Number of Xline", n_xl)
            with col1:
                self._cmap_option = self.plotly_color_select(key+1)
        col1, col2 = st.columns(2)
        data1_plt = plot_seis(data1,cmap=self._cmap_option, vmin=vmin, vmax=vmax)
        col1.write(data1_plt)
        data2_plt = plot_seis(data2,cmap=self._cmap_option, vmin=vmin, vmax=vmax)
        col2.write(data2_plt)
        if is_fspect:
            with st.expander("Amplitude spectra"):
                smooth = 2.0
                fspect_plt = plot_fspectra(data1, "data1", self._sample_rate, smooth, data2=data2, data2_name="data2")
                st.write(fspect_plt)


    def compare_two_fig_2D(self, data1, data1_name, data2, data2_name, is_fspect, sample_rate):
        """Viz 2 sets of data with comparison slider

        Args:
            data1 (SeismicData): 2D Data1 to viz
            data1_name (str): Name Data1
            data2 (SeismicData): 2D Data2 to viz
            data2_name (str): Name Data2
            is_fspect (bool): if to show freq spectrum plot
            sample_rate (float): sampling rate
        """
        vm, cmap_option = self._vm, self._cmap_option
        compare_two_fig_2D_helper(data1, data2, cmap_option, vm)
        if is_fspect:
            with st.expander("Amplitude spectra"):
                smooth = 2.0
                fspect_plt = plot_fspectra(data1, data1_name, sample_rate, smooth, data2=data2, data2_name=data2_name)
                st.write(fspect_plt)

    def plot_fspectra(self, data1, data1_name):
        col1, col2, col3, col4, col5 = st.columns(5)
        smooth = col2.slider('Smoothing', 0.0, 4.0, 2.0, key=100)
        sample_rate = col1.number_input("Sample Rate", min_value=1, value=int(self._sample_rate/1000), format='%i', key=101)
        #col3.text((signaltonoise(data1)))

        fspect_plt = plot_fspectra(data1, data1_name, sample_rate, smooth)
        return fspect_plt

    def plot_fspectra_2(self, data1, data1_name, data2, data2_name):
        col1, col2, col3, col4, col5 = st.columns(5)
        smooth = col2.slider('Smoothing', 0.0, 4.0, 2.0, key=102)
        sample_rate = col1.number_input("Sample Rate", min_value=1, value=int(self._sample_rate/1000), format='%i',key=103)
        fspect_plt = plot_fspectra(data1, data1_name, sample_rate, smooth, data2=data2, data2_name=data2_name)
        st.write(fspect_plt)
        return fspect_plt

    def plot_fspectra_3(self, data1, data1_name, data2, data2_name, data3, data3_name):
        col1, col2, col3, col4, col5 = st.columns(5)
        smooth = col2.slider('Smoothing', 0.0, 4.0, 2.0)
        sample_rate = col1.number_input("Sample Rate", min_value=1, value=int(self._sample_rate/1000), format='%i')
        fspect_plt = plot_fspectra(data1, data1_name, sample_rate, smooth, data2=data2, data2_name=data2_name, data3=data3, data3_name=data3_name)
        st.write(fspect_plt)
        return fspect_plt
    
    # OVERLAY
    """
    def get_flt_mask(self, attr, eps):
        flt_mask = np.ones([attr.shape[0], attr.shape[1], 4])
        flt_mask[:, :, 0][attr > eps] = 255
        flt_mask[:, :, 1][attr > eps] = 0
        flt_mask[:, :, 2][attr > eps] = 0
        flt_mask[:, :, 3][attr > eps] = 255
        return flt_mask

    def plot_slice_overlay(self, seis_data, attr_data, indx_old, indx_new, last_section, cmap, vm):
        seis = np.array([[[255, 0, 0], [0, 255, 0], [0, 0, 255]],
                        [[0, 255, 0], [0, 0, 255], [255, 0, 0]]
                    ], dtype=np.uint8)
        # seis_plt = px.imshow(seis)
        difference = np.abs(indx_old - indx_new)


        if np.any(difference):
            find_indx = np.nonzero(difference)[0]
        else:
            find_indx = [last_section]
        
        seis_plt = go.Figure()
        
        if find_indx[0] == 0:
            seis = seis_data.get_iline(indx_new[0]).T
            attr = attr_data.get_iline(indx_new[0])
            attr2 = self.get_flt_mask(attr, 0.9)
            attr = self.get_flt_mask(attr.T, 0.9)
            # seis_plt.add_trace(px.imshow(seis).data[0])
            # seis_plt = plot_inl(seis, cmap, -vm, vm)
            seis_plt = plot_inl(seis, cmap, -vm, vm)
            seis_plt.add_image(z=attr, colormodel='rgba256')
            # seis_plt.add_trace(px.imshow(attr).data[0])
            # seis_plt.add_trace(px.imshow(attr).data[0])
            # seis_plt.add_trace(px.imshow(attr).data[0], )
            last_section = 0
        elif find_indx[0] == 1:
            seis = seis_data.get_xline(indx_new[1]).T
            attr = attr_data.get_xline(indx_new[1]).T
            seis_plt =  plot_xln(seis, cmap, -vm, vm)
            attr = self.get_flt_mask(attr, 0.1)
            seis_plt.add_trace(px.imshow(attr).data[0])
            last_section = 1
        elif find_indx[0] == 2:
            seis = seis_data.get_zslice(indx_new[2]).T
            attr = attr_data.get_zslice(indx_new[2]).T
            seis_plt = plot_top(seis,  cmap, -vm, vm)
            attr = self.get_flt_mask(attr, 0.1)
            seis_plt.add_trace(px.imshow(attr).data[0])
            last_section = 2
        seis_plt.update_layout(
            plot_bgcolor='rgba(0,0,0,0)')
        indx_old = indx_new
        
        return seis, seis_plt, indx_old, last_section

    def visualize_seis_attr_3D(self, seismic_data, attr_data):          
        vm, n_samples, n_il, n_xl = self._vm, self._n_samples, self._n_il, self._n_xl

        if 'keys' not in st.session_state:
            st.session_state.keys = 1
            st.session_state.iline_old = 0
            st.session_state.xline_old = 0
            st.session_state.t_old = 0
            # 1 - inline, 2 - xline, 3 - time
            st.session_state.last_section = 0

        col1, col2, col3 = st.columns(3)
        with col1:
            inline_indx = st.slider('Inline', 0, n_il-1, n_il//2)
        with col2:
            xline_indx = st.slider('Xline', 0, n_xl-1, n_xl//2)
        with col3:
            time_indx = st.slider('Time', 0, n_samples-1, n_samples//2)

        index_old = np.array([st.session_state.iline_old, st.session_state.xline_old, st.session_state.t_old])
        index_new = np.array([inline_indx, xline_indx, time_indx])
        seis, seis_3d_plot, index_old, st.session_state.last_section = self.plot_slice(seismic_data, index_old, index_new, st.session_state.last_section, cmap=self._cmap_option, vm=vm)
        # seis_3d_plot, index_old, st.session_state.last_section = self.plot_slice(seismic_data, index_old, index_new, st.session_state.last_section, cmap=self._cmap_option, vm=vm)
        seis_3d_plot.add_trace(px.imshow(attr_data[inline_indx, :, :]).data[0])
        st.session_state.iline_old, st.session_state.xline_old, st.session_state.t_old = index_old
        st.write(seis_3d_plot)
        """

def plot_seis(seis, cmap, vmin, vmax): 
    seis_plot = px.imshow(seis, zmin=vmin, zmax=vmax, aspect='auto', labels=dict(x="Xline_idx", y="Time_idx", color="Amplitude"), color_continuous_scale=cmap)
    return seis_plot

def plot_inl(seis, cmap, vmin, vmax): 
    seis_plot = px.imshow(seis, zmin=vmin, zmax=vmax, aspect='auto', labels=dict(x="Xline_idx", y="Time_idx", color="Amplitude"), color_continuous_scale=cmap)
    return seis_plot

def plot_xln(seis, cmap, vmin, vmax):
    seis_plot = px.imshow(seis, zmin=vmin, zmax=vmax, aspect='auto', labels=dict(x="Iline_idx", y="Time_idx", color="Amplitude"), color_continuous_scale=cmap)
    return seis_plot

def plot_top(seis, cmap, vmin, vmax):
    seis_plot = px.imshow(seis, zmin=vmin, zmax=vmax, aspect='auto', labels=dict(x="Xline_idx", y="Iline_idx", color="Amplitude"), color_continuous_scale=cmap)
    return seis_plot

st.experimental_memo
def save_figure_in_temp(fig1):
    fig1_path = tempfile.NamedTemporaryFile()
    fig1.write_image(fig1_path.name+".jpg")
    return fig1_path.name+".jpg"

# @st.experimental_memo(suppress_st_warning=True)
def compare_two_fig_2D_helper(data1, data2, cmap_option, vm):         
    data1_plt = plot_seis(data1,cmap=cmap_option, vmin=-vm, vmax=vm)
    data2_plt = plot_seis(data2,cmap=cmap_option, vmin=-vm, vmax=vm)
    fig1_path = save_figure_in_temp(data1_plt)
    fig2_path = save_figure_in_temp(data2_plt)
    image_comparison(
            img1=fig1_path,
            img2=fig2_path,
        )

def add_trace_to_fspectra_fig(fig, freq, data, data_name, sample_rate, smooth):
    _, ampb = fspectra(data, dt=sample_rate, sigma=smooth)
    fig.add_trace(go.Scatter(x=freq, y=ampb,
                    mode='lines',
                    name=data_name))
    return fig
    
def plot_fspectra(data1, data1_name, sample_rate, smooth, *args, **kwargs):
    data2, data3 = kwargs.get('data2', None), kwargs.get('data3', None)
    data2_name, data3_name = kwargs.get('data2_name', None), kwargs.get('data3_name', None)

    freq, ampa = fspectra(data1, dt=sample_rate, sigma=smooth)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=freq, y=ampa,
                        mode='lines',
                        name=data1_name))
    if data2 is not None:
        fig = add_trace_to_fspectra_fig(fig, freq, data2, data2_name, sample_rate, smooth)
    if data3 is not None:
        fig = add_trace_to_fspectra_fig(fig, freq, data3, data3_name, sample_rate, smooth)
    fig.update_layout(title='Amplitude spectra',
                        xaxis_title='Frequency (Hz)',
                        yaxis_title='Amplitude',
                        xaxis_range=[0,110],
                        )
    # print("sample_ratesample_ratesample_ratesample_rate, ", sample_rate)
    return fig



