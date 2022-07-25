#from isofit.core.isofit import Isofit
from isofit.configs.base_config import BaseConfigSection
from isofit.configs.configs import Config
from isofit.utils import surface_model
from isofit.core.forward import ForwardModel
from isofit.configs.configs import create_new_config, get_config_differences
from isofit.inversion.inverse import Inversion
from isofit.core.fileio import IO
import numpy as np
import matplotlib.pyplot as plt
#from tkinter import * 

print('BUILDING ...')


# Surface model
surface_model("examples/20171108_Pasadena/configs/ang20171108t184227_surface.json")

config = create_new_config("examples/20171108_Pasadena/configs/ang20171108t184227_beckmanlawn.json")

fm = ForwardModel(config)


sample_state_vector = np.zeros(427)
sample_state_vector[425] = 1.75 # water vapor
sample_state_vector[426] = 0.05 # aerosol
#print(fm.out_of_bounds(sample_state_vector))
val = 0
for i in range(425):
  val = val + 0.001
  sample_state_vector[i] = val

inv = Inversion(config, fm)
io = IO(config, fm)

io.get_components_at_index(0, 0)
geom = io.current_input_data.geom # alternately, call via geom = Geometry()...this won't have data from the above config file
meas = io.current_input_data.meas  # alternately, pass in a num_wavelength numpy array (e.g., 425)
x_surface = sample_state_vector[fm.idx_surface]

##assert(fm.xa(sample_state_vector, geom).shape == sample_state_vector.shape)
# RT parameters should not have changed
##assert(fm.xa(sample_state_vector, geom)[-2:].all() == sample_state_vector[-2:].all())

print(fm.surface.component(sample_state_vector, geom))

"""

channels = np.linspace(1,425,425)
plt.plot(sample_state_vector[:425], channels, label = 'surface reflectance')
plt.savefig()

"""




#import pdb; pdb.set_trace();
##assert(fm.Sa(sample_state_vector,geom).shape == (427,427))
#fm.calc_rfl(sample_state_vector, geom)
##print((fm.calc_meas(sample_state_vector, geom)).shape)

assert(fm.calc_lamb(sample_state_vector, geom).all() == sample_state_vector[:425].all())
assert(fm.calc_rfl(sample_state_vector, geom).all() == sample_state_vector[:425].all())


assert(len(fm.unpack(sample_state_vector)) == 3)
assert(fm.unpack(sample_state_vector)[0].all() == sample_state_vector[:425].all())
assert(fm.unpack(sample_state_vector)[1].all() == sample_state_vector[425:].all())



#multicomponent_surface.py

assert(fm.surface.calc_lamb(sample_state_vector, geom).all() == sample_state_vector[:425].all())
assert(fm.surface.calc_rfl(sample_state_vector, geom).all() == sample_state_vector[:425].all())

#print(fm.surface.dlamb_dsurface(sample_state_vector, geom))
#print(fm.surface.summarize(sample_state_vector, geom))


print('TESTS COMPLETE')