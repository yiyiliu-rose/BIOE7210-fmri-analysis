#######################################################
#
# Nipype fMRI 2nd Level Analysis tutorial for PSYC7250
# Professor: Stephanie Noble
#
# Guide: https://docs.google.com/document/d/1WC4bihzVXwzXBcKWGxSpqDKQ3XUU9h-7TiL58xZQdV0/edit#heading=h.n3roqcmzam5l
# Reference: https://miykael.github.io/nipype_tutorial/notebooks/handson_analysis.html
#
#######################################################
##### USER-DEFINED #####

course_dir = '/courses/PSYC5301.202630'
results_dir = course_dir+'/students/liu.yiyi3/output/'

# System paths

matlab_path = '/opt/matlab/bin/matlab' # from the binding we set
spm_path = '/shared/centos7/spm/12'

### Import Modules

from nipype import Node, Workflow

# Specify which SPM to use
from nipype.interfaces.matlab import MatlabCommand
MatlabCommand.set_default_paths(matlab_path)

MatlabCommand.set_default_paths(spm_path)
from nipype.interfaces import spm
spm.SPMCommand.set_mlab_paths(matlab_cmd=matlab_path)


# Typically we would include all imports here, but for clarity in seeing what
# goes with what, we we do it at each step

## Set Data Paths

data_dir = course_dir+'/data/ds000114-tutorial/'
gm_mask = course_dir+'/data/GM_mask.nii' # comes from tpm_img - see below


## Create the workflow

# Hint: use 'base_dir' to specify where to store the working directory
analysis2nd = Workflow(name='work_2nd', base_dir=results_dir)

# Nodes: Create 2nd-Level design matrix, estimation, and contrasts

from nipype.interfaces.spm import OneSampleTTestDesign
# Initiate the OneSampleTTestDesign node here
onesamplettestdes = Node(OneSampleTTestDesign(), name="onesampttestdes")

from nipype.interfaces.spm import EstimateModel, EstimateContrast
# Initiate the EstimateModel and the EstimateContrast node here
level2estimate = Node(EstimateModel(estimation_method={'Classical': 1}),
                      name="level2estimate")

level2conestimate = Node(EstimateContrast(group_contrast=True),
                         name="level2conestimate")

cont01 = ['Group', 'T', ['mean'], [1]]
level2conestimate.inputs.contrasts = [cont01]

# Connect OneSampleTTestDesign, EstimateModel and EstimateContrast here
analysis2nd.connect([(onesamplettestdes, level2estimate, [('spm_mat_file',
                                                           'spm_mat_file')]),
                     (level2estimate, level2conestimate, [('spm_mat_file',
                                                           'spm_mat_file'),
                                                          ('beta_images',
                                                           'beta_images'),
                                                          ('residual_image',
                                                           'residual_image')])
                    ])

# Node: Set inferential procedure - Topological FDR with voxelwise p<0.01, cluster FDR p<0.05

# Note: TopoFDR is not very common for inference, but it's nice nipype chose it since there's
# a growing consensus that high dimensional biomedical fields may often prefer FDR >FWER
# for improved sensitivity worth the minimal increase in FP
# See TopoFDR ref: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3221040/
# Downside: this relies on parametric RFT estimates - nonparametric generally preferred: https://www.pnas.org/doi/full/10.1073/pnas.1602413113
# (For more on this topic, see discussion in https://www.sciencedirect.com/science/article/pii/S1053811919310596?via%3Dihub)

from nipype.interfaces.spm import Threshold
level2thresh = Node(Threshold(contrast_index=1,
                              use_topo_fdr=True,
                              use_fwe_correction=False,
                              extent_threshold=0,
                              height_threshold=0.05,
                              height_threshold_type='p-value',
                              extent_fdr_p_threshold=0.05),
                    name="level2thresh")
# Connect the Threshold node to the EstimateContrast node here
analysis2nd.connect([(level2conestimate, level2thresh, [('spm_mat_file',
                                                         'spm_mat_file'),
                                                        ('spmT_images',
                                                         'stat_image'),
                                                       ])
                    ])

# # DO THIS PART IN BASH
# Node: Restrict Gray Matter Mask - do in bash


# typically TPM is in an SPM directory, e.g.,  /opt/spm12-r7219/spm12_mcr/spm12/tpm/TPM.nii, but we copied this image to data
# TODO: locate the official path

# # you might have to run this first - technically fsl wants stuff like this to be set up in your shell config
# export FSLOUTPUTTYPE=NIFTI

# # %%bash
# GM_MASK_FILENAME='/courses/PSYC7250.202430/staff/s.noble/output/datasink_handson/GM_mask.nii'
# TEMPLATE='/courses/PSYC7250.202430/data/TPM.nii'

# # Extract the first volume with `fslroi`
# fslroi $TEMPLATE GM_PM.nii 0 1

# # Threshold the probability mask at 10%
# fslmaths GM_PM.nii -thr 0.10 -bin $GM_MASK_FILENAME

# # Unzip the mask and delete the GM_PM.nii file
# # gunzip $GM_MASK_FILENAME
# rm GM_PM.nii
 
    
# # BACK TO PYTHON
onesamplettestdes.inputs.explicit_mask_file = gm_mask

# Import the SelectFiles
from nipype import SelectFiles

# String template with {}-based strings
templates = {'cons': results_dir+'/work_1st/_subj_id_*/normalize/w*_{cont_id}.nii'}

# Create SelectFiles node
sf = Node(SelectFiles(templates, sort_filelist=True),
          name='selectfiles')

# list of contrast identifiers
contrast_id_list = ['0001', '0002', '0003', '0004', '0005',
                    '0006', '0007', '0008', '0009']
sf.iterables = [('cont_id', contrast_id_list)]

# connect
analysis2nd.connect([(sf, onesamplettestdes, [('cons', 'in_files')])])

# Node: Data sink - get rid of unwanted intermediates / derivatives

from nipype.interfaces.io import DataSink
# Initiate DataSink node here
# Initiate the datasink node
output_folder = 'datasink_handson'
datasink = Node(DataSink(base_directory=results_dir,
                         container=output_folder),
                name="datasink")
## Use the following substitutions for the DataSink output
substitutions = [('_cont_id_', 'con_')]
datasink.inputs.substitutions = substitutions

# Connect nodes to datasink here
analysis2nd.connect([(level2conestimate, datasink, [('spm_mat_file',
                                                     '2ndLevel.@spm_mat'),
                                                    ('spmT_images',
                                                     '2ndLevel.@T'),
                                                    ('con_images',
                                                     '2ndLevel.@con')]),
                    (level2thresh, datasink, [('thresholded_map',
                                               '2ndLevel.@threshold')])
                     ])

# # Run workflow

analysis2nd.run('MultiProc', plugin_args={'n_procs': 8})
