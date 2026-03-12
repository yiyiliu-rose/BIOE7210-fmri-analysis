#######################################################
#
# Nipype fMRI processing tutorial for PSYC7250
# Professor: Stephanie Noble
#
# Guide: https://docs.google.com/document/d/1WC4bihzVXwzXBcKWGxSpqDKQ3XUU9h-7TiL58xZQdV0/edit
# Reference: https://miykael.github.io/nipype_tutorial/notebooks/handson_preprocessing.html
#
#######################################################


### Import Modules

# Get the Node and Workflow object
from nipype import Node, Workflow

# Specify which SPM to use
from nipype.interfaces.matlab import MatlabCommand
MatlabCommand.set_default_paths('/shared/centos7/spm/12')

# Typically we would include all imports here, but for clarity in seeing what
# goes with what, we we do it at each step

## Set Paths

##### USER-DEFINED #####

data_dir = '/courses/PSYC7250.202430/data/ds000114-tutorial/'
results_dir = '/courses/PSYC7250.202430/students/<your.username>/output/'


### Nodes and Workflow Connections

## Workflow

# Create the workflow here
# Hint: use 'base_dir' to specify where to store the working directory
preproc = Workflow(name='work_preproc', base_dir=results_dir)


# In the following, we define distinct steps as "nodes"
# and connect them to the workflow with "connect"



## Subset data with SelectFiles and iterables

# Import the SelectFiles
from nipype import SelectFiles

# String template with {}-based strings
templates = {'anat': 'sub-{subject_id}/ses-{ses_id}/anat/'
                     'sub-{subject_id}_ses-test_T1w.nii.gz',
             'func': 'sub-{subject_id}/ses-{ses_id}/func/'
                     'sub-{subject_id}_ses-{ses_id}_task-{task_id}_bold.nii.gz'}

# Create SelectFiles node
sf = Node(SelectFiles(templates,
                      base_directory=data_dir,
                      sort_filelist=True),
          name='selectfiles')
sf.inputs.ses_id='test'
sf.inputs.task_id='fingerfootlips'

# select subject 7
subject_list = ['07']
# subject_list = ['02','04','05','07','08', '09']
sf.iterables = [('subject_id', subject_list)]


## Gunzip (e.g., for SPM)
from nipype.algorithms.misc import Gunzip

# Initiate Gunzip node
gunzip_anat = Node(Gunzip(), name='gunzip_anat')
gunzip_func = Node(Gunzip(), name='gunzip_func')


# Connect SelectFiles node to the other nodes here
preproc.connect([(sf, gunzip_anat, [('anat', 'in_file')]),
                 (sf, gunzip_func, [('func', 'in_file')])])



## Drop dummy scans

# Visualize
#%matplotlib inline
#import pylab as plt
#import nibabel as nb
#plt.plot(nb.load(func_file).get_fdata()[32, 32, 15, :]);

# from nipype.interfaces.fsl import ExtractROI
# extract = Node(ExtractROI(t_min=4, t_size=-1, output_type='NIFTI'),
#               name="extract")

# preproc.connect([(gunzip_func, extract, [('out_file', 'in_file')])])


# to run directly

# from nipype.interfaces.fsl import ExtractROI
# extract=ExtractROI(in_file=data_dir+'sub-07/ses-test/func/sub-07_ses-test_task-fingerfootlips_bold.nii.gz',
#            roi_file=data_dir+'test.nii.gz', t_min=4, t_size=-1, output_type='NIFTI')
# print(data_dir+'test.nii.gz')
# result=extract.run()

## Slice time correction

from nipype.interfaces.spm import SliceTiming

# Here, we set the slice order and other parameters manually based on known scan parameters
slice_order = list(range(1, 31, 2)) + list(range(2, 31, 2))

# Visualize
#print(slice_order)

# Initiate SliceTiming node here
slicetime = Node(SliceTiming(num_slices=30,
                             ref_slice=15,
                             slice_order=slice_order,
                             time_repetition=2.5,
                             time_acquisition=2.5-(2.5/30)),
                 name='slicetime')

# Connect SliceTiming node to the other nodes here
# preproc.connect([(extract, slicetime, [('roi_file', 'in_files')])])
preproc.connect([(gunzip_func, slicetime, [('out_file', 'in_files')])])

## Motion Correction
# typically a time-intensive step

from nipype.interfaces.fsl import MCFLIRT
# Initiate MCFLIRT node here

mcflirt = Node(MCFLIRT(mean_vol=True,
                       save_plots=True),
               name="mcflirt")

# Connect MCFLIRT node to the other nodes here
preproc.connect([(slicetime, mcflirt, [('timecorrected_files', 'in_file')])])

## Artifact Detection

from nipype.algorithms.rapidart import ArtifactDetect
art = Node(ArtifactDetect(norm_threshold=2,
                          zintensity_threshold=2,
                          mask_type='spm_global',
                          parameter_source='FSL',
                          use_differences=[True, False],
                          plot_type='svg'),
           name="art")

preproc.connect([(mcflirt, art, [('out_file', 'realigned_files'),
                                 ('par_file', 'realignment_parameters')])
                 ])

## Segmentation of an anatomical image

from nipype.interfaces.spm import NewSegment
# Use the following tissue specification to get a GM and WM probability map
# typically TPM is in an SPM directory, e.g.,  /opt/spm12-r7219/spm12_mcr/spm12/tpm/TPM.nii, but we copied this image to data
tpm_img ='/courses/PSYC7250.202430/data/TPM.nii'
tissue1 = ((tpm_img, 1), 1, (True,False), (False, False))
tissue2 = ((tpm_img, 2), 1, (True,False), (False, False))
tissue3 = ((tpm_img, 3), 2, (True,False), (False, False))
tissue4 = ((tpm_img, 4), 3, (False,False), (False, False))
tissue5 = ((tpm_img, 5), 4, (False,False), (False, False))
tissue6 = ((tpm_img, 6), 2, (False,False), (False, False))
tissues = [tissue1, tissue2, tissue3, tissue4, tissue5, tissue6]

# Initiate NewSegment node here
segment = Node(NewSegment(tissues=tissues), name='segment')

preproc.connect([(gunzip_anat, segment, [('out_file', 'channel_files')])])

## Compute Coregistration Matrix (Func -> anat)

from nipype.interfaces.fsl import FLIRT
# Initiate FLIRT node here
# note: removed schedule
coreg = Node(FLIRT(dof=6,
                   cost='bbr',
                   output_type='NIFTI'),
             name="coreg")
# Connect FLIRT node to the other nodes here
preproc.connect([(gunzip_anat, coreg, [('out_file', 'reference')]),
                 (mcflirt, coreg, [('mean_img', 'in_file')])
                 ])

from nipype.interfaces.fsl import Threshold

# Threshold - Threshold WM probability image
threshold_WM = Node(Threshold(thresh=0.5,
                              args='-bin',
                              output_type='NIFTI'),
                name="threshold_WM")

# Select WM segmentation file from segmentation output
def get_wm(files):
    return files[1][0]

# Connecting the segmentation node with the threshold node
preproc.connect([(segment, threshold_WM, [(('native_class_images', get_wm),
                                           'in_file')])])

# Connect Threshold node to coregistration node above here
preproc.connect([(threshold_WM, coreg, [('out_file', 'wm_seg')])])

## Apply Coregistration Matrix to functional image 

# Specify the isometric voxel resolution you want after coregistration
desired_voxel_iso = 4

# Apply coregistration warp to functional images
applywarp = Node(FLIRT(interp='spline',
                       apply_isoxfm=desired_voxel_iso,
                       output_type='NIFTI'),
                 name="applywarp")

# Connecting the ApplyWarp node to all the other nodes
preproc.connect([(mcflirt, applywarp, [('out_file', 'in_file')]),
                 (coreg, applywarp, [('out_matrix_file', 'in_matrix_file')]),
                 (gunzip_anat, applywarp, [('out_file', 'reference')])
                 ])

## Smoothing

from nipype.workflows.fmri.fsl.preprocess import create_susan_smooth


# Initiate SUSAN workflow here
susan = create_susan_smooth(name='susan')
susan.inputs.inputnode.fwhm = 4
# Connect Threshold node to coregistration node above here
preproc.connect([(applywarp, susan, [('out_file', 'inputnode.in_files')])])

## Brain Extraction I: Create Binary Mask

from nipype.interfaces.fsl import FLIRT

# Initiate resample node
resample = Node(FLIRT(apply_isoxfm=desired_voxel_iso,
                      output_type='NIFTI'),
                name="resample")

from nipype.interfaces.fsl import Threshold

# Threshold - Threshold GM probability image
mask_GM = Node(Threshold(thresh=0.5,
                         args='-bin -dilF',
                         output_type='NIFTI'),
                name="mask_GM")

# Select GM segmentation file from segmentation output
def get_gm(files):
    return files[0][0]

preproc.connect([(segment, resample, [(('native_class_images', get_gm), 'in_file'),
                                      (('native_class_images', get_gm), 'reference')
                                      ]),
                 (resample, mask_GM, [('out_file', 'in_file')])
                 ])

## Brain Extraction II: Apply Binary Mask

# Connect gray matter Mask node to the susan workflow here
preproc.connect([(mask_GM, susan, [('out_file', 'inputnode.mask_file')])])

from nipype.interfaces.fsl import ApplyMask

from nipype import MapNode
# Initiate ApplyMask node here
mask_func = MapNode(ApplyMask(output_type='NIFTI'),
                    name="mask_func",
                    iterfield=["in_file"])
# Connect smoothed susan output file to ApplyMask node here
preproc.connect([(susan, mask_func, [('outputnode.smoothed_files', 'in_file')]),
                 (mask_GM, mask_func, [('out_file', 'mask_file')])
                 ])

## Remove linear trends in functional images
# IMPORTANT: we actually want to do this in the analysis stage

from nipype.algorithms.confounds import TSNR
# Initiate TSNR node here
detrend = Node(TSNR(regress_poly=2), name="detrend")
# Connect the detrend node to the other nodes here
preproc.connect([(mask_func, detrend, [('out_file', 'in_file')])])





from nipype.interfaces.io import DataSink

# Data output with DataSink

# Initiate the datasink node
datasink = Node(DataSink(base_directory=results_dir,
                         container='datasink_handson'),
                name="datasink")

# Connect nodes to datasink here
preproc.connect([(art, datasink, [('outlier_files', 'preproc.@outlier_files'),
                                  ('plot_files', 'preproc.@plot_files')]),
                 (mcflirt, datasink, [('par_file', 'preproc.@par')]),
                 (detrend, datasink, [('detrended_file', 'preproc.@func')]),
                 ])

## Visualize the workflow

# Create preproc output graph
preproc.write_graph(graph2use='colored', format='png', simple_form=True)

# Plot graph
#from IPython.display import Image
#Image(filename=results_dir+'work_preproc/graph.png', width=750)


## Run the Workflow

####### DO NOT RUN IN CLASS ##########

preproc.run('MultiProc', plugin_args={'n_procs': 8})